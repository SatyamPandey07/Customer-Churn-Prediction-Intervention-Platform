import logging
from datetime import datetime, timedelta, timezone
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_
from apps.api.models import Intervention, InterventionOutcome, CustomerEvent

logger = logging.getLogger(__name__)

async def track_intervention_outcomes(db: AsyncSession, tenant_id: str, evaluation_days: int = 30) -> None:
    """
    Evaluates pending interventions older than evaluation_days to determine
    if the customer churned or was retained in that window.
    """
    cutoff_date = datetime.now(timezone.utc) - timedelta(days=evaluation_days)

    # Find pending interventions sent before the cutoff date
    stmt = select(Intervention).where(
        and_(
            Intervention.tenant_id == tenant_id,
            Intervention.outcome == InterventionOutcome.pending,
            Intervention.status == "sent",
            Intervention.sent_at <= cutoff_date
        )
    )
    result = await db.execute(stmt)
    pending_interventions = result.scalars().all()

    for intervention in pending_interventions:
        # Check if customer had a churn event (subscription_canceled) within the evaluation window
        end_of_window = intervention.sent_at + timedelta(days=evaluation_days)
        
        event_stmt = select(CustomerEvent).where(
            and_(
                CustomerEvent.tenant_id == tenant_id,
                CustomerEvent.customer_id == intervention.customer_id,
                CustomerEvent.event_type == 'subscription_canceled',
                CustomerEvent.occurred_at >= intervention.sent_at,
                CustomerEvent.occurred_at <= end_of_window
            )
        ).limit(1)
        
        event_result = await db.execute(event_stmt)
        churn_event = event_result.scalars().first()

        if churn_event:
            intervention.outcome = InterventionOutcome.churned
        else:
            intervention.outcome = InterventionOutcome.retained

        intervention.outcome_recorded_at = datetime.now(timezone.utc)
    
    if pending_interventions:
        await db.commit()
        logger.info(f"Recorded outcomes for {len(pending_interventions)} interventions for tenant {tenant_id}.")
