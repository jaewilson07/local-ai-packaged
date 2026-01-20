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

## MCP Tools Reference

The Lambda server provides 40+ MCP tools organized into the following categories:

### MongoDB RAG Tools

**`search_knowledge_base`** - Search the MongoDB RAG knowledge base
- Parameters: `query` (str), `match_count` (int, 1-50, default: 5), `search_type` ("semantic" | "text" | "hybrid", default: "hybrid")
- Returns: Search results with metadata and relevance scores
- Use cases: Finding information from ingested documents, web pages, conversations

**`agent_query`** - Query the conversational RAG agent
- Parameters: `query` (str)
- Returns: Natural language response with synthesized information
- Use cases: Asking questions that require knowledge base search and synthesis

**`ingest_documents`** - Ingest documents into knowledge base
- Parameters: `file_paths` (List[str]), `clean_before` (bool, default: false)
- Note: Files must be on server filesystem. Use REST API for file uploads.
- Returns: Ingestion status
- Use cases: Adding documents to knowledge base (via REST API recommended)

**`search_code_examples`** - Search for code examples
- Parameters: `query` (str), `match_count` (int, 1-50, default: 5)
- Requires: `USE_AGENTIC_RAG=true`
- Returns: Code snippets with summaries, language, and context
- Use cases: Finding code examples from ingested repositories

**`get_available_sources`** - Get all available data sources
- Parameters: None
- Returns: List of sources (domains/paths) with summaries and statistics
- Use cases: Discovering what content has been ingested

### Graphiti RAG Tools

**`search_graphiti`** - Search the Graphiti knowledge graph
- Parameters: `query` (str), `match_count` (int, default: 10)
- Requires: `USE_GRAPHITI=true`
- Returns: Facts with temporal information and source metadata
- Use cases: Finding relationships and entities in knowledge graph

**`parse_github_repository`** - Parse GitHub repository into knowledge graph
- Parameters: `repo_url` (str, must end with .git)
- Requires: `USE_KNOWLEDGE_GRAPH=true`
- Returns: Parse results with extracted classes, methods, functions
- Use cases: Analyzing code structure and relationships

**`check_ai_script_hallucinations`** - Validate AI-generated script
- Parameters: `script_path` (str, absolute path on server)
- Requires: `USE_KNOWLEDGE_GRAPH=true`
- Returns: Validation results for imports, method calls, class instantiations
- Use cases: Verifying AI-generated code against real repository data

**`query_knowledge_graph`** - Query Neo4j knowledge graph
- Parameters: `command` (str)
- Requires: `USE_KNOWLEDGE_GRAPH=true`
- Commands: `repos`, `explore <repo>`, `classes [repo]`, `class <name>`, `method <name> [class]`, `query <cypher>`
- Returns: Query results based on command
- Use cases: Exploring code structure, finding classes/methods

### Crawl4AI Tools

**`crawl_single_page`** - Crawl a single web page
- Parameters: `url` (str), `chunk_size` (int, 100-5000, default: 1000), `chunk_overlap` (int, 0-500, default: 200)
- Returns: Crawl results with automatic ingestion into MongoDB RAG
- Use cases: Adding single page to knowledge base

**`crawl_deep`** - Deep crawl website recursively
- Parameters: `url` (str), `max_depth` (int, 1-10), `allowed_domains` (List[str], optional), `allowed_subdomains` (List[str], optional), `chunk_size` (int, default: 1000), `chunk_overlap` (int, default: 200)
- Returns: Crawl results with all discovered pages ingested
- Use cases: Crawling entire websites for knowledge base

**`web_search`** - Search the web using SearXNG
- Parameters: `query` (str), `result_count` (int, 1-20, default: 10), `categories` (str, optional), `engines` (List[str], optional)
- Returns: Search results from multiple search engines
- Use cases: Finding current information not in knowledge base

### N8N Workflow Tools

**`create_n8n_workflow`** - Create a new n8n workflow
- Parameters: `name` (str), `nodes` (List[Dict], optional), `connections` (Dict, optional), `active` (bool, default: false), `settings` (Dict, optional)
- Returns: Created workflow details
- Use cases: Programmatically creating workflows

**`update_n8n_workflow`** - Update existing workflow
- Parameters: `workflow_id` (str), `name` (str, optional), `nodes` (List[Dict], optional), `connections` (Dict, optional), `active` (bool, optional), `settings` (Dict, optional)
- Returns: Updated workflow details
- Use cases: Modifying workflow configuration

**`delete_n8n_workflow`** - Delete workflow permanently
- Parameters: `workflow_id` (str)
- Returns: Deletion confirmation
- Use cases: Removing workflows

**`activate_n8n_workflow`** - Activate or deactivate workflow
- Parameters: `workflow_id` (str), `active` (bool)
- Returns: Activation status
- Use cases: Enabling/disabling workflows

**`list_n8n_workflows`** - List all workflows
- Parameters: `active_only` (bool, default: false)
- Returns: List of workflows with IDs, names, and status
- Use cases: Discovering available workflows

**`execute_n8n_workflow`** - Execute workflow manually
- Parameters: `workflow_id` (str), `input_data` (Dict, optional)
- Returns: Execution results
- Use cases: Triggering workflows programmatically

**`scrape_event_to_calendar`** - Scrape event from website and create calendar event
- Parameters: `url` (str), `event_name_pattern` (str, optional), `calendar_id` (str, default: "primary"), `timezone` (str, default: "America/New_York"), `location_pattern` (str, optional), `description_template` (str, optional), `workflow_name` (str, default: "Scrape Event To Calendar")
- Returns: Calendar event details
- Use cases: Automatically adding events from websites to Google Calendar

**`discover_n8n_nodes`** - Discover available n8n nodes
- Parameters: `category` (str, optional)
- Returns: List of available node types with descriptions
- Use cases: Finding available nodes for workflow creation

**`search_n8n_knowledge_base`** - Search n8n-related information
- Parameters: `query` (str), `match_count` (int, 1-50, default: 5), `search_type` ("semantic" | "text" | "hybrid", default: "hybrid")
- Returns: Formatted search results
- Use cases: Finding n8n documentation, examples, best practices

**`search_n8n_node_examples`** - Search for n8n node usage examples
- Parameters: `node_type` (str, optional), `query` (str, optional), `match_count` (int, default: 5)
- Returns: Formatted examples
- Use cases: Finding how to configure specific nodes

### Open WebUI Tools

**`export_openwebui_conversation`** - Export conversation to MongoDB RAG
- Parameters: `conversation_id` (str), `messages` (List[Dict]), `user_id` (str, optional), `title` (str, optional), `topics` (List[str], optional)
- Returns: Export results
- Use cases: Making conversations searchable

**`classify_conversation_topics`** - Classify conversation topics
- Parameters: `conversation_id` (str), `messages` (List[Dict]), `title` (str, optional), `existing_topics` (List[str], optional)
- Returns: Classified topics (3-5 topics)
- Use cases: Organizing conversations by topic

**`search_conversations`** - Search conversations in RAG system
- Parameters: `query` (str), `match_count` (int, 1-50, default: 5), `user_id` (str, optional), `conversation_id` (str, optional), `topics` (List[str], optional)
- Returns: Search results filtered to Open WebUI conversations
- Use cases: Finding past conversations by content or topic

### Calendar Tools

**`create_calendar_event`** - Create Google Calendar event
- Parameters: `user_id` (str), `persona_id` (str), `local_event_id` (str), `summary` (str), `start_time` (str, ISO 8601), `end_time` (str, ISO 8601), `description` (str, optional), `location` (str, optional), `calendar_id` (str, default: "primary")
- Returns: Created event details
- Use cases: Adding events to Google Calendar

**`update_calendar_event`** - Update existing calendar event
- Parameters: `user_id` (str), `persona_id` (str), `local_event_id` (str), `summary` (str, optional), `start_time` (str, optional), `end_time` (str, optional), `description` (str, optional), `location` (str, optional), `calendar_id` (str, default: "primary")
- Returns: Updated event details
- Use cases: Modifying calendar events

**`delete_calendar_event`** - Delete calendar event
- Parameters: `user_id` (str), `event_id` (str), `calendar_id` (str, default: "primary")
- Returns: Deletion confirmation
- Use cases: Removing calendar events

**`list_calendar_events`** - List calendar events
- Parameters: `user_id` (str), `calendar_id` (str, default: "primary"), `start_time` (str, ISO 8601, optional), `end_time` (str, ISO 8601, optional)
- Returns: List of events
- Use cases: Viewing upcoming or past events

### Knowledge Extraction Tools

**`extract_events_from_content`** - Extract events from web content
- Parameters: `content` (str), `url` (str, optional), `use_llm` (bool, default: false)
- Returns: Extracted events with dates, times, locations
- Use cases: Finding events in web pages or text

**`extract_events_from_crawled`** - Extract events from crawled pages
- Parameters: `crawled_pages` (List[Dict]), `use_llm` (bool, default: false)
- Returns: Extracted events from multiple pages
- Use cases: Batch event extraction from website crawls

### Persona Management Tools

**`record_message`** - Record message in conversation history
- Parameters: `user_id` (str), `persona_id` (str), `content` (str), `role` ("user" | "assistant", default: "user")
- Returns: Recorded message details
- Use cases: Storing conversation history

**`get_context_window`** - Get recent conversation context
- Parameters: `user_id` (str), `persona_id` (str), `limit` (int, default: 20)
- Returns: Recent messages for context
- Use cases: Retrieving conversation history for LLM context

**`store_fact`** - Store fact about user/persona
- Parameters: `user_id` (str), `persona_id` (str), `fact` (str), `tags` (List[str], optional)
- Returns: Stored fact details
- Use cases: Remembering user preferences, facts

**`search_facts`** - Search stored facts
- Parameters: `user_id` (str), `persona_id` (str), `query` (str), `limit` (int, default: 10)
- Returns: Matching facts
- Use cases: Finding relevant user information

**`store_web_content`** - Store web content for persona
- Parameters: `user_id` (str), `persona_id` (str), `content` (str), `source_url` (str), `tags` (List[str], optional)
- Returns: Stored content details
- Use cases: Saving web content for later reference

**`get_persona_voice_instructions`** - Get persona voice/personality instructions
- Parameters: `user_id` (str), `persona_id` (str)
- Returns: Voice instructions for LLM
- Use cases: Retrieving persona personality for conversations

**`record_persona_interaction`** - Record interaction with persona
- Parameters: `user_id` (str), `persona_id` (str), `user_message` (str), `bot_response` (str)
- Returns: Recorded interaction
- Use cases: Tracking persona interactions for mood/relationship updates

**`get_persona_state`** - Get persona state (mood, relationship, context)
- Parameters: `user_id` (str), `persona_id` (str)
- Returns: Persona state including mood, relationship level, context
- Use cases: Checking persona state before interactions

**`update_persona_mood`** - Update persona mood
- Parameters: `user_id` (str), `persona_id` (str), `primary_emotion` (str), `intensity` (float, 0.0-1.0)
- Returns: Updated mood state
- Use cases: Adjusting persona emotional state

**`orchestrate_conversation`** - Orchestrate multi-agent conversation
- Parameters: `user_id` (str), `persona_id` (str), `message` (str)
- Returns: Orchestrated conversation response
- Use cases: Managing complex multi-agent conversations

### Enhanced Search Tools

**`enhanced_search`** - Enhanced RAG search with decomposition and grading
- Parameters: `query` (str), `match_count` (int, default: 5), `use_decomposition` (bool, default: true), `use_grading` (bool, default: true)
- Returns: Enhanced search results
- Use cases: Advanced search with query decomposition and result grading

## MCP Integration Examples

### Open WebUI Integration

1. **Configure MCP Server in Open WebUI**:
   - Go to Settings → Connections → MCP Servers
   - Add new server: `http://lambda-server:8000/mcp`
   - Tools will be automatically available

2. **Use in Conversation**:
   ```
   User: Search the knowledge base for "authentication"
   Assistant: [Calls search_knowledge_base tool]
   ```

### Claude Desktop Integration

Add to `claude_desktop_config.json`:
```json
{
  "mcpServers": {
    "lambda-server": {
      "url": "http://localhost:8000/mcp"
    }
  }
}
```

### Programmatic Usage

```python
import requests

# List available tools
response = requests.post("http://lambda-server:8000/mcp/tools/list")
tools = response.json()

# Call a tool
response = requests.post("http://lambda-server:8000/mcp/tools/call", json={
    "tool": "search_knowledge_base",
    "arguments": {
        "query": "authentication",
        "match_count": 5,
        "search_type": "hybrid"
    }
})
result = response.json()
```

## Workflow Examples

### Document Ingestion → Search Workflow

1. **Ingest Document** (via REST API):
   ```bash
   curl -X POST http://lambda-server:8000/api/v1/rag/ingest \
     -F "files=@document.pdf"
   ```

2. **Search Knowledge Base** (via MCP):
   ```json
   {
     "tool": "search_knowledge_base",
     "arguments": {
       "query": "What is in the document?",
       "search_type": "hybrid"
     }
   }
   ```

### Web Crawl → Event Extraction → Calendar Workflow

1. **Crawl Website**:
   ```json
   {
     "tool": "crawl_deep",
     "arguments": {
       "url": "https://example.com/events",
       "max_depth": 2
     }
   }
   ```

2. **Extract Events**:
   ```json
   {
     "tool": "extract_events_from_crawled",
     "arguments": {
       "crawled_pages": [...],
       "use_llm": true
     }
   }
   ```

3. **Create Calendar Events**:
   ```json
   {
     "tool": "create_calendar_event",
     "arguments": {
       "user_id": "user123",
       "persona_id": "persona456",
       "local_event_id": "event789",
       "summary": "Event Name",
       "start_time": "2024-01-15T10:00:00Z",
       "end_time": "2024-01-15T12:00:00Z"
     }
   }
   ```

### Conversation Export → Topic Classification Workflow

1. **Export Conversation**:
   ```json
   {
     "tool": "export_openwebui_conversation",
     "arguments": {
       "conversation_id": "conv123",
       "messages": [...],
       "user_id": "user456"
     }
   }
   ```

2. **Classify Topics**:
   ```json
   {
     "tool": "classify_conversation_topics",
     "arguments": {
       "conversation_id": "conv123",
       "messages": [...]
     }
   }
   ```

3. **Search Conversations**:
   ```json
   {
     "tool": "search_conversations",
     "arguments": {
       "query": "authentication",
       "topics": ["security", "api"]
     }
   }
   ```

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
EMBEDDING_MODEL=qwen3-embedding:4b
EMBEDDING_BASE_URL=http://ollama:11434/v1
EMBEDDING_DIMENSION=2560

# Neo4j (for Graphiti and knowledge graph)
NEO4J_URI=bolt://neo4j:7687
NEO4J_USER=neo4j
NEO4J_PASSWORD=password
NEO4J_DATABASE=neo4j

# Cloudflare Access Authentication
CLOUDFLARE_AUTH_DOMAIN=https://datacrew-space.cloudflareaccess.com
CLOUDFLARE_AUD_TAG=e869f0dbb027893e1c9ded98f81e6c85420c574098c895a51f79a1e9930c948c

# Supabase (for auth and data)
SUPABASE_DB_URL=postgresql://postgres:password@supabase-db:5432/postgres
SUPABASE_SERVICE_KEY=<optional-service-role-key>

# MinIO (Supabase Storage)
MINIO_ENDPOINT=http://supabase-minio:9020
MINIO_ACCESS_KEY=${SUPABASE_MINIO_ROOT_USER}
MINIO_SECRET_KEY=${SUPABASE_MINIO_ROOT_PASSWORD}

# Feature Flags
USE_GRAPHITI=false  # Enable Graphiti knowledge graph RAG
USE_KNOWLEDGE_GRAPH=false  # Enable code structure knowledge graph
USE_CONTEXTUAL_EMBEDDINGS=false  # Enable contextual embeddings
USE_AGENTIC_RAG=false  # Enable code example extraction and search
USE_RERANKING=false  # Enable cross-encoder reranking
```

### Understanding the AUD Tag (Application Audience Tag)

The **AUD Tag** (Application Audience Tag) is a critical security component for Cloudflare Access authentication. Here's what you need to know:

#### What is the AUD Tag?

The AUD tag is a **unique identifier** for your Cloudflare Access application. It's a cryptographic hash (64-character hex string) that Cloudflare generates when you create an Access application. Think of it as a "fingerprint" that uniquely identifies your application.

**Example AUD Tag:**
```
e869f0dbb027893e1c9ded98f81e6c85420c574098c895a51f79a1e9930c948c
```

#### Why is it Important?

The AUD tag is used for **JWT token validation** to prevent token reuse attacks:

1. **Security**: When a user authenticates through Cloudflare Access, they receive a JWT token. This token contains an `aud` (audience) claim that must match your application's AUD tag.

2. **Token Validation**: The Lambda server validates incoming JWT tokens by checking:
   - Token signature (cryptographically valid)
   - Token expiration (not expired)
   - **Audience claim matches AUD tag** ← This is the critical check
   - Issuer matches your Cloudflare team domain

3. **Prevents Token Reuse**: If someone tries to use a JWT token from a different Cloudflare Access application, the audience won't match, and the token will be rejected.

#### How JWT Validation Works

```
User Request → Cloudflare Access → JWT Token Generated
                                    ↓
                              Token contains:
                              - email: user@example.com
                              - aud: e869f0dbb027893e1c9ded98f81e6c85420c574098c895a51f79a1e9930c948c
                              - iss: https://datacrew-space.cloudflareaccess.com
                                    ↓
                              Lambda Server validates:
                              1. Signature valid? ✓
                              2. Not expired? ✓
                              3. aud matches CLOUDFLARE_AUD_TAG? ✓ ← Critical check
                              4. iss matches CLOUDFLARE_AUTH_DOMAIN? ✓
                                    ↓
                              User authenticated → Access granted
```

#### Getting Your AUD Tag

**Method 1: Using the Script (Recommended)**
```bash
cd /home/jaewilson07/GitHub/local-ai-packaged
python3 00-infrastructure/scripts/get-lambda-api-aud-tag.py
```

This script automatically retrieves the AUD tag from your Cloudflare Access application.

**Method 2: From Cloudflare Dashboard**
1. Go to [Cloudflare One Dashboard](https://one.dash.cloudflare.com/)
2. Navigate to **Access controls** > **Applications**
3. Select your application (e.g., "Lambda API" for `api.datacrew.space`)
4. In the **Basic information** tab, copy the **Application Audience (AUD) Tag**

**Method 3: From Cloudflare API**
```bash
curl -X GET "https://api.cloudflare.com/client/v4/accounts/{account_id}/access/apps" \
  -H "Authorization: Bearer YOUR_API_TOKEN" \
  | jq '.result[] | select(.domain=="api.datacrew.space") | .aud'
```

#### Setting the AUD Tag

Once you have the AUD tag, set it in your environment:

**Option 1: Docker Compose (Recommended for Development)**
```yaml
# In 04-lambda/docker-compose.yml
environment:
  CLOUDFLARE_AUD_TAG: ${CLOUDFLARE_AUD_TAG:-e869f0dbb027893e1c9ded98f81e6c85420c574098c895a51f79a1e9930c948c}
```

**Option 2: Environment Variable**
```bash
export CLOUDFLARE_AUD_TAG=e869f0dbb027893e1c9ded98f81e6c85420c574098c895a51f79a1e9930c948c
```

**Option 3: Infisical (Recommended for Production)**
```bash
infisical secrets set CLOUDFLARE_AUD_TAG=e869f0dbb027893e1c9ded98f81e6c85420c574098c895a51f79a1e9930c948c
```

#### Common Issues

**Error: "Missing required audience (CLOUDFLARE_AUD_TAG)"**
- **Cause**: The `CLOUDFLARE_AUD_TAG` environment variable is not set or is empty
- **Solution**: Set the AUD tag using one of the methods above

**Error: "Token audience does not match expected"**
- **Cause**: The JWT token's `aud` claim doesn't match your `CLOUDFLARE_AUD_TAG`
- **Solution**:
  1. Verify you're using the correct AUD tag for your application
  2. Make sure the token is from the correct Cloudflare Access application
  3. Check that the application is linked to the correct tunnel route

**Error: "Token issuer does not match expected"**
- **Cause**: The JWT token's `iss` claim doesn't match your `CLOUDFLARE_AUTH_DOMAIN`
- **Solution**: Set `CLOUDFLARE_AUTH_DOMAIN` to your Cloudflare team domain (e.g., `https://datacrew-space.cloudflareaccess.com`)

#### Security Best Practices

1. **Never share your AUD tag publicly** - It's unique to your application
2. **Use different AUD tags for different environments** - Dev, staging, and production should have separate Access applications
3. **Rotate if compromised** - If you suspect your AUD tag is compromised, create a new Access application
4. **Store securely** - Use Infisical or secure environment variable management for production

#### Related Documentation

- [Auth Project README](src/services/auth/README.md) - Complete authentication system documentation
- [Security Considerations](src/services/auth/SECURITY.md) - Security best practices
- [Cloudflare Access Setup](00-infrastructure/scripts/setup-lambda-api-access.py) - Script to create Access application

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

# Setup Crawl4AI (installs Playwright browsers)
# This is automatically done in Docker, but required for local development
crawl4ai-setup

# Optional: Verify Crawl4AI installation
crawl4ai-doctor

# Run locally (requires MongoDB and Ollama running)
uvicorn server.main:app --reload --host 0.0.0.0 --port 8000
```

**Note**: Crawl4AI setup (`crawl4ai-setup`) is automatically run in Docker via `docker-entrypoint.sh`. For local development, you must run it manually after installing dependencies.

### Adding New Projects

1. Create project folder: `src/capabilities/your_capability/`
2. Implement project logic (config, dependencies, tools)
3. Create API router: `server/api/your_project.py`
4. Register router in `server/main.py`
5. Add MCP tools in `src/mcp_server/server.py`

## Projects

### MongoDB RAG (Retrieval Augmented Generation)
- **Location**: `src/capabilities/retrieval/mongo_rag/`
- **Inspiration**: Based on [MongoDB-RAG-Agent](https://github.com/coleam00/MongoDB-RAG-Agent)
- **Features**:
  - **Docling Integration**: Production-grade document processing with DocumentConverter and HybridChunker for intelligent document conversion and chunking
  - **Multi-Format Support**: PDF, Word, PowerPoint, Excel, HTML, Markdown, Audio (transcribed with Whisper ASR via Docling)
  - Hybrid search (semantic + text using Reciprocal Rank Fusion)
  - Document ingestion with intelligent chunking (token-aware, structure-preserving)
  - Conversational agent with automatic search
  - Code example extraction and search (Agentic RAG)
  - Contextual embeddings (optional)
  - Cross-encoder reranking (optional)
- **Database**: MongoDB Atlas Local (vector + full-text search)
- **LLM**: Ollama (llama3.2)
- **Embeddings**: Ollama (qwen3-embedding:4b)
- **Document Processing**: Docling 2.14+ (DocumentConverter, HybridChunker, ASR pipeline)

### Crawl4AI RAG (Web Crawling & Ingestion)
- **Location**: `src/workflows/ingestion/crawl4ai_rag/`
- **Features**:
  - Single page and deep recursive web crawling
  - Automatic ingestion into MongoDB RAG
  - Domain and subdomain filtering
  - Concurrent crawling (up to 10 pages simultaneously)
  - Metadata extraction (title, description, images, links)
  - Graphiti integration (enabled by default) for entity extraction
- **Dependencies**: Crawl4AI 0.6.2+, Playwright 1.40+ (browsers installed via `crawl4ai-setup`)
- **Database**: MongoDB (01-data stack) for storage, Neo4j (01-data stack) for Graphiti
- **Setup**: Playwright browsers are automatically installed via `docker-entrypoint.sh` using `crawl4ai-setup`
- **Documentation**: [Crawl4AI Installation](https://docs.crawl4ai.com/basic/installation/)

### Graphiti RAG (Knowledge Graph RAG)
- **Location**: `src/capabilities/retrieval/graphiti_rag/`
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
- Crawl4AI 0.6.2+ - Web crawling and scraping (requires Playwright browsers)
- Playwright 1.40+ - Browser automation for Crawl4AI
- Graphiti Core 1.0+ (with Neo4j extras) - Knowledge graph RAG
- Neo4j Python Driver 5.0+ - Neo4j connectivity
- Sentence Transformers 4.1+ - Reranking support

### Crawl4AI Setup

Crawl4AI requires Playwright browsers to be installed. The setup process follows the [official Crawl4AI documentation](https://docs.crawl4ai.com/basic/installation/):

1. **Install**: `pip install crawl4ai` (already in `pyproject.toml`)
2. **Setup**: `crawl4ai-setup` (installs Playwright browsers)
3. **Verify** (optional): `crawl4ai-doctor`

In Docker, this is handled automatically by `docker-entrypoint.sh`. If `crawl4ai-setup` fails, it falls back to `python -m playwright install --with-deps chromium`.

## Troubleshooting

### Authentication Issues

**Error: "Missing required audience (CLOUDFLARE_AUD_TAG)"**
```bash
# Check if AUD tag is set
docker exec lambda-server env | grep CLOUDFLARE_AUD_TAG

# If empty, get the AUD tag
python3 00-infrastructure/scripts/get-lambda-api-aud-tag.py

# Restart container to apply changes
docker compose -p localai-lambda restart lambda-server
```

**Error: "Invalid token: Token audience does not match expected"**
- The JWT token's audience doesn't match your configured AUD tag
- Verify the Access application is correctly linked to the tunnel route
- Check that you're using the correct AUD tag for the application

**Error: "Token issuer does not match expected"**
- The JWT token's issuer doesn't match your `CLOUDFLARE_AUTH_DOMAIN`
- Set `CLOUDFLARE_AUTH_DOMAIN` to your Cloudflare team domain (e.g., `https://datacrew-space.cloudflareaccess.com`)

**401 Unauthorized on all endpoints**
- Verify Cloudflare Access application exists and is linked to tunnel route
- Check that the user is authenticated through Cloudflare Access
- Verify JWT token is present in `Cf-Access-Jwt-Assertion` header

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
docker exec ollama ollama pull qwen3-embedding:4b
```

### Build Issues
```bash
# Rebuild Lambda container
cd 04-lambda
docker compose build --no-cache

# Check build logs
docker compose logs lambda-server
```

### Crawl4AI / Playwright Issues
```bash
# Check if Playwright browsers are installed
docker exec lambda-server ls -la /root/.cache/ms-playwright/

# Manually install Playwright browsers if needed
docker exec lambda-server python -m playwright install --with-deps chromium

# Verify Crawl4AI installation
docker exec lambda-server crawl4ai-doctor

# Check Crawl4AI setup logs
docker logs lambda-server | grep -i "crawl4ai\|playwright"
```

## Authentication & Security

The Lambda server uses **Cloudflare Access** for authentication. All API endpoints (except `/health` and `/docs`) require a valid Cloudflare Access JWT token.

### How Authentication Works

1. **User accesses** `https://api.datacrew.space/api/me`
2. **Cloudflare Access** intercepts the request and checks if user is authenticated
3. If not authenticated, user is redirected to Cloudflare Access login (Google OAuth)
4. After authentication, Cloudflare injects a JWT token in the `Cf-Access-Jwt-Assertion` header
5. **Lambda server** validates the JWT token:
   - Checks cryptographic signature
   - Verifies expiration
   - **Validates audience (AUD tag)** - ensures token is for this application
   - Verifies issuer matches your Cloudflare team domain
6. If valid, user is automatically provisioned (JIT) in Supabase, Neo4j, and MinIO
7. Request proceeds with user context

### Testing Authentication

**From Browser:**
- Simply visit `https://api.datacrew.space/api/me` - Cloudflare Access will handle authentication automatically

**From Command Line (with valid JWT):**
```bash
# Get JWT token from browser DevTools → Network → Request Headers → Cf-Access-Jwt-Assertion
curl -H "Cf-Access-Jwt-Assertion: YOUR_JWT_TOKEN" \
     https://api.datacrew.space/api/me
```

**Note**: JWT tokens expire after the session duration (default: 24 hours). You'll need to get a fresh token from the browser after expiration.

## Stack Integration

Lambda stack depends on:
- **00-infrastructure**: Network (`ai-network`), Cloudflare Tunnel, Caddy
- **01-data**: MongoDB, Neo4j (optional, for Graphiti), Supabase, MinIO
- **02-compute**: Ollama (LLM + embeddings)

Start order: infrastructure → data → compute → lambda

**Note**: Neo4j is optional and only required if `USE_GRAPHITI=true` or `USE_KNOWLEDGE_GRAPH=true`.

## Documentation

- [API Strategy Documentation](docs/API_STRATEGY.md) - Route naming conventions, error handling, capability/workflow API links
- [RAG MCP Architecture Decision](docs/RAG_MCP_ARCHITECTURE_DECISION.md) - Architecture decision for RAG tools design
- [RAG Functionality Documentation](docs/RAG_FUNCTIONALITY.md) - Complete RAG systems overview
- [MCP Troubleshooting Skill](../../.cursor/skills/mcp-troubleshooting/SKILL.md) - MCP connection and usage guide
- [Lambda AGENTS.md](AGENTS.md) - MCP tool design guidelines and Lambda patterns
