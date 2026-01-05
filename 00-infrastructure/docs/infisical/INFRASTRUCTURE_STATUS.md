# Infrastructure Stack Status

## Overview

The infrastructure stack provides core connectivity, security, and secret management services:
- **Caddy**: Reverse proxy for all services
- **Cloudflared**: Cloudflare Tunnel for secure external access
- **Redis**: Main Redis instance for n8n and other services
- **Infisical**: Secret management (PostgreSQL, Redis, Backend)

## Current Configuration

### Services

| Service | Status | Description |
|---------|--------|-------------|
| caddy | ✅ Running | Reverse proxy on port 80 |
| redis | ✅ Running | Main Redis for n8n and services |
| infisical-redis | ✅ Running | Redis for Infisical |
| infisical-db | ✅ Running | PostgreSQL for Infisical |
| infisical-backend | ✅ Running | Infisical secret management API |
| cloudflared | ✅ Running | Cloudflare Tunnel (waits if token missing) |

### Directory Structure

```
00-infrastructure/
├── docker-compose.yml          # Main compose file
├── config/
│   ├── Caddyfile               # Reverse proxy configuration
│   ├── caddy-addon/            # Caddy addons (empty, for future use)
│   ├── networks.yml            # Network definition (reference)
│   ├── docker-compose.override.private.yml
│   └── docker-compose.override.public.yml
└── docs/                       # Documentation
```

### caddy-addon Directory

**Status**: Empty directory (only `.gitkeep`)

**Why Keep It:**
- Caddyfile line 108 imports: `import /etc/caddy/addons/*.conf`
- Placeholder for future Caddy addons/plugins
- No harm in keeping an empty directory

**Action**: Keep for future Caddy addons/plugins

## Environment Variables

### Required

- `INFISICAL_POSTGRES_PASSWORD` - PostgreSQL password for Infisical
- `INFISICAL_ENCRYPTION_KEY` - Encryption key for Infisical
- `INFISICAL_AUTH_SECRET` - Authentication secret for Infisical

### Optional

- `CLOUDFLARE_TUNNEL_TOKEN` - Cloudflare Tunnel token (cloudflared will wait if missing)

## Launch Commands

### Recommended: Use start-stack.sh
```bash
cd /home/jaewilson07/GitHub/local-ai-packaged
./start-stack.sh infrastructure
```

### Or: Use start_services.py
```bash
python start_services.py --profile cpu
```

### Or: Manual docker compose
```bash
docker compose -p localai -f 00-infrastructure/docker-compose.yml --env-file .env up -d
```

## Verification

### Check Service Status
```bash
docker compose -p localai -f 00-infrastructure/docker-compose.yml --env-file .env ps
```

### View Logs
```bash
# All services
docker compose -p localai -f 00-infrastructure/docker-compose.yml --env-file .env logs -f

# Specific service
docker compose -p localai -f 00-infrastructure/docker-compose.yml --env-file .env logs caddy
```

## Cloudflare Tunnel Setup

### Automated Setup (Recommended)
```bash
python setup/cloudflare/setup_tunnel.py
```

### Manual Setup
1. Get tunnel token from Cloudflare dashboard
2. Add to `.env`: `CLOUDFLARE_TUNNEL_TOKEN=your_token_here`

**Note**: Cloudflared will start but wait if token is not set. This is fine for local development.

## Troubleshooting

### Services Not Starting

1. **Check environment variables**:
   ```bash
   grep -E "INFISICAL|CLOUDFLARE" .env
   ```

2. **Check network exists**:
   ```bash
   docker network ls | grep ai-network
   ```

3. **Check logs**:
   ```bash
   docker compose -p localai -f 00-infrastructure/docker-compose.yml --env-file .env logs
   ```

### Missing Password

If `infisical-db` is failing:
```bash
echo "INFISICAL_POSTGRES_PASSWORD=$(openssl rand -base64 32)" >> .env
```

Then restart:
```bash
./start-stack.sh infrastructure
```

## Related Documentation

- [Architecture Overview](./ARCHITECTURE.md)
- [Quick Start Guide](./QUICK_START.md)
- [Stack Management](./STACK_MANAGEMENT.md)
- [Cloudflare Setup](./cloudflare/setup.md)
- [Infisical Setup](../../docs/infisical/setup.md)
- [Google SSO Setup](./GOOGLE_SSO_SETUP.md)

