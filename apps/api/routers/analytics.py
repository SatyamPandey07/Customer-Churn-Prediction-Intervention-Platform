import math
from typing import Any

from apps.api.core.deps import get_db, require_role
from apps.api.models import Campaign, Intervention, InterventionOutcome, RoiReport, Role
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import Integer, and_, case, func, select
from sqlalchemy.ext.asyncio import AsyncSession

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
) -> dict[str, Any]:
    
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
) -> dict[str, Any]:
    
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

import uuid
from datetime import UTC, datetime

from apps.api.core.analytics.revenue_at_risk import calculate_tenant_revenue_at_risk
from apps.api.models import RevenueAtRiskAlertConfig, RevenueAtRiskSnapshot
from pydantic import BaseModel, Field


class RevenueAtRiskAlertConfigSchema(BaseModel):
    threshold_amount: float = Field(..., ge=0.0)
    channel: str = "slack"
    enabled: bool = True

@router.get("/tenants/{tenant_id}/analytics/revenue-at-risk")
async def get_revenue_at_risk(
    tenant_id: uuid.UUID,
    horizon_days: int = Query(90, enum=[30, 60, 90]),
    db: AsyncSession = Depends(get_db),
    user: dict = Depends(require_role([Role.owner, Role.admin, Role.analyst, Role.viewer]))
):
    user_tenant_id = uuid.UUID(str(user["tenant_id"]))
    if user_tenant_id != tenant_id:
        raise HTTPException(status_code=403, detail="Not authorized for this tenant")

    metrics = await calculate_tenant_revenue_at_risk(db, tenant_id, horizon_days=horizon_days)
    return metrics

@router.get("/tenants/{tenant_id}/analytics/revenue-at-risk-snapshots")
async def get_revenue_at_risk_snapshots(
    tenant_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    user: dict = Depends(require_role([Role.owner, Role.admin, Role.analyst, Role.viewer]))
):
    user_tenant_id = uuid.UUID(str(user["tenant_id"]))
    if user_tenant_id != tenant_id:
        raise HTTPException(status_code=403, detail="Not authorized for this tenant")

    stmt = select(RevenueAtRiskSnapshot).where(
        RevenueAtRiskSnapshot.tenant_id == tenant_id
    ).order_by(RevenueAtRiskSnapshot.as_of_date.asc())

    res = await db.execute(stmt)
    snapshots = res.scalars().all()
    return [
        {
            "id": str(s.id),
            "as_of_date": s.as_of_date.strftime("%Y-%m-%d") if hasattr(s.as_of_date, "strftime") else str(s.as_of_date),
            "horizon_30d_expected_loss": s.horizon_30d_expected_loss,
            "horizon_60d_expected_loss": s.horizon_60d_expected_loss,
            "horizon_90d_expected_loss": s.horizon_90d_expected_loss,
            "by_plan_breakdown": s.by_plan_breakdown,
            "by_cohort_breakdown": s.by_cohort_breakdown
        }
        for s in snapshots
    ]

@router.get("/tenants/{tenant_id}/analytics/revenue-at-risk-config", response_model=RevenueAtRiskAlertConfigSchema)
async def get_revenue_at_risk_config(
    tenant_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    user: dict = Depends(require_role([Role.owner, Role.admin, Role.analyst]))
):
    user_tenant_id = uuid.UUID(str(user["tenant_id"]))
    if user_tenant_id != tenant_id:
        raise HTTPException(status_code=403, detail="Not authorized for this tenant")

    res = await db.execute(select(RevenueAtRiskAlertConfig).where(RevenueAtRiskAlertConfig.tenant_id == tenant_id))
    config = res.scalars().first()
    if not config:
        return RevenueAtRiskAlertConfigSchema(threshold_amount=10000.0, channel="slack", enabled=True)
    return RevenueAtRiskAlertConfigSchema(
        threshold_amount=config.threshold_amount,
        channel=config.channel,
        enabled=config.enabled
    )

@router.put("/tenants/{tenant_id}/analytics/revenue-at-risk-config", response_model=RevenueAtRiskAlertConfigSchema)
async def update_revenue_at_risk_config(
    tenant_id: uuid.UUID,
    payload: RevenueAtRiskAlertConfigSchema,
    db: AsyncSession = Depends(get_db),
    user: dict = Depends(require_role([Role.owner, Role.admin]))
):
    user_tenant_id = uuid.UUID(str(user["tenant_id"]))
    if user_tenant_id != tenant_id:
        raise HTTPException(status_code=403, detail="Not authorized for this tenant")

    res = await db.execute(select(RevenueAtRiskAlertConfig).where(RevenueAtRiskAlertConfig.tenant_id == tenant_id))
    config = res.scalars().first()
    if not config:
        config = RevenueAtRiskAlertConfig(
            tenant_id=tenant_id,
            threshold_amount=payload.threshold_amount,
            channel=payload.channel,
            enabled=payload.enabled,
            updated_at=datetime.now(UTC)
        )
        db.add(config)
    else:
        config.threshold_amount = payload.threshold_amount
        config.channel = payload.channel
        config.enabled = payload.enabled
        config.updated_at = datetime.now(UTC)

    await db.commit()
    return payload

from apps.api.core.analytics.attribution import get_explanation_validation_report, get_tenant_attribution_report
from apps.api.core.surveys.engine import submit_exit_survey


class SubmitExitSurveyPayload(BaseModel):
    reason_category: str  # price, missing_features, poor_support, usability, competitor, other
    free_text: str | None = None

@router.get("/tenants/{tenant_id}/analytics/attribution")
async def get_attribution_report(
    tenant_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    user: dict = Depends(require_role([Role.owner, Role.admin, Role.analyst, Role.viewer]))
):
    user_tenant_id = uuid.UUID(str(user["tenant_id"]))
    if user_tenant_id != tenant_id:
        raise HTTPException(status_code=403, detail="Not authorized for this tenant")

    report = await get_tenant_attribution_report(db, tenant_id)
    return report

@router.get("/tenants/{tenant_id}/analytics/explanation-validation")
async def get_explanation_validation_report_endpoint(
    tenant_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    user: dict = Depends(require_role([Role.owner, Role.admin, Role.analyst, Role.viewer]))
):
    user_tenant_id = uuid.UUID(str(user["tenant_id"]))
    if user_tenant_id != tenant_id:
        raise HTTPException(status_code=403, detail="Not authorized for this tenant")

    report = await get_explanation_validation_report(db, tenant_id)
    return report

@router.post("/tenants/{tenant_id}/customers/{customer_id}/exit-surveys")
async def record_exit_survey(
    tenant_id: uuid.UUID,
    customer_id: uuid.UUID,
    payload: SubmitExitSurveyPayload,
    db: AsyncSession = Depends(get_db)
):
    survey = await submit_exit_survey(db, tenant_id, customer_id, payload.reason_category, payload.free_text)
    return {
        "id": str(survey.id),
        "customer_id": str(customer_id),
        "reason_category": survey.reason_category,
        "submitted_at": survey.submitted_at.isoformat() if hasattr(survey.submitted_at, "isoformat") else str(survey.submitted_at)
    }


