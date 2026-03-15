"""API tests for auth and source routes."""

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_health_check(client: AsyncClient):
    """Test health endpoint."""
    response = await client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


@pytest.mark.asyncio
async def test_register_user(client: AsyncClient):
    """Test user registration."""
    response = await client.post("/api/v1/auth/register", json={
        "email": "new@test.com",
        "username": "newuser",
        "password": "securepass",
    })
    assert response.status_code == 201
    data = response.json()
    assert data["email"] == "new@test.com"
    assert data["username"] == "newuser"
    assert data["role"] == "editor"


@pytest.mark.asyncio
async def test_register_duplicate(client: AsyncClient, admin_user):
    """Test duplicate registration fails."""
    response = await client.post("/api/v1/auth/register", json={
        "email": "admin@test.com",
        "username": "admin",
        "password": "password",
    })
    assert response.status_code == 409


@pytest.mark.asyncio
async def test_login(client: AsyncClient, admin_user):
    """Test login returns tokens."""
    response = await client.post("/api/v1/auth/login", json={
        "email": "admin@test.com",
        "password": "password123",
    })
    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert "refresh_token" in data


@pytest.mark.asyncio
async def test_login_wrong_password(client: AsyncClient, admin_user):
    """Test login with wrong password."""
    response = await client.post("/api/v1/auth/login", json={
        "email": "admin@test.com",
        "password": "wrong",
    })
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_me(client: AsyncClient, admin_token: str):
    """Test /me endpoint."""
    response = await client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {admin_token}"})
    assert response.status_code == 200
    assert response.json()["email"] == "admin@test.com"


@pytest.mark.asyncio
async def test_sources_crud(client: AsyncClient, admin_token: str):
    """Test source creation and listing."""
    headers = {"Authorization": f"Bearer {admin_token}"}

    # Create
    response = await client.post("/api/v1/sources/", json={
        "source_type": "rss",
        "name": "Test RSS",
        "feed_url": "https://example.com/rss",
        "language": "en",
    }, headers=headers)
    assert response.status_code == 201
    source_id = response.json()["id"]

    # List
    response = await client.get("/api/v1/sources/", headers=headers)
    assert response.status_code == 200
    assert len(response.json()) == 1

    # Update
    response = await client.put(f"/api/v1/sources/{source_id}", json={"priority": 10}, headers=headers)
    assert response.status_code == 200
    assert response.json()["priority"] == 10

    # Delete
    response = await client.delete(f"/api/v1/sources/{source_id}", headers=headers)
    assert response.status_code == 204


@pytest.mark.asyncio
async def test_dashboard_stats(client: AsyncClient, admin_token: str):
    """Test dashboard stats endpoint."""
    response = await client.get("/api/v1/dashboard/stats", headers={"Authorization": f"Bearer {admin_token}"})
    assert response.status_code == 200
    data = response.json()
    assert "total_sources" in data
    assert "pending_moderation" in data


@pytest.mark.asyncio
async def test_unauthorized_access(client: AsyncClient):
    """Test that protected endpoints require auth."""
    response = await client.get("/api/v1/sources/")
    assert response.status_code == 403  # No auth header
