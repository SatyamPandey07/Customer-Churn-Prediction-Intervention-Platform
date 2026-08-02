import os
import uuid
import pandas as pd
import numpy as np
import xgboost as xgb
import joblib
from datetime import datetime, timedelta, timezone
from sklearn.model_selection import train_test_split
from sklearn.metrics import roc_auc_score, precision_score, recall_score, classification_report
from sqlalchemy import select, text
from apps.api.models import Customer, CustomerEvent, ChurnFeature
from apps.api.core.deps import engine
from apps.api.core.ml.features import extract_features, save_features
from sqlalchemy.ext.asyncio import async_sessionmaker, AsyncSession

AsyncSessionLocal = async_sessionmaker(bind=engine, class_=AsyncSession, expire_on_commit=False)

MODEL_DIR = os.path.join(os.path.dirname(__file__), "models")
MODEL_PATH = os.path.join(MODEL_DIR, "xgboost_v1.joblib")
FEATURE_COLS = [
    "mrr", "days_since_created", "plan_premium", "page_views_90d",
    "features_used_90d", "tickets_created_90d", "payment_failures_90d",
    "seat_count_trend", "usage_trend_slope", "days_since_last_event"
]

async def prepare_training_data(session: AsyncSession, tenant_id: uuid.UUID, as_of_date: datetime):
    # Enable RLS
    await session.execute(text(f"SET LOCAL app.current_tenant = '{tenant_id}'"))

    # Extract features
    df_features = await extract_features(session, tenant_id, as_of_date)
    if df_features.empty:
        return pd.DataFrame(), pd.Series()
    
    # Save features to feature store
    await save_features(session, tenant_id, as_of_date, df_features, version="v1")
    
    # Determine labels: did they churn within 30 days after as_of_date?
    end_date = as_of_date + timedelta(days=30)
    
    churn_events = await session.execute(
        select(CustomerEvent)
        .where(CustomerEvent.tenant_id == tenant_id)
        .where(CustomerEvent.event_type == "subscription_canceled")
        .where(CustomerEvent.occurred_at > as_of_date)
        .where(CustomerEvent.occurred_at <= end_date)
    )
    churned_customer_ids = {str(e.customer_id) for e in churn_events.scalars().all()}
    
    df_features["label"] = df_features["customer_id"].apply(lambda x: 1 if x in churned_customer_ids else 0)
    
    X = df_features[FEATURE_COLS]
    y = df_features["label"]
    
    return X, y

def train_model(X, y):
    if len(X) < 10:
        raise ValueError("Not enough data to train model")
        
    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42, stratify=y)
    
    # Handle class imbalance
    pos_cases = sum(y_train)
    neg_cases = len(y_train) - pos_cases
    scale_pos_weight = neg_cases / pos_cases if pos_cases > 0 else 1.0
    
    model = xgb.XGBClassifier(
        n_estimators=100,
        max_depth=4,
        learning_rate=0.1,
        scale_pos_weight=scale_pos_weight,
        use_label_encoder=False,
        eval_metric="logloss",
        random_state=42
    )
    
    model.fit(X_train, y_train)
    
    y_pred_proba = model.predict_proba(X_test)[:, 1]
    y_pred = model.predict(X_test)
    
    auc = roc_auc_score(y_test, y_pred_proba)
    precision = precision_score(y_test, y_pred, zero_division=0)
    recall = recall_score(y_test, y_pred, zero_division=0)
    
    metrics = {
        "auc_roc": auc,
        "precision": precision,
        "recall": recall
    }
    
    print(f"Model Metrics: AUC-ROC={auc:.3f}, Precision={precision:.3f}, Recall={recall:.3f}")
    
    # Save model
    os.makedirs(MODEL_DIR, exist_ok=True)
    joblib.dump({"model": model, "features": FEATURE_COLS, "metrics": metrics}, MODEL_PATH)
    
    return metrics

async def run_training_pipeline(tenant_id: uuid.UUID):
    async with AsyncSessionLocal() as session:
        as_of_date = datetime.now(timezone.utc) - timedelta(days=30)
        X, y = await prepare_training_data(session, tenant_id, as_of_date)
        metrics = train_model(X, y)
        return metrics

if __name__ == "__main__":
    import asyncio
    import sys
    
    if len(sys.argv) < 2:
        print("Usage: python train.py <tenant_id>")
        sys.exit(1)
        
    tenant_id = uuid.UUID(sys.argv[1])
    metrics = asyncio.run(run_training_pipeline(tenant_id))
    print("Training pipeline completed.")
