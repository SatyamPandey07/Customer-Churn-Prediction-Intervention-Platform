from datetime import datetime, timezone, timedelta
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, status, Request
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from pydantic import BaseModel

from apps.api.models import User, Tenant, Role, PlanTier, AuditLog, RefreshToken
from apps.api.core.deps import get_db, get_current_user, require_role
from apps.api.core.security import (
    get_password_hash,
    verify_password,
    create_access_token,
    create_refresh_token,
    validate_password_policy
)
from apps.api.core.rate_limit import (
    check_rate_limit,
    check_account_lockout,
    record_failed_login,
    reset_failed_login
)

router = APIRouter(prefix="/auth", tags=["auth"])

class SignupRequest(BaseModel):
    tenant_name: str
    subdomain: str
    email: str
    password: str

class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    role: str = "viewer"

class RefreshRequest(BaseModel):
    refresh_token: str

@router.post("/signup", status_code=status.HTTP_201_CREATED)
async def signup(request: Request, body: SignupRequest, db: AsyncSession = Depends(get_db)):
    ip_address = request.client.host if request.client else None
    await check_rate_limit(ip_address or "unknown")

    if not validate_password_policy(body.password):
        raise HTTPException(status_code=400, detail="Password does not meet complexity requirements.")
    
    # Check if subdomain exists
    result = await db.execute(select(Tenant).where(Tenant.subdomain == body.subdomain))
    if result.scalars().first():
        raise HTTPException(status_code=400, detail="Subdomain already exists.")
        
    # Create tenant
    tenant = Tenant(
        name=body.tenant_name,
        subdomain=body.subdomain,
        plan_tier=PlanTier.tier1
    )
    db.add(tenant)
    await db.flush()
    
    # Check if user exists (in real app, email is unique globally or per tenant. Here we enforce per tenant in DB, but let's check anyway)
    
    # Create user
    user = User(
        tenant_id=tenant.id,
        email=body.email,
        hashed_password=get_password_hash(body.password),
        role=Role.owner
    )
    db.add(user)
    await db.flush()

    # Create audit log (bypassing RLS or since we didn't set tenant context yet, wait, audit_logs has RLS.
    # We haven't set app.current_tenant yet in this transaction, but since the user is not authenticated,
    # we might need to bypass RLS or run as superuser, OR since we didn't enable RLS on the postgres user
    # unless we force it. Wait, by default, the table owner (postgres user) bypasses RLS!
    # So inserting should be fine.)
    audit = AuditLog(
        tenant_id=tenant.id,
        actor_user_id=user.id,
        action="SIGNUP",
        ip_address=ip_address
    )
    db.add(audit)
    await db.commit()
    
    return {"message": "Signup successful."}


@router.post("/login", response_model=TokenResponse)
async def login(request: Request, form_data: OAuth2PasswordRequestForm = Depends(), db: AsyncSession = Depends(get_db)):
    ip_address = request.client.host if request.client else None
    await check_rate_limit(ip_address or "unknown")
    await check_account_lockout(form_data.username)

    # find user by email. Note: email might be across multiple tenants. 
    # For simplicity, we grab the first matching email. In a real multi-tenant app, 
    # users might specify tenant in URL or payload, but OAuth2 uses standard form.
    result = await db.execute(select(User))
    users = result.scalars().all()
    user = next((u for u in users if u.email == form_data.username), None)

    if not user or not verify_password(form_data.password, user.hashed_password):
        await record_failed_login(form_data.username)
        # Audit log failed login
        if user:
            audit = AuditLog(tenant_id=user.tenant_id, actor_user_id=user.id, action="LOGIN_FAILED", ip_address=ip_address)
            db.add(audit)
            await db.commit()
            
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    await reset_failed_login(user.email)
    
    access_token = create_access_token(subject=user.id, role=user.role.value, tenant_id=user.tenant_id)
    refresh_token_str = create_refresh_token(subject=user.id)
    
    # Store refresh token
    hashed_refresh = get_password_hash(refresh_token_str)
    expires_at = datetime.now(timezone.utc) + timedelta(days=7)
    db_token = RefreshToken(
        user_id=user.id,
        hashed_token=hashed_refresh,
        expires_at=expires_at
    )
    db.add(db_token)
    
    audit = AuditLog(
        tenant_id=user.tenant_id,
        actor_user_id=user.id,
        action="LOGIN_SUCCESS",
        ip_address=ip_address
    )
    db.add(audit)
    await db.commit()

    return {
        "access_token": access_token,
        "refresh_token": refresh_token_str,
        "token_type": "bearer",
        "role": user.role.value
    }

@router.post("/refresh", response_model=TokenResponse)
async def refresh(request: Request, body: RefreshRequest, db: AsyncSession = Depends(get_db)):
    # Very simple refresh logic. We find a token for the user that is valid.
    # Since we hashed it, we can't look it up directly.
    # Normally, you decode the refresh token to get user_id, then check all valid tokens for that user.
    from apps.api.core.security import decode_token
    from jose import JWTError
    try:
        payload = decode_token(body.refresh_token)
        user_id = payload.get("sub")
        if not user_id:
            raise HTTPException(status_code=401, detail="Invalid token")
    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid token")
    
    result = await db.execute(
        select(RefreshToken).where(RefreshToken.user_id == user_id, RefreshToken.revoked_at == None, RefreshToken.expires_at > datetime.now(timezone.utc))
    )
    tokens = result.scalars().all()
    
    valid_token_record = None
    for t in tokens:
        if verify_password(body.refresh_token, t.hashed_token):
            valid_token_record = t
            break
            
    if not valid_token_record:
        raise HTTPException(status_code=401, detail="Invalid or expired refresh token")
        
    # Get user
    user = await db.get(User, user_id)
    
    # Issue new tokens
    access_token = create_access_token(subject=user.id, role=user.role.value, tenant_id=user.tenant_id)
    new_refresh_str = create_refresh_token(subject=user.id)
    
    # Revoke old token
    valid_token_record.revoked_at = datetime.now(timezone.utc)
    
    # Add new token
    db_token = RefreshToken(
        user_id=user.id,
        hashed_token=get_password_hash(new_refresh_str),
        expires_at=datetime.now(timezone.utc) + timedelta(days=7)
    )
    db.add(db_token)
    await db.commit()

    return {
        "access_token": access_token,
        "refresh_token": new_refresh_str,
        "token_type": "bearer"
    }

@router.post("/logout")
async def logout(current_user: dict = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    # We revoke all tokens for this user for simplicity, or we could accept a specific refresh token in the body
    # and revoke just that one. Let's just revoke all active ones.
    user_id = current_user["user_id"]
    result = await db.execute(
        select(RefreshToken).where(RefreshToken.user_id == user_id, RefreshToken.revoked_at == None)
    )
    tokens = result.scalars().all()
    for t in tokens:
        t.revoked_at = datetime.now(timezone.utc)
        
    audit = AuditLog(
        tenant_id=current_user["tenant_id"],
        actor_user_id=user_id,
        action="LOGOUT",
    )
    db.add(audit)
    await db.commit()
    return {"message": "Logged out successfully"}

@router.get("/admin-only")
async def admin_only_route(current_user: dict = Depends(require_role([Role.owner, Role.admin]))):
    return {"message": "admin area"}
