# Infrastructure Stack - AGENTS.md

> **Override**: This file extends [../AGENTS.md](../AGENTS.md). Infrastructure-specific rules take precedence.

## Component Identity

**Stack**: `00-infrastructure`  
**Purpose**: Foundation services for networking, reverse proxy, secrets management, and caching  
**Docker Compose**: `00-infrastructure/docker-compose.yml` (stack-level compose for shared services)  
**Network**: Creates and manages external network `ai-network` (used by all stacks)

## Folder Structure

**Stack-Level Files**:
- `docker-compose.yml` - Stack-level compose (caddy, infisical-backend, infisical-db, infisical-redis, redis)
- `AGENTS.md` - This file (stack-specific rules)
- `README.md` - Infrastructure overview
- `docs/` - Stack-wide documentation and ADRs
- `networks.yml` - Network definition
- `docker-compose.override.*.yml` - Environment overrides

**Service-Specific Folders**:
- `caddy/` - Caddy service
  - `Caddyfile` - Main reverse proxy configuration
  - `caddy-addon/` - Custom Caddy modules
- `cloudflared/` - Cloudflare Tunnel service
  - `docs/` - Cloudflare Tunnel-specific documentation
  - (Note: Service defined in stack-level compose, folder for organization)

**Refactoring Notes**:
- Services in stack-level compose (caddy, infisical, redis) don't need individual folders unless they have service-specific configs/docs
- Service-specific folders (like `cloudflared/`) should contain service-specific documentation and configs
- When adding new services, decide: stack-level compose (shared) vs service-specific folder (independent)

## Services

### Caddy (Reverse Proxy)
- **Image**: `docker.io/library/caddy:2-alpine`
- **Container**: `caddy`
- **Config**: `00-infrastructure/caddy/Caddyfile`
- **Ports**: Exposes 80 only (443 handled by Cloudflare Tunnel if used)
- **Volumes**: `caddy-data`, `caddy-config`
- **Key Files**:
  - `00-infrastructure/caddy/Caddyfile` - Main reverse proxy configuration
  - `00-infrastructure/caddy/caddy-addon/` - Custom Caddy modules

**Patterns**:
- Uses environment variable templating for hostnames (e.g., `${N8N_HOSTNAME:-:8001}`)
- Supports both port-based (`:8001`) and domain-based (`n8n.example.com`) routing
- Capabilities: `NET_BIND_SERVICE` only (hardened)
- **Security**: Configured to trust Cloudflare IP ranges (when using Tunnel)
  - All traffic comes through Cloudflare network
  - Caddy forwards `Cf-Access-Jwt-Assertion` header to Lambda server
  - See [Auth Project Security](../04-lambda/server/projects/auth/SECURITY.md) for details

### Cloudflare Tunnel
- **Image**: `cloudflare/cloudflared:latest`
- **Container**: `cloudflared`
- **Config**: Token-based (no config file needed)
- **Environment**: `CLOUDFLARE_TUNNEL_TOKEN` (required for tunnel mode)
- **Dependencies**: Waits for `caddy` service

**Patterns**:
- Protocol: HTTP/2
- No port forwarding required (works behind NAT)
- Token stored in environment variable (never commit to repo)

### Cloudflare Access (Authentication)

**Purpose**: Provides authentication for Lambda API server and other protected services

**Setup**:
- Access applications created via Cloudflare API or dashboard
- Lambda API application: `api.datacrew.space`
- Uses Google OAuth as IdP (configured in Cloudflare Access)

**Key Configuration**:
- **AUD Tag**: Application Audience Tag (64-char hex identifier)
- **Retrieval**: Use `get-lambda-api-aud-tag.py` script
- **Environment Variable**: `CLOUDFLARE_AUD_TAG` (set in Lambda server)
- **Auth Domain**: `CLOUDFLARE_AUTH_DOMAIN` (e.g., `https://team.cloudflareaccess.com`)

**Scripts**:
- `get-lambda-api-aud-tag.py` - Retrieves AUD tag from Cloudflare API
- `setup-lambda-api-access.py` - Creates Access application and links to tunnel route

**Documentation**: See [Cloudflare Access Setup Guide](../docs/CLOUDFLARE_ACCESS_CLI_SETUP.md)

### Infisical (Secrets Management)
- **Image**: `infisical/infisical:latest`
- **Container**: `infisical-backend`
- **Database**: Dedicated PostgreSQL (`infisical-db`)
- **Cache**: Dedicated Redis (`infisical-redis`)
- **Port**: 8080 (internal), exposed via Caddy
- **Key Files**:
  - `00-infrastructure/infisical/docs/` - Setup documentation

**Patterns**:
- **Encryption Key**: `INFISICAL_ENCRYPTION_KEY` (16-byte hex)
- **Auth Secret**: `INFISICAL_AUTH_SECRET` (32-byte base64)
- **Database**: Separate from Supabase (dedicated PostgreSQL instance)
- **Health Check**: `/api/health` endpoint
- **Trust Proxy**: Enabled for reverse proxy support
- **HTTPS**: Enabled (behind Cloudflare Tunnel)

**Integration**:
- CLI authentication: `infisical login` (interactive) or machine identity (env vars)
- Secret export: `infisical export --format=dotenv` (used by `start_services.py`)
- Web UI: First user creates admin account at `/admin/signup`

### Redis (Valkey)
- **Image**: `valkey/valkey:8`
- **Container**: `redis`
- **Purpose**: General-purpose cache (separate from Infisical Redis)
- **Port**: 6379 (internal only)
- **Volume**: `valkey-data`

**Patterns**:
- Used by n8n and Langfuse for job queues
- Health check: `redis-cli ping`
- Capabilities: `SETGID`, `SETUID`, `DAC_OVERRIDE` only

## Scripts

Location: `00-infrastructure/scripts/`

### Infisical Management

#### `manage-infisical.py`
- **Purpose**: Manage Infisical state (nuclear reset or data wipe).
- **Usage**: `python3 00-infrastructure/scripts/manage-infisical.py [reset-infra|reset-data]`

#### `sync-env-to-infisical.py`
- **Purpose**: Sync secrets from `.env` file to Infisical.
- **Usage**: `python3 00-infrastructure/scripts/sync-env-to-infisical.py [--dry-run] [--env-file .env]`

#### `sync-infisical-to-env.py`
- **Purpose**: Sync secrets from Infisical to `.env` file.
- **Usage**: `python3 00-infrastructure/scripts/sync-infisical-to-env.py [--dry-run] [--env-file .env]`

#### `check-env-sync-status.py`
- **Purpose**: Check sync status between `.env` file and Infisical.
- **Usage**: `python3 00-infrastructure/scripts/check-env-sync-status.py [--env-file .env] [--verbose]`

### Cloudflare Management

#### `check-cloudflare-config.py`
- **Purpose**: Diagnose and fix Cloudflare configuration issues (SSL/TLS mode, page rules, transform rules, etc.).
- **Usage**: `python3 00-infrastructure/scripts/check-cloudflare-config.py [--fix-ssl] [--create-page-rule] [--purge-cache] [--fix-all]`

#### `manage-cloudflare-access.py`
- **Purpose**: Manage unified Cloudflare Access policies across all applications.
- **Usage**: `python3 00-infrastructure/scripts/manage-cloudflare-access.py [--create-policy] [--list] [--apply-to-all]`

#### `setup-cloudflare-tunnel-routes.py`
- **Purpose**: Configure or remove Cloudflare Tunnel public hostnames.
- **Usage**:
  - Add routes: `python3 00-infrastructure/scripts/setup-cloudflare-tunnel-routes.py`
  - Remove route: `python3 00-infrastructure/scripts/setup-cloudflare-tunnel-routes.py --remove HOSTNAME`

#### `get-lambda-api-aud-tag.py`
- **Purpose**: Retrieve the AUD tag from Cloudflare Access application for Lambda API.
- **Usage**: `python3 00-infrastructure/scripts/get-lambda-api-aud-tag.py`
- **Output**: Prints the AUD tag to stdout (copy to `CLOUDFLARE_AUD_TAG` environment variable)

### Infrastructure Management

#### `update_images.py`
- **Purpose**: Update Docker images for all stacks without restarting services.
- **Usage**: `python3 00-infrastructure/scripts/update_images.py [--profile cpu|gpu-nvidia|gpu-amd|none] [--environment private|public] [--skip-dhi-auth]`

## Architecture Patterns

### Network Creation
```yaml
networks:
  default:
    external: true
    name: ai-network
```

**Critical**: This stack must start first to create `ai-network`. Other stacks depend on it.

### Service Dependencies
- `cloudflared` → depends on `caddy`
- `infisical-backend` → depends on `infisical-db` and `infisical-redis` (health checks)

### Environment Variable Strategy
- **Shared**: `.env.global` (non-sensitive defaults)
- **Sensitive**: `.env` (secrets) or Infisical
- **Override Files**:
  - `00-infrastructure/docker-compose.override.private.yml` (dev)
  - `00-infrastructure/docker-compose.override.public.yml` (prod)

### Caddyfile Configuration
- **Dynamic Hostnames**: Uses environment variable substitution
- **TLS**: Automatic via Cloudflare Tunnel or Let's Encrypt (if direct DNS)
- **Routing**: Each service gets a hostname or port-based route

## Key Files & Search Hints

```bash
# Find Caddy configuration
cat 00-infrastructure/caddy/Caddyfile

# Find Infisical setup docs
ls 00-infrastructure/docs/infisical/

# Find environment variable usage
rg -n "INFISICAL_\|CLOUDFLARE_" 00-infrastructure/

# Find network configuration
rg -n "ai-network" --type yaml
```

## Testing & Validation

### Health Checks
```bash
# Caddy
docker exec caddy caddy validate --config /etc/caddy/Caddyfile

# Infisical
docker exec infisical-backend wget --spider http://localhost:8080/api/health

# Redis
docker exec redis redis-cli ping
```

### Common Issues
1. **Network Not Found**: Ensure infrastructure stack starts first
2. **Caddy Config Errors**: Check Caddyfile syntax with `caddy validate`
3. **Infisical Auth Failures**: Verify encryption keys and database connection
4. **Cloudflare Tunnel**: Verify token is valid and not expired
5. **Cloudflare Access**: If Lambda server JWT validation fails, verify AUD tag matches Access application. Use `get-lambda-api-aud-tag.py` to retrieve correct value.

## Do's and Don'ts

### ✅ DO
- Use environment variables for all hostnames
- Keep Caddyfile syntax valid (test with `caddy validate`)
- Separate Infisical database from Supabase
- Use health checks for service dependencies
- Hardened capabilities (drop ALL, add only needed)

### ❌ DON'T
- Hardcode hostnames in Caddyfile
- Commit Cloudflare Tunnel tokens
- Mix Infisical Redis with main Redis
- Create new networks (use `ai-network`)
- Expose ports unnecessarily (use `expose:` not `ports:`)
- Commit Cloudflare Access AUD tags (store in environment variables or Infisical)
- Bypass Caddy security (always trust Cloudflare IPs when using Tunnel)

## Domain Dictionary

- **Hostname**: Service identifier (port-based `:8001` or domain `service.example.com`)
- **ai-network**: External Docker network shared by all stacks
- **Caddy**: Reverse proxy and TLS termination
- **Cloudflare Tunnel**: Zero-trust tunnel (no port forwarding)
- **Infisical**: Secrets management platform (self-hosted)
- **Valkey**: Redis-compatible cache (fork of Redis)

---

**See Also**: [../AGENTS.md](../AGENTS.md) for universal rules

