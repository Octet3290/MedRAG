import uuid

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_register_and_login_flow(async_client: AsyncClient):
    """
    Test complete user authentication journey:
    1. Register -> 2. Duplicate Check -> 3. Login -> 4. Access /auth/me
    """
    unique_email = f"doctor_{uuid.uuid4().hex[:8]}@hospital.org"
    password = "StrongPassword2026!"

    # 1. Register
    reg_payload = {"email": unique_email, "password": password}
    reg_res = await async_client.post("/api/v1/auth/register", json=reg_payload)
    assert reg_res.status_code == 201
    reg_data = reg_res.json()
    assert "access_token" in reg_data
    assert reg_data["user"]["email"] == unique_email
    assert "hashed_password" not in reg_data["user"]
    token = reg_data["access_token"]

    # 2. Duplicate Registration Rejection
    dup_res = await async_client.post("/api/v1/auth/register", json=reg_payload)
    assert dup_res.status_code == 409
    assert "already exists" in dup_res.json()["detail"]

    # 3. Successful Login
    login_payload = {"email": unique_email, "password": password}
    login_res = await async_client.post("/api/v1/auth/login", json=login_payload)
    assert login_res.status_code == 200
    login_data = login_res.json()
    assert "access_token" in login_data
    assert login_data["user"]["email"] == unique_email

    # 4. Access /auth/me using issued token
    headers = {"Authorization": f"Bearer {token}"}
    me_res = await async_client.get("/api/v1/auth/me", headers=headers)
    assert me_res.status_code == 200
    me_data = me_res.json()
    assert me_data["email"] == unique_email


@pytest.mark.asyncio
async def test_login_invalid_credentials(async_client: AsyncClient):
    """Verify that wrong password returns generic 401 error."""
    payload = {"email": "nonexistent@hospital.org", "password": "WrongPassword123!"}
    res = await async_client.post("/api/v1/auth/login", json=payload)
    assert res.status_code == 401
    assert res.json()["detail"] == "Invalid email or password"


@pytest.mark.asyncio
async def test_auth_me_unauthorized(async_client: AsyncClient):
    """Verify that accessing protected route without token is rejected."""
    res = await async_client.get("/api/v1/auth/me")
    assert res.status_code in [401, 403]
