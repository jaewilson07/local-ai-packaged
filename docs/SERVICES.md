# Services Catalog

Complete catalog of all services in the local-ai-packaged infrastructure, organized by stack.

## Stack Overview

Services are organized into numbered stacks with explicit dependencies:

1. **00-infrastructure**: Foundation services (networking, reverse proxy, secrets)
2. **00-infrastructure/infisical**: Secret management
3. **01-data**: Data storage layer (databases, vector stores, object storage)
4. **02-compute**: AI compute services (LLMs, image generation)
5. **03-apps**: Application layer (workflows, interfaces, observability, media)
6. **04-lambda**: FastAPI server with MCP and REST APIs

## 00-infrastructure Stack

**Project**: `localai-infra`  
**Purpose**: Foundation services for networking, reverse proxy, and caching

### cloudflared
**Container**: `cloudflared`  
**Port**: N/A (tunnel service)  
**Description**: Cloudflare Tunnel for secure, zero-trust access without port forwarding

**Features**:
- No port forwarding required
- Works behind NAT/firewalls
- Origin IP hidden
- Free SSL certificates
- DDoS protection

**Dependencies**: None (standalone service)

**Configuration**:
- `CLOUDFLARE_TUNNEL_TOKEN` - Tunnel token from Cloudflare dashboard

**Access**: Routes traffic through Cloudflare to Caddy

### caddy
**Container**: `caddy`  
**Port**: 80 (HTTP), 443 (HTTPS)  
**Description**: Reverse proxy with automatic HTTPS/TLS for custom domains

**Features**:
- Automatic HTTPS via Let's Encrypt
- Domain-based routing
- Load balancing
- Request logging

**Dependencies**: None (creates `ai-network`)

**Configuration**:
- `CADDYFILE` - Caddyfile configuration
- Service hostnames (e.g., `N8N_HOSTNAME`, `WEBUI_HOSTNAME`)

**Access**:
- Private: `http://localhost:80` (HTTP), `https://localhost:443` (HTTPS)
- Public: Via domain (e.g., `https://n8n.datacrew.space`)

### redis (Valkey)
**Container**: `valkey`  
**Port**: 6379  
**Description**: In-memory data store for caching and session storage

**Features**:
- High-performance caching
- Session storage
- Pub/sub messaging

**Dependencies**: None

**Configuration**:
- `REDIS_HOST` - Redis hostname (default: `redis`)
- `REDIS_PORT` - Redis port (default: `6379`)
- `REDIS_AUTH` - Redis password (default: `LOCALONLYREDIS`)

**Access**: `redis://redis:6379` (internal)

## 00-infrastructure/infisical Stack

**Project**: `localai-infisical`  
**Purpose**: Secret management platform

### infisical-backend
**Container**: `infisical-backend`  
**Port**: 8020  
**Description**: Infisical API server for secret management

**Features**:
- Web UI for secret management
- REST API for programmatic access
- CLI integration
- Machine identity support

**Dependencies**: `infisical-db`, `infisical-redis`

**Configuration**:
- `INFISICAL_ENCRYPTION_KEY` - Encryption key (16-byte hex)
- `INFISICAL_AUTH_SECRET` - Auth secret (32-byte base64)
- `INFISICAL_HOSTNAME` - Hostname (e.g., `:8020` or `infisical.datacrew.space`)
- `INFISICAL_SITE_URL` - Site URL

**Access**: `http://infisical-backend:8020` (internal) or via Caddy

### infisical-db
**Container**: `infisical-db`  
**Port**: 5432  
**Description**: PostgreSQL database for Infisical metadata

**Dependencies**: None

**Access**: `postgresql://infisical-db:5432` (internal)

### infisical-redis
**Container**: `infisical-redis`  
**Port**: 6379  
**Description**: Redis cache for Infisical

**Dependencies**: None

**Access**: `redis://infisical-redis:6379` (internal)

## 01-data Stack

**Project**: `localai-data`  
**Purpose**: Data storage layer (databases, vector stores, object storage)

### supabase-db
**Container**: `supabase-db`  
**Port**: 5432  
**Description**: PostgreSQL database (Supabase)

**Features**:
- Primary relational database
- Row-level security
- Real-time subscriptions
- Full-text search

**Dependencies**: None

**Configuration**:
- `POSTGRES_PASSWORD` - Database password

**Access**: `postgresql://supabase-db:5432/postgres` (internal)

**Used by**: n8n, Open WebUI, Supabase services

### supabase-kong
**Container**: `supabase-kong`  
**Port**: 8000 (HTTP), 8443 (HTTPS)  
**Description**: API gateway for Supabase

**Features**:
- API routing
- Authentication
- Rate limiting

**Dependencies**: `supabase-db`

**Access**: `http://supabase-kong:8000` (internal)

### supabase-studio
**Container**: `supabase-studio`  
**Port**: 3000  
**Description**: Supabase admin UI

**Features**:
- Database management
- Table editor
- SQL editor
- API documentation

**Dependencies**: `supabase-db`, `supabase-kong`

**Access**: `http://supabase-studio:3000` (internal) or via Caddy

### qdrant
**Container**: `qdrant`  
**Port**: 6333 (HTTP), 6334 (gRPC)  
**Description**: High-performance vector database

**Features**:
- Fast vector similarity search
- Sparse vector support
- Filtering
- Clustering

**Dependencies**: None

**Configuration**:
- `QDRANT_API_KEY` - API key (optional, for local use can be any value)

**Access**: `http://qdrant:6333` (internal)

**Used by**: n8n (optional, for vector operations)

### neo4j
**Container**: `neo4j`  
**Port**: 7474 (HTTP), 7687 (Bolt)  
**Description**: Graph database for knowledge graphs

**Features**:
- Graph data model
- Cypher query language
- Graph algorithms
- Knowledge graph support

**Dependencies**: None

**Configuration**:
- `NEO4J_AUTH` - Authentication (format: `username/password`)

**Access**:
- HTTP: `http://neo4j:7474` (internal)
- Bolt: `bolt://neo4j:7687` (internal)

**Used by**: Lambda server (Graphiti RAG, knowledge graph)

### mongodb
**Container**: `mongodb`  
**Port**: 27017  
**Description**: Document database for RAG

**Features**:
- Document storage
- Vector search (Atlas Local)
- Full-text search
- Replica sets

**Dependencies**: None

**Configuration**:
- `MONGODB_ROOT_USERNAME` - Root username (default: `admin`)
- `MONGODB_ROOT_PASSWORD` - Root password
- `MONGODB_DATABASE` - Database name (default: `admin`)

**Access**: `mongodb://mongodb:27017` (internal)

**Used by**: Lambda server (MongoDB RAG project)

### minio (Supabase Storage)
**Container**: `supabase-minio`  
**Port**: 9020 (API), 9021 (Console)  
**Description**: S3-compatible object storage for Supabase

**Features**:
- S3-compatible API
- Web console
- Bucket management

**Dependencies**: None

**Configuration**:
- `SUPABASE_MINIO_ROOT_USER` - Root user (default: `supa-storage`)
- `SUPABASE_MINIO_ROOT_PASSWORD` - Root password (default: `secret1234`)

**Access**:
- API: `http://supabase-minio:9020` (internal)
- Console: `http://supabase-minio:9021` (internal)

## 02-compute Stack

**Project**: `localai-compute`  
**Purpose**: AI compute services (LLMs, image generation)

### ollama
**Container**: `ollama`  
**Port**: 11434  
**Description**: LLM inference server for local models

**Features**:
- Local LLM inference
- Embedding generation
- Model management
- GPU acceleration (optional)

**Dependencies**: None (optional: GPU for acceleration)

**Configuration**:
- `OLLAMA_CONTEXT_LENGTH` - Context length (default: 8192)
- `OLLAMA_FLASH_ATTENTION` - Flash attention (default: 1)
- `OLLAMA_KV_CACHE_TYPE` - KV cache type (default: `q8_0`)
- `OLLAMA_MAX_LOADED_MODELS` - Max loaded models (default: 2)

**Access**: `http://ollama:11434` (internal)

**Used by**: n8n, Open WebUI, Lambda server, Flowise

**GPU Support**: NVIDIA, AMD (Linux), CPU fallback

### comfyui
**Container**: `comfyui`  
**Port**: 8188  
**Description**: Stable diffusion image generation with node-based interface

**Features**:
- Image generation
- Node-based workflow editor
- Model management
- GPU acceleration (optional)

**Dependencies**: None (optional: GPU for acceleration)

**Configuration**:
- GPU profiles: `gpu-nvidia`, `gpu-amd`, `cpu`

**Access**: `http://comfyui:8188` (internal) or via Caddy

**GPU Support**: NVIDIA, AMD (Linux), CPU fallback

## 03-apps Stack

**Project**: `localai-apps`  
**Purpose**: Application layer (workflows, interfaces, observability, media)

### n8n
**Container**: `n8n`  
**Port**: 5678  
**Description**: Low-code workflow automation platform

**Features**:
- Visual workflow builder
- 400+ integrations
- AI Agent nodes
- Webhook triggers
- Scheduled workflows

**Dependencies**: PostgreSQL (Supabase), Ollama (optional), Qdrant (optional)

**Configuration**:
- `N8N_ENCRYPTION_KEY` - Encryption key
- `N8N_USER_MANAGEMENT_JWT_SECRET` - JWT secret
- `N8N_HOSTNAME` - Hostname (e.g., `n8n.datacrew.space` or `:5678`)

**Access**: `http://n8n:5678` (internal) or via Caddy

**Integration Points**: Lambda server (MCP tools), Ollama, Supabase, Qdrant

### flowise
**Container**: `flowise`  
**Port**: 3001  
**Description**: No-code AI agent builder

**Features**:
- Visual agent builder
- LLM chain creation
- Memory management
- Tool integration

**Dependencies**: Ollama (optional)

**Configuration**:
- `FLOWISE_USERNAME` - Username
- `FLOWISE_PASSWORD` - Password
- `FLOWISE_HOSTNAME` - Hostname

**Access**: `http://flowise:3001` (internal) or via Caddy

### open-webui
**Container**: `open-webui`  
**Port**: 8080  
**Description**: ChatGPT-like interface for local LLMs

**Features**:
- Conversation interface
- PostgreSQL storage
- Google OAuth (optional)
- MCP server integration
- Function calling

**Dependencies**: PostgreSQL (Supabase), Ollama, Lambda server (MCP)

**Configuration**:
- `OPENWEBUI_API_URL` - Open WebUI API URL
- `LAMBDA_SERVER_URL` - Lambda server URL for MCP
- `ENABLE_OAUTH_SIGNUP` - Enable Google OAuth
- `GOOGLE_CLIENT_ID` - Google OAuth client ID
- `GOOGLE_CLIENT_SECRET` - Google OAuth client secret
- `WEBUI_HOSTNAME` - Hostname

**Access**: `http://open-webui:8080` (internal) or via Caddy

**Integration Points**: Lambda server (MCP), Ollama, Supabase, n8n (function calling)

### searxng
**Container**: `searxng`  
**Port**: 8081  
**Description**: Privacy-focused metasearch engine

**Features**:
- Aggregates 229+ search engines
- No user tracking
- No profiling
- Self-hosted results

**Dependencies**: None

**Configuration**:
- `SEARXNG_HOSTNAME` - Hostname

**Access**: `http://searxng:8081` (internal) or via Caddy

**Integration Points**: Lambda server (web search MCP tool)

### langfuse
**Container**: `langfuse`  
**Port**: 3000  
**Description**: LLM observability platform

**Features**:
- LLM trace collection
- Performance analytics
- Cost tracking
- Prompt management
- Evaluation and testing

**Dependencies**: PostgreSQL (Supabase), ClickHouse, MinIO

**Configuration**:
- `LANGFUSE_HOSTNAME` - Hostname
- `CLICKHOUSE_PASSWORD` - ClickHouse password
- `MINIO_ROOT_PASSWORD` - MinIO password
- `LANGFUSE_SALT` - Salt for hashing
- `NEXTAUTH_SECRET` - NextAuth secret
- `ENCRYPTION_KEY` - Encryption key

**Access**: `http://langfuse:3000` (internal) or via Caddy

**Integration Points**: ClickHouse (trace storage), MinIO (artifact storage), Supabase (metadata)

### clickhouse
**Container**: `clickhouse`  
**Port**: 8123 (HTTP), 9000 (Native)  
**Description**: Column-oriented analytics database

**Features**:
- High-performance analytics
- Real-time querying
- Columnar storage
- Compression

**Dependencies**: None

**Configuration**:
- `CLICKHOUSE_PASSWORD` - Password

**Access**: `http://clickhouse:8123` (HTTP, internal)

**Used by**: Langfuse (trace data storage)

### minio (Langfuse)
**Container**: `minio`  
**Port**: 9000 (API), 9001 (Console)  
**Description**: S3-compatible object storage for Langfuse

**Features**:
- S3-compatible API
- Web console
- Object storage

**Dependencies**: None

**Configuration**:
- `MINIO_ROOT_PASSWORD` - Root password

**Access**:
- API: `http://minio:9000` (internal)
- Console: `http://minio:9001` (internal)

**Used by**: Langfuse (artifact storage)

### immich-server
**Container**: `immich-server`  
**Port**: 2283  
**Description**: Main API server for Immich photo/video management

**Features**:
- Photo/video backup
- REST API
- Metadata management
- Face detection integration

**Dependencies**: `immich-postgres`, `immich-typesense`, Redis

**Configuration**:
- `IMMICH_HOSTNAME` - Hostname
- `IMMICH_DB_PASSWORD` - PostgreSQL password
- `IMMICH_TYPESENSE_API_KEY` - Typesense API key

**Access**: `http://immich-server:2283` (internal) or via Caddy

**Integration Points**: Discord bot, Frontend, Machine learning service

### immich-microservices
**Container**: `immich-microservices`  
**Port**: N/A (background service)  
**Description**: Background jobs for video transcoding

**Features**:
- Video transcoding
- Thumbnail generation
- Background processing
- GPU acceleration (optional)

**Dependencies**: `immich-server`, `immich-postgres`

**GPU Support**: NVIDIA, AMD (Linux), CPU fallback

### immich-machine-learning
**Container**: `immich-machine-learning`  
**Port**: N/A (background service)  
**Description**: Face detection and recognition service

**Features**:
- Face detection (Buffalo_L model)
- Face recognition
- Person clustering

**Dependencies**: `immich-server`

**GPU Support**: Optional (for faster processing)

### immich-postgres
**Container**: `immich-postgres`  
**Port**: 5432  
**Description**: Dedicated PostgreSQL database for Immich

**Dependencies**: None

**Configuration**:
- `IMMICH_DB_PASSWORD` - Database password

**Access**: `postgresql://immich-postgres:5432/immich` (internal)

### immich-typesense
**Container**: `immich-typesense`  
**Port**: 8108  
**Description**: Text search engine for Immich metadata

**Features**:
- Full-text search
- Metadata search
- Fast queries

**Dependencies**: None

**Access**: `http://immich-typesense:8108` (internal)

### discord-bot
**Container**: `discord-bot`  
**Port**: 8001 (MCP server, optional)  
**Description**: Discord bot for Immich integration

**Features**:
- File upload from Discord to Immich
- User face mapping
- Automated notifications
- MCP server for Discord management

**Dependencies**: Immich API, SQLite (local database)

**Configuration**:
- `DISCORD_BOT_TOKEN` - Discord bot token
- `DISCORD_UPLOAD_CHANNEL_ID` - Upload channel ID
- `IMMICH_API_KEY` - Immich API key
- `IMMICH_SERVER_URL` - Immich server URL
- `MCP_ENABLED` - Enable MCP server (default: true)
- `MCP_PORT` - MCP server port (default: 8001)

**Access**:
- MCP: `http://discord-bot:8001/mcp` (internal, if enabled)
- Discord: Via Discord API

**Integration Points**: Immich (uploads, face detection), Lambda server (optional MCP integration)

### discord-character-bot
**Container**: `discord-character-bot`  
**Port**: N/A (Discord API only)  
**Description**: Discord bot for AI character interactions in channels

**Features**:
- Character management (add, remove, list characters in channels)
- Direct mention responses (characters respond when mentioned)
- Random engagement (characters spontaneously join conversations)
- Conversation history tracking per channel+character
- Rich embeds with character avatars
- Knowledge store querying via `/query_knowledgestore` command

**Dependencies**: Lambda server (character management API), MongoDB (via Lambda)

**Configuration**:
- `DISCORD_BOT_TOKEN` - Discord bot token
- `LAMBDA_API_URL` - Lambda server URL (default: `http://lambda-server:8000`)
- `ENGAGEMENT_CHANCE` - Probability of random engagement (default: 0.15)
- `MIN_TIME_SINCE_LAST_ENGAGEMENT_MINUTES` - Minimum time between engagements (default: 10)
- `MAX_CHANNEL_CHARACTERS` - Maximum characters per channel (default: 5)

**Access**:
- Discord: Via Discord API
- Lambda API: `http://lambda-server:8000/api/v1/discord-characters/*`

**Integration Points**: Lambda server (character management, persona service, conversation orchestration), MongoDB (conversation history)

## 04-lambda Stack

**Project**: `localai-lambda`  
**Purpose**: FastAPI server with MCP and REST APIs

### lambda-server
**Container**: `lambda-server`  
**Port**: 8000  
**Description**: FastAPI server providing REST APIs, MCP endpoints, authentication system, and data viewing APIs

**Features**:
- 40+ MCP tools
- REST API endpoints
- Cloudflare Access JWT validation
- Just-In-Time (JIT) user provisioning
- Data isolation across all storage layers
- MongoDB RAG integration
- Graphiti RAG integration
- Knowledge graph operations
- Calendar integration
- Persona management
- Discord character management
- Multi-project architecture

**Dependencies**: MongoDB, Neo4j (optional), Supabase (PostgreSQL), MinIO, Ollama

**Configuration**:
- `MONGODB_URI` - MongoDB connection string
- `MONGODB_DATABASE` - Database name
- `LLM_PROVIDER` - LLM provider (default: `ollama`)
- `LLM_MODEL` - LLM model (default: `llama3.2`)
- `LLM_BASE_URL` - LLM base URL
- `EMBEDDING_PROVIDER` - Embedding provider (default: `ollama`)
- `EMBEDDING_MODEL` - Embedding model (default: `nomic-embed-text`)
- `NEO4J_URI` - Neo4j connection string
- `USE_GRAPHITI` - Enable Graphiti (default: false)
- `USE_KNOWLEDGE_GRAPH` - Enable knowledge graph (default: false)
- `USE_AGENTIC_RAG` - Enable agentic RAG (default: false)
- `CLOUDFLARE_AUTH_DOMAIN` - Cloudflare Access domain (e.g., `https://team.cloudflareaccess.com`)
- `CLOUDFLARE_AUD_TAG` - Application audience tag (64-char hex)
- `SUPABASE_DB_URL` - PostgreSQL connection string (e.g., `postgresql://postgres:password@supabase-db:5432/postgres`)
- `SUPABASE_SERVICE_KEY` - Supabase service role key (optional)
- `MINIO_ENDPOINT` - MinIO endpoint (e.g., `http://supabase-minio:9020`)
- `MINIO_ACCESS_KEY` - MinIO access key
- `MINIO_SECRET_KEY` - MinIO secret key

**Access**: `http://lambda-server:8000` (internal) or via Caddy at `api.datacrew.space`

**API Endpoints**:

**Public Endpoints** (no authentication):
- `GET /health` - Health check
- `GET /docs` - API documentation
- `GET /openapi.json` - OpenAPI schema

**Authenticated Endpoints** (require Cloudflare Access JWT):
- `GET /api/me` - Get current user profile
- `GET /api/v1/data/storage` - View MinIO/blob storage files (with optional `prefix` parameter)
- `GET /api/v1/data/supabase` - View Supabase table data (with `table`, `page`, `per_page` parameters)
- `GET /api/v1/data/neo4j` - View Neo4j graph data (with optional `node_type` parameter)
- `GET /api/v1/data/mongodb` - View MongoDB collection data (with `collection`, `page`, `per_page` parameters)
- `GET /test/my-data` - Test endpoint for Supabase data isolation
- `GET /test/my-images` - Test endpoint for MinIO data isolation

**RAG Endpoints** (authenticated):
- `POST /api/v1/rag/search` - Search knowledge base
- `POST /api/v1/rag/ingest` - Ingest documents
- `POST /api/v1/rag/agent` - Agent query

**Discord Character Endpoints** (authenticated):
- `POST /api/v1/discord-characters/add` - Add character to channel
- `POST /api/v1/discord-characters/remove` - Remove character from channel
- `POST /api/v1/discord-characters/list` - List active characters
- `POST /api/v1/discord-characters/clear-history` - Clear conversation history
- `POST /api/v1/discord-characters/engage` - Engage character in conversation

**MCP Endpoints** (internal network only, no authentication):
- `POST /mcp/tools/list` - List MCP tools
- `POST /mcp/tools/call` - Call MCP tool

See [Lambda README](../04-lambda/README.md) and [Auth Project README](../04-lambda/server/projects/auth/README.md) for complete API reference

**Integration Points**: Open WebUI (MCP), n8n (MCP tools), MongoDB, Neo4j, Supabase, MinIO, Ollama, SearXNG

## Service Dependencies Summary

### Critical Dependencies

**Lambda Server**:
- Requires: MongoDB, Neo4j (optional), Supabase (PostgreSQL), MinIO, Ollama
- Provides: MCP tools, REST APIs, authentication system, data viewing APIs

**Open WebUI**:
- Requires: PostgreSQL (Supabase), Ollama, Lambda Server
- Provides: Chat interface

**n8n**:
- Requires: PostgreSQL (Supabase), Ollama (optional), Lambda Server (optional)
- Provides: Workflow automation

**Immich**:
- Requires: PostgreSQL (dedicated), Typesense, Redis
- Provides: Photo/video management

**Langfuse**:
- Requires: PostgreSQL (Supabase), ClickHouse, MinIO
- Provides: LLM observability

## Network Communication

All services communicate via the `ai-network` Docker network using container names:

- `n8n:5678` - n8n API
- `open-webui:8080` - Open WebUI API
- `lambda-server:8000` - Lambda REST API and MCP
- `immich-server:2283` - Immich API
- `supabase-db:5432` - PostgreSQL database
- `ollama:11434` - Ollama LLM API
- `mongodb:27017` - MongoDB
- `neo4j:7687` - Neo4j (Bolt protocol)
- `qdrant:6333` - Qdrant API

## Port Summary

### Infrastructure
- `80, 443` - Caddy (HTTP/HTTPS)
- `6379` - Redis/Valkey
- `8020` - Infisical

### Data
- `5432` - PostgreSQL (Supabase, Infisical, Immich)
- `6333` - Qdrant
- `7474, 7687` - Neo4j
- `27017` - MongoDB
- `9000, 9001` - MinIO (Langfuse)
- `9020, 9021` - MinIO (Supabase)

### Compute
- `11434` - Ollama
- `8188` - ComfyUI

### Apps
- `5678` - n8n
- `3001` - Flowise
- `8080` - Open WebUI
- `8081` - SearXNG
- `3000` - Langfuse
- `2283` - Immich
- `8001` - Discord Bot (MCP, optional)
- `8123, 9000` - ClickHouse
- `8108` - Typesense

### Lambda
- `8000` - Lambda Server

## Further Reading

- [Architecture Documentation](ARCHITECTURE.md) - System architecture
- [Workflows Documentation](WORKFLOWS.md) - Workflow documentation
- [MCP Integration](MCP_INTEGRATION.md) - MCP tools guide
- [Main README](../README.md) - Project overview
- [Apps Stack README](../03-apps/README.md) - Application services
- [Lambda Server README](../04-lambda/README.md) - Lambda API reference
