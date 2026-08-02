from fastapi import FastAPI

app = FastAPI(title="Churn Intervention Platform API")

@app.get("/health")
async def health_check():
    return {"status": "ok"}
