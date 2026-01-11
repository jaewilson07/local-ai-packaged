"""Tests for Supabase user provisioning service."""

import pytest
from unittest.mock import AsyncMock, Mock, patch, MagicMock
from uuid import uuid4
from datetime import datetime

from server.projects.auth.services.supabase_service import SupabaseService
from server.projects.auth.config import AuthConfig
from server.projects.auth.models import User


@pytest.fixture
def auth_config():
    """Create AuthConfig for testing."""
    config = AuthConfig()
    config.supabase_db_url = "postgresql://test:test@localhost:5432/test"
    return config


@pytest.fixture
def supabase_service(auth_config):
    """Create SupabaseService instance for testing."""
    return SupabaseService(auth_config)


@pytest.fixture
def mock_pool():
    """Mock asyncpg.Pool."""
    pool = AsyncMock()
    connection = AsyncMock()
    
    # Mock context manager for pool.acquire()
    async def acquire_context():
        return connection
    
    pool.acquire = MagicMock(return_value=AsyncMock())
    pool.acquire.return_value.__aenter__ = AsyncMock(return_value=connection)
    pool.acquire.return_value.__aexit__ = AsyncMock(return_value=None)
    
    return pool, connection


@pytest.mark.asyncio
async def test_get_or_provision_user_existing(supabase_service, mock_pool):
    """Test returns existing user."""
    pool, connection = mock_pool
    
    # Mock existing user
    user_id = uuid4()
    mock_row = Mock()
    mock_row.__getitem__ = Mock(side_effect=lambda key: {
        'id': user_id,
        'email': 'existing@example.com',
        'role': 'user',
        'tier': 'free',
        'created_at': datetime.now()
    }.get(key))
    
    connection.fetchrow = AsyncMock(return_value=mock_row)
    connection.fetchval = AsyncMock(return_value=True)  # Table exists
    
    with patch("asyncpg.create_pool", AsyncMock(return_value=pool)):
        user = await supabase_service.get_or_provision_user("existing@example.com")
        
        assert user is not None
        assert user.email == "existing@example.com"
        assert user.role == "user"
        assert user.tier == "free"


@pytest.mark.asyncio
async def test_get_or_provision_user_new(supabase_service, mock_pool):
    """Test creates new user with defaults (role: 'user', tier: 'free')."""
    pool, connection = mock_pool
    
    # Mock no existing user
    connection.fetchrow = AsyncMock(return_value=None)
    connection.fetchval = AsyncMock(return_value=True)  # Table exists
    connection.execute = AsyncMock()
    
    with patch("asyncpg.create_pool", AsyncMock(return_value=pool)):
        with patch("uuid.uuid4", return_value=uuid4()) as mock_uuid:
            test_uuid = uuid4()
            mock_uuid.return_value = test_uuid
            
            user = await supabase_service.get_or_provision_user("new@example.com")
            
            assert user is not None
            assert user.email == "new@example.com"
            assert user.role == "user"  # Default
            assert user.tier == "free"  # Default
            connection.execute.assert_called()


@pytest.mark.asyncio
async def test_get_or_provision_user_connection_error(supabase_service):
    """Test handles database connection errors."""
    with patch("asyncpg.create_pool", side_effect=Exception("Connection failed")):
        with pytest.raises(Exception, match="Connection failed"):
            await supabase_service.get_or_provision_user("test@example.com")


@pytest.mark.asyncio
async def test_is_admin_true(supabase_service, mock_pool):
    """Test admin user check returns true."""
    pool, connection = mock_pool
    
    user_id = uuid4()
    mock_row = Mock()
    mock_row.__getitem__ = Mock(side_effect=lambda key: {
        'id': user_id,
        'email': 'admin@example.com',
        'role': 'admin',  # Admin role
        'tier': 'pro',
        'created_at': datetime.now()
    }.get(key))
    
    connection.fetchrow = AsyncMock(return_value=mock_row)
    
    with patch("asyncpg.create_pool", AsyncMock(return_value=pool)):
        is_admin = await supabase_service.is_admin("admin@example.com")
        
        assert is_admin is True


@pytest.mark.asyncio
async def test_is_admin_false(supabase_service, mock_pool):
    """Test non-admin user check returns false."""
    pool, connection = mock_pool
    
    user_id = uuid4()
    mock_row = Mock()
    mock_row.__getitem__ = Mock(side_effect=lambda key: {
        'id': user_id,
        'email': 'user@example.com',
        'role': 'user',  # Not admin
        'tier': 'free',
        'created_at': datetime.now()
    }.get(key))
    
    connection.fetchrow = AsyncMock(return_value=mock_row)
    
    with patch("asyncpg.create_pool", AsyncMock(return_value=pool)):
        is_admin = await supabase_service.is_admin("user@example.com")
        
        assert is_admin is False


@pytest.mark.asyncio
async def test_get_user_profile(supabase_service, mock_pool):
    """Test fetches user profile from Supabase."""
    pool, connection = mock_pool
    
    user_id = uuid4()
    mock_row = Mock()
    mock_row.__getitem__ = Mock(side_effect=lambda key: {
        'id': user_id,
        'email': 'test@example.com',
        'role': 'user',
        'tier': 'free',
        'created_at': datetime.now()
    }.get(key))
    
    connection.fetchrow = AsyncMock(return_value=mock_row)
    
    with patch("asyncpg.create_pool", AsyncMock(return_value=pool)):
        user = await supabase_service.get_user_by_email("test@example.com")
        
        assert user is not None
        assert user.id == user_id
        assert user.email == "test@example.com"
        assert user.role == "user"
        assert user.tier == "free"


@pytest.mark.asyncio
async def test_create_user(supabase_service, mock_pool):
    """Test creates user with specified role and tier."""
    pool, connection = mock_pool
    
    connection.execute = AsyncMock()
    test_uuid = uuid4()
    
    with patch("asyncpg.create_pool", AsyncMock(return_value=pool)):
        with patch("server.projects.auth.services.supabase_service.uuid4", return_value=test_uuid):
            user = await supabase_service.create_user(
                "new@example.com",
                role="admin",
                tier="pro"
            )
            
            assert user.email == "new@example.com"
            assert user.role == "admin"
            assert user.tier == "pro"
            assert user.id == test_uuid
            connection.execute.assert_called_once()


@pytest.mark.asyncio
async def test_ensure_profiles_table_exists(supabase_service, mock_pool):
    """Test ensures profiles table exists."""
    pool, connection = mock_pool
    
    connection.fetchval = AsyncMock(return_value=True)  # Table exists
    
    with patch("asyncpg.create_pool", AsyncMock(return_value=pool)):
        await supabase_service._ensure_profiles_table()
        
        # Should not create table if it exists
        connection.execute.assert_not_called()


@pytest.mark.asyncio
async def test_ensure_profiles_table_creates(supabase_service, mock_pool):
    """Test creates profiles table if missing."""
    pool, connection = mock_pool
    
    connection.fetchval = AsyncMock(return_value=False)  # Table doesn't exist
    connection.execute = AsyncMock()
    
    with patch("asyncpg.create_pool", AsyncMock(return_value=pool)):
        await supabase_service._ensure_profiles_table()
        
        # Should create table and index
        assert connection.execute.call_count >= 2  # Table + index