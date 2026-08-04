import uuid
import logging
from typing import Dict, Any, List, Optional
from datetime import datetime, timezone, timedelta
from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession

from apps.api.models import Contract, Customer

logger = logging.getLogger(__name__)

async def get_renewals_at_risk(
    db: AsyncSession,
    tenant_id: uuid.UUID,
    window_days: int = 90
) -> Dict[str, Any]:
    """
    Returns upcoming contract renewals within window_days, joining renewal timing
    with current customer churn risk probability and health score for CS prioritization.
    """
    import sqlalchemy
    await db.execute(sqlalchemy.text(f"SET LOCAL app.current_tenant = '{tenant_id}'"))

    now = datetime.now(timezone.utc)
    cutoff_date = now + timedelta(days=window_days)

    res_contracts = await db.execute(
        select(Contract).where(
            and_(
                Contract.tenant_id == tenant_id,
                Contract.renewal_date >= now - timedelta(days=1),  # Include today's renewals
                Contract.renewal_date <= cutoff_date
            )
        ).order_by(Contract.renewal_date.asc())
    )
    contracts = res_contracts.scalars().all()

    items = []
    total_mrr_at_risk = 0.0

    for contract in contracts:
        res_cust = await db.execute(
            select(Customer).where(
                and_(
                    Customer.tenant_id == tenant_id,
                    Customer.id == contract.customer_id
                )
            )
        )
        c = res_cust.scalars().first()
        if not c:
            continue

        ren_date = contract.renewal_date
        if ren_date.tzinfo is None:
            ren_date = ren_date.replace(tzinfo=timezone.utc)

        days_until_renewal = max(0, int(round((ren_date - now).total_seconds() / 86400.0)))

        churn_prob = float(c.churn_probability or 0.0)
        health = float(c.health_score) if c.health_score is not None else 50.0
        mrr = float(contract.contract_value_mrr or c.mrr or 0.0)
        expected_loss = round(mrr * churn_prob, 2)
        total_mrr_at_risk += expected_loss

        # Timing + Risk Priority Score Math:
        # Priority increases with higher churn probability and closer renewal proximity.
        timing_factor = 1.0 + max(0.0, (window_days - days_until_renewal) / float(window_days))
        priority_score = round(churn_prob * 100.0 * timing_factor, 2)

        items.append({
            "contract_id": str(contract.id),
            "customer_id": str(c.id),
            "customer_plan": c.plan or "standard",
            "renewal_date": ren_date.strftime("%Y-%m-%d"),
            "days_until_renewal": days_until_renewal,
            "auto_renew": contract.auto_renew,
            "contract_term_months": contract.contract_term_months,
            "contract_value_mrr": mrr,
            "churn_probability": round(churn_prob, 4),
            "churn_risk_tier": c.churn_risk_tier or ("critical" if churn_prob >= 0.7 else "high" if churn_prob >= 0.4 else "low"),
            "health_score": round(health, 1),
            "expected_revenue_loss": expected_loss,
            "urgency_priority_score": priority_score
        })

    # Sort by urgency priority score descending
    items.sort(key=lambda x: x["urgency_priority_score"], reverse=True)

    return {
        "tenant_id": str(tenant_id),
        "window_days": window_days,
        "total_renewals_in_window": len(items),
        "total_mrr_at_risk": round(total_mrr_at_risk, 2),
        "renewals": items
    }

async def create_or_update_contract(
    db: AsyncSession,
    tenant_id: uuid.UUID,
    customer_id: uuid.UUID,
    renewal_date: datetime,
    contract_term_months: int = 12,
    auto_renew: bool = True,
    contract_value_mrr: Optional[float] = None
) -> Contract:
    """
    Upserts a contract record for a customer.
    """
    import sqlalchemy
    await db.execute(sqlalchemy.text(f"SET LOCAL app.current_tenant = '{tenant_id}'"))

    res = await db.execute(
        select(Contract).where(
            and_(
                Contract.tenant_id == tenant_id,
                Contract.customer_id == customer_id
            )
        )
    )
    contract = res.scalars().first()

    if not contract:
        contract = Contract(
            tenant_id=tenant_id,
            customer_id=customer_id,
            contract_term_months=contract_term_months,
            renewal_date=renewal_date,
            auto_renew=auto_renew,
            contract_value_mrr=contract_value_mrr or 0.0
        )
        db.add(contract)
    else:
        contract.contract_term_months = contract_term_months
        contract.renewal_date = renewal_date
        contract.auto_renew = auto_renew
        if contract_value_mrr is not None:
            contract.contract_value_mrr = contract_value_mrr

    await db.commit()
    await db.refresh(contract)
    return contract
