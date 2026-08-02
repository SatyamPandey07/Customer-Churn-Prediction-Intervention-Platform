import pytest
from httpx import AsyncClient
from sqlalchemy import select, text
from apps.api.models import User, Tenant

@pytest.mark.asyncio
async def test_rls_cross_tenant_isolation(client: AsyncClient, db_session):
    # Create Tenant A
    await client.post("/auth/signup", json={
        "tenant_name": "Tenant A", "subdomain": "tenanta", "email": "a@a.com", "password": "Password1!"
    })
    
    # Create Tenant B
    await client.post("/auth/signup", json={
        "tenant_name": "Tenant B", "subdomain": "tenantb", "email": "b@b.com", "password": "Password1!"
    })
    
    # Login as A
    res_a = await client.post("/auth/login", data={"username": "a@a.com", "password": "Password1!"})
    token_a = res_a.json()["access_token"]
    
    # Normally you test RLS by creating an endpoint that runs `select(User).all()` 
    # and makes sure it only returns Tenant A's users.
    # Since we don't have that endpoint yet, we will just simulate what `get_current_user` does directly
    # on the `db_session` and then try to query.
    
    import apps.api.core.security as sec
    payload = sec.decode_token(token_a)
    tenant_id_a = payload["tenant_id"]
    
    # We must switch to a non-superuser to actually test RLS, as testcontainers connects as postgres (superuser)
    await db_session.execute(text("CREATE ROLE rls_test_user"))
    await db_session.execute(text("GRANT SELECT ON users TO rls_test_user"))
    await db_session.execute(text("SET SESSION AUTHORIZATION rls_test_user"))

    # Activate RLS for session as if we hit an endpoint
    await db_session.execute(text(f"SET LOCAL app.current_tenant = '{tenant_id_a}'"))
    
    # Try to read users. Since RLS is enabled, we should ONLY see Tenant A's users (a@a.com)
    result = await db_session.execute(select(User))
    users = result.scalars().all()
    
    assert len(users) == 1
    assert users[0].email == "a@a.com"
    
    # Try raw SQL to Tenant B's data
    raw_result = await db_session.execute(text("SELECT email FROM users WHERE email = 'b@b.com'"))
    assert len(raw_result.all()) == 0  # Should be hidden by RLS!
