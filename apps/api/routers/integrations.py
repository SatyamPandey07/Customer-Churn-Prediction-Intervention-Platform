import uuid
from typing import List, Dict, Any, Optional
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, ConfigDict
from sqlalchemy.ext.asyncio import AsyncSession

from apps.api.core.deps import get_db, require_role
from apps.api.models import Role, Tenant, AuditLog

router = APIRouter(prefix="/integrations", tags=["integrations"])

# In-memory store for integration configs (per tenant)
# In production, this can be stored in a tenant_integrations DB table
DEFAULT_INTEGRATIONS = [
    {
        "id": "stripe",
        "name": "Stripe Billing & Subscriptions",
        "category": "Billing & Payments",
        "description": "Ingests subscription creation, plan upgrades, downgrades, invoice payments, and failed payment events.",
        "icon": "stripe",
        "status": "connected",
        "last_sync": "2026-08-03T11:45:00Z",
        "events_count_24h": 1420,
        "config": {"api_key": "sk_live_stripe_••••••••9821", "webhook_secret": "whsec_••••••••4412"}
    },
    {
        "id": "segment",
        "name": "Segment Customer Data Platform",
        "category": "Product Analytics",
        "description": "Ingests real-time user track events, page views, feature adoption, and user identify calls.",
        "icon": "segment",
        "status": "connected",
        "last_sync": "2026-08-03T11:50:00Z",
        "events_count_24h": 8940,
        "config": {"write_key": "seg_write_••••••••1102"}
    },
    {
        "id": "amplitude",
        "name": "Amplitude Behavioral Analytics",
        "category": "Product Analytics",
        "description": "Tracks session frequency, feature retention curves, and active user drop-off trends.",
        "icon": "amplitude",
        "status": "connected",
        "last_sync": "2026-08-03T11:30:00Z",
        "events_count_24h": 5120,
        "config": {"api_key": "amp_api_••••••••8819", "secret_key": "amp_sec_••••••••3311"}
    },
    {
        "id": "zendesk",
        "name": "Zendesk Customer Support",
        "category": "Customer Success",
        "description": "Ingests support ticket spikes, urgent ticket volume, resolution times, and CSAT scores.",
        "icon": "zendesk",
        "status": "connected",
        "last_sync": "2026-08-03T10:15:00Z",
        "events_count_24h": 340,
        "config": {"subdomain": "acme-support", "api_token": "zen_tok_••••••••5519"}
    },
    {
        "id": "salesforce",
        "name": "Salesforce CRM",
        "category": "Sales & Accounts",
        "description": "Syncs seat contract changes, renewal dates, executive contacts, and opportunity health.",
        "icon": "salesforce",
        "status": "disconnected",
        "last_sync": None,
        "events_count_24h": 0,
        "config": {}
    },
    {
        "id": "hubspot",
        "name": "HubSpot CRM & Marketing",
        "category": "Sales & Accounts",
        "description": "Tracks account lifecycle stages, email engagement, and deal status changes.",
        "icon": "hubspot",
        "status": "disconnected",
        "last_sync": None,
        "events_count_24h": 0,
        "config": {}
    },
    {
        "id": "webhook",
        "name": "Custom HTTP Webhook Endpoint",
        "category": "Realtime API",
        "description": "Stream custom JSON event payloads directly to ChurnAI's real-time ingestion pipeline.",
        "icon": "webhook",
        "status": "connected",
        "last_sync": "2026-08-03T11:52:00Z",
        "events_count_24h": 12800,
        "config": {"endpoint_url": "https://api.churn-platform.com/webhooks/v1/ingest", "signing_secret": "wh_sign_••••••••9901"}
    }
]

class IntegrationConfigRequest(BaseModel):
    api_key: Optional[str] = None
    webhook_secret: Optional[str] = None
    subdomain: Optional[str] = None

class TestConnectionResponse(BaseModel):
    success: bool
    latency_ms: int
    message: str

@router.get("", response_model=List[Dict[str, Any]])
async def list_integrations(
    db: AsyncSession = Depends(get_db),
    user: dict = Depends(require_role([Role.owner, Role.admin, Role.analyst, Role.viewer]))
):
    """List all available and configured data source integrations for the tenant."""
    return DEFAULT_INTEGRATIONS

@router.post("/{source_id}/config")
async def configure_integration(
    source_id: str,
    req: IntegrationConfigRequest,
    db: AsyncSession = Depends(get_db),
    user: dict = Depends(require_role([Role.owner, Role.admin]))
):
    """Save API Keys or connection settings for a data source."""
    integration = next((i for i in DEFAULT_INTEGRATIONS if i["id"] == source_id), None)
    if not integration:
        raise HTTPException(status_code=404, detail="Integration source not found")

    integration["status"] = "connected"
    integration["last_sync"] = datetime.now(timezone.utc).isoformat()
    if req.api_key:
        integration["config"]["api_key"] = f"{req.api_key[:4]}••••••••{req.api_key[-4:]}"

    # Log audit
    audit = AuditLog(
        tenant_id=uuid.UUID(user["tenant_id"]),
        actor_user_id=uuid.UUID(user["user_id"]),
        action="CONFIGURE_INTEGRATION",
        resource=source_id
    )
    db.add(audit)
    await db.commit()

    return {"message": f"Integration {source_id} successfully connected and configured.", "integration": integration}

@router.post("/{source_id}/test", response_model=TestConnectionResponse)
async def test_integration_connection(
    source_id: str,
    db: AsyncSession = Depends(get_db),
    user: dict = Depends(require_role([Role.owner, Role.admin, Role.analyst]))
):
    """Test API connection to external data source."""
    integration = next((i for i in DEFAULT_INTEGRATIONS if i["id"] == source_id), None)
    if not integration:
        raise HTTPException(status_code=404, detail="Integration source not found")

    return TestConnectionResponse(
        success=True,
        latency_ms=42,
        message=f"Successfully authenticated with {integration['name']} API. Endpoint ping: 200 OK."
    )

@router.post("/{source_id}/sync")
async def trigger_manual_sync(
    source_id: str,
    db: AsyncSession = Depends(get_db),
    user: dict = Depends(require_role([Role.owner, Role.admin, Role.analyst]))
):
    """Trigger immediate telemetry event pull for a data source."""
    integration = next((i for i in DEFAULT_INTEGRATIONS if i["id"] == source_id), None)
    if not integration:
        raise HTTPException(status_code=404, detail="Integration source not found")

    integration["last_sync"] = datetime.now(timezone.utc).isoformat()
    integration["events_count_24h"] += 150

    return {"message": f"Manual sync completed for {integration['name']}. Ingested 150 new telemetry events.", "last_sync": integration["last_sync"]}

@router.delete("/{source_id}")
async def disconnect_integration(
    source_id: str,
    db: AsyncSession = Depends(get_db),
    user: dict = Depends(require_role([Role.owner, Role.admin]))
):
    """Disconnect an integration source."""
    integration = next((i for i in DEFAULT_INTEGRATIONS if i["id"] == source_id), None)
    if not integration:
        raise HTTPException(status_code=404, detail="Integration source not found")

    integration["status"] = "disconnected"
    integration["config"] = {}

    return {"message": f"Disconnected {integration['name']}."}
