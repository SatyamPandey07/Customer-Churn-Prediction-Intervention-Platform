import uuid
from typing import List, Dict, Any, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_

from apps.api.core.deps import get_db, require_role
from apps.api.models import Campaign, Role, User

router = APIRouter(prefix="/campaigns", tags=["campaigns"])

class CampaignCreate(BaseModel):
    name: str
    trigger_rule: Dict[str, Any]
    intervention_type: str
    channel: str
    template: Optional[str] = None
    status: str = "draft"

class CampaignResponse(CampaignCreate):
    id: uuid.UUID
    tenant_id: uuid.UUID
    created_by: Optional[uuid.UUID]
    
    class Config:
        from_attributes = True

@router.get("", response_model=List[CampaignResponse])
async def list_campaigns(
    db: AsyncSession = Depends(get_db),
    user: dict = Depends(require_role([Role.owner, Role.admin, Role.analyst, Role.viewer]))
):
    result = await db.execute(
        select(Campaign).where(Campaign.tenant_id == user["tenant_id"])
    )
    return result.scalars().all()

@router.post("", response_model=CampaignResponse, status_code=status.HTTP_201_CREATED)
async def create_campaign(
    campaign_in: CampaignCreate,
    db: AsyncSession = Depends(get_db),
    user: dict = Depends(require_role([Role.owner, Role.admin, Role.analyst]))
):
    campaign = Campaign(
        tenant_id=user["tenant_id"],
        name=campaign_in.name,
        trigger_rule=campaign_in.trigger_rule,
        intervention_type=campaign_in.intervention_type,
        channel=campaign_in.channel,
        template=campaign_in.template,
        status=campaign_in.status,
        created_by=user["user_id"]
    )
    db.add(campaign)
    await db.commit()
    await db.refresh(campaign)
    return campaign

@router.put("/{campaign_id}", response_model=CampaignResponse)
async def update_campaign(
    campaign_id: uuid.UUID,
    campaign_in: CampaignCreate,
    db: AsyncSession = Depends(get_db),
    user: dict = Depends(require_role([Role.owner, Role.admin, Role.analyst]))
):
    result = await db.execute(
        select(Campaign).where(
            and_(Campaign.id == campaign_id, Campaign.tenant_id == user["tenant_id"])
        )
    )
    campaign = result.scalars().first()
    if not campaign:
        raise HTTPException(status_code=404, detail="Campaign not found")
        
    campaign.name = campaign_in.name
    campaign.trigger_rule = campaign_in.trigger_rule
    campaign.intervention_type = campaign_in.intervention_type
    campaign.channel = campaign_in.channel
    campaign.template = campaign_in.template
    campaign.status = campaign_in.status
    
    await db.commit()
    await db.refresh(campaign)
    return campaign

@router.delete("/{campaign_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_campaign(
    campaign_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    user: dict = Depends(require_role([Role.owner, Role.admin, Role.analyst]))
):
    result = await db.execute(
        select(Campaign).where(
            and_(Campaign.id == campaign_id, Campaign.tenant_id == user["tenant_id"])
        )
    )
    campaign = result.scalars().first()
    if not campaign:
        raise HTTPException(status_code=404, detail="Campaign not found")
        
    await db.delete(campaign)
    await db.commit()
