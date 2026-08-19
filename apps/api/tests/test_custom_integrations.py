import pytest
import uuid
from sqlalchemy.ext.asyncio import AsyncSession
from apps.api.models import CustomIntegration, TenantSecret, Customer
from apps.api.core.outreach.adapters import get_adapter, CustomRestAdapter
from apps.api.core.ingestion.adapters.generic import GenericWebhookAdapter

@pytest.mark.asyncio
async def test_custom_inbound_webhook_valid_mapping():
    # Arrange
    adapter = GenericWebhookAdapter(
        source_name="custom_app",
        mapping_rules={"customer_id": "uid", "event_type": "action", "properties": "data"}
    )
    payload = {
        "uid": "cus_123",
        "action": "login",
        "data": {"device": "mobile"}
    }

    # Act
    events = adapter.normalize_payload(payload)

    # Assert
    assert len(events) == 1
    assert events[0].external_customer_id == "cus_123"
    assert events[0].event_type == "login"
    assert events[0].properties == {"device": "mobile"}
    assert events[0].source == "custom_app"

def test_custom_inbound_webhook_malformed():
    adapter = GenericWebhookAdapter(mapping_rules={"customer_id": "uid", "event_type": "action"})
    payload = {"uid": "cus_123"} # missing event_type

    with pytest.raises(ValueError, match="Malformed payload: missing required mapped fields"):
        adapter.normalize_payload(payload)

@pytest.mark.asyncio
async def test_custom_outbound_adapter_auto_pause(mocker, db_session: AsyncSession):
    # Setup mock integration
    tenant_id = uuid.uuid4()
    customer = Customer(id=uuid.uuid4(), tenant_id=tenant_id, external_ids={})
    db_session.add(customer)

    integration = CustomIntegration(
        tenant_id=tenant_id,
        name="internal_webhook",
        integration_type="rest_out",
        config={"base_url": "http://fail.endpoint"},
        consecutive_failures=4,
        status="active"
    )
    db_session.add(integration)
    await db_session.commit()

    # Create adapter
    adapter = get_adapter("internal_webhook")
    assert isinstance(adapter, CustomRestAdapter)

    # Force failure
    mocker.patch('apps.api.core.outreach.adapters.logger.info', side_effect=Exception("Connection Timeout"))
    
    # Act
    success = await adapter.send(db_session, customer, "hello")
    
    # Assert
    assert not success
    await db_session.refresh(integration)
    assert integration.consecutive_failures == 5
    assert integration.status == "paused"
