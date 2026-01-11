"""Tests for Neo4j user provisioning service."""

from unittest.mock import AsyncMock, MagicMock, Mock, patch

import pytest

from server.projects.auth.config import AuthConfig
from server.projects.auth.services.neo4j_service import Neo4jService


@pytest.fixture
def auth_config():
    """Create AuthConfig for testing."""
    config = AuthConfig()
    config.neo4j_uri = "bolt://localhost:7687"
    config.neo4j_user = "neo4j"
    config.neo4j_password = "test"
    return config


@pytest.fixture
def neo4j_service(auth_config):
    """Create Neo4jService instance for testing."""
    return Neo4jService(auth_config)


@pytest.fixture
def mock_driver():
    """Mock Neo4j driver."""
    driver = AsyncMock()
    session = AsyncMock()

    # Mock session context manager
    async def session_context():
        return session

    driver.session = MagicMock(return_value=AsyncMock())
    driver.session.return_value.__aenter__ = AsyncMock(return_value=session)
    driver.session.return_value.__aexit__ = AsyncMock(return_value=None)

    return driver, session


@pytest.mark.asyncio
async def test_provision_user_new(neo4j_service, mock_driver):
    """Test creates new :User node with email."""
    driver, session = mock_driver

    # Mock MERGE query result (new user created)
    mock_result = AsyncMock()
    mock_record = Mock()
    mock_result.single = AsyncMock(return_value=mock_record)
    session.run = AsyncMock(return_value=mock_result)

    with patch("neo4j.AsyncGraphDatabase.driver", return_value=driver):
        await neo4j_service.provision_user("new@example.com")

        session.run.assert_called_once()
        call_args = session.run.call_args
        assert "MERGE (u:User {email:" in call_args[0][0]
        assert call_args[1]["email"] == "new@example.com"


@pytest.mark.asyncio
async def test_provision_user_existing(neo4j_service, mock_driver):
    """Test skips creation if node exists (MERGE is idempotent)."""
    driver, session = mock_driver

    # Mock MERGE query result (user already exists)
    mock_result = AsyncMock()
    mock_record = Mock()
    mock_result.single = AsyncMock(return_value=mock_record)
    session.run = AsyncMock(return_value=mock_result)

    with patch("neo4j.AsyncGraphDatabase.driver", return_value=driver):
        await neo4j_service.provision_user("existing@example.com")

        # MERGE is idempotent, so it should still run
        session.run.assert_called_once()


@pytest.mark.asyncio
async def test_provision_user_connection_error(neo4j_service):
    """Test handles Neo4j connection errors."""
    with patch("neo4j.AsyncGraphDatabase.driver", side_effect=Exception("Connection failed")):
        with pytest.raises(Exception, match="Connection failed"):
            await neo4j_service.provision_user("test@example.com")


@pytest.mark.asyncio
async def test_close_driver(neo4j_service, mock_driver):
    """Test properly closes Neo4j driver."""
    driver, _session = mock_driver

    with patch("neo4j.AsyncGraphDatabase.driver", return_value=driver):
        neo4j_service.driver = driver
        await neo4j_service.close()

        driver.close.assert_called_once()
        assert neo4j_service.driver is None


@pytest.mark.asyncio
async def test_user_exists_true(neo4j_service, mock_driver):
    """Test user_exists returns true when user node exists."""
    driver, session = mock_driver

    mock_result = AsyncMock()
    mock_record = Mock()
    mock_result.single = AsyncMock(return_value=mock_record)
    session.run = AsyncMock(return_value=mock_result)

    with patch("neo4j.AsyncGraphDatabase.driver", return_value=driver):
        exists = await neo4j_service.user_exists("test@example.com")

        assert exists is True
        session.run.assert_called_once()


@pytest.mark.asyncio
async def test_user_exists_false(neo4j_service, mock_driver):
    """Test user_exists returns false when user node doesn't exist."""
    driver, session = mock_driver

    mock_result = AsyncMock()
    mock_result.single = AsyncMock(return_value=None)  # No record
    session.run = AsyncMock(return_value=mock_result)

    with patch("neo4j.AsyncGraphDatabase.driver", return_value=driver):
        exists = await neo4j_service.user_exists("nonexistent@example.com")

        assert exists is False


@pytest.mark.asyncio
async def test_user_anchoring_pattern(neo4j_service):
    """Test queries anchored to user node."""
    base_query = "RETURN n"
    email = "test@example.com"

    anchored = await neo4j_service.get_user_anchored_query(base_query, email, is_admin=False)

    assert "MATCH (u:User {email:" in anchored
    assert base_query in anchored


@pytest.mark.asyncio
async def test_admin_bypass_anchoring(neo4j_service):
    """Test admin queries skip user anchoring."""
    base_query = "RETURN n"
    email = "admin@example.com"

    anchored = await neo4j_service.get_user_anchored_query(base_query, email, is_admin=True)

    # Should return original query unchanged
    assert anchored == base_query
    assert "MATCH (u:User" not in anchored


@pytest.mark.asyncio
async def test_user_node_exists(neo4j_service, mock_driver):
    """Test user node exists before querying."""
    driver, session = mock_driver

    # First provision user
    mock_result = AsyncMock()
    mock_record = Mock()
    mock_result.single = AsyncMock(return_value=mock_record)
    session.run = AsyncMock(return_value=mock_result)

    with patch("neo4j.AsyncGraphDatabase.driver", return_value=driver):
        await neo4j_service.provision_user("test@example.com")

        # Then check existence
        exists = await neo4j_service.user_exists("test@example.com")

        # Should exist after provisioning
        assert exists is True
        assert session.run.call_count == 2  # Provision + check
