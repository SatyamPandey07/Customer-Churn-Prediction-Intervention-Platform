import uuid
from datetime import UTC, datetime

from apps.api.core.deps import get_current_user, get_db
from apps.api.core.ml.features import extract_features
from apps.api.core.ml.predict import predict_churn
from apps.api.core.queue import publish_churn_update
from apps.api.models import Customer
from fastapi import APIRouter, Depends, HTTPException
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

