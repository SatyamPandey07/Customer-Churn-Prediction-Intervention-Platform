import pytest
from httpx import AsyncClient
from sqlalchemy import select
from apps.api.models import User, Role

@pytest.mark.asyncio
async def test_rbac_admin_only_route(client: AsyncClient, db_session):
    # Signup creates owner
    await client.post("/auth/signup", json={
        "tenant_name": "RBAC", "subdomain": "rbac", "email": "owner@rbac.com", "password": "Password1!"
    })
    
    # Login to get owner token
    res = await client.post("/auth/login", data={"username": "owner@rbac.com", "password": "Password1!"})
    owner_token = res.json()["access_token"]
    
    # Hit admin route
    admin_res = await client.get("/auth/admin-only", headers={"Authorization": f"Bearer {owner_token}"})
    assert admin_res.status_code == 200
    
    # Change user to viewer in DB
    result = await db_session.execute(select(User).where(User.email == "owner@rbac.com"))
    user = result.scalars().first()
    user.role = Role.viewer
    await db_session.commit()
    
    # Even though token says owner, wait... our token payload contains role!
    # We need to mint a new token for the viewer, or the API relies on token role.
    # Let's login again to get a viewer token
    res2 = await client.post("/auth/login", data={"username": "owner@rbac.com", "password": "Password1!"})
    viewer_token = res2.json()["access_token"]
    
    # Hit admin route with viewer token
    viewer_res = await client.get("/auth/admin-only", headers={"Authorization": f"Bearer {viewer_token}"})
    assert viewer_res.status_code == 403
    assert "Not enough permissions" in viewer_res.json()["detail"]
