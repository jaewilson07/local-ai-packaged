# Stack-Based Docker Compose Architecture

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

## Directory Structure

```
/ai-homelab
├── .env.global               # Non-sensitive globals (DOMAIN_NAME, TZ)
├── config/networks.yml        # Defines external 'ai-network'
│
├── 00-infrastructure/        # Stack: Connectivity & Security
│   ├── docker-compose.yml    # cloudflared, caddy, infisical-backend, infisical-db, infisical-redis, redis
│   ├── docs/                 # Infrastructure documentation
│   └── config/               # Cloudflare tunnel configs
│
├── 01-data/                  # Stack: Persistence (Databases)
│   ├── supabase/             # Supabase (multi-container setup)
│   │   ├── docker-compose.yml
│   │   └── docs/
│   ├── qdrant/               # Qdrant Vector DB
│   │   └── docker-compose.yml
│   └── neo4j/                # Neo4j Graph DB
│       └── docker-compose.yml
│
├── 02-compute/               # Stack: Heavy AI Inference (GPU)
│   ├── docker-compose.yml    # ollama, comfyui
│   └── data/                 # Model weights/outputs
│       ├── ollama/           # Ollama models
│       └── comfyui/          # ComfyUI models, workflows, config
│
└── 03-apps/                  # Stack: Agentic Workflows & UI
    └── docker-compose.yml    # n8n, flowise, open-webui, searxng, langfuse, clickhouse, mongodb, minio
```

## Stack Details

### Infrastructure Stack (`00-infrastructure/docker-compose.yml`)

- **Services**: `cloudflared`, `caddy`, `infisical-backend`, `infisical-db`, `infisical-redis`, `redis`
- **Network**: Uses external `ai-network`
- **Purpose**: Core connectivity, reverse proxy, secret management, and shared Redis
- **Key Features**:
  - Cloudflare Tunnel for secure ingress
  - Caddy as reverse proxy routing to all services
  - Infisical with dedicated PostgreSQL (separate from Supabase)
  - Redis for n8n and other services

### Data Stack (`01-data/`)

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

- **Services**: `ollama-cpu`, `ollama-gpu`, `ollama-gpu-amd`, `comfyui-cpu`, `comfyui-gpu`, `comfyui-gpu-amd`
- **Uses Profiles**: CPU vs GPU variants using Docker Compose profiles
- **Network**: Uses external `ai-network`
- **GPU Support**: NVIDIA and AMD GPU passthrough configured
- **Data**: Models stored in `02-compute/data/ollama/` and `02-compute/data/comfyui/`

### Apps Stack (`03-apps/docker-compose.yml`)

- **Services**: `n8n`, `flowise`, `open-webui`, `searxng`, `langfuse-web`, `langfuse-worker`, `clickhouse`, `mongodb`, `minio`
- **Network**: Uses external `ai-network`
- **Dependencies**: 
  - n8n → `ollama:11434`, `supabase-db:5432`
  - open-webui → `ollama:11434`, `searxng:8080`
  - langfuse → `supabase-db:5432`, `minio:9000`, `redis:6379`, `clickhouse:8123`

## Network Configuration

All stacks use the external Docker network `ai-network`:

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

## Volume Configuration

Volumes are defined in each compose file where they're used. Docker Compose automatically merges volume definitions when multiple `-f` flags are used, so volumes with the same name are shared across services.

### Volume Types

- **Named Volumes**: Used for most services (e.g., `ollama_storage`, `n8n_storage`)
- **Bind Mounts**: Used for configuration and data that needs to be directly accessible (e.g., Neo4j, Supabase volumes)

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
./start-stack.sh infrastructure

# Start data stack
./start-stack.sh data

# Start compute stack (with GPU profile)
./start-stack.sh compute gpu-nvidia

# Start apps stack
./start-stack.sh apps
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

## Profiles

The compute stack uses Docker Compose profiles to support different hardware configurations:

- **`cpu`**: CPU-only services (default)
- **`gpu-nvidia`**: NVIDIA GPU services
- **`gpu-amd`**: AMD GPU services

## Service Dependencies

Services communicate via the `ai-network` using container names:

- **n8n** → `ollama:11434`, `supabase-db:5432`
- **open-webui** → `ollama:11434`, `searxng:8080`
- **langfuse** → `supabase-db:5432`, `minio:9000`, `redis:6379`, `clickhouse:8123`
- **infisical-backend** → `infisical-db:5432`, `infisical-redis:6379`

## Secret Management

Sensitive secrets are managed via Infisical:

- **Infisical Backend**: Stores and manages all secrets
- **Infisical Database**: Dedicated PostgreSQL instance (separate from Supabase)
- **Secret Injection**: `start_services.py` exports secrets from Infisical to `.env.infisical` for use by services
- **Fallback**: If Infisical is unavailable, services fall back to `.env` file

## Updating Services

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

## References

- [Docker Compose Multiple Files](https://docs.docker.com/compose/extends/#multiple-compose-files)
- [Docker Compose Profiles](https://docs.docker.com/compose/profiles/)
- [Docker Compose Networks](https://docs.docker.com/compose/networking/)
- [Docker Compose Dependencies](https://docs.docker.com/compose/compose-file/compose-file-v3/#depends_on)
