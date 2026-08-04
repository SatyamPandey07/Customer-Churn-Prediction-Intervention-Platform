"""
API key management endpoints (RBAC: owner/admin only) and CRM sync trigger.
Fairness monitoring report endpoint.
"""
import uuid
import logging
from typing import Dict, Any, Optional, List
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel

from apps.api.core.deps import get_db, require_role
from apps.api.core.api_keys import create_api_key, list_api_keys, revoke_api_key
from apps.api.core.crm.engine import sync_all_customers_to_crm, sync_customer_to_crm
from apps.api.core.ml.fairness import get_latest_fairness_report, run_fairness_monitoring
from apps.api.models import Customer, Role
from sqlalchemy import select, and_

logger = logging.getLogger(__name__)

router = APIRouter(tags=["crm-api-fairness"])


# ---------------------------------------------------------------------------
# API Key Management
# ---------------------------------------------------------------------------

class CreateApiKeyPayload(BaseModel):
    name: str
    scope: str = "read"  # "read" or "read_write"
    expires_at: Optional[datetime] = None


@router.get("/tenants/{tenant_id}/api-keys")
async def get_api_keys(
    tenant_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    user: dict = Depends(require_role([Role.owner, Role.admin]))
):
    user_tenant_id = uuid.UUID(str(user["tenant_id"]))
    if user_tenant_id != tenant_id:
        raise HTTPException(status_code=403, detail="Not authorized for this tenant")

    keys = await list_api_keys(db, tenant_id)
    return {"tenant_id": str(tenant_id), "api_keys": keys}


@router.post("/tenants/{tenant_id}/api-keys")
async def issue_api_key(
    tenant_id: uuid.UUID,
    payload: CreateApiKeyPayload,
    db: AsyncSession = Depends(get_db),
    user: dict = Depends(require_role([Role.owner, Role.admin]))
):
    user_tenant_id = uuid.UUID(str(user["tenant_id"]))
    if user_tenant_id != tenant_id:
        raise HTTPException(status_code=403, detail="Not authorized for this tenant")

    result = await create_api_key(
        db=db,
        tenant_id=tenant_id,
        name=payload.name,
        scope=payload.scope,
        created_by_user_id=uuid.UUID(str(user["user_id"])) if user.get("user_id") else None,
        expires_at=payload.expires_at
    )
    return result


@router.delete("/tenants/{tenant_id}/api-keys/{key_id}")
async def delete_api_key(
    tenant_id: uuid.UUID,
    key_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    user: dict = Depends(require_role([Role.owner, Role.admin]))
):
    user_tenant_id = uuid.UUID(str(user["tenant_id"]))
    if user_tenant_id != tenant_id:
        raise HTTPException(status_code=403, detail="Not authorized for this tenant")

    result = await revoke_api_key(
        db=db,
        tenant_id=tenant_id,
        key_id=key_id,
        revoked_by_user_id=uuid.UUID(str(user["user_id"])) if user.get("user_id") else None
    )
    return result


# ---------------------------------------------------------------------------
# CRM Sync Triggers
# ---------------------------------------------------------------------------

@router.post("/tenants/{tenant_id}/crm/{crm_type}/sync")
async def trigger_full_crm_sync(
    tenant_id: uuid.UUID,
    crm_type: str,
    db: AsyncSession = Depends(get_db),
    user: dict = Depends(require_role([Role.owner, Role.admin]))
):
    user_tenant_id = uuid.UUID(str(user["tenant_id"]))
    if user_tenant_id != tenant_id:
        raise HTTPException(status_code=403, detail="Not authorized for this tenant")

    if crm_type not in ("salesforce", "hubspot"):
        raise HTTPException(status_code=400, detail="crm_type must be 'salesforce' or 'hubspot'")

    result = await sync_all_customers_to_crm(db, tenant_id, crm_type)
    return result


@router.post("/tenants/{tenant_id}/customers/{customer_id}/crm/{crm_type}/sync")
async def trigger_customer_crm_sync(
    tenant_id: uuid.UUID,
    customer_id: uuid.UUID,
    crm_type: str,
    db: AsyncSession = Depends(get_db),
    user: dict = Depends(require_role([Role.owner, Role.admin, Role.analyst]))
):
    user_tenant_id = uuid.UUID(str(user["tenant_id"]))
    if user_tenant_id != tenant_id:
        raise HTTPException(status_code=403, detail="Not authorized for this tenant")

    if crm_type not in ("salesforce", "hubspot"):
        raise HTTPException(status_code=400, detail="crm_type must be 'salesforce' or 'hubspot'")

    res = await db.execute(
        select(Customer).where(
            and_(Customer.id == customer_id, Customer.tenant_id == tenant_id)
        )
    )
    customer = res.scalars().first()
    if not customer:
        raise HTTPException(status_code=404, detail="Customer not found")

    log = await sync_customer_to_crm(db, tenant_id, customer, crm_type)
    return {
        "id": str(log.id),
        "customer_id": str(customer_id),
        "crm_type": crm_type,
        "status": log.status,
        "fields_pushed": log.fields_pushed,
        "error_message": log.error_message
    }


# ---------------------------------------------------------------------------
# Model Fairness Report
# ---------------------------------------------------------------------------

@router.get("/tenants/{tenant_id}/ml/fairness-report")
async def get_fairness_report(
    tenant_id: uuid.UUID,
    dimension: str = Query("plan_tier", enum=["plan_tier", "industry", "company_size_band"]),
    db: AsyncSession = Depends(get_db),
    user: dict = Depends(require_role([Role.owner, Role.admin, Role.analyst]))
):
    user_tenant_id = uuid.UUID(str(user["tenant_id"]))
    if user_tenant_id != tenant_id:
        raise HTTPException(status_code=403, detail="Not authorized for this tenant")

    report = await get_latest_fairness_report(db, tenant_id, dimension)
    return report


@router.post("/tenants/{tenant_id}/ml/fairness-report/run")
async def run_fairness_report(
    tenant_id: uuid.UUID,
    dimension: str = Query("plan_tier", enum=["plan_tier", "industry", "company_size_band"]),
    db: AsyncSession = Depends(get_db),
    user: dict = Depends(require_role([Role.owner, Role.admin]))
):
    user_tenant_id = uuid.UUID(str(user["tenant_id"]))
    if user_tenant_id != tenant_id:
        raise HTTPException(status_code=403, detail="Not authorized for this tenant")

    report = await run_fairness_monitoring(db, tenant_id, dimension)
    return {
        "id": str(report.id),
        "dimension": report.dimension,
        "generated_at": report.generated_at.isoformat(),
        "total_segments": len(report.segments),
        "flagged_segments": report.flagged_segments,
        "segments": report.segments
    }
