"""
Model Fairness Monitoring: per-segment calibration and error-rate parity.
Slices churn predictions by plan_tier, industry, company_size_band and computes:
  - Mean predicted churn probability per segment
  - Fraction of actual churns (as approximated by churn_risk_tier == "critical")
  - Calibration error = |mean_predicted - actual_churn_fraction|
  - Parity flag = True if calibration error > threshold (default 0.15)

This is a monitoring signal, not a statistical certification.
"""
import logging
import uuid
from datetime import UTC, datetime
from typing import Any

from apps.api.models import Customer, ModelFairnessReport
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)

FAIRNESS_METHODOLOGY = (
    "Per-segment churn model calibration monitoring. Computes mean predicted probability vs. "
    "estimated actual churn fraction (high-risk tier count / total) per segment group. "
    "Flags segments where calibration error exceeds the parity threshold. "
    "Intended as a directional monitoring signal, NOT a certified fairness audit."
)

PARITY_THRESHOLD = 0.15  # Flag if calibration error > 15pp


async def run_fairness_monitoring(
    db: AsyncSession,
    tenant_id: uuid.UUID,
    dimension: str = "plan_tier"
) -> ModelFairnessReport:
    """
    Runs per-segment fairness monitoring for tenant's churn model predictions.
    Stores results in model_fairness_reports table.
    """
    import sqlalchemy
    await db.execute(sqlalchemy.text(f"SET LOCAL app.current_tenant = '{tenant_id}'"))

    res = await db.execute(select(Customer).where(Customer.tenant_id == tenant_id))
    customers = res.scalars().all()

    # Group customers by dimension value
    groups: dict[str, list[Customer]] = {}
    for c in customers:
        if dimension == "plan_tier":
            val = c.plan or "standard"
        elif dimension == "industry":
            val = c.industry or "unknown"
        elif dimension == "company_size_band":
            val = getattr(c, "company_size_band", None) or "unknown"
        else:
            val = c.plan or "standard"
        groups.setdefault(val, []).append(c)

    segments = []
    flagged_segments = []

    for grp_val, custs in groups.items():
        total = len(custs)
        if total == 0:
            continue

        probs = [float(c.churn_probability or 0.0) for c in custs]
        mean_predicted = sum(probs) / total

        # Approximate ACTUAL churn fraction from LABELED risk tiers only
        # (treating churn_risk_tier as the ground-truth proxy, independent of the predicted score)
        actual_churn_count = sum(
            1 for c in custs
            if (c.churn_risk_tier or "").lower() in ("critical", "high")
        )
        actual_churn_fraction = actual_churn_count / total


        calibration_error = abs(mean_predicted - actual_churn_fraction)
        is_flagged = calibration_error > PARITY_THRESHOLD

        seg_entry = {
            "dimension_value": grp_val,
            "customer_count": total,
            "mean_predicted_churn_prob": round(mean_predicted, 4),
            "actual_churn_fraction": round(actual_churn_fraction, 4),
            "calibration_error": round(calibration_error, 4),
            "parity_threshold": PARITY_THRESHOLD,
            "is_flagged": is_flagged
        }
        segments.append(seg_entry)
        if is_flagged:
            flagged_segments.append(grp_val)

    report = ModelFairnessReport(
        tenant_id=tenant_id,
        dimension=dimension,
        segments=segments,
        flagged_segments=flagged_segments,
        methodology=FAIRNESS_METHODOLOGY,
        generated_at=datetime.now(UTC)
    )
    db.add(report)
    await db.commit()
    await db.refresh(report)
    return report


async def get_latest_fairness_report(
    db: AsyncSession,
    tenant_id: uuid.UUID,
    dimension: str = "plan_tier"
) -> dict[str, Any]:
    """Returns the latest stored fairness report or runs one fresh."""
    import sqlalchemy
    from sqlalchemy import and_
    await db.execute(sqlalchemy.text(f"SET LOCAL app.current_tenant = '{tenant_id}'"))

    res = await db.execute(
        select(ModelFairnessReport).where(
            and_(
                ModelFairnessReport.tenant_id == tenant_id,
                ModelFairnessReport.dimension == dimension
            )
        ).order_by(ModelFairnessReport.generated_at.desc())
    )
    report = res.scalars().first()

    if not report:
        report = await run_fairness_monitoring(db, tenant_id, dimension)

    return {
        "tenant_id": str(tenant_id),
        "dimension": report.dimension,
        "generated_at": report.generated_at.isoformat(),
        "methodology": report.methodology,
        "total_segments": len(report.segments),
        "flagged_segments": report.flagged_segments,
        "parity_threshold": PARITY_THRESHOLD,
        "segments": report.segments
    }
