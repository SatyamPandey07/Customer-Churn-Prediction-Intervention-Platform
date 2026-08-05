import uuid
from datetime import UTC, datetime

from apps.api.core.deps import get_current_user, get_db
from apps.api.core.ml.features import extract_features
from apps.api.core.ml.interventions import InterventionItem, generate_intervention
from apps.api.core.ml.predict import predict_churn
from apps.api.models import Customer
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

router = APIRouter(prefix="/customers", tags=["Explanations"])

class ChurnDriver(BaseModel):
    feature: str
    shap_value: float
    raw_value: float
    human_readable: str

class ChurnExplanationResponse(BaseModel):
    risk_tier: str
    probability: float
    top_drivers: list[ChurnDriver]
    interventions: list[InterventionItem]
    intervention_confidence: float

@router.get("/{customer_id}/churn-explanation", response_model=ChurnExplanationResponse)
async def get_churn_explanation(
    customer_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    tenant_id = uuid.UUID(current_user["tenant_id"])
    
    result = await db.execute(
        select(Customer)
        .where(Customer.id == customer_id)
        .where(Customer.tenant_id == tenant_id)
    )
    customer = result.scalars().first()
    
    if not customer:
        raise HTTPException(status_code=404, detail="Customer not found")
        
    now = datetime.now(UTC)
    
    # 1. Compute Features
    df_features = await extract_features(db, tenant_id, now)
    if df_features.empty:
        raise HTTPException(status_code=400, detail="Not enough data to compute churn risk")
        
    c_features = df_features[df_features["customer_id"] == str(customer_id)]
    if c_features.empty:
        raise HTTPException(status_code=400, detail="Could not compute features for this customer")
        
    feature_dict = c_features.iloc[0].drop("customer_id").to_dict()
    
    # 2. Get Prediction and SHAP top drivers
    try:
        proba, tier, model_version, top_drivers = predict_churn(feature_dict)
    except RuntimeError as e:
        raise HTTPException(status_code=503, detail=str(e))
        
    # 3. Generate Gemini Interventions
    customer_meta = {
        "mrr": float(customer.mrr or 0.0),
        "plan": customer.plan,
        "tenure_days": (now - customer.created_at).days
    }
    
    intervention_resp = await generate_intervention(
        customer_id=str(customer_id),
        churn_prob=proba,
        risk_tier=tier,
        drivers=top_drivers,
        customer_meta=customer_meta,
        feature_set_version="v1",
        model_version=model_version
    )
    
    return ChurnExplanationResponse(
        risk_tier=tier,
        probability=proba,
        top_drivers=[ChurnDriver(**d) for d in top_drivers],
        interventions=intervention_resp.recommended_interventions,
        intervention_confidence=intervention_resp.confidence
    )
