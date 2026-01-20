---
name: fastapi-development
description: Guide FastAPI development with testing, coverage, and design patterns. Use when building FastAPI endpoints, writing tests, configuring pytest, setting up coverage, creating dependency injection patterns, or when the user asks about API testing strategies.
---

# FastAPI Development

Best practices for building, testing, and maintaining FastAPI applications following this project's established patterns.

## Project Structure

Follow the domain-driven modular structure used in `04-lambda/src/`:

```
src/
├── capabilities/           # Domain capabilities (RAG, calendar, persona)
│   └── <domain>/
│       ├── __init__.py
│       ├── agent.py        # Pydantic AI agent definition
│       ├── config.py       # Domain-specific settings
│       ├── dependencies.py # Dependency injection class
│       ├── models.py       # Pydantic models
│       ├── router.py       # FastAPI router
│       ├── tools.py        # Agent tools
│       └── services/       # Business logic services
├── workflows/              # Multi-step workflows
├── services/               # Shared services (auth, storage, compute)
├── server/                 # FastAPI app entry point
│   ├── main.py
│   ├── dependencies.py
│   └── api/
└── shared/                 # Shared utilities
tests/
├── conftest.py             # Shared fixtures
├── test_<domain>/          # Domain-specific tests
└── test_samples/           # Sample script tests
```

## Dependency Injection Pattern

Use dataclass-based dependencies that inherit from `BaseDependencies`:

```python
from dataclasses import dataclass, field
from typing import Any
from shared.dependencies import BaseDependencies

@dataclass
class MyDependencies(BaseDependencies):
    """Dependencies injected into the service context."""

    # External clients
    mongo_client: AsyncMongoClient | None = None
    openai_client: openai.AsyncOpenAI | None = None

    # Configuration
    settings: Any | None = None

    # User context for RLS
    current_user_id: str | None = None
    current_user_email: str | None = None
    is_admin: bool = False

    @classmethod
    def from_settings(cls, **kwargs) -> "MyDependencies":
        """Factory method to create dependencies from settings."""
        return cls(**kwargs)

    async def initialize(self) -> None:
        """Initialize external connections."""
        # Initialize clients here
        pass

    async def cleanup(self) -> None:
        """Clean up external connections."""
        if self.mongo_client:
            await self.mongo_client.close()
```

## Router Pattern

Keep routers thin - delegate to services:

```python
from fastapi import APIRouter, Depends, HTTPException
from server.dependencies import get_current_user
from services.auth.models import User

router = APIRouter(prefix="/api/v1/myfeature", tags=["myfeature"])

@router.get("/items")
async def list_items(
    user: User = Depends(get_current_user),
    limit: int = 10,
) -> list[ItemResponse]:
    """List items for the current user."""
    deps = MyDependencies.from_settings(
        user_id=str(user.id),
        user_email=user.email,
    )
    await deps.initialize()
    try:
        service = MyService(deps)
        return await service.list_items(limit=limit)
    finally:
        await deps.cleanup()
```

## Router Prefix Convention

All routers **MUST** define their own prefix following the `/api/v1/{domain}` pattern. This ensures:
- Consistent API versioning across all endpoints
- Clear endpoint ownership (each router owns its prefix)
- No prefix duplication in `main.py` router registration
- Easier discovery and documentation

### Standard Prefix Patterns

| Layer | Prefix Pattern | Example |
|-------|----------------|---------|
| Auth | `/api/v1/auth` | `/api/v1/auth/me`, `/api/v1/auth/me/token` |
| Data Services | `/api/v1/data/{service}` | `/api/v1/data/mongodb`, `/api/v1/data/neo4j`, `/api/v1/data/supabase` |
| Capabilities | `/api/v1/capabilities` | `/api/v1/capabilities/persona/chat`, `/api/v1/capabilities/calendar/create` |
| RAG | `/api/v1/rag` | `/api/v1/rag/search`, `/api/v1/rag/ingest` |
| Workflows | `/api/v1/{workflow}` | `/api/v1/crawl/single`, `/api/v1/youtube/ingest`, `/api/v1/n8n/create` |
| Admin | `/api/v1/admin` | `/api/v1/admin/discord/config` |
| MCP | `/api/v1/mcp` | `/api/v1/mcp/tools/list`, `/api/v1/mcp/tools/call` |
| Preferences | `/api/v1/preferences` | `/api/v1/preferences/`, `/api/v1/preferences/{key}` |

### Router Definition Example

```python
# In your router.py - ALWAYS include prefix
router = APIRouter(prefix="/api/v1/myfeature", tags=["myfeature"])

# Routes are relative to the prefix
@router.get("/items")  # Full path: /api/v1/myfeature/items
async def list_items(): ...

@router.post("/items")  # Full path: /api/v1/myfeature/items
async def create_item(): ...
```

### Router Registration in main.py

Since routers define their own prefixes, registration in `main.py` is simple:

```python
# In server/main.py - NO additional prefix needed
from myfeature.router import router as myfeature_router

# Router already has prefix="/api/v1/myfeature"
app.include_router(myfeature_router)  # No prefix argument!
```

### Common Mistakes to Avoid

1. **Don't duplicate prefixes:**
   ```python
   # BAD - prefix defined twice
   router = APIRouter(prefix="/api/v1/feature")
   app.include_router(router, prefix="/api/v1/feature")  # Results in /api/v1/feature/api/v1/feature

   # GOOD - prefix defined once in router
   router = APIRouter(prefix="/api/v1/feature")
   app.include_router(router)  # Results in /api/v1/feature
   ```

2. **Don't omit the prefix in router definition:**
   ```python
   # BAD - no prefix in router, relies on main.py
   router = APIRouter()
   app.include_router(router, prefix="/api/v1/feature")

   # GOOD - prefix self-documented in router
   router = APIRouter(prefix="/api/v1/feature")
   app.include_router(router)
   ```

3. **Always include tags for OpenAPI grouping:**
   ```python
   # GOOD - tags help organize API docs
   router = APIRouter(prefix="/api/v1/calendar", tags=["capabilities", "calendar"])
   ```

## Testing Strategy

### Test Types

| Type | Location | Purpose |
|------|----------|---------|
| Unit | `tests/test_<domain>/test_*.py` | Test individual functions/classes in isolation |
| Integration | `tests/test_<domain>/test_*_integration.py` | Test component interactions |
| Endpoint | `tests/test_<domain>/test_*_endpoint.py` | Test FastAPI routes |
| Sample | `tests/test_samples/` | Validate sample scripts work |

### Pytest Configuration

In `pyproject.toml`:

```toml
[tool.pytest.ini_options]
asyncio_mode = "auto"
testpaths = ["tests"]
python_files = ["test_*.py"]
addopts = "-v --tb=short"
filterwarnings = [
    "ignore::DeprecationWarning",
]
```

### Mock Fixtures Pattern

Create reusable fixtures in `conftest.py`:

```python
import pytest
from unittest.mock import AsyncMock, Mock

@pytest.fixture
def mock_mongo_client():
    """Mock MongoDB client."""
    client = AsyncMock()
    client.__getitem__ = Mock(return_value=AsyncMock())
    return client

@pytest.fixture
def mock_openai_client():
    """Mock OpenAI client with proper structure."""
    client = AsyncMock()
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
def mock_dependencies(mock_mongo_client, mock_openai_client):
    """Mock dependencies for testing."""
    deps = AsyncMock()
    deps.mongo_client = mock_mongo_client
    deps.openai_client = mock_openai_client
    deps.initialize = AsyncMock()
    deps.cleanup = AsyncMock()
    return deps
```

### Testing Async Functions

```python
import pytest

@pytest.mark.asyncio
async def test_async_service(mock_dependencies):
    """Test async service method."""
    service = MyService(mock_dependencies)
    result = await service.process_data("input")
    assert result.status == "success"
```

### Testing FastAPI Endpoints

```python
import pytest
from fastapi.testclient import TestClient
from httpx import AsyncClient, ASGITransport

# Sync test client
def test_endpoint_sync(test_app):
    client = TestClient(test_app)
    response = client.get("/api/v1/items")
    assert response.status_code == 200

# Async test client (preferred for async routes)
@pytest.mark.asyncio
async def test_endpoint_async(test_app):
    transport = ASGITransport(app=test_app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/api/v1/items")
        assert response.status_code == 200
```

### Dependency Override for Testing

```python
from fastapi import FastAPI
from server.dependencies import get_current_user

@pytest.fixture
def test_app(mock_user):
    """Create test app with overridden dependencies."""
    from server.main import app

    app.dependency_overrides[get_current_user] = lambda: mock_user
    yield app
    app.dependency_overrides.clear()
```

## Coverage Configuration

See [coverage-config.md](coverage-config.md) for detailed `.coveragerc` and pytest-cov setup.

### Quick Coverage Command

```bash
# Run tests with coverage
pytest --cov=src --cov-report=term-missing --cov-report=html

# Fail if coverage drops below threshold
pytest --cov=src --cov-fail-under=80
```

## Error Handling

Use HTTPException with appropriate status codes:

```python
from fastapi import HTTPException, status

@router.get("/items/{item_id}")
async def get_item(item_id: str, user: User = Depends(get_current_user)):
    item = await service.get_item(item_id)
    if not item:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Item {item_id} not found"
        )
    if item.owner_id != str(user.id) and not user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to access this item"
        )
    return item
```

## Pydantic Models

Use Pydantic v2 patterns:

```python
from pydantic import BaseModel, Field
from datetime import datetime
from uuid import UUID

class ItemCreate(BaseModel):
    """Request model for creating an item."""
    name: str = Field(..., min_length=1, max_length=100)
    description: str | None = None

class ItemResponse(BaseModel):
    """Response model for an item."""
    id: UUID
    name: str
    description: str | None
    created_at: datetime
    owner_id: UUID

    model_config = {"from_attributes": True}
```

## Additional Resources

- [testing-patterns.md](testing-patterns.md) - Detailed fixture patterns and examples
- [coverage-config.md](coverage-config.md) - Coverage configuration templates
- [microservices-design.md](microservices-design.md) - API endpoint design conventions
