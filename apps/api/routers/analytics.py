from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, func, case, Integer
from apps.api.core.deps import get_db, require_role
from apps.api.models import User, Intervention, InterventionOutcome, Campaign, RoiReport, Role
from typing import Dict, Any, List
import math

router = APIRouter(prefix="/analytics", tags=["analytics"])

def wilson_score_interval(successes: int, n: int, z: float = 1.96) -> tuple[float, float]:
    """Calculate the Wilson score interval for a binomial proportion."""
    if n == 0:
        return 0.0, 0.0
    p = successes / n
    denominator = 1 + z**2 / n
    centre_adjusted_probability = p + z**2 / (2 * n)
    adjusted_standard_deviation = math.sqrt((p * (1 - p) + z**2 / (4 * n)) / n)
    
    lower_bound = (centre_adjusted_probability - z * adjusted_standard_deviation) / denominator
    upper_bound = (centre_adjusted_probability + z * adjusted_standard_deviation) / denominator
    
    return max(0.0, lower_bound), min(1.0, upper_bound)

@router.get("/intervention-performance", dependencies=[Depends(require_role([Role.owner, Role.admin, Role.analyst, Role.viewer]))])
async def get_intervention_performance(
    db: AsyncSession = Depends(get_db),
    user: dict = Depends(require_role([Role.owner, Role.admin, Role.analyst, Role.viewer]))
) -> Dict[str, Any]:
    
    tenant_id = user["tenant_id"]
    
    # We want to group by intervention_type, channel, variant_group_id
    # We need to join Intervention with Campaign to get intervention_type and variant_group_id
    
    stmt = select(
        Campaign.intervention_type,
        Campaign.variant_group_id,
        Intervention.channel,
        func.count(Intervention.id).label("total"),
        func.sum(
            case(
                (Intervention.outcome == InterventionOutcome.retained, 1), 
                else_=0
            )
        ).cast(Integer).label("retained")
    ).outerjoin(Campaign, Intervention.campaign_id == Campaign.id).where(
        and_(
            Intervention.tenant_id == tenant_id,
            Intervention.outcome.in_([InterventionOutcome.retained, InterventionOutcome.churned])
        )
    ).group_by(
        Campaign.intervention_type,
        Campaign.variant_group_id,
        Intervention.channel
    )
    
    result = await db.execute(stmt)
    rows = result.all()
    
    performance_data = []
    for row in rows:
        total = row.total
        retained = row.retained or 0
        success_rate = retained / total if total > 0 else 0.0
        
        lower_bound, upper_bound = wilson_score_interval(retained, total)
        
        performance_data.append({
            "intervention_type": row.intervention_type or "manual",
            "variant_group_id": row.variant_group_id,
            "channel": row.channel,
            "total_evaluated": total,
            "retained": retained,
            "success_rate": success_rate,
            "confidence_interval_95": {
                "lower": lower_bound,
                "upper": upper_bound
            }
        })
        
    return {"performance": performance_data}

@router.get("/roi-report", dependencies=[Depends(require_role([Role.owner, Role.admin, Role.analyst]))])
async def get_roi_report(
    db: AsyncSession = Depends(get_db),
    user: dict = Depends(require_role([Role.owner, Role.admin, Role.analyst]))
) -> Dict[str, Any]:
    
    tenant_id = user["tenant_id"]
    
    # Get the latest ROI report for the tenant
    stmt = select(RoiReport).where(
        RoiReport.tenant_id == tenant_id
    ).order_by(RoiReport.created_at.desc()).limit(1)
    
    result = await db.execute(stmt)
    report = result.scalars().first()
    
    if not report:
        raise HTTPException(status_code=404, detail="No ROI report generated yet.")
        
    return {
        "id": report.id,
        "period_start": report.period_start,
        "period_end": report.period_end,
        "churn_events_prevented": report.churn_events_prevented,
        "revenue_saved": report.revenue_saved,
        "roi_multiple": report.roi_multiple,
        "methodology": report.methodology,
        "generated_at": report.created_at
    }
