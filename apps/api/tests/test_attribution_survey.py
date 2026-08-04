import pytest
import uuid
import sqlalchemy
from datetime import datetime, timezone, timedelta
from unittest.mock import AsyncMock, patch

from apps.api.models import Tenant, User, Customer, Intervention, InterventionOutcome, ExitSurvey, ChurnFeature, Role, PlanTier
from apps.api.core.security import create_access_token
from apps.api.core.analytics.attribution import calculate_time_decay_weights, get_tenant_attribution_report, get_explanation_validation_report
from apps.api.core.surveys.engine import trigger_exit_survey_on_cancellation, submit_exit_survey
from apps.api.worker import process_webhook

def test_time_decay_attribution_math():
    now = datetime.now(timezone.utc)
    t1 = now - timedelta(days=14)  # 2 half-lives ago -> weight ~ 0.25
    t2 = now - timedelta(days=7)   # 1 half-life ago -> weight ~ 0.50
    t3 = now - timedelta(days=1)   # ~0.14 half-lives ago -> weight ~ 0.90

    touches = [
        {"id": "t1", "channel": "email", "sent_at": t1},
        {"id": "t2", "channel": "slack", "sent_at": t2},
        {"id": "t3", "channel": "email", "sent_at": t3}
    ]

    attr_touches = calculate_time_decay_weights(touches, outcome_date=now, half_life_days=7.0)

    assert len(attr_touches) == 3
    # Check weight ordering: t3 > t2 > t1
    assert attr_touches[2]["attribution_fraction"] > attr_touches[1]["attribution_fraction"]
    assert attr_touches[1]["attribution_fraction"] > attr_touches[0]["attribution_fraction"]

    # Sum of fractions must equal 1.0
    total_frac = sum(t["attribution_fraction"] for t in attr_touches)
    assert pytest.approx(total_frac, abs=1e-3) == 1.0

@pytest.mark.asyncio
async def test_attribution_report_single_vs_multitouch(db_session):
    tenant_id = uuid.uuid4()
    tenant = Tenant(id=tenant_id, name="Attribution Test", subdomain="attr-test", plan_tier=PlanTier.tier1, is_active=True)
    db_session.add(tenant)
    await db_session.commit()

    await db_session.execute(sqlalchemy.text(f"SET LOCAL app.current_tenant = '{tenant_id}'"))

    c1 = Customer(id=uuid.uuid4(), tenant_id=tenant_id, plan="premium", mrr=1000.0)
    c2 = Customer(id=uuid.uuid4(), tenant_id=tenant_id, plan="enterprise", mrr=3000.0)
    db_session.add_all([c1, c2])
    await db_session.commit()

    now = datetime.now(timezone.utc)

    # Customer 1: Single touch (outcome = retained)
    i1 = Intervention(
        id=uuid.uuid4(), tenant_id=tenant_id, customer_id=c1.id, channel="email",
        sent_at=now - timedelta(days=5), outcome=InterventionOutcome.retained
    )

    # Customer 2: Multi-touch (slack 10d ago, email 2d ago, outcome = retained)
    i2_1 = Intervention(
        id=uuid.uuid4(), tenant_id=tenant_id, customer_id=c2.id, channel="slack",
        sent_at=now - timedelta(days=10), outcome=InterventionOutcome.retained
    )
    i2_2 = Intervention(
        id=uuid.uuid4(), tenant_id=tenant_id, customer_id=c2.id, channel="email",
        sent_at=now - timedelta(days=2), outcome=InterventionOutcome.retained
    )

    db_session.add_all([i1, i2_1, i2_2])
    await db_session.commit()

    report = await get_tenant_attribution_report(db_session, tenant_id)

    assert "methodology" in report
    assert report["summary"]["total_retained_accounts"] == 2
    assert report["summary"]["single_touch_accounts"] == 1
    assert report["summary"]["multi_touch_accounts"] == 1
    assert report["channel_contributions"]["email"] > 1.0
    assert report["channel_contributions"]["slack"] > 0.0

@pytest.mark.asyncio
async def test_stripe_cancellation_triggers_exit_survey(db_session):
    tenant_id = uuid.uuid4()
    tenant = Tenant(id=tenant_id, name="Survey Trigger Test", subdomain="survey-trig", plan_tier=PlanTier.tier1, is_active=True)
    db_session.add(tenant)
    await db_session.commit()

    await db_session.execute(sqlalchemy.text(f"SET LOCAL app.current_tenant = '{tenant_id}'"))
    c = Customer(
        id=uuid.uuid4(),
        tenant_id=tenant_id,
        external_ids={"stripe": "cus_stripe_999"},
        plan="standard",
        mrr=200.0
    )
    db_session.add(c)
    await db_session.commit()

    mock_adapter = AsyncMock()
    mock_adapter.send.return_value = True

    # Case A: Cancellation event -> triggers exit survey
    cancel_payload = {
        "type": "customer.subscription.deleted",
        "id": "evt_cancel_1",
        "created": int(datetime.now(timezone.utc).timestamp()),
        "data": {"object": {"customer": "cus_stripe_999"}}
    }

    with patch("apps.api.core.surveys.engine.get_adapter", return_value=mock_adapter), \
         patch("apps.api.core.surveys.engine.trigger_exit_survey_on_cancellation", new_callable=AsyncMock) as mock_trig:
        mock_trig.return_value = True
        await process_webhook({"tracer": None}, str(tenant_id), "stripe", cancel_payload)
        mock_trig.assert_called_once()

    # Case B: Invoice payment succeeded -> does NOT trigger exit survey
    payment_payload = {
        "type": "invoice.payment_succeeded",
        "id": "evt_pay_1",
        "created": int(datetime.now(timezone.utc).timestamp()),
        "data": {"object": {"customer": "cus_stripe_999"}}
    }

    with patch("apps.api.core.surveys.engine.trigger_exit_survey_on_cancellation", new_callable=AsyncMock) as mock_trig2:
        await process_webhook({"tracer": None}, str(tenant_id), "stripe", payment_payload)
        mock_trig2.assert_not_called()

@pytest.mark.asyncio
async def test_explanation_validation_report_and_feedback_loop(db_session):
    tenant_id = uuid.uuid4()
    tenant = Tenant(id=tenant_id, name="Validation Test", subdomain="val-test", plan_tier=PlanTier.tier1, is_active=True)
    db_session.add(tenant)
    await db_session.commit()

    await db_session.execute(sqlalchemy.text(f"SET LOCAL app.current_tenant = '{tenant_id}'"))

    c = Customer(id=uuid.uuid4(), tenant_id=tenant_id, plan="premium", mrr=800.0)
    db_session.add(c)

    now = datetime.now(timezone.utc)
    cf = ChurnFeature(
        id=uuid.uuid4(), tenant_id=tenant_id, customer_id=c.id,
        as_of_date=now, feature_set_version="v1",
        features={"payment_failures_90d": 2, "days_since_last_event": 3},
        created_at=now
    )
    db_session.add(cf)
    await db_session.commit()

    # Submit ExitSurvey feedback with stated reason "price"
    survey = await submit_exit_survey(db_session, tenant_id, c.id, reason_category="price", free_text="Too expensive")
    assert survey.reason_category == "price"

    # Verify stated_churn_reason stored in Customer (Feedback loop to feature store)
    await db_session.refresh(c)
    assert c.stated_churn_reason == "price"

    # Fetch explanation validation report
    report = await get_explanation_validation_report(db_session, tenant_id)

    assert "methodology" in report
    assert report["total_surveyed"] == 1
    assert report["agreed_count"] == 1
    assert report["agreement_rate"] == 100.0
    assert report["details"][0]["predicted_category"] == "price"
    assert report["details"][0]["stated_category"] == "price"
    assert report["details"][0]["agreed"] is True
