import os
import joblib
import pandas as pd
from typing import Dict, Any

import shap
from pydantic import BaseModel, Field
import xgboost as xgb
from google import genai
from apps.api.core.secrets import secrets_manager

GEMINI_API_KEY = secrets_manager.get_secret("GEMINI_API_KEY") or os.environ.get("GEMINI_API_KEY")

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

def generate_human_readable(feature_name: str, raw_value: float) -> str:
    if feature_name == "mrr":
        return f"Monthly Recurring Revenue is ${raw_value:.2f}"
    elif feature_name == "days_since_created":
        return f"Customer tenure is {int(raw_value)} days"
    elif feature_name == "page_views_90d":
        return f"{int(raw_value)} page views in the last 90 days"
    elif feature_name == "features_used_90d":
        return f"{int(raw_value)} features used in the last 90 days"
    elif feature_name == "tickets_created_90d":
        return f"{int(raw_value)} support tickets created in the last 90 days"
    elif feature_name == "payment_failures_90d":
        return f"{int(raw_value)} failed payments in the last 90 days"
    elif feature_name == "seat_count_trend":
        direction = "decreased" if raw_value < 0 else "increased"
        return f"Seat count {direction} by {abs(int(raw_value))} recently"
    elif feature_name == "usage_trend_slope":
        direction = "down" if raw_value < 0 else "up"
        return f"Daily usage is trending {direction} (slope: {raw_value:.2f})"
    elif feature_name == "days_since_last_event":
        return f"Last active {int(raw_value)} days ago"
    elif feature_name == "plan_premium":
        return "On premium plan" if raw_value > 0 else "On basic plan"
    return f"{feature_name}: {raw_value}"

def predict_churn(features: Dict[str, Any]) -> tuple[float, str, str, list]:
    """
    Returns (probability, risk_tier, model_version, top_drivers)
    """
    model_data = load_model()
    model = model_data["model"]
    feature_cols = model_data["features"]
    
    # Extract only the needed features in the correct order
    x_input = {col: features.get(col, 0.0) for col in feature_cols}
    df = pd.DataFrame([x_input])
    
    proba = float(model.predict_proba(df)[0][1])
    tier = get_risk_tier(proba)
    
    # Compute SHAP
    explainer = shap.TreeExplainer(model)
    shap_values = explainer.shap_values(df)
    
    if isinstance(shap_values, list):
        sv = shap_values[1][0]
    else:
        if len(shap_values.shape) == 2:
            sv = shap_values[0]
        else:
            sv = shap_values
            
    drivers = []
    for col, val, shape_v in zip(feature_cols, df.iloc[0], sv):
        drivers.append({
            "feature": col,
            "shap_value": float(shape_v),
            "raw_value": float(val),
            "human_readable": generate_human_readable(col, val)
        })
        
    top_drivers = sorted(drivers, key=lambda x: abs(x["shap_value"]), reverse=True)[:3]
    
    return proba, tier, "xgboost_v1", top_drivers
