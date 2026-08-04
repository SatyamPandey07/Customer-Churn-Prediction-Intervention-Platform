import uuid
import logging
from typing import Dict, Any, List
from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession

from apps.api.models import Customer, HealthScore

logger = logging.getLogger(__name__)

async def get_cohort_breakdown(
    db: AsyncSession,
    tenant_id: uuid.UUID,
    dimension: str = "plan_tier"
) -> List[Dict[str, Any]]:
    """
    Computes cohort/segment breakdown metrics across 4 dimensions:
    - plan_tier (or plan)
    - signup_month (YYYY-MM)
    - industry
    - acquisition_channel (or channel)
    """
    import sqlalchemy
    await db.execute(sqlalchemy.text(f"SET LOCAL app.current_tenant = '{tenant_id}'"))

    res = await db.execute(select(Customer).where(Customer.tenant_id == tenant_id))
    customers = res.scalars().all()

    groups: Dict[str, List[Customer]] = {}

    for c in customers:
        if dimension in ["plan_tier", "plan"]:
            val = c.plan or "Standard"
        elif dimension == "signup_month":
            if c.signup_month:
                val = c.signup_month
            elif c.first_seen_at:
                val = c.first_seen_at.strftime("%Y-%m")
            else:
                val = "Unknown"
        elif dimension == "industry":
            val = c.industry or "Unspecified"
        elif dimension in ["channel", "acquisition_channel"]:
            val = c.acquisition_channel or "Direct"
        else:
            val = c.plan or "Standard"

        groups.setdefault(val, []).append(c)

    results = []
    for grp_val, cust_list in groups.items():
        total_cnt = len(cust_list)
        high_risk_cnt = 0
        total_revenue_at_risk = 0.0
        health_scores = []

        for c in cust_list:
            prob = float(c.churn_probability or 0.0)
            mrr = float(c.mrr or 0.0)
            if prob >= 0.5 or c.churn_risk_tier == "critical":
                high_risk_cnt += 1

            total_revenue_at_risk += (mrr * prob)
            if c.health_score is not None:
                health_scores.append(float(c.health_score))

        churn_rate = round((high_risk_cnt / total_cnt) * 100.0, 2) if total_cnt > 0 else 0.0
        avg_health = round(sum(health_scores) / len(health_scores), 2) if health_scores else 50.0

        results.append({
            "dimension": dimension,
            "dimension_value": grp_val,
            "customer_count": total_cnt,
            "high_risk_count": high_risk_cnt,
            "churn_rate": churn_rate,
            "avg_health_score": avg_health,
            "revenue_at_risk": round(total_revenue_at_risk, 2)
        })

    # Sort by customer count descending
    results.sort(key=lambda x: x["customer_count"], reverse=True)
    return results
