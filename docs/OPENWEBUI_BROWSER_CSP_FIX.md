# Open WebUI Browser CSP Fix

## Problem

Open WebUI's frontend (running in the browser) tries to fetch from `http://lambda-server:8000/api/v1/mcp/openapi.json`, but:

1. **Browser can't resolve `lambda-server`**: It's an internal Docker network hostname, not accessible from the browser
2. **CSP blocks HTTP connections**: The Content Security Policy only allows `https:` connections
3. **CSP blocks external domains**: The CSP `connect-src` directive needs to explicitly allow `api.datacrew.space`

## Solution: Use External URL

Since the browser can't access internal Docker network hostnames, you must use the **external URL** through Cloudflare Tunnel:

### Configuration

1. **In Open WebUI External Tools**:
   - **Type**: `OpenAPI` (or `MCP (Streamable HTTP)` if supported)
   - **Server URL**: `https://api.datacrew.space/mcp/openapi.json`
     - This endpoint generates an OpenAPI spec from FastMCP tools
     - Or use: `https://api.datacrew.space/api/v1/mcp/tools/call` for direct REST API access

2. **CSP Updated**: The Caddyfile has been updated to allow connections to `https://api.datacrew.space` in the `connect-src` directive.

### Why This Works

- ✅ Browser can resolve `api.datacrew.space` (public DNS)
- ✅ HTTPS is allowed by CSP
- ✅ External URL routes through Cloudflare Tunnel → Caddy → Lambda Server
- ✅ Protected by Cloudflare Access (if configured)

## Alternative: Proxy Through Open WebUI Backend

If you want to keep using internal network URLs, you can configure Open WebUI's backend to proxy requests:

1. **Configure Open WebUI** to proxy MCP requests through its backend
2. **Backend makes requests** to `http://lambda-server:8000` (internal network)
3. **Frontend makes requests** to Open WebUI backend (same origin, no CSP issues)

However, this requires Open WebUI configuration changes and may not be supported out of the box.

## Current CSP Configuration

The Caddyfile has been updated with:

```caddy
connect-src 'self' https: https://cloudflareinsights.com https://api.datacrew.space
```

This allows:
- ✅ Same-origin requests (`'self'`)
- ✅ All HTTPS connections (`https:`)
- ✅ Cloudflare Insights (`https://cloudflareinsights.com`)
- ✅ Lambda API (`https://api.datacrew.space`)

## Testing

After updating the configuration:

1. **Restart Caddy** to apply CSP changes:
   ```bash
   docker exec caddy caddy reload --config /etc/caddy/Caddyfile
   ```

2. **Test from browser console**:
   ```javascript
   fetch('https://api.datacrew.space/api/v1/mcp/tools/list')
     .then(r => r.json())
     .then(console.log)
   ```

3. **Check browser console** for CSP errors (should be gone)

## Security Note

Using the external URL means:
- ✅ Requests go through Cloudflare Access (if configured)
- ✅ Protected by Cloudflare Tunnel
- ⚠️ Requires Cloudflare Access authentication (see [MCP Security Setup](./MCP_SECURITY_SETUP.md))

If Cloudflare Access is not configured, the API is publicly accessible. Consider:
1. Setting up Cloudflare Access (recommended)
2. Or using the proxy approach through Open WebUI backend

## References

- [MCP Security Setup](./MCP_SECURITY_SETUP.md)
- [FastMCP REST API Setup](./FASTMCP_REST_API_SETUP.md)
- [Open WebUI Lambda Authentication](./OPENWEBUI_LAMBDA_AUTHENTICATION.md)

