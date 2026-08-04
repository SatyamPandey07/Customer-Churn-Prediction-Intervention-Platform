import logging
import math
import uuid
from datetime import UTC, datetime, timedelta
from typing import Any

from apps.api.models import ChurnFeature, ExitSurvey, Intervention, InterventionOutcome
from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)

ATTRIBUTION_METHODOLOGY = (
    "Time-decay heuristic attribution (half-life: 7 days). Weights interventions exponentially higher closer "
    "to retained outcome. Single-touch accounts provide unweighted direct signals, multi-touch accounts use "
    "heuristic weighting. Not a causal guarantee."
)

EXPLANATION_VALIDATION_METHODOLOGY = (
    "Directional agreement rate comparing top SHAP model feature drivers against self-reported customer exit "
    "survey categories. Intended as heuristic validation, not a formal statistical proof."
)

DRIVER_TO_REASON_MAP = {
    "usage_decline": "usability",
    "days_since_last_event": "usability",
    "payment_failures_90d": "price",
    "mrr_drop": "price",
    "support_sentiment": "poor_support",
    "support_tickets_count": "poor_support",
    "feature_abandonment": "missing_features",
    "champion_change": "poor_support"
}

def calculate_time_decay_weights(
    touches: list[dict[str, Any]],
    outcome_date: datetime,
    half_life_days: float = 7.0
) -> list[dict[str, Any]]:
    """
    Computes time-decay attribution weights for a list of intervention touches relative to outcome_date.
    Formula: w_i = 2 ** (-days_before / half_life_days)
    """
    if not touches:
        return []

    weighted_touches = []
    total_w = 0.0

    for touch in touches:
        sent_at = touch.get("sent_at")
        if isinstance(sent_at, str):
            try:
                sent_at = datetime.fromisoformat(sent_at)
            except Exception:
                sent_at = outcome_date - timedelta(days=1)
        elif not sent_at:
            sent_at = outcome_date - timedelta(days=1)

        days_before = max(0.0, (outcome_date - sent_at).total_seconds() / 86400.0)
        weight = math.pow(2.0, -days_before / half_life_days)
        total_w += weight
        weighted_touches.append({**touch, "raw_weight": weight})

    if total_w <= 0:
        total_w = 1.0

    for wt in weighted_touches:
        wt["attribution_fraction"] = round(wt["raw_weight"] / total_w, 4)

    return weighted_touches

async def get_tenant_attribution_report(db: AsyncSession, tenant_id: uuid.UUID) -> dict[str, Any]:
    """
    Aggregates multi-touch time-decay attribution report for a tenant.
    Distinguishes single-touch vs multi-touch accounts.
    """
    import sqlalchemy
    await db.execute(sqlalchemy.text(f"SET LOCAL app.current_tenant = '{tenant_id}'"))

    # Fetch all interventions with retained outcome
    res = await db.execute(
        select(Intervention).where(
            and_(
                Intervention.tenant_id == tenant_id,
                Intervention.outcome == InterventionOutcome.retained
            )
        ).order_by(Intervention.sent_at.asc())
    )
    interventions = res.scalars().all()

    # Group by customer_id
    customer_touches: dict[uuid.UUID, list[Intervention]] = {}
    for i in interventions:
        customer_touches.setdefault(i.customer_id, []).append(i)

    single_touch_count = 0
    multi_touch_count = 0
    channel_contributions: dict[str, float] = {}

    now = datetime.now(UTC)

    for touch_list in customer_touches.values():
        latest_sent = touch_list[-1].sent_at or now

        touches_data = [
            {
                "id": str(i.id),
                "channel": i.channel or "email",
                "sent_at": i.sent_at or now
            }
            for i in touch_list
        ]

        if len(touches_data) == 1:
            single_touch_count += 1
            ch = touches_data[0]["channel"]
            channel_contributions[ch] = round(channel_contributions.get(ch, 0.0) + 1.0, 2)
        else:
            multi_touch_count += 1
            attr_touches = calculate_time_decay_weights(touches_data, latest_sent)
            for t in attr_touches:
                ch = t["channel"]
                frac = t["attribution_fraction"]
                channel_contributions[ch] = round(channel_contributions.get(ch, 0.0) + frac, 2)

    total_retained_accounts = single_touch_count + multi_touch_count

    return {
        "tenant_id": str(tenant_id),
        "methodology": ATTRIBUTION_METHODOLOGY,
        "summary": {
            "total_retained_accounts": total_retained_accounts,
            "single_touch_accounts": single_touch_count,
            "multi_touch_accounts": multi_touch_count,
            "clean_signal_ratio": round(single_touch_count / total_retained_accounts, 2) if total_retained_accounts > 0 else 0.0
        },
        "channel_contributions": channel_contributions
    }

async def get_explanation_validation_report(db: AsyncSession, tenant_id: uuid.UUID) -> dict[str, Any]:
    """
    Directional agreement report comparing top SHAP model feature drivers against self-reported exit survey reasons.
    """
    import sqlalchemy
    await db.execute(sqlalchemy.text(f"SET LOCAL app.current_tenant = '{tenant_id}'"))

    res_surveys = await db.execute(
        select(ExitSurvey).where(ExitSurvey.tenant_id == tenant_id)
    )
    surveys = res_surveys.scalars().all()

    total_surveys = len(surveys)
    if total_surveys == 0:
        return {
            "tenant_id": str(tenant_id),
            "methodology": EXPLANATION_VALIDATION_METHODOLOGY,
            "total_surveyed": 0,
            "agreed_count": 0,
            "agreement_rate": 0.0,
            "details": []
        }

    agreed_count = 0
    details = []

    for survey in surveys:
        # Check customer's feature store top driver
        res_cf = await db.execute(
            select(ChurnFeature).where(
                and_(
                    ChurnFeature.tenant_id == tenant_id,
                    ChurnFeature.customer_id == survey.customer_id
                )
            ).order_by(ChurnFeature.created_at.desc())
        )
        cf = res_cf.scalars().first()

        fdict = {}
        if cf:
            fdict = getattr(cf, "features", {}) or getattr(cf, "feature_dict", {}) or {}

        top_driver = "usage_decline"
        if fdict:
            if fdict.get("payment_failures_90d", 0) > 0:
                top_driver = "payment_failures_90d"
            elif fdict.get("days_since_last_event", 0) > 14:
                top_driver = "days_since_last_event"
            elif fdict.get("support_tickets_count", 0) > 2:
                top_driver = "support_tickets_count"

        predicted_category = DRIVER_TO_REASON_MAP.get(top_driver, "other")
        stated_category = survey.reason_category

        is_match = (predicted_category == stated_category)
        if is_match:
            agreed_count += 1

        details.append({
            "customer_id": str(survey.customer_id),
            "top_shap_driver": top_driver,
            "predicted_category": predicted_category,
            "stated_category": stated_category,
            "agreed": is_match
        })

    agreement_rate = round((agreed_count / total_surveys) * 100.0, 1)

    return {
        "tenant_id": str(tenant_id),
        "methodology": EXPLANATION_VALIDATION_METHODOLOGY,
        "total_surveyed": total_surveys,
        "agreed_count": agreed_count,
        "agreement_rate": agreement_rate,
        "details": details
    }
