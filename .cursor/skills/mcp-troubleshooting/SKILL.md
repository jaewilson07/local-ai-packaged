---
name: mcp-troubleshooting
description: Troubleshoot MCP (Model Context Protocol) connection issues, configure MCP servers for Open WebUI, and diagnose Lambda server MCP problems. Use when MCP connections fail, Open WebUI can't connect to Lambda MCP, or when setting up MCP integrations.
---

# MCP Troubleshooting

Guide for diagnosing and fixing MCP (Model Context Protocol) connection issues between clients (Open WebUI, Cursor, Claude Desktop) and the Lambda MCP server.

## Common Issue: "Unable to connect" from Open WebUI

### Problem

When trying to connect to `http://lambda-server:8000/mcp` from Open WebUI's External Tools, you get an "Unable to connect" error.

### Root Cause

Open WebUI's MCP integration has known compatibility issues with Streamable HTTP transport (see [GitHub Issue #14762](https://github.com/open-webui/open-webui/issues/14762)). The Lambda server uses FastMCP with Streamable HTTP transport.

### Solutions

#### Solution 1: Use External URL (via Cloudflare Tunnel) - Recommended

Instead of using the internal Docker network URL, use the external URL through the Cloudflare Tunnel:

1. **In Open WebUI External Tools**:
   - **Type**: `MCP (Streamable HTTP)`
   - **Server URL**: `https://api.datacrew.space/mcp`
   - **Authentication**:
     - If Cloudflare Access is configured: Leave empty (authentication handled at edge)
     - If not configured: See cloudflare-access-setup skill

2. **Why this works**: The Cloudflare Tunnel routes through Caddy to the Lambda server. External URLs sometimes work better with Open WebUI's MCP client.

#### Solution 2: Try with Trailing Slash

Some MCP clients require a trailing slash:

- **Server URL**: `http://lambda-server:8000/mcp/` (note the trailing slash)
- Or: `https://api.datacrew.space/mcp/`

#### Solution 3: Use REST API Endpoints Directly (Workaround)

Instead of using MCP, you can configure Open WebUI to use the REST API endpoints directly:

1. **In Open WebUI External Tools**:
   - **Type**: `OpenAPI`
   - **Server URL**: `http://lambda-server:8000/docs/openapi.json`
   - Or: `https://api.datacrew.space/docs/openapi.json`

2. **Note**: This requires OpenAPI spec generation. Check if available:
   ```bash
   curl http://lambda-server:8000/docs/openapi.json
   ```

#### Solution 4: Verify Network Connectivity

Ensure Open WebUI can reach the Lambda server:

```bash
# From Open WebUI container
docker exec open-webui curl -v http://lambda-server:8000/health

# Check if MCP endpoint is accessible
docker exec open-webui curl -v http://lambda-server:8000/mcp-info
```

#### Solution 5: Check Lambda Server Logs

Monitor Lambda server logs for connection attempts:

```bash
docker logs lambda-server --tail 50 -f
```

Look for:
- Connection attempts from Open WebUI
- Error messages about missing headers
- SSE (Server-Sent Events) connection issues

## Testing MCP Connections

### Test 1: Basic Connectivity

```bash
docker exec open-webui curl -s http://lambda-server:8000/health
# Expected: {"status":"healthy","service":"lambda-server"}
```

### Test 2: MCP Info Endpoint

```bash
docker exec open-webui curl -s http://lambda-server:8000/mcp-info | python3 -m json.tool
# Expected: JSON with server info and tool list
```

### Test 3: MCP Endpoint (SSE)

```bash
docker exec open-webui curl -H "Accept: text/event-stream" http://lambda-server:8000/mcp/
# Expected: SSE connection (may show session error, which is normal for direct curl)
```

### Test 4: List MCP Tools

```bash
curl -X POST http://lambda-server:8000/mcp/tools/list
# Expected: JSON array of available tools
```

### Test 5: Call MCP Tool

```bash
curl -X POST http://lambda-server:8000/mcp/tools/call \
  -H "Content-Type: application/json" \
  -d '{
    "tool": "search_knowledge_base",
    "arguments": {
      "query": "test",
      "search_type": "hybrid",
      "match_count": 5
    }
  }'
```

## Client-Specific Configuration

### Open WebUI

1. Go to Settings → Connections → MCP Servers
2. Add new server: `http://lambda-server:8000/mcp` or `https://api.datacrew.space/mcp`
3. Tools will be automatically available in conversations

### Cursor IDE

Edit `~/.cursor/mcp.json`:

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

### Claude Desktop

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

### Programmatic Usage (Python)

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

### n8n Integration

**HTTP Request Node Configuration**:
- **URL**: `http://lambda-server:8000/mcp/tools/call`
- **Method**: POST
- **Body** (JSON):
  ```json
  {
    "tool": "search_knowledge_base",
    "arguments": {
      "query": "{{ $json.question }}",
      "search_type": "hybrid"
    }
  }
  ```

## MCP Server Endpoints

### Base URLs

- **Internal (Docker network)**: `http://lambda-server:8000/mcp`
- **External (via Cloudflare)**: `https://api.datacrew.space/mcp`

### Available Endpoints

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/mcp/tools/list` | POST | List all available MCP tools |
| `/mcp/tools/call` | POST | Execute an MCP tool |
| `/mcp-info` | GET | Get MCP server information |
| `/health` | GET | Health check |

## Feature Flags

Some MCP tools require feature flags to be enabled in Lambda server:

| Flag | Tools Enabled |
|------|---------------|
| `USE_GRAPHITI=true` | Graphiti RAG tools |
| `USE_KNOWLEDGE_GRAPH=true` | Knowledge graph tools |
| `USE_AGENTIC_RAG=true` | Code example search |

Check feature flags:

```bash
docker exec lambda-server env | grep USE_
```

## Error Handling

MCP tools return structured errors:

```json
{
  "error": {
    "code": "ERROR_CODE",
    "message": "Error message",
    "details": "Additional details"
  }
}
```

Common error codes:
- `VALIDATION_ERROR` - Invalid parameters
- `DATABASE_ERROR` - Database operation failed
- `NOT_FOUND` - Resource not found
- `NOT_IMPLEMENTED` - Feature not available
- `FEATURE_DISABLED` - Feature flag not enabled

## Current Status Checklist

When troubleshooting, verify these items:

- [ ] Lambda server is running: `docker ps | grep lambda-server`
- [ ] Lambda server is healthy: `curl http://lambda-server:8000/health`
- [ ] MCP endpoint is accessible: `curl http://lambda-server:8000/mcp-info`
- [ ] Tools are registered: Check tool count in `/mcp-info` response
- [ ] Network connectivity: Can client reach Lambda server?
- [ ] Cloudflare Access (if external): Is JWT required?

## References

- [Lambda AGENTS.md](04-lambda/AGENTS.md) - MCP server implementation details
- [MCP Protocol Specification](https://modelcontextprotocol.io)
- [Open WebUI GitHub Issue #14762](https://github.com/open-webui/open-webui/issues/14762) - Known MCP compatibility issues
