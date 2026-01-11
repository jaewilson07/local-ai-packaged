"""Shared pytest fixtures for RAG tests."""

import os

# Set minimal environment variables before any imports
# This prevents Settings validation errors during test collection
os.environ.setdefault("MONGODB_URI", "mongodb://localhost:27017/test")
os.environ.setdefault("MONGODB_DATABASE", "test_db")
os.environ.setdefault("LLM_BASE_URL", "http://localhost:11434/v1")
os.environ.setdefault("LLM_API_KEY", "test-key")
os.environ.setdefault("EMBEDDING_BASE_URL", "http://localhost:11434/v1")
os.environ.setdefault("EMBEDDING_API_KEY", "test-key")

from unittest.mock import AsyncMock, Mock, patch

import pytest
from bson import ObjectId


# Mock MongoDB fixtures
@pytest.fixture
def mock_mongo_client():
    """Mock MongoDB client."""
    client = AsyncMock()
    client.__getitem__ = Mock(return_value=AsyncMock())
    return client


@pytest.fixture
def mock_mongo_db(mock_mongo_client):
    """Mock MongoDB database."""
    db = AsyncMock()
    mock_mongo_client.__getitem__ = Mock(return_value=db)
    return db


@pytest.fixture
def mock_mongo_collection():
    """Mock MongoDB collection."""
    collection = AsyncMock()
    collection.aggregate = AsyncMock(return_value=AsyncMock())
    collection.find_one = AsyncMock()
    collection.insert_one = AsyncMock()
    collection.insert_many = AsyncMock()
    collection.update_one = AsyncMock()
    collection.delete_many = AsyncMock()
    return collection


@pytest.fixture
def sample_document():
    """Sample document for testing."""
    return {
        "_id": ObjectId(),
        "title": "Test Document",
        "source": "test_source",
        "metadata": {"source": "test", "user_id": "user1", "conversation_id": "conv1"},
    }


@pytest.fixture
def sample_chunk(sample_document):
    """Sample chunk for testing."""
    return {
        "_id": ObjectId(),
        "document_id": sample_document["_id"],
        "content": "This is a test chunk with some content about authentication.",
        "embedding": [0.1] * 768,  # Mock embedding vector
        "metadata": {"chunk_index": 0, "source": "test"},
        "document_info": {"title": sample_document["title"], "source": sample_document["source"]},
    }


@pytest.fixture
def sample_search_results(sample_chunk):
    """Sample search results for testing."""
    return [
        {
            "chunk_id": str(sample_chunk["_id"]),
            "document_id": str(sample_chunk["document_id"]),
            "content": sample_chunk["content"],
            "similarity": 0.95,
            "metadata": sample_chunk["metadata"],
            "document_title": sample_chunk["document_info"]["title"],
            "document_source": sample_chunk["document_info"]["source"],
        }
    ]


@pytest.fixture
def mock_embedding():
    """Mock embedding function."""

    async def _get_embedding(text: str) -> list[float]:
        return [0.1] * 768

    return _get_embedding


@pytest.fixture
def mock_openai_client():
    """Mock OpenAI client with proper structure for LLM calls."""
    client = AsyncMock()
    client.embeddings = AsyncMock()

    # Mock chat.completions.create structure
    mock_chat = AsyncMock()
    mock_completions = AsyncMock()
    mock_create = AsyncMock()

    # Default response structure
    mock_response = Mock()
    mock_choice = Mock()
    mock_choice.message = Mock()
    mock_choice.message.content = "Test response"
    mock_response.choices = [mock_choice]
    mock_create.return_value = mock_response

    mock_completions.create = mock_create
    mock_chat.completions = mock_completions
    client.chat = mock_chat

    return client


# Mock Graphiti fixtures
@pytest.fixture
def mock_graphiti():
    """Mock Graphiti instance."""
    from types import SimpleNamespace

    graphiti = AsyncMock()

    # Create proper result object structure
    def create_result(fact, score=0.9, metadata=None, chunk_id=None):
        result = SimpleNamespace()
        result.fact = fact
        result.score = float(score)  # Ensure numeric value
        result.similarity = float(score)  # Ensure numeric value
        result.metadata = metadata or {}
        if chunk_id:
            result.metadata["chunk_id"] = chunk_id
        return result

    # Default search results
    graphiti.search = AsyncMock(
        return_value=[
            create_result(
                "Python is a programming language",
                0.9,
                {"chunk_id": "fact_123", "title": "Python Facts"},
            )
        ]
    )
    graphiti.parse_repository = AsyncMock()
    return graphiti


@pytest.fixture
def mock_neo4j_client():
    """Mock Neo4j client."""
    client = AsyncMock()
    client.execute_query = AsyncMock()
    return client


@pytest.fixture
def sample_graph_fact():
    """Sample graph fact for testing."""
    return {
        "chunk_id": "fact_123",
        "content": "Python is a programming language",
        "similarity": 0.9,
        "metadata": {"title": "Python Facts", "source": "graphiti"},
    }


# Mock Crawl4AI fixtures
@pytest.fixture
def mock_crawler():
    """Mock Crawl4AI crawler."""
    crawler = AsyncMock()
    crawler.arun = AsyncMock()
    return crawler


@pytest.fixture
def sample_crawl_result():
    """Sample crawl result for testing."""
    return {
        "url": "https://example.com",
        "markdown": "# Example Page\n\nThis is example content.",
        "html": "<html><body><h1>Example Page</h1></body></html>",
        "metadata": {"title": "Example Page", "description": "An example page", "language": "en"},
    }


# Mock dependencies fixtures
@pytest.fixture
def mock_agent_dependencies(mock_mongo_db, mock_embedding, mock_openai_client):
    """Mock AgentDependencies for MongoDB RAG."""
    deps = AsyncMock()
    deps.db = mock_mongo_db
    deps.mongo_client = AsyncMock()
    deps.get_embedding = AsyncMock(side_effect=mock_embedding)
    deps.openai_client = mock_openai_client
    deps.settings = Mock(
        default_match_count=10,
        max_match_count=50,
        mongodb_collection_documents="documents",
        mongodb_collection_chunks="chunks",
        mongodb_vector_index="vector_index",
        mongodb_text_index="text_index",
    )
    deps.graphiti_deps = None
    deps.initialize = AsyncMock()
    deps.cleanup = AsyncMock()
    return deps


@pytest.fixture
def mock_graphiti_rag_deps(mock_graphiti, mock_neo4j_client):
    """Mock GraphitiRAGDeps."""
    deps = AsyncMock()
    deps.graphiti = mock_graphiti
    deps.neo4j_client = mock_neo4j_client
    deps.initialize = AsyncMock()
    deps.cleanup = AsyncMock()
    return deps


@pytest.fixture
def mock_crawl4ai_deps(mock_crawler, mock_mongo_client):
    """Mock Crawl4AIDependencies."""
    deps = AsyncMock()
    deps.crawler = mock_crawler
    deps.mongo_client = mock_mongo_client
    deps.initialize = AsyncMock()
    deps.cleanup = AsyncMock()
    return deps


# Mock LLM fixtures
@pytest.fixture
def mock_llm_response():
    """Mock LLM response (deprecated - use mock_openai_client instead)."""
    return {"choices": [{"message": {"content": "This is a test response."}}]}


@pytest.fixture
def mock_openai_client_for_llm():
    """Mock OpenAI client specifically for LLM calls in enhanced RAG."""
    client = AsyncMock()

    # Create proper mock structure for chat.completions.create
    mock_response = Mock()
    mock_choice = Mock()
    mock_choice.message = Mock()
    mock_choice.message.content = '{"needs_decomposition": false, "sub_queries": ["test query"]}'
    mock_response.choices = [mock_choice]

    mock_create = AsyncMock(return_value=mock_response)
    mock_completions = Mock()
    mock_completions.create = mock_create
    mock_chat = Mock()
    mock_chat.completions = mock_completions
    client.chat = mock_chat

    return client


# Mock file fixtures
@pytest.fixture
def mock_upload_file():
    """Mock file upload."""
    file = Mock()
    file.filename = "test.pdf"
    file.file = Mock()
    file.file.read = Mock(return_value=b"PDF content")
    return file


# Mock RunContext helper
class MockRunContext:
    """
    Mock RunContext for testing.

    For tests that need a real RunContext (not just a mock), use
    create_run_context() from server.projects.shared.context_helpers instead.
    """

    def __init__(self, deps, use_real_context=False):
        """
        Initialize mock RunContext.

        Args:
            deps: Dependencies instance
            use_real_context: If True, creates a real RunContext using create_run_context.
                            If False (default), creates a simple mock object.
        """
        if use_real_context:
            from server.projects.shared.context_helpers import create_run_context

            real_ctx = create_run_context(deps, run_id="test-run-id")
            self.deps = real_ctx.deps
            self.state = real_ctx.state
            self.agent = real_ctx.agent
            self.run_id = real_ctx.run_id
        else:
            # Simple mock for backward compatibility
            self.deps = deps
            self.state = {}
            self.agent = None
            self.run_id = "test-run-id"


# Helper for async iterators
async def async_iter(items):
    """Create an async iterator from a list."""
    for item in items:
        yield item


@pytest.fixture
def mock_run_context():
    """
    Create a MockRunContext factory.

    For tests that need a real RunContext, use create_run_context() directly:
    from server.projects.shared.context_helpers import create_run_context
    ctx = create_run_context(deps)
    """

    def _create(deps, use_real_context=False):
        return MockRunContext(deps, use_real_context=use_real_context)

    return _create


@pytest.fixture
def mock_ingestion_settings():
    """Create mock settings for DocumentIngestionPipeline."""
    settings = Mock()
    settings.mongodb_uri = "mongodb://localhost:27017"
    settings.mongodb_database = "test_db"
    settings.mongodb_collection_documents = "documents"
    settings.mongodb_collection_chunks = "chunks"
    settings.use_agentic_rag = False
    return settings


@pytest.fixture
def mock_graphiti_config():
    """Mock Graphiti config to disable Graphiti in tests."""
    with patch("server.projects.crawl4ai_rag.ingestion.adapter.graphiti_config") as mock_config:
        mock_config.use_graphiti = False
        yield mock_config


# Auth fixtures
@pytest.fixture
def mock_auth_config():
    """Mock AuthConfig for testing."""
    from unittest.mock import Mock

    config = Mock()
    config.cloudflare_auth_domain = "https://test.cloudflareaccess.com"
    config.cloudflare_aud_tag = "test-aud-tag"
    config.supabase_db_url = "postgresql://test:test@localhost:5432/test"
    config.supabase_service_key = "test-service-key"
    config.neo4j_uri = "bolt://localhost:7687"
    config.neo4j_user = "neo4j"
    config.neo4j_password = "test"
    config.neo4j_database = "neo4j"
    config.minio_endpoint = "http://localhost:9000"
    config.minio_access_key = "test-access"
    config.minio_secret_key = "test-secret"
    return config


@pytest.fixture
def mock_jwt_payload():
    """Mock JWT payload for testing."""
    return {
        "email": "test@example.com",
        "aud": "test-aud-tag",
        "iss": "https://test.cloudflareaccess.com",
        "exp": 9999999999,  # Far future
        "iat": 1000000000,
    }


@pytest.fixture
def mock_user():
    """Mock User model for testing."""
    from uuid import uuid4

    from server.projects.auth.models import User

    return User(id=uuid4(), email="test@example.com", role="user", tier="free")


@pytest.fixture
def mock_admin_user():
    """Mock admin User model for testing."""
    from uuid import uuid4

    from server.projects.auth.models import User

    return User(id=uuid4(), email="admin@example.com", role="admin", tier="pro")


@pytest.fixture
def mock_httpx_client():
    """Mock httpx.AsyncClient for testing."""
    from unittest.mock import AsyncMock, Mock

    client = AsyncMock()
    response = Mock()
    response.json = Mock(
        return_value={
            "keys": [{"kid": "test-key-id", "kty": "RSA", "use": "sig", "n": "test-n", "e": "AQAB"}]
        }
    )
    response.raise_for_status = Mock()
    client.get = AsyncMock(return_value=response)
    return client


@pytest.fixture
def mock_asyncpg_pool():
    """Mock asyncpg.Pool for testing."""
    from unittest.mock import AsyncMock

    pool = AsyncMock()
    connection = AsyncMock()
    connection.fetchrow = AsyncMock()
    connection.fetchval = AsyncMock()
    connection.execute = AsyncMock()
    pool.acquire = AsyncMock(return_value=AsyncMock().__aenter__())
    pool.acquire.return_value.__aenter__ = AsyncMock(return_value=connection)
    pool.acquire.return_value.__aexit__ = AsyncMock(return_value=None)
    return pool


@pytest.fixture
def mock_neo4j_driver():
    """Mock Neo4j driver for testing."""
    from unittest.mock import AsyncMock

    driver = AsyncMock()
    session = AsyncMock()
    transaction = AsyncMock()
    transaction.run = AsyncMock(return_value=AsyncMock())
    transaction.commit = AsyncMock()
    session.write_transaction = AsyncMock(return_value=transaction)
    session.close = AsyncMock()
    driver.session = AsyncMock(return_value=AsyncMock().__aenter__())
    driver.session.return_value.__aenter__ = AsyncMock(return_value=session)
    driver.session.return_value.__aexit__ = AsyncMock(return_value=None)
    driver.close = AsyncMock()
    return driver


@pytest.fixture
def mock_s3_client():
    """Mock boto3 S3 client for testing."""
    from unittest.mock import Mock

    client = Mock()
    client.list_objects_v2 = Mock(return_value={"Contents": []})
    client.put_object = Mock()
    client.head_bucket = Mock()
    client.create_bucket = Mock()
    client.generate_presigned_url = Mock(return_value="https://presigned-url.example.com/image.jpg")
    return client
