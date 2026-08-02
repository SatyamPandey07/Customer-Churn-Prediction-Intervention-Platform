import pytest
import uuid
from datetime import datetime, timezone, timedelta
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
import sqlalchemy

from apps.api.models import Campaign, Intervention, Customer, CustomerEvent, Role, User, InAppNotification, Tenant, PlanTier
from apps.api.core.outreach.engine import evaluate_campaigns
from apps.api.core.outreach.adapters import get_adapter, EmailAdapter, SmsAdapter, SlackAdapter, InAppAdapter

import pytest_asyncio

@pytest_asyncio.fixture()
async def test_tenant(db_session: AsyncSession):
    tenant = Tenant(id=uuid.uuid4(), name="Test Tenant", subdomain="outreach-test", plan_tier=PlanTier.tier1)
    db_session.add(tenant)
    await db_session.commit()
    await db_session.refresh(tenant)
    # Enable RLS
    await db_session.execute(sqlalchemy.text(f"SET LOCAL app.current_tenant = '{tenant.id}'"))
    return tenant

from apps.api.core.security import create_access_token

@pytest_asyncio.fixture()
async def test_user_token(test_tenant, db_session: AsyncSession):
    user_id = uuid.uuid4()
    user = User(
        id=user_id,
        tenant_id=test_tenant.id,
        email="test@outreach.com",
        hashed_password="fake",
        role=Role.owner
    )
    db_session.add(user)
    await db_session.commit()
    return create_access_token(str(user_id), Role.owner.value, str(test_tenant.id))

@pytest_asyncio.fixture()
async def sample_campaign(db_session: AsyncSession, test_tenant):
    campaign = Campaign(
        id=uuid.uuid4(),
        tenant_id=test_tenant.id,
        name="High Risk Outreach",
        trigger_rule={"risk_tier": "critical", "mrr_gt": 100},
        intervention_type="cs_review",
        channel="email",
        template="Hi {customer_id}, {ai_copy}",
        status="active"
    )
    db_session.add(campaign)
    await db_session.commit()
    await db_session.refresh(campaign)
    return campaign

@pytest_asyncio.fixture()
async def sample_customer(db_session: AsyncSession, test_tenant):
    customer = Customer(
        id=uuid.uuid4(),
        tenant_id=test_tenant.id,
        external_ids={"stripe": "cus_test_123"},
        mrr=500.0,
        churn_risk_tier="critical"
    )
    db_session.add(customer)
    await db_session.commit()
    await db_session.refresh(customer)
    return customer

@pytest.mark.asyncio
async def test_campaign_crud_rbac(client: AsyncClient, test_user_token: str, db_session: AsyncSession):
    # Test Create (User is owner by default in fixtures)
    response = await client.post(
        "/campaigns",
        headers={"Authorization": f"Bearer {test_user_token}"},
        json={
            "name": "Test Campaign",
            "trigger_rule": {"risk_tier": "high"},
            "intervention_type": "discount",
            "channel": "in_app"
        }
    )
    assert response.status_code == 201
    data = response.json()
    assert data["name"] == "Test Campaign"
    campaign_id = data["id"]
    
    # Test Read
    response = await client.get(
        "/campaigns",
        headers={"Authorization": f"Bearer {test_user_token}"}
    )
    assert response.status_code == 200
    assert len(response.json()) > 0
    
    # Test Update
    response = await client.put(
        f"/campaigns/{campaign_id}",
        headers={"Authorization": f"Bearer {test_user_token}"},
        json={
            "name": "Updated Campaign",
            "trigger_rule": {"risk_tier": "high"},
            "intervention_type": "discount",
            "channel": "in_app",
            "status": "paused"
        }
    )
    assert response.status_code == 200
    assert response.json()["status"] == "paused"
    
    # Test Delete
    response = await client.delete(
        f"/campaigns/{campaign_id}",
        headers={"Authorization": f"Bearer {test_user_token}"}
    )
    assert response.status_code == 204

@pytest.mark.asyncio
async def test_rule_engine_matching_and_cooldown(db_session: AsyncSession, sample_campaign, sample_customer, test_tenant):
    # Run evaluation
    await evaluate_campaigns(db_session, test_tenant.id)
    
    # Check that intervention was created
    result = await db_session.execute(
        select(Intervention).where(Intervention.customer_id == sample_customer.id)
    )
    interventions = result.scalars().all()
    assert len(interventions) == 1
    assert interventions[0].campaign_id == sample_campaign.id
    assert interventions[0].status == "sent"
    
    # Run evaluation again immediately - should NOT create another one due to cooldown
    await evaluate_campaigns(db_session, test_tenant.id)
    result = await db_session.execute(
        select(Intervention).where(Intervention.customer_id == sample_customer.id)
    )
    assert len(result.scalars().all()) == 1
    
    # Modify intervention to be 15 days old
    old_intervention = interventions[0]
    old_intervention.sent_at = datetime.now(timezone.utc) - timedelta(days=15)
    await db_session.commit()
    
    # Run evaluation again - SHOULD create a new one
    await evaluate_campaigns(db_session, test_tenant.id)
    result = await db_session.execute(
        select(Intervention).where(Intervention.customer_id == sample_customer.id)
    )
    assert len(result.scalars().all()) == 2

@pytest.mark.asyncio
async def test_manual_override_endpoint(client: AsyncClient, test_user_token: str, sample_customer):
    response = await client.post(
        f"/customers/{sample_customer.id}/interventions/override",
        headers={"Authorization": f"Bearer {test_user_token}"},
        json={
            "channel": "slack",
            "message": "Hey checking in"
        }
    )
    assert response.status_code == 200
    data = response.json()
    assert data["manual_override"] is True
    assert data["channel"] == "slack"
    assert data["status"] == "sent"

@pytest.mark.asyncio
async def test_adapters(db_session: AsyncSession, sample_customer):
    email = get_adapter("email")
    assert isinstance(email, EmailAdapter)
    await email.send(db_session, sample_customer, "test")
    
    sms = get_adapter("sms")
    assert isinstance(sms, SmsAdapter)
    await sms.send(db_session, sample_customer, "test")
    
    slack = get_adapter("slack")
    assert isinstance(slack, SlackAdapter)
    await slack.send(db_session, sample_customer, "test")
    
    in_app = get_adapter("in_app")
    assert isinstance(in_app, InAppAdapter)
    await in_app.send(db_session, sample_customer, "test")
    
    result = await db_session.execute(
        select(InAppNotification).where(InAppNotification.customer_id == sample_customer.id)
    )
    assert len(result.scalars().all()) == 1
