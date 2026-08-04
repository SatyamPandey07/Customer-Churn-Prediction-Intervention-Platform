from typing import Dict, Any, Tuple

def compute_health_score(
    churn_probability: float,
    feature_dict: Dict[str, Any],
    weights: Dict[str, float]
) -> Tuple[float, Dict[str, Any]]:
    """
    Computes a 0-100 composite health score and itemized breakdown.
    
    Weights dictionary expected keys:
    - churn_weight (default 0.35)
    - usage_trend_weight (default 0.25)
    - payment_health_weight (default 0.20)
    - support_sentiment_weight (default 0.0)
    - engagement_recency_weight (default 0.20)
    """
    w_churn = weights.get("churn_weight", 0.35)
    w_usage = weights.get("usage_trend_weight", 0.25)
    w_payment = weights.get("payment_health_weight", 0.20)
    w_sentiment = weights.get("support_sentiment_weight", 0.0)
    w_recency = weights.get("engagement_recency_weight", 0.20)

    # 1. Churn inverse (0-100)
    raw_churn_prob = float(churn_probability or 0.0)
    churn_score = max(0.0, min(100.0, (1.0 - raw_churn_prob) * 100.0))

    # 2. Usage trend (slope -> 0-100)
    slope = float(feature_dict.get("usage_trend_slope", 0.0))
    usage_trend_score = max(0.0, min(100.0, 50.0 + (slope * 50.0)))

    # 3. Payment health (0-100)
    payment_failures = float(feature_dict.get("payment_failures_90d", 0))
    payment_health_score = max(0.0, min(100.0, 100.0 - (payment_failures * 25.0)))

    # 4. Support sentiment score (0-100 stub neutral)
    support_sentiment_score = 50.0

    # 5. Engagement recency (0-100)
    days_since_last = float(feature_dict.get("days_since_last_event", 90))
    engagement_recency_score = max(0.0, min(100.0, 100.0 - (days_since_last * 2.0)))

    # Composite weighted score
    composite_score = (
        (churn_score * w_churn) +
        (usage_trend_score * w_usage) +
        (payment_health_score * w_payment) +
        (support_sentiment_score * w_sentiment) +
        (engagement_recency_score * w_recency)
    )
    composite_score = round(max(0.0, min(100.0, composite_score)), 2)

    breakdown = {
        "churn": {
            "weight": w_churn,
            "raw_input": raw_churn_prob,
            "normalized_score": round(churn_score, 2),
            "weighted_contribution": round(churn_score * w_churn, 2),
            "description": f"Inverse churn risk ({raw_churn_prob*100:.1f}% risk)"
        },
        "usage_trend": {
            "weight": w_usage,
            "raw_input": slope,
            "normalized_score": round(usage_trend_score, 2),
            "weighted_contribution": round(usage_trend_score * w_usage, 2),
            "description": f"Daily active usage trajectory (slope: {slope:.2f})"
        },
        "payment_health": {
            "weight": w_payment,
            "raw_input": payment_failures,
            "normalized_score": round(payment_health_score, 2),
            "weighted_contribution": round(payment_health_score * w_payment, 2),
            "description": f"Invoice billing status ({int(payment_failures)} failures in 90d)"
        },
        "support_sentiment": {
            "weight": w_sentiment,
            "raw_input": 0.0,
            "normalized_score": round(support_sentiment_score, 2),
            "weighted_contribution": round(support_sentiment_score * w_sentiment, 2),
            "description": "CS Ticket Sentiment Score (Stub 50/100 until PR-14)"
        },
        "engagement_recency": {
            "weight": w_recency,
            "raw_input": days_since_last,
            "normalized_score": round(engagement_recency_score, 2),
            "weighted_contribution": round(engagement_recency_score * w_recency, 2),
            "description": f"Last activity recency ({int(days_since_last)} days ago)"
        }
    }

    return composite_score, breakdown
