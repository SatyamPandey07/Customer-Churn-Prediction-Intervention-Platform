import uuid
import pandas as pd
from datetime import datetime, timedelta
from sqlalchemy import select, text
from apps.api.models import Customer, CustomerEvent, ChurnFeature
from sqlalchemy.ext.asyncio import AsyncSession

async def extract_features(session: AsyncSession, tenant_id: uuid.UUID, as_of_date: datetime):
    """
    Extracts features for all active customers for a given tenant as of a specific date.
    Returns a pandas DataFrame.
    """
    # 1. Get all active customers as of date
    result = await session.execute(
        select(Customer).where(Customer.tenant_id == tenant_id).where(Customer.created_at <= as_of_date)
    )
    customers = result.scalars().all()
    
    if not customers:
        return pd.DataFrame()
        
    start_date = as_of_date - timedelta(days=90)
    
    # 2. Get all events in the last 90 days
    events_result = await session.execute(
        select(CustomerEvent)
        .where(CustomerEvent.tenant_id == tenant_id)
        .where(CustomerEvent.occurred_at <= as_of_date)
        .where(CustomerEvent.occurred_at >= start_date)
    )
    events = events_result.scalars().all()
    
    # Process events into DataFrame
    events_data = [{
        "customer_id": str(e.customer_id),
        "event_type": e.event_type,
        "occurred_at": e.occurred_at,
        "properties": e.properties
    } for e in events]
    df_events = pd.DataFrame(events_data)
    
    features_list = []
    
    for c in customers:
        cid = str(c.id)
        c_events = df_events[df_events["customer_id"] == cid] if not df_events.empty else pd.DataFrame()
        
        # Base features
        feat = {
            "customer_id": cid,
            "mrr": float(c.mrr or 0.0),
            "days_since_created": (as_of_date - c.created_at).days,
            "plan_premium": 1 if c.plan == "premium" else 0
        }
        
        if c_events.empty:
            feat.update({
                "page_views_90d": 0,
                "features_used_90d": 0,
                "tickets_created_90d": 0,
                "payment_failures_90d": 0,
                "seat_count_trend": 0.0,
                "usage_trend_slope": 0.0,
                "days_since_last_event": 90
            })
        else:
            feat["page_views_90d"] = len(c_events[c_events["event_type"] == "page_view"])
            feat["features_used_90d"] = len(c_events[c_events["event_type"] == "feature_used"])
            feat["tickets_created_90d"] = len(c_events[c_events["event_type"] == "ticket_created"])
            feat["payment_failures_90d"] = len(c_events[c_events["event_type"] == "invoice.failed"])
            
            # Seat count trend
            sub_updates = c_events[c_events["event_type"] == "subscription_updated"].sort_values("occurred_at")
            if not sub_updates.empty:
                first_seats = sub_updates.iloc[0]["properties"].get("seat_count", 0)
                last_seats = sub_updates.iloc[-1]["properties"].get("seat_count", 0)
                feat["seat_count_trend"] = float(int(last_seats) - int(first_seats))
            else:
                feat["seat_count_trend"] = 0.0
                
            # Recent vs Past usage
            recent_30d = c_events[c_events["occurred_at"] >= (as_of_date - timedelta(days=30))]
            past_60d = c_events[c_events["occurred_at"] < (as_of_date - timedelta(days=30))]
            
            pv_30d = len(recent_30d[recent_30d["event_type"] == "page_view"])
            pv_60d = len(past_60d[past_60d["event_type"] == "page_view"])
            # Average daily views 30d vs 60d
            feat["usage_trend_slope"] = float((pv_30d / 30.0) - (pv_60d / 60.0) if pv_60d > 0 else 0)
            
            last_event = c_events["occurred_at"].max()
            feat["days_since_last_event"] = (as_of_date - last_event).days if pd.notnull(last_event) else 90

        features_list.append(feat)
        
    df_features = pd.DataFrame(features_list)
    return df_features

async def save_features(session: AsyncSession, tenant_id: uuid.UUID, as_of_date: datetime, df_features: pd.DataFrame, version="v1"):
    """
    Save extracted features to the feature store (churn_features table)
    """
    if df_features.empty:
        return
        
    for _, row in df_features.iterrows():
        feature_dict = row.drop("customer_id").to_dict()
        
        # Check if exists
        res = await session.execute(
            select(ChurnFeature)
            .where(ChurnFeature.tenant_id == tenant_id)
            .where(ChurnFeature.customer_id == uuid.UUID(row["customer_id"]))
            .where(ChurnFeature.as_of_date == as_of_date)
            .where(ChurnFeature.feature_set_version == version)
        )
        existing = res.scalars().first()
        if existing:
            existing.features = feature_dict
        else:
            cf = ChurnFeature(
                tenant_id=tenant_id,
                customer_id=uuid.UUID(row["customer_id"]),
                as_of_date=as_of_date,
                feature_set_version=version,
                features=feature_dict
            )
            session.add(cf)
    await session.commit()
