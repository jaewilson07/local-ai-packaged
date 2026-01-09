# MCP Server Security Setup Guide

## Security Considerations for External MCP Access

When exposing the Lambda MCP server externally via `https://api.datacrew.space/mcp`, you **must** implement authentication to prevent unauthorized access.

**Current Status**: 
- ✅ Cloudflare Tunnel is already configured for `api.datacrew.space`
- ✅ Traffic is routing through Caddy to the Lambda server
- ⚠️ **Cloudflare Access authentication is NOT yet enabled** (API is currently publicly accessible)

## Option 1: Cloudflare Access (Recommended) ✅

Cloudflare Access provides authentication at the edge before requests reach your server. This is the recommended approach for external access.

**Note**: The Cloudflare Tunnel for `api.datacrew.space` is already configured and routing traffic to the Lambda server. You only need to set up Cloudflare Access authentication.

### Check for Wildcard Access Policy First

**If you have a wildcard access policy for `*.datacrew.space`**, `api.datacrew.space` should already be covered by it! You may only need to:

1. **Verify Wildcard Application Exists**:
   - Go to https://one.dash.cloudflare.com/
   - Access → Applications
   - Look for an application with domain `*.datacrew.space` (e.g., "Datacrew Wildcard Access")

2. **Link Wildcard Application to Tunnel Route**:
   - Go to Networks → Tunnels → Your tunnel
   - Find the `api.datacrew.space` route (already configured)
   - Click **Edit**
   - Scroll to **Access** section
   - Under **Access**, select the wildcard application (e.g., "Datacrew Wildcard Access")
   - Click **Save**

**That's it!** If the wildcard application is properly configured and linked, `api.datacrew.space` will be protected.

**Note**: Specific applications (like a dedicated `api.datacrew.space` application) take precedence over wildcard applications. If you want `api.datacrew.space` to have different access rules than other subdomains, create a specific application instead.

### Setup Steps (If No Wildcard Policy Exists)

If you don't have a wildcard access policy, you can create a specific application for `api.datacrew.space`:

1. **Create/Verify Standard Access Policy** (if not already created):
   ```bash
   python3 00-infrastructure/scripts/manage-cloudflare-access.py --create-policy
   ```

2. **Create Access Application for API** (via Cloudflare Dashboard):
   - Go to https://one.dash.cloudflare.com/
   - Access → Applications → Add an application
   - Select **Self-hosted**
   - Configure:
     - **Application name**: `Lambda API`
     - **Application domain**: `api.datacrew.space`
     - **Session duration**: `24 hours` (or your preference)
   - Click **Next**

3. **Add Access Policy**:
   - In the Lambda API application → Policies tab
   - Click **Add a policy**
   - Select **Standard Access Policy** (reusable policy, if available)
   - Or create a new policy with your access rules:
     - **Policy name**: `Lambda API Access`
     - **Action**: `Allow`
     - **Include Rules**:
       - **Emails**: `jaewilson07@gmail.com` (or your email)
       - **Email domain**: `@datacrew.space` (optional)
     - **Identity Providers**: Google OAuth (if configured)
   - Click **Add application**

4. **Link Access Application to Tunnel Route**:
   - Go to Networks → Tunnels → Your tunnel
   - Find the `api.datacrew.space` route (already configured)
   - Click **Edit**
   - Scroll to **Access** section
   - Under **Access**, select **Lambda API** application (created in step 2)
   - Click **Save**

### Benefits

- ✅ Authentication at the edge (before reaching your server)
- ✅ No code changes required
- ✅ Supports multiple auth methods (Google OAuth, Email OTP, Service Tokens)
- ✅ Centralized access management
- ✅ Works with all endpoints (REST API + MCP)

### Testing

After setup, accessing `https://api.datacrew.space/mcp` should:
1. Redirect to Cloudflare Access login
2. Require authentication (Google OAuth or Email OTP)
3. Only allow authorized users

## Option 2: API Key Authentication (Alternative)

If you prefer API key authentication at the application level, you can add it to the Lambda server.

### Implementation Steps

1. **Add API Key to Configuration**:
   ```python
   # In 04-lambda/server/config.py
   class Settings(BaseSettings):
       # ... existing settings ...
       api_key: Optional[str] = Field(None, env="LAMBDA_API_KEY")
   ```

2. **Create Authentication Middleware**:
   ```python
   # In 04-lambda/server/core/auth.py
   from fastapi import HTTPException, Security
   from fastapi.security import APIKeyHeader
   from server.config import settings
   
   api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)
   
   async def verify_api_key(api_key: str = Security(api_key_header)):
       if not settings.api_key:
           return None  # No API key required if not configured
       if api_key != settings.api_key:
           raise HTTPException(status_code=401, detail="Invalid API key")
       return api_key
   ```

3. **Apply to MCP Endpoint**:
   ```python
   # In 04-lambda/server/main.py
   from server.core.auth import verify_api_key
   
   # Apply to MCP mount (requires FastMCP support for middleware)
   # Or apply at Caddy level with header validation
   ```

4. **Set API Key in Environment**:
   ```bash
   # In .env or Infisical
   LAMBDA_API_KEY=your-secret-api-key-here
   ```

5. **Configure Open WebUI**:
   - In External Tools → MCP Server
   - **Authentication**: Add header `X-API-Key: your-secret-api-key-here`
   - Or configure in Open WebUI's auth settings

### Benefits

- ✅ Application-level control
- ✅ Works with any client (not just browsers)
- ✅ Can be used alongside Cloudflare Access

### Limitations

- ⚠️ Requires code changes
- ⚠️ API keys must be managed and rotated
- ⚠️ Less user-friendly than Cloudflare Access

## Option 3: Internal Network Only (Most Secure) ✅ Recommended for Server-to-Server

For maximum security, only use the internal Docker network URL:

- **URL**: `http://lambda-server:8000/mcp` (internal only)
- **Access**: Only accessible from within Docker network
- **Authentication**: Not required (network isolation)

### When to Use

- ✅ Open WebUI is in the same Docker network (your current setup)
- ✅ No external access needed
- ✅ Maximum security (no internet exposure)
- ✅ **Best for server-to-server requests** (Open WebUI → Lambda MCP)

### Server-to-Server Authentication

**Important**: When Open WebUI (running in a container) makes requests to Lambda MCP, it's a **server-to-server** request, not a browser request. Cloudflare Access won't work for this.

**Solution**: Use the internal Docker network URL (`http://lambda-server:8000/mcp`) which:
- ✅ Bypasses Cloudflare Access (not needed for internal network)
- ✅ Faster (no external routing)
- ✅ More secure (network isolation)
- ✅ Already configured in your setup

**See**: [Open WebUI to Lambda Authentication Guide](./OPENWEBUI_LAMBDA_AUTHENTICATION.md) for detailed setup.

## Recommendation

**For External Access**: Use **Option 1 (Cloudflare Access)** because:
1. No code changes required
2. Better user experience (OAuth login)
3. Centralized access management
4. Works with all endpoints automatically

**For Internal Access**: Use **Option 3 (Internal Network)** because:
1. No authentication overhead
2. Maximum security (network isolation)
3. Faster (no external routing)

## Current Status

**Tunnel Configuration**: ✅ Already configured
- Cloudflare Tunnel route for `api.datacrew.space` is set up
- Traffic routes: Internet → Cloudflare Tunnel → Caddy → Lambda Server

**Access Authentication**: ⚠️ Check if configured
- The API may be protected by a wildcard access policy (`*.datacrew.space`)
- Or it may be publicly accessible if no access policy is linked to the tunnel route
- You should verify and set up Cloudflare Access before using in production

### Check Current Access Configuration

```bash
# List all Access applications
python3 00-infrastructure/scripts/manage-cloudflare-access.py --list

# Look for:
# 1. Wildcard application: *.datacrew.space (covers api.datacrew.space)
# 2. Specific application: api.datacrew.space (takes precedence over wildcard)
```

### Verify Tunnel Route Access

1. Go to https://one.dash.cloudflare.com/
2. Networks → Tunnels → Your tunnel
3. Find the `api.datacrew.space` route
4. Check the **Access** column:
   - If it shows a wildcard or specific application → ✅ Protected
   - If it shows "None" or is empty → ⚠️ Not protected (publicly accessible)

**If not protected**, follow the setup steps above to either:
- Link the existing wildcard application to the tunnel route, OR
- Create a specific application for `api.datacrew.space`

## Security Best Practices

1. **Always use HTTPS** for external endpoints
2. **Enable Cloudflare Access** for public-facing APIs
3. **Use internal URLs** when possible (Docker network)
4. **Rotate API keys** regularly (if using Option 2)
5. **Monitor access logs** in Cloudflare Dashboard
6. **Limit access** to specific users/domains
7. **Use service tokens** for programmatic access (Cloudflare Access)

## References

- [Cloudflare Access Setup](../00-infrastructure/scripts/manage-cloudflare-access.py)
- [Lambda API Cloudflare Setup](./API_CLOUDFLARE_SETUP.md)
- [MCP Connection Troubleshooting](./MCP_CONNECTION_TROUBLESHOOTING.md)

