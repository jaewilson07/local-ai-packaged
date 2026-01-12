# AGENTS.md - Universal Constitution

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

## Architecture Overview

### Stack Organization
Services are organized into numbered stacks with explicit dependencies:

1. **00-infrastructure**: Foundation services (cloudflared, caddy, redis) - Project: `localai-infra`
2. **00-infrastructure/infisical**: Secret management (infisical-backend, infisical-db, infisical-redis) - Project: `localai-infisical`
3. **01-data**: Data stores (supabase, qdrant, neo4j, mongodb, minio) - Project: `localai-data`
4. **02-compute**: AI compute (ollama, comfyui) - Project: `localai-compute`
5. **03-apps**: Application layer (n8n, flowise, open-webui, searxng, langfuse, clickhouse) - Project: `localai-apps`
6. **04-lambda**: FastAPI server with MCP and REST APIs - Project: `localai-lambda`

Each stack uses its own Docker Compose project name for independent management, but all stacks share the `ai-network` for inter-service communication.

### Authentication System

The Lambda server implements a centralized authentication system using Cloudflare Access:

- **Method**: Header-based JWT validation (`Cf-Access-Jwt-Assertion`)
- **IdP**: Google OAuth (via Cloudflare Access)
- **JIT Provisioning**: Automatically creates users in Supabase, Neo4j, and MinIO on first access
- **Data Isolation**: Enforces user-scoped data access across all storage layers
- **Admin Override**: Users with `role: "admin"` can view all data
- **Location**: `04-lambda/server/projects/auth/`
- **Documentation**: See [Auth Project README](04-lambda/server/projects/auth/README.md) and [04-lambda/AGENTS.md](04-lambda/AGENTS.md)

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
- **[01-data/AGENTS.md](01-data/AGENTS.md)** - Data layer (Supabase, Qdrant, Neo4j, MongoDB, MinIO)
- **[02-compute/AGENTS.md](02-compute/AGENTS.md)** - AI compute (Ollama, ComfyUI)
- **[03-apps/AGENTS.md](03-apps/AGENTS.md)** - Application services (n8n, Flowise, Open WebUI, SearXNG, Langfuse, ClickHouse, Discord bots)
- **[04-lambda/AGENTS.md](04-lambda/AGENTS.md)** - Lambda FastAPI server with MCP and REST APIs
- **[setup/AGENTS.md](setup/AGENTS.md)** - Setup scripts and configuration utilities

### Lambda Project-Level Documentation
For Lambda server projects, see project-specific AGENTS.md files:

- **[04-lambda/server/projects/calendar/AGENTS.md](04-lambda/server/projects/calendar/AGENTS.md)** - Google Calendar integration and sync
- **[04-lambda/server/projects/conversation/AGENTS.md](04-lambda/server/projects/conversation/AGENTS.md)** - Multi-agent conversation orchestration
- **[04-lambda/server/projects/crawl4ai_rag/AGENTS.md](04-lambda/server/projects/crawl4ai_rag/AGENTS.md)** - Web crawling and automatic ingestion into MongoDB RAG knowledge base
- **[04-lambda/server/projects/graphiti_rag/AGENTS.md](04-lambda/server/projects/graphiti_rag/AGENTS.md)** - Graph-based RAG using Graphiti and Neo4j
- **[04-lambda/server/projects/knowledge/AGENTS.md](04-lambda/server/projects/knowledge/AGENTS.md)** - Event extraction from web content
- **[04-lambda/server/projects/mongo_rag/AGENTS.md](04-lambda/server/projects/mongo_rag/AGENTS.md)** - MongoDB RAG with enhanced search, memory tools, and knowledge graph
- **[04-lambda/server/projects/n8n_workflow/AGENTS.md](04-lambda/server/projects/n8n_workflow/AGENTS.md)** - N8n workflow management with RAG
- **[04-lambda/server/projects/openwebui_export/AGENTS.md](04-lambda/server/projects/openwebui_export/AGENTS.md)** - Export Open WebUI conversations to MongoDB RAG system for searchability
- **[04-lambda/server/projects/openwebui_topics/AGENTS.md](04-lambda/server/projects/openwebui_topics/AGENTS.md)** - Classify conversation topics using LLM for organization and filtering
- **[04-lambda/server/projects/persona/AGENTS.md](04-lambda/server/projects/persona/AGENTS.md)** - Persona state management (mood, relationship, context)
- **[04-lambda/server/projects/discord_characters/AGENTS.md](04-lambda/server/projects/discord_characters/AGENTS.md)** - Discord character management and interaction
- **[04-lambda/server/projects/auth/README.md](04-lambda/server/projects/auth/README.md)** - Authentication system (Cloudflare Access, JIT provisioning, data isolation)

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
├── qdrant/
│   └── docker-compose.yml
└── neo4j/
    └── docker-compose.yml

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

**See**: [Docker Compose Optimization Guide](docs/docker-compose-optimization-guide.md) for complete details

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

**JIT Provisioning**:
- Automatically handled by `get_current_user` dependency
- Creates user in Supabase, Neo4j, and MinIO on first access
- Failures are logged but don't block authentication

See [Auth Project README](04-lambda/server/projects/auth/README.md) for complete patterns.

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
- **JIT User Provisioning**: Users automatically created in Supabase, Neo4j, and MinIO on first authenticated request.

### Common Mistakes to Avoid
1. **Port Conflicts**: Don't hardcode ports. Use environment variables or expose-only.
2. **Network Isolation**: All services must use `ai-network`. Don't create new networks.
3. **Volume Paths**: MUST use full paths from project root (e.g., `./03-apps/flowise/data`, not `./flowise/data`). See [docs/docker-compose-volume-paths.md](docs/docker-compose-volume-paths.md).
4. **Profile Mismatch**: Ensure GPU profile services match the `--profile` flag.
5. **Secret Exposure**: Never commit `.env` files or hardcode secrets in compose files.

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
rg -n "^[a-z_]+_agent = Agent" 04-lambda/server/projects/

# Find Pydantic AI tool definitions
rg -n "@.*\.tool" 04-lambda/server/projects/

# Find project dependencies classes
rg -n "class.*Deps" 04-lambda/server/projects/

# Find authentication endpoints
rg -n "get_current_user" 04-lambda/server/api/
rg -n "Depends\(get_current_user\)" 04-lambda/server/

# Find data viewing endpoints
rg -n "data_view|data/storage|data/supabase|data/neo4j|data/mongodb" 04-lambda/server/api/
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

---

**Last Updated**: Generated from codebase analysis
**Drift Check**: If codebase patterns change, update this document and flag discrepancies.
