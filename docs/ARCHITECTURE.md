# System Architecture

This document describes the overall architecture of the local-ai-packaged infrastructure, including service dependencies, data flows, and network topology.

## Architecture Overview

The system is organized into numbered stacks with explicit dependencies:

```
00-infrastructure → 01-data → 02-compute → 03-apps → 04-lambda
     ↓                ↓           ↓           ↓          ↓
  (network)      (databases)  (AI models)  (apps)   (APIs/MCP)
```

## Stack Organization

### 00-infrastructure
**Purpose**: Foundation services (networking, reverse proxy, secrets management)  
**Project**: `localai-infra`  
**Services**:
- `cloudflared` - Cloudflare Tunnel (optional, for public access)
- `caddy` - Reverse proxy with automatic HTTPS
- `redis` - Caching and session storage

**Network**: Creates `ai-network` (external network shared by all stacks)

### 00-infrastructure/infisical
**Purpose**: Secret management  
**Project**: `localai-infisical`  
**Services**:
- `infisical-backend` - Infisical API server
- `infisical-db` - PostgreSQL for Infisical metadata
- `infisical-redis` - Redis for Infisical caching

### 01-data
**Purpose**: Data storage layer  
**Project**: `localai-data`  
**Services**:
- `supabase-db` - PostgreSQL database
- `supabase-kong` - API gateway
- `supabase-studio` - Admin UI
- `qdrant` - Vector database
- `neo4j` - Graph database (for Graphiti, knowledge graphs)
- `mongodb` - Document database (for RAG)
- `minio` - Object storage (S3-compatible)

**Dependencies**: Requires `00-infrastructure` (network)

### 02-compute
**Purpose**: AI compute services  
**Project**: `localai-compute`  
**Services**:
- `ollama` - LLM inference server
- `comfyui` - Stable diffusion image generation

**Dependencies**: Requires `00-infrastructure` (network), `01-data` (optional, for model storage)

### 03-apps
**Purpose**: Application layer  
**Project**: `localai-apps`  
**Services**:
- `n8n` - Workflow automation
- `flowise` - AI agent builder
- `open-webui` - Chat interface
- `searxng` - Privacy-focused search
- `langfuse` - LLM observability
- `clickhouse` - Analytics database
- `immich-server` - Photo/video management
- `immich-microservices` - Background jobs
- `immich-machine-learning` - Face detection
- `discord-bot` - Discord integration (Immich)
- `discord-character-bot` - Discord AI character bot
- `minio` - Object storage (for Langfuse)

**Dependencies**: Requires `00-infrastructure`, `01-data`, `02-compute`

### 04-lambda
**Purpose**: FastAPI server with MCP and REST APIs  
**Project**: `localai-lambda`  
**Services**:
- `lambda-server` - FastAPI application with 40+ MCP tools

**Dependencies**: Requires `00-infrastructure`, `01-data` (MongoDB, Neo4j), `02-compute` (Ollama)

## Network Architecture

```mermaid
graph TB
    subgraph Internet
        User[User Browser]
        Cloudflare[Cloudflare Tunnel]
    end
    
    subgraph Infrastructure["00-infrastructure"]
        Caddy[Caddy Reverse Proxy]
        Redis[Redis Cache]
    end
    
    subgraph Data["01-data"]
        Supabase[(Supabase PostgreSQL)]
        Qdrant[(Qdrant Vector DB)]
        Neo4j[(Neo4j Graph DB)]
        MongoDB[(MongoDB Document DB)]
    end
    
    subgraph Compute["02-compute"]
        Ollama[Ollama LLM]
        ComfyUI[ComfyUI]
    end
    
    subgraph Apps["03-apps"]
        N8N[n8n]
        OpenWebUI[Open WebUI]
        Flowise[Flowise]
        SearXNG[SearXNG]
        Langfuse[Langfuse]
        Immich[Immich]
        DiscordBot[Discord Bot]
        DiscordCharBot[Discord Character Bot]
    end
    
    subgraph Lambda["04-lambda"]
        LambdaServer[Lambda Server]
    end
    
    User -->|HTTPS| Cloudflare
    Cloudflare -->|Tunnel| Caddy
    Caddy -->|Route| N8N
    Caddy -->|Route| OpenWebUI
    Caddy -->|Route| Flowise
    Caddy -->|Route| SearXNG
    Caddy -->|Route| Langfuse
    Caddy -->|Route| Immich
    Caddy -->|Route| LambdaServer
    
    N8N -->|PostgreSQL| Supabase
    N8N -->|Vector Search| Qdrant
    N8N -->|LLM| Ollama
    N8N -->|MCP Tools| LambdaServer
    
    OpenWebUI -->|PostgreSQL| Supabase
    OpenWebUI -->|LLM| Ollama
    OpenWebUI -->|MCP| LambdaServer
    
    LambdaServer -->|RAG| MongoDB
    LambdaServer -->|Knowledge Graph| Neo4j
    LambdaServer -->|LLM| Ollama
    LambdaServer -->|Embeddings| Ollama
    LambdaServer -->|Web Search| SearXNG
    LambdaServer -->|Workflows| N8N
    
    DiscordBot -->|Upload| Immich
    Immich -->|PostgreSQL| Supabase
    
    DiscordCharBot -->|Character API| LambdaServer
    LambdaServer -->|Persona| MongoDB
    
    Langfuse -->|Analytics| ClickHouse
    Langfuse -->|Storage| MinIO
```

## Service Dependencies

### Dependency Graph

```mermaid
graph TD
    Infra[00-infrastructure] -->|Creates Network| Data[01-data]
    Infra -->|Creates Network| Compute[02-compute]
    Infra -->|Creates Network| Apps[03-apps]
    Infra -->|Creates Network| Lambda[04-lambda]
    
    Data -->|Provides DB| Compute
    Data -->|Provides DB| Apps
    Data -->|Provides DB| Lambda
    
    Compute -->|Provides LLM| Apps
    Compute -->|Provides LLM| Lambda
    
    Apps -->|Uses MCP| Lambda
    Apps -->|Uses DB| Data
    Apps -->|Uses LLM| Compute
```

### Critical Dependencies

**Lambda Server**:
- Requires: MongoDB (RAG), Neo4j (Graphiti), Ollama (LLM + embeddings)
- Provides: MCP tools, REST APIs

**Open WebUI**:
- Requires: PostgreSQL (Supabase), Ollama, Lambda Server (MCP)
- Provides: Chat interface

**n8n**:
- Requires: PostgreSQL (Supabase), Ollama, Qdrant (optional), Lambda Server (MCP tools)
- Provides: Workflow automation

**Immich**:
- Requires: PostgreSQL (dedicated), Typesense, Redis
- Provides: Photo/video management

## Data Flow Diagrams

### Document Ingestion Flow

```mermaid
sequenceDiagram
    participant User
    participant Lambda
    participant MongoDB
    participant Ollama
    
    User->>Lambda: POST /api/v1/rag/ingest (file)
    Lambda->>Lambda: Process document (Docling)
    Lambda->>Lambda: Chunk document
    Lambda->>Ollama: Generate embeddings
    Ollama-->>Lambda: Embeddings
    Lambda->>MongoDB: Store chunks + embeddings
    MongoDB-->>Lambda: Confirmation
    Lambda-->>User: Ingestion complete
```

### RAG Search Flow

```mermaid
sequenceDiagram
    participant User
    participant OpenWebUI
    participant Lambda
    participant MongoDB
    participant Ollama
    
    User->>OpenWebUI: Ask question
    OpenWebUI->>Lambda: MCP: agent_query(query)
    Lambda->>Ollama: Generate query embedding
    Ollama-->>Lambda: Query embedding
    Lambda->>MongoDB: Vector search + text search
    MongoDB-->>Lambda: Relevant chunks
    Lambda->>Ollama: Generate response (with context)
    Ollama-->>Lambda: Response
    Lambda-->>OpenWebUI: Answer
    OpenWebUI-->>User: Display answer
```

### Conversation Export Flow

```mermaid
sequenceDiagram
    participant User
    participant OpenWebUI
    participant Lambda
    participant PostgreSQL
    participant MongoDB
    
    User->>OpenWebUI: Chat conversation
    OpenWebUI->>PostgreSQL: Store messages
    User->>OpenWebUI: Export conversation
    OpenWebUI->>Lambda: MCP: export_openwebui_conversation
    Lambda->>PostgreSQL: Fetch conversation
    PostgreSQL-->>Lambda: Messages
    Lambda->>Lambda: Format as document
    Lambda->>Lambda: Chunk and embed
    Lambda->>MongoDB: Store in RAG
    MongoDB-->>Lambda: Confirmation
    Lambda-->>OpenWebUI: Export complete
```

### Discord → Immich Flow

```mermaid
sequenceDiagram
    participant User
    participant Discord
    participant Bot
    participant Immich
    participant ML
    
    User->>Discord: Upload photo to #event-uploads
    Discord->>Bot: Message event
    Bot->>Bot: Download file
    Bot->>Immich: POST /api/asset/upload
    Immich->>ML: Process image (face detection)
    ML-->>Immich: Face detections
    Immich-->>Bot: Upload confirmation
    Bot->>Discord: Reply with confirmation
    Immich->>Bot: New asset with faces (polling)
    Bot->>Discord: DM user (if face claimed)
```

### N8N Workflow Orchestration Flow

```mermaid
sequenceDiagram
    participant Trigger
    participant N8N
    participant Lambda
    participant MongoDB
    participant Ollama
    
    Trigger->>N8N: Webhook/Schedule/File
    N8N->>Lambda: HTTP: MCP tool call
    Lambda->>MongoDB: Search knowledge base
    MongoDB-->>Lambda: Results
    Lambda->>Ollama: Generate response
    Ollama-->>Lambda: Response
    Lambda-->>N8N: Tool result
    N8N->>N8N: Process workflow
    N8N-->>Trigger: Response/Webhook
```

## API Gateway Architecture

Caddy acts as the reverse proxy for all services:

```mermaid
graph LR
    subgraph Caddy["Caddy Reverse Proxy"]
        Router[Request Router]
    end
    
    subgraph Services
        N8N[n8n:5678]
        WebUI[Open WebUI:8080]
        Flowise[Flowise:3001]
        SearXNG[SearXNG:8081]
        Langfuse[Langfuse:3000]
        Immich[Immich:2283]
        Lambda[Lambda:8000]
    end
    
    Router -->|n8n.datacrew.space| N8N
    Router -->|webui.datacrew.space| WebUI
    Router -->|flowise.datacrew.space| Flowise
    Router -->|searxng.datacrew.space| SearXNG
    Router -->|langfuse.datacrew.space| Langfuse
    Router -->|immich.datacrew.space| Immich
    Router -->|lambda.datacrew.space| Lambda
```

### Routing Rules

- **Private Mode**: Services exposed on ports (e.g., `localhost:5678`)
- **Public Mode**: All traffic via Caddy on ports 80/443
- **Cloudflare Tunnel**: Optional, routes through Cloudflare before Caddy

## Database Architecture

### PostgreSQL (Supabase)
- **Purpose**: Primary relational database
- **Used by**: n8n, Open WebUI, Supabase services
- **Schema**: Multiple schemas for different services

### MongoDB
- **Purpose**: Document database for RAG
- **Used by**: Lambda server (MongoDB RAG project)
- **Features**: Vector search, full-text search, Atlas Local

### Neo4j
- **Purpose**: Graph database for knowledge graphs
- **Used by**: Lambda server (Graphiti RAG, knowledge graph)
- **Protocol**: Bolt protocol

### Qdrant
- **Purpose**: High-performance vector database
- **Used by**: n8n (optional, for vector operations)
- **Features**: Fast vector similarity search

### ClickHouse
- **Purpose**: Analytics database
- **Used by**: Langfuse (trace data storage)
- **Features**: Column-oriented, optimized for analytics

## Security Architecture

### Network Isolation
- All services on `ai-network` (Docker network)
- Services communicate via container names
- No direct external access (except via Caddy/Cloudflare)

### Authentication
- **Open WebUI**: Google OAuth (optional), local accounts
- **n8n**: Local accounts, Google OIDC (optional)
- **Infisical**: Admin account, machine identity
- **Immich**: First user is admin

### Secret Management
- **Primary**: Infisical (optional, can use `.env` files)
- **Fallback**: `.env` files in repository root
- **Best Practice**: Use Infisical for production, `.env` for development

## Scaling Considerations

### Horizontal Scaling
- **Stateless Services**: Lambda server, Open WebUI (with shared PostgreSQL)
- **Stateful Services**: Databases require shared storage/replication

### Vertical Scaling
- **GPU Services**: Ollama, ComfyUI, Immich (video transcoding)
- **CPU Services**: Most services can scale with more CPU cores

### Resource Requirements
- **Minimum**: 8GB RAM, 4 CPU cores
- **Recommended**: 16GB+ RAM, 8+ CPU cores, GPU for AI workloads
- **GPU**: NVIDIA GPU recommended for Ollama, ComfyUI, Immich

## Monitoring and Observability

### Logging
- **Format**: JSON logs (via Docker logging driver)
- **Retention**: 1 file, 1MB max per service
- **Access**: `docker compose logs <service>`

### Metrics
- **Langfuse**: LLM trace collection and analytics
- **ClickHouse**: Analytics database for Langfuse traces

### Health Checks
- All services have HTTP health check endpoints
- Docker health checks configured for automatic restart

## Deployment Modes

### Private Mode (Development)
- All ports exposed directly
- No reverse proxy required
- Direct access: `localhost:<port>`

### Public Mode (Production)
- Only ports 80/443 exposed
- All traffic via Caddy reverse proxy
- Domain-based routing

### Cloudflare Tunnel Mode
- No port forwarding required
- Works behind NAT/firewalls
- Origin IP hidden
- Free SSL certificates

## Further Reading

- [Workflows Documentation](WORKFLOWS.md) - Detailed workflow documentation
- [Services Documentation](SERVICES.md) - Complete service catalog
- [MCP Integration](MCP_INTEGRATION.md) - MCP server and tools guide
- [Main README](../README.md) - Project overview
