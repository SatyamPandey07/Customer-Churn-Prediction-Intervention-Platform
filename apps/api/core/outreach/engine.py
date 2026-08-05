import logging
import uuid
from datetime import UTC, datetime, timedelta

from apps.api.core.ml.interventions import generate_intervention
from apps.api.core.ml.predict import predict_churn
from apps.api.core.outreach.adapters import get_adapter
from apps.api.models import Campaign, ChurnFeature, Customer, Intervention
from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)

async def evaluate_campaigns(db: AsyncSession, tenant_id: uuid.UUID):
    # Get active campaigns for the tenant
    result = await db.execute(
        select(Campaign).where(
            and_(Campaign.tenant_id == tenant_id, Campaign.status == "active")
        )
    )
    campaigns = result.scalars().all()

    for campaign in campaigns:
        await _evaluate_single_campaign(db, tenant_id, campaign)

async def _evaluate_single_campaign(db: AsyncSession, tenant_id: uuid.UUID, campaign: Campaign):
    # Parse trigger_rule
    # e.g., {"risk_tier": "critical", "mrr_gt": 500}
    # For robust matching, we support risk_tier (string or list) and mrr_gt
    rule = campaign.trigger_rule or {}
    
    query = select(Customer).where(Customer.tenant_id == tenant_id)
    
    if "risk_tier" in rule:
        rt = rule["risk_tier"]
        if isinstance(rt, list):
            query = query.where(Customer.churn_risk_tier.in_(rt))
        else:
            query = query.where(Customer.churn_risk_tier == rt)
            
    if "mrr_gt" in rule:
        query = query.where(Customer.mrr > rule["mrr_gt"])

    if "anomaly_type" in rule:
        from apps.api.models import AnomalyEvent
        target_type = rule["anomaly_type"]
        target_sev = rule.get("severity")

        subq = select(AnomalyEvent.customer_id).where(
            and_(
                AnomalyEvent.tenant_id == tenant_id,
                AnomalyEvent.anomaly_type == target_type,
                AnomalyEvent.resolved == False
            )
        )
        if target_sev:
            subq = subq.where(AnomalyEvent.severity == target_sev)

        res_ids = await db.execute(subq)
        anomaly_cids = res_ids.scalars().all()
        query = query.where(Customer.id.in_(anomaly_cids))

    result = await db.execute(query)

    customers = result.scalars().all()

    cooldown_days = 14
    cutoff_date = datetime.now(UTC) - timedelta(days=cooldown_days)

    for customer in customers:
        # Check cooldown
        recent_interventions = await db.execute(
            select(Intervention).where(
                and_(
                    Intervention.tenant_id == tenant_id,
                    Intervention.customer_id == customer.id,
                    Intervention.campaign_id == campaign.id,
                    Intervention.sent_at >= cutoff_date
                )
            )
        )
        if recent_interventions.scalars().first():
            continue # Cooldown active

        # Fetch SHAP drivers to get the AI recommendation (if needed for template)
        # We can just call predict_churn which calculates SHAP under the hood, 
        # or we just use the latest features.
        # For simplicity, if template needs AI copy, we fetch it.
        ai_copy = ""
        template = campaign.template or "{ai_copy}"
        if "{ai_copy}" in template or "{rationale}" in template:
            # Need to get drivers. Get the latest feature row.
            feat_res = await db.execute(
                select(ChurnFeature).where(
                    and_(ChurnFeature.tenant_id == tenant_id, ChurnFeature.customer_id == customer.id)
                ).order_by(ChurnFeature.as_of_date.desc()).limit(1)
            )
            cf = feat_res.scalars().first()
            if cf:
                # Calculate SHAP and get intervention
                prob, risk, drivers, mv = predict_churn(cf.features)
                customer_meta = {"mrr": customer.mrr, "plan": customer.plan}
                ai_resp = await generate_intervention(
                    str(customer.id), prob, risk, drivers, customer_meta, cf.feature_set_version, mv
                )
                
                # Find matching intervention type, or use first
                intervention_item = next((i for i in ai_resp.recommended_interventions if i.type == campaign.intervention_type), None)
                if not intervention_item and ai_resp.recommended_interventions:
                    intervention_item = ai_resp.recommended_interventions[0]
                    
                if intervention_item:
                    ai_copy = intervention_item.suggested_copy
                    if "{rationale}" in template:
                        template = template.replace("{rationale}", intervention_item.rationale)
        
        # Render message
        message = template.replace("{ai_copy}", ai_copy).replace("{customer_id}", str(customer.id))
        
        # Dispatch
        adapter = get_adapter(campaign.channel)
        
        # Create pending intervention
        intervention = Intervention(
            id=uuid.uuid4(),
            tenant_id=tenant_id,
            customer_id=customer.id,
            campaign_id=campaign.id,
            channel=campaign.channel,
            status="pending"
        )
        db.add(intervention)
        
        try:
            success = await adapter.send(db, customer, message)
            intervention.status = "sent" if success else "failed"
            intervention.sent_at = datetime.now(UTC)
        except Exception as e:
            logger.error(f"Failed to send intervention via {campaign.channel}: {e}")
            intervention.status = "failed"
            
        await db.commit()
