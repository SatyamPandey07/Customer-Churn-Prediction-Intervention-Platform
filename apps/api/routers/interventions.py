import uuid
from typing import Optional
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_

from apps.api.core.deps import get_db, require_role
from apps.api.models import Customer, Intervention, Role, User, AuditLog
from apps.api.core.outreach.adapters import get_adapter

router = APIRouter(prefix="/customers/{customer_id}/interventions", tags=["interventions"])

class ManualOverrideRequest(BaseModel):
    channel: str
    message: str

class InterventionResponse(BaseModel):
    id: uuid.UUID
    tenant_id: uuid.UUID
    customer_id: uuid.UUID
    campaign_id: Optional[uuid.UUID]
    channel: str
    status: str
    sent_at: Optional[datetime]
    manual_override: bool
    
    class Config:
        from_attributes = True

@router.post("/override", response_model=InterventionResponse)
async def manual_override(
    customer_id: uuid.UUID,
    req: ManualOverrideRequest,
    db: AsyncSession = Depends(get_db),
    user: dict = Depends(require_role([Role.owner, Role.admin, Role.analyst]))
):
    # Verify customer belongs to tenant
    result = await db.execute(
        select(Customer).where(
            and_(Customer.id == customer_id, Customer.tenant_id == user["tenant_id"])
        )
    )
    customer = result.scalars().first()
    if not customer:
        raise HTTPException(status_code=404, detail="Customer not found")
        
    adapter = get_adapter(req.channel)
    
    intervention = Intervention(
        id=uuid.uuid4(),
        tenant_id=user["tenant_id"],
        customer_id=customer.id,
        channel=req.channel,
        status="pending",
        manual_override=True
    )
    db.add(intervention)
    
    # Send
    try:
        success = await adapter.send(db, customer, req.message)
        intervention.status = "sent" if success else "failed"
        intervention.sent_at = datetime.now(timezone.utc)
    except Exception:
        intervention.status = "failed"
        
    # Audit log
    audit_log = AuditLog(
        id=uuid.uuid4(),
        tenant_id=user["tenant_id"],
        actor_user_id=user["user_id"],
        action="manual_intervention",
        resource=f"customer:{customer.id}"
    )
    db.add(audit_log)
    
    await db.commit()
    await db.refresh(intervention)
    
    return intervention
