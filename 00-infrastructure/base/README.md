# Shared Base Configuration Files

This directory contains shared configuration files used across all Docker Compose files in the project.

## Purpose

These files eliminate duplication and provide consistent patterns for:
- Network configuration
- Logging configuration
- Security hardening
- Health check timing
- Volume strategy

## Files

### networks.yml
Defines the external `ai-network` used by all services.

**Usage:**
```yaml
include:
  - ../00-infrastructure/base/networks.yml
```

### logging.yml
Standard logging configurations with YAML anchors.

**Anchors:**
- `*logging-json` - Standard logging (1MB max, 1 file)
- `*logging-json-verbose` - Verbose logging (10MB max, 3 files)

**Usage:**
```yaml
include:
  - ../00-infrastructure/base/logging.yml

services:
  my-service:
    logging: *logging-json
```

### security.yml
Security hardening templates following principle of least privilege.

**Anchors:**
- `*security-hardened` - Basic hardening (drop all capabilities)
- `*security-network` - For services needing NET_BIND_SERVICE
- `*security-usergroup` - For services needing user/group management
- `*security-chown` - For services needing chown operations

**Usage:**
```yaml
include:
  - ../00-infrastructure/base/security.yml

services:
  my-service:
    <<: *security-hardened
```

### healthchecks.yml
Standard health check timing patterns.

**Anchors:**
- `*healthcheck-http` - Standard HTTP services (30s interval)
- `*healthcheck-db` - Database services (10s interval)
- `*healthcheck-fast` - Lightweight services (5s interval)
- `*healthcheck-slow` - Heavy services (60s interval)

**Usage:**
```yaml
include:
  - ../00-infrastructure/base/healthchecks.yml

services:
  my-service:
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8080/health"]
      <<: *healthcheck-http
```

### volumes.yml
Documents the volume strategy (named vs bind mounts).

**Strategy:**
- **Named volumes**: Databases, caches (Docker-managed)
- **Bind mounts**: Configs, development data (host-accessible)

## Benefits

1. **Reduced Duplication**: Network declarations reduced from 19 files to 1
2. **Easier Maintenance**: Update once, apply everywhere
3. **Consistent Patterns**: Same approach across all stacks
4. **Better Security**: Standardized security hardening
5. **Improved Observability**: Consistent health check patterns

## Usage Pattern

All Docker Compose files should include relevant base configs:

```yaml
# At the top of your docker-compose.yml
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
    networks:
      - default
```

## Path Adjustments

The include paths are relative to the compose file location:

- **Infrastructure stack**: `base/networks.yml`
- **Data stack**: `../../00-infrastructure/base/networks.yml`
- **Compute stack**: `../00-infrastructure/base/networks.yml`
- **Apps stack**: `../00-infrastructure/base/networks.yml`

## Documentation

For complete details, see:
- [docker-compose-patterns skill](../../.cursor/skills/docker-compose-patterns/SKILL.md)
- [Root AGENTS.md](../../AGENTS.md)

## Version

Created: 2026-01-04  
Last Updated: 2026-01-04  
Docker Compose Version: 2.20+
