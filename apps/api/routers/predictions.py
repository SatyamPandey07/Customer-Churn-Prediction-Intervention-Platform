import uuid
from datetime import UTC, datetime
from typing import Any

from apps.api.core.deps import get_current_user, get_db
from apps.api.core.ml.features import extract_features
from apps.api.core.ml.predict import predict_churn
from apps.api.core.queue import publish_churn_update
from apps.api.models import Customer
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, ConfigDict
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession


class CustomerListResponse(BaseModel):
    id: uuid.UUID
    plan: str | None = None
    mrr: float = 0.0
    churn_probability: float | None = None
    churn_risk_tier: str | None = None
    model_config = ConfigDict(from_attributes=True)

router = APIRouter(prefix="/customers", tags=["Predictions"])

@router.get("", response_model=list[CustomerListResponse])
async def list_customers(
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    tenant_id = uuid.UUID(current_user["tenant_id"])
    result = await db.execute(
        select(Customer)
        .where(Customer.tenant_id == tenant_id)
        .order_by(Customer.mrr.desc())
    )
    customers = result.scalars().all()
    return customers

@router.get("/{customer_id}/churn-risk")
async def get_churn_risk(
    customer_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    tenant_id = uuid.UUID(current_user["tenant_id"])
    
    # 1. Fetch customer
    result = await db.execute(
        select(Customer)
        .where(Customer.id == customer_id)
        .where(Customer.tenant_id == tenant_id)
    )
    customer = result.scalars().first()
    
    if not customer:
        raise HTTPException(status_code=404, detail="Customer not found")
        
    # 2. Check if cached prediction is fresh (e.g. less than 24h old)
    now = datetime.now(UTC)
    if customer.churn_computed_at and (now - customer.churn_computed_at).days < 1:
        return {
            "probability": customer.churn_probability,
            "risk_tier": customer.churn_risk_tier,
            "model_version": customer.churn_model_version,
            "computed_at": customer.churn_computed_at
        }
        
    # 3. Compute on the fly if stale
    df_features = await extract_features(db, tenant_id, now)
    if df_features.empty:
        raise HTTPException(status_code=400, detail="Not enough data to compute churn risk")
        
    c_features = df_features[df_features["customer_id"] == str(customer_id)]
    if c_features.empty:
        raise HTTPException(status_code=400, detail="Could not compute features for this customer")
        
    feature_dict = c_features.iloc[0].drop("customer_id").to_dict()
    
    try:
        proba, tier, model_version, _ = predict_churn(feature_dict)
    except RuntimeError as e:
        raise HTTPException(status_code=503, detail=str(e))
    
    # Update cache
    customer.churn_probability = proba
    customer.churn_risk_tier = tier
    customer.churn_model_version = model_version
    customer.churn_computed_at = now
    await db.commit()
    
    # Publish to Redis
    await publish_churn_update(str(tenant_id), str(customer_id), proba, tier)
    
    return {
        "probability": proba,
        "risk_tier": tier,
        "model_version": model_version,
        "computed_at": now
    }

from apps.api.core.ml.expansion import predict_expansion


class ExpansionSignalResponse(BaseModel):
    probability: float
    top_drivers: list[dict[str, Any]]
    suggested_upsell_type: str
    model_version: str = "xgboost_expansion_v1"

@router.get("/tenants/{tenant_id}/customers/{customer_id}/expansion-signal", response_model=ExpansionSignalResponse)
async def get_expansion_signal(
    tenant_id: uuid.UUID,
    customer_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    user_tenant = uuid.UUID(current_user["tenant_id"]) if isinstance(current_user, dict) else current_user.tenant_id
    if user_tenant != tenant_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized for this tenant")

    result = await db.execute(
        select(Customer)
        .where(Customer.id == customer_id)
        .where(Customer.tenant_id == tenant_id)
    )
    customer = result.scalars().first()
    if not customer:
        raise HTTPException(status_code=404, detail="Customer not found")

    now = datetime.now(UTC)
    df_features = await extract_features(db, tenant_id, now)
    if df_features.empty:
        # Default baseline if empty features
        return ExpansionSignalResponse(
            probability=0.1,
            top_drivers=[],
            suggested_upsell_type="cross_sell_module"
        )

    c_features = df_features[df_features["customer_id"] == str(customer_id)]
    feature_dict = c_features.iloc[0].to_dict() if not c_features.empty else {}

    try:
        proba, top_drivers, upsell_type = predict_expansion(feature_dict)
    except RuntimeError:
        # Fallback prediction if model not trained yet
        seat_trend = float(feature_dict.get("seat_count_trend", 0))
        usage_slope = float(feature_dict.get("usage_trend_slope", 0))
        proba = min(0.95, max(0.05, 0.2 + (seat_trend * 0.2) + (usage_slope * 0.3)))
        top_drivers = [
            {"feature": "seat_count_trend", "shap_value": 0.2, "raw_value": seat_trend, "human_readable": f"Seat trend: {seat_trend}"}
        ]
        upsell_type = "seat_expansion" if seat_trend > 0 else "tier_upgrade"

    # Cache expansion proba on customer
    customer.expansion_probability = proba
    customer.expansion_model_version = "xgboost_expansion_v1"
    customer.expansion_computed_at = now
    await db.commit()

    return ExpansionSignalResponse(
        probability=round(proba, 4),
        top_drivers=top_drivers,
        suggested_upsell_type=upsell_type
    )
