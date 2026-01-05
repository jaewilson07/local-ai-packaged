# Migration to Modular Docker Compose Architecture

## What Changed

The project has been migrated from a single `docker-compose.yml` file (using `include:` directive) to a modular architecture with separate compose files for each component.

## Old vs New

### Old Architecture
- Single `docker-compose.yml` with `include:` directive
- Supabase compose files included via `include:`
- Conflicts when starting services separately
- Harder to update individual services

### New Architecture
- Modular compose files in `compose/` subdirectories
- Each component has its own compose file
- Services stitched together using multiple `-f` flags
- No conflicts, easier updates, better organization

## File Locations

### Old Files (Archived)
- `archive/docker-compose.yml.old` - Original compose file
- `archive/docker-compose.yml` - Root compose file (moved from project root)
- `archive/INFISICAL_SUPABASE_CONFLICTS.md` - Outdated conflict documentation

### New Files
- `compose/core/docker-compose.yml` - Core infrastructure (Caddy, Cloudflared, Redis, Postgres)
- `compose/supabase/docker-compose.yml` - Supabase services
- `compose/infisical/docker-compose.yml` - Infisical service
- `compose/ai/docker-compose.yml` - AI services (Ollama, ComfyUI)
- `compose/workflow/docker-compose.yml` - Workflow services (n8n, Flowise)
- `compose/data/docker-compose.yml` - Data stores (Qdrant, Neo4j, MongoDB, MinIO)
- `compose/observability/docker-compose.yml` - Observability (Langfuse, ClickHouse)
- `compose/web/docker-compose.yml` - Web interfaces (Open WebUI, SearXNG)

## Migration Steps Completed

1. ✅ Created modular compose structure
2. ✅ Extracted all services into component files
3. ✅ Updated `start_services.py` to use modular files
4. ✅ Configured networks (localai_default)
5. ✅ Configured volumes (shared across files)
6. ✅ Created update script for Supabase
7. ✅ Updated documentation
8. ✅ Archived old docker-compose.yml
9. ✅ Fixed dependency issues
10. ✅ Added Infisical authentication to startup script

## Usage

The startup script works the same way:

```bash
python start_services.py --profile gpu-nvidia
```

The script automatically:
- Stops existing containers (including orphaned ones)
- Authenticates with Infisical (if enabled)
- Stitches together all modular compose files
- Starts all services

## Updating Services

### Supabase
```bash
python scripts/update-supabase-compose.py
```

### Other Services
Update image tags in their respective compose files in `compose/` subdirectories.

## Benefits

1. **No Conflicts**: Each compose file is independent
2. **Easy Updates**: Update individual services without affecting others
3. **Better Organization**: Clear separation of concerns
4. **Flexible**: Easy to enable/disable components
5. **Maintainable**: Follows Docker best practices

## Documentation

See `docs/modular-compose-architecture.md` for detailed documentation.

