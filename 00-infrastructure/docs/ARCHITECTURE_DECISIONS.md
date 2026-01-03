# Architecture Decisions

## Why Modular Docker Compose?

### Problem: The `include:` Directive Conflict

The original architecture used a single `docker-compose.yml` file with the `include:` directive to include Supabase compose files:

```yaml
include:
  - ./supabase/docker/docker-compose.yml
  - ./supabase/docker/docker-compose.s3.yml
```

This caused conflicts when:
- Starting services independently
- Using `docker compose down` 
- Trying to start Infisical separately
- Updating Supabase compose files

Error example:
```
services.storage conflicts with imported resource
```

### Solution: Stack-Based Compose Files

Each stack now has its own compose file in numbered directories:

```
00-infrastructure/docker-compose.yml
01-data/supabase/docker-compose.yml
01-data/qdrant/docker-compose.yml
01-data/neo4j/docker-compose.yml
02-compute/docker-compose.yml
03-apps/docker-compose.yml
```

Services are stitched together at runtime using multiple `-f` flags:

```bash
docker compose -p localai \
  -f 00-infrastructure/docker-compose.yml \
  -f 01-data/supabase/docker-compose.yml \
  -f 01-data/qdrant/docker-compose.yml \
  -f 01-data/neo4j/docker-compose.yml \
  -f 02-compute/docker-compose.yml \
  -f 03-apps/docker-compose.yml \
  ...
```

### Benefits

1. **No Conflicts**: Each compose file is independent until merged
2. **Easy Updates**: Update Supabase by running `scripts/update-supabase-compose.py`
3. **Better Organization**: Clear separation of concerns
4. **Flexible**: Easy to enable/disable components
5. **Docker Best Practice**: Aligns with Docker's recommended approach for large applications

## Network Architecture

### Single Shared Network

All services use the `localai_default` network:

- **Core compose file** creates the network (not external)
- **Other compose files** use it as external

This ensures all services can communicate with each other by container name.

### Why Not Multiple Networks?

A single network simplifies:
- Service discovery (containers can reference each other by name)
- Dependency management (`depends_on` works across compose files)
- Configuration (one network to manage)

## Volume Strategy

### Shared Volumes

Volumes are defined in each compose file where they're used. Docker Compose automatically merges volume definitions when multiple `-f` flags are used, so volumes with the same name are shared across services.

Example:
- `compose/core/docker-compose.yml` defines `valkey-data`
- `compose/infisical/docker-compose.yml` can reference `valkey-data` (if needed)
- Both reference the same volume

### Volume Path Resolution

Volume paths are relative to the compose file's location:

```yaml
# compose/supabase/docker-compose.yml
volumes:
  - ../../supabase/docker/volumes/db/data:/var/lib/postgresql/data:Z
```

This resolves to: `project_root/supabase/docker/volumes/db/data`

## Service Dependencies

### Using Service Names vs Container Names

**Critical distinction**:
- `depends_on` uses **service names** (e.g., `db`)
- Connection strings use **container names** (e.g., `supabase-db`)

Example:
```yaml
# compose/infisical/docker-compose.yml
services:
  infisical:
    depends_on:
      db:  # Service name from compose/supabase/docker-compose.yml
        condition: service_healthy
    environment:
      - DB_CONNECTION_URI=postgresql://postgres:${POSTGRES_PASSWORD}@supabase-db:5432/postgres
      # Container name (supabase-db) used in connection string
```

## Component Organization

### Why These Components?

Components are organized by function:

- **core**: Infrastructure services (Caddy, Cloudflared, Redis, Postgres)
- **supabase**: Database and backend services
- **infisical**: Secret management
- **ai**: AI/ML services (Ollama, ComfyUI)
- **workflow**: Automation (n8n, Flowise)
- **data**: Data stores (Qdrant, Neo4j, MongoDB, MinIO)
- **observability**: Monitoring (Langfuse, ClickHouse)
- **web**: User interfaces (Open WebUI, SearXNG)

### Why Not One File Per Service?

Grouping related services:
- Reduces number of files to manage
- Keeps related services together
- Makes it easier to understand dependencies
- Still provides enough granularity for updates

## Update Strategy

### Supabase Updates

Supabase compose files come from upstream. We use a script to:
1. Copy from `supabase/docker/docker-compose.yml`
2. Preserve customizations (network, volume paths)
3. Merge S3 configuration

This allows easy updates while maintaining our customizations.

### Other Service Updates

For other services, simply update image tags in their compose files. No script needed because we control these files entirely.

## Migration Strategy

### Backward Compatibility

The old `docker-compose.yml` file is archived in `archive/` for reference, but:
- `start_services.py` no longer uses it
- All new deployments use modular files
- Old deployments can migrate by running the startup script

### No Breaking Changes

The startup script (`start_services.py`) maintains the same interface:
- Same command-line arguments
- Same behavior from user perspective
- Internal implementation changed to use modular files

## Future Considerations

### Potential Improvements

1. **Service Discovery**: Could add Consul or similar for dynamic service discovery
2. **Health Checks**: Could add more comprehensive health checking across services
3. **Service Mesh**: Could add Istio or Linkerd for advanced networking features
4. **Configuration Management**: Could use Helm charts or similar for more complex deployments

### Current Limitations

1. **Manual Dependency Management**: `depends_on` must be manually configured
2. **No Service Discovery**: Services must know container names
3. **Static Configuration**: Compose files are static (no dynamic service discovery)

These limitations are acceptable for the current use case and keep the architecture simple.

