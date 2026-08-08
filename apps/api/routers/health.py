import uuid
from datetime import UTC, datetime
from typing import Any

from apps.api.core.deps import get_current_user, get_db
from apps.api.core.ml.expansion import predict_expansion
from apps.api.core.ml.features import extract_features
from apps.api.core.ml.health import compute_health_score
from apps.api.models import Customer, HealthScore, HealthScoreConfig
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

router = APIRouter(prefix="/tenants", tags=["health-scores"])

def check_tenant_access(current_user: Any, tenant_id: uuid.UUID):
    user_tenant = current_user.get("tenant_id") if isinstance(current_user, dict) else getattr(current_user, "tenant_id", None)
    if not user_tenant or uuid.UUID(str(user_tenant)) != tenant_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized for this tenant")

class HealthScoreConfigSchema(BaseModel):
    churn_weight: float = Field(..., ge=0.0, le=1.0)
    usage_trend_weight: float = Field(..., ge=0.0, le=1.0)
    payment_health_weight: float = Field(..., ge=0.0, le=1.0)
    support_sentiment_weight: float = Field(..., ge=0.0, le=1.0)
    engagement_recency_weight: float = Field(..., ge=0.0, le=1.0)

class HealthScoreResponse(BaseModel):
    tenant_id: str
    customer_id: str
    health_score: float
    version: str
    as_of_date: datetime
    breakdown: dict[str, Any]

class ExpansionSignalResponse(BaseModel):
    probability: float
    top_drivers: list
    suggested_upsell_type: str
    model_version: str = "xgboost_expansion_v1"

@router.get("/{tenant_id}/health-score-config", response_model=HealthScoreConfigSchema)
async def get_health_score_config(
    tenant_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: Any = Depends(get_current_user)
):
    check_tenant_access(current_user, tenant_id)

    res = await db.execute(select(HealthScoreConfig).where(HealthScoreConfig.tenant_id == tenant_id))
    config = res.scalars().first()
    if not config:
        return HealthScoreConfigSchema(
            churn_weight=0.35,
            usage_trend_weight=0.25,
            payment_health_weight=0.20,
            support_sentiment_weight=0.0,
            engagement_recency_weight=0.20
        )
    return HealthScoreConfigSchema(
        churn_weight=config.churn_weight,
        usage_trend_weight=config.usage_trend_weight,
        payment_health_weight=config.payment_health_weight,
        support_sentiment_weight=config.support_sentiment_weight,
        engagement_recency_weight=config.engagement_recency_weight
    )

@router.put("/{tenant_id}/health-score-config", response_model=HealthScoreConfigSchema)
async def update_health_score_config(
    tenant_id: uuid.UUID,
    payload: HealthScoreConfigSchema,
    db: AsyncSession = Depends(get_db),
    current_user: Any = Depends(get_current_user)
):
    check_tenant_access(current_user, tenant_id)

    total_weight = (
        payload.churn_weight +
        payload.usage_trend_weight +
        payload.payment_health_weight +
        payload.support_sentiment_weight +
        payload.engagement_recency_weight
    )
    if abs(total_weight - 1.0) > 1e-4:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Health score weights must sum to 1.0 (got {total_weight:.4f})"
        )

    res = await db.execute(select(HealthScoreConfig).where(HealthScoreConfig.tenant_id == tenant_id))
    config = res.scalars().first()
    if not config:
        config = HealthScoreConfig(
            tenant_id=tenant_id,
            churn_weight=payload.churn_weight,
            usage_trend_weight=payload.usage_trend_weight,
            payment_health_weight=payload.payment_health_weight,
            support_sentiment_weight=payload.support_sentiment_weight,
            engagement_recency_weight=payload.engagement_recency_weight,
            updated_at=datetime.now(UTC)
        )
        db.add(config)
    else:
        config.churn_weight = payload.churn_weight
        config.usage_trend_weight = payload.usage_trend_weight
        config.payment_health_weight = payload.payment_health_weight
        config.support_sentiment_weight = payload.support_sentiment_weight
        config.engagement_recency_weight = payload.engagement_recency_weight
        config.updated_at = datetime.now(UTC)

    await db.commit()
    return payload

@router.get("/{tenant_id}/customers/{customer_id}/health-score", response_model=HealthScoreResponse)
async def get_customer_health_score(
    tenant_id: uuid.UUID,
    customer_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: Any = Depends(get_current_user)
):
    check_tenant_access(current_user, tenant_id)

    res_c = await db.execute(
        select(Customer).where(Customer.tenant_id == tenant_id, Customer.id == customer_id)
    )
    customer = res_c.scalars().first()
    if not customer:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Customer not found")

    res_hs = await db.execute(
        select(HealthScore)
        .where(HealthScore.tenant_id == tenant_id, HealthScore.customer_id == customer_id)
        .order_by(HealthScore.created_at.desc())
    )
    hs_record = res_hs.scalars().first()

    if hs_record:
        return HealthScoreResponse(
            tenant_id=str(tenant_id),
            customer_id=str(customer_id),
            health_score=hs_record.score,
            version=hs_record.version,
            as_of_date=hs_record.as_of_date,
            breakdown=hs_record.components
        )

    now = datetime.now(UTC)
    res_cfg = await db.execute(select(HealthScoreConfig).where(HealthScoreConfig.tenant_id == tenant_id))
    cfg = res_cfg.scalars().first()
    weights = {
        "churn_weight": cfg.churn_weight if cfg else 0.35,
        "usage_trend_weight": cfg.usage_trend_weight if cfg else 0.25,
        "payment_health_weight": cfg.payment_health_weight if cfg else 0.20,
        "support_sentiment_weight": cfg.support_sentiment_weight if cfg else 0.0,
        "engagement_recency_weight": cfg.engagement_recency_weight if cfg else 0.20,
    }

    df_feats = await extract_features(db, tenant_id, now)
    feat_dict = {}
    if not df_feats.empty:
        c_rows = df_feats[df_feats["customer_id"] == str(customer_id)]
        if not c_rows.empty:
            feat_dict = c_rows.iloc[0].to_dict()

    score, breakdown = compute_health_score(customer.churn_probability or 0.1, feat_dict, weights)

    return HealthScoreResponse(
        tenant_id=str(tenant_id),
        customer_id=str(customer_id),
        health_score=score,
        version="v1",
        as_of_date=now,
        breakdown=breakdown
    )

@router.get("/{tenant_id}/customers/{customer_id}/expansion-signal", response_model=ExpansionSignalResponse)
async def get_expansion_signal(
    tenant_id: uuid.UUID,
    customer_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: Any = Depends(get_current_user)
):
    check_tenant_access(current_user, tenant_id)

    res_c = await db.execute(
        select(Customer).where(Customer.tenant_id == tenant_id, Customer.id == customer_id)
    )
    customer = res_c.scalars().first()
    if not customer:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Customer not found")

    now = datetime.now(UTC)
    df_features = await extract_features(db, tenant_id, now)
    feature_dict = {}
    if not df_features.empty:
        c_rows = df_features[df_features["customer_id"] == str(customer_id)]
        if not c_rows.empty:
            feature_dict = c_rows.iloc[0].to_dict()

    try:
        proba, top_drivers, upsell_type = predict_expansion(feature_dict)
    except Exception:
        seat_trend = float(feature_dict.get("seat_count_trend", 0))
        usage_slope = float(feature_dict.get("usage_trend_slope", 0))
        proba = min(0.95, max(0.05, 0.2 + (seat_trend * 0.2) + (usage_slope * 0.3)))
        top_drivers = [
            {"feature": "seat_count_trend", "shap_value": 0.2, "raw_value": seat_trend, "human_readable": f"Seat trend: {seat_trend}"}
        ]
        upsell_type = "seat_expansion" if seat_trend > 0 else "tier_upgrade"

    customer.expansion_probability = proba
    customer.expansion_model_version = "xgboost_expansion_v1"
    customer.expansion_computed_at = now
    await db.commit()

    return ExpansionSignalResponse(
        probability=round(proba, 4),
        top_drivers=top_drivers,
        suggested_upsell_type=upsell_type
    )


