import pytest
from apps.api.models import User
from httpx import AsyncClient
from sqlalchemy import select, text


@pytest.mark.asyncio
async def test_rls_cross_tenant_isolation(client: AsyncClient, db_session, setup_redis):
    # Ensure clean rate limit state
    import apps.api.core.rate_limit as rl
    try:
        await rl.redis_client.flushdb()
    except Exception:
        pass

    # Create Tenant A
    res_a_signup = await client.post("/auth/signup", json={
        "tenant_name": "Tenant A", "subdomain": "tenanta", "email": "a@a.com", "password": "Password1!"
    })
    assert res_a_signup.status_code == 201, f"Signup A failed: {res_a_signup.status_code} {res_a_signup.text}"

    # Create Tenant B
    res_b_signup = await client.post("/auth/signup", json={
        "tenant_name": "Tenant B", "subdomain": "tenantb", "email": "b@b.com", "password": "Password1!"
    })
    assert res_b_signup.status_code == 201, f"Signup B failed: {res_b_signup.status_code} {res_b_signup.text}"

    # Login as A
    res_a = await client.post("/auth/login", data={"username": "a@a.com", "password": "Password1!"})
    assert res_a.status_code == 200, f"Login A failed: {res_a.status_code} {res_a.text}"
    token_a = res_a.json()["access_token"]
    
    import apps.api.core.security as sec
    payload = sec.decode_token(token_a)
    tenant_id_a = payload["tenant_id"]
    
    # We must switch to a non-superuser to actually test RLS, as testcontainers connects as postgres (superuser)
    try:
        await db_session.execute(text("CREATE ROLE rls_test_user"))
    except Exception:
        # Role might already exist from a previous test run
        await db_session.rollback()
        await db_session.execute(text("DROP ROLE IF EXISTS rls_test_user"))
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
