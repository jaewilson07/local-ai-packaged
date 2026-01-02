# Modular Docker Compose Architecture

## Overview

This project uses a **modular Docker Compose architecture** where each major component has its own `docker-compose.yml` file in a dedicated subfolder within the `compose/` directory. The `start_services.py` script stitches them together using multiple `-f` flags, which is Docker's recommended "merge" approach for large applications.

This architecture was implemented to solve conflicts that occurred when using the `include:` directive in a single `docker-compose.yml` file. The modular approach ensures each service is defined in a single, clear context and then merged at runtime.

## Architecture Benefits

1. **No Conflicts**: Each compose file is independent until merged at runtime, avoiding the conflicts that occur with the `include:` directive
2. **Modularity**: Easy to enable/disable components by including/excluding compose files
3. **Easy Updates**: Update individual services (like Supabase) by updating their compose file
4. **Clear Organization**: Each component is self-contained and easy to understand
5. **Flexible Startup**: Can start services in phases or all at once
6. **Maintainability**: Clear separation of concerns

## Directory Structure

```
compose/
  ├── core/
  │   └── docker-compose.yml          # Caddy, Cloudflared, Redis, Postgres (for Langfuse)
  ├── supabase/
  │   └── docker-compose.yml          # Supabase services (from upstream)
  ├── infisical/
  │   └── docker-compose.yml          # Infisical service
  ├── ai/
  │   └── docker-compose.yml          # Ollama, ComfyUI (CPU/GPU variants)
  ├── workflow/
  │   └── docker-compose.yml          # n8n, Flowise
  ├── data/
  │   └── docker-compose.yml          # Qdrant, Neo4j, MongoDB, MinIO
  ├── observability/
  │   └── docker-compose.yml          # Langfuse, ClickHouse
  └── web/
      └── docker-compose.yml          # Open WebUI, SearXNG
```

## Component Details

### Core Infrastructure (`compose/core/docker-compose.yml`)

- **Services**: Caddy, Cloudflared, Redis, Postgres (for Langfuse)
- **Network**: Creates `localai_default` network
- **Volumes**: Shared volumes used by other services
- **Purpose**: Core infrastructure that other services depend on

### Supabase (`compose/supabase/docker-compose.yml`)

- **Services**: `db`, `studio`, `kong`, `auth`, `rest`, `realtime`, `storage`, `imgproxy`, `meta`, `functions`, `analytics`, `vector`, `supavisor`, `supabase-minio`
- **Source**: Copied from `supabase/docker/docker-compose.yml` and `docker-compose.s3.yml`
- **Network**: Uses external network `localai_default`
- **Volume Paths**: Adjusted to be relative to `compose/supabase/` (e.g., `../../supabase/docker/volumes/`)
- **Updates**: Use `scripts/update-supabase-compose.py` to update from upstream

### Infisical (`compose/infisical/docker-compose.yml`)

- **Services**: `infisical`
- **Dependencies**: Requires `supabase-db` (postgres) and `redis` from core
- **Network**: Uses external network `localai_default`

### AI Services (`compose/ai/docker-compose.yml`)

- **Services**: `ollama-cpu`, `ollama-gpu`, `ollama-gpu-amd`, `comfyui-cpu`, `comfyui-gpu`, `comfyui-gpu-amd`
- **Uses Profiles**: CPU vs GPU variants using Docker Compose profiles
- **Dependencies**: May need GPU access

### Workflow (`compose/workflow/docker-compose.yml`)

- **Services**: `n8n`, `n8n-import`, `flowise`
- **Dependencies**: `supabase-db` (postgres), `redis`

### Data Stores (`compose/data/docker-compose.yml`)

- **Services**: `qdrant`, `neo4j`, `mongodb`, `minio`
- **Volumes**: Data persistence volumes

### Observability (`compose/observability/docker-compose.yml`)

- **Services**: `langfuse-worker`, `langfuse-web`, `clickhouse`
- **Dependencies**: `postgres` (from core), `minio` (from data), `redis` (from core)

### Web Interfaces (`compose/web/docker-compose.yml`)

- **Services**: `open-webui`, `searxng`
- **Dependencies**: `ollama` (from ai)

## Network Configuration

All compose files use the same Docker network (`localai_default`):

- **Core compose file** creates the network:
  ```yaml
  networks:
    default:
      name: localai_default
  ```

- **Other compose files** use it as external:
  ```yaml
  networks:
    default:
      external: true
      name: localai_default
  ```

## Volume Configuration

Volumes are defined in each compose file where they're used. Docker Compose automatically merges volume definitions when multiple `-f` flags are used, so volumes with the same name are shared across services.

## Starting Services

The `start_services.py` script stitches together all compose files:

```python
compose_files = [
    "compose/core/docker-compose.yml",
    "compose/supabase/docker-compose.yml",
    "compose/infisical/docker-compose.yml",  # if enabled
    "compose/ai/docker-compose.yml",
    "compose/workflow/docker-compose.yml",
    "compose/data/docker-compose.yml",
    "compose/observability/docker-compose.yml",
    "compose/web/docker-compose.yml",
]

cmd = ["docker", "compose", "-p", "localai"]
for file in compose_files:
    cmd.extend(["-f", file])
cmd.extend(["up", "-d"])
```

### Manual Example

You can also start services manually:

```bash
docker compose \
  -p localai \
  -f compose/core/docker-compose.yml \
  -f compose/supabase/docker-compose.yml \
  -f compose/infisical/docker-compose.yml \
  -f compose/ai/docker-compose.yml \
  -f compose/workflow/docker-compose.yml \
  -f compose/data/docker-compose.yml \
  -f compose/observability/docker-compose.yml \
  -f compose/web/docker-compose.yml \
  --profile gpu-nvidia \
  up -d
```

## Updating Individual Services

### Updating Supabase

Use the provided script to update Supabase compose file from upstream:

```bash
python scripts/update-supabase-compose.py
```

This script:
1. Copies from `supabase/docker/docker-compose.yml` and `supabase/docker/docker-compose.s3.yml`
2. Preserves network configuration (external: localai_default)
3. Updates volume paths to be relative to `compose/supabase/`
4. Merges S3 storage configuration

### Updating Other Services

For other services, simply update the image tags in their respective compose files:

```yaml
# compose/ai/docker-compose.yml
services:
  ollama-cpu:
    image: ollama/ollama:latest  # Update tag here
```

## Override Files

Port bindings and other environment-specific configurations are handled via override files:

- `docker-compose.override.private.yml` - Port bindings for local dev
- `docker-compose.override.public.yml` - Port resets for public deployment

These are automatically included by `start_services.py` based on the `--environment` flag.

## Troubleshooting

### Service Conflicts

If you see "conflicts with imported resource" errors, ensure you're using the modular compose files and not mixing them with the old `docker-compose.yml` that uses `include:`.

### Network Issues

If services can't communicate, verify:
1. All compose files use the same network name (`localai_default`)
2. Core compose file creates the network (not external)
3. Other compose files use it as external

### Volume Issues

If volumes aren't shared correctly:
1. Ensure volume names match exactly across compose files
2. Check that volumes are defined in at least one compose file
3. Docker Compose merges volumes automatically when using multiple `-f` flags

## Migration from Old Architecture

The old architecture used:
- Single `docker-compose.yml` with `include:` directive
- Separate Supabase compose file started independently
- Conflict handling logic in `start_services.py`

The new architecture:
- Modular compose files in `compose/` subdirectories
- All services started together via multiple `-f` flags
- No conflict handling needed (each file is independent)

## Best Practices

1. **Keep compose files focused**: Each file should contain related services
2. **Use external networks**: All files except core should use external network
3. **Relative volume paths**: Use relative paths from the compose file's location
4. **Document dependencies**: Comment which services depend on others
5. **Version control**: Keep compose files in version control, but note which are from upstream

## Service Dependencies

Understanding service dependencies is crucial for troubleshooting:

```
Core (creates network)
  ├── Supabase (depends on core network)
  │   └── Infisical (depends on db from Supabase, redis from core)
  ├── AI Services (depends on core network)
  ├── Workflow (depends on db from Supabase, redis from core)
  ├── Data Stores (depends on core network)
  ├── Observability (depends on postgres from core, minio from data, redis from core)
  └── Web Interfaces (depends on ollama from ai)
```

## Container Names vs Service Names

**Important**: When using `depends_on`, you must use **service names**, not container names.

- **Service name**: `db` (used in `depends_on`)
- **Container name**: `supabase-db` (used in connection strings)

Example:
```yaml
# compose/infisical/docker-compose.yml
services:
  infisical:
    depends_on:
      db:  # Service name, not container name
        condition: service_healthy
    environment:
      - DB_CONNECTION_URI=postgresql://postgres:${POSTGRES_PASSWORD}@supabase-db:5432/postgres
      # Container name used in connection string
```

## Volume Path Resolution

Volume paths in compose files are relative to the **compose file's location**, not the project root.

Example from `compose/supabase/docker-compose.yml`:
```yaml
volumes:
  - ../../supabase/docker/volumes/db/data:/var/lib/postgresql/data:Z
```

This resolves to: `project_root/supabase/docker/volumes/db/data`

## Infisical Integration

The startup script includes automatic Infisical authentication:

1. **Checks if authenticated** - Verifies Infisical CLI authentication status
2. **Machine Identity** - Tries automated login if `INFISICAL_MACHINE_CLIENT_ID` and `INFISICAL_MACHINE_CLIENT_SECRET` are set
3. **Interactive Login** - Falls back to browser-based login if needed
4. **Secret Export** - Exports secrets to `.env.infisical` for use by services
5. **Fallback** - Uses `.env` file if Infisical is not available or not authenticated

To use Infisical for secret management:
- Set up Infisical service (included in compose files)
- Authenticate CLI: `infisical login` or set machine identity env vars
- Store secrets in Infisical UI
- Script will automatically export and use them

## File Organization Summary

```
project_root/
├── compose/                          # Modular compose files
│   ├── core/docker-compose.yml       # Core infrastructure
│   ├── supabase/docker-compose.yml   # Supabase services
│   ├── infisical/docker-compose.yml # Infisical service
│   ├── ai/docker-compose.yml        # AI services
│   ├── workflow/docker-compose.yml   # Workflow services
│   ├── data/docker-compose.yml      # Data stores
│   ├── observability/docker-compose.yml # Observability
│   └── web/docker-compose.yml        # Web interfaces
├── supabase/                         # Supabase upstream repo
│   └── docker/                      # Original Supabase compose files
├── scripts/
│   └── update-supabase-compose.py   # Update script for Supabase
├── docs/
│   └── modular-compose-architecture.md # This file
├── archive/                          # Archived old files
│   ├── docker-compose.yml.old       # Old compose file
│   └── README.md                    # Archive documentation
├── docker-compose.override.private.yml # Port bindings for local dev
├── docker-compose.override.public.yml  # Port resets for public
└── start_services.py                # Main startup script
```

## Common Operations

### Starting All Services
```bash
python start_services.py --profile gpu-nvidia
```

### Starting Specific Components
```bash
# Start only core and Supabase
docker compose -p localai \
  -f compose/core/docker-compose.yml \
  -f compose/supabase/docker-compose.yml \
  up -d

# Start only AI services
docker compose -p localai \
  -f compose/core/docker-compose.yml \
  -f compose/ai/docker-compose.yml \
  --profile gpu-nvidia \
  up -d
```

### Stopping Services
```bash
# Stop all services
python start_services.py --profile gpu-nvidia
# Then: docker compose -p localai down

# Stop specific component
docker compose -p localai \
  -f compose/workflow/docker-compose.yml \
  down
```

### Viewing Logs
```bash
# All services
docker compose -p localai logs -f

# Specific service
docker compose -p localai logs -f n8n
```

### Updating a Service
```bash
# Update Supabase
python scripts/update-supabase-compose.py

# Update other services - edit the compose file and pull images
docker compose -p localai \
  -f compose/ai/docker-compose.yml \
  pull ollama-cpu
```

## References

- [Docker Compose Multiple Files](https://docs.docker.com/compose/extends/#multiple-compose-files)
- [Docker Compose Profiles](https://docs.docker.com/compose/profiles/)
- [Docker Compose Networks](https://docs.docker.com/compose/networking/)
- [Docker Compose Dependencies](https://docs.docker.com/compose/compose-file/compose-file-v3/#depends_on)

