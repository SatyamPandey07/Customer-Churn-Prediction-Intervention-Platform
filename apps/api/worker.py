import uuid
import logging
import sqlalchemy
from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from apps.api.core.deps import AsyncSessionLocal
from apps.api.core.ingestion.adapters import get_adapter
from apps.api.core.queue import get_redis_settings
from arq.cron import cron
from datetime import datetime, timezone
from apps.api.models import Customer, CustomerEvent, Tenant
from apps.api.core.ml.predict import predict_churn
from apps.api.core.ml.features import extract_features

logger = logging.getLogger(__name__)

async def batch_score_churn(ctx):
    """
    Nightly batch job to compute churn risk for all active customers.
    """
    logger.info("Running nightly batch_score_churn job...")
    now = datetime.now(timezone.utc)
    
    async with AsyncSessionLocal() as session:
        # Get all distinct active tenants
        tenants_res = await session.execute(sqlalchemy.select(Tenant.id).where(Tenant.is_active == True))
        tenant_ids = tenants_res.scalars().all()
        
        for tenant_id in tenant_ids:
            logger.info(f"Processing tenant {tenant_id}")
            # Enable RLS
            await session.execute(sqlalchemy.text(f"SET LOCAL app.current_tenant = '{tenant_id}'"))
            
            df_features = await extract_features(session, tenant_id, now)
            if df_features.empty:
                continue
                
            customers_res = await session.execute(
                sqlalchemy.select(Customer).where(Customer.tenant_id == tenant_id)
            )
            customers = {str(c.id): c for c in customers_res.scalars().all()}
            
            for _, row in df_features.iterrows():
                c_id = str(row["customer_id"])
                if c_id not in customers:
                    continue
                    
                feature_dict = row.drop("customer_id").to_dict()
                try:
                    proba, tier, model_version = predict_churn(feature_dict)
                except RuntimeError as e:
                    logger.error(f"Prediction failed: {e}")
                    continue
                    
                c = customers[c_id]
                c.churn_probability = proba
                c.churn_risk_tier = tier
                c.churn_model_version = model_version
                c.churn_computed_at = now
                
            await session.commit()
            
    logger.info("Finished batch_score_churn job.")

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
    cron_jobs = [
        cron(batch_score_churn, hour=2, minute=0)
    ]
    redis_settings = get_redis_settings()
    
