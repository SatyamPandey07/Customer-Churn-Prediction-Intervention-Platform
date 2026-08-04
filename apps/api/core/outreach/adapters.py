import logging
import uuid

from apps.api.models import Customer, InAppNotification
from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)

class OutreachAdapter:
    async def send(self, db: AsyncSession, customer: Customer, message: str, **kwargs) -> bool:
        raise NotImplementedError("Subclasses must implement send()")

class EmailAdapter(OutreachAdapter):
    async def send(self, db: AsyncSession, customer: Customer, message: str, **kwargs) -> bool:
        # Mock SendGrid client
        email = customer.external_ids.get("email", f"customer_{customer.id}@example.com")
        logger.info(f"[EmailAdapter] Simulated sending email to {email}: {message}")
        return True

class SmsAdapter(OutreachAdapter):
    async def send(self, db: AsyncSession, customer: Customer, message: str, **kwargs) -> bool:
        # Mock Twilio client
        phone = customer.external_ids.get("phone", "+15550000000")
        logger.info(f"[SmsAdapter] Simulated sending SMS to {phone}: {message}")
        return True

class SlackAdapter(OutreachAdapter):
    async def send(self, db: AsyncSession, customer: Customer, message: str, **kwargs) -> bool:
        # Mock Slack webhook
        slack_id = customer.external_ids.get("slack", f"U{str(customer.id)[:8]}")
        logger.info(f"[SlackAdapter] Simulated sending Slack message to {slack_id}: {message}")
        return True

class InAppAdapter(OutreachAdapter):
    async def send(self, db: AsyncSession, customer: Customer, message: str, **kwargs) -> bool:
        # Writes to the InAppNotification table
        notification = InAppNotification(
            id=uuid.uuid4(),
            tenant_id=customer.tenant_id,
            customer_id=customer.id,
            message=message,
            is_read=False
        )
        db.add(notification)
        await db.commit()
        logger.info(f"[InAppAdapter] Created InAppNotification for customer {customer.id}")
        return True

def get_adapter(channel: str) -> OutreachAdapter:
    adapters: dict[str, type[OutreachAdapter]] = {
        "email": EmailAdapter,
        "sms": SmsAdapter,
        "slack": SlackAdapter,
        "in_app": InAppAdapter,
    }
    adapter_cls = adapters.get(channel.lower())
    if not adapter_cls:
        raise ValueError(f"Unknown channel: {channel}")
    return adapter_cls()
