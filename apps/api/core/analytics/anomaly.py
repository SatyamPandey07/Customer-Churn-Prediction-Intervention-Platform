import json
import logging
import math
import uuid
from datetime import UTC, datetime, timedelta

import redis.asyncio as redis
from apps.api.core.queue import REDIS_URL
from apps.api.models import AnomalyEvent, Campaign, Customer, CustomerEvent
from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)

async def publish_anomaly_update(tenant_id: str, anomaly: AnomalyEvent):
    """
    Publishes live anomaly event payload to Redis pub/sub channel for WebSocket broadcast.
    """
    try:
        r = redis.from_url(REDIS_URL)
        payload = json.dumps({
            "event": "anomaly_detected",
            "tenant_id": tenant_id,
            "id": str(anomaly.id),
            "customer_id": str(anomaly.customer_id),
            "anomaly_type": anomaly.anomaly_type,
            "severity": anomaly.severity,
            "detail": anomaly.detail,
            "detected_at": anomaly.detected_at.isoformat() if hasattr(anomaly.detected_at, "isoformat") else str(anomaly.detected_at)
        })
        await r.publish("anomaly_updates", payload)
        await r.aclose()
    except Exception as e:
        logger.warning(f"Failed to publish anomaly update to Redis: {e}")

async def trigger_campaigns_for_anomaly(
    db: AsyncSession,
    tenant_id: uuid.UUID,
    customer: Customer,
    anomaly_type: str,
    severity: str
):
    """
    Evaluates active campaigns with trigger_rule containing anomaly_type and triggers interventions.
    """
    from apps.api.core.outreach.engine import _evaluate_single_campaign
    res = await db.execute(
        select(Campaign).where(
            and_(Campaign.tenant_id == tenant_id, Campaign.status == "active")
        )
    )
    campaigns = res.scalars().all()

    for campaign in campaigns:
        rule = campaign.trigger_rule or {}
        if "anomaly_type" in rule:
            target_type = rule["anomaly_type"]
            target_severity = rule.get("severity")
            if target_type == anomaly_type and (not target_severity or target_severity == severity):
                await _evaluate_single_campaign(db, tenant_id, campaign)

async def detect_anomalies_for_customer(
    db: AsyncSession,
    tenant_id: uuid.UUID,
    customer_id: uuid.UUID,
    cooldown_hours: int = 24
) -> list[AnomalyEvent]:
    """
    Computes rolling statistics for customer, flags anomalies (usage cliff, login gap, payment spike, feature abandonment),
    applies 24h debouncing, publishes live update, and triggers campaign engine hooks.
    """
    import sqlalchemy
    await db.execute(sqlalchemy.text(f"SET LOCAL app.current_tenant = '{tenant_id}'"))

    now = datetime.now(UTC)
    start_30d = now - timedelta(days=30)

    cutoff_cooldown = now - timedelta(hours=cooldown_hours)

    # 1. Fetch Customer
    res_c = await db.execute(
        select(Customer).where(Customer.tenant_id == tenant_id, Customer.id == customer_id)
    )
    customer = res_c.scalars().first()
    if not customer:
        return []

    # 2. Fetch Events last 30 days
    res_e = await db.execute(
        select(CustomerEvent)
        .where(
            CustomerEvent.tenant_id == tenant_id,
            CustomerEvent.customer_id == customer_id,
            CustomerEvent.occurred_at >= start_30d
        )
    )
    events = res_e.scalars().all()

    # Daily activity breakdown
    daily_counts: dict[str, int] = {}
    for day_i in range(30):
        day_key = (now - timedelta(days=day_i)).strftime("%Y-%m-%d")
        daily_counts[day_key] = 0

    today_key = now.strftime("%Y-%m-%d")
    for e in events:
        d_str = e.occurred_at.strftime("%Y-%m-%d")
        if d_str in daily_counts:
            daily_counts[d_str] += 1

    counts_list = list(daily_counts.values())
    today_count = daily_counts.get(today_key, 0)
    past_counts = counts_list[1:]  # past 29 days

    mean_past = sum(past_counts) / max(1, len(past_counts))
    variance_past = sum((x - mean_past) ** 2 for x in past_counts) / max(1, len(past_counts))
    stddev_past = max(1.0, math.sqrt(variance_past))

    detected_anomalies: list[AnomalyEvent] = []

    # Check 1: Usage Cliff (Z-score <= -2.0 when baseline mean >= 3.0)
    if mean_past >= 3.0:
        z_score = (today_count - mean_past) / stddev_past
        if z_score <= -2.0:

            severity = "high" if (z_score <= -3.0 or today_count == 0) else "medium"
            detected_anomalies.append({
                "type": "usage_cliff",
                "severity": severity,
                "detail": {
                    "z_score": round(z_score, 2),
                    "today_activity": today_count,
                    "baseline_mean_30d": round(mean_past, 2),
                    "baseline_stddev_30d": round(stddev_past, 2),
                    "message": f"Usage cliff detected: daily activity dropped to {today_count} (Z-score: {z_score:.2f})"
                }
            })

    # Check 2: Login Gap (Inactivity >= 7 days)
    last_seen = customer.last_seen_at or customer.created_at or (now - timedelta(days=30))
    days_since_seen = (now - last_seen).days
    if days_since_seen >= 7:
        severity = "high" if days_since_seen >= 14 else "medium"
        detected_anomalies.append({
            "type": "login_gap",
            "severity": severity,
            "detail": {
                "days_inactive": days_since_seen,
                "last_seen_at": last_seen.isoformat(),
                "message": f"Login gap detected: no user activity recorded for {days_since_seen} consecutive days"
            }
        })

    # Check 3: Payment Failure Spike (>= 2 failed invoices in 90d events)
    payment_failures = [e for e in events if e.event_type == "invoice.failed"]
    if len(payment_failures) >= 2:
        detected_anomalies.append({
            "type": "payment_failure_spike",
            "severity": "high",
            "detail": {
                "failure_count": len(payment_failures),
                "message": f"Payment failure spike: {len(payment_failures)} failed invoices recorded recently"
            }
        })

    # Check 4: Feature Abandonment
    feature_events_past = [e for e in events if e.event_type == "feature_used"]
    feature_7d = [e for e in feature_events_past if e.occurred_at >= (now - timedelta(days=7))]
    if len(feature_events_past) >= 5 and len(feature_7d) == 0:
        detected_anomalies.append({
            "type": "feature_abandonment",
            "severity": "medium",
            "detail": {
                "historical_feature_uses": len(feature_events_past),
                "recent_7d_uses": 0,
                "message": "Feature abandonment: customer stopped using core modules in the last 7 days"
            }
        })

    # 3. Debounce & Save Anomalies
    created_records: list[AnomalyEvent] = []
    for candidate in detected_anomalies:
        anom_type = candidate["type"]
        sev = candidate["severity"]
        det = candidate["detail"]

        # Check existing open anomaly or recent anomaly within cooldown
        res_existing = await db.execute(
            select(AnomalyEvent).where(
                and_(
                    AnomalyEvent.tenant_id == tenant_id,
                    AnomalyEvent.customer_id == customer_id,
                    AnomalyEvent.anomaly_type == anom_type,
                    AnomalyEvent.resolved == False,
                    AnomalyEvent.detected_at >= cutoff_cooldown
                )
            )
        )
        if res_existing.scalars().first():
            logger.info(f"Debounced anomaly creation for customer {customer_id} ({anom_type} cooldown active)")
            continue

        new_anom = AnomalyEvent(
            id=uuid.uuid4(),
            tenant_id=tenant_id,
            customer_id=customer_id,
            anomaly_type=anom_type,
            severity=sev,
            detected_at=now,
            detail=det,
            resolved=False
        )
        db.add(new_anom)
        created_records.append(new_anom)

    if created_records:
        await db.commit()
        for rec in created_records:
            await publish_anomaly_update(str(tenant_id), rec)
            if rec.severity == "high":
                await trigger_campaigns_for_anomaly(db, tenant_id, customer, rec.anomaly_type, rec.severity)

    return created_records
