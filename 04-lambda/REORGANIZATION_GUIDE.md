# Project Reorganization Guide - Layered Architecture

## Overview

This project has been reorganized to follow a **Layered Service Orchestration** architecture, which provides clear separation of concerns and makes the codebase more maintainable and scalable.

## What Changed

### Directory Structure

**Before:**
```
/04-lambda/
├── docker-compose.yml
├── Dockerfile
├── docker-entrypoint.sh
├── pyproject.toml
└── src/
    ├── server/
    │   ├── main.py
    │   ├── config.py
    │   ├── core/
    │   ├── api/
    │   └── mcp/
    ├── capabilities/
    ├── workflows/
    └── services/
```

**After:**
```
/04-lambda/
├── infra/                    # Infrastructure files
│   ├── docker-compose.yml
│   ├── Dockerfile
│   └── docker-entrypoint.sh
├── config/                   # Configuration templates
│   ├── settings.yaml.example
│   └── workflows/
├── app/                      # Application code
│   ├── core/                 # Foundation layer
│   ├── services/             # External integrations (dumb pipes)
│   ├── capabilities/         # Business logic (source of truth)
│   ├── workflows/            # Orchestration
│   └── interfaces/           # Entry points
│       ├── http/             # REST API (main.py, routers)
│       └── mcp/              # MCP protocol server
├── tests/
└── pyproject.toml
```

## Architecture Layers

### 1. Infrastructure Layer (`/infra`)
- **Purpose**: Infrastructure as code
- **Contents**: Docker configuration, build files, deployment scripts
- **Rules**: Only infrastructure concerns, no application logic

### 2. Configuration Layer (`/config`)
- **Purpose**: Non-secret configuration templates
- **Contents**: Settings templates, workflow templates
- **Rules**: No secrets, only example configurations

### 3. Application Layer (`/app`)

#### 3a. Interfaces Layer (`/app/interfaces`)
- **Purpose**: Entry points - thin triggers with NO logic
- **Contents**: REST API (main.py, routers), MCP server
- **Rules**: 
  - Call capabilities/workflows
  - Parse/validate input
  - Format output
  - NO business logic

#### 3b. Workflows Layer (`/app/workflows`)
- **Purpose**: Orchestration of capabilities for complex operations
- **Contents**: Multi-step workflows that coordinate capabilities
- **Rules**:
  - Call capabilities and services
  - Orchestrate complex operations
  - Handle workflow state
  - NO atomic business logic (delegate to capabilities)

#### 3c. Capabilities Layer (`/app/capabilities`)
- **Purpose**: Business logic - SOURCE OF TRUTH
- **Contents**: Atomic operations, agents, tools
- **Rules**:
  - Implement core business logic
  - Call services for I/O
  - Self-contained and reusable
  - Used by both interfaces and workflows

#### 3d. Services Layer (`/app/services`)
- **Purpose**: External integrations - DUMB PIPES
- **Contents**: Database clients, API clients, storage clients
- **Rules**:
  - ONLY I/O operations
  - NO business logic
  - Simple wrappers around external services

#### 3e. Core Layer (`/app/core`)
- **Purpose**: Foundation - shared utilities
- **Contents**: Config, exceptions, logging, protocols, base classes
- **Rules**:
  - No dependencies on other layers
  - Reusable utilities
  - Foundation for everything else

## Import Changes

All imports have been updated to use the `app.*` namespace:

**Before:**
```python
from server.config import settings
from server.core.logging import setup_logging
from capabilities.retrieval.mongo_rag.agent import rag_agent
from services.auth.dependencies import get_current_user
```

**After:**
```python
from app.core.config import settings
from app.core.logging import setup_logging
from app.capabilities.retrieval.mongo_rag.agent import rag_agent
from app.services.auth.dependencies import get_current_user
```

## Running the Application

### Local Development

```bash
# From project root /workspace/
cd 04-lambda

# Build container (from infra directory)
cd infra
docker compose build

# Start services
docker compose up -d

# View logs
docker compose logs -f lambda-server

# Stop services
docker compose down
```

### Using start_services.py (Recommended)

```bash
# From workspace root
python start_services.py --stack lambda

# Stop
python start_services.py --action stop --stack lambda
```

## Key Principles

### 1. Capabilities Are the Source of Truth
- All business logic lives in `/app/capabilities`
- Both REST API and MCP endpoints call the same capabilities
- If you change logic, change it in capabilities

### 2. Interfaces Are Thin Triggers
- `/app/interfaces/http/` and `/app/interfaces/mcp/` contain NO business logic
- They only:
  - Parse input
  - Call capabilities/workflows
  - Format output

### 3. Services Are Dumb Pipes
- `/app/services/` contains NO business logic
- They only:
  - Connect to external systems
  - Execute I/O operations
  - Return raw data

### 4. Workflows Orchestrate
- `/app/workflows/` coordinate multiple capabilities
- They implement complex multi-step operations
- They delegate atomic operations to capabilities

## Migration Checklist for New Features

When adding new features, follow this pattern:

1. **Business Logic**: Implement in `/app/capabilities/{category}/{name}/`
2. **I/O Operations**: Create service client in `/app/services/{service}/`
3. **Orchestration**: If multi-step, create workflow in `/app/workflows/{category}/{name}/`
4. **REST API**: Add router in capability/workflow, register in `main.py`
5. **MCP Tools**: Define tools in MCP server, call capability functions
6. **Configuration**: Add settings to `app/core/config.py` or capability config
7. **Documentation**: Update AGENTS.md and capability/workflow README

## Example: Adding a New Capability

```bash
# 1. Create capability structure
mkdir -p app/capabilities/analysis/sentiment_analysis

# 2. Create files
touch app/capabilities/analysis/sentiment_analysis/{__init__.py,config.py,dependencies.py,agent.py,tools.py,router.py}

# 3. Implement business logic in agent.py and tools.py
# 4. Create service client if needed in app/services/
# 5. Create REST router in router.py
# 6. Register router in app/interfaces/http/main.py
# 7. Register MCP tools in app/interfaces/mcp/server.py
```

## Testing

**Important**: Testing requires a running environment with all dependencies:

```bash
# Run tests (from 04-lambda directory)
cd /workspace/04-lambda
pytest tests/

# Run specific test
pytest tests/test_mongo_rag/test_agent.py

# Run with coverage
pytest --cov=app tests/
```

## Troubleshooting

### Import Errors

If you see import errors like `ModuleNotFoundError: No module named 'server'`:
- Check that imports use `app.*` namespace
- Verify PYTHONPATH includes `/app`
- Check that `pyproject.toml` packages includes `app`

### Docker Build Failures

If Docker build fails:
- Verify `infra/Dockerfile` paths are correct
- Check `infra/docker-compose.yml` context is `..` (parent directory)
- Ensure volumes mount `../app:/app/app`

### Missing Modules

If you see errors about missing modules in `app/core/`:
- We created `app/core/api_models.py` and `app/core/exceptions.py`
- You may need to create additional shared modules as needed

## Benefits of This Structure

1. **Clear Separation**: Each layer has a single responsibility
2. **Testability**: Capabilities can be tested in isolation
3. **Reusability**: Capabilities are used by both HTTP and MCP interfaces
4. **Maintainability**: Easy to find and modify code
5. **Scalability**: Easy to add new capabilities without affecting existing code
6. **Documentation**: Structure is self-documenting

## Next Steps

1. **Test the Application**: Start the container and verify all endpoints work
2. **Fix Any Import Issues**: Some dynamic imports may need adjustment
3. **Add Missing Core Modules**: Create any missing shared utilities
4. **Update Tests**: Verify all tests pass with new structure
5. **Document Edge Cases**: Note any unique patterns or exceptions

## Questions?

Refer to:
- `AGENTS.md` - Detailed architecture documentation
- `config/settings.yaml.example` - Configuration template
- `/app/{layer}/` - Example implementations in each layer
