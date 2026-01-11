# Stack Management Cheat Sheet

Quick reference for managing the AI Homelab stacks.

## Network

The external `ai-network` must be created before starting services:

```bash
docker network create ai-network
```

Or use the networks.yml definition (for reference).

## Starting Services

### Start All Stacks

```bash
python start_services.py --profile gpu-nvidia
```

Profiles:
- `cpu` - CPU-only services
- `gpu-nvidia` - NVIDIA GPU services
- `gpu-amd` - AMD GPU services

### Start Individual Stacks

```bash
# Infrastructure (cloudflared, caddy, redis)
python start_services.py --stack infrastructure

# Infisical (infisical-backend, infisical-db, infisical-redis)
python start_services.py --stack infisical

# Data (supabase, qdrant, neo4j, mongodb, minio)
python start_services.py --stack data

# Compute (ollama, comfyui) - requires profile
python start_services.py --stack compute --profile gpu-nvidia

# Apps (n8n, flowise, open-webui, searxng, langfuse, clickhouse)
python start_services.py --stack apps

# Lambda (lambda-server)
python start_services.py --stack lambda
```

## Stopping Services

### Stop All Stacks

```bash
python start_services.py --action stop
```

### Stop Individual Stacks

```bash
# Stop infrastructure
python start_services.py --action stop --stack infrastructure

# Stop infisical
python start_services.py --action stop --stack infisical

# Stop data
python start_services.py --action stop --stack data

# Stop compute
python start_services.py --action stop --stack compute

# Stop apps
python start_services.py --action stop --stack apps

# Stop lambda
python start_services.py --action stop --stack lambda
```

## Updating Services

### Update All Stacks

```bash
python start_services.py --profile gpu-nvidia
```

### Update Individual Stack

```bash
# Update infrastructure
python start_services.py --stack infrastructure

# Update infisical
python start_services.py --stack infisical

# Update data
python start_services.py --stack data

# Update compute (with profile)
python start_services.py --stack compute --profile gpu-nvidia

# Update apps
python start_services.py --stack apps

# Update lambda
python start_services.py --stack lambda
```

## Viewing Logs

```bash
# Infrastructure stack
docker compose -p localai-infra logs -f

# Infisical stack
docker compose -p localai-infisical logs -f

# Data stack
docker compose -p localai-data logs -f

# Compute stack
docker compose -p localai-compute logs -f

# Apps stack
docker compose -p localai-apps logs -f

# Lambda stack
docker compose -p localai-lambda logs -f

# Specific service (example)
docker compose -p localai-apps logs -f n8n
docker compose -p localai-compute logs -f ollama
docker compose -p localai-infisical logs -f infisical-backend
```

## Service URLs

Once services are running, access them via:

- **n8n**: `http://localhost:5678` or via Caddy hostname
- **Open WebUI**: `http://localhost:8080` or via Caddy hostname
- **Flowise**: `http://localhost:3001` or via Caddy hostname
- **Langfuse**: `http://localhost:3000` or via Caddy hostname
- **Supabase Studio**: `http://localhost:8000` or via Caddy hostname
- **Infisical**: `http://localhost:8080` (infisical-backend) or via Caddy hostname

## Troubleshooting

### Check Network

```bash
docker network inspect ai-network
```

### Check Running Services

```bash
docker ps --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}"
```

### Check Service Health

```bash
# Check specific service
docker ps | grep <service-name>
docker logs <container-name>
```

### Restart Service

```bash
docker restart <container-name>
```

## Stack Dependencies

Start order (if starting manually):
1. **Infrastructure** - Network, reverse proxy (creates `ai-network`)
2. **Infisical** - Secret management (optional, can start later)
3. **Data** - Databases must be ready
4. **Compute** - AI inference services
5. **Apps** - Application services depend on data and compute
6. **Lambda** - API server depends on data and compute

## Project Names

Each stack uses its own Docker Compose project name:

- `localai-infra` - Infrastructure services
- `localai-infisical` - Infisical secret management
- `localai-data` - Data persistence services
- `localai-compute` - AI compute services
- `localai-apps` - Application services
- `localai-lambda` - Lambda API server

All stacks share the external `ai-network` for inter-service communication.
