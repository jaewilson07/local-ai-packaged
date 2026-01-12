# Caddy Quick Reference Guide

## Common Operations

### Validate Configuration
```bash
docker exec caddy caddy validate --config /etc/caddy/Caddyfile
```

### Reload Configuration (without downtime)
```bash
docker exec caddy caddy reload --config /etc/caddy/Caddyfile
```

### View Logs
```bash
# All logs
docker logs caddy

# Follow logs in real-time
docker logs -f caddy

# Last 50 lines
docker logs caddy --tail 50

# Filter for errors
docker logs caddy 2>&1 | grep -i error
```

### Check Container Status
```bash
docker ps --filter "name=caddy" --format "{{.Names}}\t{{.Status}}"
```

### Restart Caddy
```bash
docker restart caddy
```

### Test Security Headers
```bash
# Test from localhost
curl -I http://localhost:80 -H "Host: infisical.datacrew.space"

# Test specific service
curl -I http://localhost:80 -H "Host: n8n.datacrew.space"
```

## Environment Variables

Set these in `.env` file or docker-compose.yml:

```bash
# Logging level (INFO, WARN, ERROR, DEBUG)
CADDY_LOG_LEVEL=INFO

# Infisical CORS origin
INFISICAL_SITE_URL=https://infisical.datacrew.space

# Service hostnames (for local development)
N8N_HOSTNAME=:8001
WEBUI_HOSTNAME=:8002
FLOWISE_HOSTNAME=:8003
OLLAMA_HOSTNAME=:8004
SUPABASE_HOSTNAME=:8005
NEO4J_HOSTNAME=:8008
COMFYUI_HOSTNAME=:8009
QDRANT_HOSTNAME=:8010
```

## Troubleshooting

### Caddy Won't Start
1. Check logs: `docker logs caddy --tail 50`
2. Validate config: `docker exec caddy caddy validate --config /etc/caddy/Caddyfile`
3. Check environment variables: `docker exec caddy env | grep HOSTNAME`

### 404 Errors
- Ensure the `Host` header matches a configured hostname
- Check if the service is running: `docker ps`
- Verify DNS/hosts file if using domain names

### CORS Errors (Infisical)
1. Check `INFISICAL_SITE_URL` matches the frontend URL
2. Verify browser is sending correct `Origin` header
3. Check Caddy logs for CORS-related errors

### Timeout Errors
- Check if service has extended timeouts configured
- Increase timeout values in Caddyfile if needed
- Verify backend service is responding

### Permission Denied (Logs)
- Use stdout logging (already configured)
- If file logging needed, ensure proper permissions on log directory

## Security Best Practices

### Enable Debug Logging (Temporarily)
```bash
# Set environment variable
docker compose -f 00-infrastructure/docker-compose.yml -p localai \
  exec caddy sh -c 'export CADDY_LOG_LEVEL=DEBUG && caddy reload'

# Remember to set back to INFO after troubleshooting
```

### Test Rate Limiting (When Implemented)
```bash
# Use Apache Bench to test rate limits
ab -n 100 -c 10 http://localhost:80/api/auth/login \
  -H "Host: infisical.datacrew.space"
```

### Monitor Security Events
```bash
# Watch for 4xx/5xx errors
docker logs -f caddy | grep -E '"status":(4|5)[0-9]{2}'

# Watch for large request bodies
docker logs -f caddy | grep -i "request body"
```

## Configuration Snippets

### Add New Service

1. Add to `:80` block (for Cloudflare Tunnel):
```caddyfile
@myservice host myservice.datacrew.space
handle @myservice {
    import security_headers_base
    import csp_standard
    request_body {
        max_size 10MB
    }
    reverse_proxy myservice:port {
        import standard_proxy
        import standard_timeouts
    }
}
```

2. Add environment variable block (for local development):
```caddyfile
{$MYSERVICE_HOSTNAME} {
    import security_headers_base
    import csp_standard
    request_body {
        max_size 10MB
    }
    reverse_proxy myservice:port {
        import standard_proxy
        import standard_timeouts
    }
}
```

3. Add environment variable to docker-compose.yml:
```yaml
environment:
  - MYSERVICE_HOSTNAME=${MYSERVICE_HOSTNAME:-:8011}
```

### Customize Security Headers for Specific Service
```caddyfile
@myservice host myservice.datacrew.space
handle @myservice {
    # Override default CSP
    header {
        Content-Security-Policy "default-src 'self'; script-src 'self';"
    }
    import security_headers_base
    # ... rest of configuration
}
```

## Performance Tuning

### Adjust Timeouts
```caddyfile
# For very long-running operations
(extra_long_timeouts) {
    transport http {
        read_timeout 600s
        write_timeout 600s
    }
}
```

### Enable Response Buffering (if needed)
```caddyfile
reverse_proxy backend:port {
    flush_interval -1  # Disable streaming
}
```

## Useful Commands

### Format Caddyfile
```bash
docker exec caddy caddy fmt --overwrite /etc/caddy/Caddyfile
```

### Show Adapted JSON Config
```bash
docker exec caddy caddy adapt --config /etc/caddy/Caddyfile
```

### Test Specific Route
```bash
# Test with curl
curl -v http://localhost:80 \
  -H "Host: n8n.datacrew.space" \
  -H "X-Forwarded-Proto: https"
```

## Emergency Procedures

### Quick Rollback
```bash
# 1. Restore from git
git checkout HEAD -- 00-infrastructure/caddy/Caddyfile

# 2. Reload Caddy
docker exec caddy caddy reload --config /etc/caddy/Caddyfile
```

### Disable Specific Service
```bash
# Comment out the service block in Caddyfile
# Then reload:
docker exec caddy caddy reload --config /etc/caddy/Caddyfile
```

### Emergency Stop
```bash
docker stop caddy
```

## Additional Resources

- [Caddy Documentation](https://caddyserver.com/docs/)
- [Caddyfile Syntax](https://caddyserver.com/docs/caddyfile)
- [Reverse Proxy Guide](https://caddyserver.com/docs/caddyfile/directives/reverse_proxy)
- [Security Headers](https://caddyserver.com/docs/caddyfile/directives/header)
