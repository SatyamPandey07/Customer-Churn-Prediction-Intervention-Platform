import os

import redis.asyncio as redis
from fastapi import HTTPException, status

REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")
redis_client = redis.from_url(REDIS_URL, decode_responses=True)

# 5 attempts per minute
RATE_LIMIT_ATTEMPTS = 5
RATE_LIMIT_WINDOW_SEC = 60

# Lockout after 10 failed attempts within 15 mins
LOCKOUT_ATTEMPTS = 10
LOCKOUT_WINDOW_SEC = 900

async def check_rate_limit(ip_address: str):
    """
    General rate limit for auth endpoints (e.g. signup, login).
    5 attempts per minute per IP.
    """
    key = f"ratelimit:auth:{ip_address}"
    try:
        current = await redis_client.incr(key)
        if current == 1:
            await redis_client.expire(key, RATE_LIMIT_WINDOW_SEC)
        
        if current > RATE_LIMIT_ATTEMPTS:
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="Too many requests. Please try again later."
            )
    except HTTPException:
        raise  # Re-raise the 429 we just created
    except Exception:
        # If Redis is down, fail open to prevent auth from being entirely blocked
        pass

async def check_account_lockout(email: str):
    """
    Check if the account (email) is locked out due to too many failed attempts.
    """
    key = f"lockout:auth:{email}"
    try:
        attempts = await redis_client.get(key)
        if attempts and int(attempts) >= LOCKOUT_ATTEMPTS:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Account locked due to too many failed login attempts. Try again later."
            )
    except HTTPException:
        raise  # Re-raise the 403 we just created
    except Exception:
        pass

async def record_failed_login(email: str):
    """
    Record a failed login attempt for the given email.
    """
    key = f"lockout:auth:{email}"
    try:
        current = await redis_client.incr(key)
        if current == 1:
            await redis_client.expire(key, LOCKOUT_WINDOW_SEC)
    except Exception:
        pass

async def reset_failed_login(email: str):
    """
    Reset failed login attempts upon successful login.
    """
    key = f"lockout:auth:{email}"
    try:
        await redis_client.delete(key)
    except Exception:
        pass

