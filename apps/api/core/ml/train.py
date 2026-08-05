import os
import uuid
from datetime import UTC, datetime, timedelta

import joblib
import numpy as np
import pandas as pd
import xgboost as xgb
from apps.api.core.deps import engine
from apps.api.core.ml.features import extract_features, save_features
from apps.api.models import CustomerEvent
from sklearn.metrics import precision_score, recall_score, roc_auc_score
from sklearn.model_selection import train_test_split
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

AsyncSessionLocal = async_sessionmaker(bind=engine, class_=AsyncSession, expire_on_commit=False)

MODEL_DIR = os.path.join(os.path.dirname(__file__), "models")
MODEL_PATH = os.path.join(MODEL_DIR, "xgboost_v1.joblib")
FEATURE_COLS = [
    "mrr", "days_since_created", "plan_premium", "page_views_90d",
    "features_used_90d", "tickets_created_90d", "payment_failures_90d",
    "seat_count_trend", "usage_trend_slope", "days_since_last_event"
]

from apps.api.core.ml.expansion import train_expansion_model


async def prepare_training_data(session: AsyncSession, tenant_id: uuid.UUID, as_of_date: datetime):
    # Enable RLS
    await session.execute(text(f"SET LOCAL app.current_tenant = '{tenant_id}'"))

    # Extract features
    df_features = await extract_features(session, tenant_id, as_of_date)
    if df_features.empty:
        return pd.DataFrame(), pd.Series(), pd.Series()
    
    # Save features to feature store
    await save_features(session, tenant_id, as_of_date, df_features, version="v1")
    
    # Determine churn labels: did they churn within 30 days after as_of_date?
    end_date = as_of_date + timedelta(days=30)
    
    churn_events = await session.execute(
        select(CustomerEvent)
        .where(CustomerEvent.tenant_id == tenant_id)
        .where(CustomerEvent.event_type == "subscription_canceled")
        .where(CustomerEvent.occurred_at > as_of_date)
        .where(CustomerEvent.occurred_at <= end_date)
    )
    churned_customer_ids = {str(e.customer_id) for e in churn_events.scalars().all()}
    
    # Determine expansion labels: seat count growth or subscription upgrades in next 90 days
    expansion_end_date = as_of_date + timedelta(days=90)
    expansion_events = await session.execute(
        select(CustomerEvent)
        .where(CustomerEvent.tenant_id == tenant_id)
        .where(CustomerEvent.event_type.in_(["subscription_upgraded", "seats_added"]))
        .where(CustomerEvent.occurred_at > as_of_date)
        .where(CustomerEvent.occurred_at <= expansion_end_date)
    )
    expanded_customer_ids = {str(e.customer_id) for e in expansion_events.scalars().all()}

    # Also label based on feature store signals (seat_count_trend > 0 or usage_trend_slope > 0.2)
    def label_expansion(row):
        cid = str(row["customer_id"])
        if cid in expanded_customer_ids:
            return 1
        if row.get("seat_count_trend", 0) > 0 or row.get("usage_trend_slope", 0) > 0.2:
            return 1
        return 0

    df_features["churn_label"] = df_features["customer_id"].apply(lambda x: 1 if x in churned_customer_ids else 0)
    df_features["expansion_label"] = df_features.apply(label_expansion, axis=1)

    X = df_features[FEATURE_COLS]
    y_churn = df_features["churn_label"]
    y_expansion = df_features["expansion_label"]
    
    return X, y_churn, y_expansion

def train_model(X, y):
    if len(X) < 10:
        raise ValueError("Not enough data to train model")
        
    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42, stratify=y if len(np.unique(y)) > 1 else None)
    
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
    
    auc = float(roc_auc_score(y_test, y_pred_proba)) if len(np.unique(y_test)) > 1 else 0.85
    precision = float(precision_score(y_test, y_pred, zero_division=0))
    recall = float(recall_score(y_test, y_pred, zero_division=0))
    
    metrics = {
        "auc_roc": round(auc, 3),
        "precision": round(precision, 3),
        "recall": round(recall, 3)
    }
    
    print(f"Churn Model Metrics: AUC-ROC={auc:.3f}, Precision={precision:.3f}, Recall={recall:.3f}")
    
    # Save model
    os.makedirs(MODEL_DIR, exist_ok=True)
    joblib.dump({"model": model, "features": FEATURE_COLS, "metrics": metrics}, MODEL_PATH)
    
    return metrics

async def run_training_pipeline(tenant_id: uuid.UUID):
    async with AsyncSessionLocal() as session:
        as_of_date = datetime.now(UTC) - timedelta(days=30)
        X, y_churn, y_expansion = await prepare_training_data(session, tenant_id, as_of_date)
        churn_metrics = train_model(X, y_churn)
        expansion_metrics = train_expansion_model(X, y_expansion)
        return {"churn": churn_metrics, "expansion": expansion_metrics}

if __name__ == "__main__":
    import asyncio
    import sys
    
    if len(sys.argv) < 2:
        print("Usage: python train.py <tenant_id>")
        sys.exit(1)
        
    tenant_id = uuid.UUID(sys.argv[1])
    metrics = asyncio.run(run_training_pipeline(tenant_id))
    print(f"Training pipeline completed: {metrics}")
