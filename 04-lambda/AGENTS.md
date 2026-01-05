# Lambda Stack - Agent Rules

## Overview

FastAPI multi-project server providing REST APIs and MCP (Model Context Protocol) endpoints. Designed for clean separation of concerns and easy addition of new projects.

## Design Strategy

### Core Philosophy

**Multi-Project Lambda Server**: A unified FastAPI application that hosts multiple independent projects (agents, pipelines, integrations) while maintaining clean boundaries and shared infrastructure.

**Key Principles:**
1. **Project Isolation**: Each project is self-contained in `server/projects/{name}/`
2. **Dual Interface**: Every project exposes both REST API and MCP endpoints
3. **Shared Infrastructure**: Common utilities (logging, config, exceptions) in `server/core/`
4. **Type Safety**: Pydantic models for all data structures
5. **Async First**: All I/O operations are async
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
server/projects/{project_name}/
├── __init__.py
├── config.py              # Project-specific configuration
├── dependencies.py        # ProjectDeps class (follows standard)
├── agent.py              # Agent definition (follows standard)
├── tools.py              # Agent tools (if complex)
├── prompts.py            # System prompts
└── {domain}/             # Domain-specific modules
    ├── pipeline.py       # Data processing pipelines
    ├── validators.py     # Validation logic
    └── utils.py          # Utilities
```

### REST API Design

**Endpoint Pattern:**
```python
from fastapi import APIRouter, HTTPException
from server.models.{project} import RequestModel, ResponseModel
from server.projects.{project}.dependencies import ProjectDeps

router = APIRouter()

@router.post("/endpoint", response_model=ResponseModel)
async def endpoint(request: RequestModel):
    """Endpoint description."""
    deps = ProjectDeps.from_settings()
    await deps.initialize()  # If needed
    
    try:
        # Business logic
        result = await process(deps, request)
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

### MCP Server Design

**Tool Registration Pattern:**
```python
# In server/mcp/server.py
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

2. **Project Config** (`server/projects/{project}/config.py`):
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
- **Project-specific**: `server/projects/{project}/config.py` (derives from global)
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
- Tools registered in `server/mcp/server.py`
- Calls REST endpoints internally (no code duplication)
- Returns formatted text responses

## Adding New Projects

1. **Create project folder**: `server/projects/your_project/`
   - `config.py` - Project configuration
   - `dependencies.py` - External connections
   - `tools.py` - Core functionality
   
2. **Create API router**: `server/api/your_project.py`
   - Define endpoints
   - Use Pydantic models from `server/models/`
   
3. **Register in main**: `server/main.py`
   ```python
   from server.api import your_project
   app.include_router(your_project.router, prefix="/api/v1/your_project")
   ```
   
4. **Add MCP tools**: `server/mcp/server.py`
   - Add tool definitions to `list_tools()`
   - Add tool execution to `call_tool()`

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
- `EMBEDDING_MODEL` - Embedding model (default: nomic-embed-text)
- `LOG_LEVEL` - Logging level (default: info)

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

**Standards Compliance**: This project fully complies with the Pydantic AI Agent Implementation Standard. See [STANDARDS_COMPLIANCE.md](server/projects/n8n_workflow/docs/STANDARDS_COMPLIANCE.md) for details.

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

See [ENHANCEMENT_RESEARCH.md](server/projects/n8n_workflow/docs/ENHANCEMENT_RESEARCH.md) for detailed research and implementation strategy.

### Integration Points
- **N8n Service**: `http://n8n:5678` (from 03-apps stack)
- **Network**: `ai-network` (shared Docker network)

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

# Find MCP tools
rg -n "def.*tool" server/mcp/

# Find configuration
rg -n "class.*Config" server/

# Find dependencies
rg -n "class.*Dependencies" server/projects/
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

