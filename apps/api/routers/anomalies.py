import uuid
from datetime import UTC, datetime

from apps.api.core.analytics.anomaly import detect_anomalies_for_customer
from apps.api.core.deps import get_current_user, get_db
from apps.api.models import AnomalyEvent, Customer
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession

router = APIRouter(prefix="/tenants", tags=["anomalies"])

def check_tenant_access(user: dict, tenant_id: uuid.UUID):
    user_tenant_id = uuid.UUID(str(user["tenant_id"]))
    if user_tenant_id != tenant_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized for this tenant")

@router.get("/{tenant_id}/anomalies")
async def list_anomalies(
    tenant_id: uuid.UUID,
    resolved: bool | None = Query(False),
    severity: str | None = Query(None),
    db: AsyncSession = Depends(get_db),
    user: dict = Depends(get_current_user)
):
    check_tenant_access(user, tenant_id)
    stmt = select(AnomalyEvent).where(AnomalyEvent.tenant_id == tenant_id)
    if resolved is not None:
        stmt = stmt.where(AnomalyEvent.resolved == resolved)
    if severity:
        stmt = stmt.where(AnomalyEvent.severity == severity)
    stmt = stmt.order_by(AnomalyEvent.detected_at.desc())

    res = await db.execute(stmt)
    anomalies = res.scalars().all()
    return [
        {
            "id": str(a.id),
            "tenant_id": str(a.tenant_id),
            "customer_id": str(a.customer_id),
            "anomaly_type": a.anomaly_type,
            "severity": a.severity,
            "detected_at": a.detected_at.isoformat() if hasattr(a.detected_at, "isoformat") else str(a.detected_at),
            "detail": a.detail,
            "resolved": a.resolved,
            "resolved_at": a.resolved_at.isoformat() if a.resolved_at and hasattr(a.resolved_at, "isoformat") else None
        }
        for a in anomalies
    ]

@router.post("/{tenant_id}/anomalies/{anomaly_id}/resolve")
async def resolve_anomaly(
    tenant_id: uuid.UUID,
    anomaly_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    user: dict = Depends(get_current_user)
):
    check_tenant_access(user, tenant_id)
    res = await db.execute(
        select(AnomalyEvent).where(
            and_(AnomalyEvent.tenant_id == tenant_id, AnomalyEvent.id == anomaly_id)
        )
    )
    anomaly = res.scalars().first()
    if not anomaly:
        raise HTTPException(status_code=404, detail="Anomaly event not found")

    anomaly.resolved = True
    anomaly.resolved_at = datetime.now(UTC)
    await db.commit()
    return {"status": "resolved", "id": str(anomaly_id)}

@router.post("/{tenant_id}/anomalies/detect")
async def trigger_streaming_anomaly_detection(
    tenant_id: uuid.UUID,
    customer_id: uuid.UUID | None = Query(None),
    db: AsyncSession = Depends(get_db),
    user: dict = Depends(get_current_user)
):
    check_tenant_access(user, tenant_id)
    if customer_id:
        c_ids = [customer_id]
    else:
        res_c = await db.execute(select(Customer.id).where(Customer.tenant_id == tenant_id))
        c_ids = res_c.scalars().all()

    total_created = 0
    for cid in c_ids:
        created = await detect_anomalies_for_customer(db, tenant_id, cid)
        total_created += len(created)

    return {"status": "ok", "anomalies_detected": total_created}
