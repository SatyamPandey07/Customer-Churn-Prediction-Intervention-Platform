import os
import joblib
import pandas as pd
from typing import Dict, Any

MODEL_DIR = os.path.join(os.path.dirname(__file__), "models")
MODEL_PATH = os.path.join(MODEL_DIR, "xgboost_v1.joblib")

_model_cache = None

def load_model():
    global _model_cache
    if _model_cache is None:
        if not os.path.exists(MODEL_PATH):
            raise RuntimeError("Model artifact not found. Please train the model first.")
        _model_cache = joblib.load(MODEL_PATH)
    return _model_cache

def get_risk_tier(probability: float) -> str:
    if probability < 0.2:
        return "low"
    elif probability < 0.5:
        return "medium"
    elif probability < 0.8:
        return "high"
    else:
        return "critical"

def predict_churn(features: Dict[str, Any]) -> tuple[float, str, str]:
    """
    Returns (probability, risk_tier, model_version)
    """
    model_data = load_model()
    model = model_data["model"]
    feature_cols = model_data["features"]
    
    # Extract only the needed features in the correct order
    x_input = {col: features.get(col, 0.0) for col in feature_cols}
    df = pd.DataFrame([x_input])
    
    proba = float(model.predict_proba(df)[0][1])
    tier = get_risk_tier(proba)
    
    return proba, tier, "xgboost_v1"
