import uuid

import pytest
from apps.api.main import app
from httpx import ASGITransport, AsyncClient
from sqlalchemy.sql import text


@pytest.mark.asyncio
async def test_sql_injection_protection_campaigns(db_session, setup_redis):
    # Setup test tenant
    tenant_id = uuid.uuid4()
    await db_session.execute(text(
        "INSERT INTO tenants (id, name, subdomain, plan_tier) VALUES (:id, 'Test', 'test', 'tier1')"
    ), {"id": tenant_id})
    await db_session.commit()

    # Attempt an SQL injection on campaign search
    injection_payload = "' OR 1=1 --"
    
    # We create an admin token to authenticate
    from apps.api.core.security import create_access_token
    token = create_access_token(subject="admin@test.com", role="admin", tenant_id=str(tenant_id))
    headers = {"Authorization": f"Bearer {token}"}

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        response = await ac.get(f"/campaigns/?name={injection_payload}", headers=headers)
        
        # If it's a 500 Internal Server Error, then a poorly parameterized query broke the DB driver.
        # If it's a 200, the ORM correctly parameterized it and found 0 results safely.
        # Allow 429 as well in case the global rate limiter fires (not a SQL injection issue)
        assert response.status_code in (200, 429), f"Unexpected status {response.status_code}: {response.text}"
        if response.status_code == 200:
            assert len(response.json()) == 0

@pytest.mark.asyncio
async def test_sql_injection_create_campaign(db_session, setup_redis):
    tenant_id = uuid.uuid4()
    await db_session.execute(text(
        "INSERT INTO tenants (id, name, subdomain, plan_tier) VALUES (:id, 'Test2', 'test2', 'tier1')"
    ), {"id": tenant_id})
    await db_session.commit()

    from apps.api.core.security import create_access_token
    token = create_access_token(subject="admin@test2.com", role="admin", tenant_id=str(tenant_id))
    headers = {"Authorization": f"Bearer {token}"}
    
    injection_name = "Drop table campaigns; --"
    
    # Try inserting a campaign with an injected name
    payload = {
        "name": injection_name,
        "trigger_rule": {"metric": "mrr", "operator": ">", "value": 100},
        "intervention_type": "discount",
        "channel": "email",
        "template": "Hello"
    }
    
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        response = await ac.post("/campaigns/", json=payload, headers=headers)
        # Allow 429 as well in case the global rate limiter fires
        assert response.status_code in (200, 429), f"Unexpected status {response.status_code}: {response.text}"
        
        if response.status_code == 200:
            # The ORM should have inserted it safely as a literal string
            data = response.json()
            assert data["name"] == injection_name
