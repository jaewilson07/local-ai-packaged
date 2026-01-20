# Apps Stack - Application Services

The Apps stack provides workflow automation, AI interfaces, observability, and media management services.

## Overview

The Apps stack includes:
- **Workflow Automation**: n8n, Flowise
- **AI Interfaces**: Open WebUI, SearXNG
- **Observability**: Langfuse, ClickHouse
- **Media Management**: Immich, Discord Bot
- **Storage**: MinIO (for Langfuse)

All services run on the `ai-network` Docker network and can communicate using container names as hostnames.

## Services

### n8n - Workflow Automation

**Container**: `n8n`  
**Port**: 5678 (internal)  
**Access**: `http://n8n:5678` (internal) or via Caddy reverse proxy

**Description**: Low-code workflow automation platform with 400+ integrations and advanced AI components.

**Features**:
- Visual workflow builder
- AI Agent nodes for LLM interactions
- Integration with Ollama for local LLMs
- Webhook triggers and HTTP requests
- Database connections (PostgreSQL via Supabase)
- Vector store integration (Qdrant)

**Dependencies**:
- PostgreSQL (Supabase) for workflow storage
- Ollama (02-compute) for AI nodes
- Qdrant (01-data) for vector operations

**Integration Points**:
- Lambda server MCP tools for RAG and knowledge graph operations
- Open WebUI for AI agent workflows
- Supabase for data storage

**Configuration**:
- Database: Uses shared `x-database-env` anchor (Supabase PostgreSQL)
- Ollama: Configure via UI (Settings → Credentials → Ollama)
  - Docker: `http://ollama:11434`
  - Local (Mac): `http://host.docker.internal:11434`

### Flowise - AI Agent Builder

**Container**: `flowise`  
**Port**: 3001 (internal)  
**Access**: `http://flowise:3001` (internal) or via Caddy reverse proxy

**Description**: No-code AI agent builder that pairs well with n8n for creating conversational AI agents.

**Features**:
- Visual agent builder
- LLM chain creation
- Memory management
- Tool integration

**Dependencies**:
- Ollama (02-compute) for LLM inference

**Integration Points**:
- Can be used alongside n8n workflows
- Integrates with local Ollama models

### Open WebUI - AI Chat Interface

**Container**: `open-webui`  
**Port**: 8080 (internal)  
**Access**: `http://open-webui:8080` (internal) or via Caddy reverse proxy

**Description**: ChatGPT-like interface for privately interacting with local LLMs and N8N agents.

**Features**:
- Conversation interface for local LLMs
- PostgreSQL storage for conversation persistence
- Google OAuth integration (optional)
- MCP server integration for Lambda tools
- Function calling for n8n workflow integration

**Dependencies**:
- PostgreSQL (Supabase) for conversation storage
- Ollama (02-compute) for LLM inference
- Lambda server (04-lambda) for MCP tools and RAG

**Integration Points**:
- Lambda server: MCP protocol for RAG, knowledge graphs, calendar, etc.
- n8n: Function calling via `n8n_pipe.py` function
- PostgreSQL: Conversation persistence and topic classification

**Configuration**:
- Database: Uses shared `x-database-env` anchor (Supabase PostgreSQL)
- Lambda Integration: `LAMBDA_SERVER_URL=http://lambda-server:8000`
- OAuth: Configure via `ENABLE_OAUTH_SIGNUP`, `GOOGLE_CLIENT_ID`, `GOOGLE_CLIENT_SECRET`

### SearXNG - Privacy-Focused Search

**Container**: `searxng`  
**Port**: 8081 (internal)  
**Access**: `http://searxng:8081` (internal) or via Caddy reverse proxy

**Description**: Open source, privacy-focused metasearch engine that aggregates results from up to 229 search services without tracking or profiling users.

**Features**:
- Privacy-focused search
- Multiple search engine aggregation
- No user tracking or profiling
- Self-hosted search results

**Integration Points**:
- Lambda server: Web search MCP tool uses SearXNG backend
- Can be used in n8n workflows for web search

### Langfuse - LLM Observability

**Container**: `langfuse`  
**Port**: 3000 (internal)  
**Access**: `http://langfuse:3000` (internal) or via Caddy reverse proxy

**Description**: Open source LLM engineering platform for agent observability, tracing, and analytics.

**Features**:
- LLM trace collection
- Performance analytics
- Cost tracking
- Prompt management
- Evaluation and testing

**Dependencies**:
- PostgreSQL (Supabase) for metadata storage
- ClickHouse for trace data storage
- MinIO for object storage

**Integration Points**:
- Can trace LLM calls from Lambda server
- Integrates with Open WebUI for conversation analytics

### ClickHouse - Analytics Database

**Container**: `clickhouse`  
**Port**: 8123 (HTTP), 9000 (Native)  
**Access**: `http://clickhouse:8123` (internal)

**Description**: Column-oriented database optimized for analytics and real-time queries.

**Features**:
- High-performance analytics
- Real-time querying
- Columnar storage

**Dependencies**: None (standalone service)

**Integration Points**:
- Langfuse uses ClickHouse for trace data storage

### Immich - Photo/Video Management

**Container**: `immich-server`, `immich-microservices`, `immich-machine-learning`  
**Port**: 2283 (server)  
**Access**: `http://immich-server:2283` (internal) or via Caddy reverse proxy

**Description**: Self-hosted photo and video backup solution with face detection, metadata search, and social features.

**Features**:
- Photo and video backup
- Face detection using Buffalo_L model
- Metadata search via Typesense
- Video transcoding (with optional GPU acceleration)
- Social features (comments, reactions via frontend)

**Dependencies**:
- PostgreSQL (dedicated `immich-postgres`) for metadata
- Typesense for text search
- Redis (00-infrastructure) for caching

**Integration Points**:
- Discord bot: Automatic uploads from Discord channels
- Frontend: Social features (comments, reactions)
- Lambda server: Can be integrated via REST API

**Configuration**:
- Database: Dedicated PostgreSQL instance
- Typesense: Embedded Typesense service
- GPU: Optional GPU acceleration for video transcoding

### Discord Bot - Immich Integration

**Container**: `discord-bot`  
**Port**: 8001 (MCP server, optional)  
**Access**: `http://discord-bot:8001/mcp` (MCP server, internal)

**Description**: Discord bot that bridges Discord uploads to Immich, manages user face mapping, and sends automated notifications.

**Features**:
- Drag-and-drop file ingestion from Discord channels
- User face mapping via `/claim_face` command
- Automated notifications when users detected in photos
- MCP server for Discord management tools

**Dependencies**:
- Immich API for photo/video uploads
- SQLite database for user-face mappings

**Integration Points**:
- Immich: Automatic uploads and face detection integration
- Lambda server: MCP tools for Discord management (optional)

**MCP Tools** (when MCP server enabled):
- Server information (list servers, get channels, list members)
- Message management (send, read, react, moderate)
- Channel management (create, delete, move)
- Event management (create, edit scheduled events)
- Role management (add, remove roles)

See [discord-bot/README.md](discord-bot/README.md) for detailed setup and usage.

### MinIO - Object Storage

**Container**: `minio` (for Langfuse)  
**Port**: 9000 (API), 9001 (Console)  
**Access**: `http://minio:9000` (API, internal)

**Description**: S3-compatible object storage for Langfuse trace data and artifacts.

**Features**:
- S3-compatible API
- Web console for management
- Object storage for LLM traces

**Dependencies**: None (standalone service)

**Integration Points**:
- Langfuse uses MinIO for storing trace artifacts

## Service Interconnections

### Data Flow Examples

**n8n → Lambda → RAG Workflow**:
1. n8n workflow triggers on webhook
2. Calls Lambda MCP tool `search_knowledge_base`
3. Lambda searches MongoDB RAG
4. Returns results to n8n
5. n8n processes and responds

**Open WebUI → Lambda → RAG Workflow**:
1. User asks question in Open WebUI
2. Open WebUI calls Lambda MCP tool `agent_query`
3. Lambda agent searches knowledge base
4. LLM generates response using retrieved context
5. Response returned to Open WebUI

**Discord → Immich Workflow**:
1. User uploads photo to Discord `#event-uploads`
2. Discord bot downloads file
3. Bot uploads to Immich via REST API
4. Immich processes (face detection, metadata extraction)
5. Bot sends confirmation message

**Conversation Export Workflow**:
1. User chats in Open WebUI
2. Conversations stored in PostgreSQL
3. Lambda tool `export_openwebui_conversation` exports to MongoDB RAG
4. Conversations become searchable via vector search
5. Topics classified via `classify_conversation_topics`

### Network Communication

All services communicate via the `ai-network` Docker network using container names:

- `n8n:5678` - n8n API
- `open-webui:8080` - Open WebUI API
- `lambda-server:8000` - Lambda REST API and MCP
- `immich-server:2283` - Immich API
- `supabase-db:5432` - PostgreSQL database
- `ollama:11434` - Ollama LLM API
- `mongodb:27017` - MongoDB
- `neo4j:7687` - Neo4j (Bolt protocol)

## Starting the Apps Stack

```bash
# Start all apps services
python start_services.py --stack apps

# Start with specific profile
python start_services.py --profile gpu-nvidia --stack apps

# Stop apps stack
python start_services.py --action stop --stack apps
```

## Configuration

All services use environment variables from the root `.env` file. Key variables:

- `N8N_HOSTNAME` - n8n hostname (e.g., `n8n.datacrew.space` or `:5678`)
- `WEBUI_HOSTNAME` - Open WebUI hostname
- `FLOWISE_HOSTNAME` - Flowise hostname
- `SEARXNG_HOSTNAME` - SearXNG hostname
- `LANGFUSE_HOSTNAME` - Langfuse hostname
- `IMMICH_HOSTNAME` - Immich hostname
- `LAMBDA_SERVER_URL` - Lambda server URL for MCP integration
- `POSTGRES_PASSWORD` - Shared PostgreSQL password (Supabase)

## Troubleshooting

### Service Not Accessible

1. Check service is running: `docker compose -p localai-apps ps`
2. Check logs: `docker compose -p localai-apps logs <service-name>`
3. Verify network: `docker network inspect ai-network`
4. Check health: `curl http://<service-name>:<port>/health`

### Database Connection Issues

1. Verify Supabase is running: `docker compose -p localai-data ps supabase-db`
2. Check credentials in `.env` file
3. Test connection: `docker exec supabase-db psql -U postgres -c "SELECT 1"`

### MCP Integration Issues

1. Verify Lambda server is running: `docker compose -p localai-lambda ps`
2. Check Lambda logs: `docker compose -p localai-lambda logs lambda-server`
3. Test MCP endpoint: `curl http://lambda-server:8000/mcp/tools/list`
4. Verify Open WebUI MCP configuration

## Further Reading

- [Main README](../README.md) - Overall project overview
- [Lambda Server README](../04-lambda/README.md) - MCP tools and REST APIs
- [Root AGENTS.md](../AGENTS.md) - Architecture and rules
- [Apps Stack AGENTS.md](./AGENTS.md) - Apps stack details
