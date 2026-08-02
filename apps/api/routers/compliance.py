from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
import uuid
from typing import Any, Dict

from apps.api.core.deps import get_db, get_current_user
from apps.api.models import User, Customer, CustomerEvent, Intervention, Campaign

router = APIRouter(prefix="/tenants/{tenant_id}/data", tags=["compliance"])

@router.get("/export")
async def export_tenant_data(
    tenant_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
) -> Dict[str, Any]:
    """
    GDPR/CCPA Data Export: Returns all data associated with the tenant.
    """
    if str(current_user.tenant_id) != str(tenant_id):
        raise HTTPException(status_code=403, detail="Not authorized to export data for this tenant")
    if current_user.role != "owner":
        raise HTTPException(status_code=403, detail="Only owners can export data")

    # Fetch data
    customers_result = await db.execute(select(Customer))
    customers = customers_result.scalars().all()

    events_result = await db.execute(select(CustomerEvent))
    events = events_result.scalars().all()

    interventions_result = await db.execute(select(Intervention))
    interventions = interventions_result.scalars().all()

    campaigns_result = await db.execute(select(Campaign))
    campaigns = campaigns_result.scalars().all()

    return {
        "tenant_id": str(tenant_id),
        "exported_by": current_user.email,
        "customers": [
            {
                "id": str(c.id),
                "external_ids": c.external_ids,
                "plan": c.plan,
                "mrr": c.mrr,
                "churn_probability": c.churn_probability
            } for c in customers
        ],
        "events": [
            {
                "id": str(e.id),
                "customer_id": str(e.customer_id),
                "event_type": e.event_type,
                "source": e.source,
                "properties": e.properties,
                "occurred_at": e.occurred_at.isoformat()
            } for e in events
        ],
        "interventions": [
            {
                "id": str(i.id),
                "customer_id": str(i.customer_id),
                "campaign_id": str(i.campaign_id) if i.campaign_id else None,
                "channel": i.channel,
                "status": i.status,
                "outcome": i.outcome
            } for i in interventions
        ],
        "campaigns": [
            {
                "id": str(c.id),
                "name": c.name,
                "status": c.status
            } for c in campaigns
        ]
    }

@router.delete("/delete")
async def delete_tenant_data(
    tenant_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    GDPR Right to be Forgotten: Deletes all customer/event data for the tenant.
    """
    if str(current_user.tenant_id) != str(tenant_id):
        raise HTTPException(status_code=403, detail="Not authorized to delete data for this tenant")
    if current_user.role != "owner":
        raise HTTPException(status_code=403, detail="Only owners can delete data")

    # In a real system, you would soft delete or queue this for background processing.
    # For now, we execute deletions in order of dependencies.
    
    # Intervention -> CustomerEvent -> ChurnFeature -> Customer
    # Campaign -> Intervention
    # Due to RLS, simply deleting from these tables drops exactly the tenant's data.
    
    await db.execute(Intervention.__table__.delete())
    await db.execute(Campaign.__table__.delete())
    from apps.api.models import ChurnFeature
    await db.execute(ChurnFeature.__table__.delete())
    await db.execute(CustomerEvent.__table__.delete())
    await db.execute(Customer.__table__.delete())
    
    await db.commit()
    
    return {"status": "success", "detail": "Tenant data successfully purged"}
