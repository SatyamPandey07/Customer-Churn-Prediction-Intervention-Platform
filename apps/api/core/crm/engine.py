"""
CRM sync engine: orchestrates scheduled and manual outbound sync of ChurnGuard
risk/health data to Salesforce and HubSpot CRM records.
"""
import logging
import uuid
from datetime import UTC, datetime
from typing import Any

from apps.api.core.crm.adapters import get_crm_adapter
from apps.api.models import CrmSyncLog, Customer
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)

CRM_TYPES = ["salesforce", "hubspot"]


def _build_fields_for_customer(customer: Customer) -> dict[str, Any]:
    """Builds the field dict to push to CRM for a given customer."""
    return {
        "churn_risk_tier": customer.churn_risk_tier or "unknown",
        "churn_probability": round(float(customer.churn_probability or 0.0), 4),
        "health_score": round(float(customer.health_score or 50.0), 1),
        # open_interventions placeholder — a real query would count pending interventions
        "open_interventions": 0
    }


async def sync_customer_to_crm(
    db: AsyncSession,
    tenant_id: uuid.UUID,
    customer: Customer,
    crm_type: str
) -> CrmSyncLog:
    """
    Pushes ChurnGuard risk + health fields for a single customer to the given CRM.
    Logs each sync attempt in crm_sync_logs.
    """
    adapter = get_crm_adapter(crm_type)
    crm_id = (customer.external_ids or {}).get(crm_type)

    sync_log = CrmSyncLog(
        tenant_id=tenant_id,
        customer_id=customer.id,
        crm_type=crm_type,
        status="pending",
        fields_pushed={},
        synced_at=datetime.now(UTC)
    )
    db.add(sync_log)
    await db.flush()

    if not crm_id:
        sync_log.status = "failed"
        sync_log.error_message = f"No {crm_type} external ID found for customer {customer.id}"
        await db.commit()
        return sync_log

    try:
        fields = _build_fields_for_customer(customer)
        result = await adapter.push_customer_fields(crm_id, fields)
        sync_log.status = "success"
        sync_log.fields_pushed = result.get("pushed_fields", fields)
    except Exception as exc:
        logger.error("CRM sync failed for customer %s via %s: %s", customer.id, crm_type, exc)
        sync_log.status = "failed"
        sync_log.error_message = str(exc)

    await db.commit()
    await db.refresh(sync_log)
    return sync_log


async def sync_all_customers_to_crm(
    db: AsyncSession,
    tenant_id: uuid.UUID,
    crm_type: str
) -> dict[str, Any]:
    """
    Scheduled batch sync: pushes ChurnGuard risk/health fields for all tenant
    customers to the specified CRM.
    """
    import sqlalchemy
    await db.execute(sqlalchemy.text(f"SET LOCAL app.current_tenant = '{tenant_id}'"))

    res = await db.execute(select(Customer).where(Customer.tenant_id == tenant_id))
    customers = res.scalars().all()

    results = {"total": len(customers), "success": 0, "failed": 0, "skipped": 0}

    for c in customers:
        log = await sync_customer_to_crm(db, tenant_id, c, crm_type)
        if log.status == "success":
            results["success"] += 1
        elif log.status == "failed":
            if "No" in (log.error_message or ""):
                results["skipped"] += 1
            else:
                results["failed"] += 1

    return {
        "tenant_id": str(tenant_id),
        "crm_type": crm_type,
        "synced_at": datetime.now(UTC).isoformat(),
        **results
    }
