import time
import pytest
import uuid
import sqlalchemy
from datetime import datetime, timezone, timedelta
from unittest.mock import AsyncMock, patch

from apps.api.models import Tenant, User, Customer, CustomerEvent, Campaign, Intervention, AnomalyEvent, Role, PlanTier
from apps.api.core.security import create_access_token
from apps.api.core.analytics.anomaly import detect_anomalies_for_customer

@pytest.mark.asyncio
async def test_z_score_usage_cliff_detection_and_no_false_positives(db_session):
    tenant_id = uuid.uuid4()
    tenant = Tenant(id=tenant_id, name="Anomaly Detection Test", subdomain="anom-test", plan_tier=PlanTier.tier1, is_active=True)
    db_session.add(tenant)
    await db_session.commit()

    await db_session.execute(sqlalchemy.text(f"SET LOCAL app.current_tenant = '{tenant_id}'"))

    # Customer 1: Normal steady usage (10 events/day for 29 days, 9 events today -> Z is near 0)
    c1 = Customer(
        id=uuid.uuid4(), tenant_id=tenant_id, external_ids={"stripe": "cus_normal"},
        plan="standard", mrr=100.0, created_at=datetime.now(timezone.utc) - timedelta(days=35),
        last_seen_at=datetime.now(timezone.utc)
    )
    # Customer 2: Usage Cliff (10 events/day for 29 days, 0 events today -> Z = -3.0+)
    c2 = Customer(
        id=uuid.uuid4(), tenant_id=tenant_id, external_ids={"stripe": "cus_cliff"},
        plan="premium", mrr=500.0, created_at=datetime.now(timezone.utc) - timedelta(days=35),
        last_seen_at=datetime.now(timezone.utc)
    )

    db_session.add_all([c1, c2])
    await db_session.commit()

    await db_session.execute(sqlalchemy.text(f"SET LOCAL app.current_tenant = '{tenant_id}'"))

    now = datetime.now(timezone.utc)
    # Seed events for past 29 days (excluding today)
    events_to_add = []
    for day_i in range(1, 30):
        occurred = now - timedelta(days=day_i)
        for _ in range(10):
            events_to_add.append(CustomerEvent(
                id=uuid.uuid4(), tenant_id=tenant_id, customer_id=c1.id,
                source="app", external_event_id=str(uuid.uuid4()), event_type="login", occurred_at=occurred
            ))
            events_to_add.append(CustomerEvent(
                id=uuid.uuid4(), tenant_id=tenant_id, customer_id=c2.id,
                source="app", external_event_id=str(uuid.uuid4()), event_type="login", occurred_at=occurred
            ))

    # Add 9 events today for c1
    for _ in range(9):
        events_to_add.append(CustomerEvent(
            id=uuid.uuid4(), tenant_id=tenant_id, customer_id=c1.id,
            source="app", external_event_id=str(uuid.uuid4()), event_type="login", occurred_at=now
        ))

    db_session.add_all(events_to_add)
    await db_session.commit()

    with patch("apps.api.core.analytics.anomaly.publish_anomaly_update", new_callable=AsyncMock):
        # Run detection for c1 (normal variance)
        anoms_c1 = await detect_anomalies_for_customer(db_session, tenant_id, c1.id)
        assert len(anoms_c1) == 0, "Normal variance should NOT trigger an anomaly"

        # Run detection for c2 (usage cliff)
        anoms_c2 = await detect_anomalies_for_customer(db_session, tenant_id, c2.id)
        assert len(anoms_c2) >= 1
        cliff_anom = next((a for a in anoms_c2 if a.anomaly_type == "usage_cliff"), None)
        assert cliff_anom is not None
        assert cliff_anom.severity in ["high", "critical"]
        assert cliff_anom.detail["z_score"] <= -2.0

@pytest.mark.asyncio
async def test_debounce_cooldown_logic(db_session):
    tenant_id = uuid.uuid4()
    tenant = Tenant(id=tenant_id, name="Debounce Test", subdomain="debounce-test", plan_tier=PlanTier.tier1, is_active=True)
    db_session.add(tenant)
    await db_session.commit()

    await db_session.execute(sqlalchemy.text(f"SET LOCAL app.current_tenant = '{tenant_id}'"))
    c = Customer(
        id=uuid.uuid4(), tenant_id=tenant_id, external_ids={"stripe": "cus_deb"},
        plan="standard", mrr=200.0, created_at=datetime.now(timezone.utc) - timedelta(days=35)
    )
    db_session.add(c)
    await db_session.commit()

    await db_session.execute(sqlalchemy.text(f"SET LOCAL app.current_tenant = '{tenant_id}'"))
    now = datetime.now(timezone.utc)
    events = []
    for day_i in range(1, 30):
        occurred = now - timedelta(days=day_i)
        for _ in range(10):
            events.append(CustomerEvent(
                id=uuid.uuid4(), tenant_id=tenant_id, customer_id=c.id,
                source="app", external_event_id=str(uuid.uuid4()), event_type="page_view", occurred_at=occurred
            ))
    db_session.add_all(events)
    await db_session.commit()

    with patch("apps.api.core.analytics.anomaly.publish_anomaly_update", new_callable=AsyncMock):
        # Run detection pass 1 -> Creates 1 anomaly
        first_pass = await detect_anomalies_for_customer(db_session, tenant_id, c.id)
        assert len(first_pass) >= 1

        # Run detection pass 2 immediately -> Cooldown active, 0 new anomalies created
        second_pass = await detect_anomalies_for_customer(db_session, tenant_id, c.id)
        assert len(second_pass) == 0, "Repeated triggering within cooldown must produce 0 duplicate records"

        res_total = await db_session.execute(
            sqlalchemy.select(AnomalyEvent).where(AnomalyEvent.tenant_id == tenant_id, AnomalyEvent.customer_id == c.id)
        )
        all_db_anoms = res_total.scalars().all()
        assert len(all_db_anoms) == len(first_pass)

@pytest.mark.asyncio
async def test_auto_trigger_campaign_hook(db_session):
    tenant_id = uuid.uuid4()
    tenant = Tenant(id=tenant_id, name="Campaign Auto Trigger Test", subdomain="camp-trigger", plan_tier=PlanTier.tier1, is_active=True)
    db_session.add(tenant)
    await db_session.commit()

    await db_session.execute(sqlalchemy.text(f"SET LOCAL app.current_tenant = '{tenant_id}'"))
    camp = Campaign(
        id=uuid.uuid4(),
        tenant_id=tenant_id,
        name="Usage Cliff CS Outreach",
        trigger_rule={"anomaly_type": "usage_cliff", "severity": "high"},
        intervention_type="email_outreach",
        channel="email",
        status="active",
        template="Hi CS team, customer {customer_id} has suffered a usage cliff."
    )
    db_session.add(camp)

    c = Customer(
        id=uuid.uuid4(), tenant_id=tenant_id, external_ids={"email": "cliff@customer.com"},
        plan="enterprise", mrr=2000.0, created_at=datetime.now(timezone.utc) - timedelta(days=40)
    )
    db_session.add(c)
    await db_session.commit()

    await db_session.execute(sqlalchemy.text(f"SET LOCAL app.current_tenant = '{tenant_id}'"))
    now = datetime.now(timezone.utc)
    events = []
    for day_i in range(1, 30):
        occurred = now - timedelta(days=day_i)
        for _ in range(15):
            events.append(CustomerEvent(
                id=uuid.uuid4(), tenant_id=tenant_id, customer_id=c.id,
                source="app", external_event_id=str(uuid.uuid4()), event_type="login", occurred_at=occurred
            ))
    db_session.add_all(events)
    await db_session.commit()

    mock_adapter = AsyncMock()
    mock_adapter.send.return_value = True

    with patch("apps.api.core.analytics.anomaly.publish_anomaly_update", new_callable=AsyncMock), \
         patch("apps.api.core.outreach.engine.get_adapter", return_value=mock_adapter):

        created = await detect_anomalies_for_customer(db_session, tenant_id, c.id)
        assert len(created) >= 1

        # Verify intervention was auto-created via campaign engine
        res_int = await db_session.execute(
            sqlalchemy.select(Intervention).where(Intervention.tenant_id == tenant_id, Intervention.customer_id == c.id)
        )
        interventions = res_int.scalars().all()
        assert len(interventions) == 1
        assert interventions[0].campaign_id == camp.id
        mock_adapter.send.assert_called_once()

@pytest.mark.asyncio
async def test_detection_latency_bounds(db_session):
    tenant_id = uuid.uuid4()
    tenant = Tenant(id=tenant_id, name="Latency Test", subdomain="lat-test", plan_tier=PlanTier.tier1, is_active=True)
    db_session.add(tenant)
    await db_session.commit()

    await db_session.execute(sqlalchemy.text(f"SET LOCAL app.current_tenant = '{tenant_id}'"))
    c = Customer(
        id=uuid.uuid4(), tenant_id=tenant_id, external_ids={"stripe": "cus_lat"},
        plan="standard", mrr=300.0, created_at=datetime.now(timezone.utc) - timedelta(days=35)
    )
    db_session.add(c)
    await db_session.commit()

    with patch("apps.api.core.analytics.anomaly.publish_anomaly_update", new_callable=AsyncMock):
        t0 = time.perf_counter()
        await detect_anomalies_for_customer(db_session, tenant_id, c.id)
        elapsed_ms = (time.perf_counter() - t0) * 1000.0

        # Assert latency bound < 1000ms (generous CI-safe bound)
        assert elapsed_ms < 1000.0, f"Detection latency took {elapsed_ms:.2f}ms, exceeding 1000ms CI bound"

@pytest.mark.asyncio
async def test_anomaly_endpoints(client, db_session):
    tenant_id = uuid.uuid4()
    tenant = Tenant(id=tenant_id, name="Anomaly API Test", subdomain="anom-api", plan_tier=PlanTier.tier1, is_active=True)
    db_session.add(tenant)
    user_id = uuid.uuid4()
    user = User(id=user_id, tenant_id=tenant_id, email="admin@anomapi.com", role=Role.owner)
    db_session.add(user)
    await db_session.commit()

    token = create_access_token(user.email, role=user.role.value, tenant_id=str(tenant_id))
    headers = {"Authorization": f"Bearer {token}"}

    await db_session.execute(sqlalchemy.text(f"SET LOCAL app.current_tenant = '{tenant_id}'"))
    c = Customer(id=uuid.uuid4(), tenant_id=tenant_id, plan="standard", mrr=100.0)
    db_session.add(c)
    await db_session.flush()

    anom = AnomalyEvent(
        id=uuid.uuid4(), tenant_id=tenant_id, customer_id=c.id,
        anomaly_type="usage_cliff", severity="high", detail={"z_score": -3.1}, resolved=False
    )
    db_session.add(anom)
    await db_session.commit()

    # GET anomalies
    res = await client.get(f"/tenants/{tenant_id}/anomalies?resolved=false", headers=headers)
    assert res.status_code == 200
    data = res.json()
    assert len(data) == 1
    assert data[0]["anomaly_type"] == "usage_cliff"

    # Resolve anomaly
    res_resolve = await client.post(f"/tenants/{tenant_id}/anomalies/{anom.id}/resolve", headers=headers)
    assert res_resolve.status_code == 200
    assert res_resolve.json()["status"] == "resolved"
