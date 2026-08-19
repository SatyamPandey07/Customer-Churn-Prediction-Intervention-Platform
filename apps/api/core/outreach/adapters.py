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

class CustomRestAdapter(OutreachAdapter):
    def __init__(self, channel_name: str):
        self.channel_name = channel_name

    async def send(self, db: AsyncSession, customer: Customer, message: str, **kwargs) -> bool:
        from apps.api.models import CustomIntegration, TenantSecret
        from sqlalchemy.future import select
        
        # 1. Fetch custom integration
        stmt = select(CustomIntegration).where(
            CustomIntegration.name == self.channel_name,
            CustomIntegration.integration_type == "rest_out",
            CustomIntegration.tenant_id == customer.tenant_id
        )
        result = await db.execute(stmt)
        integration = result.scalars().first()
        
        if not integration:
            logger.error(f"[CustomRestAdapter] No custom rest_out integration found for channel {self.channel_name}")
            return False
            
        if integration.status == "paused":
            logger.warning(f"[CustomRestAdapter] Integration {self.channel_name} is paused due to consecutive failures.")
            return False
            
        # 2. Fetch credentials
        secret_value = None
        if integration.credential_ref:
            sec_stmt = select(TenantSecret).where(TenantSecret.id == integration.credential_ref)
            sec_result = await db.execute(sec_stmt)
            secret = sec_result.scalars().first()
            if secret:
                secret_value = secret.encrypted_value
                
        # 3. Make mock REST call
        config = integration.config
        base_url = config.get("base_url", "http://mock.endpoint")
        auth_type = config.get("auth_type", "none")
        
        # Simulate network request
        try:
            logger.info(f"[CustomRestAdapter] Sending payload to {base_url} (auth: {auth_type})")
            # Simulate a successful request
            integration.consecutive_failures = 0
            integration.last_test_result = "success"
            await db.commit()
            return True
        except Exception as e:
            logger.error(f"[CustomRestAdapter] Request failed: {e}")
            integration.consecutive_failures += 1
            if integration.consecutive_failures >= 5:
                integration.status = "paused"
                logger.error(f"[CustomRestAdapter] Auto-pausing integration {self.channel_name} after 5 failures. Sending alert.")
            integration.last_test_result = f"error: {str(e)}"
            await db.commit()
            return False

def get_adapter(channel: str) -> OutreachAdapter:
    adapters: dict[str, type[OutreachAdapter]] = {
        "email": EmailAdapter,
        "sms": SmsAdapter,
        "slack": SlackAdapter,
        "in_app": InAppAdapter,
    }
    adapter_cls = adapters.get(channel.lower())
    if adapter_cls:
        return adapter_cls()
    
    # If not built-in, assume it's a CustomIntegration channel name
    return CustomRestAdapter(channel_name=channel)

