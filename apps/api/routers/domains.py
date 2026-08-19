import uuid
from typing import List

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from apps.api.core.deps import get_db, get_current_user, require_role
from apps.api.models import TenantDomain, DomainVerificationStatus, Tenant, User, Role, PlanTier
from pydantic import BaseModel

router = APIRouter(prefix="/domains", tags=["domains"])

class DomainCreate(BaseModel):
    domain: str

class DomainResponse(BaseModel):
    id: str
    domain: str
    verification_status: str
    verification_token: str

@router.get("", response_model=List[DomainResponse])
async def list_domains(
    user: User = Depends(require_role([Role.admin, Role.owner])), 
    db: AsyncSession = Depends(get_db)
):
    result = await db.execute(select(TenantDomain).where(TenantDomain.tenant_id == user.tenant_id))
    domains = result.scalars().all()
    
    return [
        DomainResponse(
            id=str(d.id),
            domain=d.domain,
            verification_status=d.verification_status,
            verification_token=d.verification_token
        ) for d in domains
    ]

@router.post("", response_model=DomainResponse, status_code=status.HTTP_201_CREATED)
async def add_domain(
    body: DomainCreate,
    user: User = Depends(require_role([Role.admin, Role.owner])),
    db: AsyncSession = Depends(get_db)
):
    tenant_res = await db.execute(select(Tenant).where(Tenant.id == user.tenant_id))
    tenant = tenant_res.scalars().first()
    if tenant.plan_tier != PlanTier.tier3:
        raise HTTPException(status_code=403, detail="Custom domains require Tier 3 plan.")
        
    # Check if domain already exists
    existing = await db.execute(select(TenantDomain).where(TenantDomain.domain == body.domain))
    if existing.scalars().first():
        raise HTTPException(status_code=400, detail="Domain is already registered.")
        
    domain_entry = TenantDomain(
        tenant_id=user.tenant_id,
        domain=body.domain,
        verification_status=DomainVerificationStatus.pending,
        verification_token=f"churndb-verify-{uuid.uuid4().hex}"
    )
    db.add(domain_entry)
    await db.commit()
    await db.refresh(domain_entry)
    
    return DomainResponse(
        id=str(domain_entry.id),
        domain=domain_entry.domain,
        verification_status=domain_entry.verification_status,
        verification_token=domain_entry.verification_token
    )

@router.post("/{domain_id}/verify", response_model=DomainResponse)
async def verify_domain(
    domain_id: str,
    user: User = Depends(require_role([Role.admin, Role.owner])),
    db: AsyncSession = Depends(get_db)
):
    result = await db.execute(select(TenantDomain).where(
        (TenantDomain.id == domain_id) & 
        (TenantDomain.tenant_id == user.tenant_id)
    ))
    domain_entry = result.scalars().first()
    
    if not domain_entry:
        raise HTTPException(status_code=404, detail="Domain not found.")
        
    # Mocking DNS verification logic (e.g. looking up TXT records).
    # We will automatically consider it verified for this PR.
    domain_entry.verification_status = DomainVerificationStatus.verified
    await db.commit()
    await db.refresh(domain_entry)
    
    return DomainResponse(
        id=str(domain_entry.id),
        domain=domain_entry.domain,
        verification_status=domain_entry.verification_status,
        verification_token=domain_entry.verification_token
    )

@router.delete("/{domain_id}", status_code=status.HTTP_204_NO_CONTENT)
async def remove_domain(
    domain_id: str,
    user: User = Depends(require_role([Role.admin, Role.owner])),
    db: AsyncSession = Depends(get_db)
):
    result = await db.execute(select(TenantDomain).where(
        (TenantDomain.id == domain_id) & 
        (TenantDomain.tenant_id == user.tenant_id)
    ))
    domain_entry = result.scalars().first()
    
    if not domain_entry:
        raise HTTPException(status_code=404, detail="Domain not found.")
        
    await db.delete(domain_entry)
    await db.commit()
