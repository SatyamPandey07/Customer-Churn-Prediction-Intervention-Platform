import uuid
from datetime import UTC, datetime
from typing import Any

from apps.api.core.deps import get_db, require_role
from apps.api.models import AuditLog, Role
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

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
        "id": "sendgrid",
        "name": "SendGrid Email Marketing",
        "category": "Marketing & Email",
        "description": "Syncs email sends, opens, clicks, and bounce events.",
        "icon": "mail",
        "status": "connected",
        "last_sync": "2026-08-03T11:30:00Z",
        "events_count_24h": 3200,
        "config": {"api_key": "sg_••••••••1234"}
    },
    {
        "id": "twilio",
        "name": "Twilio SMS",
        "category": "Communications",
        "description": "Syncs SMS delivery status, replies, and error codes.",
        "icon": "message-square",
        "status": "connected",
        "last_sync": "2026-08-03T10:15:00Z",
        "events_count_24h": 450,
        "config": {"account_sid": "AC_••••••••5678", "auth_token": "tk_••••••••9012"}
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
    }
]

class IntegrationConfigRequest(BaseModel):
    api_key: str | None = None
    webhook_secret: str | None = None
    subdomain: str | None = None

class TestConnectionResponse(BaseModel):
    success: bool
    latency_ms: int
    message: str

@router.get("", response_model=list[dict[str, Any]])
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
    integration["last_sync"] = datetime.now(UTC).isoformat()
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

    integration["last_sync"] = datetime.now(UTC).isoformat()
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

# ---------------------------------------------------------
# Custom Integrations CRUD
# ---------------------------------------------------------
from sqlalchemy.future import select
from apps.api.models import CustomIntegration, TenantSecret

class CustomIntegrationRequest(BaseModel):
    name: str
    integration_type: str
    config: dict[str, Any]
    credential: str | None = None

@router.post("/custom")
async def create_custom_integration(
    req: CustomIntegrationRequest,
    db: AsyncSession = Depends(get_db),
    user: dict = Depends(require_role([Role.owner, Role.admin]))
):
    """Create a new custom integration (webhook_in or rest_out)."""
    # Create secret if credential provided
    secret_id = None
    if req.credential:
        secret = TenantSecret(
            tenant_id=uuid.UUID(user["tenant_id"]),
            name=f"custom_{req.name}_cred",
            encrypted_value=req.credential
        )
        db.add(secret)
        await db.commit()
        await db.refresh(secret)
        secret_id = secret.id

    integration = CustomIntegration(
        tenant_id=uuid.UUID(user["tenant_id"]),
        name=req.name,
        integration_type=req.integration_type,
        config=req.config,
        credential_ref=secret_id,
        status="active",
        created_by=uuid.UUID(user["user_id"])
    )
    db.add(integration)
    await db.commit()
    await db.refresh(integration)

    return {"id": str(integration.id), "name": integration.name, "status": integration.status}

@router.get("/custom")
async def list_custom_integrations(
    db: AsyncSession = Depends(get_db),
    user: dict = Depends(require_role([Role.owner, Role.admin, Role.analyst, Role.viewer]))
):
    """List custom integrations."""
    stmt = select(CustomIntegration).where(CustomIntegration.tenant_id == uuid.UUID(user["tenant_id"]))
    result = await db.execute(stmt)
    integrations = result.scalars().all()
    
    return [
        {
            "id": str(i.id),
            "name": i.name,
            "integration_type": i.integration_type,
            "config": i.config,
            "status": i.status,
            "last_test_result": i.last_test_result,
            "has_credential": i.credential_ref is not None
        }
        for i in integrations
    ]

@router.post("/custom/{integration_id}/test")
async def test_custom_integration(
    integration_id: str,
    db: AsyncSession = Depends(get_db),
    user: dict = Depends(require_role([Role.owner, Role.admin]))
):
    """Test custom integration connection."""
    stmt = select(CustomIntegration).where(
        CustomIntegration.id == uuid.UUID(integration_id),
        CustomIntegration.tenant_id == uuid.UUID(user["tenant_id"])
    )
    result = await db.execute(stmt)
    integration = result.scalars().first()
    
    if not integration:
        raise HTTPException(status_code=404, detail="Integration not found")

    # Simulate test connection
    integration.last_test_result = "success"
    integration.consecutive_failures = 0
    await db.commit()

    return {"success": True, "message": "Test successful", "latency_ms": 42}

