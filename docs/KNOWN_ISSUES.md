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

**Status**: Resolved  
**Date**: 2026-01-11  
**Severity**: Low

### Issue
```
Found orphan containers ([infisical-backend infisical-db infisical-redis]) for this project.
```

### Resolution
Infisical has been moved to an external standalone project at `/home/jaewilson07/GitHub/infisical-standalone`. If you see orphan container warnings, they are from the old local setup and can be safely removed:

```bash
docker compose -p localai down --remove-orphans
```

Infisical is now managed separately via the external project.

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

## Frontend Health Check IPv6 Issue

**Status**: Fixed  
**Date**: 2026-01-11  
**Severity**: Low

### Issue
Frontend health check was failing with "Connection refused" errors:
```
wget: can't connect to remote host: Connection refused
Connecting to localhost:3000 ([::1]:3000)
```

### Root Cause
Health check was using `localhost` which resolves to IPv6 (`[::1]`) first, but Next.js was only binding to IPv4 (`0.0.0.0`).

### Resolution
Changed health check to use `127.0.0.1` explicitly:
```yaml
healthcheck:
  test: ["CMD", "wget", "--no-verbose", "--tries=1", "--spider", "http://127.0.0.1:3000/api/health"]
```

### Files Affected
- `03-apps/docker-compose.yml` (frontend service health check)

### Related
This pattern should be applied to all health checks that use `localhost` - prefer `127.0.0.1` for IPv4-only services.

---

## Supabase Storage Health Check Failure

**Status**: Fixed  
**Date**: 2026-01-11  
**Severity**: Low

### Issue
`supabase-storage` service showed as unhealthy even though the service was running and listening on port 5000.

### Root Cause
The health check was using `nc -z localhost 5000`, but `localhost` resolves to IPv6 (`[::1]`) first, which may not be available or properly configured in the container. The service was listening on IPv4 (`0.0.0.0:5000`).

### Resolution
Changed health check to use `127.0.0.1` explicitly:
```yaml
healthcheck:
  test: ["CMD", "nc", "-z", "127.0.0.1", "5000"]
```

### Files Affected
- `01-data/supabase/docker-compose.yml` (storage service health check)

---

## Supabase Vector Health Check Failure

**Status**: Fixed  
**Date**: 2026-01-11  
**Severity**: Low

### Issue
`supabase-vector` service showed as unhealthy.

### Root Cause
Similar to storage service - `nc -z localhost 9001` health check was failing due to IPv6 resolution issues.

### Resolution
Changed health check to use `127.0.0.1` explicitly:
```yaml
healthcheck:
  test: ["CMD", "nc", "-z", "127.0.0.1", "9001"]
```

### Files Affected
- `01-data/supabase/docker-compose.yml` (vector service health check)

---

## Supabase Edge Functions Entrypoint Issue

**Status**: Fixed  
**Date**: 2026-01-11  
**Severity**: Low

### Issue
`supabase-edge-functions` service was in a restart loop:
```
Error: main worker boot error
Caused by: could not find an appropriate entrypoint
```

### Root Cause
1. The `--main-service` flag expects a **directory**, not a file path
2. The edge runtime requires the upstream main function router, not a simple function file
3. The data directory had a simple function instead of the router

### Resolution
1. **Fixed**: Changed command from `--main-service /home/deno/functions/main/index.ts` to `--main-service /home/deno/functions/main` (directory)
2. **Fixed**: Copied the upstream main function router from `01-data/supabase/upstream/docker/volumes/functions/main/index.ts` to `01-data/supabase/data/functions/main/index.ts`

The upstream main function is a router that loads other edge functions from subdirectories. Simple functions should be placed in subdirectories (e.g., `functions/hello/index.ts`), not in the main directory.

### Files Affected
- `01-data/supabase/docker-compose.yml` (functions service command - fixed)
- `01-data/supabase/data/functions/main/index.ts` (now uses upstream router - fixed)

### Verification
Service now starts successfully and logs show "main function started". Edge functions are operational.

---

## Discord Bot Port Conflict

**Status**: Fixed  
**Date**: 2026-01-11  
**Severity**: Medium

### Issue
Discord bot failed to start with port binding error:
```
Error response from daemon: failed to set up container networking:
driver failed programming external connectivity on endpoint discord-bot:
Bind for 127.0.0.1:8001 failed: port is already allocated
```

### Root Cause
Port 8001 was already allocated by Caddy (which uses ports 8001-8010 for internal routing). The discord-bot MCP server doesn't need external access.

### Resolution
Changed from `ports` to `expose` to only expose the port internally:
```yaml
expose:
  - "8001/tcp"  # MCP server port (internal network only)
```

### Files Affected
- `03-apps/docker-compose.yml` (discord-bot service)

### Related
MCP servers typically only need internal network access, not external port mapping.

---

Last Updated: 2026-01-11
