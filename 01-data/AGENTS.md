# Data Stack - AGENTS.md

> **Override**: This file extends [../AGENTS.md](../AGENTS.md). Data layer rules take precedence.

## Component Identity

**Stack**: `01-data`  
**Purpose**: Data persistence layer (PostgreSQL, vector store, graph database)  
**Docker Compose Files**:
- `01-data/supabase/docker-compose.yml` - Supabase (PostgreSQL + Auth + Storage)
- `01-data/qdrant/docker-compose.yml` - Qdrant vector store
- `01-data/neo4j/docker-compose.yml` - Neo4j graph database
- `01-data/mongodb/docker-compose.yml` - MongoDB with Atlas Search
- `01-data/minio/docker-compose.yml` - MinIO S3-compatible storage

**Network**: Uses external `ai-network` (created by infrastructure stack)

## Folder Structure

**Stack-Level Files**:
- `AGENTS.md` - This file (stack-specific rules)
- (No stack-level compose - each service has its own compose file)

**Service-Specific Folders** (Each service gets its own folder):
- `supabase/` - Supabase service
  - `docker-compose.yml` - Service-specific compose
  - `config/` - Supabase configuration (override files)
  - `data/` - Persistent data storage (mounted volumes)
  - `upstream/` - Cloned `supabase/supabase` repository (docker config source)
  - `docs/` - Supabase-specific documentation
  - `README.md` - Supabase setup and usage
- `qdrant/` - Qdrant vector store
  - `docker-compose.yml` - Service-specific compose
  - `data/` - Persistent vector data
- `neo4j/` - Neo4j graph database
  - `docker-compose.yml` - Service-specific compose
  - `data/` - Persistent graph data
- `mongodb/` - MongoDB database
  - `docker-compose.yml` - Service-specific compose
  - `data/` - Persistent document data
- `minio/` - MinIO S3-compatible storage
  - `docker-compose.yml` - Service-specific compose
  - `data/` - Persistent object storage data

**Refactoring Notes**:
- Each data service has its own folder with its own compose file (independent management)
- Service-specific configs and docs go in the service folder
- **Pattern**: Use `upstream/` for cloned repos and `data/` for persistence.
- Follow the pattern: `01-data/{service-name}/docker-compose.yml`

## Supabase

### Architecture
- **Upstream Source**: Cloned from `https://github.com/supabase/supabase.git` (sparse checkout, `docker/` only)
- **Location**: `01-data/supabase/upstream/`
- **Compose File**: `01-data/supabase/docker-compose.yml` (modular, not upstream)
- **Key Services**:
  - `supabase-db` - PostgreSQL 15
  - `supabase-kong` - API Gateway
  - `supabase-auth` - GoTrue authentication
  - `supabase-studio` - Admin UI
  - `supabase-minio` - S3-compatible storage (separate from Langfuse MinIO)

### Key Files
- `01-data/supabase/docker-compose.yml` - Service definitions
- `01-data/supabase/config/docker-compose.override.public.supabase.yml` - Public environment overrides
- `supabase/docker/volumes/api/kong.yml` - Kong API gateway config (from upstream)

### Patterns

**Database Connection**:
- **Host**: `supabase-db` (container name)
- **Port**: 5432 (internal), exposed via Kong on 8000/8443
- **Database**: `postgres`
- **User**: `postgres`
- **Password**: `${POSTGRES_PASSWORD}` (from `.env`)

**API Access**:
- **Internal**: `http://kong:8000` (service name)
- **External**: Via Caddy reverse proxy (hostname-based)
- **Keys**: `ANON_KEY`, `SERVICE_ROLE_KEY`, `JWT_SECRET` (generated)
- **Configuration**: Kong entrypoint validates `kong.yml` template exists before starting, uses `sed` to substitute environment variables

**Environment Variables**:
- **Required for Kong**: `ANON_KEY`, `SERVICE_ROLE_KEY`, `DASHBOARD_USERNAME`, `DASHBOARD_PASSWORD`
- **Required for Pooler**: `POSTGRES_HOST`, `POSTGRES_PORT`, `POSTGRES_DB`, `POSTGRES_PASSWORD`, `SECRET_KEY_BASE`, `VAULT_ENC_KEY`, `POOLER_TENANT_ID`
- **Required for Realtime**: `POSTGRES_HOST`, `POSTGRES_PORT`, `POSTGRES_DB`, `POSTGRES_PASSWORD`, `DB_AFTER_CONNECT_QUERY` (set to `SET search_path TO _realtime,public`)
- **Required for Storage**: `POSTGRES_HOST`, `POSTGRES_PORT`, `POSTGRES_DB`, `POSTGRES_PASSWORD`
- **Required for Functions**: `ANON_KEY`, `SERVICE_ROLE_KEY`
- **Required for Vector**: `LOGFLARE_PUBLIC_ACCESS_TOKEN` (optional, but required for full functionality)
- **All services**: Use `env_file: - ../../.env` to load variables from root `.env` file

**Storage**:
- **MinIO Service**: `supabase-minio` (separate from Langfuse MinIO)
- **Ports**: 9020 (API), 9021 (Console)
- **Credentials**: `SUPABASE_MINIO_ROOT_USER`, `SUPABASE_MINIO_ROOT_PASSWORD`

**User Provisioning**:
- **JIT Provisioning**: Lambda server automatically creates user profiles in `profiles` table
- **Table Schema**: `id` (UUID), `email` (unique), `role` (default: "user"), `tier` (default: "free"), `created_at`
- **Location**: `04-lambda/server/projects/auth/services/supabase_service.py`
- **Pattern**: `get_or_provision_user(email)` creates user if doesn't exist

**Database Migrations**:
- **Automatic Application**: Lambda server automatically applies migrations from `01-data/supabase/migrations/` on startup
- **Core Tables**: `profiles` table is validated and auto-created if missing (CRITICAL for system operation)
- **Optional Tables**: `comfyui_workflows`, `comfyui_workflow_runs`, `comfyui_lora_models` are checked but missing them won't prevent startup
- **Validation Service**: `04-lambda/server/projects/auth/services/database_validation_service.py` handles validation and migration application
- **Migration Files**: Numbered migrations (e.g., `000_profiles_table.sql`, `001_comfyui_workflows.sql`) are applied in order
- **Idempotent**: All migrations use `CREATE TABLE IF NOT EXISTS` to be safe to run multiple times
- **Protection**: Core tables are validated on every Lambda server startup to prevent accidental deletion
- **Documentation**: See [Supabase Migrations README](supabase/migrations/README.md)

**Data Isolation**:
- **Application-Level**: Queries filtered by `owner_email = user.email`
- **Admin Override**: Users with `role: "admin"` bypass filtering
- **RLS**: Can be enabled at database level (requires custom policies)
- **Pattern**: Always include `WHERE owner_email = $1` in user-scoped queries (unless admin)

**Common Gotchas**:
- **Password Characters**: Avoid `@` symbol in `POSTGRES_PASSWORD` (causes connection issues)
- **Pooler**: Requires `POOLER_DB_POOL_SIZE=5` in `.env` (if setup before June 2024)
- **Upstream Updates**: Run `git pull` in `supabase/` directory to update
- **User Provisioning**: `profiles` table is automatically created by Lambda server on startup if missing (no manual intervention needed)
- **Migrations**: Migrations are automatically applied during Lambda server startup - no manual application required
- **Database Resets**: If database volume is deleted/recreated, migrations will be automatically reapplied on next Lambda server startup
- **Health Checks**: Storage service uses `nc` (netcat) for TCP port checks (wget/curl not available in container)
- **Volume Paths**: All volume paths in `docker-compose.yml` use relative paths (`./`) from the compose file location
- **Environment Variables**: All Supabase services (kong, pooler, realtime, functions, storage) have `env_file: - ../../.env` to load variables from root `.env` file
- **Vector Dependency**: Database depends on vector with `service_started` (not `service_healthy`) to allow startup even if vector is unhealthy

### Search Hints
```bash
# Find Supabase service definitions
rg -n "supabase-" 01-data/supabase/docker-compose.yml

# Find database connection strings
rg -n "POSTGRES_\|DB_POSTGRES" --type yaml

# Find Kong configuration
cat supabase/docker/volumes/api/kong.yml
```

## Qdrant

### Architecture
- **Image**: `qdrant/qdrant:latest`
- **Container**: `qdrant`
- **Port**: 6333 (API), 6334 (gRPC)
- **Volume**: `qdrant_data` (persistent storage)

### Patterns
- **API Key**: Optional for local (can be any value)
- **Internal URL**: `http://qdrant:6333`
- **Use Case**: High-performance vector search (faster than Supabase for RAG)

### Configuration
- No authentication required for local deployment
- Storage: Persistent volume for vector data
- Network: `ai-network` only

## Neo4j

### Architecture
- **Image**: `neo4j:latest`
- **Container**: `neo4j`
- **Port**: 7474 (HTTP), 7687 (Bolt)
- **Volumes**: Named volumes (managed by Docker)
  - `neo4j_data` - Graph database storage
  - `neo4j_logs` - Application logs
  - `neo4j_import` - Import directory for data loading
  - `neo4j_plugins` - Plugin storage

### Patterns
- **Authentication**: `NEO4J_AUTH` (format: `username/password`)
- **Use Case**: Knowledge graphs (GraphRAG, LightRAG, Graphiti)
- **Internal URL**: `bolt://neo4j:7687`

**User Provisioning**:
- **JIT Provisioning**: Lambda server automatically creates `:User` nodes
- **Node Pattern**: `(:User {email: "user@example.com"})`
- **Location**: `04-lambda/server/projects/auth/services/neo4j_service.py`
- **Pattern**: `provision_user(email)` creates user node if doesn't exist

**Data Isolation**:
- **User Anchoring**: All queries should anchor to user node: `MATCH (u:User {email: $email})`
- **Admin Override**: Users with `role: "admin"` skip user anchoring
- **Pattern**: Use `get_user_anchored_query()` helper from `Neo4jService`
- **Documentation**: See [Neo4j Data Isolation Guide](neo4j/docs/data-isolation.md)

### Configuration
- **Auth**: Set via `NEO4J_AUTH` environment variable
- **Storage**: Named volumes for all persistent data (follows same pattern as Qdrant and MongoDB)
- **Network**: `ai-network` only
- **Logs**: Stored in Docker-managed volume `localai_neo4j_logs` (not in repository)

## MongoDB

### Architecture
- **Image**: `mongodb/mongodb-atlas-local:latest`
- **Container**: `mongodb` (Single container includes MongoDB + Atlas Search)
- **Port**: 27017 (MongoDB)
- **Volumes**: `mongodb_data`, `mongodb_config`, `mongot_data` (Required for Vector Search index persistence)

### Patterns
- **Authentication**: `MONGODB_INITDB_ROOT_USERNAME`, `MONGODB_INITDB_ROOT_PASSWORD`
- **Use Case**: Document storage, Vector Search, Local Atlas Development
- **Internal URL**: `mongodb://mongodb:27017`

**Data Isolation**:
- **Field-Based Filtering**: Filter by `user_id` or `user_email` fields in documents
- **Admin Override**: Users with `role: "admin"` bypass filtering
- **Pattern**: Query filter: `{"$or": [{"user_id": user_id}, {"user_email": email}]}`
- **Metadata Fields**: Also check `metadata.user_id` and `metadata.user_email`
- **No Explicit Provisioning**: Users are identified via field matching (no explicit user collection)

### Configuration
- **Replica Set**: Required and handled by `MONGODB_REPLICA_SET_NAME=rs0`
- **Search**: Integrated Atlas Search (mongot) process
- **Network**: `ai-network` only

## MinIO

### Architecture
- **Image**: `minio/minio`
- **Container**: `minio`
- **Ports**: 9000 (API), 9001 (Console)
- **Volume**: `./data` (bind mount, relative to service directory)

### Patterns
- **Authentication**: `MINIO_ROOT_USER` (default: `minio`), `MINIO_ROOT_PASSWORD` (required)
- **Use Case**: S3-compatible object storage for Langfuse and other services
- **Internal URL**: `http://minio:9000` (API), `http://minio:9001` (Console)
- **Buckets**: `langfuse` bucket auto-created on startup

### Configuration
- **Root User**: `MINIO_ROOT_USER` (default: `minio`)
- **Root Password**: `MINIO_ROOT_PASSWORD` (required, from `.env`)
- **Storage**: Bind mount to `./minio/data` (persistent)
- **Network**: `ai-network` only

**Note**: Separate from `supabase-minio` (different service, different credentials, different ports)

### Supabase MinIO (User Storage)

**Architecture**:
- **Service**: `supabase-minio` (part of Supabase stack)
- **Ports**: 9020 (API), 9021 (Console)
- **Bucket**: `user-data` (shared bucket with prefix-based organization)
- **Credentials**: `SUPABASE_MINIO_ROOT_USER`, `SUPABASE_MINIO_ROOT_PASSWORD`

**User Provisioning**:
- **JIT Provisioning**: Lambda server automatically creates user folders
- **Folder Pattern**: `user-{uuid}/` (e.g., `user-123e4567-e89b-12d3-a456-426614174000/`)
- **Location**: `04-lambda/server/projects/auth/services/minio_service.py`
- **Pattern**: `provision_user(user_id, email)` creates folder structure if doesn't exist

**Data Isolation**:
- **Prefix-Based**: User files stored under `user-{uuid}/` prefix
- **Admin Override**: Users with `role: "admin"` can access all folders
- **Pattern**: List objects with prefix: `s3_client.list_objects_v2(Bucket="user-data", Prefix=f"user-{uuid}/")`
- **Bucket**: Shared `user-data` bucket (not per-user buckets)

## Architecture Patterns

### Service Discovery
All data services use container names as hostnames:
- `supabase-db:5432` - PostgreSQL
- `qdrant:6333` - Qdrant API
- `neo4j:7687` - Neo4j Bolt
- `mongodb:27017` - MongoDB
- `minio:9000` - MinIO API

### Volume Management
- **Persistent**: All data volumes are named (e.g., `qdrant_data`, `neo4j_data`)
- **Backup**: Not automated. Manual backup via volume exports.
- **Location**: Managed by Docker (not in repo)

### Environment Variables
- **Shared**: `.env.global` for non-sensitive defaults
- **Secrets**: `.env` for passwords and keys
- **Service-Specific**: Each service has its own env var namespace

## Testing & Validation

### Health Checks
```bash
# Supabase (via Kong)
curl http://localhost:8005/api/health

# Supabase Storage (TCP port check - uses nc, not wget/curl)
docker exec supabase-storage nc -z localhost 5000

# Supabase Vector (TCP port check)
docker exec supabase-vector nc -z localhost 9001

# Qdrant
curl http://qdrant:6333/health

# Neo4j
curl http://neo4j:7474

# MongoDB
docker exec mongodb mongosh --eval "db.adminCommand('ping')"

# MinIO
docker exec minio mc ready local
```

**Health Check Patterns**:
- **TCP Port Checks**: Use `nc -z localhost PORT` for services without wget/curl (storage, vector)
- **HTTP Checks**: Use `wget` or `curl` for services with HTTP endpoints (kong, auth, rest)
- **IPv4 vs IPv6**: Use `127.0.0.1` instead of `localhost` in health checks to avoid IPv6 connection issues
- **Service Readiness**: Some services may be running but unhealthy due to health check timing or configuration issues

### Known Health Check Issues

**Supabase Storage**: ✅ **Fixed** - Health check now uses `127.0.0.1` instead of `localhost` to avoid IPv6 resolution issues.

**Supabase Vector**: ✅ **Fixed** - Health check now uses `127.0.0.1` instead of `localhost` to avoid IPv6 resolution issues.

**Supabase Edge Functions**: ✅ **Fixed** - Now uses the upstream router function and starts successfully.

### Common Issues
1. **Supabase Pooler Restarting**: Check `POOLER_DB_POOL_SIZE` in `.env`
2. **Password Issues**: Avoid special characters (especially `@`) in `POSTGRES_PASSWORD`
3. **Connection Refused**: Verify service is on `ai-network` and container name is correct
4. **Volume Permissions**: Ensure Docker has write access to volume directories
5. **Health Check Failures**: If health check fails but service is running, check if tool (wget/curl/nc) is available in container
6. **Environment Variables Not Loading**: Ensure `env_file: - ../../.env` is present in service definition and `.env` file exists in project root
7. **Vector Unhealthy**: Vector may be unhealthy due to missing `LOGFLARE_PUBLIC_ACCESS_TOKEN`, but database can still start (dependency uses `service_started` not `service_healthy`)
8. **Kong Config Error**: If Kong fails to parse config, check that `kong.yml` template exists and environment variables are set (ANON_KEY, SERVICE_ROLE_KEY, DASHBOARD_USERNAME, DASHBOARD_PASSWORD)
9. **IPv6 Health Check Issues**: Use `127.0.0.1` instead of `localhost` in health checks to avoid IPv6 connection refused errors

## Do's and Don'ts

### ✅ DO
- Use container names for internal connections
- Keep Supabase upstream updated (`git pull` in `supabase/`)
- Use persistent volumes for data
- Generate secure passwords (use `setup/generate-env-passwords.py`)
- Separate Supabase MinIO from Langfuse MinIO
- Enforce data isolation in all queries (filter by user email/UUID)
- Use user anchoring pattern for Neo4j queries
- Check admin status before bypassing data isolation
- Reference [Auth Project README](../04-lambda/server/projects/auth/README.md) for user management patterns

### ❌ DON'T
- do not put any files in the root folder.  files should be created within their respective service stack
- create minimum necessary scripts.  use `service_stack/scripts` for long living scripts and `service_stack/temp` for onetime use scrips
- Hardcode database passwords
- Use `@` symbol in PostgreSQL passwords
- Mix data volumes between services
- Expose database ports directly (use Kong/Caddy)
- Commit `.env` files with secrets
- Expose other users' data (always filter by user email/UUID)
- Skip user anchoring in Neo4j queries (unless admin)
- Create per-user buckets in MinIO (use prefix-based organization)

## Domain Dictionary

- **Supabase**: Full-stack PostgreSQL platform (Auth, DB, Storage, Realtime)
- **Qdrant**: Vector database for embeddings and similarity search
- **Neo4j**: Graph database for relationship modeling
- **Kong**: API gateway (routes requests to Supabase services)
- **GoTrue**: Supabase authentication service
- **MinIO**: S3-compatible object storage (for Langfuse and other services)
- **Supabase MinIO**: Separate MinIO instance for Supabase Storage (different service)
- **Atlas Search**: MongoDB's full-text and vector search engine (provided by `mongot` container)

---

**See Also**:
- [../AGENTS.md](../AGENTS.md) for universal rules
- [supabase/README.md](../supabase/README.md) for Supabase-specific docs
- [Auth Project README](../04-lambda/server/projects/auth/README.md) - User provisioning and data isolation patterns
- [Neo4j Data Isolation Guide](neo4j/docs/data-isolation.md) - Neo4j user anchoring patterns
