# AI Homelab Modular Refactor - Summary

## ✅ Completed Refactoring

This document summarizes the complete refactoring from a modular `compose/` structure to a stack-based architecture.

## New Structure

```
/ai-homelab
├── .env.global               # Non-sensitive globals (DOMAIN_NAME, TZ)
├── start_services.py         # Updated for new stack structure
├── start-stack.sh            # Start individual stacks
├── stop-stack.sh             # Stop individual stacks
│
├── 00-infrastructure/        # Stack: Connectivity & Security
│   ├── docker-compose.yml    # cloudflared, caddy, infisical-backend, infisical-db, infisical-redis, redis
│   ├── config/               # Infrastructure configuration
│   │   ├── Caddyfile         # Reverse proxy configuration
│   │   ├── caddy-addon/      # Caddy addons
│   │   ├── networks.yml      # Network definition (reference)
│   │   ├── docker-compose.override.private.yml  # Private env overrides
│   │   └── docker-compose.override.public.yml   # Public env overrides
│   └── docs/                 # Infrastructure documentation
│       ├── ARCHITECTURE.md
│       ├── ARCHITECTURE_DECISIONS.md
│       ├── QUICK_START.md
│       ├── cloudflare/       # Cloudflare Tunnel docs
│       └── infisical/        # Infisical docs
│
├── 01-data/                  # Stack: Persistence (Databases)
│   ├── supabase/
│   │   ├── docker-compose.yml
│   │   ├── config/           # Supabase configuration
│   │   │   └── docker-compose.override.public.supabase.yml
│   │   └── docs/             # Supabase-specific docs
│   ├── qdrant/
│   │   └── docker-compose.yml
│   └── neo4j/
│       └── docker-compose.yml
│
├── 02-compute/               # Stack: Heavy AI Inference (GPU)
│   ├── docker-compose.yml    # ollama, comfyui
│   └── data/                 # Model weights/outputs
│       ├── ollama/           # Ollama models
│       └── comfyui/          # ComfyUI models, workflows, config (merged from GitHub/comfyui)
│
└── 03-apps/                  # Stack: Agentic Workflows & UI
    └── docker-compose.yml    # n8n, flowise, open-webui, searxng, langfuse, clickhouse, mongodb, minio
```

## Key Changes

### Network
- **Old**: `localai_default` (created by core compose)
- **New**: External `ai-network` (created separately, referenced by all stacks)

### Directory Structure
- **Old**: `compose/{core,supabase,infisical,ai,workflow,data,observability,web}/`
- **New**: `{00-infrastructure,01-data,02-compute,03-apps}/`

### Services Reorganization
- **Infrastructure**: cloudflared, caddy, infisical (with dedicated PostgreSQL), redis
- **Data**: Supabase, Qdrant, Neo4j (separate compose files)
- **Compute**: Ollama, ComfyUI (with merged resources)
- **Apps**: n8n, flowise, open-webui, searxng, langfuse, clickhouse, mongodb, minio

### Documentation
- **Old**: Top-level `/docs` directory
- **New**: Documentation moved to service folders:
  - `00-infrastructure/docs/` - Infrastructure, Cloudflare, Infisical docs
  - `01-data/supabase/docs/` - Supabase-specific docs

### Merged Resources
- **Infisical**: Merged from `/home/jaewilson07/GitHub/infisical/` with dedicated PostgreSQL
- **ComfyUI**: Merged all resources from `/home/jaewilson07/GitHub/comfyui/` to `02-compute/data/comfyui/`

## Deleted Directories

- ✅ `/compose/` - Old modular structure
- ✅ `/docs/` - Top-level documentation (moved to service folders)
- ✅ `/home/jaewilson07/GitHub/infisical/` - Merged into infrastructure stack
- ✅ `/home/jaewilson07/GitHub/comfyui/` - Merged into compute stack

## Updated Files

- ✅ `start_services.py` - Updated for new stack structure
- ✅ `scripts/update-supabase-compose.py` - Updated paths and network references
- ✅ All compose files - Updated to use `ai-network`
- ✅ Volume paths - Updated for new directory structure

## Network Migration

The external `ai-network` has been created. The old `localai_default` network can be removed after verifying all services work:

```bash
docker network rm localai_default
```

## Cleanup Status

### ✅ Completed
- Utility scripts moved to `scripts/utilities/`
- Service data directories moved to appropriate stack folders
- Documentation organized into proper locations
- Compose files updated with new paths

### ⚠️ Manual Action Required
- `searxng/` and `neo4j/` require stopping containers and using sudo to move (permission issues)
- `heimdall/` and `traefik/` need review - archive if unused
- `comfyui/` in root needs verification against `02-compute/data/comfyui/`

See `CLEANUP_STATUS.md` in root for detailed status.

## Next Steps

1. **Complete cleanup**: Move remaining directories (see CLEANUP_STATUS.md)
2. **Test the stacks**: Start services and verify connectivity
3. **Verify volumes**: Ensure all data persisted correctly
4. **Update README**: Update main README with new structure
5. **Remove old network**: After verification, remove `localai_default`

## Quick Start

```bash
# Create network (if not exists)
docker network create ai-network

# Start all stacks
python start_services.py --profile gpu-nvidia

# Or start individual stacks
./start-stack.sh infrastructure
./start-stack.sh data
./start-stack.sh compute gpu-nvidia
./start-stack.sh apps
```

## Stack Management

See `STACK_MANAGEMENT.md` for detailed stack management commands.


