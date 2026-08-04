import logging
import uuid
from datetime import UTC, datetime, timedelta
from typing import Any

from apps.api.models import SupportSentimentScore
from sqlalchemy import and_, func, select
from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)

POSITIVE_WORDS = {
    "great", "love", "fantastic", "excellent", "wonderful", "amazing",
    "smooth", "awesome", "fast", "helpful", "good", "happy", "satisfied", "best", "superb"
}

NEGATIVE_WORDS = {
    "broken", "unusable", "terrible", "horrible", "crashed", "slow", "buggy",
    "frustrated", "worst", "hate", "cancelled", "canceling", "fail", "failed",
    "error", "useless", "disappointed", "poor", "unresponsive", "rage", "awful"
}

TOPIC_KEYWORDS = {
    "billing": ["billing", "invoice", "payment", "charge", "refund", "subscription", "price", "credit card"],
    "bugs": ["bug", "error", "crash", "crashed", "broken", "issue", "fault", "exception"],
    "usability": ["ui", "ux", "interface", "unusable", "confusing", "clunky", "navigation"],
    "performance": ["slow", "latency", "timeout", "lag", "performance", "speed"],
    "onboarding": ["setup", "onboarding", "install", "documentation", "guide", "tutorial"]
}

URGENCY_KEYWORDS = {
    "cancelled", "canceling", "unusable", "broken", "urgent", "immediately", "executive", "churn", "escalate"
}

def analyze_sentiment(text: str) -> dict[str, Any]:
    """
    Scores sentiment (-1.0 to +1.0), extracts topics, and checks urgency flag.
    Includes open-source/rule-based fallback pipeline.
    """
    if not text:
        return {"sentiment": 0.0, "topics": [], "urgency_flag": False}

    text_lower = text.lower()
    words = text_lower.split()

    score = 0.0
    for w in words:
        w_clean = w.strip(".,!?\"'()")
        if w_clean in POSITIVE_WORDS:
            score += 0.25
        elif w_clean in NEGATIVE_WORDS:
            score -= 0.35

    # Normalize to [-1.0, 1.0]
    sentiment = max(-1.0, min(1.0, score))

    # Topic extraction
    detected_topics = []
    for topic, kw_list in TOPIC_KEYWORDS.items():
        if any(kw in text_lower for kw in kw_list):
            detected_topics.append(topic)

    # Urgency flag check
    urgency_flag = sentiment < -0.5 or any(ukw in text_lower for ukw in URGENCY_KEYWORDS)

    return {
        "sentiment": round(sentiment, 2),
        "topics": detected_topics,
        "urgency_flag": urgency_flag
    }

async def process_and_store_sentiment(
    db: AsyncSession,
    tenant_id: uuid.UUID,
    customer_id: uuid.UUID,
    ticket_id: str,
    source: str,
    text_content: str
) -> SupportSentimentScore:
    res = analyze_sentiment(text_content)
    record = SupportSentimentScore(
        id=uuid.uuid4(),
        tenant_id=tenant_id,
        customer_id=customer_id,
        ticket_id=ticket_id,
        source=source,
        text_content=text_content,
        sentiment=res["sentiment"],
        topics=res["topics"],
        urgency_flag=res["urgency_flag"],
        created_at=datetime.now(UTC)
    )
    db.add(record)
    await db.commit()
    return record

async def get_customer_average_sentiment(
    db: AsyncSession,
    tenant_id: uuid.UUID,
    customer_id: uuid.UUID,
    days: int = 30
) -> float:
    cutoff = datetime.now(UTC) - timedelta(days=days)
    stmt = select(func.avg(SupportSentimentScore.sentiment)).where(
        and_(
            SupportSentimentScore.tenant_id == tenant_id,
            SupportSentimentScore.customer_id == customer_id,
            SupportSentimentScore.created_at >= cutoff
        )
    )
    res = await db.execute(stmt)
    avg_sent = res.scalar()
    if avg_sent is None:
        return 0.0  # Neutral default
    return float(avg_sent)
