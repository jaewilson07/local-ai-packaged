"""Shared fixtures for sample validation tests."""

import os
from pathlib import Path
from unittest.mock import AsyncMock, Mock

import pytest

# Set up environment variables to prevent validation errors during import
os.environ.setdefault("MONGODB_URI", "mongodb://localhost:27017/test")
os.environ.setdefault("NEO4J_URI", "bolt://localhost:7687")
os.environ.setdefault("NEO4J_USER", "neo4j")
os.environ.setdefault("NEO4J_PASSWORD", "password")
os.environ.setdefault("LLM_BASE_URL", "http://localhost:11434")
os.environ.setdefault("EMBEDDING_BASE_URL", "http://localhost:11434")
os.environ.setdefault("LLM_MODEL", "llama3.2")
os.environ.setdefault("EMBEDDING_MODEL", "qwen3-embedding:4b")
os.environ.setdefault("N8N_API_URL", "http://localhost:5678")
os.environ.setdefault("OPENWEBUI_API_URL", "http://localhost:3000")
os.environ.setdefault("GOOGLE_CALENDAR_CREDENTIALS_PATH", "/tmp/credentials.json")


@pytest.fixture
def sample_base_path():
    """Get the base path to the sample directory."""
    project_root = Path(__file__).parent.parent.parent.parent
    return project_root / "sample"


@pytest.fixture
def lambda_path():
    """Get the path to the lambda directory."""
    project_root = Path(__file__).parent.parent.parent.parent
    return project_root / "04-lambda"


@pytest.fixture
def mock_mongodb():
    """Mock MongoDB client and database."""
    mock_client = AsyncMock()
    mock_db = Mock()
    mock_client.__getitem__.return_value = mock_db
    mock_client.admin.command = AsyncMock(return_value={"ok": 1})

    # Set up collections with proper aggregation cursors
    async def async_iter_mock(items):
        for item in items:
            yield item

    # Mock chunks collection with aggregation that returns empty results
    mock_chunks = Mock()
    mock_chunks.aggregate = AsyncMock(return_value=async_iter_mock([]))
    mock_chunks.find_one = AsyncMock(return_value=None)
    mock_chunks.insert_many = AsyncMock(return_value=Mock(inserted_ids=[]))

    # Mock documents collection
    mock_documents = Mock()
    mock_documents.find_one = AsyncMock(return_value=None)
    mock_documents.insert_one = AsyncMock(return_value=Mock(inserted_id=None))

    # Make db return collections
    def get_collection(name):
        if name == "chunks":
            return mock_chunks
        if name == "documents":
            return mock_documents
        return Mock()

    mock_db.__getitem__ = Mock(side_effect=get_collection)

    return mock_client, mock_db


@pytest.fixture
def mock_neo4j():
    """Mock Neo4j driver and session."""
    mock_driver = AsyncMock()
    mock_session = AsyncMock()
    mock_driver.session.return_value.__aenter__.return_value = mock_session
    mock_driver.session.return_value.__aexit__.return_value = None
    return mock_driver, mock_session


@pytest.fixture
def mock_openai_client():
    """Mock OpenAI client for embeddings and LLM."""
    mock_client = AsyncMock()
    mock_embedding_response = Mock()
    mock_embedding_response.data = [Mock(embedding=[0.1] * 384)]
    mock_client.embeddings.create = AsyncMock(return_value=mock_embedding_response)

    mock_chat_response = Mock()
    mock_chat_response.choices = [Mock(message=Mock(content="Test response"))]
    mock_client.chat.completions.create = AsyncMock(return_value=mock_chat_response)

    return mock_client


@pytest.fixture
def mock_httpx_client():
    """Mock httpx client for HTTP requests."""
    mock_client = AsyncMock()
    mock_response = Mock()
    mock_response.status_code = 200
    mock_response.json = Mock(return_value={"success": True})
    mock_client.get = AsyncMock(return_value=mock_response)
    mock_client.post = AsyncMock(return_value=mock_response)
    mock_client.aclose = AsyncMock()
    return mock_client


@pytest.fixture
def mock_crawl4ai_crawler():
    """Mock Crawl4AI crawler."""
    mock_crawler = AsyncMock()
    mock_result = Mock()
    mock_result.markdown = "# Test Content"
    mock_result.links = []
    mock_crawler.arun = AsyncMock(return_value=mock_result)
    mock_crawler.__aenter__ = AsyncMock(return_value=mock_crawler)
    mock_crawler.__aexit__ = AsyncMock(return_value=None)
    return mock_crawler


@pytest.fixture
def mock_graphiti():
    """Mock Graphiti client."""
    mock_graphiti = AsyncMock()
    mock_graphiti.search = AsyncMock(return_value=[])
    mock_graphiti.build_indices_and_constraints = AsyncMock()
    mock_graphiti.close = AsyncMock()
    return mock_graphiti


@pytest.fixture
def mock_google_calendar_service():
    """Mock Google Calendar sync service."""
    mock_service = Mock()
    mock_service.create_event = AsyncMock(return_value={"id": "event_123"})
    mock_service.list_events = AsyncMock(return_value=[])
    return mock_service
