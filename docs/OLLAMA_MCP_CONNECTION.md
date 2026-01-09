# Connecting to Lambda MCP Server from Ollama

## Understanding the Architecture

**Important**: Ollama itself doesn't connect to MCP servers. Instead:
- **Ollama** = LLM inference server (provides models like llama3.2, mistral, etc.)
- **Lambda Server** = MCP server (provides tools like search, crawl, etc.)
- **Client** (Open WebUI, Cursor, etc.) = Connects to both Ollama and MCP servers

When you use Ollama models in a client, that client can also connect to MCP servers to give the model access to tools.

## Connection Methods

### Method 1: Via Open WebUI (Recommended)

Open WebUI can use Ollama models AND connect to the Lambda MCP server simultaneously.

#### Step 1: Configure Ollama in Open WebUI

1. **Add Ollama as a Model Provider**
   - Go to **Settings** → **Models**
   - Add Ollama:
     - **Base URL**: `http://ollama:11434` (internal Docker network)
     - Or: `http://localhost:11434` (if accessing from host)
   - Pull models: `llama3.2`, `mistral`, etc.

#### Step 2: Configure Lambda MCP Server

1. **Access Admin Panel**
   - Log in to Open WebUI as administrator
   - Navigate to **Settings** → **External Tools**

2. **Add MCP Server**
   - Click **"+" (Add Server)**
   - Configure:
     - **Type**: `MCP (Streamable HTTP)`
     - **Server URL**: 
       - Internal (Docker): `http://lambda-server:8000/mcp` (recommended for internal use)
       - External (via Cloudflare Tunnel): `https://api.datacrew.space/mcp` (requires Cloudflare Access setup)
     - **Authentication**: 
       - Internal URL: Leave empty (network isolation provides security)
       - External URL: Leave empty if Cloudflare Access is configured, otherwise see [MCP Security Setup](./MCP_SECURITY_SETUP.md)

   **Note**: The Cloudflare Tunnel for `api.datacrew.space` is already configured. If using the external URL, you should set up Cloudflare Access authentication for security (see [MCP Security Setup](./MCP_SECURITY_SETUP.md)).

3. **Enable Tools**
   - Enable the tools you want available:
     - `search_knowledge_base` - Search RAG system
     - `web_search` - Search the web
     - `crawl_single_page` - Crawl websites
     - `agent_query` - Conversational RAG agent
     - And 20+ more tools

#### Step 3: Use Ollama Models with MCP Tools

When you chat with an Ollama model in Open WebUI:
- The model can automatically call MCP tools when needed
- Tools appear as function calls the model can invoke
- Results are returned to the model for context

**Example Conversation:**
```
You: "Search the knowledge base for information about Python async programming"

[Model calls search_knowledge_base tool]
[Tool returns results]
[Model synthesizes response with tool results]
```

### Method 2: Via Cursor IDE

Cursor IDE can connect to MCP servers and use Ollama models.

#### Configuration

1. **Add Ollama to Cursor**
   - Cursor → Settings → Models
   - Add Ollama endpoint: `http://localhost:11434` or `http://ollama:11434`

2. **Configure MCP Server in Cursor**
   - Edit Cursor's MCP configuration file (usually `~/.cursor/mcp.json` or similar)
   - Add:
   ```json
   {
     "mcpServers": {
       "lambda-server": {
         "command": "npx",
         "args": [
           "-y",
           "@modelcontextprotocol/server-fetch",
           "http://lambda-server:8000/mcp"
         ]
       }
     }
   }
   ```

### Method 3: Direct API Access

You can also call MCP tools programmatically:

```python
import httpx

# MCP endpoint (SSE protocol)
async with httpx.AsyncClient() as client:
    async with client.stream(
        "POST",
        "http://lambda-server:8000/mcp",
        json={
            "method": "tools/call",
            "params": {
                "name": "search_knowledge_base",
                "arguments": {
                    "query": "Python async programming",
                    "match_count": 5
                }
            }
        }
    ) as response:
        async for line in response.aiter_lines():
            print(line)
```

## Available MCP Tools

The Lambda MCP server provides 25+ tools:

### RAG & Knowledge Base
- `search_knowledge_base` - Search MongoDB RAG system
- `ingest_documents` - Add documents to knowledge base
- `agent_query` - Conversational RAG agent
- `search_code_examples` - Find code examples

### Web & Crawling
- `web_search` - Search web via SearXNG
- `crawl_single_page` - Crawl single page
- `crawl_deep` - Deep crawl websites

### Knowledge Graph
- `search_graphiti` - Search Graphiti knowledge graph
- `parse_github_repository` - Parse GitHub repos
- `query_knowledge_graph` - Query Neo4j knowledge graph

### N8N Workflows
- `create_n8n_workflow` - Create workflows
- `execute_n8n_workflow` - Execute workflows
- `list_n8n_workflows` - List workflows

### Open WebUI
- `export_openwebui_conversation` - Export conversations
- `search_conversations` - Search conversations

And more! See full list: `http://lambda-server:8000/mcp-info`

## Testing the Connection

### Test MCP Server

```bash
# Check if MCP server is running
docker exec lambda-server curl -s http://localhost:8000/mcp-info | python3 -m json.tool

# Test from another container
docker exec open-webui curl -s http://lambda-server:8000/mcp-info
```

### Test from Open WebUI

1. Start a chat with an Ollama model
2. Ask: "What tools are available?"
3. The model should list available MCP tools
4. Try: "Search the knowledge base for [your query]"

## Troubleshooting

### MCP Tools Not Appearing

1. **Check Open WebUI Configuration**
   - Verify MCP server is added in Settings → External Tools
   - Ensure tools are enabled (toggle on)

2. **Check Network Connectivity**
   ```bash
   # From Open WebUI container
   docker exec open-webui curl -s http://lambda-server:8000/health
   ```

3. **Check Lambda Server Logs**
   ```bash
   docker logs lambda-server --tail 50
   ```

### Tools Not Working

1. **Verify Dependencies**
   - MongoDB running: `docker ps | grep mongodb`
   - Ollama running: `docker ps | grep ollama`
   - Neo4j running (for Graphiti tools): `docker ps | grep neo4j`

2. **Check Tool Parameters**
   - Each tool has specific parameters
   - Check tool descriptions in `/mcp-info` endpoint

## Architecture Diagram

```
┌─────────────┐
│   Ollama    │ ← Provides LLM models (llama3.2, mistral, etc.)
│  (Port 11434)│
└──────┬──────┘
       │
       │ Uses models
       │
┌──────▼──────────────────┐
│   Open WebUI / Cursor   │ ← Client that uses Ollama models
│                         │   AND connects to MCP servers
└──────┬──────────────────┘
       │
       │ Calls MCP tools
       │
┌──────▼──────────────┐
│  Lambda MCP Server │ ← Provides tools (search, crawl, etc.)
│  (Port 8000/mcp)   │
└─────────────────────┘
       │
       │ Uses
       │
┌──────▼──────┐  ┌─────────┐  ┌──────┐
│  MongoDB    │  │  Neo4j   │  │SearXNG│
│  (RAG)      │  │(Graphiti) │  │(Search)│
└─────────────┘  └─────────┘  └──────┘
```

## Quick Start

1. **Start Services**
   ```bash
   python start_services.py --stack compute  # Start Ollama
   python start_services.py --stack lambda    # Start Lambda MCP server
   ```

2. **Configure Open WebUI**
   - Add Ollama: Settings → Models → Add `http://ollama:11434`
   - Add MCP: Settings → External Tools → Add `http://lambda-server:8000/mcp`

3. **Start Chatting**
   - Select an Ollama model
   - Ask questions that require tools
   - Model will automatically use MCP tools when needed

## References

- [Open WebUI MCP Integration Guide](../03-apps/open-webui/docs/MCP_INTEGRATION.md)
- [Lambda MCP Server Documentation](../04-lambda/server/mcp/AGENTS.md)
- [MCP Protocol Specification](https://modelcontextprotocol.io)

