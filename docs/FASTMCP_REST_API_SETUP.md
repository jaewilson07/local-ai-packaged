# FastMCP REST API Setup Guide

## Overview

This guide explains how to use the REST API wrapper for FastMCP tools, allowing clients like Open WebUI that don't fully support FastMCP's Streamable HTTP transport to still access MCP tools.

## Architecture

The Lambda server now supports **multiple transport methods** simultaneously:

1. **Streamable HTTP** (FastMCP native): `/mcp/`
   - For clients that support FastMCP (Cursor, Claude Desktop, etc.)

2. **REST API** (Wrapper): `/api/v1/mcp/tools/call`
   - For clients that need standard REST APIs (Open WebUI, etc.)

Both use the same FastMCP tools under the hood!

## Endpoints

### List Tools
```http
GET /api/v1/mcp/tools/list
```

**Response**:
```json
{
  "tools": [
    {
      "name": "search_knowledge_base",
      "description": "Search the MongoDB RAG knowledge base...",
      "inputSchema": {...}
    },
    ...
  ],
  "count": 25
}
```

### Call Tool
```http
POST /api/v1/mcp/tools/call
Content-Type: application/json

{
  "name": "search_knowledge_base",
  "arguments": {
    "query": "Python async programming",
    "match_count": 5,
    "search_type": "hybrid"
  }
}
```

**Response**:
```json
{
  "success": true,
  "result": {
    "query": "Python async programming",
    "results": [...],
    "count": 5
  }
}
```

### Get MCP Info
```http
GET /api/v1/mcp/info
```

**Response**:
```json
{
  "server": "Lambda Server",
  "transports": {
    "streamable_http": "/mcp/",
    "rest_api": "/api/v1/mcp/tools/call"
  },
  "available_tools_count": 25,
  "tools": [...]
}
```

## Open WebUI Configuration

### Option 1: Use Custom Functions (Recommended)

Since Open WebUI doesn't fully support MCP Streamable HTTP, you can configure it to use the REST API endpoints directly via custom functions:

1. **In Open WebUI**:
   - Go to **Settings** → **Functions**
   - Add a new function for each tool you want to use
   - Configure:
     - **Name**: `search_knowledge_base`
     - **URL**: `http://lambda-server:8000/api/v1/mcp/tools/call`
     - **Method**: `POST`
     - **Headers**: `Content-Type: application/json`
     - **Body Template**:
       ```json
       {
         "name": "search_knowledge_base",
         "arguments": {
           "query": "{{query}}",
           "match_count": {{match_count|default(5)}},
           "search_type": "{{search_type|default('hybrid')}}"
         }
       }
       ```

2. **Repeat for each tool** you want to expose

### Option 2: Use OpenAPI (If Supported)

If Open WebUI supports OpenAPI, you can:

1. **Generate OpenAPI spec** from the REST endpoints
2. **Configure Open WebUI**:
   - Type: `OpenAPI`
   - Server URL: `http://lambda-server:8000/docs/openapi.json`

### Option 3: Wait for Open WebUI MCP Support

Open WebUI is working on better MCP support. Once they fix the Streamable HTTP compatibility, you can switch to:
- Type: `MCP (Streamable HTTP)`
- Server URL: `http://lambda-server:8000/mcp`

## Testing

### Test REST API Endpoints

```bash
# List tools
curl -X GET http://lambda-server:8000/api/v1/mcp/tools/list | python3 -m json.tool

# Call a tool
curl -X POST http://lambda-server:8000/api/v1/mcp/tools/call \
  -H "Content-Type: application/json" \
  -d '{
    "name": "search_knowledge_base",
    "arguments": {
      "query": "test",
      "match_count": 5
    }
  }' | python3 -m json.tool

# Get MCP info
curl -X GET http://lambda-server:8000/api/v1/mcp/info | python3 -m json.tool
```

### Test from Open WebUI Container

```bash
# Test connectivity
docker exec open-webui curl -s http://lambda-server:8000/api/v1/mcp/tools/list | python3 -m json.tool

# Test tool call
docker exec open-webui curl -X POST http://lambda-server:8000/api/v1/mcp/tools/call \
  -H "Content-Type: application/json" \
  -d '{"name": "search_knowledge_base", "arguments": {"query": "test"}}'
```

## Benefits

✅ **Keep FastMCP**: Continue using FastMCP for other clients  
✅ **Internal Network**: Use `http://lambda-server:8000` (secure, fast)  
✅ **Open WebUI Compatible**: REST API works with Open WebUI  
✅ **Same Tools**: Both transports use the same FastMCP tools  
✅ **No Code Duplication**: Tools defined once in FastMCP  

## Current Status

- ✅ FastMCP Streamable HTTP: `/mcp/` (for Cursor, Claude, etc.)
- ✅ REST API Wrapper: `/api/v1/mcp/tools/call` (for Open WebUI)
- ✅ Both use internal network: `http://lambda-server:8000`
- ✅ Same tools available via both transports

## References

- [FastMCP Multiple Transports](./FASTMCP_MULTIPLE_TRANSPORTS.md)
- [Open WebUI MCP Integration](../03-apps/open-webui/docs/MCP_INTEGRATION.md)
- [MCP Connection Troubleshooting](./MCP_CONNECTION_TROUBLESHOOTING.md)

