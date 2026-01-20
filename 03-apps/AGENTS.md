# Apps Stack - AGENTS.md

> **Multi-Editor Support**: Both GitHub Copilot and Cursor AI read this file. Rules here override the root AGENTS.md for application layer concerns.

> **Override**: This file extends [../AGENTS.md](../AGENTS.md). Application layer rules take precedence.

## Component Identity

**Stack**: `03-apps`  
**Purpose**: Application services (workflow automation, AI interfaces, observability)  
**Docker Compose**: `03-apps/docker-compose.yml` (stack-level compose for all app services)  
**Network**: Uses external `ai-network`

## Folder Structure

**Stack-Level Files**:
- `docker-compose.yml` - Stack-level compose (n8n, flowise, open-webui, searxng, langfuse, clickhouse)
- `AGENTS.md` - This file (stack-specific rules)

**Service-Specific Folders** (Standardized structure: `upstream/`, `data/`, `config/`, `scripts/`):
- `n8n/`
  - `data/`
    - `home/` - n8n home directory (mounted)
    - `backup/` - Runtime backups (empty initially)
  - `config/`
    - `import/` - Seed workflows and credentials (for import)
    - `workflows/` - Workflow JSONs
  - `scripts/` - Utility scripts (e.g., `n8n_pipe.py`)
- `flowise/`
  - `data/` - Flowise data directory
  - `config/` - Config files and seed data (JSONs)
- `open-webui/`
  - `data/` - Backend data storage
- `searxng/`
  - `config/`
    - `settings-base.yml` - Template configuration
    - `settings.yml` - Generated configuration (not committed)
- `langfuse/`
  - `data/`, `config/`, `scripts/` - (Placeholders for future use)
- `clickhouse/`
  - `data/` - Database storage
  - `logs/` - Server logs

**Refactoring Notes**:
- **Strict Adherence**: All services strictly follow `service/{data,config,scripts}` pattern.
- **Bind Mounts**: Named volumes have been replaced with relative bind mounts (e.g., `./n8n/data/home`).
- **Config Management**: Configuration files reside in `config/` subdirectories.

## Services Overview

### Workflow & Automation
- **n8n** - Low-code workflow automation
- **Flowise** - No-code AI agent builder

### AI Interfaces
- **Open WebUI** - ChatGPT-like interface for local LLMs
- **SearXNG** - Privacy-focused metasearch engine

### Observability
- **Langfuse** - LLM observability platform (web + worker)
- **ClickHouse** - Time-series database (for Langfuse)

### Discord Integration
- **discord-bot** - Discord bot for Immich integration and AI character interactions (unified bot with capability-based architecture)

## Discord Bot Architecture

The Discord bot uses two complementary extensibility systems: **Capabilities** and **Agents**. Understanding when to use each is critical for maintaining clean separation of concerns.

### Capabilities vs Agents: Decision Guide

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                        WHEN TO USE EACH SYSTEM                              │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  USE CAPABILITIES WHEN:                USE AGENTS WHEN:                     │
│  ─────────────────────                 ───────────────────                  │
│  • Responding to Discord messages      • Polling external services          │
│  • Registering slash commands          • Background tasks (Bluesky, Tumblr) │
│  • Priority-based message routing      • Event-driven external integrations │
│  • User-facing Discord features        • Supabase realtime subscriptions    │
│  • Needs access to Discord message     • Does NOT need Discord message obj  │
│                                                                             │
│  LIFECYCLE:                            LIFECYCLE:                           │
│  on_ready() → on_message() → cleanup() on_start() → process_task() → stop()│
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

### Capabilities (`bot/capabilities/`)

**Purpose**: Handle Discord events and user interactions

**Key Characteristics**:
- Triggered by Discord events (messages, slash commands)
- Process in priority order (lower number = higher priority)
- Return `True` from `on_message()` to stop chain, `False` to continue
- Have direct access to `discord.Message` objects
- Support dependency validation via `requires` field
- Inter-capability communication via event bus pattern

**Base Class**: `BaseCapability`
```python
class BaseCapability(ABC):
    name: str = "base"           # Unique identifier for config
    description: str = "..."     # Human-readable description  
    priority: int = 100          # Message routing order
    requires: list[str] = []     # Dependency capabilities (validated at load)

    async def on_ready(self, tree) -> None: ...   # Register commands
    async def on_message(self, message) -> bool: ... # Handle messages
    async def cleanup(self) -> None: ...          # Shutdown cleanup

    # Event bus methods for inter-capability communication
    async def emit_event(self, event_type: str, data: dict) -> None: ...
    def subscribe_to_event(self, event_type: str, handler: callable) -> None: ...
    def unsubscribe_from_event(self, event_type: str) -> None: ...
```

**Available Capabilities**:
| Name | Priority | Description |
|------|----------|-------------|
| `echo` | 50 | Responds to @mentions with echo |
| `character_commands` | 65 | Character management slash commands (/add_character, /remove_character, etc.) |
| `character_mention` | 60 | AI character responses when mentioned by name (requires: character_commands) |
| `upload` | 100 | Uploads media to Immich, includes `/claim_face` and `/link_discord` commands |

**Slash Commands** (registered by capabilities):
| Command | Capability | Description |
|---------|-----------|-------------|
| `/claim_face` | upload | Link Discord user to Immich person for face recognition |
| `/link_discord` | upload | Link Discord account to datacrew.space for personal Immich uploads |
| `/add_character` | character_commands | Add an AI character to a channel |
| `/remove_character` | character_commands | Remove an AI character from a channel |
| `/list_characters` | character_commands | List AI characters in current channel |
| `/clear_history` | character_commands | Clear character conversation history |
| `/query_knowledge` | character_commands | Query the knowledge base |

**Deprecated Capabilities**:
| Name | Status | Replacement |
|------|--------|-------------|
| `character` | DEPRECATED | Split into `character_commands`, `character_mention`, and `CharacterEngagementAgent` |

**Legacy Handlers** (migration planned):
| Name | Status | Future |
|------|--------|--------|
| `notification_task` | Legacy | Planned migration to `NotificationAgent` |

**Configuration**: Via `ENABLED_CAPABILITIES` env var or Lambda API `/admin/discord/config`

**Note**: When `character` is specified in `ENABLED_CAPABILITIES`, it automatically loads `character_commands`, `character_mention`, and registers `CharacterEngagementAgent`.

### Lambda API Integration

The Discord bot authenticates with the Lambda API for user-specific features (e.g., personal Immich uploads).

**Authentication Methods** (in priority order):
1. **Bearer Token** (`LAMBDA_API_TOKEN`): Preferred for production. Generate via `POST /api/v1/auth/me/token` after Cloudflare Access authentication.
2. **Internal Network** (`X-User-Email` header): Works automatically when bot runs within Docker `ai-network`.

**Environment Variables**:
| Variable | Description |
|----------|-------------|
| `LAMBDA_API_URL` | Lambda server URL (default: `http://lambda-server:8000`) |
| `LAMBDA_API_TOKEN` | API token for authenticated requests (recommended for production) |
| `CLOUDFLARE_EMAIL` | Fallback email for internal network auth |

**Key API Endpoints Used**:
| Endpoint | Purpose |
|----------|---------|
| `POST /api/v1/auth/me/discord/link` | Link Discord account to Cloudflare user |
| `GET /api/v1/auth/user/by-discord/{id}` | Lookup user by Discord ID for Immich API key |

### Agents (`bot/agents/`)

**Purpose**: Background workers for external service integrations

**Key Characteristics**:
- Long-running background tasks
- Task queue-based processing
- Communicate via `DiscordCommunicationLayer` (not direct message objects)
- Independent of Discord message flow

**Base Class**: `BaseAgent`
```python
class BaseAgent(ABC):
    agent_id: str               # Unique identifier
    name: str                   # Human-readable name
    discord_channel_id: str     # Output channel for notifications

    async def on_start(self) -> None: ...        # Agent startup
    async def process_task(self, task) -> dict: ... # Task processing
    async def on_stop(self) -> None: ...         # Agent shutdown
```

**Available Agents**:
| Agent ID | Description |
|----------|-------------|
| `bluesky` | Posts to Bluesky, monitors mentions |
| `tumblr` | Reposts content to Tumblr |
| `supabase-event` | Listens to Supabase realtime events |
| `character_engagement` | Background spontaneous character engagement (polls channels) |

**Communication**: Agents use `DiscordCommunicationLayer` to send messages:
```python
discord_comm = agent_manager.get_discord_comm()
await discord_comm.send_message(channel_id, content="...")
```

### Inter-System Communication

Capabilities and agents can coordinate through multiple mechanisms:

1. **Capability → Agent**: Use `agent_manager.route_task(agent_id, task_dict)`
2. **Agent → Capability**: Agents post to Discord channels; capabilities can react to those messages
3. **Capability → Capability**: Use the event bus pattern:
   ```python
   # Emit an event
   await self.emit_event("upload_complete", {"filename": "photo.jpg", "asset_id": "abc123"})

   # Subscribe to events (in on_ready)
   self.subscribe_to_event("upload_complete", self.handle_upload_complete)
   ```

**Event Bus Pattern**:
- `CapabilityEvent`: Dataclass with `event_type`, `source`, `data`, `timestamp`
- Events are emitted asynchronously to all subscribers (except source)
- Subscribers are called concurrently with error isolation

### Adding New Features: Decision Tree

```
Does it respond to Discord messages/commands?
├── YES → Create a Capability
│   └── Does it need background polling?
│       └── YES → Also create a companion Agent
└── NO → Is it a background integration?
    ├── YES → Create an Agent
    └── NO → Probably doesn't belong in discord-bot
```

### Best Practices

1. **Single Responsibility**: Each capability/agent should do one thing well
2. **Delegate Heavy Logic**: Move API calls to service classes (`APIClient`, etc.)
3. **Priority Ordering**: Use meaningful priorities (50=core, 100=supplemental)
4. **Graceful Cleanup**: Always implement `cleanup()`/`on_stop()` for resource management
5. **Configuration-Driven**: Support enable/disable via config, not code changes
6. **Declare Dependencies**: Use `requires` field to declare capability dependencies
7. **Use Shared Resources**: Use shared `APIClient` instance instead of creating multiple clients
8. **Event-Driven Communication**: Use event bus for inter-capability communication instead of direct coupling

## n8n

### Architecture
- **Image**: `n8nio/n8n:latest`
- **Container**: `n8n` (main), `n8n-import` (one-time import)
- **Port**: 5678 (internal)
- **Database**: PostgreSQL (via Supabase, `supabase-db:5432`)
- **Storage**: `./n8n/data/home` (bind mount) + `./n8n/data/backup` (runtime) + `./n8n/config/import` (seeds)

### n8n-import Service
- **Purpose**: One-time import of credentials and workflows from `config/import/` directory
- **Restart Policy**: `restart: "no"` - Prevents blocking startup if Docker Desktop/WSL mount issues occur
- **Behavior**: Runs import command and exits (does not restart on failure)
- **Note**: If mount fails, service exits but doesn't block other services from starting

### Configuration
- **Database Type**: `DB_TYPE=postgresdb`
- **Database Host**: `DB_POSTGRESDB_HOST=supabase-db` (container name)
- **Database Credentials**: From `.env` (`POSTGRES_PASSWORD`)
- **Encryption**: `N8N_ENCRYPTION_KEY` (required)
- **JWT Secret**: `N8N_USER_MANAGEMENT_JWT_SECRET` (required)
- **Webhook URL**: `WEBHOOK_URL` (derived from `N8N_HOSTNAME`)

### Patterns
```yaml
x-n8n: &service-n8n
  image: n8nio/n8n:latest
  environment:
    - DB_TYPE=postgresdb
    - DB_POSTGRESDB_HOST=supabase-db
    # ... shared config

services:
  n8n:
    <<: *service-n8n
    volumes:
      - ./n8n/data/home:/home/node/.n8n
      - ./n8n/data/backup:/backup
      - ../../shared:/data/shared  # Shared filesystem access
```

### Key Files
- `03-apps/docker-compose.yml` - Service definition
- `03-apps/n8n/config/import/` - Seed workflows and credentials
- `03-apps/n8n/data/backup/` - Runtime backups

### Integration Points
- **Ollama**: `http://ollama:11434` (for LLM nodes)
- **Supabase**: `supabase-db:5432` (for database nodes)
- **Qdrant**: `http://qdrant:6333` (for vector store nodes)
- **Shared Files**: `/data/shared` (mounted from repo root `shared/`)

### Ollama Configuration

n8n connects to Ollama through credentials configured in the UI. Both services run on the `ai-network`, so they can communicate using container names.

**To configure Ollama access in n8n:**

1. **Access n8n UI**: Navigate to `http://localhost:5678` (or your configured hostname)
2. **Go to Credentials**: Settings → Credentials → Add Credential
3. **Select Ollama**: Choose "Ollama" from the credential types
4. **Configure Base URL**:
   - **Docker (default)**: `http://ollama:11434` (container name on ai-network)
   - **Local Ollama (Mac)**: `http://host.docker.internal:11434`
   - **Remote Ollama**: Your remote Ollama instance URL
5. **API Key** (optional): Leave empty for local Ollama. Required only for authenticated proxy services.
6. **Save**: Name the credential (e.g., "Ollama account") and save

**Using Ollama in workflows:**

- **Chat Models**: Use "Chat Ollama" node (`@n8n/n8n-nodes-langchain.lmChatOllama`)
- **LLM Models**: Use "Ollama" node (`@n8n/n8n-nodes-langchain.lmOllama`)
- **Embeddings**: Use "Embeddings Ollama" node (`@n8n/n8n-nodes-langchain.embeddingsOllama`)

All nodes require selecting the Ollama credential you created. The credential stores the Base URL, so you only need to configure it once.

**Available Models** (from Ollama service):
- Chat: `qwen2.5:7b-instruct-q4_K_M`, `llama3.1:latest`, etc.
- Embeddings: `qwen3-embedding:4b`

**Troubleshooting**:
- If connection fails, verify both `n8n` and `ollama` containers are running: `docker ps | grep -E "n8n|ollama"`
- Check network connectivity: `docker exec n8n ping -c 2 ollama`
- Verify Ollama is accessible: `docker exec n8n curl -f http://ollama:11434/api/tags`

## Flowise

### Architecture
- **Image**: `flowiseai/flowise`
- **Container**: `flowise`
- **Port**: 3001 (internal)
- **Storage**: `./flowise/data` (bind mount)

### Configuration
- **Port**: `PORT=3001`
- **Authentication**: `FLOWISE_USERNAME`, `FLOWISE_PASSWORD` (optional)
- **Config**: Seed data in `./flowise/config/`

### Patterns
- Uses `host.docker.internal` for host machine access
- Entrypoint includes `sleep 3` to allow dependencies to start

## Open WebUI

### Architecture
- **Image**: `ghcr.io/open-webui/open-webui:main`
- **Container**: `open-webui`
- **Port**: 8080 (internal)
- **Storage**: `./open-webui/data` (bind mount)
- **Database**: PostgreSQL (via Supabase, `supabase-db:5432`)

### Configuration
- **Database**: PostgreSQL for persistent conversation storage
- **OAuth**: Google OAuth (SSO) authentication enabled
  - Reuses `CLIENT_ID_GOOGLE_LOGIN` and `CLIENT_SECRET_GOOGLE_LOGIN` from `.env`
  - Automatic account creation on first Google sign-in (if enabled)
  - Proper logout via OpenID Provider URL
- **Lambda Integration**: MCP server and RAG APIs via `LAMBDA_SERVER_URL`
- Connects to Ollama at `http://ollama:11434`
- Supports custom functions (e.g., n8n integration via webhook)

### Integration
- **n8n Pipe**: Custom function to route requests to n8n workflows
- **Ollama**: Direct connection for model inference
- **Lambda Server**: MCP tools, conversation export, topic classification, RAG search
- **PostgreSQL**: Persistent conversation and user data storage

## SearXNG

### Architecture
- **Image**: `docker.io/searxng/searxng:latest`
- **Container**: `searxng`
- **Port**: 8080 (internal)
- **Config**: `./searxng/config/settings.yml` (mounted to `/etc/searxng`)

### Configuration
- **Base URL**: `SEARXNG_BASE_URL` (derived from `SEARXNG_HOSTNAME`)
- **Workers**: `UWSGI_WORKERS` (default: 4)
- **Threads**: `UWSGI_THREADS` (default: 4)
- **Secret Key**: Auto-generated on first run (replaces `ultrasecretkey`)

### Patterns
- **First Run**: Temporarily removes `cap_drop: - ALL` to create `uwsgi.ini`
- **Config Generation**: `start_services.py` generates secret key via `openssl rand -hex 32`
- **Capabilities**: `CHOWN`, `SETGID`, `SETUID` only (hardened after first run)

### Key Files
- `searxng/config/settings-base.yml` - Template configuration
- `searxng/config/settings.yml` - Generated configuration (with secret key)

## Langfuse

### Architecture
- **Components**:
  - `langfuse-web` - Web UI (Next.js)
  - `langfuse-worker` - Background job processor
- **Image**: `langfuse/langfuse:3` (web), `langfuse/langfuse-worker:3` (worker)
- **Ports**: 3000 (web, internal), 3030 (worker, internal)
- **Dependencies**: ClickHouse, MinIO, Redis, PostgreSQL (Supabase)

### Configuration
- **Database**: PostgreSQL via Supabase (`supabase-db:5432`)
- **ClickHouse**: For time-series data (`clickhouse:8123`)
- **MinIO**: For event and media storage (`minio:9000`) - See data layer
- **Redis**: For job queue (`redis:6379`)
- **Secrets**: `LANGFUSE_SALT`, `ENCRYPTION_KEY`, `NEXTAUTH_SECRET`

### Patterns
- Uses shared environment anchor (`&langfuse-worker-env`) for common config
- S3-compatible storage via MinIO (from data layer, separate from Supabase MinIO)
- Event uploads to `langfuse` bucket with `events/` prefix
- Media uploads to `langfuse` bucket with `media/` prefix

## ClickHouse

### Architecture
- **Image**: `clickhouse/clickhouse-server:latest`
- **Container**: `clickhouse`
- **Ports**: 8123 (HTTP), 9000 (native), 9009 (inter-server)
- **Volumes**: `./clickhouse/data`, `./clickhouse/logs` (bind mounts)

### Configuration
- **User**: `clickhouse`
- **Password**: `CLICKHOUSE_PASSWORD` (from `.env`)
- **User ID**: `101:101` (non-root)

## Architecture Patterns

### Service Dependencies
- **Langfuse**: Depends on ClickHouse, MinIO, Redis (health checks)
- **n8n**: Depends on Supabase (database connection)
- **All Services**: Depend on `ai-network` (external network)

### Volume Strategy
- **Bind Mounts**: All persistent storage uses local bind mounts relative to the service directory.
  - Pattern: `./<service>/data[/<subdirectory>]`
  - Advantage: Clear data ownership, easy backup/restore, git-ignore friendly.

### Environment Variable Patterns
- **Service URLs**: Use container names for internal, hostnames for external
- **Secrets**: All from `.env` (never hardcoded)
- **Defaults**: Use `${VAR:-default}` syntax

## Testing & Validation

### Health Checks
```bash
# n8n
curl http://localhost:5678/healthz

# Flowise
curl http://flowise:3001/api/v1/ping

# Open WebUI
curl http://open-webui:8080/health

# Frontend (Next.js)
curl http://127.0.0.1:3000/api/health  # Use 127.0.0.1, not localhost (IPv6 issue)

# SearXNG
curl http://searxng:8080/

# Langfuse
curl http://langfuse-web:3000/api/public/health

# ClickHouse
curl http://clickhouse:8123/ping
```

**Health Check Patterns**:
- **Use `127.0.0.1` instead of `localhost`** for health checks to avoid IPv6 connection issues
- **Frontend**: Health check uses `http://127.0.0.1:3000/api/health` (Next.js binds to IPv4 only)
- **Discord Bot**: MCP server port (8001) uses `expose` not `ports` (internal only, avoids Caddy port conflict)

## Do's and Don'ts

### ✅ DO
- Use container names for internal service communication
- Share volumes between related services when needed
- Use health checks for service dependencies
- Generate secure secrets (use password generator script)

### ❌ DON'T
- Hardcode service URLs (use environment variables)
- Expose database ports directly (use reverse proxy)
- Commit generated configuration files (e.g., `searxng/config/settings.yml`)
- Skip health checks in dependencies

## Domain Dictionary

- **n8n**: Workflow automation platform (400+ integrations)
- **Flowise**: Visual AI agent builder (LangChain-based)
- **Open WebUI**: Web interface for local LLMs (ChatGPT alternative)
- **SearXNG**: Privacy-focused search engine aggregator
- **Langfuse**: LLM observability and analytics platform
- **ClickHouse**: Columnar database for analytics

---

**See Also**:
- [../AGENTS.md](../AGENTS.md) for universal rules
- [start_services.py](../start_services.py) for SearXNG secret generation
