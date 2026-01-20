"""Tests for MongoDB user provisioning service."""

from unittest.mock import AsyncMock, Mock, patch

import pytest
from pymongo.errors import OperationFailure
from server.projects.auth.config import AuthConfig
from server.projects.auth.services.mongodb_service import MongoDBService


@pytest.fixture
def mock_auth_config():
    """Mock AuthConfig for testing."""
    config = Mock(spec=AuthConfig)
    config.cloudflare_auth_domain = "https://test.cloudflareaccess.com"
    config.cloudflare_aud_tag = "test-aud-tag"
    return config


@pytest.fixture
def mock_mongo_client():
    """Mock MongoDB admin client."""
    client = AsyncMock()
    client.admin = AsyncMock()
    client.admin.command = AsyncMock()
    return client


@pytest.fixture
def mongodb_service(mock_auth_config):
    """Create MongoDBService instance for testing."""
    with patch("server.projects.auth.services.mongodb_service.rag_config") as mock_config:
        mock_config.mongodb_uri = "mongodb://admin:admin123@localhost:27017"
        mock_config.mongodb_database = "test_db"
        service = MongoDBService(mock_auth_config)
        return service


class TestUsernameSanitization:
    """Test username sanitization."""

    def test_simple_email(self, mongodb_service):
        """Test simple email conversion."""
        email = "user@example.com"
        username = mongodb_service._sanitize_username(email)

        assert "@" not in username
        assert username == "user_at_example_com"

    def test_email_with_multiple_dots(self, mongodb_service):
        """Test email with multiple dots."""
        email = "user.name@sub.example.com"
        username = mongodb_service._sanitize_username(email)

        assert "@" not in username
        assert "." not in username
        assert username == "user_name_at_sub_example_com"

    def test_long_email_truncation(self, mongodb_service):
        """Test long email gets truncated with hash."""
        # Create a very long email
        long_email = "a" * 50 + "@" + "b" * 50 + ".com"
        username = mongodb_service._sanitize_username(long_email)

        # Should be <= 64 chars (MongoDB limit)
        assert len(username) <= 64
        assert "@" not in username


class TestPasswordGeneration:
    """Test password generation."""

    def test_password_length(self, mongodb_service):
        """Test password has correct length."""
        password = mongodb_service._generate_password(length=32)

        assert len(password) == 32

    def test_password_randomness(self, mongodb_service):
        """Test passwords are random."""
        password1 = mongodb_service._generate_password()
        password2 = mongodb_service._generate_password()

        # Should be different (very unlikely to be same)
        assert password1 != password2

    def test_password_characters(self, mongodb_service):
        """Test password contains valid characters."""
        password = mongodb_service._generate_password(length=100)

        # Should contain alphanumeric and special chars
        has_alpha = any(c.isalpha() for c in password)
        has_digit = any(c.isdigit() for c in password)

        assert has_alpha or has_digit  # At least one type


class TestUserExists:
    """Test user_exists method."""

    @pytest.mark.asyncio
    async def test_user_exists_true(self, mongodb_service, mock_mongo_client):
        """Test user_exists returns True when user exists."""
        mongodb_service._admin_client = mock_mongo_client
        mock_mongo_client.admin.command.return_value = {
            "users": [{"user": "test_user", "roles": []}]
        }

        exists = await mongodb_service.user_exists("test@example.com")

        assert exists is True
        mock_mongo_client.admin.command.assert_called_once()

    @pytest.mark.asyncio
    async def test_user_exists_false(self, mongodb_service, mock_mongo_client):
        """Test user_exists returns False when user doesn't exist."""
        mongodb_service._admin_client = mock_mongo_client
        mock_mongo_client.admin.command.side_effect = OperationFailure("UserNotFound", code=11)

        exists = await mongodb_service.user_exists("test@example.com")

        assert exists is False

    @pytest.mark.asyncio
    async def test_user_exists_empty_list(self, mongodb_service, mock_mongo_client):
        """Test user_exists returns False when users list is empty."""
        mongodb_service._admin_client = mock_mongo_client
        mock_mongo_client.admin.command.return_value = {"users": []}

        exists = await mongodb_service.user_exists("test@example.com")

        assert exists is False


class TestProvisionUser:
    """Test provision_user method."""

    @pytest.mark.asyncio
    async def test_provision_new_user(self, mongodb_service, mock_mongo_client):
        """Test provisioning a new user."""
        mongodb_service._admin_client = mock_mongo_client
        mongodb_service.user_exists = AsyncMock(return_value=False)
        mongodb_service._create_rag_user_role = AsyncMock()

        # Mock successful user creation
        mock_mongo_client.admin.command.return_value = {"ok": 1}

        username, password = await mongodb_service.provision_user("test@example.com", "user-123")

        assert username == "test_at_example_com"
        assert len(password) > 0
        mongodb_service._create_rag_user_role.assert_called_once()
        mock_mongo_client.admin.command.assert_called()

    @pytest.mark.asyncio
    async def test_provision_existing_user(self, mongodb_service, mock_mongo_client):
        """Test provisioning an existing user returns credentials."""
        mongodb_service._admin_client = mock_mongo_client
        mongodb_service.user_exists = AsyncMock(return_value=True)
        mongodb_service._create_rag_user_role = AsyncMock()

        username, password = await mongodb_service.provision_user("test@example.com", "user-123")

        assert username == "test_at_example_com"
        assert len(password) > 0
        # Should not try to create user again
        create_calls = [
            call
            for call in mock_mongo_client.admin.command.call_args_list
            if call[0][0].get("createUser")
        ]
        assert len(create_calls) == 0

    @pytest.mark.asyncio
    async def test_provision_handles_duplicate(self, mongodb_service, mock_mongo_client):
        """Test provisioning handles duplicate user gracefully."""
        mongodb_service._admin_client = mock_mongo_client
        mongodb_service.user_exists = AsyncMock(return_value=False)
        mongodb_service._create_rag_user_role = AsyncMock()

        # Mock duplicate user error
        mock_mongo_client.admin.command.side_effect = OperationFailure("already exists", code=51003)

        username, password = await mongodb_service.provision_user("test@example.com", "user-123")

        # Should still return credentials
        assert username == "test_at_example_com"
        assert len(password) > 0


class TestCreateRAGUserRole:
    """Test _create_rag_user_role method."""

    @pytest.mark.asyncio
    async def test_create_role_success(self, mongodb_service, mock_mongo_client):
        """Test creating RAG user role."""
        mongodb_service._admin_client = mock_mongo_client
        mock_mongo_client.admin.command.return_value = {"ok": 1}

        await mongodb_service._create_rag_user_role()

        # Should call createRole command
        call_args = mock_mongo_client.admin.command.call_args[0][0]
        assert call_args["createRole"] == "rag_user"
        assert "privileges" in call_args

    @pytest.mark.asyncio
    async def test_create_role_already_exists(self, mongodb_service, mock_mongo_client):
        """Test creating role that already exists is safe."""
        mongodb_service._admin_client = mock_mongo_client
        mock_mongo_client.admin.command.side_effect = OperationFailure("already exists", code=51003)

        # Should not raise
        await mongodb_service._create_rag_user_role()


class TestGetMongoDBUsername:
    """Test get_mongodb_username method."""

    @pytest.mark.asyncio
    async def test_get_username(self, mongodb_service):
        """Test getting MongoDB username from email."""
        username = await mongodb_service.get_mongodb_username("test@example.com")

        assert username == "test_at_example_com"
        assert "@" not in username


class TestDeleteUser:
    """Test delete_user method."""

    @pytest.mark.asyncio
    async def test_delete_user_success(self, mongodb_service, mock_mongo_client):
        """Test deleting a user."""
        mongodb_service._admin_client = mock_mongo_client
        mock_mongo_client.admin.command.return_value = {"ok": 1}

        await mongodb_service.delete_user("test@example.com")

        mock_mongo_client.admin.command.assert_called_with("dropUser", "test_at_example_com")

    @pytest.mark.asyncio
    async def test_delete_nonexistent_user(self, mongodb_service, mock_mongo_client):
        """Test deleting non-existent user is safe."""
        mongodb_service._admin_client = mock_mongo_client
        mock_mongo_client.admin.command.side_effect = OperationFailure("UserNotFound", code=11)

        # Should not raise
        await mongodb_service.delete_user("test@example.com")
