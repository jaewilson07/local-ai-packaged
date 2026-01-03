# Apps Stack - AGENTS.md

> **Override**: This file extends [../AGENTS.md](../AGENTS.md). Application layer rules take precedence.

## Component Identity

**Stack**: `03-apps`  
**Purpose**: Application services (workflow automation, AI interfaces, observability)  
**Docker Compose**: `03-apps/docker-compose.yml` (stack-level compose for all app services)  
**Network**: Uses external `ai-network`

## Folder Structure

**Stack-Level Files**:
- `docker-compose.yml` - Stack-level compose (n8n, flowise, open-webui, searxng, langfuse, clickhouse, mongodb, minio)
- `AGENTS.md` - This file (stack-specific rules)
- `data/` - Shared data directory for app data
  - `n8n/backup/` - n8n workflow and credential backups
  - `searxng/` - SearXNG configuration files

**Service-Specific Folders** (Each service should have its own folder):
- `n8n/` - n8n workflow automation
  - (Future: `docs/`, `config/` if service-specific configs needed)
- `flowise/` - Flowise AI agent builder
  - (Future: `docs/`, `config/` if service-specific configs needed)
- `open-webui/` - Open WebUI interface
  - (Future: `docs/`, `config/` if service-specific configs needed)
- `searxng/` - SearXNG search engine
  - `settings-base.yml` - Template configuration
  - `settings.yml` - Generated configuration (not committed)
  - (Future: `docs/`, `config/` if needed)
- `langfuse/` - Langfuse observability
  - (Future: `docs/`, `config/` if service-specific configs needed)
- `comfyui/` - ComfyUI (if moved from compute stack)
  - (Note: Currently in 02-compute, may be duplicated here for app access)

**Refactoring Notes**:
- Most services are currently in stack-level compose (shared management)
- Service-specific folders should be created even if empty (for consistency)
- When services need independent management or have service-specific resources, move to service-specific compose files
- Follow the pattern: create service folder → add service-specific compose → move configs/docs

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
- **MinIO** - S3-compatible storage (for Langfuse)
- **MongoDB** - Document database (for various services)

## n8n

### Architecture
- **Image**: `n8nio/n8n:latest`
- **Container**: `n8n` (main), `n8n-import` (one-time import)
- **Port**: 5678 (internal)
- **Database**: PostgreSQL (via Supabase, `supabase-db:5432`)
- **Storage**: `n8n_storage` volume + `./data/n8n/backup` (bind mount)

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
      - n8n_storage:/home/node/.n8n
      - ../../shared:/data/shared  # Shared filesystem access
```

### Key Files
- `03-apps/docker-compose.yml` - Service definition
- `03-apps/data/n8n/backup/` - Workflow and credential backups

### Integration Points
- **Ollama**: `http://ollama:11434` (for LLM nodes)
- **Supabase**: `supabase-db:5432` (for database nodes)
- **Qdrant**: `http://qdrant:6333` (for vector store nodes)
- **Shared Files**: `/data/shared` (mounted from repo root `shared/`)

## Flowise

### Architecture
- **Image**: `flowiseai/flowise`
- **Container**: `flowise`
- **Port**: 3001 (internal)
- **Storage**: `flowise` volume

### Configuration
- **Port**: `PORT=3001`
- **Authentication**: `FLOWISE_USERNAME`, `FLOWISE_PASSWORD` (optional)

### Patterns
- Uses `host.docker.internal` for host machine access
- Entrypoint includes `sleep 3` to allow dependencies to start

## Open WebUI

### Architecture
- **Image**: `ghcr.io/open-webui/open-webui:main`
- **Container**: `open-webui`
- **Port**: 8080 (internal)
- **Storage**: `open-webui` volume

### Configuration
- Connects to Ollama at `http://ollama:11434`
- Supports custom functions (e.g., n8n integration via webhook)

### Integration
- **n8n Pipe**: Custom function to route requests to n8n workflows
- **Ollama**: Direct connection for model inference

## SearXNG

### Architecture
- **Image**: `docker.io/searxng/searxng:latest`
- **Container**: `searxng`
- **Port**: 8080 (internal)
- **Config**: `./data/searxng/settings.yml` (generated from `settings-base.yml`)

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
- `searxng/settings-base.yml` - Template configuration
- `searxng/settings.yml` - Generated configuration (with secret key)

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
- **MinIO**: For event and media storage (`minio:9000`)
- **Redis**: For job queue (`redis:6379`)
- **Secrets**: `LANGFUSE_SALT`, `ENCRYPTION_KEY`, `NEXTAUTH_SECRET`

### Patterns
- Uses shared environment anchor (`&langfuse-worker-env`) for common config
- S3-compatible storage via MinIO (separate from Supabase MinIO)
- Event uploads to `langfuse` bucket with `events/` prefix
- Media uploads to `langfuse` bucket with `media/` prefix

## ClickHouse

### Architecture
- **Image**: `clickhouse/clickhouse-server:latest`
- **Container**: `clickhouse`
- **Ports**: 8123 (HTTP), 9000 (native), 9009 (inter-server)
- **Volumes**: `langfuse_clickhouse_data`, `langfuse_clickhouse_logs`

### Configuration
- **User**: `clickhouse`
- **Password**: `CLICKHOUSE_PASSWORD` (from `.env`)
- **User ID**: `101:101` (non-root)

## MinIO (Langfuse)

### Architecture
- **Image**: `minio/minio`
- **Container**: `minio`
- **Ports**: 9000 (API), 9001 (Console)
- **Volume**: `langfuse_minio_data`

### Configuration
- **Root User**: `minio`
- **Root Password**: `MINIO_ROOT_PASSWORD` (from `.env`)
- **Buckets**: `langfuse` (auto-created)

**Note**: Separate from `supabase-minio` (different service, different credentials)

## MongoDB

### Architecture
- **Image**: `mongo:latest`
- **Container**: `mongodb`
- **Port**: 27017 (internal)
- **Volume**: `mongodb_data`

### Configuration
- **Root Username**: `MONGODB_ROOT_USERNAME` (default: `admin`)
- **Root Password**: `MONGODB_ROOT_PASSWORD` (required)
- **Database**: `MONGODB_DATABASE` (default: `admin`)

## Architecture Patterns

### Service Dependencies
- **Langfuse**: Depends on ClickHouse, MinIO, Redis (health checks)
- **n8n**: Depends on Supabase (database connection)
- **All Services**: Depend on `ai-network` (external network)

### Volume Strategy
- **Named Volumes**: For application data (e.g., `n8n_storage`, `flowise`)
- **Bind Mounts**: For configuration and backups (e.g., `./data/n8n/backup`)

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

# MinIO
docker exec minio mc ready local

# MongoDB
docker exec mongodb mongosh --eval "db.adminCommand('ping')"
```

### Common Issues
1. **n8n Database Connection**: Verify `supabase-db` is running and password doesn't contain `@`
2. **SearXNG Restart Loop**: Run `chmod 755 searxng` to fix permissions
3. **Langfuse Dependencies**: Ensure ClickHouse, MinIO, and Redis are healthy
4. **MinIO vs Supabase MinIO**: Don't confuse credentials (different services)

## Do's and Don'ts

### ✅ DO
- Use container names for internal service communication
- Share volumes between related services when needed
- Use health checks for service dependencies
- Generate secure secrets (use password generator script)
- Separate MinIO instances (Langfuse vs Supabase)

### ❌ DON'T
- Hardcode service URLs (use environment variables)
- Mix MinIO credentials between services
- Expose database ports directly (use reverse proxy)
- Commit generated configuration files (e.g., `searxng/settings.yml`)
- Skip health checks in dependencies

## Domain Dictionary

- **n8n**: Workflow automation platform (400+ integrations)
- **Flowise**: Visual AI agent builder (LangChain-based)
- **Open WebUI**: Web interface for local LLMs (ChatGPT alternative)
- **SearXNG**: Privacy-focused search engine aggregator
- **Langfuse**: LLM observability and analytics platform
- **ClickHouse**: Columnar database for analytics
- **MinIO**: S3-compatible object storage
- **MongoDB**: Document database

---

**See Also**: 
- [../AGENTS.md](../AGENTS.md) for universal rules
- [start_services.py](../start_services.py) for SearXNG secret generation

