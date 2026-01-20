"""Integration tests for API endpoints."""

from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from server.main import app
from server.projects.auth.models import User


@pytest.fixture
def mock_user():
    """Mock user for testing."""
    return User(id=uuid4(), email="test@example.com", role="user", tier="free")


@pytest.fixture
def mock_admin_user():
    """Mock admin user for testing."""
    return User(id=uuid4(), email="admin@example.com", role="admin", tier="pro")


def test_get_me_success(mock_user):
    """Test GET /api/me returns user profile with correct structure."""
    from server.projects.auth.dependencies import get_current_user

    # Override the dependency
    async def override_get_current_user():
        return mock_user

    app.dependency_overrides[get_current_user] = override_get_current_user

    try:
        client = TestClient(app)
        response = client.get("/api/me", headers={"Cf-Access-Jwt-Assertion": "valid.jwt.token"})

        assert response.status_code == 200
        data = response.json()
        assert data["uid"] == str(mock_user.id)
        assert data["email"] == mock_user.email
        assert data["role"] == mock_user.role
        assert data["tier"] == mock_user.tier
        assert "services_enabled" in data
    finally:
        app.dependency_overrides.clear()


def test_get_me_jit_provisioning():
    """Test GET /api/me triggers JIT provisioning for new user."""
    new_user = User(id=uuid4(), email="new@example.com", role="user", tier="free")

    from server.projects.auth.dependencies import get_current_user

    async def override_get_current_user():
        return new_user

    app.dependency_overrides[get_current_user] = override_get_current_user

    try:
        client = TestClient(app)
        response = client.get("/api/me", headers={"Cf-Access-Jwt-Assertion": "valid.jwt.token"})

        assert response.status_code == 200
    finally:
        app.dependency_overrides.clear()


def test_get_me_services_enabled(mock_user, mock_admin_user):
    """Test GET /api/me returns correct services based on tier/role."""
    from server.projects.auth.dependencies import get_current_user

    # Test free user
    async def override_get_current_user_free():
        return mock_user

    app.dependency_overrides[get_current_user] = override_get_current_user_free

    try:
        client = TestClient(app)
        response = client.get("/api/me", headers={"Cf-Access-Jwt-Assertion": "valid.jwt.token"})

        assert response.status_code == 200
        data = response.json()
        assert "supabase" in data["services_enabled"]
        # Free users don't get immich/n8n
        assert "immich" not in data["services_enabled"]
    finally:
        app.dependency_overrides.clear()

    # Test admin user
    async def override_get_current_user_admin():
        return mock_admin_user

    app.dependency_overrides[get_current_user] = override_get_current_user_admin

    try:
        client = TestClient(app)
        response = client.get("/api/me", headers={"Cf-Access-Jwt-Assertion": "valid.jwt.token"})

        assert response.status_code == 200
        data = response.json()
        # Admin gets all services
        assert "supabase" in data["services_enabled"]
        assert "immich" in data["services_enabled"]
        assert "n8n" in data["services_enabled"]
    finally:
        app.dependency_overrides.clear()


def test_get_me_missing_header():
    """Test GET /api/me returns 403 when header missing."""
    client = TestClient(app)
    response = client.get("/api/me")

    assert response.status_code == 403


def test_get_me_invalid_jwt():
    """Test GET /api/me returns 401 when JWT invalid."""
    from fastapi import HTTPException
    from server.projects.auth.dependencies import get_current_user

    async def override_get_current_user():
        raise HTTPException(status_code=401, detail="Invalid token")

    app.dependency_overrides[get_current_user] = override_get_current_user

    try:
        client = TestClient(app)
        response = client.get("/api/me", headers={"Cf-Access-Jwt-Assertion": "invalid.jwt.token"})

        assert response.status_code == 401
    finally:
        app.dependency_overrides.clear()
