import pytest
import uuid
import sqlalchemy
from sqlalchemy import select
from unittest.mock import AsyncMock, patch, MagicMock
from apps.api.models import Customer, CustomerEvent
from apps.api.worker import process_webhook
import contextlib

@pytest.mark.asyncio
async def test_webhook_ingestion_and_idempotency(db_session, client):
    tenant_id = uuid.uuid4()
    
    # Create tenant
    await db_session.execute(
        sqlalchemy.text("INSERT INTO tenants (id, name, subdomain, plan_tier) VALUES (:id, :name, :sub, :tier)"),
        {"id": tenant_id, "name": "Ingest Corp", "sub": "ingest", "tier": "tier1"}
    )
    await db_session.commit()
    
    payload = {
        "id": "evt_12345",
        "type": "invoice.paid",
        "created": 1690000000,
        "data": {
            "object": {
                "customer": "cus_12345",
                "amount_paid": 5000,
                "plan": "premium",
                "mrr": 50.0
            }
        }
    }

    mock_queue = AsyncMock()

    # 1. Test Endpoint
    with patch("apps.api.routers.webhooks.get_queue", return_value=mock_queue):
        response = await client.post(f"/webhooks/{tenant_id}/stripe", json=payload)
    
    assert response.status_code == 202
    mock_queue.enqueue_job.assert_called_once_with("process_webhook", str(tenant_id), "stripe", payload)
    
    # 2. Test Worker Processing
    @contextlib.asynccontextmanager
    async def mock_session_maker():
        yield db_session

    with patch("apps.api.worker.AsyncSessionLocal", new=mock_session_maker):
        # Run worker processing
        await process_webhook(None, str(tenant_id), "stripe", payload)

        # Verify DB records
        await db_session.execute(sqlalchemy.text(f"SET LOCAL app.current_tenant = '{tenant_id}'"))
        
        customer_res = await db_session.execute(select(Customer).where(Customer.tenant_id == tenant_id))
        customer = customer_res.scalars().first()
        assert customer is not None
        assert customer.external_ids["stripe"] == "cus_12345"
        
        event_res = await db_session.execute(select(CustomerEvent).where(CustomerEvent.tenant_id == tenant_id))
        events = event_res.scalars().all()
        assert len(events) == 1
        assert events[0].source == "stripe"
        assert events[0].external_event_id == "evt_12345"

        # 3. Test Idempotency
        # Run worker again with same payload
        await process_webhook(None, str(tenant_id), "stripe", payload)
        
        # Verify NO new events were added
        event_res2 = await db_session.execute(select(CustomerEvent).where(CustomerEvent.tenant_id == tenant_id))
        events2 = event_res2.scalars().all()
        assert len(events2) == 1  # Still 1
