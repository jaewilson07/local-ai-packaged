# Lambda Stack - AGENTS.md

> **Multi-Editor Support**: Both GitHub Copilot and Cursor AI read this file. Rules here override the root AGENTS.md for Lambda server concerns.

> **Override**: This file extends [../AGENTS.md](../AGENTS.md). Lambda stack rules take precedence.

## Overview

FastAPI multi-project server providing REST APIs and MCP (Model Context Protocol) endpoints. Designed for clean separation of concerns and easy addition of new projects.

## Design Strategy

### Core Philosophy

**Multi-Project Lambda Server**: A unified FastAPI application that hosts multiple independent capabilities and workflows while maintaining clean boundaries and shared infrastructure.

**Key Principles:**
1. **Capability Isolation**: Each capability is self-contained in `src/capabilities/{category}/{name}/`
2. **Workflow Organization**: Workflows are organized in `src/workflows/{category}/{name}/`
3. **Dual Interface**: Every capability/workflow exposes both REST API and MCP endpoints
4. **Shared Infrastructure**: Common utilities (logging, config, exceptions) in `src/shared/`
5. **Type Safety**: Pydantic models for all data structures
6. **Async First**: All I/O operations are async
6. **Clean Architecture**: No backward compatibility concerns, modern patterns only

### Architecture Layers

```
┌─────────────────────────────────────────────────────────┐
│                    Client Layer                          │
│  (REST Clients, MCP Clients, Web UIs)                   │
└─────────────────────────────────────────────────────────┘
                          │
┌─────────────────────────────────────────────────────────┐
│                   FastAPI Server                         │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐  │
│  │  REST API    │  │  MCP Server  │  │  WebSocket   │  │
│  │  Routers     │  │  Protocol    │  │  (Future)    │  │
│  └──────────────┘  └──────────────┘  └──────────────┘  │
└─────────────────────────────────────────────────────────┘
                          │
┌─────────────────────────────────────────────────────────┐
│                  Project Layer                           │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐  │
│  │  RAG Project │  │  Pipeline    │  │  Future      │  │
│  │  (Agents)    │  │  Project     │  │  Projects    │  │
│  └──────────────┘  └──────────────┘  └──────────────┘  │
└─────────────────────────────────────────────────────────┘
                          │
┌─────────────────────────────────────────────────────────┐
│              External Services Layer                     │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐  │
│  │  MongoDB     │  │  Ollama      │  │  Other       │  │
│  │  (01-data)   │  │  (02-compute)│  │  Services    │  │
│  └──────────────┘  └──────────────┘  └──────────────┘  │
└─────────────────────────────────────────────────────────┘
```

### Pydantic AI Agent Standard

All agents in this server follow the **Pydantic AI Agent Implementation Standard** from `.cursor/instructions/agent_design.md`.

**Naming Conventions:**
- Dependencies MUST end with "Deps": `AgentDeps`, `RouletteDeps`
- Response models MUST end with "Response": `SearchResponse`, `IngestResponse`
- Agent instances: descriptive snake_case (e.g., `rag_agent`, `caption_validation_agent`)

**Agent Structure:**
```python
# 1. Dependencies (dataclass with @classmethod from_settings)
@dataclass
class ProjectDeps:
    """Runtime dependencies for project."""
    http_client: httpx.AsyncClient
    db_client: AsyncMongoClient
    api_key: str

    @classmethod
    def from_settings(cls, ...) -> "ProjectDeps":
        """Create dependencies from application settings."""
        pass

# 2. Response Model (Pydantic BaseModel)
class ProjectResponse(BaseModel):
    """Structured response from agent."""
    result: str = Field(description="...")
    metadata: Dict[str, Any] = Field(default_factory=dict)

# 3. Model Factory
def _get_project_model() -> OpenAIModel:
    """Factory function to get the model."""
    return get_agent_model("PROJECT")

# 4. System Prompts (static or dynamic)
project_system_prompt = "You are a helpful assistant..."

# OR dynamic:
@project_agent.system_prompt
async def dynamic_prompt(ctx: RunContext[ProjectDeps]) -> str:
    return f"Context: {ctx.deps.context}"

# 5. Agent Definition
project_agent = Agent(
    _get_project_model(),
    deps_type=ProjectDeps,
    output_type=ProjectResponse,
    retries=3,
    system_prompt=project_system_prompt,
)

# 6. Tools
@project_agent.tool
async def tool_name(ctx: RunContext[ProjectDeps], arg: str) -> str:
    """Tool description."""
    # Use ctx.deps to access dependencies
    pass

**Tool Implementation:**
- Tools MUST use `RunContext[DepsType]` as first parameter
- Access dependencies via `ctx.deps` (never initialize dependencies inside tools)
- Samples and tests MUST use `create_run_context()` helper for RunContext creation
- See `src/shared/context_helpers.py` for helper implementation

# 7. Output Validation (optional)
@project_agent.output_validator
async def validate_output(
    ctx: RunContext[ProjectDeps],
    output: ProjectResponse
) -> ProjectResponse:
    """Validate and potentially modify output."""
    if not output.result:
        raise ModelRetry("Result cannot be empty")
    return output
```

### Project Structure Standard

Each project follows this structure:

```
src/capabilities/{category}/{name}/
├── __init__.py
├── config.py              # Capability-specific configuration
├── dependencies.py        # CapabilityDeps class
├── agent.py              # Agent definition
├── tools.py              # Agent tools
├── prompts.py            # System prompts
└── {domain}/             # Domain-specific modules
    ├── pipeline.py       # Data processing pipelines
    ├── validators.py     # Validation logic
    └── utils.py          # Utilities
```

### REST API Design

**Authentication:**
All API endpoints (except `/health` and `/docs`) require Cloudflare Access authentication via `get_current_user` dependency:

```python
from server.projects.auth.dependencies import get_current_user
from server.projects.auth.models import User

@router.get("/protected")
async def endpoint(user: User = Depends(get_current_user)):
    """Endpoint requires authentication."""
    return {"email": user.email}
```

**Endpoint Pattern:**
```python
from fastapi import APIRouter, HTTPException, Depends
from server.models.{project} import RequestModel, ResponseModel
from server.projects.{project}.dependencies import ProjectDeps
from server.projects.auth.dependencies import get_current_user
from server.projects.auth.models import User

router = APIRouter()

@router.post("/endpoint", response_model=ResponseModel)
async def endpoint(
    request: RequestModel,
    user: User = Depends(get_current_user)  # Authentication required
):
    """Endpoint description."""
    deps = ProjectDeps.from_settings()
    await deps.initialize()  # If needed

    try:
        # Business logic (user context available)
        result = await process(deps, request, user)
        return ResponseModel(result=result)
    except SpecificError as e:
        logger.exception("operation_failed")
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        await deps.cleanup()  # If needed
```

**Router Registration:**
```python
# In server/main.py
from server.api import project_router
app.include_router(
    project_router.router,
    prefix="/api/v1/project",
    tags=["project"]
)
```

## API Documentation

For comprehensive API routing standards, error handling, and cross-linked capability/workflow documentation, see:

- **[API Strategy](docs/API_STRATEGY.md)** - Central API documentation hub with:
  - Route naming conventions and prefix standards
  - Standardized error handling with `APIError` model
  - Capability and workflow API documentation links
  - Router registration patterns

### MCP Server Design

**Tool Registration Pattern:**
```python
# In src/mcp_server/server.py
def setup_routes(app: FastAPI):
    @app.post("/mcp/tools/list")
    async def list_tools():
        return {
            "tools": [
                {
                    "name": "tool_name",
                    "description": "What the tool does",
                    "inputSchema": {
                        "type": "object",
                        "properties": {
                            "param": {"type": "string", "description": "..."}
                        },
                        "required": ["param"]
                    }
                }
            ]
        }

    @app.post("/mcp/tools/call")
    async def call_tool(request: Request):
        body = await request.json()
        tool = body["name"]
        args = body.get("arguments", {})

        # Call REST endpoint internally (no code duplication)
        if tool == "tool_name":
            from server.api.project import endpoint
            result = await endpoint(RequestModel(**args))
            return {"content": [{"type": "text", "text": str(result)}]}
```

### Configuration Management

**Three-Level Configuration:**

1. **Global Config** (`server/config.py`):
```python
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    """Global server settings."""
    mongodb_uri: str
    llm_model: str = "llama3.2"
    log_level: str = "info"

    class Config:
        env_file = ".env"
        case_sensitive = False

settings = Settings()
```

2. **Project Config** (`src/capabilities/{category}/{name}/config.py` or `src/workflows/{category}/{name}/config.py`):
```python
from server.config import settings as global_settings

class ProjectConfig:
    """Project-specific configuration."""
    # Derive from global
    mongodb_uri = global_settings.mongodb_uri
    llm_model = global_settings.llm_model

    # Project-specific
    collection_name = "project_data"
    max_retries = 3

config = ProjectConfig()
```

3. **Runtime Config** (via Dependencies):
```python
@dataclass
class ProjectDeps:
    """Runtime dependencies."""
    config: ProjectConfig = field(default_factory=lambda: config)

    @classmethod
    def from_settings(cls, override_config: Optional[ProjectConfig] = None):
        return cls(config=override_config or config)
```

### Error Handling Strategy

**Layered Error Handling:**

1. **Project Layer**: Business logic errors
```python
class ProjectError(Exception):
    """Base exception for project."""
    pass

class ValidationError(ProjectError):
    """Validation failed."""
    pass
```

2. **API Layer**: HTTP exceptions
```python
try:
    result = await project_operation()
except ValidationError as e:
    raise HTTPException(status_code=400, detail=str(e))
except ProjectError as e:
    raise HTTPException(status_code=500, detail=str(e))
```

3. **Agent Layer**: Model retries
```python
@agent.output_validator
async def validate(ctx, output):
    if not output.is_valid:
        raise ModelRetry("Invalid output, retry")
    return output
```

### Testing Strategy

**Test Structure:**
```
tests/
├── unit/
│   ├── test_config.py
│   ├── test_dependencies.py
│   └── projects/
│       └── test_project_agent.py
├── integration/
│   ├── test_api_endpoints.py
│   └── test_mcp_server.py
└── e2e/
    └── test_full_workflow.py
```

**Testing Patterns:**
```python
import pytest
from httpx import AsyncClient

@pytest.mark.asyncio
async def test_endpoint():
    async with AsyncClient(app=app, base_url="http://test") as client:
        response = await client.post(
            "/api/v1/project/endpoint",
            json={"param": "value"}
        )
        assert response.status_code == 200
```

### RunContext Patterns for Testing

**Helper Function**: `src/shared/context_helpers.create_run_context()`

**Testing Tools Directly:**
```python
from server.projects.shared.context_helpers import create_run_context
from server.projects.mongo_rag.dependencies import AgentDependencies
from server.projects.mongo_rag.tools import semantic_search

@pytest.mark.asyncio
async def test_semantic_search():
    deps = AgentDependencies()
    await deps.initialize()
    try:
        ctx = create_run_context(deps)
        results = await semantic_search(ctx, query="test")
        assert len(results) >= 0
    finally:
        await deps.cleanup()
```

**Testing Agents:**
```python
from server.projects.mongo_rag.agent import rag_agent

@pytest.mark.asyncio
async def test_rag_agent():
    deps = AgentDependencies()
    await deps.initialize()
    try:
        result = await rag_agent.run("What is RAG?", deps=deps)
        assert result.data is not None
    finally:
        await deps.cleanup()
```

**Key Points:**
- Tools expect `RunContext[DepsType]` - use `create_run_context()` to create properly typed contexts
- Never manually construct `RunContext()` - always use the helper
- Dependencies are accessed via `ctx.deps` in tools
- Always cleanup dependencies in `finally` blocks

## Architecture

### Stack Position
- **Stack**: 04-lambda
- **Project Name**: `localai-lambda` (independent stack with own project name)
- **Dependencies**: 00-infrastructure (network), 01-data (MongoDB), 02-compute (Ollama)
- **Network**: `ai-network` (external, shared across all stacks)

### Service
- **Container**: `lambda-server`
- **Image**: Built from local Dockerfile
- **Port**: 8000 (internal only, exposed via Caddy if needed)
- **Restart**: `unless-stopped`
- **Package Persistence**: Python packages stored in Docker volume `lambda-packages:/opt/venv`
  - Packages installed on first run via entrypoint script
  - Subsequent restarts reuse existing packages (no reinstallation)
  - Volume persists across container restarts and rebuilds

### Database Validation & Migrations
- **Startup Validation**: Lambda server validates core database tables exist on startup
- **Automatic Migration Application**: Migrations from `01-data/supabase/migrations/` are automatically applied if tables are missing
- **Core Tables**: `profiles` table is validated (CRITICAL - required for authentication)
- **Optional Tables**: `comfyui_workflows`, `comfyui_workflow_runs`, `comfyui_lora_models` are checked but missing them won't prevent startup
- **Service**: `DatabaseValidationService` in `src/services/auth/services/database_validation_service.py`
- **Integration**: Validation runs during FastAPI lifespan startup (before accepting requests)
- **Protection**: Core tables are validated on every startup to prevent accidental deletion
- **Documentation**: See [Supabase Migrations README](../01-data/supabase/migrations/README.md)

## Patterns

### Project Structure
```
server/
├── api/              # REST API routers
├── mcp/              # MCP server implementation
├── projects/         # Project modules (isolated)
│   ├── mongo_rag/   # MongoDB RAG project
│   ├── crawl4ai_rag/ # Crawl4AI RAG project
│   ├── graphiti_rag/ # Graphiti RAG project
│   └── n8n_workflow/ # N8n workflow management project
│       ├── config.py
│       ├── dependencies.py
│       ├── agent.py
│       ├── tools.py
│       ├── prompts.py
│       └── models.py
├── models/           # Pydantic schemas
└── core/             # Shared utilities
```

### Configuration
- **Global**: `server/config.py` (Pydantic Settings from env vars)
- **Project-specific**: `src/capabilities/{category}/{name}/config.py` or `src/workflows/{category}/{name}/config.py` (derives from global)
- **Environment**: `.env` file (Docker Compose injects into container)

### Database Connections
- **MongoDB**: Internal Docker network (`mongodb://mongodb:27017`)
- **Connection Pool**: Managed by PyMongo AsyncMongoClient
- **Cleanup**: Always cleanup in `finally` blocks

### API Patterns
```python
# REST endpoint pattern
@router.post("/endpoint")
async def endpoint(request: RequestModel):
    deps = AgentDependencies()
    await deps.initialize()
    try:
        # Do work
        return ResponseModel(...)
    finally:
        await deps.cleanup()
```

### MCP Integration
- Tools registered in `src/mcp_server/server.py`
- Calls REST endpoints internally (no code duplication)
- Returns formatted text responses

## API Endpoints Overview

### Public Endpoints (No Authentication)
- `GET /health` - Health check
- `GET /docs` - OpenAPI documentation
- `GET /openapi.json` - OpenAPI specification
- `GET /mcp-info` - MCP server information

### Authenticated Endpoints (Require Cloudflare Access JWT)

**Auth & Identity:**
- `GET /api/me` - Get current user profile
- `GET /api/me/data` - Get data summary across all services
- `GET /api/me/data/rag` - Get RAG data summary (MongoDB + Supabase)
- `GET /api/me/data/immich` - Get Immich data summary (placeholder)
- `GET /api/me/data/loras` - Get LoRA models summary

**Data Viewing:**
- `GET /api/v1/data/storage` - View MinIO/blob storage files
- `GET /api/v1/data/supabase` - View Supabase table data
- `GET /api/v1/data/neo4j` - View Neo4j nodes and relationships
- `GET /api/v1/data/mongodb` - View MongoDB collection data

**RAG & Knowledge:**
- `POST /api/v1/rag/search` - Search MongoDB RAG knowledge base
- `POST /api/v1/rag/ingest` - Ingest documents
- `POST /api/v1/rag/agent` - Query conversational agent
- `POST /api/v1/crawl/single` - Crawl single page
- `POST /api/v1/crawl/deep` - Deep crawl website
- `POST /api/v1/graphiti/search` - Search Graphiti knowledge graph

**Workflows & Automation:**
- `POST /api/v1/n8n/create` - Create N8n workflow
- `POST /api/v1/n8n/update` - Update workflow
- `GET /api/v1/n8n/list` - List workflows
- `POST /api/v1/n8n/execute` - Execute workflow

**Calendar:**
- `POST /api/v1/calendar/events/create` - Create calendar event
- `POST /api/v1/calendar/events/update` - Update event
- `POST /api/v1/calendar/events/delete` - Delete event
- `GET /api/v1/calendar/events/list` - List events
- `POST /api/v1/calendar/sync` - Sync calendar

**Storage:**
- `POST /api/v1/storage/upload` - Upload file
- `GET /api/v1/storage/list` - List files
- `GET /api/v1/storage/download/{filename}` - Download file
- `DELETE /api/v1/storage/delete/{filename}` - Delete file
- `GET /api/v1/storage/url/{filename}` - Get presigned URL

**Other:**
- `POST /api/v1/conversation/orchestrate` - Orchestrate multi-agent conversation
- `POST /api/v1/persona/get-voice` - Get persona voice instructions
- `GET /api/v1/persona/state` - Get persona state
- `POST /api/v1/openwebui/export` - Export conversation to RAG
- `POST /api/v1/openwebui/classify` - Classify conversation topics

## Adding New Projects

1. **Create project folder**: `src/capabilities/{category}/{name}/` or `src/workflows/{category}/{name}/`
   - `config.py` - Project configuration
   - `dependencies.py` - External connections
   - `tools.py` - Core functionality

2. **Create API router**: `server/api/your_project.py`
   - Define endpoints
   - Use Pydantic models from `server/models/`
   - **Add authentication**: Use `Depends(get_current_user)` for protected endpoints

3. **Register in main**: `server/main.py`
   ```python
   from server.api import your_project
   app.include_router(your_project.router, prefix="/api/v1/your_project", tags=["your-project"])
   ```

4. **Add MCP tools**: `src/mcp_server/server.py` (if using FastMCP)
   - Tools are automatically registered from project agent definitions

## Dependencies

### Python Packages
- FastAPI + Uvicorn (web framework)
- Pydantic AI (agent framework)
- PyMongo (MongoDB async driver)
- OpenAI (embeddings API)
- Docling (document processing)

### External Services
- MongoDB (01-data stack)
- Ollama (02-compute stack)

## Environment Variables

### Required
- `MONGODB_URI` - MongoDB connection string
- `MONGODB_DATABASE` - Database name

### Optional (with defaults)
- `LLM_PROVIDER` - LLM provider (default: ollama)
- `LLM_MODEL` - Model name (default: llama3.2)
- `LLM_BASE_URL` - API base URL (default: http://ollama:11434/v1)
- `EMBEDDING_MODEL` - Embedding model (default: qwen3-embedding:4b)
- `LOG_LEVEL` - Logging level (default: info)

## Service Composition Patterns

### Composition Class Architecture

**Rule**: When creating service classes that need to be broken down for SOLID principles, use **inner classes with Capital letters for composition**.

**Pattern**: `ServiceClass.ComponentName` (e.g., `GoogleDrive.Search`, `GoogleDrive.Export`)

#### Base Class Hierarchy

**Always use ABC and Protocol when reasonable:**

```python
from abc import ABC, abstractmethod
from typing import Protocol, runtime_checkable

@runtime_checkable
class ServiceProtocol(Protocol):
    """Protocol for service with common operations."""
    authenticator: AuthType

    def core_operation(self, param: str) -> dict: ...

class BaseService(ABC):
    """Base service with shared authentication and setup."""

    def __init__(self, authenticator: AuthType):
        self.authenticator = authenticator

    @abstractmethod
    def initialize(self): ...

class BaseComponent(ABC):
    """Base class for service components."""

    def __init__(self, parent: ServiceProtocol):
        """Always pass parent reference for access to service."""
        self._parent = parent

    @abstractmethod
    def component_operation(self, **kwargs): ...
```

#### Service Implementation Pattern

```python
class GoogleDrive(BaseService):
    """Service with composition-based architecture."""

    def __init__(self, authenticator: GoogleAuth):
        super().__init__(authenticator)

        # Composition: Initialize inner class instances
        self.Search = GoogleDrive.Search(self)
        self.Export = GoogleDrive.Export(self)

    class Search(BaseSearch):
        """Search operations as inner class."""

        def _execute_search(self, query: str, **kwargs) -> dict:
            # Access parent service via self._parent
            return self._parent.api_call(query)

    class Export(BaseExport):
        """Export operations as inner class."""

        def _download_content(self, file_id: str) -> str:
            return self._parent.download(file_id)
```

#### Usage Pattern

```python
# Create service instance
service = GoogleDrive(authenticator)

# Use composed functionality
results = service.Search.search("query")
content = service.Export.export_as_markdown("doc_id")

# Service still has core methods
metadata = service.get_file_metadata("file_id")
```

#### Configuration Pattern

**Always move hardcoded constants to config files:**

```python
# config.py
DEFAULT_FOLDER_ID = "13ICM72u7cnvCb0ATpVXdHWqxH1SmiG_Q"
DEFAULT_PAGE_SIZE = 10
EXPORT_MIME_TYPES = {
    "markdown": "text/plain",
    "html": "text/html"
}

# service.py
from .config import DEFAULT_FOLDER_ID, DEFAULT_PAGE_SIZE
```

### Exception Patterns

**Create service-specific exception hierarchies:**

```python
class ServiceException(Exception):
    """Base exception for service operations."""

    def __init__(self, message: str, original_error: Exception | None = None):
        super().__init__(message)
        self.original_error = original_error

class ServiceAuthError(ServiceException): ...
class ServiceNotFoundError(ServiceException): ...
class ServiceExportError(ServiceException): ...
```

**Usage in methods:**

```python
try:
    result = api_call()
except HttpError as e:
    if e.resp.status == 404:
        raise ServiceNotFoundError(f"Resource not found: {resource_id}", e)
    raise ServiceException(f"API call failed: {e}", e)
```

### When to Apply This Pattern

**Use composition with inner classes when:**
- Service has multiple distinct responsibilities (Search, Export, Import)
- Components share common parent functionality
- Want to maintain single entry point but organize by concern
- Each component needs access to parent service methods

**Example services to refactor:**
- `ComfyUIService` → `ComfyUI.Workflow`, `ComfyUI.Model`, `ComfyUI.Queue`
- `MinIOService` → `MinIO.Upload`, `MinIO.Download`, `MinIO.Bucket`
- `Neo4jService` → `Neo4j.Query`, `Neo4j.Graph`, `Neo4j.Schema`

## Common Patterns

### Async MongoDB Operations
```python
from pymongo import AsyncMongoClient

client = AsyncMongoClient(uri, serverSelectionTimeoutMS=5000)
db = client[database_name]
collection = db[collection_name]

# Always use async/await
result = await collection.find_one({"_id": doc_id})
results = await collection.aggregate(pipeline).to_list(length=limit)
```

### Error Handling
```python
try:
    result = await operation()
except ConnectionFailure as e:
    logger.exception("mongodb_connection_failed")
    raise HTTPException(status_code=503, detail="Database unavailable")
except Exception as e:
    logger.exception("operation_failed")
    raise HTTPException(status_code=500, detail=str(e))
```

### Structured Logging
```python
import logging

logger = logging.getLogger(__name__)

# Use extra dict for structured data
logger.info("operation_completed", extra={"count": 10, "duration_ms": 123})
logger.error("operation_failed", extra={"error": str(e)})
```

## Testing

### Health Checks
```bash
# Basic health
curl http://lambda-server:8000/health

# MongoDB health
curl http://lambda-server:8000/health/mongodb
```

### API Testing
```bash
# Search endpoint
curl -X POST http://lambda-server:8000/api/v1/rag/search \
  -H "Content-Type: application/json" \
  -d '{"query": "test", "search_type": "hybrid"}'
```

### MCP Testing
```bash
# List tools
curl -X POST http://lambda-server:8000/mcp/tools/list

# Call tool
curl -X POST http://lambda-server:8000/mcp/tools/call \
  -H "Content-Type: application/json" \
  -d '{"name": "search_knowledge_base", "arguments": {"query": "test"}}'
```

## Troubleshooting

### Container Won't Start
```bash
# Check logs
docker logs lambda-server

# Check dependencies
docker ps | grep -E "mongodb|ollama"

# Rebuild
cd 04-lambda
docker compose build --no-cache
```

### MongoDB Connection Issues
```bash
# Test MongoDB from Lambda container
docker exec lambda-server curl -f http://mongodb:27017

# Check MongoDB is healthy
docker exec mongodb mongosh --eval "db.adminCommand('ping')"
```

### Import Errors
- Ensure all `__init__.py` files exist
- Check import paths use `server.` prefix
- Verify dependencies in `pyproject.toml`

## N8n Workflow Project

### Overview
The N8n Workflow project provides agentic workflow management for N8n automation platform. It enables AI agents to create, update, delete, activate, and execute N8n workflows through natural language.

**Standards Compliance**: This project fully complies with the Pydantic AI Agent Implementation Standard. See [STANDARDS_COMPLIANCE.md](src/workflows/automation/n8n_workflow/docs/STANDARDS_COMPLIANCE.md) for details.

### Architecture
- **Agent**: Pydantic AI agent with N8n workflow management tools
- **Dependencies**: `N8nWorkflowDeps` with httpx client for N8n API
- **API**: REST endpoints at `/api/v1/n8n/*`
- **MCP Tools**: 6 tools for workflow operations

### Configuration
- **N8n API URL**: `N8N_API_URL` (default: `http://n8n:5678/api/v1`)
- **N8n API Key**: `N8N_API_KEY` (optional, for authentication)

### API Endpoints
- `POST /api/v1/n8n/create` - Create new workflow
- `POST /api/v1/n8n/update` - Update existing workflow
- `POST /api/v1/n8n/delete` - Delete workflow
- `POST /api/v1/n8n/activate` - Activate/deactivate workflow
- `GET /api/v1/n8n/list` - List all workflows
- `POST /api/v1/n8n/execute` - Execute workflow manually

### MCP Tools
- `create_n8n_workflow` - Create workflow with nodes and connections
- `update_n8n_workflow` - Update workflow properties
- `delete_n8n_workflow` - Delete workflow permanently
- `activate_n8n_workflow` - Activate or deactivate workflow
- `list_n8n_workflows` - List all workflows (optionally active only)
- `execute_n8n_workflow` - Execute workflow with input data
- `discover_n8n_nodes` - Discover available nodes via N8n API
- `search_n8n_knowledge_base` - Search knowledge base for N8n documentation and examples
- `search_n8n_node_examples` - Search for specific node configuration examples

### Agent Tools (RAG-Enhanced)
The agent provides natural language interface to workflow operations with RAG capabilities:
- **Knowledge Base Search**: Searches MongoDB RAG for N8n documentation, examples, and best practices
- **Node Discovery**: Discovers available nodes via N8n API
- **Node Examples**: Finds configuration examples for specific nodes
- **Workflow Creation**: Uses RAG to inform workflow design before creation
- **Iterative Refinement**: Adapts searches based on results

### RAG Integration
The agent uses Retrieval-Augmented Generation (RAG) to:
1. **Search before creating**: Always searches knowledge base before creating workflows
2. **Discover nodes**: Uses API to discover available node types
3. **Find examples**: Searches for node configuration examples
4. **Cite sources**: References knowledge base sources in responses

See [ENHANCEMENT_RESEARCH.md](src/workflows/automation/n8n_workflow/docs/ENHANCEMENT_RESEARCH.md) for detailed research and implementation strategy.

### Integration Points
- **N8n Service**: `http://n8n:5678` (from 03-apps stack)
- **Network**: `ai-network` (shared Docker network)

## Discord Characters Project

### Overview
The Discord Characters project provides AI character management and interaction capabilities for Discord channels. It enables adding AI characters with distinct personalities to Discord channels, where they can respond to mentions and engage in conversations.

**Standards Compliance**: This project fully complies with the Pydantic AI Agent Implementation Standard.

### Architecture
- **Agent**: Pydantic AI agent with Discord character management tools
- **Dependencies**: `DiscordCharactersDeps` with MongoDB store and Persona service integration
- **API**: REST endpoints at `/api/v1/discord-characters/*`
- **MCP Tools**: 5 tools for character operations

### Configuration
- **MongoDB URI**: `MONGODB_URI` (from global settings)
- **MongoDB Database**: `MONGODB_DATABASE` (from global settings)
- **Collections**: `discord_channel_states`, `discord_conversation_history`

### API Endpoints
- `POST /api/v1/discord-characters/add` - Add character to channel
- `POST /api/v1/discord-characters/remove` - Remove character from channel
- `POST /api/v1/discord-characters/list` - List active characters in channel
- `POST /api/v1/discord-characters/clear-history` - Clear conversation history
- `POST /api/v1/discord-characters/engage` - Engage character in conversation

### MCP Tools
- `add_discord_character` - Add character to Discord channel
- `remove_discord_character` - Remove character from Discord channel
- `list_discord_characters` - List active characters in channel
- `clear_discord_character_history` - Clear conversation history
- `engage_discord_character` - Engage character in conversation

### Integration Points
- **Persona Service**: Uses `PersonaDeps` for character definitions and voice instructions
- **Conversation Orchestrator**: Uses `ConversationOrchestrator` for multi-agent responses
- **MongoDB**: Stores channel state and conversation history
- **Discord Bot**: `03-apps/discord-bot` (with `ENABLED_CAPABILITIES=character`) calls these APIs

### Service Layer
The project includes a service layer (`server/services/discord_characters/`) with:
- **Models**: `ChannelCharacter`, `DiscordMessage`, `ConversationHistory`, `ChannelState`
- **Store**: `MongoCharacterStore` for MongoDB persistence
- **Manager**: `CharacterManager` for business logic

## Auth Project

### Overview
The auth project provides centralized header-based authentication using Cloudflare Access (Zero Trust) with Just-In-Time (JIT) user provisioning and strict data isolation.

**Key Features:**
- JWT validation from `Cf-Access-Jwt-Assertion` header
- Automatic user provisioning in Supabase, Neo4j, and MinIO
- Data isolation enforcement across all data stores
- Admin override for privileged access

**Configuration:**
- `CLOUDFLARE_AUTH_DOMAIN`: Cloudflare Access team domain (e.g., `https://datacrew-space.cloudflareaccess.com`)
- `CLOUDFLARE_AUD_TAG`: Application audience tag (64-character hex string, unique per Access application)
- `SUPABASE_DB_URL`: PostgreSQL connection string
- `MINIO_ENDPOINT`, `MINIO_ACCESS_KEY`, `MINIO_SECRET_KEY`: MinIO credentials

**Getting the AUD Tag:**
```bash
# Use the script to retrieve AUD tag
python3 00-infrastructure/scripts/get-lambda-api-aud-tag.py
```

**Usage:**
```python
from server.projects.auth.dependencies import get_current_user
from server.projects.auth.models import User

@router.get("/protected")
async def endpoint(user: User = Depends(get_current_user)):
    return {"email": user.email}
```

**Endpoints:**
- `GET /api/me` - Get current user profile
- `GET /api/me/data` - Get data summary across all services
- `GET /api/me/data/rag` - Get RAG data summary (MongoDB + Supabase)
- `GET /api/me/data/immich` - Get Immich data summary (placeholder)
- `GET /api/me/data/loras` - Get LoRA models summary

**Services:**
- `JWTService`: Validates Cloudflare Access JWTs, checks audience and issuer
- `SupabaseService`: User provisioning and management in PostgreSQL
- `Neo4jService`: User node provisioning in Neo4j graph
- `MinIOService`: User folder provisioning in MinIO object storage
- `AuthService`: Helper functions (admin checks)
- `DatabaseValidationService`: Validates core database tables and applies migrations on startup

**Database Schema Management:**
- **Automatic Migrations**: Migrations are automatically applied during Lambda server startup
- **Core Table Validation**: `profiles` table is validated and auto-created if missing
- **Startup Integration**: Validation runs in FastAPI lifespan before accepting requests
- **Location**: `src/services/auth/services/database_validation_service.py`

See [src/services/auth/README.md](src/services/auth/README.md) for detailed documentation.

## Data Viewing APIs

### Overview
The data viewing APIs provide JSON endpoints for authenticated users to view their data across all storage layers with proper data isolation.

**Location**: `server/api/data_view.py`

**Key Features:**
- All endpoints require authentication via `get_current_user`
- Data isolation: Regular users see only their data
- Admin override: Admin users see all data
- JSON responses (no HTML)
- Pagination support where applicable

**Endpoints:**
- `GET /api/v1/data/storage` - View MinIO/blob storage files
  - Query params: `prefix` (optional, e.g., `prefix=loras/`)
  - Returns: File metadata (key, filename, size, last_modified, etag)
- `GET /api/v1/data/supabase` - View Supabase table data
  - Query params: `table` (default: "items"), `page`, `per_page`
  - Returns: Paginated items from specified table
- `GET /api/v1/data/neo4j` - View Neo4j nodes and relationships
  - Query params: `node_type` (optional, e.g., `node_type=Document`)
  - Returns: Nodes and relationships (user-anchored for regular users)
- `GET /api/v1/data/mongodb` - View MongoDB collection data
  - Query params: `collection` (default: "documents"), `page`, `per_page`
  - Returns: Paginated documents (filtered by user_id/user_email)

**Usage Example:**
```bash
# List all files in blob storage
curl -H "Cf-Access-Jwt-Assertion: YOUR_JWT" \
     https://api.datacrew.space/api/v1/data/storage

# List files with prefix filter
curl -H "Cf-Access-Jwt-Assertion: YOUR_JWT" \
     "https://api.datacrew.space/api/v1/data/storage?prefix=loras/"

# View Supabase items
curl -H "Cf-Access-Jwt-Assertion: YOUR_JWT" \
     "https://api.datacrew.space/api/v1/data/supabase?table=items&page=1&per_page=50"
```

**Data Isolation:**
- **Regular users**: See only their own data (filtered by user_id, user_email, or owner_email)
- **Admin users**: See all data across all users (bypasses filtering)
- Admin status checked via `AuthService.is_admin(user.email)`

**Response Models:**
- `StorageDataResponse`: Files list with metadata
- `SupabaseDataResponse`: Paginated table items
- `Neo4jDataResponse`: Nodes and relationships
- `MongoDBDataResponse`: Paginated documents

**Implementation Details:**
- Location: `server/api/data_view.py`
- All endpoints use `get_current_user` dependency for authentication
- Services used: `AuthService`, `SupabaseService`, `Neo4jService`, `MinIOService`, `AsyncMongoClient`
- Admin override implemented in each endpoint via `AuthService.is_admin()`
- For MinIO: Admin users can view all files from all user folders
- For Supabase: Admin users bypass `owner_email` filtering
- For Neo4j: Admin users skip user anchoring in Cypher queries
- For MongoDB: Admin users bypass `user_id`/`user_email` filtering

## Best Practices

1. **Always cleanup resources**: Use `try/finally` blocks
2. **Use Pydantic models**: For all request/response data
3. **Structured logging**: Use `extra` dict for context
4. **Async all the way**: All I/O operations must be async
5. **Type hints**: All functions must have type annotations
6. **Error handling**: Catch specific exceptions, log with context
7. **Configuration**: Use environment variables, not hardcoded values
8. **Documentation**: Docstrings for all public functions

## Search Hints

```bash
# Find API endpoints
rg -n "@router\." server/api/

# Find authenticated endpoints (using get_current_user)
rg -n "get_current_user" server/api/

# Find data viewing endpoints
rg -n "data_view|data/storage|data/supabase|data/neo4j|data/mongodb" server/api/

# Find MCP tools
rg -n "def.*tool" src/mcp_server/

# Find configuration
rg -n "class.*Config" src/

# Find dependencies
rg -n "class.*Dependencies" src/capabilities/ src/workflows/

# Find auth services
rg -n "class.*Service" src/services/auth/services/

# Find response models
rg -n "class.*Response" server/api/
```

## Stack Orchestration

```bash
# Start lambda (with dependencies)
python start_services.py --stack lambda

# Stop lambda
python start_services.py --action stop --stack lambda

# Start all stacks
python start_services.py --stack all

# Check status
docker compose -p localai-lambda ps

# View logs
docker compose -p localai-lambda logs -f lambda-server

# Rebuild with package persistence (packages won't be lost)
docker compose -p localai-lambda build --no-cache
docker compose -p localai-lambda up -d
```

## Package Management

### Persistent Package Storage

The lambda container uses a Docker volume to persist Python packages:

- **Volume**: `lambda-packages:/opt/venv`
- **Entrypoint**: `docker-entrypoint.sh` checks if venv exists, creates and installs on first run
- **Benefits**:
  - No package reinstallation on container restarts
  - Faster startup times
  - Packages survive image rebuilds

### Manual Package Installation

If you need to install additional packages at runtime:

```bash
# Enter container
docker exec -it lambda-server bash

# Activate venv and install
source /opt/venv/bin/activate
pip install package-name

# Packages will persist in volume
```

### Rebuilding with Fresh Packages

To start fresh (removes all packages):

```bash
# Remove volume
docker compose -p localai-lambda down -v

# Rebuild and start (packages will be reinstalled)
docker compose -p localai-lambda up -d --build
```
