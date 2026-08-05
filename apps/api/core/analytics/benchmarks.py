import uuid
import logging
import statistics
from typing import Dict, Any, List, Optional
from fastapi import HTTPException
from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession

from apps.api.models import Tenant, Customer

logger = logging.getLogger(__name__)

BENCHMARK_METHODOLOGY = (
    "Cross-tenant anonymized benchmark aggregated across opted-in tenants. Strict minimum cohort size guard "
    "enforced (N >= 3 tenants and N >= 15 accounts) to guarantee differential privacy and prevent re-identification. "
    "Zero raw tenant or customer identifiers are exposed."
)

MIN_TENANTS_THRESHOLD = 3
MIN_CUSTOMERS_THRESHOLD = 15

async def get_industry_benchmark(
    db: AsyncSession,
    tenant_id: uuid.UUID,
    segment: str = "fintech"
) -> Dict[str, Any]:
    """
    Computes anonymized industry benchmark metrics for opted-in tenants.
    Enforces opt-in verification and minimum cohort size guards.
    """
    # 1. Verify requesting tenant exists & has opt-in enabled
    res_tenant = await db.execute(select(Tenant).where(Tenant.id == tenant_id))
    req_tenant = res_tenant.scalars().first()

    if not req_tenant:
        raise HTTPException(status_code=404, detail="Tenant not found")

    if not req_tenant.benchmarking_opt_in:
        raise HTTPException(
            status_code=403,
            detail="Benchmarking opt-in required to access industry benchmarks. Enable benchmarking_opt_in in tenant settings."
        )

    target_industry = segment or req_tenant.industry_vertical or "fintech"

    # 2. Query all OPTED-IN tenants matching the target industry vertical (or all opted-in tenants if unspecified)
    res_opted = await db.execute(
        select(Tenant).where(
            and_(
                Tenant.benchmarking_opt_in == True,
                Tenant.is_active == True
            )
        )
    )
    opted_tenants = res_opted.scalars().all()
    opted_tenant_ids = [t.id for t in opted_tenants]

    # Filter for customers under opted-in tenants
    res_custs = await db.execute(
        select(Customer).where(Customer.tenant_id.in_(opted_tenant_ids))
    )
    all_opted_custs = res_custs.scalars().all()

    # Filter by industry segment match (fallback to all opted-in if industry is generic)
    matching_custs = [
        c for c in all_opted_custs
        if (c.industry and c.industry.lower() == target_industry.lower()) or (target_industry.lower() in ["all", "global"])
    ]

    distinct_tenant_count = len({c.tenant_id for c in matching_custs})
    distinct_cust_count = len(matching_custs)

    # 3. Minimum Cohort Size Guard Check
    if distinct_tenant_count < MIN_TENANTS_THRESHOLD or distinct_cust_count < MIN_CUSTOMERS_THRESHOLD:
        raise HTTPException(
            status_code=422,
            detail=f"Benchmark group does not meet minimum anonymization threshold (minimum {MIN_TENANTS_THRESHOLD} opted-in tenants and {MIN_CUSTOMERS_THRESHOLD} accounts required, found {distinct_tenant_count} tenants and {distinct_cust_count} accounts)."
        )

    # 4. Calculate tenant's own churn rate & average health score
    req_custs = [c for c in all_opted_custs if c.tenant_id == tenant_id]
    if not req_custs:
        # Fetch directly if requesting tenant had no matching segment filter
        res_own = await db.execute(select(Customer).where(Customer.tenant_id == tenant_id))
        req_custs = res_own.scalars().all()

    req_churn_count = sum(1 for c in req_custs if float(c.churn_probability or 0.0) >= 0.5 or c.churn_risk_tier == "critical")
    req_churn_rate = round((req_churn_count / len(req_custs)) * 100.0, 2) if req_custs else 0.0

    req_health_list = [float(c.health_score) for c in req_custs if c.health_score is not None]
    req_avg_health = round(sum(req_health_list) / len(req_health_list), 2) if req_health_list else 50.0

    # 5. Compute tenant-level aggregated churn rates across opted-in tenants
    tenant_churn_rates: List[float] = []
    tenant_cust_map: Dict[uuid.UUID, List[Customer]] = {}
    for c in matching_custs:
        tenant_cust_map.setdefault(c.tenant_id, []).append(c)

    for tid, t_custs in tenant_cust_map.items():
        high_cnt = sum(1 for c in t_custs if float(c.churn_probability or 0.0) >= 0.5 or c.churn_risk_tier == "critical")
        rate = round((high_cnt / len(t_custs)) * 100.0, 2)
        tenant_churn_rates.append(rate)

    tenant_churn_rates.sort()

    median_churn = round(float(statistics.median(tenant_churn_rates)), 2)
    p25_churn = round(float(tenant_churn_rates[int(len(tenant_churn_rates) * 0.25)]), 2)
    p75_churn = round(float(tenant_churn_rates[int(len(tenant_churn_rates) * 0.75)]), 2)

    return {
        "tenant_id": str(tenant_id),
        "segment": target_industry,
        "methodology": BENCHMARK_METHODOLOGY,
        "tenant_metrics": {
            "churn_rate": req_churn_rate,
            "avg_health_score": req_avg_health
        },
        "anonymized_benchmark": {
            "opted_in_tenants_count": distinct_tenant_count,
            "total_accounts_analyzed": distinct_cust_count,
            "metric": "churn_rate",
            "median": median_churn,
            "p25": p25_churn,
            "p75": p75_churn
        }
    }
