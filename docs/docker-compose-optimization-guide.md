# Docker Compose Optimization Guide

## Overview

This document describes the optimization patterns implemented across all Docker Compose files in this project. These optimizations follow 2024 best practices and improve consistency, maintainability, and security.

## Shared Configuration Files

All compose files now use shared configuration files located in `00-infrastructure/base/`:

### 1. networks.yml
- **Purpose**: Defines the external `ai-network` used by all services
- **Usage**: Include in all compose files to eliminate network duplication
- **Benefit**: Single source of truth for network configuration

```yaml
include:
  - ../00-infrastructure/base/networks.yml
```

### 2. logging.yml
- **Purpose**: Standard logging configurations
- **Anchors**:
  - `*logging-json`: Standard logging (1MB max, 1 file)
  - `*logging-json-verbose`: Verbose logging (10MB max, 3 files)
- **Usage**: Apply to services using `logging: *logging-json`

### 3. security.yml
- **Purpose**: Security hardening templates following principle of least privilege
- **Anchors**:
  - `*security-hardened`: Basic hardening (drop all capabilities)
  - `*security-network`: For services needing NET_BIND_SERVICE
  - `*security-usergroup`: For services needing user/group management
  - `*security-chown`: For services needing chown operations
- **Usage**: Apply to services using `<<: *security-network`

### 4. healthchecks.yml
- **Purpose**: Standard health check timing patterns
- **Anchors**:
  - `*healthcheck-http`: Standard HTTP services (30s interval)
  - `*healthcheck-db`: Database services (10s interval)
  - `*healthcheck-fast`: Lightweight services (5s interval)
  - `*healthcheck-slow`: Heavy services (60s interval)
- **Usage**: Combine with test command:
```yaml
healthcheck:
  test: ["CMD", "curl", "-f", "http://localhost:8080/health"]
  <<: *healthcheck-http
```

### 5. volumes.yml
- **Purpose**: Documents volume strategy (named vs bind mounts)
- **Pattern**:
  - Named volumes: Databases, caches (Docker-managed)
  - Bind mounts: Configs, development data (host-accessible)

## Health Checks

All critical services now have health checks:

### Added Health Checks
- **caddy**: HTTP endpoint check on port 80
- **ollama**: API tags endpoint check
- **comfyui**: Root endpoint check
- **n8n**: /healthz endpoint check
- **flowise**: /api/v1/ping endpoint check
- **open-webui**: /health endpoint check
- **qdrant**: /health endpoint check
- **neo4j**: HTTP endpoint check on port 7474

### Health Check Benefits
1. **Proper dependency ordering**: Services wait for dependencies to be healthy
2. **Better monitoring**: Integration with Docker health status
3. **Automatic recovery**: Restart unhealthy containers
4. **Rolling updates**: Only update healthy services

## Environment Variable Consolidation

Shared environment variable groups reduce duplication:

### Apps Stack (03-apps/docker-compose.yml)
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
  REDIS_TLS_ENABLED: ${REDIS_TLS_ENABLED:-false}
```

### Usage
```yaml
services:
  n8n:
    environment:
      <<: *database-env
      # n8n-specific vars
      
  langfuse-worker:
    environment:
      <<: *database-env
      <<: *redis-env
      # langfuse-specific vars
```

## Security Hardening

Applied principle of least privilege across all stacks:

### Infrastructure Stack
- **caddy**: Uses `*security-network` (NET_BIND_SERVICE capability)
- **redis**: Uses `*security-usergroup` (SETGID, SETUID, DAC_OVERRIDE)
- **cloudflared**: No special capabilities needed

### Apps Stack
- **searxng**: Uses `*security-chown` (CHOWN, SETGID, SETUID)

### Security Benefits
1. **Reduced attack surface**: Drop all capabilities by default
2. **Principle of least privilege**: Add only required capabilities
3. **No new privileges**: Prevent privilege escalation
4. **Consistent security posture**: Same patterns across all services

## Logging Standardization

All services use consistent logging configuration:

### Pattern
```yaml
services:
  my-service:
    logging: *logging-json
```

### Benefits
1. **Consistent log rotation**: 1MB max size, 1 file retention
2. **Prevent disk exhaustion**: Automatic log cleanup
3. **Easy troubleshooting**: Same format across all services
4. **Centralized configuration**: Update once, apply everywhere

## Dependency Management

Improved dependency declarations:

### Before
```yaml
depends_on:
  - caddy
```

### After
```yaml
depends_on:
  caddy:
    condition: service_healthy
```

### Benefits
1. **Wait for readiness**: Don't start until dependencies are healthy
2. **Faster startup**: No artificial sleep delays
3. **Better reliability**: Automatic retry on dependency failure

## File Organization

### Base Configuration Directory
```
00-infrastructure/base/
├── networks.yml          # Network definitions
├── logging.yml           # Logging configurations
├── security.yml          # Security templates
├── healthchecks.yml      # Health check patterns
└── volumes.yml           # Volume strategy documentation
```

### Include Pattern
All compose files include relevant base configs:
```yaml
include:
  - ../00-infrastructure/base/networks.yml
  - ../00-infrastructure/base/logging.yml
  - ../00-infrastructure/base/security.yml
  - ../00-infrastructure/base/healthchecks.yml
```

## Migration Guide

### For New Services
1. Include base configuration files
2. Apply appropriate security anchor
3. Add health check with appropriate timing anchor
4. Use logging anchor for consistent log rotation
5. Follow volume strategy (named for data, bind for configs)

### Example New Service
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
      test: ["CMD", "curl", "-f", "http://localhost:8080/health"]
      <<: *healthcheck-http
    volumes:
      - my-service-data:/data
      - ./my-service/config:/etc/my-service:ro
    networks:
      - default

volumes:
  my-service-data:
```

## Testing

After making changes, validate with:

```bash
# Validate compose files
docker compose -f 00-infrastructure/docker-compose.yml config

# Check service health
docker compose -p localai ps

# View health status
docker inspect --format='{{.State.Health.Status}}' <container-name>
```

## Benefits Summary

1. **Reduced Duplication**: Network declarations reduced from 19 files to 1
2. **Improved Security**: Consistent security hardening across all services
3. **Better Observability**: Health checks on all critical services
4. **Easier Maintenance**: Update shared configs once, apply everywhere
5. **Consistent Patterns**: Same approach across all stacks
6. **Better Documentation**: Clear patterns and standards

## References

- [Docker Compose Include](https://docs.docker.com/compose/compose-file/14-include/)
- [Docker Compose Health Checks](https://docs.docker.com/compose/compose-file/05-services/#healthcheck)
- [Docker Security Best Practices](https://docs.docker.com/engine/security/)
- [YAML Anchors and Aliases](https://yaml.org/spec/1.2.2/#3222-anchors-and-aliases)

