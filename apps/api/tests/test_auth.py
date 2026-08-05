import pytest
from apps.api.models import AuditLog
from httpx import AsyncClient
from sqlalchemy import select


@pytest.mark.asyncio
async def test_signup_happy_path(client: AsyncClient, db_session):
    payload = {
        "tenant_name": "Acme Corp",
        "subdomain": "acme",
        "email": "owner@acme.com",
        "password": "StrongPassword123!"
    }
    response = await client.post("/auth/signup", json=payload)
    assert response.status_code == 201
    
    # Verify audit log
    result = await db_session.execute(select(AuditLog))
    logs = result.scalars().all()
    assert len(logs) == 1
    assert logs[0].action == "SIGNUP"

@pytest.mark.asyncio
async def test_signup_password_policy(client: AsyncClient):
    payload = {
        "tenant_name": "Bad",
        "subdomain": "bad",
        "email": "bad@bad.com",
        "password": "short" # Too short
    }
    response = await client.post("/auth/signup", json=payload)
    assert response.status_code == 400
    assert "complexity" in response.json()["detail"]

@pytest.mark.asyncio
async def test_login_and_logout(client: AsyncClient, db_session):
    # Setup user
    await client.post("/auth/signup", json={
        "tenant_name": "Login Test", "subdomain": "login", "email": "test@login.com", "password": "StrongPassword123!"
    })

    # Login
    response = await client.post("/auth/login", data={
        "username": "test@login.com", "password": "StrongPassword123!"
    })
    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert "refresh_token" in data
    
    data["access_token"]
    
    # Refresh
    refresh_response = await client.post("/auth/refresh", json={
        "refresh_token": data["refresh_token"]
    })
    assert refresh_response.status_code == 200
    new_data = refresh_response.json()
    assert "access_token" in new_data
    
    # Logout
    logout_response = await client.post("/auth/logout", headers={"Authorization": f"Bearer {new_data['access_token']}"})
    assert logout_response.status_code == 200
    
    # Refresh token should be revoked now in DB, refresh should fail
    fail_refresh = await client.post("/auth/refresh", json={
        "refresh_token": new_data["refresh_token"]
    })
    assert fail_refresh.status_code == 401

@pytest.mark.asyncio
async def test_rate_limiting_auth(client: AsyncClient, setup_redis):
    """Test auth rate limiting: 5 attempts per minute per IP, 6th should be 429."""
    import apps.api.core.rate_limit as rl
    # Ensure clean state
    try:
        await rl.redis_client.flushdb()
    except Exception:
        pytest.skip("Redis not available for rate limit test")

    # Try 5 times rapidly, all should be 401 (bad credentials, not 429)
    for i in range(5):
        res = await client.post("/auth/login", data={"username": "a", "password": "b"})
        assert res.status_code == 401, f"Request {i+1} expected 401, got {res.status_code}"
        
    # 6th should fail with 429
    res_6 = await client.post("/auth/login", data={"username": "a", "password": "b"})
    assert res_6.status_code == 429

@pytest.mark.asyncio
async def test_account_lockout(client: AsyncClient, setup_redis):
    """Test account lockout after 10 failed login attempts."""
    import apps.api.core.rate_limit as rl
    try:
        await rl.redis_client.flushdb()
    except Exception:
        pytest.skip("Redis not available for lockout test")

    # Set the lockout counter directly in Redis
    await rl.redis_client.set("lockout:auth:locked@test.com", "10")
    
    res = await client.post("/auth/login", data={"username": "locked@test.com", "password": "b"})
    # Since IP isn't rate limited yet, it hits lockout check
    assert res.status_code == 403
    assert "Account locked" in res.json()["detail"]
