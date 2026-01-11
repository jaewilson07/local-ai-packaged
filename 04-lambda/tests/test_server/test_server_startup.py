"""Tests for FastAPI server startup and health check."""

from fastapi.testclient import TestClient

from server.main import app


def test_server_imports():
    """Test that server can be imported without errors."""
    # This test validates that all imports work
    from server.main import app

    assert app is not None
    assert app.title == "Lambda Server"


def test_health_check():
    """Test that health check endpoint responds."""
    client = TestClient(app)
    response = client.get("/health")
    assert response.status_code == 200
    assert "status" in response.json()


def test_root_endpoint():
    """Test that root endpoint responds."""
    client = TestClient(app)
    response = client.get("/")
    assert response.status_code == 200
    data = response.json()
    assert data["service"] == "Lambda Server"
    assert data["status"] == "running"


def test_mcp_info_endpoint():
    """Test that MCP info endpoint responds."""
    client = TestClient(app)
    response = client.get("/mcp-info")
    # Should return 200 even if no tools are registered
    assert response.status_code == 200
