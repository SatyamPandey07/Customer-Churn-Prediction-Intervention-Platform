"""
Public versioned API (/v1/...) with API-key-based authentication.
Exposes: churn score lookup, health score lookup, webhook subscriptions.
Rate limiting: uses per-key in-memory rate limiter (reuse PR-10 pattern).
"""
import logging
import time
import uuid
from collections import defaultdict
from typing import Any

from apps.api.core.api_keys import verify_api_key
from apps.api.core.deps import get_db
from apps.api.models import ApiKey, Customer
from fastapi import APIRouter, Depends, Header, HTTPException
from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/v1", tags=["public-api-v1"])

# ---------------------------------------------------------------------------
# Per-key in-memory rate limiter (sliding window, 100 req / 60 seconds)
# ---------------------------------------------------------------------------
_rate_store: dict[str, list] = defaultdict(list)
RATE_LIMIT_WINDOW_SEC = 60
RATE_LIMIT_MAX_REQUESTS = 100


def _check_rate_limit(key_id: str):
    now = time.monotonic()
    window_start = now - RATE_LIMIT_WINDOW_SEC
    hits = _rate_store[key_id]
    # Drop old entries outside the window
    _rate_store[key_id] = [t for t in hits if t > window_start]
    if len(_rate_store[key_id]) >= RATE_LIMIT_MAX_REQUESTS:
        raise HTTPException(
            status_code=429,
            detail=f"Rate limit exceeded: {RATE_LIMIT_MAX_REQUESTS} requests per {RATE_LIMIT_WINDOW_SEC}s per API key."
        )
    _rate_store[key_id].append(now)


# ---------------------------------------------------------------------------
# Dependency: resolve and validate API key from header
# ---------------------------------------------------------------------------
async def require_api_key(
    x_api_key: str | None = Header(None, alias="X-Api-Key"),
    db: AsyncSession = Depends(get_db)
) -> ApiKey:
    if not x_api_key:
        raise HTTPException(status_code=401, detail="Missing X-Api-Key header")

    api_key = await verify_api_key(db, x_api_key)
    if not api_key:
        raise HTTPException(status_code=401, detail="Invalid or revoked API key")

    _check_rate_limit(str(api_key.id))
    return api_key


async def require_write_api_key(api_key: ApiKey = Depends(require_api_key)) -> ApiKey:
    """Enforces that the key has read_write scope."""
    if api_key.scope != "read_write":
        raise HTTPException(
            status_code=403,
            detail="This endpoint requires a read_write scoped API key"
        )
    return api_key


# ---------------------------------------------------------------------------
# Public Endpoints
# ---------------------------------------------------------------------------

@router.get("/customers/{customer_id}/churn-score")
async def get_public_churn_score(
    customer_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    api_key: ApiKey = Depends(require_api_key)
) -> dict[str, Any]:
    """
    Public endpoint: Returns churn probability + risk tier for a customer.
    Requires API key with 'read' or 'read_write' scope.
    """
    res = await db.execute(
        select(Customer).where(
            and_(Customer.id == customer_id, Customer.tenant_id == api_key.tenant_id)
        )
    )
    c = res.scalars().first()
    if not c:
        raise HTTPException(status_code=404, detail="Customer not found")

    return {
        "customer_id": str(c.id),
        "churn_probability": round(float(c.churn_probability or 0.0), 4),
        "churn_risk_tier": c.churn_risk_tier or "unknown",
        "model_version": c.churn_model_version or "v1",
        "computed_at": c.churn_computed_at.isoformat() if c.churn_computed_at else None
    }


@router.get("/customers/{customer_id}/health-score")
async def get_public_health_score(
    customer_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    api_key: ApiKey = Depends(require_api_key)
) -> dict[str, Any]:
    """
    Public endpoint: Returns composite health score for a customer.
    Requires API key with 'read' or 'read_write' scope.
    """
    res = await db.execute(
        select(Customer).where(
            and_(Customer.id == customer_id, Customer.tenant_id == api_key.tenant_id)
        )
    )
    c = res.scalars().first()
    if not c:
        raise HTTPException(status_code=404, detail="Customer not found")

    return {
        "customer_id": str(c.id),
        "health_score": round(float(c.health_score or 50.0), 1),
        "computed_at": c.health_score_computed_at.isoformat() if c.health_score_computed_at else None
    }


@router.get("/meta/openapi")
async def get_openapi_info() -> dict[str, Any]:
    """Returns metadata about the public API schema version."""
    return {
        "openapi_version": "3.1.0",
        "api_version": "v1",
        "title": "ChurnGuard.AI Public API",
        "description": "Versioned public API for embedding ChurnGuard churn and health intelligence into your own tools.",
        "endpoints": [
            "GET /v1/customers/{customer_id}/churn-score",
            "GET /v1/customers/{customer_id}/health-score"
        ],
        "auth": "Bearer API key via X-Api-Key header",
        "rate_limit": f"{RATE_LIMIT_MAX_REQUESTS} requests per {RATE_LIMIT_WINDOW_SEC}s per key"
    }
