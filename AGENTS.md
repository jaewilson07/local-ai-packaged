# AGENTS.md - Universal Constitution

> **Multi-Editor Support**: These instructions apply to both GitHub Copilot and Cursor AI editors. Both read AGENTS.md files as the universal source of truth for AI-assisted development.

> **Nearest-wins hierarchy**: Sub-folder AGENTS.md files override this root document. Always check for component-specific rules first.

## Agent Behavioral Protocols

### Thinking Process
1. **Explore Context First**: Before making changes, search the codebase for existing patterns using `rg` or semantic search.
2. **Verify DRY**: Check if similar functionality already exists. Reuse, don't recreate.
3. **Plan Before Execute**: For multi-file changes, outline the approach before editing.
4. **Drift Check**: If this document contradicts active code, **trust the codebase** and flag the discrepancy.

### Safety Constraints
- **Never run destructive commands** without explicit user confirmation:
  - `rm -rf` (especially on root or system directories)
  - `DROP TABLE` or database schema deletions
  - `docker system prune -a` or volume deletions
  - Commits with secrets or credentials
- **No blind retries**: If a fix fails, stop, analyze error logs, propose a new strategy.
- **Environment awareness**: Distinguish between `.env`, `.env.global`, and Infisical-managed secrets.
- **Authentication**: External Lambda API requests require Cloudflare Access JWT. Internal network requests bypass authentication (network isolation).
- **Data Isolation**: Always enforce user-scoped filtering unless user is admin. Never expose other users' data.

### Token Economy & Output
- Use `sed` or patch-style replacements for small edits (prefer `search_replace` tool).
- Do not output unchanged code blocks. Use `// ... existing code ...` for context.
- Do not repeat the user's prompt verbatim in responses.
- When referencing files, use code references: `startLine:endLine:filepath`

## File Organization & Root Directory Standards

**Do not create new root-level files or directories.** Use designated locations:

- **`.github/`** - GitHub-specific configs (workflows, Copilot instructions)
- **`.cursor/`** - Cursor-specific configs (rules, commands, plans)
- **`.venv/`** - Python virtual environment (always use `uv`)
- **`docs/`** - Project documentation
- **`sample/`** - User-facing sample code and examples
- **`scripts/`** - Maintenance scripts (agents: do not modify these)
- **`setup/`** - Installation scripts (CLIs, pre-commit hooks, etc.)
- **`test/`** - Test files to validate generated code
- **`temp/`** - Temporary files during code generation (gitignored)
- **Stack directories** (`00-infrastructure/`, `01-data/`, `02-compute/`, `03-apps/`, `04-lambda/`) - Service stacks

## Universal Tech Stack

### Repository Type
- **Monorepo** with stack-based Docker Compose architecture
- **Orchestration**: Python 3.10+ (`start_services.py`)
- **Containerization**: Docker Compose with external network (`ai-network`)
- **Package Management**:
  - Python: `uv` (pyproject.toml)
  - Node.js (Supabase): `pnpm` (monorepo with Turbo)

### Core Commands
```bash
# Start all services
python start_services.py --profile <cpu|gpu-nvidia|gpu-amd|none> [--environment <private|public>]

# Start specific stack
python start_services.py --stack <infrastructure|infisical|data|compute|apps|lambda>

# Stop all services
python start_services.py --action stop

# Stop specific stack
python start_services.py --action stop --stack <infrastructure|infisical|data|compute|apps|lambda>

# Check service status (each stack has its own project name)
docker compose -p localai-infra ps      # Infrastructure
docker compose -p localai-infisical ps # Infisical
docker compose -p localai-data ps      # Data
docker compose -p localai-compute ps   # Compute
docker compose -p localai-apps ps      # Apps
docker compose -p localai-lambda ps    # Lambda
```

### Code Style Standards
- **Python**: Black (line-length: 100), Ruff (target: py310)
- **YAML**: 2-space indentation, consistent service naming
- **Shell**: POSIX-compliant, use `#!/bin/bash` for bash-specific features
- **Docker Compose**: Use anchors (`x-service: &service-name`) for shared configs

### Python Import Guidelines
- **Never use `TYPE_CHECKING`**: Do not use `from typing import TYPE_CHECKING` with conditional imports. This pattern obscures dependencies and makes debugging harder.
- **Fix circular imports properly**: If you encounter a circular import:
  1. **Restructure modules**: Move shared code to a separate module that both can import
  2. **Use lazy imports**: Import inside functions/methods when the import is only needed at runtime
  3. **Simplify `__init__.py`**: Only export leaf modules that don't have circular dependencies
  4. **Import from submodules directly**: Instead of `from package import X`, use `from package.module import X`
- **Example - Fixing circular imports in `__init__.py`**:
  ```python
  # BAD - causes circular import if router.py imports from dependencies.py
  from .dependencies import get_current_user
  from .router import router  # router imports dependencies, triggering __init__ again

  # GOOD - only export leaf modules, document how to import others
  """Import specific items directly from submodules:
      from package.dependencies import get_current_user
      from package.router import router
  """
  from .config import Config  # Safe - no internal dependencies
  from .models import User    # Safe - no internal dependencies
  ```

## Architecture Overview

### Stack Organization
Services are organized into numbered stacks with explicit dependencies:

1. **00-infrastructure**: Foundation services (cloudflared, caddy, redis) - Project: `localai-infra`
2. **infisical-standalone**: Secret management (external standalone project) - Project: `localai-infisical`
3. **01-data**: Data stores (supabase, neo4j, mongodb, minio) - Project: `localai-data`
4. **02-compute**: AI compute (ollama, comfyui) - Project: `localai-compute`
5. **03-apps**: Application layer (n8n, flowise, open-webui, searxng, langfuse, clickhouse) - Project: `localai-apps`
6. **04-lambda**: FastAPI server with MCP and REST APIs - Project: `localai-lambda`

Each stack uses its own Docker Compose project name for independent management, but all stacks share the `ai-network` for inter-service communication.

### Authentication System

The Lambda server implements a centralized authentication system using Cloudflare Access:

- **Method**: Header-based JWT validation (`Cf-Access-Jwt-Assertion`)
- **IdP**: Google OAuth (via Cloudflare Access)
- **JIT Provisioning**: Automatically creates users in Supabase, Neo4j, MinIO, MongoDB, and Immich on first access
- **Data Isolation**: Enforces user-scoped data access across all storage layers
- **Admin Override**: Users with `role: "admin"` can view all data
- **Location**: `04-lambda/src/services/auth/`
- **Documentation**: See [Auth Project README](04-lambda/src/services/auth/README.md) and [04-lambda/AGENTS.md](04-lambda/AGENTS.md)

### Database Schema Management

The Lambda server automatically validates and applies database migrations on startup:

- **Automatic Migration Application**: Migrations in `01-data/supabase/migrations/` are automatically applied during Lambda server startup
- **Core Table Validation**: Validates that critical tables (e.g., `profiles`) exist before allowing requests
- **Idempotent Migrations**: All migrations use `CREATE TABLE IF NOT EXISTS` to be safe to run multiple times
- **Startup Validation**: Lambda server validates core tables exist and applies missing migrations before accepting requests
- **Protection**: Core tables are validated on every startup to prevent accidental deletion
- **Location**: `04-lambda/src/services/auth/services/database_validation_service.py`
- **Migration Files**: `01-data/supabase/migrations/*.sql`
- **Documentation**: See [Supabase Migrations README](01-data/supabase/migrations/README.md)

### Network Architecture
- **External Network**: All services use `ai-network` (created by infrastructure stack)
- **Service Discovery**: Use container names as hostnames (e.g., `ollama:11434`, `supabase-db:5432`)
- **Port Strategy**:
  - Private: Expose ports directly
  - Public: Only 80/443 exposed, all traffic via Caddy reverse proxy

### Configuration Management
- **Environment Files**: `.env` (root), `.env.global` (shared), stack-specific overrides
- **Secret Management**: Infisical (optional, can fall back to `.env`)
- **Profiles**: GPU/CPU variants via Docker Compose profiles
- **Environments**: `private` (dev) vs `public` (production) via override files

## JIT Index (Component Map)

For detailed component rules, see:

### Stack-Level Documentation
- **[00-infrastructure/AGENTS.md](00-infrastructure/AGENTS.md)** - Infrastructure services (Caddy, Cloudflare Tunnel, Infisical, Redis)
- **[01-data/AGENTS.md](01-data/AGENTS.md)** - Data layer (Supabase, Neo4j, MongoDB, MinIO)
- **[02-compute/AGENTS.md](02-compute/AGENTS.md)** - AI compute (Ollama, ComfyUI)
- **[03-apps/AGENTS.md](03-apps/AGENTS.md)** - Application services (n8n, Flowise, Open WebUI, SearXNG, Langfuse, ClickHouse, Discord bots)
- **[04-lambda/AGENTS.md](04-lambda/AGENTS.md)** - Lambda FastAPI server with MCP and REST APIs
- **[setup/AGENTS.md](setup/AGENTS.md)** - Setup scripts and configuration utilities

### Lambda Project-Level Documentation
For Lambda server capabilities and workflows, see project-specific AGENTS.md files:

**Capabilities**:
- **[04-lambda/src/capabilities/calendar/calendar_sync/AGENTS.md](04-lambda/src/capabilities/calendar/calendar_sync/AGENTS.md)** - Google Calendar integration and sync
- **[04-lambda/src/capabilities/retrieval/mongo_rag/AGENTS.md](04-lambda/src/capabilities/retrieval/mongo_rag/AGENTS.md)** - MongoDB RAG with enhanced search, memory tools, and knowledge graph
- **[04-lambda/src/capabilities/retrieval/graphiti_rag/AGENTS.md](04-lambda/src/capabilities/retrieval/graphiti_rag/AGENTS.md)** - Graph-based RAG using Graphiti and Neo4j
- **[04-lambda/src/capabilities/knowledge_graph/knowledge/AGENTS.md](04-lambda/src/capabilities/knowledge_graph/knowledge/AGENTS.md)** - Event extraction from web content
- **[04-lambda/src/capabilities/knowledge_graph/knowledge_base/AGENTS.md](04-lambda/src/capabilities/knowledge_graph/knowledge_base/AGENTS.md)** - Knowledge base management
- **[04-lambda/src/capabilities/processing/openwebui_topics/AGENTS.md](04-lambda/src/capabilities/processing/openwebui_topics/AGENTS.md)** - Classify conversation topics using LLM
- **[04-lambda/src/capabilities/persona/persona_state/AGENTS.md](04-lambda/src/capabilities/persona/persona_state/AGENTS.md)** - Persona state management (mood, relationship, context)
- **[04-lambda/src/capabilities/persona/discord_characters/AGENTS.md](04-lambda/src/capabilities/persona/discord_characters/AGENTS.md)** - Discord character management and interaction

**Workflows**:
- **[04-lambda/src/workflows/automation/n8n_workflow/AGENTS.md](04-lambda/src/workflows/automation/n8n_workflow/AGENTS.md)** - N8n workflow management with RAG
- **[04-lambda/src/workflows/ingestion/crawl4ai_rag/AGENTS.md](04-lambda/src/workflows/ingestion/crawl4ai_rag/AGENTS.md)** - Web crawling and automatic ingestion into MongoDB RAG
- **[04-lambda/src/workflows/ingestion/openwebui_export/AGENTS.md](04-lambda/src/workflows/ingestion/openwebui_export/AGENTS.md)** - Export Open WebUI conversations to MongoDB RAG
- **[04-lambda/src/workflows/ingestion/youtube_rag/AGENTS.md](04-lambda/src/workflows/ingestion/youtube_rag/AGENTS.md)** - YouTube video ingestion and transcription
- **[04-lambda/src/workflows/chat/conversation/AGENTS.md](04-lambda/src/workflows/chat/conversation/AGENTS.md)** - Multi-agent conversation orchestration
- **[04-lambda/src/workflows/research/deep_research/AGENTS.md](04-lambda/src/workflows/research/deep_research/AGENTS.md)** - Deep research workflows

**Services**:
- **[04-lambda/src/services/auth/README.md](04-lambda/src/services/auth/README.md)** - Authentication system (Cloudflare Access, JIT provisioning, data isolation)

## Common Patterns

### Folder Structure Standards

**Stack-Level Organization**:
- Each numbered stack (`00-infrastructure`, `01-data`, `02-compute`, `03-apps`) is a top-level directory
- Stack-level `docker-compose.yml` at stack root (for services sharing a compose file)
- Stack-level `AGENTS.md` documents stack-specific rules
- Stack-level `docs/` for stack-wide documentation and ADRs
- Stack-level `README.md` for stack overview

**Service-Level Organization**:
- **Every service gets its own folder**, even if empty (e.g., `ollama/`). This ensures consistency and makes refactoring easier.
- Service-specific `docker-compose.yml` or `docker-compose.yaml` in the service folder
- Service-specific subdirectories:
  - `docs/` - Service-specific documentation (e.g., `cloudflared/docs/` for Cloudflare implementation)
  - `config/` - Service configuration files (Caddyfile, env overrides, etc.)
  - `data/` - Data persistence mounts (e.g., `comfyui/data/` for model weights)
  - `upstream/` - Cloned upstream repositories (e.g., for services that lack a single Docker image or require source builds)
  - `scripts/` - Service-specific utility scripts
  - `README.md` - Service documentation

**Example Structure**:
```
00-infrastructure/
├── base/                       # Shared configuration files (NEW)
│   ├── networks.yml            # Network definitions
│   ├── logging.yml             # Logging configurations
│   ├── security.yml            # Security templates
│   ├── healthchecks.yml        # Health check patterns
│   └── volumes.yml             # Volume strategy docs
├── docker-compose.yml          # Stack-level compose (caddy, infisical, redis)
├── AGENTS.md                   # Stack-specific rules
├── README.md                   # Infrastructure overview
├── docs/                       # Stack-wide docs and ADRs
├── cloudflared/
│   └── docs/                   # Cloudflare Tunnel-specific docs
├── config/                     # Stack-level configs (Caddyfile)
└── [other services...]

01-data/
├── AGENTS.md
├── supabase/
│   ├── docker-compose.yml      # Service-specific compose
│   ├── config/                 # Supabase configs
│   └── docs/                   # Supabase-specific docs
├── mongodb/
│   └── docker-compose.yml      # MongoDB with Atlas vector search
├── neo4j/
│   └── docker-compose.yml
├── minio/
│   └── docker-compose.yml
└── qdrant/                     # REMOVED - kept for reference only
    └── docker-compose.yml      # Commented out

02-compute/
├── docker-compose.yml          # Stack-level compose (ollama, comfyui)
├── AGENTS.md
├── comfyui/
│   ├── docker-compose.yaml     # Service-specific compose (if needed)
│   ├── data/                   # Model weights, outputs
│   ├── scripts/                # ComfyUI utilities
│   └── docs/                   # ComfyUI-specific docs
└── ollama/
    └── data/                   # Model storage (mounted from volume)

03-apps/
├── docker-compose.yml          # Stack-level compose
├── AGENTS.md
└── [service folders...]

04-lambda/
├── docker-compose.yml          # Lambda stack compose
├── Dockerfile                  # Custom build with package persistence
├── docker-entrypoint.sh        # Entrypoint that manages venv
├── AGENTS.md                   # Lambda-specific rules
├── server/                     # FastAPI application
└── pyproject.toml              # Python dependencies
```

**Refactoring Guidelines**:
- When moving services to service-specific folders, create the folder even if only containing `docker-compose.yml`
- Move service-specific configs, docs, and scripts into the service folder
- Keep stack-level compose files for services that logically belong together
- Use service-specific compose files when services need independent management

### Docker Compose Service Definition

**New Pattern (2024 Optimizations)**:
```yaml
# Include shared base configurations
include:
  - ../00-infrastructure/base/networks.yml
  - ../00-infrastructure/base/logging.yml
  - ../00-infrastructure/base/security.yml
  - ../00-infrastructure/base/healthchecks.yml

# Define service anchor
x-service-name: &service-name
  image: image:tag
  container_name: service-name
  restart: unless-stopped
  <<: *security-hardened  # Apply security template
  logging: *logging-json  # Apply logging config
  networks:
    - default  # ai-network (from networks.yml)
  healthcheck:
    test: ["CMD", "curl", "-f", "http://localhost:PORT/health"]
    <<: *healthcheck-http  # Apply health check timing

services:
  service-name:
    <<: *service-name
    # ... service-specific overrides
```

**See**: [docker-compose-patterns skill](.cursor/skills/docker-compose-patterns/SKILL.md) for complete details

### Profile-Based Services
```yaml
service-cpu:
  profiles: ["cpu"]
  <<: *service-base

service-gpu:
  profiles: ["gpu-nvidia"]
  <<: *service-base
  deploy:
    resources:
      reservations:
        devices:
          - driver: nvidia
            count: all
            capabilities: [gpu]
```

### Environment Variable Usage
- **Required**: Always use `${VAR_NAME:-default}` syntax for optional vars
- **Secrets**: Never hardcode. Use env vars or Infisical.
- **Service URLs**: Use container names for internal communication, hostnames for external.

### Authentication Patterns

**FastAPI Dependency Pattern** (Recommended):
```python
from server.projects.auth.dependencies import get_current_user
from server.projects.auth.models import User

@router.get("/protected")
async def protected_endpoint(user: User = Depends(get_current_user)):
    # user is automatically validated and provisioned
    return {"message": f"Hello {user.email}!"}
```

**Data Isolation Pattern**:
- Regular users: Filter queries by `user.email` or `user.uid`
- Admin users: Bypass filtering (check with `AuthService.is_admin()`)
- Storage layers:
  - **Supabase**: Filter by `owner_email` field
  - **Neo4j**: Use user anchoring: `MATCH (u:User {email: $email})`
  - **MinIO**: Filter by `user-{uuid}/` prefix
  - **MongoDB**: Filter by `user_id` or `user_email` fields
  - **Immich**: Each user has their own Immich account (1:1 mapping with Cloudflare Access email), API keys stored in `profiles.immich_api_key`

**JIT Provisioning**:
- Automatically handled by `get_current_user` dependency
- Creates user in Supabase, Neo4j, MinIO, MongoDB, and Immich on first access
- Failures are logged but don't block authentication
- Immich users get auto-generated API keys stored in `profiles.immich_api_key`

See [Auth Project README](04-lambda/src/services/auth/README.md) for complete patterns.

**Sample Script Authentication Pattern**:

All sample scripts that make HTTP API calls should use the shared authentication helpers from `sample/shared/auth_helpers.py`:

```python
from sample.shared.auth_helpers import get_api_base_url, get_auth_headers, get_cloudflare_email

# Get API base URL (defaults to internal network for local development)
api_base_url = get_api_base_url()

# Get authentication headers (empty for internal, JWT for external)
headers = get_auth_headers()

# Get user email for identification
cloudflare_email = get_cloudflare_email()
```

**Key Points**:
- **Internal Network** (`http://lambda-server:8000`): No authentication required (network isolation provides security)
- **External Network** (`https://api.datacrew.space`): Requires Cloudflare Access JWT token in `Cf-Access-Jwt-Assertion` header
- **CLOUDFLARE_EMAIL**: Automatically loaded from `.env` file in project root for user identification
- **Default Behavior**: Scripts default to internal network URLs when running locally, allowing seamless local development without JWT tokens

**Example Usage**:
```python
import requests
from sample.shared.auth_helpers import get_api_base_url, get_auth_headers

api_base_url = get_api_base_url()
headers = get_auth_headers()

response = requests.get(
    f"{api_base_url}/api/v1/comfyui/loras",
    headers=headers
)
```

**Reference**: See [sample/shared/auth_helpers.py](sample/shared/auth_helpers.py) for complete implementation.

### Pydantic AI RunContext Patterns

**Standardized RunContext Creation:**

All samples and tests should use the `create_run_context()` helper for consistent, type-safe RunContext creation:

```python
from server.projects.shared.context_helpers import create_run_context

# Initialize dependencies
deps = AgentDependencies()
await deps.initialize()

try:
    # Create run context using helper
    ctx = create_run_context(deps)

    # Call tools directly
    results = await semantic_search(ctx, query="test")
finally:
    await deps.cleanup()
```

**When to Use Each Pattern:**

1. **`agent.run(deps=deps)`** - Use when:
   - Testing full agent workflow
   - You want agent tool selection and orchestration
   - Testing end-to-end agent behavior

2. **`create_run_context()` + direct tool calls** - Use when:
   - Testing individual tools in isolation
   - Writing sample scripts that demonstrate tool usage
   - You need fine-grained control over tool inputs
   - Testing tool logic without agent overhead

**Testing Patterns:**

- **Unit Testing Tools**: Use `create_run_context()` with mocked dependencies
- **Integration Testing Agents**: Use `agent.run(deps=deps)` with real dependencies
- **Sample Scripts**: Use `create_run_context()` for direct tool demonstration

**Reference**: See [.cursor/instructions/agent-tools.instructions.md](.cursor/instructions/agent-tools.instructions.md) for detailed testing patterns and examples.

## Testing Strategy

- **ComfyUI**: pytest-based unit and inference tests (see `02-compute/comfyui/data/ComfyUI/tests/`)
- **Supabase**: pnpm/turbo test commands (see `supabase/package.json`)
- **Python Scripts**: No formal test suite yet. Manual validation via script execution.
- **Lambda Projects**: Manual API testing via REST endpoints and MCP tools. No formal test suite yet.

## Agent Gotchas

### Legacy vs Modern
- **Old**: Single `docker-compose.yml` with `include:` directive (archived)
- **New**: Stack-based modular compose files in numbered directories
- **Migration**: If you see `archive/docker-compose.yml`, it's legacy. Use stack-based files.

### Unique Patterns
- **Supabase Integration**: Uses upstream Supabase repo (cloned via `start_services.py`)
- **SearXNG First-Run**: Temporarily removes `cap_drop: - ALL` on first run (see `start_services.py:762-854`)
- **Infisical Auth**: Supports machine identity (env vars) and interactive login
- **DHI Registry**: Requires Docker Hub authentication for `dhi.io` images
- **Lambda Package Persistence**: Python packages stored in Docker volume (`lambda-packages`) to avoid reinstalling on every restart
- **Network Auto-Creation**: `start_services.py` automatically creates `ai-network` if it doesn't exist
- **Cloudflare Access Authentication**: Lambda server validates JWTs from `Cf-Access-Jwt-Assertion` header. Internal network requests bypass authentication.
- **JIT User Provisioning**: Users automatically created in Supabase, Neo4j, MinIO, MongoDB, and Immich on first authenticated request. Immich API keys are auto-generated and stored in `profiles.immich_api_key`.

### Common Mistakes to Avoid
1. **Port Conflicts**: Don't hardcode ports. Use environment variables or expose-only.
2. **Network Isolation**: All services must use `ai-network`. Don't create new networks.
3. **Volume Paths**: MUST use full paths from project root (e.g., `./03-apps/flowise/data`, not `./flowise/data`). See [docker-compose-patterns skill](.cursor/skills/docker-compose-patterns/SKILL.md).
4. **Profile Mismatch**: Ensure GPU profile services match the `--profile` flag.
5. **Secret Exposure**: Never commit `.env` files or hardcode secrets in compose files.
6. **Health Check Tools**: Use `nc -z localhost PORT` for TCP port checks when `wget`/`curl` aren't available in container. Use HTTP checks (`wget`/`curl`) when service has HTTP endpoints. **Use `127.0.0.1` instead of `localhost` in health checks** to avoid IPv6 connection issues (e.g., `http://127.0.0.1:3000/api/health`).
7. **Environment Variable Loading**: Use `env_file: - ../../.env` in docker-compose.yml to load variables from root `.env` file (path relative to compose file location).
8. **Service Dependencies**: Use `service_started` instead of `service_healthy` for dependencies when a service can function even if its dependency is unhealthy (e.g., database can start even if vector is unhealthy).
9. **One-Time Import/Init Services**: Services that run once and exit (e.g., `n8n-import`) should use `restart: "no"` to prevent blocking startup if Docker Desktop/WSL mount issues occur. These services complete their task and exit, so they don't need to restart.
10. **Database Migrations**: Migrations are automatically applied during Lambda server startup. Never manually delete core tables (e.g., `profiles`) - they will be recreated automatically but data will be lost. Always backup before schema changes.

## Search Hints

```bash
# Find Docker Compose files
rg -l "docker-compose.yml" --type yaml

# Find service definitions
rg -n "container_name:" --type yaml

# Find environment variable usage
rg -n "\$\{" --type yaml

# Find Python orchestration logic
rg -n "def " start_services.py

# Find stack-specific configs
rg -n "profile" --type yaml

# Find Lambda project agents
rg -n "^[a-z_]+_agent = Agent" 04-lambda/src/

# Find Pydantic AI tool definitions
rg -n "@.*\.tool" 04-lambda/src/

# Find project dependencies classes
rg -n "class.*Deps" 04-lambda/src/

# Find authentication endpoints
rg -n "get_current_user" 04-lambda/src/server/api/
rg -n "Depends\(get_current_user\)" 04-lambda/src/

# Find data viewing endpoints
rg -n "data_view|data/storage|data/supabase|data/neo4j|data/mongodb" 04-lambda/src/server/api/
```

## Error Handling Protocol

1. **Container Startup Failures**: Check logs first: `docker logs <container-name>`
2. **Network Issues**: Verify `ai-network` exists: `docker network inspect ai-network`
3. **Secret Errors**: Check `.env` file and Infisical authentication status
4. **GPU Issues**: Validate with `nvidia-smi` and `docker info | grep nvidia`
5. **Compose Conflicts**: Each stack uses its own project name (e.g., `-p localai-infra`, `-p localai-data`)
6. **Cross-Stack Dependencies**: `depends_on` only works within the same compose project. For cross-stack dependencies, rely on health checks and application-level retry logic.
7. **Authentication Errors**: If JWT validation fails, check `CLOUDFLARE_AUD_TAG` matches Cloudflare Access app configuration. Use `get-lambda-api-aud-tag.py` script to retrieve AUD tag.
8. **Data Isolation Issues**: Verify user email matches in all queries. Check admin status if expecting to see all data. Ensure queries use user anchoring for Neo4j.
9. **Database Schema Errors**: If you see "relation 'profiles' does not exist", check Lambda server logs for migration errors. Migrations are automatically applied on startup. If errors persist, verify database connection and manually apply migrations using `01-data/supabase/migrations/README.md` instructions.

---

**Last Updated**: Generated from codebase analysis
**Drift Check**: If codebase patterns change, update this document and flag discrepancies.
