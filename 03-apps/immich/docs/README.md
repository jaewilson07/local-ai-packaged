# Immich Setup and Usage

Immich is a self-hosted photo and video backup solution integrated into the local-ai-packaged infrastructure.

> **Status:** Infrastructure PRD completed and validated (2025-01-27). See [`.cursor/PRDS/infrastructure_psec`](../../../.cursor/PRDS/infrastructure_psec) for requirements and validation details.

## Architecture

Immich consists of the following services:

- **immich-server**: Main API server (port 2283)
- **immich-microservices**: Background jobs for video transcoding (with optional GPU acceleration)
- **immich-machine-learning**: Face detection using Buffalo_L model
- **immich-postgres**: Dedicated PostgreSQL 14+ database
- **immich-typesense**: Text search engine for metadata search

## Quick Start

### Prerequisites

1. Infrastructure stack must be running (Caddy, Redis)
2. Environment variables configured in `.env` or Infisical:
   - `IMMICH_DB_PASSWORD` - PostgreSQL password
   - `IMMICH_TYPESENSE_API_KEY` - Typesense API key (generate with `openssl rand -hex 32`)
   - `IMMICH_HOSTNAME` - Hostname for Caddy routing (e.g., `immich.datacrew.space` or `:2283`)

### Starting Immich

Immich is part of the `apps` stack and will start automatically:

```bash
# Start with GPU acceleration (recommended for video transcoding)
python start_services.py --profile gpu-nvidia --stack apps

# Start without GPU (CPU-only transcoding)
python start_services.py --profile cpu --stack apps
```

### Accessing Immich

- **Local**: `http://localhost:2283` (if `IMMICH_HOSTNAME=:2283`)
- **Production**: `https://immich.datacrew.space` (via Cloudflare Tunnel and Caddy)

### First-Time Setup

1. Navigate to the Immich web interface
2. Register the first user (this user will have admin privileges)
3. Configure storage templates and settings as needed

## Configuration

### Environment Variables

Key environment variables (see `.env_sample` for complete list):

- `IMMICH_VERSION` - Immich version (default: `release`)
- `IMMICH_DB_USERNAME` - PostgreSQL username (default: `postgres`)
- `IMMICH_DB_PASSWORD` - PostgreSQL password (required)
- `IMMICH_DB_DATABASE_NAME` - Database name (default: `immich`)
- `IMMICH_TYPESENSE_API_KEY` - Typesense API key (required)
- `IMMICH_HOSTNAME` - Caddy hostname routing

### Storage

- **Media Library**: `03-apps/immich/data/library` (mapped to `/usr/src/app/upload` in container)
- **PostgreSQL Data**: `03-apps/immich/data/postgres`
- **Typesense Data**: `03-apps/immich/data/typesense`
- **Model Cache**: `03-apps/immich/data/model-cache` (for machine learning models)

### GPU Acceleration

For video transcoding, GPU acceleration is recommended. See [GPU_SETUP.md](GPU_SETUP.md) for details.

### Typesense Search

Typesense provides fast text search for metadata. See [TYPESENSE_SETUP.md](TYPESENSE_SETUP.md) for configuration details.

## Service Management

### Check Service Status

```bash
docker compose -p localai-apps ps
```

### View Logs

```bash
# All Immich services
docker compose -p localai-apps logs -f immich-server immich-microservices-gpu immich-machine-learning

# Specific service
docker compose -p localai-apps logs -f immich-server
```

### Restart Services

```bash
# Restart all Immich services
docker compose -p localai-apps restart immich-server immich-microservices-gpu immich-machine-learning immich-postgres immich-typesense

# Restart specific service
docker compose -p localai-apps restart immich-server
```

## Health Checks

All services include health checks:

- **immich-server**: HTTP check on `/api/server-info/ping`
- **immich-postgres**: PostgreSQL readiness check
- **immich-typesense**: HTTP check on `/health`

## Backup

### Database Backup

```bash
docker exec immich-postgres pg_dump -U postgres immich > immich_backup_$(date +%Y%m%d).sql
```

### Media Backup

The media library is stored in `03-apps/immich/data/library`. Backup this directory regularly.

## Troubleshooting

### Services Not Starting

1. Check logs: `docker compose -p localai-apps logs immich-server`
2. Verify environment variables are set correctly
3. Ensure infrastructure stack (Caddy, Redis) is running
4. Check database health: `docker exec immich-postgres pg_isready -U postgres`

### Video Transcoding Issues

1. Verify GPU is accessible: `docker exec immich-microservices-gpu nvidia-smi`
2. Check microservices logs for transcoding errors
3. Ensure GPU profile is used: `--profile gpu-nvidia`

### Search Not Working

1. Verify Typesense is running: `docker compose -p localai-apps ps immich-typesense`
2. Check Typesense API key is set correctly
3. Review Typesense logs: `docker compose -p localai-apps logs immich-typesense`

## Integration with Infrastructure

### Caddy Reverse Proxy

Immich is accessible via Caddy at the configured hostname. Large uploads (up to 500MB) are supported.

### Cloudflare Tunnel

For external access, configure a Cloudflare Tunnel route:
- Subdomain: `immich`
- Domain: `datacrew.space`
- Service URL: `http://caddy:80`
- Host Header: `immich.datacrew.space`

### Infisical Secrets

Store sensitive configuration in Infisical:
- `IMMICH_DB_PASSWORD`
- `IMMICH_TYPESENSE_API_KEY`

These will be automatically exported to `.env.infisical` when using `start_services.py --use-infisical`.

## References

- [Immich Documentation](https://docs.immich.app/)
- [Immich GitHub](https://github.com/immich-app/immich)
