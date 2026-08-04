from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from apps.api.routers import auth, webhooks, predictions, explanations, campaigns, interventions, analytics, compliance, integrations, health, anomalies, websocket, champions
from apps.api.core.observability import setup_observability
from apps.api.core.middleware import SecurityHeadersMiddleware, GlobalRateLimitMiddleware

app = FastAPI(title="ChurnGuard.ai API")

# Security Middlewares
app.add_middleware(
    CORSMiddleware,
    allow_origins=["https://app.churnguard.ai", "http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.add_middleware(SecurityHeadersMiddleware)
app.add_middleware(GlobalRateLimitMiddleware)

app.include_router(auth.router)
app.include_router(webhooks.router)
app.include_router(predictions.router)
app.include_router(explanations.router)
app.include_router(campaigns.router)
app.include_router(interventions.router)
app.include_router(analytics.router)
app.include_router(compliance.router)
app.include_router(integrations.router)
app.include_router(health.router)
app.include_router(anomalies.router)
app.include_router(websocket.router)
app.include_router(champions.router)



# Initialize observability
setup_observability(app)

@app.get("/health")
async def health_check():
    return {"status": "ok"}

@app.get("/live")
async def liveness_probe():
    return {"status": "alive"}

@app.get("/ready")
async def readiness_probe():
    # In a real app, you would check DB connection here
    return {"status": "ready"}
