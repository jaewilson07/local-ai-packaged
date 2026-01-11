# Apps Stack - AGENTS.md

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
- **discord-bot** - Discord bot for Immich integration
- **discord-character-bot** - Discord bot for AI character interactions

## n8n

### Architecture
- **Image**: `n8nio/n8n:latest`
- **Container**: `n8n` (main), `n8n-import` (one-time import)
- **Port**: 5678 (internal)
- **Database**: PostgreSQL (via Supabase, `supabase-db:5432`)
- **Storage**: `./n8n/data/home` (bind mount) + `./n8n/data/backup` (runtime) + `./n8n/config/import` (seeds)

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
- Embeddings: `nomic-embed-text:latest`

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

# SearXNG
curl http://searxng:8080/

# Langfuse
curl http://langfuse-web:3000/api/public/health

# ClickHouse
curl http://clickhouse:8123/ping
```

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