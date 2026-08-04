import uuid
from datetime import UTC, datetime

import pytest
import sqlalchemy
from apps.api.models import Customer, HealthScore, PlanTier, Tenant
from apps.api.worker import batch_score_churn


@pytest.mark.asyncio
async def test_unified_batch_scoring_job(db_session):
    tenant_id = uuid.uuid4()
    tenant = Tenant(id=tenant_id, name="Unified Batch Test", subdomain="unified-batch", plan_tier=PlanTier.tier1)
    db_session.add(tenant)
    await db_session.commit()

    await db_session.execute(sqlalchemy.text(f"SET LOCAL app.current_tenant = '{tenant_id}'"))

    # Create synthetic customer
    c_id = uuid.uuid4()
    now = datetime.now(UTC)
    c = Customer(
        id=c_id,
        tenant_id=tenant_id,
        external_ids={"stripe": "cus_batch_1"},
        plan="standard",
        mrr=200.0,
        created_at=now,
        first_seen_at=now,
        last_seen_at=now
    )
    db_session.add(c)
    await db_session.commit()

    # Run unified batch scoring job
    ctx = {}
    await batch_score_churn(ctx)

    # Verify that churn_probability, expansion_probability, and health_score are populated on Customer
    await db_session.execute(sqlalchemy.text(f"SET LOCAL app.current_tenant = '{tenant_id}'"))
    res = await db_session.execute(sqlalchemy.select(Customer).where(Customer.id == c_id))
    customer = res.scalars().first()

    assert customer.churn_probability is not None
    assert customer.expansion_probability is not None
    assert customer.health_score is not None
    assert customer.churn_risk_tier in ["low", "medium", "high", "critical"]

    # Verify HealthScore history record created
    res_hs = await db_session.execute(sqlalchemy.select(HealthScore).where(HealthScore.customer_id == c_id))
    hs_record = res_hs.scalars().first()
    assert hs_record is not None
    assert hs_record.score == customer.health_score
    assert "churn" in hs_record.components
