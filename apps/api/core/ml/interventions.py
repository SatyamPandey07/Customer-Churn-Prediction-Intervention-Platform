import logging
import os
from typing import Any

from apps.api.core.queue import get_redis_settings
from google import genai
from google.genai import types
from pydantic import BaseModel, Field
from redis.asyncio import Redis

logger = logging.getLogger(__name__)

class InterventionItem(BaseModel):
    type: str = Field(description="One of: discount, training, cs_review, upgrade_path")
    rationale: str = Field(description="Why this intervention makes sense")
    suggested_copy: str = Field(description="Email or message copy for the customer")
    priority: str = Field(description="One of: low, medium, high, critical")

class InterventionResponse(BaseModel):
    recommended_interventions: list[InterventionItem]
    confidence: float = Field(description="Confidence in the recommendation from 0.0 to 1.0")

_redis = None

def get_redis_client() -> Redis:
    global _redis
    if _redis is None:
        settings = get_redis_settings()
        # Fallback to local redis if setting is complex
        host = "localhost"
        try:
            # arq settings is sometimes a custom class
            if hasattr(settings, 'host'):
                host = settings.host
            elif isinstance(settings, dict):
                host = settings.get("host", "localhost")
            elif hasattr(settings, 'redis_settings') and hasattr(settings.redis_settings, 'host'):
                host = settings.redis_settings.host
        except Exception:
            pass
        _redis = Redis.from_url(f"redis://{host}:6379")
    return _redis

def get_fallback_intervention() -> InterventionResponse:
    return InterventionResponse(
        recommended_interventions=[
            InterventionItem(
                type="cs_review",
                rationale="High risk detected by model; automated recommendation unavailable.",
                suggested_copy="Hi there, checking in to see if you need any assistance getting value from our platform.",
                priority="high"
            )
        ],
        confidence=0.5
    )

def sanitize_input(text: str) -> str:
    """Lightweight prompt injection guard."""
    if not text:
        return ""
    # Strip common prompt injection tokens
    forbidden = ["ignore previous", "system prompt", "instruction", "output:"]
    lower_text = text.lower()
    for word in forbidden:
        if word in lower_text:
            logger.warning(f"Sanitized potential prompt injection string: {text}")
            return "REDACTED"
    return text.strip()

async def generate_intervention(
    customer_id: str,
    churn_prob: float,
    risk_tier: str,
    drivers: list[dict[str, Any]],
    customer_meta: dict[str, Any],
    feature_set_version: str = "v1",
    model_version: str = "xgboost_v1"
) -> InterventionResponse:
    
    cache_key = f"intervention:{customer_id}:{feature_set_version}:{model_version}"
    redis = get_redis_client()
    
    # Check cache
    try:
        cached = await redis.get(cache_key)
        if cached:
            return InterventionResponse.model_validate_json(cached)
    except Exception as e:
        logger.error(f"Redis cache error: {e}")
        
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        logger.warning("No GEMINI_API_KEY found, returning fallback.")
        return get_fallback_intervention()
        
    try:
        client = genai.Client(api_key=api_key)
    except Exception as e:
        logger.error(f"Failed to initialize Gemini client: {e}")
        return get_fallback_intervention()
        
    # Sanitize inputs
    plan = sanitize_input(str(customer_meta.get("plan", "unknown")))
    mrr = customer_meta.get("mrr", 0.0)
    tenure = customer_meta.get("tenure_days", 0)
    
    drivers_str = "\n".join([f"- {d.get('human_readable')}" for d in drivers])
    
    prompt = f"""
You are an expert customer success AI. Provide an intervention recommendation.

Customer Profile:
- Risk Tier: {risk_tier} (Probability: {churn_prob:.2f})
- Plan: {plan}
- MRR: ${mrr:.2f}
- Tenure: {tenure} days

Top Churn Drivers:
{drivers_str}

Return ONLY a JSON object that perfectly adheres to the requested schema.
"""
    
    try:
        # Use structured outputs
        response = client.models.generate_content(
            model='gemini-2.5-flash',
            contents=prompt,
            config=types.GenerateContentConfig(
                response_mime_type="application/json",
                response_schema=InterventionResponse,
                temperature=0.2,
            ),
        )
        
        # Validate output
        result = InterventionResponse.model_validate_json(response.text)
        
        # Cache result for 24h
        try:
            await redis.setex(cache_key, 86400, result.model_dump_json())
        except Exception as e:
            logger.error(f"Redis cache set error: {e}")
            
        return result
        
    except Exception as e:
        logger.error(f"Gemini API or validation error: {e}")
        return get_fallback_intervention()
