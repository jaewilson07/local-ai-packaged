# Quick Start Guide

## Modular Docker Compose Architecture

This project uses a **modular Docker Compose architecture** where each component has its own compose file in the `compose/` directory. This eliminates conflicts and makes updates easier.

## Project Structure

```
compose/
  ├── core/          # Caddy, Cloudflared, Redis, Postgres
  ├── supabase/      # Supabase services
  ├── infisical/     # Infisical secret management
  ├── ai/            # Ollama, ComfyUI
  ├── workflow/      # n8n, Flowise
  ├── data/          # Qdrant, Neo4j, MongoDB, MinIO
  ├── observability/ # Langfuse, ClickHouse
  └── web/           # Open WebUI, SearXNG
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
4. Start all services using modular compose files

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
  -f compose/core/docker-compose.yml \
  -f compose/supabase/docker-compose.yml \
  -f compose/infisical/docker-compose.yml \
  -f compose/ai/docker-compose.yml \
  -f compose/workflow/docker-compose.yml \
  -f compose/data/docker-compose.yml \
  -f compose/observability/docker-compose.yml \
  -f compose/web/docker-compose.yml \
  --profile gpu-nvidia \
  up -d

# Stop all services
docker compose -p localai \
  -f compose/core/docker-compose.yml \
  -f compose/supabase/docker-compose.yml \
  -f compose/infisical/docker-compose.yml \
  -f compose/ai/docker-compose.yml \
  -f compose/workflow/docker-compose.yml \
  -f compose/data/docker-compose.yml \
  -f compose/observability/docker-compose.yml \
  -f compose/web/docker-compose.yml \
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

Edit the compose file in `compose/[component]/docker-compose.yml` and update image tags.

## Troubleshooting

### Services Won't Start

1. Check if containers are already running: `docker ps -a`
2. Stop and remove: `python start_services.py --profile gpu-nvidia` (stops existing containers)
3. Check logs: `docker compose -p localai logs [service-name]`

### Network Issues

All services use the `localai_default` network. Verify it exists:
```bash
docker network inspect localai_default
```

### Volume Issues

Volumes are shared across compose files. Check volumes:
```bash
docker volume ls | grep localai
```

## More Information

- **Full Architecture Documentation**: [docs/modular-compose-architecture.md](modular-compose-architecture.md)
- **Migration Notes**: [MIGRATION_NOTES.md](../../MIGRATION_NOTES.md)
- **Archive**: [archive/README.md](../../archive/README.md)

