# Lambda Stack - FastAPI Multi-Project Server

FastAPI server providing REST APIs and MCP (Model Context Protocol) endpoints for multiple projects.

## Architecture

```
04-lambda/
├── server/               # FastAPI application
│   ├── api/             # REST API endpoints
│   ├── mcp/             # MCP server implementation
│   ├── projects/        # Project modules (RAG, etc.)
│   ├── models/          # Pydantic schemas
│   └── core/            # Shared utilities
├── uploads/             # Document upload storage
└── _archive/            # Original MongoDB-RAG-Agent (reference)
```

## Services

### lambda-server
- **Container**: `lambda-server`
- **Port**: 8000 (internal)
- **Network**: `ai-network`
- **Dependencies**: MongoDB (01-data), Neo4j (01-data), Ollama (02-compute)

## API Endpoints

### Health Checks
- `GET /health` - Basic health check
- `GET /health/mongodb` - MongoDB connectivity check

### MongoDB RAG Project
- `POST /api/v1/rag/search` - Search knowledge base (hybrid: semantic + text)
- `POST /api/v1/rag/ingest` - Upload and ingest documents
- `POST /api/v1/rag/agent` - Query conversational agent
- `POST /api/v1/rag/code-examples/search` - Search for code examples
- `GET /api/v1/rag/sources` - Get available data sources

### Graphiti RAG Project
- `POST /api/v1/graphiti/search` - Search Graphiti knowledge graph
- `POST /api/v1/graphiti/knowledge-graph/repositories` - Parse GitHub repository into knowledge graph
- `POST /api/v1/graphiti/knowledge-graph/validate` - Validate AI script for hallucinations
- `POST /api/v1/graphiti/knowledge-graph/query` - Query Neo4j knowledge graph

### MCP Server
- `POST /mcp/tools/list` - List available MCP tools
- `POST /mcp/tools/call` - Execute MCP tool

## Configuration

Environment variables (see `.env.example`):

```bash
# MongoDB (Docker internal)
MONGODB_URI=mongodb://admin:admin123@mongodb:27017/?replicaSet=rs0
MONGODB_DATABASE=rag_db

# LLM (Ollama default)
LLM_PROVIDER=ollama
LLM_MODEL=llama3.2
LLM_BASE_URL=http://ollama:11434/v1

# Embeddings (Ollama default)
EMBEDDING_PROVIDER=ollama
EMBEDDING_MODEL=nomic-embed-text
EMBEDDING_BASE_URL=http://ollama:11434/v1
EMBEDDING_DIMENSION=768

# Neo4j (for Graphiti and knowledge graph)
NEO4J_URI=bolt://neo4j:7687
NEO4J_USER=neo4j
NEO4J_PASSWORD=password
NEO4J_DATABASE=neo4j

# Feature Flags
USE_GRAPHITI=false  # Enable Graphiti knowledge graph RAG
USE_KNOWLEDGE_GRAPH=false  # Enable code structure knowledge graph
USE_CONTEXTUAL_EMBEDDINGS=false  # Enable contextual embeddings
USE_AGENTIC_RAG=false  # Enable code example extraction and search
USE_RERANKING=false  # Enable cross-encoder reranking
```

## Usage

### Start Lambda Stack

```bash
# Start all stacks including lambda
python start_services.py

# Start only lambda stack (requires infrastructure, data, compute)
python start_services.py --stack lambda

# Stop lambda stack
python start_services.py --action stop --stack lambda
```

### Access API

```bash
# Health check
curl http://lambda-server:8000/health

# Search knowledge base
curl -X POST http://lambda-server:8000/api/v1/rag/search \
  -H "Content-Type: application/json" \
  -d '{"query": "What is RAG?", "search_type": "hybrid", "match_count": 5}'

# Search code examples
curl -X POST http://lambda-server:8000/api/v1/rag/code-examples/search \
  -H "Content-Type: application/json" \
  -d '{"query": "authentication", "match_count": 5}'

# Search Graphiti knowledge graph
curl -X POST http://lambda-server:8000/api/v1/graphiti/search \
  -H "Content-Type: application/json" \
  -d '{"query": "authentication", "match_count": 5}'

# List MCP tools
curl -X POST http://lambda-server:8000/mcp/tools/list
```

## Development

### Local Development

```bash
cd 04-lambda

# Create virtual environment
uv venv
source .venv/bin/activate

# Install dependencies
uv pip install -e .

# Run locally (requires MongoDB and Ollama running)
uvicorn server.main:app --reload --host 0.0.0.0 --port 8000
```

### Adding New Projects

1. Create project folder: `server/projects/your_project/`
2. Implement project logic (config, dependencies, tools)
3. Create API router: `server/api/your_project.py`
4. Register router in `server/main.py`
5. Add MCP tools in `server/mcp/server.py`

## Projects

### MongoDB RAG (Retrieval Augmented Generation)
- **Location**: `server/projects/mongo_rag/`
- **Features**: 
  - Hybrid search (semantic + text using Reciprocal Rank Fusion)
  - Document ingestion with chunking and embedding
  - Conversational agent with automatic search
  - Code example extraction and search (Agentic RAG)
  - Contextual embeddings (optional)
  - Cross-encoder reranking (optional)
- **Database**: MongoDB Atlas Local (vector + full-text search)
- **LLM**: Ollama (llama3.2)
- **Embeddings**: Ollama (nomic-embed-text)

### Graphiti RAG (Knowledge Graph RAG)
- **Location**: `server/projects/graphiti_rag/`
- **Features**:
  - Graph-based search using Graphiti
  - Temporal fact storage with source metadata
  - GitHub repository parsing for code structure
  - AI script hallucination detection
  - Knowledge graph querying (Cypher)
- **Database**: Neo4j (01-data stack)
- **Integration**: Works alongside MongoDB RAG for hybrid search

## Dependencies

- FastAPI 0.115+
- Pydantic AI 0.1+
- PyMongo 4.10+ (async)
- OpenAI 1.58+ (for embeddings API)
- Docling 2.14+ (document processing)
- Transformers 4.47+ (for Docling)
- Graphiti Core 1.0+ (with Neo4j extras) - Knowledge graph RAG
- Neo4j Python Driver 5.0+ - Neo4j connectivity
- Sentence Transformers 4.1+ - Reranking support

## Troubleshooting

### MongoDB Connection Issues
```bash
# Check MongoDB is running
docker ps | grep mongodb

# Test connection
docker exec mongodb mongosh --eval "db.adminCommand('ping')"

# Check Lambda server logs
docker logs lambda-server
```

### Ollama Issues
```bash
# Check Ollama is running
docker ps | grep ollama

# Pull required models
docker exec ollama ollama pull llama3.2
docker exec ollama ollama pull nomic-embed-text
```

### Build Issues
```bash
# Rebuild Lambda container
cd 04-lambda
docker compose build --no-cache

# Check build logs
docker compose logs lambda-server
```

## Stack Integration

Lambda stack depends on:
- **00-infrastructure**: Network (`ai-network`)
- **01-data**: MongoDB, Neo4j (optional, for Graphiti)
- **02-compute**: Ollama (LLM + embeddings)

Start order: infrastructure → data → compute → lambda

**Note**: Neo4j is optional and only required if `USE_GRAPHITI=true` or `USE_KNOWLEDGE_GRAPH=true`.

