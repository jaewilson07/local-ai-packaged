# Data Stack - AGENTS.md

> **Override**: This file extends [../AGENTS.md](../AGENTS.md). Data layer rules take precedence.

## Component Identity

**Stack**: `01-data`  
**Purpose**: Data persistence layer (PostgreSQL, vector store, graph database)  
**Docker Compose Files**:
- `01-data/supabase/docker-compose.yml` - Supabase (PostgreSQL + Auth + Storage)
- `01-data/qdrant/docker-compose.yml` - Qdrant vector store
- `01-data/neo4j/docker-compose.yml` - Neo4j graph database

**Network**: Uses external `ai-network` (created by infrastructure stack)

## Folder Structure

**Stack-Level Files**:
- `AGENTS.md` - This file (stack-specific rules)
- (No stack-level compose - each service has its own compose file)

**Service-Specific Folders** (Each service gets its own folder):
- `supabase/` - Supabase service
  - `docker-compose.yml` - Service-specific compose
  - `config/` - Supabase configuration (override files)
  - `docs/` - Supabase-specific documentation
  - `README.md` - Supabase setup and usage
- `qdrant/` - Qdrant vector store
  - `docker-compose.yml` - Service-specific compose
  - (Future: `docs/`, `config/` if needed)
- `neo4j/` - Neo4j graph database
  - `docker-compose.yml` - Service-specific compose
  - (Future: `docs/`, `config/` if needed)

**Refactoring Notes**:
- Each data service has its own folder with its own compose file (independent management)
- Service-specific configs and docs go in the service folder
- Follow the pattern: `01-data/{service-name}/docker-compose.yml`

## Supabase

### Architecture
- **Upstream Source**: Cloned from `https://github.com/supabase/supabase.git` (sparse checkout, `docker/` only)
- **Location**: `01-data/supabase/` (local) and `supabase/` (upstream clone)
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

**Storage**:
- **MinIO Service**: `supabase-minio` (separate from Langfuse MinIO)
- **Ports**: 9020 (API), 9021 (Console)
- **Credentials**: `SUPABASE_MINIO_ROOT_USER`, `SUPABASE_MINIO_ROOT_PASSWORD`

**Common Gotchas**:
- **Password Characters**: Avoid `@` symbol in `POSTGRES_PASSWORD` (causes connection issues)
- **Pooler**: Requires `POOLER_DB_POOL_SIZE=5` in `.env` (if setup before June 2024)
- **Upstream Updates**: Run `git pull` in `supabase/` directory to update

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
- **Volume**: `neo4j_data` (graph database storage)

### Patterns
- **Authentication**: `NEO4J_AUTH` (format: `username/password`)
- **Use Case**: Knowledge graphs (GraphRAG, LightRAG, Graphiti)
- **Internal URL**: `bolt://neo4j:7687`

### Configuration
- **Auth**: Set via `NEO4J_AUTH` environment variable
- **Storage**: Persistent volume for graph data
- **Network**: `ai-network` only

## Architecture Patterns

### Service Discovery
All data services use container names as hostnames:
- `supabase-db:5432` - PostgreSQL
- `qdrant:6333` - Qdrant API
- `neo4j:7687` - Neo4j Bolt

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

# Qdrant
curl http://qdrant:6333/health

# Neo4j
curl http://neo4j:7474
```

### Common Issues
1. **Supabase Pooler Restarting**: Check `POOLER_DB_POOL_SIZE` in `.env`
2. **Password Issues**: Avoid special characters (especially `@`) in `POSTGRES_PASSWORD`
3. **Connection Refused**: Verify service is on `ai-network` and container name is correct
4. **Volume Permissions**: Ensure Docker has write access to volume directories

## Do's and Don'ts

### ✅ DO
- Use container names for internal connections
- Keep Supabase upstream updated (`git pull` in `supabase/`)
- Use persistent volumes for data
- Generate secure passwords (use `utils/setup/env/generate_passwords.py`)
- Separate Supabase MinIO from Langfuse MinIO

### ❌ DON'T
- Hardcode database passwords
- Use `@` symbol in PostgreSQL passwords
- Mix data volumes between services
- Expose database ports directly (use Kong/Caddy)
- Commit `.env` files with secrets

## Domain Dictionary

- **Supabase**: Full-stack PostgreSQL platform (Auth, DB, Storage, Realtime)
- **Qdrant**: Vector database for embeddings and similarity search
- **Neo4j**: Graph database for relationship modeling
- **Kong**: API gateway (routes requests to Supabase services)
- **GoTrue**: Supabase authentication service
- **MinIO**: S3-compatible object storage

---

**See Also**: 
- [../AGENTS.md](../AGENTS.md) for universal rules
- [supabase/README.md](../supabase/README.md) for Supabase-specific docs

