from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from apps.api.core.deps import get_db, get_current_user, require_role
from apps.api.models import TenantBranding, Tenant, User, Role, PlanTier
from pydantic import BaseModel
from typing import Optional

router = APIRouter(prefix="/branding", tags=["branding"])

class BrandingUpdate(BaseModel):
    logo_url: Optional[str] = None
    primary_color: Optional[str] = None
    secondary_color: Optional[str] = None
    favicon_url: Optional[str] = None
    product_display_name: Optional[str] = "Churn Intervention Platform"
    support_contact_email: Optional[str] = None

class BrandingResponse(BrandingUpdate):
    tenant_id: str

@router.get("/public", response_model=Optional[BrandingResponse])
async def get_public_branding(domain: str, db: AsyncSession = Depends(get_db)):
    # Simple lookup based on domain
    subdomain = domain.split(".")[0]
    result = await db.execute(select(Tenant).where(Tenant.subdomain == subdomain))
    tenant = result.scalars().first()
    
    if not tenant:
        from apps.api.models import TenantDomain, DomainVerificationStatus
        domain_res = await db.execute(select(TenantDomain).where(
            (TenantDomain.domain == domain) & 
            (TenantDomain.verification_status == DomainVerificationStatus.verified)
        ))
        td = domain_res.scalars().first()
        if td:
            res = await db.execute(select(Tenant).where(Tenant.id == td.tenant_id))
            tenant = res.scalars().first()
            
    if not tenant:
        raise HTTPException(status_code=404, detail="Tenant not found for domain")
        
    branding_res = await db.execute(select(TenantBranding).where(TenantBranding.tenant_id == tenant.id))
    branding = branding_res.scalars().first()
    
    if not branding:
        return None
        
    return BrandingResponse(
        tenant_id=str(branding.tenant_id),
        logo_url=branding.logo_url,
        primary_color=branding.primary_color,
        secondary_color=branding.secondary_color,
        favicon_url=branding.favicon_url,
        product_display_name=branding.product_display_name,
        support_contact_email=branding.support_contact_email
    )

@router.get("", response_model=Optional[BrandingResponse])
async def get_tenant_branding(
    user: User = Depends(get_current_user), 
    db: AsyncSession = Depends(get_db)
):
    result = await db.execute(select(TenantBranding).where(TenantBranding.tenant_id == user.tenant_id))
    branding = result.scalars().first()
    if not branding:
        return None
    return BrandingResponse(
        tenant_id=str(branding.tenant_id),
        logo_url=branding.logo_url,
        primary_color=branding.primary_color,
        secondary_color=branding.secondary_color,
        favicon_url=branding.favicon_url,
        product_display_name=branding.product_display_name,
        support_contact_email=branding.support_contact_email
    )

@router.put("", response_model=BrandingResponse)
async def update_tenant_branding(
    body: BrandingUpdate,
    user: User = Depends(require_role([Role.admin, Role.owner])),
    db: AsyncSession = Depends(get_db)
):
    tenant_res = await db.execute(select(Tenant).where(Tenant.id == user.tenant_id))
    tenant = tenant_res.scalars().first()
    if tenant.plan_tier != PlanTier.tier3:
        raise HTTPException(status_code=403, detail="Enterprise white-labeling requires Tier 3 plan.")
        
    result = await db.execute(select(TenantBranding).where(TenantBranding.tenant_id == user.tenant_id))
    branding = result.scalars().first()
    
    if not branding:
        branding = TenantBranding(tenant_id=user.tenant_id)
        db.add(branding)
        
    branding.logo_url = body.logo_url
    branding.primary_color = body.primary_color
    branding.secondary_color = body.secondary_color
    branding.favicon_url = body.favicon_url
    branding.product_display_name = body.product_display_name
    branding.support_contact_email = body.support_contact_email
    
    await db.commit()
    await db.refresh(branding)
    
    return BrandingResponse(
        tenant_id=str(branding.tenant_id),
        logo_url=branding.logo_url,
        primary_color=branding.primary_color,
        secondary_color=branding.secondary_color,
        favicon_url=branding.favicon_url,
        product_display_name=branding.product_display_name,
        support_contact_email=branding.support_contact_email
    )
