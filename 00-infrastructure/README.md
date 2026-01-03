# Infrastructure Configuration

This directory contains infrastructure-level configuration files.

## Files

- **Caddyfile** - Caddy reverse proxy configuration for all services
- **caddy-addon/** - Caddy addon configurations
- **networks.yml** - Docker network definition (reference file)
- **docker-compose.override.private.yml** - Private/local environment overrides
- **docker-compose.override.public.yml** - Public/production environment overrides

## Usage

These files are automatically referenced by:
- `00-infrastructure/docker-compose.yml` - References Caddyfile and caddy-addon
- `start_services.py` - References override files based on environment

## Network Setup

To create the network defined in `networks.yml`:

```bash
docker network create ai-network
```

