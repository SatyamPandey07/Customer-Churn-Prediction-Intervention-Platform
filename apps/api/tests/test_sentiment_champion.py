import pytest
import uuid
import sqlalchemy
from datetime import datetime, timezone, timedelta
from unittest.mock import AsyncMock, patch

from apps.api.models import Tenant, User, Customer, AccountContact, AnomalyEvent, SupportSentimentScore, Role, PlanTier
from apps.api.core.security import create_access_token
from apps.api.core.ingestion.adapters import ZendeskAdapter, IntercomAdapter, NpsSurveyAdapter
from apps.api.core.analytics.sentiment import analyze_sentiment, process_and_store_sentiment, get_customer_average_sentiment
from apps.api.core.ml.health import compute_health_score
from apps.api.core.analytics.champion import evaluate_champion_status

def test_adapters_normalize_fixtures():
    # Zendesk
    zd = ZendeskAdapter()
    zd_payload = {
        "ticket_id": "1001",
        "customer_id": "cus_zd_1",
        "subject": "App crashing on login",
        "comment": "System crashed and unusable",
        "created_at": "2026-08-04T12:00:00Z"
    }
    zd_events = zd.normalize_payload(zd_payload)
    assert len(zd_events) == 1
    assert zd_events[0].source == "zendesk"
    assert zd_events[0].event_type == "support_ticket.created"

    # Intercom
    ic = IntercomAdapter()
    ic_payload = {
        "conversation_id": "c_200",
        "user_id": "cus_ic_1",
        "message": "Extremely frustrated with latency and slowness",
        "created_at": 1785830000
    }
    ic_events = ic.normalize_payload(ic_payload)
    assert len(ic_events) == 1
    assert ic_events[0].source == "intercom"

    # NPS Survey
    nps = NpsSurveyAdapter()
    nps_payload = {
        "survey_id": "nps_99",
        "customer_id": "cus_nps_1",
        "score": 2,
        "feedback": "Worst platform ever, horrible interface",
        "submitted_at": "2026-08-04T12:00:00Z"
    }
    nps_events = nps.normalize_payload(nps_payload)
    assert len(nps_events) == 1
    assert nps_events[0].source == "nps"
    assert nps_events[0].event_type == "nps_survey.submitted"

def test_sentiment_pipeline_scoring_and_topics():
    # Positive text
    pos_res = analyze_sentiment("Great service, smooth setup, wonderful and fantastic experience!")
    assert pos_res["sentiment"] > 0.3
    assert "onboarding" in pos_res["topics"]
    assert pos_res["urgency_flag"] is False

    # Negative text with urgency
    neg_res = analyze_sentiment("System is broken, terrible, unusable and crashed! We are cancelling immediately!")
    assert neg_res["sentiment"] < -0.5
    assert "bugs" in neg_res["topics"]
    assert "usability" in neg_res["topics"]
    assert neg_res["urgency_flag"] is True

def test_health_score_incorporates_sentiment_weight():
    feature_dict = {
        "usage_trend_slope": 0.2,
        "payment_failures_90d": 0,
        "days_since_last_event": 5,
        "support_sentiment": 0.8  # Positive sentiment -> 50 + (0.8 * 50) = 90.0
    }

    # Case A: Sentiment weight = 0.0 (stub/ignored)
    weights_stub = {
        "churn_weight": 0.40,
        "usage_trend_weight": 0.30,
        "payment_health_weight": 0.15,
        "support_sentiment_weight": 0.0,
        "engagement_recency_weight": 0.15
    }
    score_stub, breakdown_stub = compute_health_score(0.10, feature_dict, weights_stub)

    # Case B: Sentiment weight = 0.20 (real active weight)
    weights_active = {
        "churn_weight": 0.30,
        "usage_trend_weight": 0.25,
        "payment_health_weight": 0.15,
        "support_sentiment_weight": 0.20,
        "engagement_recency_weight": 0.10
    }
    score_active, breakdown_active = compute_health_score(0.10, feature_dict, weights_active)

    assert breakdown_active["support_sentiment"]["weight"] == 0.20
    assert breakdown_active["support_sentiment"]["normalized_score"] == 90.0
    assert breakdown_active["support_sentiment"]["weighted_contribution"] == 18.0
    assert score_active != score_stub

@pytest.mark.asyncio
async def test_champion_inactivity_triggers_champion_change_anomaly(db_session):
    tenant_id = uuid.uuid4()
    tenant = Tenant(id=tenant_id, name="Champion Test", subdomain="champ-test", plan_tier=PlanTier.tier1, is_active=True)
    db_session.add(tenant)
    await db_session.commit()

    await db_session.execute(sqlalchemy.text(f"SET LOCAL app.current_tenant = '{tenant_id}'"))
    c = Customer(id=uuid.uuid4(), tenant_id=tenant_id, plan="enterprise", mrr=3000.0)
    db_session.add(c)
    await db_session.commit()

    await db_session.execute(sqlalchemy.text(f"SET LOCAL app.current_tenant = '{tenant_id}'"))

    # Add Champion contact who is bounced & inactive for 45 days
    old_date = datetime.now(timezone.utc) - timedelta(days=45)
    contact = AccountContact(
        id=uuid.uuid4(),
        tenant_id=tenant_id,
        customer_id=c.id,
        name="Sarah Connor",
        email="sarah@customer.com",
        role="VP of Engineering",
        is_champion=True,
        is_active=False,
        bounced=True,
        last_confirmed_active=old_date
    )
    db_session.add(contact)
    await db_session.commit()

    with patch("apps.api.core.analytics.champion.publish_anomaly_update", new_callable=AsyncMock):
        anomalies = await evaluate_champion_status(db_session, tenant_id, c.id)
        assert len(anomalies) == 1
        anom = anomalies[0]
        assert anom.anomaly_type == "champion_change"
        assert anom.severity == "high"
        assert anom.detail["name"] == "Sarah Connor"
        assert anom.detail["bounced"] is True

@pytest.mark.asyncio
async def test_champion_status_endpoint(client, db_session):
    tenant_id = uuid.uuid4()
    tenant = Tenant(id=tenant_id, name="Champion API Test", subdomain="champ-api", plan_tier=PlanTier.tier1, is_active=True)
    db_session.add(tenant)
    user_id = uuid.uuid4()
    user = User(id=user_id, tenant_id=tenant_id, email="admin@champapi.com", role=Role.owner)
    db_session.add(user)
    await db_session.commit()

    token = create_access_token(user.email, role=user.role.value, tenant_id=str(tenant_id))
    headers = {"Authorization": f"Bearer {token}"}

    await db_session.execute(sqlalchemy.text(f"SET LOCAL app.current_tenant = '{tenant_id}'"))
    c = Customer(id=uuid.uuid4(), tenant_id=tenant_id, plan="premium", mrr=1500.0)
    db_session.add(c)
    await db_session.flush()

    contact = AccountContact(
        id=uuid.uuid4(),
        tenant_id=tenant_id,
        customer_id=c.id,
        name="John Doe",
        email="john@customer.com",
        role="Head of Product",
        is_champion=True,
        is_active=True,
        bounced=False,
        last_confirmed_active=datetime.now(timezone.utc)
    )
    db_session.add(contact)
    await db_session.commit()

    res = await client.get(f"/tenants/{tenant_id}/customers/{c.id}/champion-status", headers=headers)
    assert res.status_code == 200
    data = res.json()
    assert len(data) == 1
    assert data[0]["name"] == "John Doe"
    assert data[0]["is_champion"] is True
    assert data[0]["status"] == "active"
