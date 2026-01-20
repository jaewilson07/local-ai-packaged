# Lambda Server Infrastructure

**Location**: `04-lambda/server/`  
**Type**: FastAPI Multi-Project Server  
**Status**: ⚠️ **Partially Operational** - Server structure complete, but startup blocked by configuration issues

---

## Overview

The Lambda server is a unified FastAPI application that serves multiple AI/ML projects through both REST API endpoints and MCP (Model Context Protocol) tools. It acts as the central orchestration layer for all Lambda project services.

### Architecture

```
┌─────────────────────────────────────────────────────────┐
│              Lambda FastAPI Server                      │
│  ┌──────────────────────────────────────────────────┐  │
│  │  FastAPI Application (main.py)                   │  │
│  │  - REST API Endpoints                             │  │
│  │  - MCP Tools (via FastMCP)                        │  │
│  │  - CORS Middleware                                │  │
│  └──────────────────────────────────────────────────┘  │
│                          │                              │
│  ┌──────────────────────┼──────────────────────────┐ │
│  │                      │                            │ │
│  │  ┌───────────────────▼──────────┐                │ │
│  │  │  Project Routers              │                │ │
│  │  │  - MongoDB RAG                │                │ │
│  │  │  - Graphiti RAG                │                │ │
│  │  │  - Crawl4AI RAG                 │                │ │
│  │  │  - Calendar                    │                │ │
│  │  │  - Conversation                │                │ │
│  │  │  - Persona                     │                │ │
│  │  │  - N8N Workflow                │                │ │
│  │  │  - Open WebUI                  │                │ │
│  │  │  - Knowledge                   │                │ │
│  │  │  - Blob Storage                │                │ │
│  │  │  - ComfyUI Workflow            │                │ │
│  │  │  - Discord Characters          │                │ │
│  │  └────────────────────────────────┘                │ │
│  │                                                     │ │
│  │  ┌─────────────────────────────────────────────┐ │ │
│  │  │  Dependency Injection Layer                   │ │ │
│  │  │  - AgentDependencies (MongoDB RAG)            │ │ │
│  │  │  - CalendarDeps                                │ │ │
│  │  │  - PersonaDeps                                 │ │ │
│  │  │  - N8nWorkflowDeps                             │ │ │
│  │  │  - OpenWebUIExportDeps                         │ │ │
│  │  │  - GraphitiRAGDeps                             │ │ │
│  │  └─────────────────────────────────────────────┘ │ │
│  └─────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────┘
                          │
                          ▼
        ┌─────────────────────────────────┐
        │  External Services              │
        │  - MongoDB (01-data)            │
        │  - Neo4j (01-data)              │
        │  - Ollama (02-compute)          │
        │  - N8N (03-apps)                │
        │  - Open WebUI (03-apps)         │
        └─────────────────────────────────┘
```

---

## Current Problems

### Problem 1: Pydantic Type Validation Error ⚠️ **BLOCKING**

**Location**: `04-lambda/src/capabilities/retrieval/mongo_rag/dependencies.py:19-23`

**Issue**: `AgentDependencies` is a Pydantic `BaseModel` that includes `AsyncMongoClient` as an optional field. Pydantic cannot generate a schema for `AsyncMongoClient` because it's not a Pydantic-compatible type.

**Error Message**:
```
pydantic.errors.PydanticSchemaGenerationError: Unable to generate pydantic-core schema for <class 'pymongo.asynchronous.mongo_client.AsyncMongoClient'>. Set `arbitrary_types_allowed=True` in the model_config to ignore this error or implement `__get_pydantic_core_schema__` on your type to fully support it.
```

**Impact**:
- **BLOCKS**: Server cannot import `server.main:app` during startup
- **BLOCKS**: All REST API endpoints that use `AgentDependencies` cannot be registered
- **BLOCKS**: MCP tools that depend on MongoDB RAG cannot be initialized
- **AFFECTS**: MongoDB RAG, Crawl4AI RAG, Open WebUI Export, and other services using `AgentDependencies`

**Root Cause**:
```python
class AgentDependencies(BaseModel):
    mongo_client: Optional[AsyncMongoClient] = None  # ❌ Pydantic can't validate this
```

**Current Workaround**: None - server cannot start

**Proposed Solutions**:

1. **Option A: Use `arbitrary_types_allowed=True`** (Quick Fix)
   ```python
   class AgentDependencies(BaseModel):
       model_config = ConfigDict(arbitrary_types_allowed=True)
       mongo_client: Optional[AsyncMongoClient] = None
   ```
   - ✅ Simple, minimal code change
   - ⚠️ Bypasses Pydantic validation for these fields
   - ⚠️ May hide type errors

2. **Option B: Use `Field` with `arbitrary_types_allowed`** (Recommended)
   ```python
   from pydantic import Field, ConfigDict

   class AgentDependencies(BaseModel):
       model_config = ConfigDict(arbitrary_types_allowed=True)
       mongo_client: Optional[AsyncMongoClient] = Field(default=None, exclude=True)
   ```
   - ✅ Explicitly excludes from serialization
   - ✅ Maintains type hints for IDE support
   - ✅ Follows Pydantic v2 best practices

3. **Option C: Implement Custom Pydantic Schema** (Most Robust)
   ```python
   from pydantic_core import core_schema

   @classmethod
   def __get_pydantic_core_schema__(cls, source_type, handler):
       return core_schema.any_schema()
   ```
   - ✅ Full control over validation
   - ❌ More complex implementation
   - ❌ Requires custom wrapper class

**Recommended**: Option B - balances simplicity with correctness

---

### Problem 2: Required Configuration Fields ⚠️ **BLOCKING**

**Location**: `04-lambda/server/config.py:15`

**Issue**: `mongodb_uri` is a required field with no default value. When the server imports `settings` at module level, it fails if the environment variable is not set.

**Error Message**:
```
pydantic_core._pydantic_core.ValidationError: 1 validation error for Settings
mongodb_uri
  Field required [type=missing, input_value={}, input_type=dict]
```

**Impact**:
- **BLOCKS**: Server cannot import configuration during module load
- **BLOCKS**: All imports of `server.config` fail
- **AFFECTS**: All services that depend on configuration

**Root Cause**:
```python
class Settings(BaseSettings):
    mongodb_uri: str  # ❌ No default, fails if env var not set
```

**Current Workaround**: Set environment variables before importing (done in tests)

**Proposed Solutions**:

1. **Option A: Provide Default Values** (Quick Fix)
   ```python
   mongodb_uri: str = "mongodb://localhost:27017"
   ```
   - ✅ Allows server to start without env vars
   - ⚠️ May connect to wrong database if env var missing
   - ⚠️ Silent failure if connection fails

2. **Option B: Make Optional with Validation** (Recommended)
   ```python
   mongodb_uri: Optional[str] = None

   @field_validator('mongodb_uri')
   @classmethod
   def validate_mongodb_uri(cls, v):
       if v is None:
           raise ValueError("MONGODB_URI environment variable is required")
       return v
   ```
   - ✅ Clear error message if missing
   - ✅ Allows conditional validation
   - ⚠️ More complex

3. **Option C: Lazy Configuration Loading** (Most Flexible)
   ```python
   # Don't create settings at module level
   # Load on first access via property
   ```
   - ✅ No import-time failures
   - ✅ Can validate on first use
   - ❌ Requires refactoring all config access

**Recommended**: Option A for development, Option B for production

---

### Problem 3: Syntax Errors ✅ **FIXED**

**Location**: `04-lambda/server/api/mongo_rag.py:509-605`

**Issue**: Multiple endpoint functions had parameters with default values after parameters without defaults, which violates Python syntax rules.

**Status**: ✅ **RESOLVED** - Fixed by reordering parameters (moved `deps` before parameters with defaults)

**Fixed Endpoints**:
- `record_message_endpoint` (line 509)
- `get_context_window_endpoint` (line 524)
- `store_fact_endpoint` (line 552)
- `search_facts_endpoint` (line 568)
- `store_web_content_endpoint` (line 595)

---

## Infrastructure Dependencies

### Internal Dependencies

1. **FastAPI** - Web framework
2. **FastMCP** - MCP server integration
3. **Pydantic** - Data validation and settings
4. **Pydantic AI** - Agent framework
5. **PyMongo** - MongoDB async client
6. **OpenAI SDK** - LLM client (compatible with Ollama)

### External Service Dependencies

1. **MongoDB** (01-data stack)
   - Required for: MongoDB RAG, Calendar, Persona, Open WebUI Export
   - Connection: `mongodb_uri` from config
   - Database: `mongodb_database` from config

2. **Neo4j** (01-data stack)
   - Required for: Graphiti RAG, Knowledge Graph features
   - Connection: `neo4j_uri`, `neo4j_user`, `neo4j_password` from config
   - Optional: Only needed if `use_graphiti=true` or `use_knowledge_graph=true`

3. **Ollama** (02-compute stack)
   - Required for: LLM inference, embedding generation
   - Connection: `llm_base_url`, `embedding_base_url` from config
   - Models: `llm_model`, `embedding_model` from config

4. **N8N** (03-apps stack)
   - Required for: N8N Workflow service
   - Connection: `n8n_api_url`, `n8n_api_key` from config

5. **Open WebUI** (03-apps stack)
   - Required for: Open WebUI Export service
   - Connection: `openwebui_api_url`, `openwebui_api_key` from config

---

## Configuration

### Environment Variables

**Required**:
- `MONGODB_URI` - MongoDB connection string

**Optional** (with defaults):
- `MONGODB_DATABASE` - Database name (default: `rag_db`)
- `LLM_BASE_URL` - LLM API URL (default: `http://ollama:11434/v1`)
- `LLM_MODEL` - LLM model name (default: `llama3.2`)
- `EMBEDDING_BASE_URL` - Embedding API URL (default: `http://ollama:11434/v1`)
- `EMBEDDING_MODEL` - Embedding model name (default: `qwen3-embedding:4b`)
- `NEO4J_URI` - Neo4j connection URI (default: `bolt://neo4j:7687`)
- `NEO4J_USER` - Neo4j username (default: `neo4j`)
- `NEO4J_PASSWORD` - Neo4j password (default: `password`)
- `N8N_API_URL` - N8N API URL (default: `http://n8n:5678/api/v1`)
- `OPENWEBUI_API_URL` - Open WebUI API URL

### Configuration Loading

Configuration is loaded at module import time:
```python
# server/config.py
settings = Settings()  # ❌ Fails if required fields missing
```

This causes import-time failures if environment variables are not set.

---

## API Structure

### REST Endpoints

- `/health` - Health check endpoint
- `/api/v1/rag/*` - MongoDB RAG endpoints
- `/api/v1/crawl/*` - Crawl4AI RAG endpoints
- `/api/v1/n8n/*` - N8N Workflow endpoints
- `/api/v1/openwebui/*` - Open WebUI endpoints
- `/api/v1/storage/*` - Blob storage endpoints
- `/api/v1/comfyui/*` - ComfyUI workflow endpoints

### MCP Tools

Exposed via FastMCP at `/mcp/`:
- MongoDB RAG tools (search, ingestion, memory)
- Graphiti RAG tools (knowledge graph search, repository parsing)
- Crawl4AI RAG tools (single page crawl, deep crawl)
- Calendar tools (create, update, delete, list events)
- Persona tools (voice instructions, interaction recording)
- N8N Workflow tools (create, list, execute workflows)
- Open WebUI tools (export conversation, get conversations)

---

## Startup Sequence

1. **Module Import** (`server/main.py`)
   - Import `server.config.settings` → **FAILS** if env vars not set
   - Import routers → **FAILS** if `AgentDependencies` has Pydantic error
   - Create FastAPI app
   - Register middleware (CORS)
   - Register routers

2. **Lifespan Startup**
   - Generate MCP server modules
   - Initialize MCP server lifespan
   - Log startup

3. **Request Handling**
   - Dependency injection via FastAPI `Depends()`
   - Create `AgentDependencies` instances → **FAILS** if Pydantic error
   - Execute endpoint handlers

---

## Testing Status

### Unit Tests

✅ **All Passing** (13/13):
- Calendar: 5 tests
- Conversation: 1 test
- Persona: 2 tests
- N8N Workflow: 3 tests
- Open WebUI: 2 tests

### Server Startup Test

⚠️ **Blocked**:
- Test exists: `04-lambda/tests/test_server/test_server_startup.py`
- Cannot run: Server import fails due to configuration/Pydantic issues
- Workaround: Tests set environment variables before import

---

## Resolution Plan

### Priority 1: Fix Pydantic Type Validation (BLOCKING)

**Action**: Update `AgentDependencies` to allow arbitrary types

**File**: `04-lambda/src/capabilities/retrieval/mongo_rag/dependencies.py`

**Change**:
```python
from pydantic import BaseModel, ConfigDict

class AgentDependencies(BaseModel):
    model_config = ConfigDict(arbitrary_types_allowed=True)

    mongo_client: Optional[AsyncMongoClient] = None
    # ... rest of fields
```

**Impact**: Allows server to import and start

**Estimated Time**: 5 minutes

---

### Priority 2: Fix Required Configuration Fields (BLOCKING)

**Action**: Provide default values or make fields optional with validation

**File**: `04-lambda/server/config.py`

**Change**:
```python
mongodb_uri: str = Field(default="mongodb://localhost:27017", env="MONGODB_URI")
```

**Impact**: Allows server to import configuration without env vars (for development)

**Estimated Time**: 5 minutes

---

### Priority 3: Validate Server Startup

**Action**: Run server startup test after fixes

**Command**:
```bash
cd 04-lambda
MONGODB_URI="mongodb://localhost:27017/test" \
LLM_BASE_URL="http://localhost:11434" \
EMBEDDING_BASE_URL="http://localhost:11434" \
LLM_MODEL="llama3.2" \
EMBEDDING_MODEL="qwen3-embedding:4b" \
python -c "from server.main import app; print('✅ Server imports successfully')"
```

**Expected**: Server imports without errors

**Estimated Time**: 2 minutes

---

## Related Documentation

- **Service Capabilities**: `.cursor/PRDS/capabilities/service_capabilities.md`
- **MongoDB RAG**: `04-lambda/src/capabilities/retrieval/mongo_rag/AGENTS.md`
- **Graphiti RAG**: `04-lambda/src/capabilities/retrieval/graphiti_rag/AGENTS.md`
- **Crawl4AI RAG**: `04-lambda/src/workflows/ingestion/crawl4ai_rag/AGENTS.md`

---

**Last Updated**: 2026-01-10  
**Status**: ⚠️ **Blocked** - Server cannot start due to Pydantic configuration issues  
**Next Steps**: Fix Pydantic type validation and required configuration fields
