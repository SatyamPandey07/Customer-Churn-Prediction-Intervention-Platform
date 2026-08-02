from fastapi import FastAPI
from apps.api.routers import auth, webhooks

app = FastAPI(title="Churn Platform API")

app.include_router(auth.router)
app.include_router(webhooks.router)

@app.get("/health")
async def health_check():
    return {"status": "ok"}
