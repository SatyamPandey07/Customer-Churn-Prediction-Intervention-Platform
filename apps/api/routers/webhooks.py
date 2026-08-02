from typing import Any, Dict
from fastapi import APIRouter, Request, Depends, HTTPException, status
from apps.api.core.queue import get_queue
from pydantic import BaseModel

router = APIRouter(prefix="/webhooks", tags=["Webhooks"])

@router.post("/{tenant_id}/{source}", status_code=status.HTTP_202_ACCEPTED)
async def receive_webhook(tenant_id: str, source: str, payload: Dict[str, Any]):
    """
    Ingest webhook payload asynchronously.
    For this PR, we accept an arbitrary JSON payload and queue it for processing.
    """
    valid_sources = ["stripe", "segment", "amplitude", "generic"]
    if source not in valid_sources:
        raise HTTPException(status_code=400, detail="Invalid source")
        
    queue = await get_queue()
    await queue.enqueue_job("process_webhook", tenant_id, source, payload)
    return {"status": "accepted"}
