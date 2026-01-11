# MCP Connection Troubleshooting Guide

## Issue: "Unable to connect" to Lambda MCP Server from Open WebUI

### Problem

When trying to connect to `http://lambda-server:8000/mcp` from Open WebUI's External Tools, you get an "Unable to connect" error.

### Root Cause

Open WebUI's MCP integration has known compatibility issues with Streamable HTTP transport (see [GitHub Issue #14762](https://github.com/open-webui/open-webui/issues/14762)). The Lambda server uses FastMCP with Streamable HTTP transport, which may not be fully supported by Open WebUI's MCP client.

### Solutions

#### Solution 1: Use External URL (via Cloudflare Tunnel) ✅ Recommended

Instead of using the internal Docker network URL, use the external URL through the Cloudflare Tunnel:

1. **In Open WebUI External Tools**:
   - **Type**: `MCP (Streamable HTTP)`
   - **Server URL**: `https://api.datacrew.space/mcp`
   - **Authentication**:
     - If Cloudflare Access is configured: Leave empty (authentication handled at edge)
     - If not configured: See [MCP Security Setup](./MCP_SECURITY_SETUP.md) to add authentication

2. **Why this works**: The Cloudflare Tunnel is already configured for `api.datacrew.space` and routes through Caddy to the Lambda server. External URLs sometimes work better with Open WebUI's MCP client.

**Note**: The Cloudflare Tunnel for `api.datacrew.space` is already set up. You may want to add Cloudflare Access authentication for security (see [MCP Security Setup](./MCP_SECURITY_SETUP.md)).

#### Solution 2: Try with Trailing Slash

Some MCP clients require a trailing slash:

1. **Server URL**: `http://lambda-server:8000/mcp/` (note the trailing slash)
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

### Expected Behavior

When working correctly:
1. Open WebUI should connect to the MCP server
2. It should list available tools (25+ tools)
3. Tools should be available in chat conversations

### Current Status

- **Lambda Server**: ✅ Running and healthy
- **MCP Endpoint**: ✅ Accessible at `/mcp/`
- **Tools Available**: ✅ 25 tools registered
- **Open WebUI Compatibility**: ⚠️ Known issues with Streamable HTTP

### Testing the Connection

#### Test 1: Basic Connectivity
```bash
docker exec open-webui curl -s http://lambda-server:8000/health
# Expected: {"status":"healthy","service":"lambda-server"}
```

#### Test 2: MCP Info Endpoint
```bash
docker exec open-webui curl -s http://lambda-server:8000/mcp-info | python3 -m json.tool
# Expected: JSON with server info and tool list
```

#### Test 3: MCP Endpoint (SSE)
```bash
docker exec open-webui curl -H "Accept: text/event-stream" http://lambda-server:8000/mcp/
# Expected: SSE connection (may show session error, which is normal for direct curl)
```

### Alternative: Use Cursor IDE

If Open WebUI continues to have issues, you can use Cursor IDE which has better MCP support:

1. **Configure Cursor MCP**:
   - Edit `~/.cursor/mcp.json` (or similar)
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

### References

- [Open WebUI MCP Integration Guide](../03-apps/open-webui/docs/MCP_INTEGRATION.md)
- [Open WebUI GitHub Issue #14762](https://github.com/open-webui/open-webui/issues/14762)
- [Lambda MCP Server Documentation](../04-lambda/server/mcp/AGENTS.md)
- [MCP Protocol Specification](https://modelcontextprotocol.io)
