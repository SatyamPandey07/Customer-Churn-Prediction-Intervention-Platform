import os
import json
from arq import create_pool
from arq.connections import RedisSettings

REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")

# Parse redis URL for arq RedisSettings
def get_redis_settings() -> RedisSettings:
    import urllib.parse
    url = urllib.parse.urlparse(REDIS_URL)
    return RedisSettings(
        host=url.hostname or 'localhost',
        port=url.port or 6379,
        password=url.password,
        database=int(url.path.lstrip('/')) if url.path and url.path != '/' else 0
    )

async def get_queue():
    settings = get_redis_settings()
    return await create_pool(settings)

async def publish_churn_update(tenant_id: str, customer_id: str, probability: float, risk_tier: str):
    import redis.asyncio as redis
    r = redis.from_url(REDIS_URL)
    payload = json.dumps({
        "tenant_id": tenant_id,
        "customer_id": customer_id,
        "churn_probability": probability,
        "churn_risk_tier": risk_tier
    })
    await r.publish("churn_updates", payload)
    await r.aclose()
