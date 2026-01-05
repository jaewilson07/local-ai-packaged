# Architecture Decisions

## Overview

This project uses a **stack-based Docker Compose architecture** where services are organized into logical stacks (infrastructure, data, compute, apps). Each stack has its own `docker-compose.yml` file in a dedicated directory. The `start_services.py` script stitches them together using multiple `-f` flags, which is Docker's recommended "merge" approach for large applications.

This architecture provides clear separation between infrastructure, data persistence, compute workloads, and application services, making it easier to manage, update, and scale individual components.

## Architecture Benefits

1. **Stack Isolation**: Services are grouped by function (infrastructure, data, compute, apps)
2. **Independent Updates**: Update individual stacks without affecting others
3. **Clear Organization**: Each stack is self-contained and easy to understand
4. **Flexible Startup**: Can start stacks independently or all at once
5. **Network Isolation**: All services use external `ai-network` for communication
6. **Maintainability**: Clear separation of concerns by function

## Why Modular Docker Compose?

### Problem: The `include:` Directive Conflict

The original architecture used a single `docker-compose.yml` file with the `include:` directive to include Supabase compose files:

```yaml
include:
  - ./supabase/docker/docker-compose.yml
  - ./supabase/docker/docker-compose.s3.yml
```

This caused conflicts when:
- Starting services independently
- Using `docker compose down` 
- Trying to start Infisical separately
- Updating Supabase compose files

Error example:
```
services.storage conflicts with imported resource
```

### Solution: Stack-Based Compose Files

Each stack now has its own compose file in numbered directories:

```
00-infrastructure/docker-compose.yml
01-data/supabase/docker-compose.yml
01-data/qdrant/docker-compose.yml
01-data/neo4j/docker-compose.yml
02-compute/docker-compose.yml
03-apps/docker-compose.yml
```

Each stack uses its own Docker Compose project name for independent management:

```bash
# Infrastructure stack
docker compose -p localai-infra -f 00-infrastructure/docker-compose.yml up -d

# Infisical stack
docker compose -p localai-infisical -f 00-infrastructure/infisical/docker-compose.yml up -d

# Data stack
docker compose -p localai-data \
  -f 01-data/supabase/docker-compose.yml \
  -f 01-data/qdrant/docker-compose.yml \
  -f 01-data/neo4j/docker-compose.yml \
  -f 01-data/mongodb/docker-compose.yml \
  -f 01-data/minio/docker-compose.yml \
  up -d

# Compute stack
docker compose -p localai-compute -f 02-compute/docker-compose.yml --profile gpu-nvidia up -d

# Apps stack
docker compose -p localai-apps -f 03-apps/docker-compose.yml up -d

# Lambda stack
docker compose -p localai-lambda -f 04-lambda/docker-compose.yml up -d
```

All stacks share the external `ai-network` for inter-service communication.

### Benefits

1. **No Conflicts**: Each compose file is independent until merged
2. **Easy Updates**: Update Supabase by running `scripts/update-supabase-compose.py`
3. **Better Organization**: Clear separation of concerns
4. **Flexible**: Easy to enable/disable components
5. **Docker Best Practice**: Aligns with Docker's recommended approach for large applications

## Directory Structure

```
/ai-homelab
├── .env.global               # Non-sensitive globals (DOMAIN_NAME, TZ)
├── config/networks.yml        # Defines external 'ai-network'
│
├── 00-infrastructure/        # Stack: Connectivity & Security (Project: localai-infra)
│   ├── docker-compose.yml    # cloudflared, caddy, redis
│   ├── infisical/            # Infisical stack (Project: localai-infisical)
│   │   └── docker-compose.yml # infisical-backend, infisical-db, infisical-redis
│   ├── docs/                 # Infrastructure documentation
│   └── config/               # Cloudflare tunnel configs
│
├── 01-data/                  # Stack: Persistence (Databases) (Project: localai-data)
│   ├── supabase/             # Supabase (multi-container setup)
│   │   ├── docker-compose.yml
│   │   └── docs/
│   ├── qdrant/               # Qdrant Vector DB
│   │   └── docker-compose.yml
│   ├── neo4j/                # Neo4j Graph DB
│   │   └── docker-compose.yml
│   ├── mongodb/              # MongoDB
│   │   └── docker-compose.yml
│   └── minio/                # MinIO S3-compatible storage
│       └── docker-compose.yml
│
├── 02-compute/               # Stack: Heavy AI Inference (GPU) (Project: localai-compute)
│   ├── docker-compose.yml    # ollama, comfyui
│   └── data/                 # Model weights/outputs
│       ├── ollama/           # Ollama models
│       └── comfyui/          # ComfyUI models, workflows, config
│
├── 03-apps/                  # Stack: Agentic Workflows & UI (Project: localai-apps)
│   └── docker-compose.yml    # n8n, flowise, open-webui, searxng, langfuse, clickhouse
│
└── 04-lambda/                # Stack: FastAPI Server (Project: localai-lambda)
    └── docker-compose.yml    # lambda-server
```

## Stack Details

### Infrastructure Stack (`00-infrastructure/docker-compose.yml`)

- **Project Name**: `localai-infra`
- **Services**: `cloudflared`, `caddy`, `redis`
- **Network**: Uses external `ai-network`
- **Purpose**: Core connectivity, reverse proxy, and shared Redis
- **Key Features**:
  - Cloudflare Tunnel for secure ingress
  - Caddy as reverse proxy routing to all services
  - Redis for n8n and other services

### Infisical Stack (`00-infrastructure/infisical/docker-compose.yml`)

- **Project Name**: `localai-infisical`
- **Services**: `infisical-backend`, `infisical-db`, `infisical-redis`
- **Network**: Uses external `ai-network`
- **Purpose**: Secret management with dedicated PostgreSQL (separate from Supabase)
- **Key Features**:
  - Infisical backend for secret management
  - Dedicated PostgreSQL database
  - Dedicated Redis instance

### Data Stack (`01-data/`)

- **Project Name**: `localai-data`

#### Supabase (`01-data/supabase/docker-compose.yml`)

- **Services**: `db`, `studio`, `kong`, `auth`, `rest`, `realtime`, `storage`, `imgproxy`, `meta`, `functions`, `analytics`, `vector`, `supavisor`, `supabase-minio`
- **Source**: Based on upstream Supabase compose files
- **Network**: Uses external `ai-network`
- **Volume Paths**: Relative to `01-data/supabase/` (e.g., `../../../supabase/docker/volumes/`)

#### Qdrant (`01-data/qdrant/docker-compose.yml`)

- **Services**: `qdrant`
- **Purpose**: Vector database for embeddings and RAG
- **Network**: Uses external `ai-network`

#### Neo4j (`01-data/neo4j/docker-compose.yml`)

- **Services**: `neo4j`
- **Purpose**: Graph database for knowledge graphs
- **Network**: Uses external `ai-network`
- **Volumes**: Bind mounts to `../../neo4j/{logs,config,data,plugins}`

### Compute Stack (`02-compute/docker-compose.yml`)

- **Project Name**: `localai-compute`
- **Services**: `ollama-cpu`, `ollama-gpu`, `ollama-gpu-amd`, `comfyui-cpu`, `comfyui-gpu`, `comfyui-gpu-amd`
- **Uses Profiles**: CPU vs GPU variants using Docker Compose profiles
- **Network**: Uses external `ai-network`
- **GPU Support**: NVIDIA and AMD GPU passthrough configured
- **Data**: Models stored in `02-compute/data/ollama/` and `02-compute/data/comfyui/`

### Apps Stack (`03-apps/docker-compose.yml`)

- **Project Name**: `localai-apps`
- **Services**: `n8n`, `flowise`, `open-webui`, `searxng`, `langfuse-web`, `langfuse-worker`, `clickhouse`
- **Network**: Uses external `ai-network`
- **Dependencies**: 
  - n8n → `ollama:11434`, `supabase-db:5432`, `redis:6379`
  - open-webui → `ollama:11434`, `searxng:8080`
  - langfuse → `supabase-db:5432`, `minio:9000`, `redis:6379`, `clickhouse:8123`

### Lambda Stack (`04-lambda/docker-compose.yml`)

- **Project Name**: `localai-lambda`
- **Services**: `lambda-server`
- **Network**: Uses external `ai-network`
- **Purpose**: FastAPI server with MCP and REST APIs
- **Dependencies**: `mongodb:27017`, `ollama:11434`

## Project Naming Strategy

Each stack uses its own Docker Compose project name to enable independent management:

- `localai-infra` - Infrastructure services
- `localai-infisical` - Infisical secret management
- `localai-data` - Data persistence services
- `localai-compute` - AI compute services
- `localai-apps` - Application services
- `localai-lambda` - Lambda API server

### Benefits of Separate Project Names

1. **Independent Management**: Each stack can be started/stopped independently
2. **Clear Organization**: Docker Desktop shows separate project groups
3. **Easier Debugging**: Isolate issues to specific stacks
4. **Resource Control**: Stop compute stack when not needed, keep data running
5. **Shared Network**: All stacks use `ai-network` for inter-service communication

### Network Architecture

All stacks share the external Docker network `ai-network`:

- **Services**: `n8n`, `flowise`, `open-webui`, `searxng`, `langfuse-web`, `langfuse-worker`, `clickhouse`, `mongodb`, `minio`
- **Network**: Uses external `ai-network`
- **Dependencies**: 
  - n8n → `ollama:11434`, `supabase-db:5432`
  - open-webui → `ollama:11434`, `searxng:8080`
  - langfuse → `supabase-db:5432`, `minio:9000`, `redis:6379`, `clickhouse:8123`

## Network Architecture

### Single Shared Network

All services use the external Docker network `ai-network`:

- **Network Definition**: Defined in `config/networks.yml` and created separately:
  ```bash
  docker network create ai-network
  ```

- **All compose files** reference it as external:
  ```yaml
  networks:
    default:
      external: true
      name: ai-network
  ```

This ensures all services can communicate with each other by container name across all stacks.

### Why Not Multiple Networks?

A single network simplifies:
- Service discovery (containers can reference each other by name)
- Dependency management (`depends_on` works across compose files)
- Configuration (one network to manage)

## Volume Strategy

### Shared Volumes

Volumes are defined in each compose file where they're used. Docker Compose automatically merges volume definitions when multiple `-f` flags are used, so volumes with the same name are shared across services.

Example:
- `00-infrastructure/docker-compose.yml` defines `valkey-data`
- Other compose files can reference `valkey-data` (if needed)
- Both reference the same volume

### Volume Path Resolution

Volume paths are relative to the compose file's location:

```yaml
# 01-data/supabase/docker-compose.yml
volumes:
  - ../../../supabase/docker/volumes/db/data:/var/lib/postgresql/data:Z
```

This resolves to: `project_root/supabase/docker/volumes/db/data`

### Volume Types

- **Named Volumes**: Used for most services (e.g., `ollama_storage`, `n8n_storage`)
- **Bind Mounts**: Used for configuration and data that needs to be directly accessible (e.g., Neo4j, Supabase volumes)

## Service Dependencies

### Using Service Names vs Container Names

**Critical distinction**:
- `depends_on` uses **service names** (e.g., `db`)
- Connection strings use **container names** (e.g., `supabase-db`)

Example:
```yaml
# 00-infrastructure/docker-compose.yml
services:
  infisical-backend:
    depends_on:
      infisical-db:  # Service name
        condition: service_healthy
    environment:
      - DB_CONNECTION_URI=postgresql://postgres:${POSTGRES_PASSWORD}@infisical-db:5432/postgres
      # Container name (infisical-db) used in connection string
```

### Service Communication

Services communicate via the `ai-network` using container names:

- **n8n** → `ollama:11434`, `supabase-db:5432`
- **open-webui** → `ollama:11434`, `searxng:8080`
- **langfuse** → `supabase-db:5432`, `minio:9000`, `redis:6379`, `clickhouse:8123`
- **infisical-backend** → `infisical-db:5432`, `infisical-redis:6379`

## Component Organization

### Why These Components?

Components are organized by function:

- **00-infrastructure**: Infrastructure services (Caddy, Cloudflared, Redis, Infisical)
- **01-data**: Data stores (Supabase, Qdrant, Neo4j)
- **02-compute**: AI/ML services (Ollama, ComfyUI)
- **03-apps**: Application services (n8n, Flowise, Open WebUI, SearXNG, Langfuse, etc.)

### Why Not One File Per Service?

Grouping related services:
- Reduces number of files to manage
- Keeps related services together
- Makes it easier to understand dependencies
- Still provides enough granularity for updates

## Profiles

The compute stack uses Docker Compose profiles to support different hardware configurations:

- **`cpu`**: CPU-only services (default)
- **`gpu-nvidia`**: NVIDIA GPU services
- **`gpu-amd`**: AMD GPU services

## Secret Management

Sensitive secrets are managed via Infisical:

- **Infisical Backend**: Stores and manages all secrets
- **Infisical Database**: Dedicated PostgreSQL instance (separate from Supabase)
- **Secret Injection**: `start_services.py` exports secrets from Infisical to `.env.infisical` for use by services
- **Fallback**: If Infisical is unavailable, services fall back to `.env` file

## Starting Services

### Start All Stacks

```bash
python start_services.py --profile gpu-nvidia
```

This will start all stacks in order:
1. Infrastructure (cloudflared, caddy, infisical, redis)
2. Data (supabase, qdrant, neo4j)
3. Compute (ollama, comfyui)
4. Apps (n8n, flowise, open-webui, searxng, langfuse, etc.)

### Start Individual Stacks

```bash
# Start infrastructure stack
python start_services.py --stack infrastructure

# Start data stack
python start_services.py --stack data

# Start compute stack (with GPU profile)
python start_services.py --stack compute --profile gpu-nvidia

# Start apps stack
python start_services.py --stack apps
```

### Manual Docker Compose Commands

If you need to run Docker Compose commands manually:

```bash
# Start all services
docker compose -p localai \
  -f 00-infrastructure/docker-compose.yml \
  -f 01-data/supabase/docker-compose.yml \
  -f 01-data/qdrant/docker-compose.yml \
  -f 01-data/neo4j/docker-compose.yml \
  -f 02-compute/docker-compose.yml \
  -f 03-apps/docker-compose.yml \
  --profile gpu-nvidia \
  up -d

# Stop all services
docker compose -p localai \
  -f 00-infrastructure/docker-compose.yml \
  -f 01-data/supabase/docker-compose.yml \
  -f 01-data/qdrant/docker-compose.yml \
  -f 01-data/neo4j/docker-compose.yml \
  -f 02-compute/docker-compose.yml \
  -f 03-apps/docker-compose.yml \
  down
```

## Update Strategy

### Supabase Updates

Supabase compose files come from upstream. We use a script to:
1. Copy from `supabase/docker/docker-compose.yml`
2. Preserve customizations (network, volume paths)
3. Merge S3 configuration

This allows easy updates while maintaining our customizations.

### Other Service Updates

For other services, simply update image tags in their compose files. No script needed because we control these files entirely.

### Update Individual Stack

```bash
# Update infrastructure stack
cd 00-infrastructure
docker compose -p localai -f docker-compose.yml pull
docker compose -p localai -f docker-compose.yml up -d

# Update compute stack
cd 02-compute
docker compose -p localai -f docker-compose.yml --profile gpu-nvidia pull
docker compose -p localai -f docker-compose.yml --profile gpu-nvidia up -d
```

### Update All Stacks

```bash
python start_services.py --profile gpu-nvidia
```

## Migration Strategy

### Backward Compatibility

The old `docker-compose.yml` file is archived in `archive/` for reference, but:
- `start_services.py` no longer uses it
- All new deployments use modular files
- Old deployments can migrate by running the startup script

### No Breaking Changes

The startup script (`start_services.py`) maintains the same interface:
- Same command-line arguments
- Same behavior from user perspective
- Internal implementation changed to use modular files

## Troubleshooting

### Network Issues

If services can't communicate, verify the network exists:

```bash
docker network inspect ai-network
```

### Volume Issues

Check volume locations:

```bash
docker volume ls | grep localai
docker volume inspect <volume-name>
```

### Service Dependencies

Ensure dependent services are running:

```bash
docker ps --format "table {{.Names}}\t{{.Status}}"
```

## Future Considerations

### Potential Improvements

1. **Service Discovery**: Could add Consul or similar for dynamic service discovery
2. **Health Checks**: Could add more comprehensive health checking across services
3. **Service Mesh**: Could add Istio or Linkerd for advanced networking features
4. **Configuration Management**: Could use Helm charts or similar for more complex deployments

### Current Limitations

1. **Manual Dependency Management**: `depends_on` must be manually configured
2. **No Service Discovery**: Services must know container names
3. **Static Configuration**: Compose files are static (no dynamic service discovery)

These limitations are acceptable for the current use case and keep the architecture simple.

## References

- [Docker Compose Multiple Files](https://docs.docker.com/compose/extends/#multiple-compose-files)
- [Docker Compose Profiles](https://docs.docker.com/compose/profiles/)
- [Docker Compose Networks](https://docs.docker.com/compose/networking/)
- [Docker Compose Dependencies](https://docs.docker.com/compose/compose-file/compose-file-v3/#depends_on)
