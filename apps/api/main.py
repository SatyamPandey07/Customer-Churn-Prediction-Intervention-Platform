from fastapi import FastAPI
from apps.api.routers import auth, webhooks, predictions

app = FastAPI(title="Churn Intervention API")

app.include_router(auth.router)
app.include_router(webhooks.router)
app.include_router(predictions.router)

@app.get("/health")
async def health_check():
    return {"status": "ok"}
