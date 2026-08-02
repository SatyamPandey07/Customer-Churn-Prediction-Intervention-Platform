import uuid
import logging
import sqlalchemy
from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from apps.api.core.deps import AsyncSessionLocal
from apps.api.core.ingestion.adapters import get_adapter
from apps.api.core.queue import get_redis_settings
from apps.api.models import Customer, CustomerEvent

logger = logging.getLogger(__name__)

async def process_webhook(ctx, tenant_id: str, source: str, payload: dict):
    adapter = get_adapter(source)
    if not adapter:
        logger.error(f"Unknown source adapter: {source}")
        return

    events = adapter.normalize_payload(payload)
    if not events:
        logger.warning(f"No events extracted for {source} payload.")
        return

    async with AsyncSessionLocal() as session:
        # Set tenant for RLS
        await session.execute(
            sqlalchemy.text(f"SET LOCAL app.current_tenant = '{tenant_id}'")
        )

        for event in events:
            # Upsert Customer
            stmt = select(Customer).where(
                Customer.tenant_id == uuid.UUID(tenant_id),
                Customer.external_ids.op("->>")(source) == event.external_customer_id
            )
            result = await session.execute(stmt)
            customer = result.scalars().first()
            
            if not customer:
                customer = Customer(
                    tenant_id=uuid.UUID(tenant_id),
                    external_ids={source: event.external_customer_id},
                    first_seen_at=event.occurred_at,
                    last_seen_at=event.occurred_at
                )
                session.add(customer)
                await session.flush()
            else:
                if customer.last_seen_at is None or event.occurred_at > customer.last_seen_at:
                    customer.last_seen_at = event.occurred_at
                
                # Assuming simple MRR updates via event properties
                # (For real implementation, you'd calculate this specifically)
                mrr = event.properties.get("mrr")
                if mrr is not None:
                    customer.mrr = mrr
                    
                plan = event.properties.get("plan")
                if plan is not None:
                    customer.plan = plan
                
                await session.flush()
                
            # Insert Event with ON CONFLICT DO NOTHING (Idempotency)
            stmt_insert_event = pg_insert(CustomerEvent).values(
                id=uuid.uuid4(),
                tenant_id=uuid.UUID(tenant_id),
                customer_id=customer.id,
                source=event.source,
                external_event_id=event.external_event_id,
                event_type=event.event_type,
                properties=event.properties,
                occurred_at=event.occurred_at
            ).on_conflict_do_nothing(
                index_elements=['tenant_id', 'source', 'external_event_id']
            )
            
            await session.execute(stmt_insert_event)
        
        await session.commit()

class WorkerSettings:
    functions = [process_webhook]
    redis_settings = get_redis_settings()
    
