import pytest
import uuid
import pandas as pd
import numpy as np
import sqlalchemy
from datetime import datetime, timezone

from apps.api.models import Tenant, User, Customer, Role, PlanTier
from apps.api.core.ml.expansion import train_expansion_model, predict_expansion
from apps.api.core.security import create_access_token

@pytest.mark.asyncio
async def test_expansion_model_auc_roc_and_endpoint(client, db_session):
    tenant_id = uuid.uuid4()
    tenant = Tenant(id=tenant_id, name="Expansion Test", subdomain="exp-test", plan_tier=PlanTier.tier1)
    db_session.add(tenant)
    user_id = uuid.uuid4()
    user = User(id=user_id, tenant_id=tenant_id, email="admin@exptest.com", role=Role.owner)
    db_session.add(user)
    await db_session.commit()

    # 1. Generate Synthetic Dataset with 40 samples (20 expanding, 20 static)
    np.random.seed(42)
    rows = []
    for i in range(40):
        is_expansion = (i < 20)
        seat_trend = float(np.random.randint(2, 10)) if is_expansion else float(np.random.choice([0, -1, -2]))
        usage_slope = float(np.random.uniform(0.3, 1.5)) if is_expansion else float(np.random.uniform(-1.0, 0.0))
        features_used = float(np.random.randint(8, 25)) if is_expansion else float(np.random.randint(1, 5))
        
        feat = {
            "customer_id": str(uuid.uuid4()),
            "mrr": float(np.random.randint(100, 1000)),
            "days_since_created": int(np.random.randint(30, 365)),
            "plan_premium": 1 if is_expansion else 0,
            "page_views_90d": int(np.random.randint(200, 1000)) if is_expansion else int(np.random.randint(10, 100)),
            "features_used_90d": features_used,
            "tickets_created_90d": int(np.random.randint(0, 2)),
            "payment_failures_90d": 0,
            "seat_count_trend": seat_trend,
            "usage_trend_slope": usage_slope,
            "days_since_last_event": int(np.random.randint(0, 3))
        }
        rows.append(feat)

    df_feats = pd.DataFrame(rows)
    df_feats["label"] = [1 if i < 20 else 0 for i in range(40)]

    from apps.api.core.ml.expansion import FEATURE_COLS
    X = df_feats[FEATURE_COLS]
    y = df_feats["label"]

    # Train model and assert AUC-ROC >= 0.72
    metrics = train_expansion_model(X, y)
    assert metrics["auc_roc"] >= 0.72, f"AUC-ROC {metrics['auc_roc']} below required 0.72 threshold"

    # Test prediction function
    expanding_sample = rows[0]
    proba, top_drivers, upsell_type = predict_expansion(expanding_sample)
    assert 0.0 <= proba <= 1.0
    assert len(top_drivers) > 0
    assert upsell_type in ["seat_expansion", "tier_upgrade", "enterprise_custom_addon", "cross_sell_module"]

    # 2. Test Expansion API Endpoint
    token = create_access_token(user.email, role=user.role.value, tenant_id=str(tenant_id))
    headers = {"Authorization": f"Bearer {token}"}

    # Add customer
    c_id = uuid.uuid4()
    await db_session.execute(sqlalchemy.text(f"SET LOCAL app.current_tenant = '{tenant_id}'"))
    c = Customer(
        id=c_id,
        tenant_id=tenant_id,
        external_ids={"stripe": "cus_exp_1"},
        plan="standard",
        mrr=500.0
    )
    db_session.add(c)
    await db_session.commit()

    res_exp = await client.get(f"/tenants/{tenant_id}/customers/{c_id}/expansion-signal", headers=headers)
    assert res_exp.status_code == 200
    exp_data = res_exp.json()
    assert 0.0 <= exp_data["probability"] <= 1.0
    assert "top_drivers" in exp_data
    assert "suggested_upsell_type" in exp_data
