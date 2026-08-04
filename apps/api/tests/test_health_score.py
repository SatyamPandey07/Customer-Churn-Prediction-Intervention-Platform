import pytest
import uuid
import sqlalchemy
from datetime import datetime, timezone
from apps.api.models import Tenant, User, Customer, HealthScoreConfig, HealthScore, Role, PlanTier
from apps.api.core.ml.health import compute_health_score
from apps.api.core.security import create_access_token

def test_health_score_weighting_math():
    feature_dict = {
        "usage_trend_slope": 0.5,
        "payment_failures_90d": 0,
        "days_since_last_event": 5
    }
    weights = {
        "churn_weight": 0.35,
        "usage_trend_weight": 0.25,
        "payment_health_weight": 0.20,
        "support_sentiment_weight": 0.0,
        "engagement_recency_weight": 0.20
    }
    churn_prob = 0.10

    score, breakdown = compute_health_score(churn_prob, feature_dict, weights)

    assert 85.0 <= score <= 90.0
    assert "churn" in breakdown
    assert breakdown["churn"]["weighted_contribution"] == 31.5

@pytest.mark.asyncio
async def test_health_score_config_endpoints(client, db_session):
    tenant_id = uuid.uuid4()
    tenant = Tenant(id=tenant_id, name="Health Config Test", subdomain="health-config", plan_tier=PlanTier.tier1)
    db_session.add(tenant)

    user_id = uuid.uuid4()
    user = User(
        id=user_id,
        tenant_id=tenant_id,
        email="admin@healthconfig.com",
        role=Role.owner
    )
    db_session.add(user)
    await db_session.commit()

    token = create_access_token(user.email, role=user.role.value, tenant_id=str(tenant_id))
    headers = {"Authorization": f"Bearer {token}"}

    # 1. Test GET default config
    res_get = await client.get(f"/tenants/{tenant_id}/health-score-config", headers=headers)
    assert res_get.status_code == 200
    data = res_get.json()
    assert data["churn_weight"] == 0.35

    # 2. Test PUT with invalid weights (sum != 1.0) -> 400
    res_bad = await client.put(f"/tenants/{tenant_id}/health-score-config", json={
        "churn_weight": 0.40,
        "usage_trend_weight": 0.20,
        "payment_health_weight": 0.10,
        "support_sentiment_weight": 0.0,
        "engagement_recency_weight": 0.10
    }, headers=headers)
    assert res_bad.status_code == 400
    assert "must sum to 1.0" in res_bad.json()["detail"]

    # 3. Test PUT with valid weights (sum == 1.0) -> 200
    res_valid = await client.put(f"/tenants/{tenant_id}/health-score-config", json={
        "churn_weight": 0.40,
        "usage_trend_weight": 0.20,
        "payment_health_weight": 0.20,
        "support_sentiment_weight": 0.0,
        "engagement_recency_weight": 0.20
    }, headers=headers)
    assert res_valid.status_code == 200
    assert res_valid.json()["churn_weight"] == 0.40

    # 4. Tenant isolation check: request for another tenant_id -> 403 Forbidden
    other_tenant_id = uuid.uuid4()
    res_forbidden = await client.get(f"/tenants/{other_tenant_id}/health-score-config", headers=headers)
    assert res_forbidden.status_code == 403

@pytest.mark.asyncio
async def test_customer_health_score_endpoint(client, db_session):
    tenant_id = uuid.uuid4()
    tenant = Tenant(id=tenant_id, name="Health Customer Test", subdomain="health-cust", plan_tier=PlanTier.tier1)
    db_session.add(tenant)

    user_id = uuid.uuid4()
    user = User(id=user_id, tenant_id=tenant_id, email="admin@healthcust.com", role=Role.owner)
    db_session.add(user)
    await db_session.commit()

    token = create_access_token(user.email, role=user.role.value, tenant_id=str(tenant_id))
    headers = {"Authorization": f"Bearer {token}"}

    # Add customer for this tenant
    c_id = uuid.uuid4()
    await db_session.execute(sqlalchemy.text(f"SET LOCAL app.current_tenant = '{tenant_id}'"))
    customer = Customer(
        id=c_id,
        tenant_id=tenant_id,
        external_ids={"stripe": "cus_health_1"},
        plan="premium",
        mrr=150.0,
        churn_probability=0.15
    )
    db_session.add(customer)
    await db_session.commit()

    # Query GET health score
    res = await client.get(f"/tenants/{tenant_id}/customers/{c_id}/health-score", headers=headers)
    assert res.status_code == 200
    data = res.json()
    assert 0.0 <= data["health_score"] <= 100.0
    assert "breakdown" in data
    assert "churn" in data["breakdown"]
