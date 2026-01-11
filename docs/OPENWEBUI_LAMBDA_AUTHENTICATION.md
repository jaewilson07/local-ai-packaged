# Open WebUI to Lambda Server Authentication Guide

## The Problem

When Open WebUI (public-facing, users authenticate via Cloudflare Access) makes requests to the Lambda MCP server, you need to handle **server-to-server authentication**:

- **Browser → Open WebUI**: User authenticates via Cloudflare Access ✅
- **Open WebUI → Lambda MCP**: Server-to-server request (no user browser session) ⚠️

Cloudflare Access is designed for **browser/user authentication**, not server-to-server requests. When Open WebUI (running in a container) tries to connect to `https://api.datacrew.space/mcp`, it won't have a user's Cloudflare Access session.

**Note**: The Lambda server now implements JWT validation for external requests. However, for internal Docker network communication, authentication is not required (network isolation provides security).

## Solution 1: Use Internal Docker Network (Recommended) ✅

**Best approach**: Use the internal Docker network URL, which bypasses Cloudflare Access entirely.

### Configuration

1. **In Open WebUI External Tools**:
   - **Type**: `MCP (Streamable HTTP)`
   - **Server URL**: `http://lambda-server:8000/mcp` (internal Docker network)
   - **Authentication**: Leave empty (network isolation provides security)

2. **Why this works**:
   - ✅ No authentication needed (network isolation)
   - ✅ Faster (no external routing)
   - ✅ More secure (not exposed to internet)
   - ✅ Works regardless of Cloudflare Access configuration

### Current Setup

Your `03-apps/docker-compose.yml` already configures this:
```yaml
environment:
  LAMBDA_SERVER_URL: ${LAMBDA_SERVER_URL:-http://lambda-server:8000}
```

Both Open WebUI and Lambda Server are on the same Docker network (`ai-network`), so they can communicate directly.

## Solution 2: Cloudflare Service Tokens (For External URL)

If you must use the external URL (`https://api.datacrew.space/mcp`), use **Cloudflare Service Tokens** for server-to-server authentication.

### Setup Steps

1. **Create Service Token in Cloudflare**:
   - Go to https://one.dash.cloudflare.com/
   - Access → Service Tokens → Create Token
   - Name: `Open WebUI to Lambda MCP`
   - Click **Create Token**
   - **Save the token** (shown only once!)

2. **Add Service Token to Access Policy**:
   - Go to Access → Applications → Your wildcard or API application
   - Edit the policy
   - Under **Include Rules**, add:
     - **Service Token**: Select the token you created
   - Save

3. **Configure Open WebUI to Use Service Token**:
   - In Open WebUI External Tools → MCP Server
   - **Server URL**: `https://api.datacrew.space/mcp`
   - **Authentication**:
     - Add header: `CF-Access-Client-Id: <client-id>`
     - Add header: `CF-Access-Client-Secret: <client-secret>`

   **Note**: Open WebUI may not support custom headers directly. You may need to:
   - Use a proxy/forwarder service
   - Modify Open WebUI configuration
   - Or use Solution 1 (internal network) instead

### Service Token Format

Cloudflare Service Tokens have two parts:
- **Client ID**: `xxxxx-xxxxx-xxxxx-xxxxx`
- **Client Secret**: `xxxxx-xxxxx-xxxxx-xxxxx`

Both must be sent as headers:
```
CF-Access-Client-Id: <client-id>
CF-Access-Client-Secret: <client-secret>
```

## Solution 3: API Key Authentication (Alternative)

If Service Tokens don't work with Open WebUI, implement API key authentication at the Lambda server level.

### Implementation

1. **Add API Key to Lambda Server**:
   ```python
   # In 04-lambda/server/config.py
   class Settings(BaseSettings):
       # ... existing settings ...
       api_key: Optional[str] = Field(None, env="LAMBDA_API_KEY")
   ```

2. **Create Authentication Middleware**:
   ```python
   # In 04-lambda/server/core/auth.py
   from fastapi import HTTPException, Security, Header
   from server.config import settings

   async def verify_api_key(x_api_key: str = Header(None)):
       if not settings.api_key:
           return None  # No API key required if not configured
       if x_api_key != settings.api_key:
           raise HTTPException(status_code=401, detail="Invalid API key")
       return x_api_key
   ```

3. **Apply to MCP Endpoint** (if FastMCP supports middleware):
   - Or apply at Caddy level with header validation

4. **Set API Key in Environment**:
   ```bash
   # In .env or Infisical
   LAMBDA_API_KEY=your-secret-api-key-here
   ```

5. **Configure Open WebUI**:
   - In External Tools → MCP Server
   - **Authentication**: Add header `X-API-Key: your-secret-api-key-here`
   - Or configure in Open WebUI's auth settings (if supported)

## Solution 4: Bypass Cloudflare Access for Internal IPs

Configure Cloudflare Access to bypass authentication for requests from your internal network (Open WebUI container IP).

### Setup

1. **Get Open WebUI Container IP**:
   ```bash
   docker inspect open-webui | grep IPAddress
   ```

2. **Add IP Allow Rule in Cloudflare Access**:
   - Go to Access → Applications → Your API application
   - Edit policy
   - Add **Include Rule**:
     - **IP Address**: `<open-webui-container-ip>`
   - Save

**Note**: This only works if Open WebUI requests go through Cloudflare (external URL). If using internal network, this isn't needed.

## Recommended Architecture

```
┌─────────────┐
│   Browser   │
│  (User)     │
└──────┬──────┘
       │
       │ Cloudflare Access (User Auth)
       │
┌──────▼──────────────────┐
│   Open WebUI            │
│  (Public-facing)        │
│  Container IP: 172.x.x.x│
└──────┬──────────────────┘
       │
       │ Internal Docker Network
       │ (No Auth Needed)
       │
┌──────▼──────────────┐
│  Lambda MCP Server │
│  (Internal)        │
└────────────────────┘
```

**Key Points**:
- Users authenticate to Open WebUI via Cloudflare Access
- Open WebUI connects to Lambda MCP via internal network (no auth)
- Lambda MCP is protected by network isolation (Docker network)

## Current Configuration Check

Verify your current setup:

```bash
# Check if Open WebUI can reach Lambda server
docker exec open-webui curl -s http://lambda-server:8000/health

# Check Lambda server is on same network
docker network inspect ai-network | grep -A 5 "open-webui\|lambda-server"

# Check environment variable
docker exec open-webui env | grep LAMBDA_SERVER_URL
```

## Lambda Server Authentication

The Lambda server now implements Cloudflare Access JWT validation for external requests:

- **External Requests** (`https://api.datacrew.space/*`): Require valid `Cf-Access-Jwt-Assertion` header
- **Internal Requests** (`http://lambda-server:8000/*`): No authentication required (network isolation)

**MCP Endpoints**:
- Internal network: `http://lambda-server:8000/mcp` - No authentication needed
- External URL: `https://api.datacrew.space/mcp` - Requires Cloudflare Access JWT

**REST API Endpoints**:
- All `/api/*` endpoints require authentication (except `/health`, `/docs`, `/openapi.json`)
- Use `get_current_user` dependency for JWT validation
- See [Auth Project README](../04-lambda/server/projects/auth/README.md) for details

## Best Practice Recommendation

**Use Solution 1 (Internal Network)** because:
1. ✅ No authentication complexity
2. ✅ Faster (no external routing)
3. ✅ More secure (network isolation)
4. ✅ Works regardless of Cloudflare Access
5. ✅ Already configured in your setup
6. ✅ Lambda server doesn't require JWT validation for internal requests

Only use external URL (`https://api.datacrew.space/mcp`) if:
- You need external access from outside Docker network
- You're testing from a different environment
- You have specific requirements for external routing
- You can provide Cloudflare Access JWT tokens

## Troubleshooting

### Open WebUI Can't Connect to Lambda MCP

1. **Check Network Connectivity**:
   ```bash
   docker exec open-webui ping -c 1 lambda-server
   ```

2. **Check Lambda Server is Running**:
   ```bash
   docker ps | grep lambda-server
   docker exec lambda-server curl -s http://localhost:8000/health
   ```

3. **Check MCP Endpoint**:
   ```bash
   docker exec open-webui curl -s http://lambda-server:8000/mcp-info
   ```

4. **Check Open WebUI Logs**:
   ```bash
   docker logs open-webui --tail 50 | grep -i mcp
   ```

### Authentication Errors

If using external URL and getting auth errors:
- Verify Cloudflare Access is configured correctly
- Check Service Token is valid (if using)
- Verify API key is set (if using)
- Check Lambda server logs for auth failures

## References

- [MCP Security Setup](./MCP_SECURITY_SETUP.md)
- [MCP Connection Troubleshooting](./MCP_CONNECTION_TROUBLESHOOTING.md)
- [Cloudflare Service Tokens Documentation](https://developers.cloudflare.com/cloudflare-one/identity/service-tokens/)
