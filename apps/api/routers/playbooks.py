import uuid
from typing import List, Optional, Dict, Any
from datetime import datetime, timezone
from pydantic import BaseModel, Field
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession

from apps.api.core.deps import get_db, get_current_user, require_role
from apps.api.models import PlaybookDefinition, PlaybookRun, CsmProfile, AuditLog, Role, User, Customer
from apps.api.core.playbooks.engine import advance_playbook_run

router = APIRouter(prefix="/tenants", tags=["playbooks"])

def check_tenant_access(user: dict, tenant_id: uuid.UUID):
    user_tenant_id = uuid.UUID(str(user["tenant_id"]))
    if user_tenant_id != tenant_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized for this tenant")

class CreatePlaybookPayload(BaseModel):
    name: str
    description: Optional[str] = None
    graph: Dict[str, Any]  # {"nodes": [...], "edges": [...]}
    status: str = "active"

class CreateCsmProfilePayload(BaseModel):
    user_id: uuid.UUID
    max_active_accounts: int = Field(20, ge=1)
    specialty_tags: List[str] = []
    is_available: bool = True

class ReassignCsmPayload(BaseModel):
    csm_user_id: uuid.UUID

@router.post("/{tenant_id}/playbooks")
async def create_playbook_definition(
    tenant_id: uuid.UUID,
    payload: CreatePlaybookPayload,
    db: AsyncSession = Depends(get_db),
    user: dict = Depends(require_role([Role.owner, Role.admin, Role.analyst]))
):
    check_tenant_access(user, tenant_id)
    user_id = uuid.UUID(str(user["sub"])) if "sub" in user and user["sub"] else None

    playbook = PlaybookDefinition(
        id=uuid.uuid4(),
        tenant_id=tenant_id,
        name=payload.name,
        description=payload.description,
        graph=payload.graph,
        status=payload.status,
        created_by_user_id=user_id,
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc)
    )
    db.add(playbook)
    await db.commit()

    return {
        "id": str(playbook.id),
        "name": playbook.name,
        "status": playbook.status,
        "graph": playbook.graph
    }

@router.get("/{tenant_id}/playbooks")
async def list_playbook_definitions(
    tenant_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    user: dict = Depends(get_current_user)
):
    check_tenant_access(user, tenant_id)
    res = await db.execute(
        select(PlaybookDefinition).where(PlaybookDefinition.tenant_id == tenant_id).order_by(PlaybookDefinition.created_at.desc())
    )
    playbooks = res.scalars().all()
    return [
        {
            "id": str(p.id),
            "name": p.name,
            "description": p.description,
            "status": p.status,
            "graph": p.graph,
            "created_at": p.created_at.isoformat() if hasattr(p.created_at, "isoformat") else str(p.created_at)
        }
        for p in playbooks
    ]

@router.get("/{tenant_id}/playbooks/{playbook_id}")
async def get_playbook_definition(
    tenant_id: uuid.UUID,
    playbook_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    user: dict = Depends(get_current_user)
):
    check_tenant_access(user, tenant_id)
    res = await db.execute(
        select(PlaybookDefinition).where(
            and_(PlaybookDefinition.tenant_id == tenant_id, PlaybookDefinition.id == playbook_id)
        )
    )
    pb = res.scalars().first()
    if not pb:
        raise HTTPException(status_code=404, detail="Playbook definition not found")

    return {
        "id": str(pb.id),
        "name": pb.name,
        "description": pb.description,
        "status": pb.status,
        "graph": pb.graph,
        "created_at": pb.created_at.isoformat() if hasattr(pb.created_at, "isoformat") else str(pb.created_at)
    }

@router.post("/{tenant_id}/playbooks/{playbook_id}/trigger")
async def trigger_playbook_run(
    tenant_id: uuid.UUID,
    playbook_id: uuid.UUID,
    customer_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    user: dict = Depends(get_current_user)
):
    check_tenant_access(user, tenant_id)
    res_pb = await db.execute(
        select(PlaybookDefinition).where(
            and_(PlaybookDefinition.tenant_id == tenant_id, PlaybookDefinition.id == playbook_id)
        )
    )
    pb = res_pb.scalars().first()
    if not pb or not pb.graph or not pb.graph.get("nodes"):
        raise HTTPException(status_code=400, detail="Invalid or empty playbook definition graph")

    start_node_id = pb.graph["nodes"][0]["id"]
    now = datetime.now(timezone.utc)

    run = PlaybookRun(
        id=uuid.uuid4(),
        tenant_id=tenant_id,
        playbook_id=playbook_id,
        customer_id=customer_id,
        current_node_id=start_node_id,
        status="running",
        state_data={"vars": {}, "history": []},
        started_at=now,
        updated_at=now
    )
    db.add(run)
    await db.commit()

    # Advance first step
    await advance_playbook_run(db, run.id)

    return {
        "run_id": str(run.id),
        "playbook_id": str(playbook_id),
        "customer_id": str(customer_id),
        "current_node_id": run.current_node_id,
        "status": run.status
    }

@router.get("/{tenant_id}/customers/{customer_id}/playbook-runs")
async def get_customer_playbook_runs(
    tenant_id: uuid.UUID,
    customer_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    user: dict = Depends(get_current_user)
):
    check_tenant_access(user, tenant_id)
    res = await db.execute(
        select(PlaybookRun).where(
            and_(PlaybookRun.tenant_id == tenant_id, PlaybookRun.customer_id == customer_id)
        ).order_by(PlaybookRun.started_at.desc())
    )
    runs = res.scalars().all()
    return [
        {
            "id": str(r.id),
            "playbook_id": str(r.playbook_id),
            "customer_id": str(r.customer_id),
            "current_node_id": r.current_node_id,
            "status": r.status,
            "state_data": r.state_data,
            "assigned_csm_id": str(r.assigned_csm_id) if r.assigned_csm_id else None,
            "task_status": r.task_status,
            "started_at": r.started_at.isoformat() if hasattr(r.started_at, "isoformat") else str(r.started_at),
            "completed_at": r.completed_at.isoformat() if r.completed_at and hasattr(r.completed_at, "isoformat") else None
        }
        for r in runs
    ]

@router.get("/{tenant_id}/csm-profiles")
async def list_csm_profiles(
    tenant_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    user: dict = Depends(get_current_user)
):
    check_tenant_access(user, tenant_id)
    res = await db.execute(select(CsmProfile).where(CsmProfile.tenant_id == tenant_id))
    profiles = res.scalars().all()
    return [
        {
            "id": str(p.id),
            "user_id": str(p.user_id),
            "max_active_accounts": p.max_active_accounts,
            "current_active_count": p.current_active_count,
            "specialty_tags": p.specialty_tags,
            "is_available": p.is_available
        }
        for p in profiles
    ]

@router.post("/{tenant_id}/csm-profiles")
async def create_or_update_csm_profile(
    tenant_id: uuid.UUID,
    payload: CreateCsmProfilePayload,
    db: AsyncSession = Depends(get_db),
    user: dict = Depends(require_role([Role.owner, Role.admin]))
):
    check_tenant_access(user, tenant_id)
    res = await db.execute(
        select(CsmProfile).where(
            and_(CsmProfile.tenant_id == tenant_id, CsmProfile.user_id == payload.user_id)
        )
    )
    profile = res.scalars().first()
    if not profile:
        profile = CsmProfile(
            id=uuid.uuid4(),
            tenant_id=tenant_id,
            user_id=payload.user_id,
            max_active_accounts=payload.max_active_accounts,
            current_active_count=0,
            specialty_tags=payload.specialty_tags,
            is_available=payload.is_available
        )
        db.add(profile)
    else:
        profile.max_active_accounts = payload.max_active_accounts
        profile.specialty_tags = payload.specialty_tags
        profile.is_available = payload.is_available

    await db.commit()
    return {"status": "saved", "id": str(profile.id), "user_id": str(profile.user_id)}

@router.get("/{tenant_id}/csm-tasks/overflow")
async def get_overflow_tasks(
    tenant_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    user: dict = Depends(get_current_user)
):
    check_tenant_access(user, tenant_id)
    res = await db.execute(
        select(PlaybookRun).where(
            and_(
                PlaybookRun.tenant_id == tenant_id,
                PlaybookRun.task_status == "unassigned_overflow"
            )
        )
    )
    runs = res.scalars().all()
    return [
        {
            "run_id": str(r.id),
            "playbook_id": str(r.playbook_id),
            "customer_id": str(r.customer_id),
            "current_node_id": r.current_node_id,
            "task_status": r.task_status,
            "started_at": r.started_at.isoformat() if hasattr(r.started_at, "isoformat") else str(r.started_at)
        }
        for r in runs
    ]

@router.post("/{tenant_id}/playbook-runs/{run_id}/reassign")
async def reassign_playbook_task(
    tenant_id: uuid.UUID,
    run_id: uuid.UUID,
    payload: ReassignCsmPayload,
    db: AsyncSession = Depends(get_db),
    user: dict = Depends(require_role([Role.owner, Role.admin]))
):
    check_tenant_access(user, tenant_id)
    res_run = await db.execute(
        select(PlaybookRun).where(
            and_(PlaybookRun.tenant_id == tenant_id, PlaybookRun.id == run_id)
        )
    )
    run = res_run.scalars().first()
    if not run:
        raise HTTPException(status_code=404, detail="Playbook run not found")

    old_csm_id = run.assigned_csm_id
    run.assigned_csm_id = payload.csm_user_id
    run.task_status = "assigned"
    run.updated_at = datetime.now(timezone.utc)

    # Write AuditLog
    actor_id_raw = user.get("user_id") or user.get("sub")
    actor_id = None
    if actor_id_raw:
        try:
            actor_id = uuid.UUID(str(actor_id_raw))
        except ValueError:
            res_u = await db.execute(select(User).where(User.email == str(actor_id_raw)))
            u_obj = res_u.scalars().first()
            if u_obj:
                actor_id = u_obj.id

    audit = AuditLog(
        id=uuid.uuid4(),
        tenant_id=tenant_id,
        actor_user_id=actor_id,
        action="playbook_reassign_csm",
        resource=f"playbook_run:{run_id}",
        timestamp=datetime.now(timezone.utc)
    )
    db.add(audit)
    await db.commit()


    return {
        "status": "reassigned",
        "run_id": str(run_id),
        "old_assigned_csm_id": str(old_csm_id) if old_csm_id else None,
        "new_assigned_csm_id": str(payload.csm_user_id)
    }
