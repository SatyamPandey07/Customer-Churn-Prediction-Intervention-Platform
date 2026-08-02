import pytest
import uuid
import pandas as pd
from datetime import datetime, timezone
import os
import sqlalchemy

from apps.api.models import Customer, CustomerEvent, ChurnFeature, PlanTier, Tenant
from apps.api.core.ml.features import extract_features
from apps.api.core.ml.train import train_model
from apps.api.core.ml.predict import predict_churn

@pytest.mark.asyncio
async def test_feature_engineering_and_model(db_session, client):
    tenant_id = uuid.uuid4()
    
    # 1. Setup Tenant
    tenant = Tenant(id=tenant_id, name="Test ML", subdomain="ml-test", plan_tier=PlanTier.tier1)
    db_session.add(tenant)
    await db_session.commit()
    
    await db_session.execute(sqlalchemy.text(f"SET LOCAL app.current_tenant = '{tenant_id}'"))
    
    now = datetime.now(timezone.utc)
    
    # Create 20 synthetic customers (10 churned, 10 retained)
    for i in range(20):
        is_churner = (i < 10)
        c_id = uuid.uuid4()
        c = Customer(
            id=c_id, tenant_id=tenant_id, external_ids={"stripe": f"cus_{c_id}"},
            plan="premium", mrr=50.0, created_at=now - pd.Timedelta(days=60),
            first_seen_at=now - pd.Timedelta(days=60), last_seen_at=now
        )
        db_session.add(c)
        
        # Add events
        if is_churner:
            # high ticket count, low page views
            for _ in range(5):
                db_session.add(CustomerEvent(
                    tenant_id=tenant_id, customer_id=c_id, source="zendesk", external_event_id=str(uuid.uuid4()),
                    event_type="ticket_created", properties={}, occurred_at=now - pd.Timedelta(days=5)
                ))
            db_session.add(CustomerEvent(
                tenant_id=tenant_id, customer_id=c_id, source="stripe", external_event_id=str(uuid.uuid4()),
                event_type="subscription_canceled", properties={}, occurred_at=now + pd.Timedelta(days=5)
            ))
        else:
            # high page views, no tickets
            for _ in range(10):
                db_session.add(CustomerEvent(
                    tenant_id=tenant_id, customer_id=c_id, source="segment", external_event_id=str(uuid.uuid4()),
                    event_type="page_view", properties={}, occurred_at=now - pd.Timedelta(days=5)
                ))
    
    await db_session.commit()
    
    # 2. Test feature extraction
    df_features = await extract_features(db_session, tenant_id, now)
    assert not df_features.empty
    assert len(df_features) == 20
    
    # Check specific features
    churner = df_features.iloc[0]
    assert churner["tickets_created_90d"] == 5
    assert churner["page_views_90d"] == 0
    
    retained = df_features.iloc[10]
    assert retained["tickets_created_90d"] == 0
    assert retained["page_views_90d"] == 10
    
    # 3. Test Model Training
    # Apply labels
    churn_events = await db_session.execute(
        sqlalchemy.select(CustomerEvent)
        .where(CustomerEvent.tenant_id == tenant_id)
        .where(CustomerEvent.event_type == "subscription_canceled")
    )
    churned_ids = {str(e.customer_id) for e in churn_events.scalars().all()}
    df_features["label"] = df_features["customer_id"].apply(lambda x: 1 if x in churned_ids else 0)
    
    from apps.api.core.ml.train import FEATURE_COLS
    X = df_features[FEATURE_COLS]
    y = df_features["label"]
    
    metrics = train_model(X, y)
    
    assert metrics["auc_roc"] >= 0.75
    
    # 4. Test Predict API
    # Login as tenant owner to test prediction endpoint
    await client.post("/auth/signup", json={
        "tenant_name": "ML API Test", "subdomain": "ml-api", "email": "admin@ml.com", "password": "Password123!"
    })
    resp = await client.post("/auth/login", data={"username": "admin@ml.com", "password": "Password123!"})
    token = resp.json()["access_token"]
    
    # Wait, the customer we created is for tenant `tenant_id` which does not have this user.
    # We should just test predict_churn function directly
    proba, tier, version = predict_churn(churner.to_dict())
    assert 0.0 <= proba <= 1.0
    assert tier in ["low", "medium", "high", "critical"]
    assert version == "xgboost_v1"
