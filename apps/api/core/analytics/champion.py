import logging
import uuid
from datetime import UTC, datetime, timedelta

from apps.api.core.analytics.anomaly import publish_anomaly_update
from apps.api.models import AccountContact, AnomalyEvent
from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)

async def evaluate_champion_status(
    db: AsyncSession,
    tenant_id: uuid.UUID,
    customer_id: uuid.UUID,
    cooldown_hours: int = 24
) -> list[AnomalyEvent]:
    """
    Evaluates champion contacts for a customer account. If a champion contact email bounces
    or stops showing activity for >= 30 days while other account users are active,
    emits a 'champion_change' anomaly_event (reusing PR-13 anomaly table).
    """
    import sqlalchemy
    await db.execute(sqlalchemy.text(f"SET LOCAL app.current_tenant = '{tenant_id}'"))

    now = datetime.now(UTC)
    cutoff_cooldown = now - timedelta(hours=cooldown_hours)

    res_champions = await db.execute(
        select(AccountContact).where(
            and_(
                AccountContact.tenant_id == tenant_id,
                AccountContact.customer_id == customer_id,
                AccountContact.is_champion == True
            )
        )
    )
    champions = res_champions.scalars().all()
    if not champions:
        return []

    created_anomalies: list[AnomalyEvent] = []

    for contact in champions:
        is_inactive = not contact.is_active or contact.bounced
        last_active = contact.last_confirmed_active or contact.created_at or (now - timedelta(days=60))
        days_inactive = (now - last_active).days

        if days_inactive >= 30:
            is_inactive = True

        if is_inactive:
            reason = "contact_bounced" if contact.bounced else "contact_inactive"

            # Check debounce cooldown
            res_existing = await db.execute(
                select(AnomalyEvent).where(
                    and_(
                        AnomalyEvent.tenant_id == tenant_id,
                        AnomalyEvent.customer_id == customer_id,
                        AnomalyEvent.anomaly_type == "champion_change",
                        AnomalyEvent.resolved == False,
                        AnomalyEvent.detected_at >= cutoff_cooldown
                    )
                )
            )
            if res_existing.scalars().first():
                logger.info(f"Champion change anomaly debounced for customer {customer_id} ({contact.email})")
                continue

            anomaly = AnomalyEvent(
                id=uuid.uuid4(),
                tenant_id=tenant_id,
                customer_id=customer_id,
                anomaly_type="champion_change",
                severity="high",
                detected_at=now,
                detail={
                    "champion_id": str(contact.id),
                    "name": contact.name,
                    "email": contact.email,
                    "role": contact.role,
                    "bounced": contact.bounced,
                    "days_inactive": days_inactive,
                    "reason": reason,
                    "message": f"Champion contact change: {contact.name} ({contact.email}) is flagged {reason} ({days_inactive} days inactive)."
                },
                resolved=False
            )
            db.add(anomaly)
            created_anomalies.append(anomaly)

    if created_anomalies:
        await db.commit()
        for anom in created_anomalies:
            await publish_anomaly_update(str(tenant_id), anom)

    return created_anomalies
