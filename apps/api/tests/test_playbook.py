import pytest
import uuid
import sqlalchemy
from datetime import datetime, timezone, timedelta
from unittest.mock import AsyncMock, patch

from apps.api.models import Tenant, User, Customer, PlaybookDefinition, PlaybookRun, CsmProfile, AuditLog, Role, PlanTier
from apps.api.core.security import create_access_token
from apps.api.core.playbooks.engine import advance_playbook_run, assign_csm_for_human_task

@pytest.mark.asyncio
async def test_multi_step_branching_playbook_execution(db_session):
    tenant_id = uuid.uuid4()
    tenant = Tenant(id=tenant_id, name="Playbook Test", subdomain="pb-test", plan_tier=PlanTier.tier1, is_active=True)
    db_session.add(tenant)
    await db_session.commit()

    await db_session.execute(sqlalchemy.text(f"SET LOCAL app.current_tenant = '{tenant_id}'"))
    c = Customer(id=uuid.uuid4(), tenant_id=tenant_id, plan="standard", mrr=500.0)
    db_session.add(c)
    await db_session.commit()

    graph = {
        "nodes": [
            {"id": "n1", "type": "action", "channel": "email", "template": "Welcome!"},
            {
                "id": "n2",
                "type": "condition",
                "condition_type": "var_check",
                "var_name": "is_vip",
                "expected_value": True,
                "true_target": "n3_vip",
                "false_target": "n3_std"
            },
            {"id": "n3_vip", "type": "action", "channel": "slack", "template": "VIP Alert"},
            {"id": "n3_std", "type": "action", "channel": "email", "template": "Standard Followup"}
        ],
        "edges": [
            {"source": "n1", "target": "n2"}
        ]
    }

    pb = PlaybookDefinition(
        id=uuid.uuid4(), tenant_id=tenant_id, name="Branching Playbook", graph=graph, status="active"
    )
    db_session.add(pb)
    await db_session.commit()

    # Case A: True branch (is_vip = True)
    now = datetime.now(timezone.utc)
    run_true = PlaybookRun(
        id=uuid.uuid4(), tenant_id=tenant_id, playbook_id=pb.id, customer_id=c.id,
        current_node_id="n1", status="running", state_data={"vars": {"is_vip": True}, "history": []},
        started_at=now, updated_at=now
    )
    db_session.add(run_true)
    await db_session.commit()

    mock_adapter = AsyncMock()
    mock_adapter.send.return_value = True

    with patch("apps.api.core.playbooks.engine.get_adapter", return_value=mock_adapter):
        # Step 1: n1 (action) -> advances to n2
        r1 = await advance_playbook_run(db_session, run_true.id)
        assert r1.current_node_id == "n2"

        # Step 2: n2 (condition is_vip==True) -> advances to n3_vip
        r2 = await advance_playbook_run(db_session, run_true.id)
        assert r2.current_node_id == "n3_vip"

    # Case B: False branch (is_vip = False)
    run_false = PlaybookRun(
        id=uuid.uuid4(), tenant_id=tenant_id, playbook_id=pb.id, customer_id=c.id,
        current_node_id="n1", status="running", state_data={"vars": {"is_vip": False}, "history": []},
        started_at=now, updated_at=now
    )
    db_session.add(run_false)
    await db_session.commit()

    with patch("apps.api.core.playbooks.engine.get_adapter", return_value=mock_adapter):
        await advance_playbook_run(db_session, run_false.id)  # n1 -> n2
        r_false = await advance_playbook_run(db_session, run_false.id)  # n2 -> n3_std
        assert r_false.current_node_id == "n3_std"

@pytest.mark.asyncio
async def test_crash_safety_resumable_execution(db_session):
    tenant_id = uuid.uuid4()
    tenant = Tenant(id=tenant_id, name="Crash Safety Test", subdomain="crash-test", plan_tier=PlanTier.tier1, is_active=True)
    db_session.add(tenant)
    await db_session.commit()

    await db_session.execute(sqlalchemy.text(f"SET LOCAL app.current_tenant = '{tenant_id}'"))
    c = Customer(id=uuid.uuid4(), tenant_id=tenant_id, plan="premium", mrr=1000.0)
    db_session.add(c)

    graph = {
        "nodes": [
            {"id": "step1", "type": "action", "channel": "email", "template": "Step 1"},
            {"id": "step2", "type": "action", "channel": "slack", "template": "Step 2"},
            {"id": "step3", "type": "action", "channel": "email", "template": "Step 3"}
        ],
        "edges": [
            {"source": "step1", "target": "step2"},
            {"source": "step2", "target": "step3"}
        ]
    }
    pb = PlaybookDefinition(id=uuid.uuid4(), tenant_id=tenant_id, name="Crash Playbook", graph=graph, status="active")
    db_session.add(pb)
    await db_session.commit()

    now = datetime.now(timezone.utc)
    run = PlaybookRun(
        id=uuid.uuid4(), tenant_id=tenant_id, playbook_id=pb.id, customer_id=c.id,
        current_node_id="step1", status="running", state_data={"vars": {}, "history": []},
        started_at=now, updated_at=now
    )
    db_session.add(run)
    await db_session.commit()

    mock_adapter = AsyncMock()
    mock_adapter.send.return_value = True

    with patch("apps.api.core.playbooks.engine.get_adapter", return_value=mock_adapter):
        # Advance step 1 -> persisted state moves to step2
        await advance_playbook_run(db_session, run.id)

    # SIMULATE WORKER CRASH / RESTART: Query run fresh from DB
    await db_session.execute(sqlalchemy.text(f"SET LOCAL app.current_tenant = '{tenant_id}'"))
    res_fresh = await db_session.execute(sqlalchemy.select(PlaybookRun).where(PlaybookRun.id == run.id))
    restarted_run = res_fresh.scalars().first()

    assert restarted_run.current_node_id == "step2"
    assert len(restarted_run.state_data["history"]) == 1

    with patch("apps.api.core.playbooks.engine.get_adapter", return_value=mock_adapter):
        # Resume execution from step 2 -> advances to step 3
        resumed = await advance_playbook_run(db_session, restarted_run.id)
        assert resumed.current_node_id == "step3"
        assert len(resumed.state_data["history"]) == 2

@pytest.mark.asyncio
async def test_csm_auto_routing_and_overflow_queueing(db_session):
    tenant_id = uuid.uuid4()
    tenant = Tenant(id=tenant_id, name="CSM Routing Test", subdomain="csm-route", plan_tier=PlanTier.tier1, is_active=True)
    db_session.add(tenant)

    user1 = User(id=uuid.uuid4(), tenant_id=tenant_id, email="csm1@test.com", role=Role.analyst)
    db_session.add(user1)
    await db_session.commit()

    await db_session.execute(sqlalchemy.text(f"SET LOCAL app.current_tenant = '{tenant_id}'"))

    # CSM 1 profile: max_active_accounts = 1, current_active_count = 0, specialty = "fintech"
    profile = CsmProfile(
        id=uuid.uuid4(), tenant_id=tenant_id, user_id=user1.id,
        max_active_accounts=1, current_active_count=0, specialty_tags=["fintech"], is_available=True
    )
    db_session.add(profile)
    await db_session.commit()

    await db_session.execute(sqlalchemy.text(f"SET LOCAL app.current_tenant = '{tenant_id}'"))

    node_fintech = {"id": "h1", "type": "human_task", "task_name": "Review Account", "specialty_tag": "fintech"}

    # Task 1: CSM is available -> assigned
    csm_id1, status1 = await assign_csm_for_human_task(db_session, tenant_id, node_fintech)
    assert csm_id1 == user1.id
    assert status1 == "assigned"

    # Task 2: CSM current_active_count is now 1 (at capacity max=1) -> queued as unassigned_overflow
    csm_id2, status2 = await assign_csm_for_human_task(db_session, tenant_id, node_fintech)
    assert csm_id2 is None
    assert status2 == "unassigned_overflow"

@pytest.mark.asyncio
async def test_manual_reassignment_and_audit_logging(client, db_session):
    tenant_id = uuid.uuid4()
    tenant = Tenant(id=tenant_id, name="Reassign Test", subdomain="reassign-test", plan_tier=PlanTier.tier1, is_active=True)
    db_session.add(tenant)

    manager = User(id=uuid.uuid4(), tenant_id=tenant_id, email="manager@test.com", role=Role.admin)
    csm_target = User(id=uuid.uuid4(), tenant_id=tenant_id, email="target_csm@test.com", role=Role.analyst)
    db_session.add_all([manager, csm_target])
    await db_session.commit()

    token = create_access_token(str(manager.id), role=manager.role.value, tenant_id=str(tenant_id))
    headers = {"Authorization": f"Bearer {token}"}

    await db_session.execute(sqlalchemy.text(f"SET LOCAL app.current_tenant = '{tenant_id}'"))
    c = Customer(id=uuid.uuid4(), tenant_id=tenant_id, plan="enterprise", mrr=5000.0)
    db_session.add(c)
    pb = PlaybookDefinition(id=uuid.uuid4(), tenant_id=tenant_id, name="Test PB", graph={"nodes": [{"id": "h1", "type": "human_task"}]}, status="active")
    db_session.add(pb)
    await db_session.flush()

    run = PlaybookRun(
        id=uuid.uuid4(), tenant_id=tenant_id, playbook_id=pb.id, customer_id=c.id,
        current_node_id="h1", status="running", state_data={}, assigned_csm_id=None, task_status="unassigned_overflow"
    )
    db_session.add(run)
    await db_session.commit()

    # Manager calls reassignment endpoint
    res = await client.post(
        f"/tenants/{tenant_id}/playbook-runs/{run.id}/reassign",
        json={"csm_user_id": str(csm_target.id)},
        headers=headers
    )
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "reassigned"
    assert data["new_assigned_csm_id"] == str(csm_target.id)

    # Verify AuditLog entry written
    await db_session.execute(sqlalchemy.text(f"SET LOCAL app.current_tenant = '{tenant_id}'"))
    res_audit = await db_session.execute(
        sqlalchemy.select(AuditLog).where(AuditLog.tenant_id == tenant_id, AuditLog.action == "playbook_reassign_csm")
    )
    audits = res_audit.scalars().all()
    assert len(audits) == 1
    assert str(audits[0].actor_user_id) == str(manager.id)
