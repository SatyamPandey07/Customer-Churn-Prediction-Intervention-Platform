from fastapi import FastAPI
from apps.api.routers import auth

app = FastAPI(title="Churn Platform API")

app.include_router(auth.router)

@app.get("/health")
async def health_check():
    return {"status": "ok"}
