import uuid
from datetime import UTC, datetime

from apps.api.core.deps import get_db, require_role
from apps.api.core.outreach.adapters import get_adapter
from apps.api.models import AuditLog, Customer, Intervention, Role
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, ConfigDict
from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession

router = APIRouter(prefix="/customers/{customer_id}/interventions", tags=["interventions"])

class ManualOverrideRequest(BaseModel):
    channel: str
    message: str

class InterventionResponse(BaseModel):
    id: uuid.UUID
    tenant_id: uuid.UUID
    customer_id: uuid.UUID
    campaign_id: uuid.UUID | None
    channel: str
    status: str
    sent_at: datetime | None
    manual_override: bool
    
    model_config = ConfigDict(from_attributes=True)

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
        intervention.sent_at = datetime.now(UTC)
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

@router.get("", response_model=list[InterventionResponse])
async def get_interventions(
    customer_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    user: dict = Depends(require_role([Role.owner, Role.admin, Role.analyst, Role.viewer]))
):
    result = await db.execute(
        select(Intervention).where(
            and_(Intervention.customer_id == customer_id, Intervention.tenant_id == user["tenant_id"])
        ).order_by(Intervention.sent_at.desc().nulls_last())
    )
    return result.scalars().all()
