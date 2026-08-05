"""
API Key management: generate, hash, verify, and revoke tenant-scoped API keys.
Keys are hashed at rest using SHA-256. Only the prefix (first 8 chars) is stored
in plaintext for display purposes. The full key is only returned once at creation.
"""
import hashlib
import logging
import secrets
import uuid
from datetime import UTC, datetime
from typing import Any

from apps.api.models import ApiKey, AuditLog
from fastapi import HTTPException
from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)

KEY_PREFIX = "cgk_"
KEY_BYTE_LENGTH = 32  # 256 bits of entropy


def _generate_raw_key() -> str:
    """Generates a cryptographically-random API key with prefix."""
    token = secrets.token_urlsafe(KEY_BYTE_LENGTH)
    return f"{KEY_PREFIX}{token}"


def _hash_key(raw_key: str) -> str:
    """SHA-256 hash of the raw key for at-rest storage."""
    return hashlib.sha256(raw_key.encode()).hexdigest()


def _extract_prefix(raw_key: str) -> str:
    """Returns first 12 chars of raw key for display (e.g. 'cgk_abc12345')."""
    return raw_key[:12]


async def create_api_key(
    db: AsyncSession,
    tenant_id: uuid.UUID,
    name: str,
    scope: str = "read",
    created_by_user_id: uuid.UUID | None = None,
    expires_at: datetime | None = None
) -> dict[str, Any]:
    """
    Issues a new API key for the tenant. The raw key is returned ONCE only.
    Subsequent requests only see the key prefix and metadata.
    """
    if scope not in ("read", "read_write"):
        raise HTTPException(status_code=400, detail="scope must be 'read' or 'read_write'")

    raw_key = _generate_raw_key()
    hashed = _hash_key(raw_key)
    prefix = _extract_prefix(raw_key)

    api_key = ApiKey(
        tenant_id=tenant_id,
        created_by=created_by_user_id,
        name=name,
        hashed_key=hashed,
        key_prefix=prefix,
        scope=scope,
        is_active=True,
        expires_at=expires_at
    )
    db.add(api_key)

    # Audit trail
    log = AuditLog(
        tenant_id=tenant_id,
        actor_user_id=created_by_user_id,
        action="api_key.created",
        resource=f"api_key:{name}"
    )
    db.add(log)

    await db.commit()
    await db.refresh(api_key)

    return {
        "id": str(api_key.id),
        "name": api_key.name,
        "key": raw_key,  # Only returned once
        "key_prefix": prefix,
        "scope": scope,
        "expires_at": expires_at.isoformat() if expires_at else None,
        "created_at": api_key.created_at.isoformat()
    }


async def list_api_keys(db: AsyncSession, tenant_id: uuid.UUID) -> list:
    """Lists all API keys for a tenant (without raw key values)."""
    res = await db.execute(
        select(ApiKey).where(
            and_(ApiKey.tenant_id == tenant_id, ApiKey.is_active == True)
        ).order_by(ApiKey.created_at.desc())
    )
    keys = res.scalars().all()
    return [
        {
            "id": str(k.id),
            "name": k.name,
            "key_prefix": k.key_prefix,
            "scope": k.scope,
            "last_used_at": k.last_used_at.isoformat() if k.last_used_at else None,
            "expires_at": k.expires_at.isoformat() if k.expires_at else None,
            "created_at": k.created_at.isoformat()
        }
        for k in keys
    ]


async def revoke_api_key(
    db: AsyncSession,
    tenant_id: uuid.UUID,
    key_id: uuid.UUID,
    revoked_by_user_id: uuid.UUID | None = None
) -> dict[str, Any]:
    """Revokes an API key by marking it inactive."""
    res = await db.execute(
        select(ApiKey).where(
            and_(ApiKey.id == key_id, ApiKey.tenant_id == tenant_id)
        )
    )
    api_key = res.scalars().first()
    if not api_key:
        raise HTTPException(status_code=404, detail="API key not found")

    api_key.is_active = False
    api_key.revoked_at = datetime.now(UTC)

    log = AuditLog(
        tenant_id=tenant_id,
        actor_user_id=revoked_by_user_id,
        action="api_key.revoked",
        resource=f"api_key:{api_key.name}"
    )
    db.add(log)
    await db.commit()

    return {"id": str(key_id), "revoked": True}


async def verify_api_key(db: AsyncSession, raw_key: str) -> ApiKey | None:
    """
    Validates an incoming API key against stored hashes.
    Returns the ApiKey record if valid and active; None otherwise.
    Updates last_used_at on success.
    """
    if not raw_key:
        return None

    hashed = _hash_key(raw_key)
    res = await db.execute(
        select(ApiKey).where(
            and_(ApiKey.hashed_key == hashed, ApiKey.is_active == True)
        )
    )
    api_key = res.scalars().first()

    if not api_key:
        return None

    # Check expiry
    if api_key.expires_at and datetime.now(UTC) > api_key.expires_at.replace(tzinfo=UTC):
        return None

    # Update last_used_at
    api_key.last_used_at = datetime.now(UTC)
    await db.commit()

    return api_key
