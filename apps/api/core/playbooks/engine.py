import json
import uuid
import logging
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime, timezone, timedelta
from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession

from apps.api.models import PlaybookDefinition, PlaybookRun, CsmProfile, Customer, Intervention
from apps.api.core.outreach.adapters import get_adapter

logger = logging.getLogger(__name__)

async def assign_csm_for_human_task(
    db: AsyncSession,
    tenant_id: uuid.UUID,
    node: Dict[str, Any]
) -> Tuple[Optional[uuid.UUID], str]:
    """
    Auto-assigns human task to the CSM with available capacity and matching specialty.
    If all CSMs are at capacity, queues task as 'unassigned_overflow'.
    """
    specialty_tag = node.get("specialty_tag")

    res = await db.execute(
        select(CsmProfile).where(
            and_(
                CsmProfile.tenant_id == tenant_id,
                CsmProfile.is_available == True,
                CsmProfile.current_active_count < CsmProfile.max_active_accounts
            )
        ).order_by(CsmProfile.current_active_count.asc())
    )
    csms = res.scalars().all()

    if not csms:
        logger.warning(f"All CSMs at capacity for tenant {tenant_id}. Task queued as unassigned_overflow.")
        return None, "unassigned_overflow"

    selected_csm = None
    if specialty_tag:
        for csm in csms:
            tags = csm.specialty_tags or []
            if specialty_tag in tags:
                selected_csm = csm
                break

    if not selected_csm:
        selected_csm = csms[0]

    selected_csm.current_active_count += 1
    return selected_csm.user_id, "assigned"

def evaluate_condition(customer: Customer, state_data: Dict[str, Any], node: Dict[str, Any]) -> bool:
    """
    Evaluates conditional branch against customer metrics or state_data vars.
    """
    cond_type = node.get("condition_type", "var_check")
    var_name = node.get("var_name")
    expected_val = node.get("expected_value")

    vars_dict = state_data.get("vars", {})

    if cond_type == "customer_replied":
        return bool(vars_dict.get("customer_replied", False))
    elif cond_type == "risk_tier":
        return customer.churn_risk_tier == expected_val
    elif cond_type == "var_check" and var_name:
        return vars_dict.get(var_name) == expected_val
    else:
        return bool(vars_dict.get("branch_condition", True))

async def advance_playbook_run(db: AsyncSession, run_id: uuid.UUID) -> PlaybookRun:
    """
    Resumable/crash-safe playbook execution engine. Advances PlaybookRun graph state by one step
    and immediately persists updated node/state to DB.
    """
    import sqlalchemy
    res_run = await db.execute(select(PlaybookRun).where(PlaybookRun.id == run_id))
    run = res_run.scalars().first()
    if not run or run.status in ["completed", "failed"]:
        return run

    await db.execute(sqlalchemy.text(f"SET LOCAL app.current_tenant = '{run.tenant_id}'"))

    now = datetime.now(timezone.utc)

    # If delay timer active and not elapsed
    if run.next_step_at and now < run.next_step_at:
        logger.info(f"PlaybookRun {run.id} paused waiting for delay until {run.next_step_at}")
        return run

    res_pb = await db.execute(select(PlaybookDefinition).where(PlaybookDefinition.id == run.playbook_id))
    playbook = res_pb.scalars().first()
    if not playbook or not playbook.graph:
        run.status = "failed"
        await db.commit()
        return run

    nodes = {n["id"]: n for n in playbook.graph.get("nodes", [])}
    edges = playbook.graph.get("edges", [])

    current_node = nodes.get(run.current_node_id)
    if not current_node:
        run.status = "completed"
        run.completed_at = now
        await db.commit()
        return run

    # Fetch Customer
    res_c = await db.execute(select(Customer).where(Customer.id == run.customer_id))
    customer = res_c.scalars().first()

    state = run.state_data or {"vars": {}, "history": []}
    history = state.get("history", [])

    node_type = current_node.get("type", "action")
    next_node_id = None

    if node_type == "action":
        channel = current_node.get("channel", "email")
        template = current_node.get("template", "Playbook notification")
        if customer:
            adapter = get_adapter(channel)
            try:
                await adapter.send(db, customer, template)
            except Exception as e:
                logger.error(f"Action node failed: {e}")

        history.append({
            "node_id": run.current_node_id,
            "type": "action",
            "channel": channel,
            "executed_at": now.isoformat()
        })
        # Find edge
        out_edges = [e for e in edges if e["source"] == run.current_node_id]
        if out_edges:
            next_node_id = out_edges[0]["target"]

    elif node_type == "delay":
        delay_hours = current_node.get("delay_hours", 1)
        if run.next_step_at is None:
            # Set timer
            run.next_step_at = now + timedelta(hours=delay_hours)
            run.updated_at = now
            await db.commit()
            return run

        # Timer elapsed, advance
        run.next_step_at = None
        history.append({
            "node_id": run.current_node_id,
            "type": "delay",
            "completed_at": now.isoformat()
        })
        out_edges = [e for e in edges if e["source"] == run.current_node_id]
        if out_edges:
            next_node_id = out_edges[0]["target"]

    elif node_type == "condition":
        cond_bool = evaluate_condition(customer, state, current_node)
        history.append({
            "node_id": run.current_node_id,
            "type": "condition",
            "eval_result": cond_bool,
            "evaluated_at": now.isoformat()
        })
        if cond_bool:
            next_node_id = current_node.get("true_target")
        else:
            next_node_id = current_node.get("false_target")

        # Fallback to edges if targets not explicitly in node
        if not next_node_id:
            out_edges = [e for e in edges if e["source"] == run.current_node_id]
            if out_edges:
                next_node_id = out_edges[0]["target"]

    elif node_type == "human_task":
        csm_id, task_stat = await assign_csm_for_human_task(db, run.tenant_id, current_node)
        run.assigned_csm_id = csm_id
        run.task_status = task_stat
        history.append({
            "node_id": run.current_node_id,
            "type": "human_task",
            "task_name": current_node.get("task_name", "CSM Review"),
            "assigned_csm_id": str(csm_id) if csm_id else None,
            "task_status": task_stat,
            "created_at": now.isoformat()
        })
        out_edges = [e for e in edges if e["source"] == run.current_node_id]
        if out_edges:
            next_node_id = out_edges[0]["target"]

    # Crash-Safe State Update
    state["history"] = history
    run.state_data = state
    run.updated_at = now

    if next_node_id and next_node_id in nodes:
        run.current_node_id = next_node_id
    else:
        run.status = "completed"
        run.completed_at = now

    await db.commit()
    return run

async def process_active_playbook_runs(db: AsyncSession, tenant_id: uuid.UUID):
    import sqlalchemy
    await db.execute(sqlalchemy.text(f"SET LOCAL app.current_tenant = '{tenant_id}'"))

    res = await db.execute(
        select(PlaybookRun.id).where(
            and_(
                PlaybookRun.tenant_id == tenant_id,
                PlaybookRun.status == "running"
            )
        )
    )
    run_ids = res.scalars().all()
    for rid in run_ids:
        await advance_playbook_run(db, rid)
