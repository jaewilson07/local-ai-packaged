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

## Domain Dictionary

- **Hostname**: Service identifier (port-based `:8001` or domain `service.example.com`)
- **ai-network**: External Docker network shared by all stacks
- **Caddy**: Reverse proxy and TLS termination
- **Cloudflare Tunnel**: Zero-trust tunnel (no port forwarding)
- **Infisical**: Secrets management platform (self-hosted)
- **Valkey**: Redis-compatible cache (fork of Redis)

---

**See Also**: [../AGENTS.md](../AGENTS.md) for universal rules

