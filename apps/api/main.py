from fastapi import FastAPI
from apps.api.routers import auth, webhooks, predictions, explanations, campaigns, interventions, analytics
from apps.api.core.observability import setup_observability

app = FastAPI(title="Churn Intervention API")

app.include_router(auth.router)
app.include_router(webhooks.router)
app.include_router(predictions.router)
app.include_router(explanations.router)
app.include_router(campaigns.router)
app.include_router(interventions.router)
app.include_router(analytics.router)

# Initialize observability
setup_observability(app)

@app.get("/health")
async def health_check():
    return {"status": "ok"}
