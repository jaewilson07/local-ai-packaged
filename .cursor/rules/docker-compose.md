# Docker Compose Rules

Applies to all `docker-compose*.yml` files.

## Service Definition Pattern

```yaml
x-service-name: &service-name
  image: image:tag
  container_name: service-name
  restart: unless-stopped
  networks:
    - default  # ai-network
  healthcheck:
    test: ["CMD", "curl", "-f", "http://127.0.0.1:PORT/health"]
```

## Volume Paths

- MUST use full paths from project root (e.g., `./03-apps/flowise/data`)
- Never use relative paths from service folder

## Health Checks

- Use `127.0.0.1` instead of `localhost` to avoid IPv6 issues
- Use `nc -z 127.0.0.1 PORT` for TCP checks when curl unavailable

## Common Mistakes

- Port conflicts: Use environment variables
- Network isolation: All services must use `ai-network`
- Secret exposure: Never commit `.env` files
- One-time services: Use `restart: "no"`
