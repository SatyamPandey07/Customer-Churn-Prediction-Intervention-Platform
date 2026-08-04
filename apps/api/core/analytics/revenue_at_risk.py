import math
import uuid
import logging
from typing import Dict, Any, List
from datetime import datetime, timezone, timedelta
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from apps.api.models import Customer, RevenueAtRiskAlertConfig
from apps.api.core.outreach.adapters import get_adapter

logger = logging.getLogger(__name__)

METHODOLOGY_NOTE = (
    "Expected-value estimate calculated as sum(MRR * churn_probability * (horizon_days / 30)). "
    "This is a probabilistic forecast, not a guaranteed financial loss."
)

def compute_revenue_at_risk_metrics(customers: List[Customer], horizon_days: int = 90) -> Dict[str, Any]:
    """
    Computes expected revenue loss, variance/confidence interval, segment breakdown,
    and top exposure accounts across given customer list.
    """
    horizon_days = int(horizon_days)
    scale = horizon_days / 30.0

    total_expected_loss = 0.0
    total_mrr = 0.0
    total_variance = 0.0

    plan_groups: Dict[str, Dict[str, Any]] = {}
    cohort_groups: Dict[str, Dict[str, Any]] = {}
    exposure_list = []

    for c in customers:
        mrr = float(c.mrr or 0.0)
        p = float(c.churn_probability or 0.0)
        p = max(0.0, min(1.0, p))

        total_mrr += mrr
        customer_scaled_mrr = mrr * scale
        exp_loss = customer_scaled_mrr * p
        total_expected_loss += exp_loss

        # Variance under binomial independence
        variance = (customer_scaled_mrr ** 2) * p * (1.0 - p)
        total_variance += variance

        # Plan Grouping
        plan_name = c.plan or "standard"
        if plan_name not in plan_groups:
            plan_groups[plan_name] = {
                "segment_type": "plan",
                "segment_name": plan_name,
                "customer_count": 0,
                "total_mrr": 0.0,
                "expected_revenue_at_risk": 0.0
            }
        plan_groups[plan_name]["customer_count"] += 1
        plan_groups[plan_name]["total_mrr"] += mrr
        plan_groups[plan_name]["expected_revenue_at_risk"] += exp_loss

        # Cohort Grouping (Signup month YYYY-MM)
        cohort_name = c.created_at.strftime("%Y-%m") if c.created_at else "unknown"
        if cohort_name not in cohort_groups:
            cohort_groups[cohort_name] = {
                "segment_type": "cohort",
                "segment_name": cohort_name,
                "customer_count": 0,
                "total_mrr": 0.0,
                "expected_revenue_at_risk": 0.0
            }
        cohort_groups[cohort_name]["customer_count"] += 1
        cohort_groups[cohort_name]["total_mrr"] += mrr
        cohort_groups[cohort_name]["expected_revenue_at_risk"] += exp_loss

        # Exposure Account item
        exposure_list.append({
            "customer_id": str(c.id),
            "external_id": str(c.external_ids or {}),
            "plan": plan_name,
            "mrr": round(mrr, 2),
            "churn_probability": round(p, 4),
            "dollar_exposure": round(exp_loss, 2)
        })

    # Standard error and 95% Confidence Band
    std_err = math.sqrt(total_variance)
    lower_95 = max(0.0, total_expected_loss - (1.96 * std_err))
    upper_95 = total_expected_loss + (1.96 * std_err)

    # Sort exposure accounts
    top_10_exposure = sorted(exposure_list, key=lambda x: x["dollar_exposure"], reverse=True)[:10]

    # Format segment lists
    by_plan = [
        {
            **v,
            "total_mrr": round(v["total_mrr"], 2),
            "expected_revenue_at_risk": round(v["expected_revenue_at_risk"], 2)
        }
        for v in plan_groups.values()
    ]
    by_cohort = [
        {
            **v,
            "total_mrr": round(v["total_mrr"], 2),
            "expected_revenue_at_risk": round(v["expected_revenue_at_risk"], 2)
        }
        for v in cohort_groups.values()
    ]

    return {
        "horizon_days": horizon_days,
        "total_expected_loss": round(total_expected_loss, 2),
        "total_mrr": round(total_mrr, 2),
        "methodology": METHODOLOGY_NOTE,
        "confidence_band": {
            "lower_95": round(lower_95, 2),
            "upper_95": round(upper_95, 2),
            "standard_error": round(std_err, 2),
            "method": "Binomial variance standard error"
        },
        "by_segment": {
            "by_plan": sorted(by_plan, key=lambda x: x["expected_revenue_at_risk"], reverse=True),
            "by_cohort": sorted(by_cohort, key=lambda x: x["segment_name"])
        },
        "top_10_accounts_by_dollar_exposure": top_10_exposure
    }

async def calculate_tenant_revenue_at_risk(db: AsyncSession, tenant_id: uuid.UUID, horizon_days: int = 90) -> Dict[str, Any]:
    res = await db.execute(
        select(Customer).where(Customer.tenant_id == tenant_id)
    )
    customers = res.scalars().all()
    metrics = compute_revenue_at_risk_metrics(customers, horizon_days=horizon_days)
    metrics["tenant_id"] = str(tenant_id)
    return metrics

async def evaluate_revenue_at_risk_alert(db: AsyncSession, tenant_id: uuid.UUID, current_rar_90d: float) -> bool:
    res = await db.execute(
        select(RevenueAtRiskAlertConfig).where(RevenueAtRiskAlertConfig.tenant_id == tenant_id)
    )
    config = res.scalars().first()
    if not config or not config.enabled:
        return False

    if current_rar_90d >= config.threshold_amount:
        now = datetime.now(timezone.utc)
        if config.last_alerted_at is None or (now - config.last_alerted_at) > timedelta(hours=24):
            adapter = get_adapter(config.channel or "slack")
            # Fetch a sample customer or send tenant-wide alert
            res_c = await db.execute(select(Customer).where(Customer.tenant_id == tenant_id).limit(1))
            sample_c = res_c.scalars().first()
            if not sample_c:
                sample_c = Customer(id=uuid.uuid4(), tenant_id=tenant_id, external_ids={"slack": "C123456"})

            msg = (
                f"🚨 [Revenue-at-Risk Alert] Tenant 90-day expected revenue at risk is "
                f"${current_rar_90d:,.2f}, breaching threshold of ${config.threshold_amount:,.2f}."
            )
            await adapter.send(db, sample_c, msg)
            config.last_alerted_at = now
            await db.commit()
            return True

    return False
