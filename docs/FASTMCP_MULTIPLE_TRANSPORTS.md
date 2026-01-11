# FastMCP Multiple Transport Support

## Problem

Open WebUI doesn't fully support FastMCP's Streamable HTTP transport, but we want to:
1. Keep FastMCP (it's great!)
2. Use internal network (for security)
3. Support Open WebUI's MCP client

## Solution: Add REST API Endpoints

FastMCP's `http_app()` creates a Streamable HTTP endpoint, but we can also expose the same tools via REST API endpoints that Open WebUI can use.

### Current Setup

Currently, Lambda server exposes MCP via:
- **Streamable HTTP**: `/mcp/` (FastMCP's native transport)
- **Info endpoint**: `/mcp-info` (for debugging)

### Adding REST API Endpoints

We can add REST API endpoints that wrap MCP tools, making them accessible via standard HTTP POST requests that Open WebUI can use.

## Implementation Options

### Option 1: Add REST API Wrapper Endpoints ✅ Recommended

Create REST API endpoints that wrap MCP tools:

```python
# In 04-lambda/server/api/mcp_rest.py
from fastapi import APIRouter, HTTPException
from server.mcp.fastmcp_server import mcp
from typing import Dict, Any

router = APIRouter()

@router.post("/api/v1/mcp/tools/list")
async def list_tools():
    """List all available MCP tools."""
    try:
        # Get tools from FastMCP
        tools = []
        if hasattr(mcp, '_tool_manager'):
            tool_manager = mcp._tool_manager
            if hasattr(tool_manager, '_tools') and tool_manager._tools:
                for tool_name, tool in tool_manager._tools.items():
                    tools.append({
                        "name": tool_name,
                        "description": tool.description if hasattr(tool, 'description') else "",
                        "inputSchema": tool.inputSchema if hasattr(tool, 'inputSchema') else {}
                    })
        return {"tools": tools}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/api/v1/mcp/tools/call")
async def call_tool(request: Dict[str, Any]):
    """Call an MCP tool via REST API."""
    tool_name = request.get("name")
    arguments = request.get("arguments", {})
    
    if not tool_name:
        raise HTTPException(status_code=400, detail="Tool name is required")
    
    try:
        # Call the tool via FastMCP
        result = await mcp.call_tool(tool_name, arguments)
        return {"result": result}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
```

Then mount this router in `main.py`:

```python
from server.api import mcp_rest
app.include_router(mcp_rest.router)
```

**Pros**:
- ✅ Works with Open WebUI (standard REST API)
- ✅ Keeps FastMCP for other clients
- ✅ Internal network (secure)
- ✅ Simple to implement

**Cons**:
- ⚠️ Not native MCP protocol (but works!)

### Option 2: Use Open WebUI's OpenAPI Support

If Open WebUI supports OpenAPI, we can generate an OpenAPI spec from FastMCP tools and expose it:

```python
# Generate OpenAPI spec from MCP tools
@app.get("/api/v1/mcp/openapi.json")
async def mcp_openapi():
    """Generate OpenAPI spec from MCP tools."""
    # Convert MCP tools to OpenAPI format
    # Return OpenAPI JSON
```

Then configure Open WebUI to use:
- **Type**: `OpenAPI`
- **Server URL**: `http://lambda-server:8000/api/v1/mcp/openapi.json`

### Option 3: Add SSE Endpoint (If Open WebUI Supports It)

FastMCP also supports SSE (Server-Sent Events), though it's deprecated. We could add it as an alternative:

```python
# In main.py, add SSE endpoint
@app.get("/mcp/sse")
async def mcp_sse():
    """SSE endpoint for MCP (deprecated but may work with Open WebUI)."""
    # Implement SSE transport
    # This would require additional FastMCP configuration
```

**Note**: SSE is deprecated in FastMCP, so this may not be the best option.

## Recommended Approach

**Use Option 1 (REST API Wrapper)** because:
1. ✅ Open WebUI can use standard REST APIs
2. ✅ Keeps FastMCP for other clients (Cursor, Claude, etc.)
3. ✅ Internal network (secure)
4. ✅ Simple to implement and maintain

## Implementation Steps

1. **Create REST API wrapper** (`04-lambda/server/api/mcp_rest.py`)
2. **Mount router** in `main.py`
3. **Configure Open WebUI** to use REST API endpoints
4. **Test** with Open WebUI

## Open WebUI Configuration

After implementing REST API endpoints, configure Open WebUI:

1. **Option A: Use OpenAPI** (if supported):
   - Type: `OpenAPI`
   - Server URL: `http://lambda-server:8000/api/v1/mcp/openapi.json`

2. **Option B: Use Custom Functions**:
   - Configure Open WebUI to call REST endpoints directly
   - Use custom function definitions

3. **Option C: Use MCP Bridge**:
   - Create a lightweight MCP-to-REST bridge service
   - Runs alongside Lambda server
   - Translates MCP protocol to REST API

## Testing

After implementation, test:

```bash
# List tools
curl -X POST http://lambda-server:8000/api/v1/mcp/tools/list

# Call a tool
curl -X POST http://lambda-server:8000/api/v1/mcp/tools/call \
  -H "Content-Type: application/json" \
  -d '{
    "name": "search_knowledge_base",
    "arguments": {
      "query": "test",
      "match_count": 5
    }
  }'
```

## References

- [FastMCP Documentation](https://github.com/jlowin/fastmcp)
- [Open WebUI MCP Integration](./MCP_INTEGRATION.md)
- [MCP Protocol Specification](https://modelcontextprotocol.io)
