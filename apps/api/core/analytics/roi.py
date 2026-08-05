import logging
import uuid
from datetime import datetime

from apps.api.models import Customer, Intervention, InterventionOutcome, RoiReport, Tenant
from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)

async def calculate_roi(db: AsyncSession, tenant_id: str, start_date: datetime, end_date: datetime) -> RoiReport:
    """
    Calculates ROI based on retained high-risk customers who received interventions.
    """
    
    # Simple methodology: High-risk customers who received an intervention and were retained.
    # Without an A/B test control group, we assume a simple counterfactual: 
    # e.g., 50% of these high-risk customers would have churned anyway.
    
    stmt = select(Intervention, Customer).join(Customer).where(
        and_(
            Intervention.tenant_id == tenant_id,
            Intervention.outcome == InterventionOutcome.retained,
            Intervention.outcome_recorded_at >= start_date,
            Intervention.outcome_recorded_at <= end_date,
            Customer.churn_risk_tier.in_(["high", "critical"])
        )
    )
    result = await db.execute(stmt)
    retained_high_risk = result.all()

    # The fallback methodology
    assumed_natural_retention_rate = 0.5 
    # So the counterfactual is that we prevented churn for the other 50%
    
    churn_events_prevented = len(retained_high_risk) * (1.0 - assumed_natural_retention_rate)
    
    revenue_saved = 0.0
    for intervention, customer in retained_high_risk:
        revenue_saved += (customer.mrr or 0.0) * (1.0 - assumed_natural_retention_rate)
        
    # Get Tenant to determine plan cost
    tenant_stmt = select(Tenant).where(Tenant.id == tenant_id)
    tenant = (await db.execute(tenant_stmt)).scalars().first()
    
    plan_cost = 0.0
    if tenant:
        # We assume monthly price for ROI comparison based on plan_tier enum
        if tenant.plan_tier.value == "tier1":
            plan_cost = 100.0
        elif tenant.plan_tier.value == "tier2":
            plan_cost = 500.0
        elif tenant.plan_tier.value == "tier3":
            plan_cost = 1000.0
            
    roi_multiple = 0.0
    if plan_cost > 0:
        roi_multiple = revenue_saved / plan_cost
        
    report = RoiReport(
        id=uuid.uuid4(),
        tenant_id=tenant_id,
        period_start=start_date,
        period_end=end_date,
        churn_events_prevented=churn_events_prevented,
        revenue_saved=revenue_saved,
        roi_multiple=roi_multiple,
        methodology="Simple Estimate: Assumes 50% of retained high-risk customers would have churned without intervention."
    )
    
    db.add(report)
    await db.commit()
    await db.refresh(report)
    
    return report
