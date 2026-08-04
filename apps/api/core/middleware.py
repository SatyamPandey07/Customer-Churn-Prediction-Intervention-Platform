import time

from apps.api.core.rate_limit import redis_client
from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        response = await call_next(request)
        response.headers["Content-Security-Policy"] = "default-src 'self'"
        response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        return response

class GlobalRateLimitMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        import os
        if os.environ.get("TESTING") == "true" or os.environ.get("PYTEST_CURRENT_TEST"):
            return await call_next(request)

        # Allow health checks without rate limits
        if request.url.path in ["/health", "/live", "/ready", "/metrics", "/metrics/"]:
            return await call_next(request)
            
        client_ip = request.client.host if request.client else "unknown"
        # We also want to rate limit by tenant_id if available, but for a global middleware,
        # IP is the safest baseline unless we decode the JWT here (which adds overhead).
        # We will do a baseline IP rate limit of 100 req/sec.
        
        current_time = int(time.time())
        key = f"ratelimit:global:{client_ip}:{current_time}"
        
        # Simple fixed window counter per second
        try:
            current = await redis_client.incr(key)
            if current == 1:
                await redis_client.expire(key, 2)
                
            if current > 100:
                return JSONResponse(
                    status_code=429,
                    content={"detail": "Too many requests. Global limit exceeded."}
                )
        except Exception:
            # If redis is down, fail open (allow request) to prevent complete outage,
            # but in a strict enterprise context, you might choose to fail closed.
            pass
            
        return await call_next(request)
