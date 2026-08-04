import uuid
import logging
from typing import Optional, Dict, Any
from datetime import datetime, timezone
from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession

from apps.api.models import Customer, ExitSurvey
from apps.api.core.outreach.adapters import get_adapter

logger = logging.getLogger(__name__)

async def trigger_exit_survey_on_cancellation(
    db: AsyncSession,
    tenant_id: uuid.UUID,
    customer_id: uuid.UUID
) -> bool:
    """
    Auto-triggers an exit survey when a customer subscription is cancelled (from Stripe events).
    Dispatches survey invitation email using PR-06 outreach channel adapters.
    """
    import sqlalchemy
    await db.execute(sqlalchemy.text(f"SET LOCAL app.current_tenant = '{tenant_id}'"))

    res_c = await db.execute(
        select(Customer).where(
            and_(Customer.tenant_id == tenant_id, Customer.id == customer_id)
        )
    )
    customer = res_c.scalars().first()
    if not customer:
        logger.warning(f"Customer {customer_id} not found for exit survey trigger.")
        return False

    # Dispatch survey outreach email via PR-06 adapter
    adapter = get_adapter("email")
    survey_template = (
        "We're sorry to see you go. Please take 30 seconds to let us know how we can improve: "
        f"https://app.churnguard.ai/exit-survey?customer_id={customer_id}"
    )
    try:
        await adapter.send(db, customer, survey_template)
        logger.info(f"Triggered exit survey for cancelled customer {customer_id}")
        return True
    except Exception as e:
        logger.error(f"Failed to dispatch exit survey email to customer {customer_id}: {e}")
        return False

async def submit_exit_survey(
    db: AsyncSession,
    tenant_id: uuid.UUID,
    customer_id: uuid.UUID,
    reason_category: str,
    free_text: Optional[str] = None
) -> ExitSurvey:
    """
    Stores exit survey response and feeds stated reason back into the feature store / customer model.
    """
    import sqlalchemy
    await db.execute(sqlalchemy.text(f"SET LOCAL app.current_tenant = '{tenant_id}'"))

    now = datetime.now(timezone.utc)

    survey = ExitSurvey(
        id=uuid.uuid4(),
        tenant_id=tenant_id,
        customer_id=customer_id,
        reason_category=reason_category,
        free_text=free_text,
        submitted_at=now
    )
    db.add(survey)

    # Feed stated reason back into Customer model
    res_c = await db.execute(
        select(Customer).where(
            and_(Customer.tenant_id == tenant_id, Customer.id == customer_id)
        )
    )
    customer = res_c.scalars().first()
    if customer:
        customer.stated_churn_reason = reason_category

    await db.commit()
    return survey
