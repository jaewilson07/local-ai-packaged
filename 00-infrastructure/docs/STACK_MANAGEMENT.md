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
# Infrastructure (cloudflared, caddy, infisical, redis)
./start-stack.sh infrastructure

# Data (supabase, qdrant, neo4j)
./start-stack.sh data

# Compute (ollama, comfyui) - requires profile
./start-stack.sh compute gpu-nvidia

# Apps (n8n, flowise, open-webui, searxng, langfuse, etc.)
./start-stack.sh apps
```

## Stopping Services

### Stop All Stacks

```bash
docker compose -p localai \
  -f 00-infrastructure/docker-compose.yml \
  -f 01-data/supabase/docker-compose.yml \
  -f 01-data/qdrant/docker-compose.yml \
  -f 01-data/neo4j/docker-compose.yml \
  -f 02-compute/docker-compose.yml \
  -f 03-apps/docker-compose.yml \
  down
```

### Stop Individual Stacks

```bash
# Stop infrastructure
./stop-stack.sh infrastructure

# Stop data
./stop-stack.sh data

# Stop compute
./stop-stack.sh compute

# Stop apps
./stop-stack.sh apps
```

## Updating Services

### Update All Stacks

```bash
python start_services.py --profile gpu-nvidia
```

### Update Individual Stack

```bash
# Update infrastructure
cd 00-infrastructure
docker compose -p localai -f docker-compose.yml pull
docker compose -p localai -f docker-compose.yml up -d

# Update compute (with profile)
cd 02-compute
docker compose -p localai -f docker-compose.yml --profile gpu-nvidia pull
docker compose -p localai -f docker-compose.yml --profile gpu-nvidia up -d
```

## Viewing Logs

```bash
# All services
docker compose -p localai logs -f

# Specific service
docker compose -p localai logs -f n8n
docker compose -p localai logs -f ollama
docker compose -p localai logs -f infisical-backend
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
1. **Infrastructure** - Network, reverse proxy, secrets
2. **Data** - Databases must be ready
3. **Compute** - AI inference services
4. **Apps** - Application services depend on data and compute


