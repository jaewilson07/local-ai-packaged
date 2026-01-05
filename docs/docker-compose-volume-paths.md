# Docker Compose Volume Path Resolution

## Problem

When Docker Compose is executed from the project root with multiple `-f` flags pointing to compose files in different directories, **all relative paths in volume mounts are resolved relative to the current working directory (project root)**, not relative to each compose file's location.

### Example of the Issue

Given this command executed from project root:
```bash
docker compose -p localai \
  -f 00-infrastructure/docker-compose.yml \
  -f 01-data/supabase/docker-compose.yml \
  -f 02-compute/docker-compose.yml \
  -f 03-apps/docker-compose.yml \
  up -d
```

If `03-apps/docker-compose.yml` contains:
```yaml
volumes:
  - ./flowise/data:/root/.flowise
```

Docker will look for `./flowise/data` relative to the **project root**, not relative to `03-apps/`.

This caused files to be created in incorrect locations like:
- `00-infrastructure/flowise/` (wrong)
- `00-infrastructure/comfyui/` (wrong)
- `00-infrastructure/data/` (wrong)

Instead of the correct locations:
- `03-apps/flowise/` (correct)
- `02-compute/comfyui/` (correct)
- `01-data/*/data/` (correct)

## Solution

All relative volume paths in compose files must include the full path from the project root.

### Correct Pattern

**Before (incorrect):**
```yaml
# In 03-apps/docker-compose.yml
volumes:
  - ./flowise/data:/root/.flowise
```

**After (correct):**
```yaml
# In 03-apps/docker-compose.yml
volumes:
  - ./03-apps/flowise/data:/root/.flowise
```

## Changes Made

### 1. Infrastructure Stack (`00-infrastructure/docker-compose.yml`)

```yaml
# Caddy volumes
volumes:
  - ./00-infrastructure/caddy/Caddyfile:/etc/caddy/Caddyfile:ro
  - ./00-infrastructure/caddy/caddy-addon:/etc/caddy/addons:ro
```

### 2. Data Stack

#### Supabase (`01-data/supabase/docker-compose.yml`)
```yaml
volumes:
  # Config files from upstream
  - ./01-data/supabase/upstream/docker/volumes/api/kong.yml:/home/kong/temp.yml:ro,z
  - ./01-data/supabase/upstream/docker/volumes/db/realtime.sql:/docker-entrypoint-initdb.d/migrations/99-realtime.sql:Z
  # ... (all upstream volume references)
  
  # Data directories
  - ./01-data/supabase/data/minio:/data
  - ./01-data/supabase/data/storage:/var/lib/storage:z
  - ./01-data/supabase/data/functions:/home/deno/functions:Z
  - ./01-data/supabase/data/db:/var/lib/postgresql/data:Z
```

#### MinIO (`01-data/minio/docker-compose.yml`)
```yaml
volumes:
  - ./01-data/minio/data:/data
```

#### Neo4j (`01-data/neo4j/docker-compose.yml`)
```yaml
volumes:
  - ./01-data/neo4j/data/data:/data
  - ./01-data/neo4j/data/logs:/logs
```

#### Qdrant and MongoDB
These services use **named volumes** (not bind mounts), so they are not affected by this issue:
```yaml
volumes:
  - qdrant_storage:/qdrant/storage  # Named volume (no path issue)
  - mongodb_data:/data/db            # Named volume (no path issue)
```

### 3. Compute Stack (`02-compute/docker-compose.yml`)

```yaml
# Ollama
volumes:
  - ./02-compute/ollama/data:/root/.ollama

# ComfyUI
volumes:
  - ./02-compute/comfyui/data:/comfy/mnt
  - ./02-compute/comfyui/data/basedir:/basedir
  - ./02-compute/comfyui/scripts:/provision:ro
```

### 4. Apps Stack (`03-apps/docker-compose.yml`)

```yaml
# n8n
volumes:
  - ./03-apps/n8n/config/import:/backup
  - ./03-apps/n8n/data/home:/home/node/.n8n
  - ./03-apps/n8n/data/backup:/backup
  - ./shared:/data/shared  # Shared folder at project root

# Flowise
volumes:
  - ./03-apps/flowise/data:/root/.flowise

# Open WebUI
volumes:
  - ./03-apps/open-webui/data:/app/backend/data

# SearXNG
volumes:
  - ./03-apps/searxng/config:/etc/searxng:rw

# ClickHouse
volumes:
  - ./03-apps/clickhouse/data:/var/lib/clickhouse
  - ./03-apps/clickhouse/logs:/var/log/clickhouse-server
```

## Verification

To verify all paths are correct, run:
```bash
# Check for any relative paths that don't start with stack directories
rg '^\s*-\s*\./(?!0[0-3]-)' --type yaml
```

This should return no results if all paths are correctly prefixed.

## Best Practices

1. **Always use full paths from project root** in volume mounts when using multi-file compose
2. **Use named volumes** for data that doesn't need to be directly accessible from the host
3. **Use bind mounts with full paths** for configuration files and data that needs host access
4. **Test compose file changes** by checking where Docker actually creates directories

## Related Documentation

- [Docker Compose File Reference - Volumes](https://docs.docker.com/compose/compose-file/07-volumes/)
- [AGENTS.md - Folder Structure Standards](../AGENTS.md#folder-structure-standards)

## Migration Notes

If you have existing data in the wrong locations (e.g., `00-infrastructure/flowise/`), you'll need to:

1. Stop all services
2. Move the data to the correct location:
   ```bash
   # Example: Move flowise data
   mv 00-infrastructure/flowise/data 03-apps/flowise/data
   
   # Example: Move comfyui data
   mv 00-infrastructure/comfyui/data 02-compute/comfyui/data
   ```
3. Start services with the corrected compose files

---

**Last Updated**: 2026-01-04
**Issue**: Files being created in `00-infrastructure/` instead of correct stack directories
**Resolution**: Updated all volume paths to use full paths from project root

