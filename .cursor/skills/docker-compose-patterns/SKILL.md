---
name: docker-compose-patterns
description: Apply Docker Compose best practices including health checks, security hardening, logging configuration, and shared base files. Use when adding new services, configuring health checks, applying security templates, or optimizing Docker Compose files.
---

# Docker Compose Patterns

Guide for applying Docker Compose best practices in this project, including health checks, security hardening, logging, and shared configuration patterns.

## Shared Configuration Files

All compose files should use shared configuration files from `00-infrastructure/base/`:

### 1. networks.yml

**Purpose**: Defines the external `ai-network` used by all services

**Usage**:
```yaml
include:
  - ../00-infrastructure/base/networks.yml
```

### 2. logging.yml

**Purpose**: Standard logging configurations

**Anchors**:
- `*logging-json`: Standard logging (1MB max, 1 file)
- `*logging-json-verbose`: Verbose logging (10MB max, 3 files)

**Usage**:
```yaml
services:
  my-service:
    logging: *logging-json
```

### 3. security.yml

**Purpose**: Security hardening templates following principle of least privilege

**Anchors**:
- `*security-hardened`: Basic hardening (drop all capabilities)
- `*security-network`: For services needing NET_BIND_SERVICE
- `*security-usergroup`: For services needing user/group management
- `*security-chown`: For services needing chown operations

**Usage**:
```yaml
services:
  my-service:
    <<: *security-hardened
```

### 4. healthchecks.yml

**Purpose**: Standard health check timing patterns

**Anchors**:
- `*healthcheck-http`: Standard HTTP services (30s interval)
- `*healthcheck-db`: Database services (10s interval)
- `*healthcheck-fast`: Lightweight services (5s interval)
- `*healthcheck-slow`: Heavy services (60s interval)

**Usage**:
```yaml
services:
  my-service:
    healthcheck:
      test: ["CMD", "curl", "-f", "http://127.0.0.1:8080/health"]
      <<: *healthcheck-http
```

## Adding a New Service

### Step-by-Step Process

1. **Include base configuration files**:
```yaml
include:
  - ../00-infrastructure/base/networks.yml
  - ../00-infrastructure/base/logging.yml
  - ../00-infrastructure/base/security.yml
  - ../00-infrastructure/base/healthchecks.yml
```

2. **Define service with security and logging**:
```yaml
services:
  my-service:
    image: my-service:latest
    container_name: my-service
    restart: unless-stopped
    <<: *security-hardened
    logging: *logging-json
    healthcheck:
      test: ["CMD", "curl", "-f", "http://127.0.0.1:8080/health"]
      <<: *healthcheck-http
    volumes:
      - my-service-data:/data
      - ./my-service/config:/etc/my-service:ro
    networks:
      - default

volumes:
  my-service-data:
```

### Complete Example

```yaml
include:
  - ../00-infrastructure/base/networks.yml
  - ../00-infrastructure/base/logging.yml
  - ../00-infrastructure/base/security.yml
  - ../00-infrastructure/base/healthchecks.yml

services:
  my-service:
    image: my-service:latest
    container_name: my-service
    restart: unless-stopped
    <<: *security-hardened
    logging: *logging-json
    healthcheck:
      test: ["CMD", "curl", "-f", "http://127.0.0.1:8080/health"]
      <<: *healthcheck-http
    environment:
      - CONFIG_VAR=${CONFIG_VAR:-default}
    volumes:
      - my-service-data:/data
      - ./my-service/config:/etc/my-service:ro
    networks:
      - default
    depends_on:
      other-service:
        condition: service_healthy

volumes:
  my-service-data:
```

## Health Check Patterns

### CRITICAL: Use 127.0.0.1, Not localhost

**Always use `127.0.0.1`** instead of `localhost` in health checks to avoid IPv6 connection issues:

```yaml
# CORRECT
healthcheck:
  test: ["CMD", "curl", "-f", "http://127.0.0.1:8080/health"]

# WRONG - may fail due to IPv6
healthcheck:
  test: ["CMD", "curl", "-f", "http://localhost:8080/health"]
```

### Health Check by Service Type

**HTTP Services** (curl/wget available):
```yaml
healthcheck:
  test: ["CMD", "curl", "-f", "http://127.0.0.1:8080/health"]
  <<: *healthcheck-http
```

**HTTP Services** (wget only, no curl):
```yaml
healthcheck:
  test: ["CMD", "wget", "--no-verbose", "--tries=1", "--spider", "http://127.0.0.1:8080/health"]
  <<: *healthcheck-http
```

**TCP Port Check** (no HTTP endpoint):
```yaml
healthcheck:
  test: ["CMD", "nc", "-z", "127.0.0.1", "5000"]
  <<: *healthcheck-fast
```

**Database Services**:
```yaml
# PostgreSQL
healthcheck:
  test: ["CMD-SHELL", "pg_isready -U postgres -h 127.0.0.1"]
  <<: *healthcheck-db

# MongoDB
healthcheck:
  test: ["CMD", "mongosh", "--eval", "db.adminCommand('ping')"]
  <<: *healthcheck-db

# Redis
healthcheck:
  test: ["CMD", "redis-cli", "ping"]
  <<: *healthcheck-fast
```

## Security Hardening

### Choosing the Right Security Template

| Template | Use When |
|----------|----------|
| `*security-hardened` | Default for most services |
| `*security-network` | Service needs to bind to ports < 1024 |
| `*security-usergroup` | Service needs to change user/group |
| `*security-chown` | Service needs to change file ownership |

### Examples by Service Type

**Standard Web Service**:
```yaml
services:
  web-app:
    <<: *security-hardened
```

**Reverse Proxy (needs port 80/443)**:
```yaml
services:
  caddy:
    <<: *security-network  # Needs NET_BIND_SERVICE
```

**Service with User Management**:
```yaml
services:
  redis:
    <<: *security-usergroup  # Needs SETGID, SETUID
```

**SearXNG (needs chown on startup)**:
```yaml
services:
  searxng:
    <<: *security-chown  # Needs CHOWN, SETGID, SETUID
```

## Volume Path Resolution

### CRITICAL RULE

**MUST use full paths from project root**, not relative paths from compose file location:

```yaml
# CORRECT - full path from project root
volumes:
  - ./03-apps/flowise/data:/data

# WRONG - relative to compose file (will break)
volumes:
  - ./flowise/data:/data
```

### Volume Types

**Named Volumes** (Docker-managed, for databases/caches):
```yaml
volumes:
  my-service-data:

services:
  my-service:
    volumes:
      - my-service-data:/data
```

**Bind Mounts** (host-accessible, for configs/development):
```yaml
services:
  my-service:
    volumes:
      - ./my-service/config:/etc/my-service:ro  # Read-only config
      - ./my-service/data:/data                  # Writable data
```

## Environment Variable Patterns

### Shared Environment Groups

Define reusable environment variable groups:

```yaml
x-database-env: &database-env
  DB_TYPE: postgresdb
  DB_POSTGRESDB_HOST: supabase-db
  DB_POSTGRESDB_USER: postgres
  DB_POSTGRESDB_PASSWORD: ${POSTGRES_PASSWORD}
  DB_POSTGRESDB_DATABASE: postgres

x-redis-env: &redis-env
  REDIS_HOST: ${REDIS_HOST:-redis}
  REDIS_PORT: ${REDIS_PORT:-6379}
  REDIS_AUTH: ${REDIS_AUTH:-LOCALONLYREDIS}

services:
  n8n:
    environment:
      <<: *database-env
      # n8n-specific vars
      N8N_ENCRYPTION_KEY: ${N8N_ENCRYPTION_KEY}

  langfuse-worker:
    environment:
      <<: *database-env
      <<: *redis-env
      # langfuse-specific vars
```

### Default Values

Always provide defaults for optional variables:

```yaml
environment:
  - REQUIRED_VAR=${REQUIRED_VAR}           # Will error if not set
  - OPTIONAL_VAR=${OPTIONAL_VAR:-default}  # Uses default if not set
```

## Dependency Management

### Health-Based Dependencies

```yaml
services:
  app:
    depends_on:
      database:
        condition: service_healthy
      cache:
        condition: service_started  # Use when health check isn't critical
```

### When to Use Each Condition

| Condition | Use When |
|-----------|----------|
| `service_healthy` | Service must be ready to accept connections |
| `service_started` | Service can start even if dependency is unhealthy |

## Service Anchor Pattern

Define service base configuration as anchors:

```yaml
x-service-base: &service-base
  restart: unless-stopped
  logging: *logging-json
  networks:
    - default

services:
  service-cpu:
    <<: *service-base
    profiles: ["cpu"]
    image: my-service:cpu

  service-gpu:
    <<: *service-base
    profiles: ["gpu-nvidia"]
    image: my-service:gpu
    deploy:
      resources:
        reservations:
          devices:
            - driver: nvidia
              count: all
              capabilities: [gpu]
```

## Validation

After making changes, validate with:

```bash
# Validate compose file syntax
docker compose -f path/to/docker-compose.yml config

# Check service health
docker compose -p project-name ps

# View health status of specific container
docker inspect --format='{{.State.Health.Status}}' container-name
```

## Common Mistakes to Avoid

1. **Using `localhost` in health checks** - Use `127.0.0.1` instead
2. **Wrong volume paths** - Use full paths from project root
3. **Missing health checks** - All critical services should have health checks
4. **Hardcoded secrets** - Always use environment variables
5. **Exposed database ports** - Use internal network only
6. **Missing security hardening** - Apply appropriate security template

## References

- [Docker Compose Include](https://docs.docker.com/compose/compose-file/14-include/)
- [Docker Compose Health Checks](https://docs.docker.com/compose/compose-file/05-services/#healthcheck)
- [Docker Security Best Practices](https://docs.docker.com/engine/security/)
- [YAML Anchors and Aliases](https://yaml.org/spec/1.2.2/#3222-anchors-and-aliases)
