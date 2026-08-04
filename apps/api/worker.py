import uuid
import logging
import sqlalchemy
import os
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
from apps.api.core.queue import publish_churn_update
from opentelemetry import trace
from apps.api.core.observability import setup_observability

logger = logging.getLogger(__name__)

async def startup(ctx):
    setup_observability()
    ctx["tracer"] = trace.get_tracer(__name__)

from apps.api.models import Customer, CustomerEvent, Tenant, HealthScoreConfig, HealthScore
from apps.api.core.ml.predict import predict_churn
from apps.api.core.ml.expansion import predict_expansion
from apps.api.core.ml.health import compute_health_score

async def batch_score_churn(ctx):
    """
    Nightly unified batch job to compute churn risk, expansion signal, and composite health score for all active customers in a single pass.
    """
    tracer = ctx.get("tracer", trace.get_tracer(__name__))
    with tracer.start_as_current_span("batch_score_all"):
        logger.info("Running nightly unified batch scoring job...")
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
                    
                # Fetch tenant HealthScoreConfig
                cfg_res = await session.execute(
                    sqlalchemy.select(HealthScoreConfig).where(HealthScoreConfig.tenant_id == tenant_id)
                )
                cfg = cfg_res.scalars().first()
                weights = {
                    "churn_weight": cfg.churn_weight if cfg else 0.35,
                    "usage_trend_weight": cfg.usage_trend_weight if cfg else 0.25,
                    "payment_health_weight": cfg.payment_health_weight if cfg else 0.20,
                    "support_sentiment_weight": cfg.support_sentiment_weight if cfg else 0.0,
                    "engagement_recency_weight": cfg.engagement_recency_weight if cfg else 0.20,
                }

                customers_res = await session.execute(
                    sqlalchemy.select(Customer).where(Customer.tenant_id == tenant_id)
                )
                customers = {str(c.id): c for c in customers_res.scalars().all()}
                
                for _, row in df_features.iterrows():
                    c_id = str(row["customer_id"])
                    if c_id not in customers:
                        continue
                        
                    feature_dict = row.drop("customer_id").to_dict()
                    
                    # 1. Churn Prediction
                    try:
                        churn_proba, tier, churn_version, _ = predict_churn(feature_dict)
                    except Exception:
                        churn_proba, tier, churn_version = 0.1, "low", "xgboost_v1"

                    # 2. Expansion Prediction
                    try:
                        exp_proba, _, _ = predict_expansion(feature_dict)
                    except Exception:
                        exp_proba = 0.1

                    # 3. Composite Health Score Calculation
                    h_score, breakdown = compute_health_score(churn_proba, feature_dict, weights)

                    # Update Customer record
                    c = customers[c_id]
                    c.churn_probability = churn_proba
                    c.churn_risk_tier = tier
                    c.churn_model_version = churn_version
                    c.churn_computed_at = now

                    c.expansion_probability = exp_proba
                    c.expansion_model_version = "xgboost_expansion_v1"
                    c.expansion_computed_at = now

                    c.health_score = h_score
                    c.health_score_computed_at = now

                    # Save versioned HealthScore record
                    hs_record = HealthScore(
                        tenant_id=tenant_id,
                        customer_id=c.id,
                        as_of_date=now,
                        score=h_score,
                        components=breakdown,
                        version="v1"
                    )
                    session.add(hs_record)

                    await publish_churn_update(str(tenant_id), c_id, churn_proba, tier)
                    
                await session.commit()
                
        logger.info("Finished unified batch scoring job.")

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

from apps.api.core.outreach.engine import evaluate_campaigns
from apps.api.core.analytics.outcomes import track_intervention_outcomes
from apps.api.core.analytics.roi import calculate_roi
from datetime import timedelta

async def run_campaign_evaluations(ctx):
    """
    Cron job to evaluate campaign trigger rules for active tenants and dispatch interventions.
    """
    logger.info("Running run_campaign_evaluations job...")
    async with AsyncSessionLocal() as session:
        # Get all distinct active tenants
        tenants_res = await session.execute(sqlalchemy.select(Tenant.id).where(Tenant.is_active == True))
        tenant_ids = tenants_res.scalars().all()
        
        for tenant_id in tenant_ids:
            logger.info(f"Evaluating campaigns for tenant {tenant_id}")
            # Enable RLS
            await session.execute(sqlalchemy.text(f"SET LOCAL app.current_tenant = '{tenant_id}'"))
            await evaluate_campaigns(session, tenant_id)
            
    logger.info("Finished run_campaign_evaluations job.")

async def run_outcome_tracking(ctx):
    """
    Cron job to evaluate outcomes of pending interventions.
    """
    logger.info("Running run_outcome_tracking job...")
    async with AsyncSessionLocal() as session:
        tenants_res = await session.execute(sqlalchemy.select(Tenant.id).where(Tenant.is_active == True))
        tenant_ids = tenants_res.scalars().all()
        for tenant_id in tenant_ids:
            # Enable RLS
            await session.execute(sqlalchemy.text(f"SET LOCAL app.current_tenant = '{tenant_id}'"))
            await track_intervention_outcomes(session, str(tenant_id), evaluation_days=30)
    logger.info("Finished run_outcome_tracking job.")

async def generate_weekly_roi_reports(ctx):
    """
    Cron job to generate ROI reports weekly.
    """
    logger.info("Running generate_weekly_roi_reports job...")
    now = datetime.now(timezone.utc)
    start_date = now - timedelta(days=7)
    
    async with AsyncSessionLocal() as session:
        tenants_res = await session.execute(sqlalchemy.select(Tenant.id).where(Tenant.is_active == True))
        tenant_ids = tenants_res.scalars().all()
        for tenant_id in tenant_ids:
            # Enable RLS
            await session.execute(sqlalchemy.text(f"SET LOCAL app.current_tenant = '{tenant_id}'"))
            await calculate_roi(session, str(tenant_id), start_date, now)
    logger.info("Finished generate_weekly_roi_reports job.")

class WorkerSettings:
    functions = [process_webhook]
    cron_jobs = [
        cron(batch_score_churn, hour=2, minute=0),
        cron(run_campaign_evaluations, hour=3, minute=0),
        cron(run_outcome_tracking, hour=4, minute=0),
        # Run ROI calculation every Monday (weekday=0) at 5 AM
        cron(generate_weekly_roi_reports, weekday={0}, hour=5, minute=0)
    ]
    redis_settings = get_redis_settings()
