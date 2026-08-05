import math
import uuid
from datetime import UTC, datetime, timedelta

import pytest
import pytest_asyncio
import sqlalchemy
from apps.api.core.analytics.outcomes import track_intervention_outcomes
from apps.api.core.analytics.roi import calculate_roi
from apps.api.core.security import create_access_token
from apps.api.models import (
    Campaign,
    Customer,
    CustomerEvent,
    Intervention,
    InterventionOutcome,
    PlanTier,
    Role,
    Tenant,
    User,
)
from apps.api.routers.analytics import wilson_score_interval
from sqlalchemy.ext.asyncio import AsyncSession

pytestmark = pytest.mark.asyncio

@pytest_asyncio.fixture()
async def test_tenant(db_session: AsyncSession):
    tenant = Tenant(id=uuid.uuid4(), name="Analytics Tenant", subdomain="analytics-test", plan_tier=PlanTier.tier1)
    db_session.add(tenant)
    await db_session.commit()
    await db_session.refresh(tenant)
    await db_session.execute(sqlalchemy.text(f"SET LOCAL app.current_tenant = '{tenant.id}'"))
    return tenant

@pytest_asyncio.fixture()
async def user_headers(test_tenant, db_session: AsyncSession):
    user_id = uuid.uuid4()
    user = User(
        id=user_id,
        tenant_id=test_tenant.id,
        email="analytics@test.com",
        hashed_password="fake",
        role=Role.owner
    )
    db_session.add(user)
    await db_session.commit()
    token = create_access_token(str(user_id), Role.owner.value, str(test_tenant.id))
    return {"Authorization": f"Bearer {token}"}


async def test_wilson_score_interval():
    # Test cases: 0 successes, 0 failures; some successes; all successes
    lower, upper = wilson_score_interval(0, 0)
    assert lower == 0.0
    assert upper == 0.0
    
    lower, upper = wilson_score_interval(10, 100)
    assert 0.04 < lower < 0.17 # 95% CI for 10% is ~ 0.05 to 0.17
    assert 0.16 < upper < 0.18
    
    lower, upper = wilson_score_interval(100, 100)
    assert lower > 0.95
    assert math.isclose(upper, 1.0)

async def test_track_intervention_outcomes(client, db_session, test_tenant, user_headers):
    # Setup Data
    tenant_id = test_tenant.id
    customer_id = uuid.uuid4()
    c = Customer(id=customer_id, tenant_id=tenant_id, external_ids={"stripe": "c1"})
    
    campaign_id = uuid.uuid4()
    camp = Campaign(id=campaign_id, tenant_id=tenant_id, name="Test Campaign", intervention_type="discount", channel="email")
    
    # Intervention sent 35 days ago
    sent_at = datetime.now(UTC) - timedelta(days=35)
    i1 = Intervention(id=uuid.uuid4(), tenant_id=tenant_id, customer_id=customer_id, campaign_id=campaign_id, channel="email", status="sent", sent_at=sent_at, outcome=InterventionOutcome.pending)
    
    db_session.add_all([c, camp, i1])
    await db_session.commit()
    
    # Run outcome tracking. Since no events exist, they should be marked retained.
    await track_intervention_outcomes(db_session, str(tenant_id), evaluation_days=30)
    
    await db_session.refresh(i1)
    assert i1.outcome == InterventionOutcome.retained
    assert i1.outcome_recorded_at is not None

    # Intervention 2, with a churn event
    i2 = Intervention(id=uuid.uuid4(), tenant_id=tenant_id, customer_id=customer_id, campaign_id=campaign_id, channel="email", status="sent", sent_at=sent_at, outcome=InterventionOutcome.pending)
    e1 = CustomerEvent(id=uuid.uuid4(), tenant_id=tenant_id, customer_id=customer_id, source="stripe", external_event_id="e1", event_type="subscription_canceled", occurred_at=sent_at + timedelta(days=10))
    
    db_session.add_all([i2, e1])
    await db_session.commit()
    
    await track_intervention_outcomes(db_session, str(tenant_id), evaluation_days=30)
    await db_session.refresh(i2)
    assert i2.outcome == InterventionOutcome.churned

async def test_calculate_roi(client, db_session, test_tenant, user_headers):
    tenant_id = test_tenant.id
    customer_id = uuid.uuid4()
    c = Customer(id=customer_id, tenant_id=tenant_id, external_ids={"stripe": "c2"}, mrr=100.0, churn_risk_tier="high")
    
    campaign_id = uuid.uuid4()
    camp = Campaign(id=campaign_id, tenant_id=tenant_id, name="Test Campaign", intervention_type="discount", channel="email")
    
    now = datetime.now(UTC)
    # Reatined high-risk customer
    i1 = Intervention(id=uuid.uuid4(), tenant_id=tenant_id, customer_id=customer_id, campaign_id=campaign_id, channel="email", status="sent", sent_at=now, outcome=InterventionOutcome.retained, outcome_recorded_at=now)
    
    db_session.add_all([c, camp, i1])
    await db_session.commit()
    
    start_date = now - timedelta(days=7)
    report = await calculate_roi(db_session, str(tenant_id), start_date, now + timedelta(days=1))
    
    assert report.tenant_id == tenant_id
    assert report.churn_events_prevented == 0.5 # 1 customer * 0.5
    assert report.revenue_saved == 50.0 # 100 * 0.5
    assert report.methodology.startswith("Simple Estimate")
    # For tier1, cost is 100, so roi is 50/100 = 0.5
    assert report.roi_multiple == 0.5

async def test_analytics_endpoints(client, db_session, test_tenant, user_headers):
    # Need some data for endpoints
    # Use data from previous test implicitly, or recreate
    tenant_id = test_tenant.id
    customer_id = uuid.uuid4()
    c = Customer(id=customer_id, tenant_id=tenant_id, external_ids={"stripe": "c3"}, mrr=100.0, churn_risk_tier="high")
    camp = Campaign(id=uuid.uuid4(), tenant_id=tenant_id, name="Camp3", intervention_type="discount", channel="email", variant_group_id="A")
    i1 = Intervention(id=uuid.uuid4(), tenant_id=tenant_id, customer_id=customer_id, campaign_id=camp.id, channel="email", status="sent", sent_at=datetime.now(UTC), outcome=InterventionOutcome.retained, outcome_recorded_at=datetime.now(UTC))
    
    db_session.add_all([c, camp, i1])
    await db_session.commit()
    
    # Run ROI generation to ensure a report exists
    now = datetime.now(UTC)
    await calculate_roi(db_session, str(tenant_id), now - timedelta(days=7), now + timedelta(days=1))
    
    # Test Performance Endpoint
    response = await client.get("/analytics/intervention-performance", headers=user_headers)
    assert response.status_code == 200
    data = response.json()
    assert "performance" in data
    assert len(data["performance"]) > 0
    
    # Test ROI Report Endpoint
    response = await client.get("/analytics/roi-report", headers=user_headers)
    assert response.status_code == 200
    data = response.json()
    assert "revenue_saved" in data
    assert data["revenue_saved"] > 0
