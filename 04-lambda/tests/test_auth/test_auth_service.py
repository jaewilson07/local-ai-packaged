"""Tests for authentication helper service."""

from unittest.mock import AsyncMock, patch

import pytest

from server.projects.auth.config import AuthConfig
from server.projects.auth.services.auth_service import AuthService


@pytest.fixture
def auth_config():
    """Create AuthConfig for testing."""
    config = AuthConfig()
    return config


@pytest.fixture
def auth_service(auth_config):
    """Create AuthService instance for testing."""
    return AuthService(auth_config)


@pytest.mark.asyncio
async def test_is_admin_true(auth_service):
    """Test admin user identified correctly."""
    with patch.object(
        auth_service.supabase_service, "is_admin", new_callable=AsyncMock
    ) as mock_is_admin:
        mock_is_admin.return_value = True

        is_admin = await auth_service.is_admin("admin@example.com")

        assert is_admin is True
        mock_is_admin.assert_called_once_with("admin@example.com")


@pytest.mark.asyncio
async def test_is_admin_false(auth_service):
    """Test non-admin user identified correctly."""
    with patch.object(
        auth_service.supabase_service, "is_admin", new_callable=AsyncMock
    ) as mock_is_admin:
        mock_is_admin.return_value = False

        is_admin = await auth_service.is_admin("user@example.com")

        assert is_admin is False
        mock_is_admin.assert_called_once_with("user@example.com")
