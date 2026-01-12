# Quick Start Guide

## Stack-Based Docker Compose Architecture

This project uses a **stack-based Docker Compose architecture** where services are organized into logical stacks (infrastructure, data, compute, apps). Each stack has its own `docker-compose.yml` file in a dedicated directory.

## Project Structure

```
/ai-homelab
├── 00-infrastructure/  # cloudflared, caddy, infisical, redis
├── 01-data/           # supabase, qdrant, neo4j
├── 02-compute/        # ollama, comfyui
└── 03-apps/           # n8n, flowise, open-webui, searxng, langfuse, etc.
```

## Starting Services

### Basic Startup

```bash
python start_services.py --profile gpu-nvidia
```

This will:
1. Stop any existing containers
2. Authenticate with Infisical (if enabled)
3. Pull latest images
4. Start all services using stack-based compose files

### Profiles

- `--profile cpu` - CPU-only services (default)
- `--profile gpu-nvidia` - NVIDIA GPU services
- `--profile gpu-amd` - AMD GPU services

### Environments

- `--environment private` - Local development with port bindings (default)
- `--environment public` - Production deployment without port bindings

### Infisical Options

- `--use-infisical` - Use Infisical for secrets (default: True)
- `--skip-infisical` - Use .env file directly

## Manual Docker Compose Commands

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

# View logs
docker compose -p localai logs -f [service-name]

# Check status
docker compose -p localai ps
```

## Updating Services

### Supabase

```bash
python scripts/update-supabase-compose.py
```

### Other Services

Edit the compose file in the appropriate stack directory (e.g., `00-infrastructure/docker-compose.yml`) and update image tags.

## Troubleshooting

### Services Won't Start

1. Check if containers are already running: `docker ps -a`
2. Stop and remove: `python start_services.py --profile gpu-nvidia` (stops existing containers)
3. Check logs: `docker compose -p localai logs [service-name]`

### Network Issues

All services use the external `ai-network`. Verify it exists:
```bash
docker network inspect ai-network
```

If it doesn't exist, create it:
```bash
docker network create ai-network
```

### Volume Issues

Volumes are shared across compose files. Check volumes:
```bash
docker volume ls | grep localai
```

## More Information

- **Full Architecture Documentation**: [ARCHITECTURE.md](./ARCHITECTURE.md)
- **Stack Management**: [STACK_MANAGEMENT.md](./STACK_MANAGEMENT.md)
- **Infrastructure Status**: [INFRASTRUCTURE_STATUS.md](./INFRASTRUCTURE_STATUS.md)
- **Migration Notes**: [migration/REFACTOR_SUMMARY.md](./migration/REFACTOR_SUMMARY.md)
