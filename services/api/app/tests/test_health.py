import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_root_health_check(async_client: AsyncClient):
    """Verify that root /health endpoint returns 200 and status healthy."""
    response = await async_client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert data["environment"] == "development"
    assert "version" in data


@pytest.mark.asyncio
async def test_api_v1_health_check(async_client: AsyncClient):
    """Verify that versioned /api/v1/health endpoint returns 200 and status healthy."""
    response = await async_client.get("/api/v1/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert data["environment"] == "development"
    assert "version" in data
