# Testing Patterns for FastAPI

Detailed fixture patterns and testing strategies based on this project's conventions.

## Fixture Categories

### 1. Database Mock Fixtures

```python
from unittest.mock import AsyncMock, Mock
import pytest
from bson import ObjectId

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
    """Mock MongoDB collection with common operations."""
    collection = AsyncMock()
    collection.aggregate = AsyncMock(return_value=AsyncMock())
    collection.find_one = AsyncMock()
    collection.insert_one = AsyncMock()
    collection.insert_many = AsyncMock()
    collection.update_one = AsyncMock()
    collection.delete_many = AsyncMock()
    return collection

@pytest.fixture
def mock_asyncpg_pool():
    """Mock asyncpg.Pool for PostgreSQL testing."""
    pool = AsyncMock()
    connection = AsyncMock()
    connection.fetchrow = AsyncMock()
    connection.fetchval = AsyncMock()
    connection.execute = AsyncMock()

    # Context manager support
    pool.acquire = AsyncMock(return_value=AsyncMock().__aenter__())
    pool.acquire.return_value.__aenter__ = AsyncMock(return_value=connection)
    pool.acquire.return_value.__aexit__ = AsyncMock(return_value=None)
    return pool
```

### 2. AI/LLM Mock Fixtures

```python
@pytest.fixture
def mock_openai_client():
    """Mock OpenAI client with chat completions structure."""
    client = AsyncMock()
    client.embeddings = AsyncMock()

    # Mock chat.completions.create structure
    mock_response = Mock()
    mock_choice = Mock()
    mock_choice.message = Mock()
    mock_choice.message.content = "Test response"
    mock_response.choices = [mock_choice]

    mock_create = AsyncMock(return_value=mock_response)
    mock_completions = Mock()
    mock_completions.create = mock_create
    mock_chat = Mock()
    mock_chat.completions = mock_completions
    client.chat = mock_chat

    return client

@pytest.fixture
def mock_embedding():
    """Mock embedding function returning consistent vectors."""
    async def _get_embedding(text: str) -> list[float]:
        return [0.1] * 2560  # Standard embedding dimension (Qwen3-Embedding-4B)
    return _get_embedding

@pytest.fixture
def mock_llm_json_response():
    """Mock LLM response with JSON content."""
    client = AsyncMock()

    mock_response = Mock()
    mock_choice = Mock()
    mock_choice.message = Mock()
    mock_choice.message.content = '{"result": "success", "data": []}'
    mock_response.choices = [mock_choice]

    mock_create = AsyncMock(return_value=mock_response)
    mock_completions = Mock()
    mock_completions.create = mock_create
    mock_chat = Mock()
    mock_chat.completions = mock_completions
    client.chat = mock_chat

    return client
```

### 3. Authentication Mock Fixtures

```python
from uuid import uuid4

@pytest.fixture
def mock_user():
    """Mock User model for testing."""
    from services.auth.models import User
    return User(
        id=uuid4(),
        email="test@example.com",
        role="user",
        tier="free"
    )

@pytest.fixture
def mock_admin_user():
    """Mock admin User model for testing."""
    from services.auth.models import User
    return User(
        id=uuid4(),
        email="admin@example.com",
        role="admin",
        tier="pro"
    )

@pytest.fixture
def mock_jwt_payload():
    """Mock JWT payload for Cloudflare Access testing."""
    return {
        "email": "test@example.com",
        "aud": "test-aud-tag",
        "iss": "https://test.cloudflareaccess.com",
        "exp": 9999999999,  # Far future
        "iat": 1000000000,
    }

@pytest.fixture
def mock_auth_config():
    """Mock AuthConfig for testing."""
    config = Mock()
    config.cloudflare_auth_domain = "https://test.cloudflareaccess.com"
    config.cloudflare_aud_tag = "test-aud-tag"
    config.supabase_db_url = "postgresql://test:test@localhost:5432/test"
    return config
```

### 4. HTTP Client Mock Fixtures

```python
@pytest.fixture
def mock_httpx_client():
    """Mock httpx.AsyncClient for testing."""
    client = AsyncMock()
    response = Mock()
    response.json = Mock(return_value={"status": "ok"})
    response.raise_for_status = Mock()
    response.status_code = 200
    client.get = AsyncMock(return_value=response)
    client.post = AsyncMock(return_value=response)
    return client

@pytest.fixture
def mock_aiohttp_session():
    """Mock aiohttp.ClientSession for testing."""
    session = AsyncMock()
    response = AsyncMock()
    response.status = 200
    response.json = AsyncMock(return_value={"data": "test"})
    response.raise_for_status = AsyncMock()

    # Context manager support
    session.get = AsyncMock(return_value=response)
    session.post = AsyncMock(return_value=response)
    return session
```

### 5. Sample Data Fixtures

```python
@pytest.fixture
def sample_document():
    """Sample document for testing."""
    return {
        "_id": ObjectId(),
        "title": "Test Document",
        "source": "test_source",
        "metadata": {
            "source": "test",
            "user_id": "user1",
            "conversation_id": "conv1"
        },
    }

@pytest.fixture
def sample_chunk(sample_document):
    """Sample chunk for testing."""
    return {
        "_id": ObjectId(),
        "document_id": sample_document["_id"],
        "content": "This is a test chunk with some content.",
        "embedding": [0.1] * 2560,
        "metadata": {"chunk_index": 0, "source": "test"},
        "document_info": {
            "title": sample_document["title"],
            "source": sample_document["source"]
        },
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
        }
    ]
```

## Testing Patterns

### Pattern 1: Testing Services with Mocked Dependencies

```python
import pytest
from unittest.mock import AsyncMock, patch

@pytest.mark.asyncio
async def test_service_method(mock_dependencies):
    """Test a service method with mocked dependencies."""
    # Arrange
    mock_dependencies.db["collection"].find_one = AsyncMock(
        return_value={"id": "123", "name": "test"}
    )

    service = MyService(mock_dependencies)

    # Act
    result = await service.get_item("123")

    # Assert
    assert result is not None
    assert result["name"] == "test"
    mock_dependencies.db["collection"].find_one.assert_awaited_once()
```

### Pattern 2: Testing FastAPI Endpoints

```python
import pytest
from fastapi.testclient import TestClient
from httpx import AsyncClient, ASGITransport

@pytest.fixture
def test_app(mock_user):
    """Create test app with dependency overrides."""
    from server.main import app
    from server.dependencies import get_current_user

    app.dependency_overrides[get_current_user] = lambda: mock_user
    yield app
    app.dependency_overrides.clear()

def test_list_items_sync(test_app):
    """Test endpoint with sync client."""
    client = TestClient(test_app)
    response = client.get("/api/v1/items")

    assert response.status_code == 200
    assert isinstance(response.json(), list)

@pytest.mark.asyncio
async def test_list_items_async(test_app):
    """Test endpoint with async client."""
    transport = ASGITransport(app=test_app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/api/v1/items")

        assert response.status_code == 200
```

### Pattern 3: Testing with Context Managers

```python
@pytest.mark.asyncio
async def test_with_context_manager():
    """Test code that uses context managers."""
    deps = MyDependencies.from_settings()

    # Use patch for external services
    with patch.object(deps, 'mongo_client', new=AsyncMock()):
        await deps.initialize()
        try:
            result = await some_function(deps)
            assert result is not None
        finally:
            await deps.cleanup()
```

### Pattern 4: Parameterized Tests

```python
import pytest

@pytest.mark.parametrize("input_data,expected", [
    ({"name": "test"}, True),
    ({"name": ""}, False),
    ({}, False),
])
def test_validate_input(input_data, expected):
    """Test input validation with multiple cases."""
    result = validate_input(input_data)
    assert result == expected

@pytest.mark.parametrize("status_code,should_retry", [
    (200, False),
    (429, True),
    (500, True),
    (404, False),
])
@pytest.mark.asyncio
async def test_retry_logic(status_code, should_retry, mock_httpx_client):
    """Test retry logic for different status codes."""
    mock_httpx_client.get.return_value.status_code = status_code
    result = await should_retry_request(status_code)
    assert result == should_retry
```

### Pattern 5: Testing Error Handling

```python
import pytest
from fastapi import HTTPException

@pytest.mark.asyncio
async def test_not_found_raises_404(mock_dependencies):
    """Test that missing resource raises 404."""
    mock_dependencies.db["collection"].find_one = AsyncMock(return_value=None)

    service = MyService(mock_dependencies)

    with pytest.raises(HTTPException) as exc_info:
        await service.get_item("nonexistent")

    assert exc_info.value.status_code == 404

@pytest.mark.asyncio
async def test_unauthorized_raises_403(mock_dependencies, mock_user):
    """Test that unauthorized access raises 403."""
    mock_dependencies.db["collection"].find_one = AsyncMock(
        return_value={"owner_id": "different-user"}
    )

    service = MyService(mock_dependencies)

    with pytest.raises(HTTPException) as exc_info:
        await service.get_item("123", user=mock_user)

    assert exc_info.value.status_code == 403
```

### Pattern 6: Testing Background Tasks

```python
from unittest.mock import patch, AsyncMock

@pytest.mark.asyncio
async def test_background_task_scheduled():
    """Test that background task is scheduled correctly."""
    mock_task = AsyncMock()

    with patch("mymodule.background_task", mock_task):
        await endpoint_that_schedules_task()

        # Verify task was called
        mock_task.assert_called_once()
```

## RunContext Testing

For testing Pydantic AI agents, use the `create_run_context` helper:

```python
from shared.context_helpers import create_run_context

@pytest.mark.asyncio
async def test_agent_tool_directly(mock_dependencies):
    """Test agent tool without running full agent."""
    await mock_dependencies.initialize()

    try:
        ctx = create_run_context(mock_dependencies)
        result = await my_tool(ctx, query="test")
        assert "expected" in result
    finally:
        await mock_dependencies.cleanup()
```

## Async Iterator Testing

```python
async def async_iter(items):
    """Helper to create async iterator from list."""
    for item in items:
        yield item

@pytest.mark.asyncio
async def test_async_iteration():
    """Test code that consumes async iterators."""
    items = [1, 2, 3]
    result = []

    async for item in async_iter(items):
        result.append(item)

    assert result == items
```
