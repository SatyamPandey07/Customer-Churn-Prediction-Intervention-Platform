import pytest
import uuid
import sqlalchemy
from datetime import datetime, timezone, timedelta
from unittest.mock import AsyncMock, patch

from apps.api.models import Tenant, User, Customer, Role, PlanTier, RevenueAtRiskSnapshot, RevenueAtRiskAlertConfig
from apps.api.core.security import create_access_token
from apps.api.core.analytics.revenue_at_risk import (
    compute_revenue_at_risk_metrics,
    calculate_tenant_revenue_at_risk,
    evaluate_revenue_at_risk_alert
)
from apps.api.worker import snapshot_revenue_at_risk

def test_expected_value_math_and_confidence_band():
    now = datetime.now(timezone.utc)
    c1 = Customer(id=uuid.uuid4(), mrr=100.0, churn_probability=0.20, plan="standard", created_at=now)
    c2 = Customer(id=uuid.uuid4(), mrr=500.0, churn_probability=0.50, plan="premium", created_at=now)

    # 30-day horizon
    metrics_30 = compute_revenue_at_risk_metrics([c1, c2], horizon_days=30)
    assert metrics_30["total_expected_loss"] == 270.0  # 20.0 + 250.0
    assert metrics_30["confidence_band"]["lower_95"] <= metrics_30["total_expected_loss"] <= metrics_30["confidence_band"]["upper_95"]
    assert "methodology" in metrics_30

    # 90-day horizon (scale = 3.0)
    metrics_90 = compute_revenue_at_risk_metrics([c1, c2], horizon_days=90)
    assert metrics_90["total_expected_loss"] == 810.0  # 270.0 * 3

def test_segmentation_by_plan_and_cohort():
    jan_date = datetime(2026, 1, 15, tzinfo=timezone.utc)
    feb_date = datetime(2026, 2, 20, tzinfo=timezone.utc)

    c1 = Customer(id=uuid.uuid4(), mrr=200.0, churn_probability=0.10, plan="basic", created_at=jan_date)
    c2 = Customer(id=uuid.uuid4(), mrr=300.0, churn_probability=0.40, plan="premium", created_at=jan_date)
    c3 = Customer(id=uuid.uuid4(), mrr=400.0, churn_probability=0.50, plan="premium", created_at=feb_date)

    metrics = compute_revenue_at_risk_metrics([c1, c2, c3], horizon_days=30)
    by_plan = {item["segment_name"]: item for item in metrics["by_segment"]["by_plan"]}
    by_cohort = {item["segment_name"]: item for item in metrics["by_segment"]["by_cohort"]}

    # Premium: (300*0.4) + (400*0.5) = 120 + 200 = 320
    assert "premium" in by_plan
    assert by_plan["premium"]["customer_count"] == 2
    assert by_plan["premium"]["expected_revenue_at_risk"] == 320.0

    # 2026-01 Cohort: (200*0.1) + (300*0.4) = 20 + 120 = 140
    assert "2026-01" in by_cohort
    assert by_cohort["2026-01"]["customer_count"] == 2
    assert by_cohort["2026-01"]["expected_revenue_at_risk"] == 140.0

@pytest.mark.asyncio
async def test_revenue_at_risk_endpoint(client, db_session):
    tenant_id = uuid.uuid4()
    tenant = Tenant(id=tenant_id, name="RAR API Test", subdomain="rar-api", plan_tier=PlanTier.tier1, is_active=True)
    db_session.add(tenant)
    await db_session.flush()

    user_id = uuid.uuid4()
    user = User(id=user_id, tenant_id=tenant_id, email="admin@rarapi.com", role=Role.owner)
    db_session.add(user)
    await db_session.commit()

    token = create_access_token(user.email, role=user.role.value, tenant_id=str(tenant_id))
    headers = {"Authorization": f"Bearer {token}"}

    # Add customer
    await db_session.execute(sqlalchemy.text(f"SET LOCAL app.current_tenant = '{tenant_id}'"))
    c = Customer(
        id=uuid.uuid4(), tenant_id=tenant_id, external_ids={"stripe": "cus_rar_1"},
        plan="premium", mrr=1000.0, churn_probability=0.25, created_at=datetime.now(timezone.utc)
    )
    db_session.add(c)
    await db_session.commit()

    res = await client.get(f"/tenants/{tenant_id}/analytics/revenue-at-risk?horizon_days=90", headers=headers)
    assert res.status_code == 200
    data = res.json()
    assert data["total_expected_loss"] == 750.0  # 1000 * 0.25 * 3
    assert len(data["top_10_accounts_by_dollar_exposure"]) == 1
    assert "methodology" in data

@pytest.mark.asyncio
async def test_snapshot_job_idempotency(db_session):
    tenant_id = uuid.uuid4()
    tenant = Tenant(id=tenant_id, name="Snapshot Idempotency", subdomain="snap-idem", plan_tier=PlanTier.tier1, is_active=True)
    db_session.add(tenant)
    await db_session.commit()

    await db_session.execute(sqlalchemy.text(f"SET LOCAL app.current_tenant = '{tenant_id}'"))
    c = Customer(
        id=uuid.uuid4(), tenant_id=tenant_id, external_ids={"stripe": "cus_snap_1"},
        plan="standard", mrr=500.0, churn_probability=0.30, created_at=datetime.now(timezone.utc)
    )
    db_session.add(c)
    await db_session.commit()

    # Run snapshot job twice
    ctx = {}
    await snapshot_revenue_at_risk(ctx)
    await snapshot_revenue_at_risk(ctx)

    await db_session.execute(sqlalchemy.text(f"SET LOCAL app.current_tenant = '{tenant_id}'"))
    res_snaps = await db_session.execute(
        sqlalchemy.select(RevenueAtRiskSnapshot).where(RevenueAtRiskSnapshot.tenant_id == tenant_id)
    )
    snapshots = res_snaps.scalars().all()

    # Assert exactly 1 snapshot row created for today
    assert len(snapshots) == 1
    assert snapshots[0].horizon_90d_expected_loss == 450.0

@pytest.mark.asyncio
async def test_threshold_crossing_alert(db_session):
    tenant_id = uuid.uuid4()
    tenant = Tenant(id=tenant_id, name="Alert Test", subdomain="alert-test", plan_tier=PlanTier.tier1, is_active=True)
    db_session.add(tenant)
    await db_session.flush()

    # Config: Threshold $200
    cfg = RevenueAtRiskAlertConfig(
        id=uuid.uuid4(),
        tenant_id=tenant_id,
        threshold_amount=200.0,
        channel="slack",
        enabled=True
    )
    db_session.add(cfg)

    c = Customer(
        id=uuid.uuid4(), tenant_id=tenant_id, external_ids={"slack": "C99999"},
        plan="premium", mrr=1000.0, churn_probability=0.30, created_at=datetime.now(timezone.utc)
    )
    db_session.add(c)
    await db_session.commit()

    await db_session.execute(sqlalchemy.text(f"SET LOCAL app.current_tenant = '{tenant_id}'"))

    # Mock outreach SlackAdapter send method
    mock_adapter = AsyncMock()
    mock_adapter.send.return_value = True

    with patch("apps.api.core.analytics.revenue_at_risk.get_adapter", return_value=mock_adapter):
        # Current 90d RAR is $900 (> $200 threshold)
        triggered = await evaluate_revenue_at_risk_alert(db_session, tenant_id, current_rar_90d=900.0)
        assert triggered is True
        mock_adapter.send.assert_called_once()
        assert "breaching threshold" in mock_adapter.send.call_args[0][2]
