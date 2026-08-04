import uuid
from datetime import UTC, datetime

from apps.api.core.analytics.champion import evaluate_champion_status
from apps.api.core.analytics.sentiment import process_and_store_sentiment
from apps.api.core.deps import get_current_user, get_db
from apps.api.models import AccountContact
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession

router = APIRouter(tags=["champions-sentiment"])

def check_tenant_access(user: dict, tenant_id: uuid.UUID):
    user_tenant_id = uuid.UUID(str(user["tenant_id"]))
    if user_tenant_id != tenant_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized for this tenant")

class CreateContactPayload(BaseModel):
    name: str
    email: str
    role: str = "Decision Maker"
    is_champion: bool = False
    is_active: bool = True
    bounced: bool = False

class AnalyzeSentimentPayload(BaseModel):
    customer_id: uuid.UUID
    ticket_id: str
    source: str = "zendesk"  # zendesk, intercom, nps
    text: str

@router.get("/tenants/{tenant_id}/customers/{customer_id}/champion-status")
async def get_champion_status(
    tenant_id: uuid.UUID,
    customer_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    user: dict = Depends(get_current_user)
):
    check_tenant_access(user, tenant_id)

    # Evaluate champion status / trigger anomaly if needed
    await evaluate_champion_status(db, tenant_id, customer_id)

    res = await db.execute(
        select(AccountContact).where(
            and_(
                AccountContact.tenant_id == tenant_id,
                AccountContact.customer_id == customer_id,
                AccountContact.is_champion == True
            )
        )
    )
    champions = res.scalars().all()
    now = datetime.now(UTC)

    return [
        {
            "id": str(c.id),
            "customer_id": str(c.customer_id),
            "name": c.name,
            "email": c.email,
            "role": c.role,
            "is_champion": c.is_champion,
            "is_active": c.is_active,
            "bounced": c.bounced,
            "last_confirmed_active": c.last_confirmed_active.isoformat() if hasattr(c.last_confirmed_active, "isoformat") else str(c.last_confirmed_active),
            "days_inactive": (now - (c.last_confirmed_active or c.created_at or now)).days,
            "status": "bounced" if c.bounced else ("active" if c.is_active else "inactive")
        }
        for c in champions
    ]

@router.post("/tenants/{tenant_id}/customers/{customer_id}/contacts")
async def create_or_update_contact(
    tenant_id: uuid.UUID,
    customer_id: uuid.UUID,
    payload: CreateContactPayload,
    db: AsyncSession = Depends(get_db),
    user: dict = Depends(get_current_user)
):
    check_tenant_access(user, tenant_id)

    res = await db.execute(
        select(AccountContact).where(
            and_(
                AccountContact.tenant_id == tenant_id,
                AccountContact.customer_id == customer_id,
                AccountContact.email == payload.email
            )
        )
    )
    contact = res.scalars().first()
    now = datetime.now(UTC)

    if not contact:
        contact = AccountContact(
            id=uuid.uuid4(),
            tenant_id=tenant_id,
            customer_id=customer_id,
            name=payload.name,
            email=payload.email,
            role=payload.role,
            is_champion=payload.is_champion,
            is_active=payload.is_active,
            bounced=payload.bounced,
            last_confirmed_active=now,
            created_at=now
        )
        db.add(contact)
    else:
        contact.name = payload.name
        contact.role = payload.role
        contact.is_champion = payload.is_champion
        contact.is_active = payload.is_active
        contact.bounced = payload.bounced
        if payload.is_active and not payload.bounced:
            contact.last_confirmed_active = now

    await db.commit()
    return {"status": "saved", "id": str(contact.id), "is_champion": contact.is_champion}

@router.post("/tenants/{tenant_id}/sentiment/analyze")
async def analyze_and_record_sentiment(
    tenant_id: uuid.UUID,
    payload: AnalyzeSentimentPayload,
    db: AsyncSession = Depends(get_db),
    user: dict = Depends(get_current_user)
):
    check_tenant_access(user, tenant_id)
    record = await process_and_store_sentiment(
        db, tenant_id, payload.customer_id, payload.ticket_id, payload.source, payload.text
    )
    return {
        "id": str(record.id),
        "sentiment": record.sentiment,
        "topics": record.topics,
        "urgency_flag": record.urgency_flag
    }
