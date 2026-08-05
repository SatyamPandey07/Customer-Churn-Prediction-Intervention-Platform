import asyncio
import json
import logging

import redis.asyncio as redis
from apps.api.core.queue import REDIS_URL
from fastapi import APIRouter, WebSocket, WebSocketDisconnect

logger = logging.getLogger(__name__)
router = APIRouter(tags=["websockets"])

@router.websocket("/ws/tenants/{tenant_id}/anomalies")
async def websocket_anomaly_gateway(websocket: WebSocket, tenant_id: str):
    await websocket.accept()
    r = redis.from_url(REDIS_URL)
    pubsub = r.pubsub()
    await pubsub.subscribe("anomaly_updates")

    try:
        while True:
            msg = await pubsub.get_message(ignore_subscribe_messages=True, timeout=1.0)
            if msg and msg.get("type") == "message":
                data = json.loads(msg["data"].decode("utf-8"))
                if str(data.get("tenant_id")) == str(tenant_id):
                    await websocket.send_json(data)
            await asyncio.sleep(0.1)
    except WebSocketDisconnect:
        logger.info(f"WebSocket client disconnected for tenant {tenant_id}")
    except Exception as e:
        logger.error(f"WebSocket error for tenant {tenant_id}: {e}")
    finally:
        await pubsub.unsubscribe("anomaly_updates")
        await r.aclose()

@router.websocket("/ws/tenants/{tenant_id}/churn-updates")
async def websocket_churn_gateway(websocket: WebSocket, tenant_id: str):
    await websocket.accept()
    r = redis.from_url(REDIS_URL)
    pubsub = r.pubsub()
    await pubsub.subscribe("churn_updates")

    try:
        while True:
            msg = await pubsub.get_message(ignore_subscribe_messages=True, timeout=1.0)
            if msg and msg.get("type") == "message":
                data = json.loads(msg["data"].decode("utf-8"))
                if str(data.get("tenant_id")) == str(tenant_id):
                    await websocket.send_json(data)
            await asyncio.sleep(0.1)
    except WebSocketDisconnect:
        logger.info(f"WebSocket client disconnected for tenant {tenant_id}")
    except Exception as e:
        logger.error(f"WebSocket error for tenant {tenant_id}: {e}")
    finally:
        await pubsub.unsubscribe("churn_updates")
        await r.aclose()
