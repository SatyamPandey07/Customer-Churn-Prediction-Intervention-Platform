from fastapi import FastAPI
from apps.api.routers import auth, webhooks, predictions, explanations, campaigns, interventions, analytics

app = FastAPI(title="Churn Intervention API")

app.include_router(auth.router)
app.include_router(webhooks.router)
app.include_router(predictions.router)
app.include_router(explanations.router)
app.include_router(campaigns.router)
app.include_router(interventions.router)
app.include_router(analytics.router)

@app.get("/health")
async def health_check():
    return {"status": "ok"}
