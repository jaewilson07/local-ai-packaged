# Known Issues

## Caddy Health Check Disabled

**Status**: Temporarily Disabled  
**Date**: 2026-01-04  
**Severity**: Medium

### Issue
Caddy has a pre-existing Caddyfile syntax error that prevents it from starting:
```
Error: adapting config using caddyfile: server block without any key is global configuration, and if used, it must be first
```

### Impact
- Caddy container restarts continuously
- Health check was added during optimization but had to be disabled
- Cloudflared dependency on caddy health check was blocking service startup

### Workaround
The health check has been commented out in `00-infrastructure/docker-compose.yml` to allow services to start:
```yaml
# Health check temporarily disabled due to pre-existing Caddyfile syntax error
# healthcheck:
#   test: ["CMD", "wget", "--no-verbose", "--tries=1", "--spider", "http://localhost:80/"]
#   <<: *healthcheck-fast
```

Cloudflared dependency changed from `condition: service_healthy` to simple dependency.

### Resolution Steps
1. Fix the Caddyfile syntax error (likely in `00-infrastructure/caddy/Caddyfile`)
2. The error indicates a global configuration block is not at the beginning of the file
3. Once fixed, uncomment the health check in the docker-compose.yml
4. Update cloudflared dependency back to `condition: service_healthy`

### Files Affected
- `00-infrastructure/caddy/Caddyfile` (needs fix)
- `00-infrastructure/docker-compose.yml` (health check commented out)

### Related
This is a pre-existing issue, not introduced by the Docker Compose optimization work.

---

## SearXNG Secret Key Generation Permission Error

**Status**: Warning (Non-blocking)  
**Date**: Pre-existing  
**Severity**: Low

### Issue
```
sed: couldn't open temporary file 03-apps/searxng/config/sed*: Permission denied
```

### Impact
- Warning message during startup
- Does not prevent services from starting
- Secret key generation may fail on first run

### Workaround
The `start_services.py` script detects if SearXNG is already running and skips secret generation.

### Resolution Steps
Manual secret key generation if needed:
```bash
# Linux
sed -i "s|ultrasecretkey|$(openssl rand -hex 32)|g" 03-apps/searxng/config/settings.yml

# macOS
sed -i '' "s|ultrasecretkey|$(openssl rand -hex 32)|g" 03-apps/searxng/config/settings.yml
```

---

## Orphan Infisical Containers

**Status**: Informational  
**Date**: 2026-01-04  
**Severity**: Low

### Issue
```
Found orphan containers ([infisical-backend infisical-db infisical-redis]) for this project.
```

### Impact
- Warning message during startup
- Does not affect functionality
- Infisical containers exist but are not part of current compose configuration

### Resolution Steps
```bash
docker compose -p localai down --remove-orphans
```

Or add Infisical back to the infrastructure stack if needed.

---

## Missing Environment Variables

**Status**: Informational  
**Date**: Pre-existing  
**Severity**: Low

### Issue
Warnings about missing environment variables:
- `SUPABASE_ANON_KEY`
- `SUPABASE_SERVICE_KEY`
- `FLOWISE_USERNAME`

### Impact
- Warning messages during startup
- Services default to blank strings
- May affect functionality if these are required

### Resolution Steps
Add missing variables to `.env` file or use Infisical for secret management.

---

Last Updated: 2026-01-04
