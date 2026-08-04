import pytest
from apps.api.models import Role, User
from httpx import AsyncClient
from sqlalchemy import select


@pytest.mark.asyncio
async def test_rbac_admin_only_route(client: AsyncClient, db_session, setup_redis):
    # Ensure clean rate limit state
    import apps.api.core.rate_limit as rl
    try:
        await rl.redis_client.flushdb()
    except Exception:
        pass

    # Signup creates owner
    signup_res = await client.post("/auth/signup", json={
        "tenant_name": "RBAC", "subdomain": "rbac", "email": "owner@rbac.com", "password": "Password1!"
    })
    assert signup_res.status_code == 201, f"Signup failed: {signup_res.status_code} {signup_res.text}"

    # Login to get owner token
    res = await client.post("/auth/login", data={"username": "owner@rbac.com", "password": "Password1!"})
    assert res.status_code == 200, f"Login failed: {res.status_code} {res.text}"
    owner_token = res.json()["access_token"]
    
    # Hit admin route
    admin_res = await client.get("/auth/admin-only", headers={"Authorization": f"Bearer {owner_token}"})
    assert admin_res.status_code == 200
    
    # Change user to viewer in DB
    result = await db_session.execute(select(User).where(User.email == "owner@rbac.com"))
    user = result.scalars().first()
    user.role = Role.viewer
    await db_session.commit()
    
    # Login again to get a viewer token
    res2 = await client.post("/auth/login", data={"username": "owner@rbac.com", "password": "Password1!"})
    assert res2.status_code == 200, f"Second login failed: {res2.status_code} {res2.text}"
    viewer_token = res2.json()["access_token"]
    
    # Hit admin route with viewer token
    viewer_res = await client.get("/auth/admin-only", headers={"Authorization": f"Bearer {viewer_token}"})
    assert viewer_res.status_code == 403
    assert "Not enough permissions" in viewer_res.json()["detail"]
