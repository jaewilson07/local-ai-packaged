# Lambda MongoDB RAG API - Cloudflare Exposure Setup

## Overview

The Lambda MongoDB RAG API is now exposed via Cloudflare Tunnel at:
- **Public URL**: `https://api.datacrew.space`
- **Container**: `lambda-server`
- **Port**: 8000 (internal)

**Note**: If you currently have Postman or another service at `api.datacrew.space`, you'll need to:
1. Move that service to `postman.datacrew.space` (or another subdomain)
2. Update the Cloudflare Tunnel route for `api.datacrew.space` to point to `http://caddy:80`
3. Update/remove any Cloudflare Access policies on `api.datacrew.space` if needed

## Configuration Changes

### 1. Caddy Reverse Proxy (`00-infrastructure/caddy/Caddyfile`)

Added routing configuration for api.datacrew.space:

```caddyfile
# Lambda API route for Cloudflare Tunnel (MongoDB RAG API)
@lambda_api host api.datacrew.space
handle @lambda_api {
    import security_headers_base
    request_body {
        max_size 50MB  # Support document uploads for RAG ingestion
    }
    reverse_proxy lambda-server:8000 {
        import standard_proxy
        import extended_timeouts  # RAG operations and LLM responses can take time
    }
}
```

**Configuration Details**:
- **Security**: Standard security headers applied
- **Max body size**: 50MB to support document uploads
- **Timeouts**: Extended timeouts for long-running RAG operations
- **Proxy**: Routes to `lambda-server:8000` container

### 2. Cloudflare Tunnel Routes (`00-infrastructure/scripts/setup-cloudflare-tunnel-routes.py`)

Added lambda service to SERVICES dictionary:

```python
SERVICES = {
    # ... other services ...
    "lambda": {"subdomain": "api", "port": 8000},  # MongoDB RAG API
}
```

## Deployment Steps

### Step 1: Restart Caddy

Reload Caddy configuration to apply the new route:

```bash
# Option A: Reload only (preferred - no downtime)
docker exec caddy caddy reload --config /etc/caddy/Caddyfile

# Option B: Restart container
docker restart caddy
```

### Step 2: Configure Cloudflare Tunnel Route

Run the setup script to add/update the api.datacrew.space route:

```bash
cd /home/jaewilson07/GitHub/local-ai-packaged
python 00-infrastructure/scripts/setup-cloudflare-tunnel-routes.py
```

This will:
1. Connect to Cloudflare API using credentials from Infisical or `.env`
2. Configure the tunnel to route `api.datacrew.space` → `http://caddy:80`
3. Caddy will then route to `lambda-server:8000` based on the Host header

**Important**: This will replace any existing tunnel route for `api.datacrew.space`. If you have Postman currently configured there, the route will be updated to point to the Lambda API instead.

### Step 3: (Optional) Move Postman to postman.datacrew.space

If Postman is currently at `api.datacrew.space`, you'll need to reconfigure it:

**Option A: Manual Cloudflare Dashboard**
1. Go to Cloudflare Dashboard → Networks → Tunnels → Your Tunnel
2. Edit the Public Hostname for your Postman service
3. Change hostname from `api.datacrew.space` to `postman.datacrew.space`
4. Update any Cloudflare Access policies to use the new hostname

**Option B: Via Cloudflare API**
If your Postman tunnel route has a specific service URL, you may need to manually update it in the Cloudflare dashboard or API.

### Step 4: Verify DNS

The DNS record for `api.datacrew.space` should automatically update when you configure the tunnel route:
- Go to Cloudflare Dashboard → DNS → Records
- The `api` CNAME record should point to your tunnel (e.g., `<tunnel-id>.cfargotunnel.com`)
- This may already exist if Postman was using it

If you're moving Postman to `postman.datacrew.space`:
- A new `postman` CNAME record will be created automatically when you configure that route

If not present, the script will create it automatically.

### Step 5: Test the API

```bash
# Health check
curl https://api.datacrew.space/health

# MongoDB health check
curl https://api.datacrew.space/health/mongodb

# RAG search endpoint
curl -X POST https://api.datacrew.space/api/v1/rag/search \
  -H "Content-Type: application/json" \
  -d '{"query": "test", "search_type": "hybrid"}'

# RAG agent endpoint
curl -X POST https://api.datacrew.space/api/v1/rag/agent \
  -H "Content-Type: application/json" \
  -d '{"query": "What documents are in the knowledge base?"}'

# Search code examples
curl -X POST https://api.datacrew.space/api/v1/rag/code-examples/search \
  -H "Content-Type: application/json" \
  -d '{"query": "authentication", "match_count": 5}'

# Search Graphiti knowledge graph
curl -X POST https://api.datacrew.space/api/v1/graphiti/search \
  -H "Content-Type: application/json" \
  -d '{"query": "authentication", "match_count": 5}'
```

## API Endpoints

All endpoints are now available at `https://api.datacrew.space`:

### Health Checks
- `GET /health` - Basic health check
- `GET /health/mongodb` - MongoDB connection health

### MongoDB RAG Operations
- `POST /api/v1/rag/search` - Search the knowledge base
  - Request: `{"query": "string", "match_count": 5, "search_type": "hybrid|semantic|text"}`

- `POST /api/v1/rag/ingest` - Ingest documents
  - Multipart form with files

- `POST /api/v1/rag/agent` - Conversational agent
  - Request: `{"query": "string"}`

- `POST /api/v1/rag/code-examples/search` - Search for code examples
  - Request: `{"query": "string", "match_count": 5}`

- `GET /api/v1/rag/sources` - Get available data sources
  - Returns: List of crawled domains/paths with statistics

### Graphiti RAG Operations
- `POST /api/v1/graphiti/search` - Search Graphiti knowledge graph
  - Request: `{"query": "string", "match_count": 5}`
  - Requires: `USE_GRAPHITI=true`

- `POST /api/v1/graphiti/knowledge-graph/repositories` - Parse GitHub repository
  - Request: `{"repo_url": "string", "branch": "string"}`
  - Requires: `USE_KNOWLEDGE_GRAPH=true`

- `POST /api/v1/graphiti/knowledge-graph/validate` - Validate AI script for hallucinations
  - Request: `{"script": "string", "repo_url": "string"}`
  - Requires: `USE_KNOWLEDGE_GRAPH=true`

- `POST /api/v1/graphiti/knowledge-graph/query` - Query Neo4j knowledge graph
  - Request: `{"command": "string"}`
  - Requires: `USE_KNOWLEDGE_GRAPH=true`

### MCP Tools (Model Context Protocol)
- `POST /mcp/tools/list` - List available MCP tools
- `POST /mcp/tools/call` - Execute MCP tool

## Architecture Flow

```
Internet
  ↓
Cloudflare Edge
  ↓
Cloudflare Tunnel (cloudflared container)
  ↓
Caddy Reverse Proxy (port 80)
  ↓ (routes based on Host: api.datacrew.space)
Lambda Server (port 8000)
  ↓ (connects to)
MongoDB (01-data stack) + Neo4j (01-data stack, optional) + Ollama (02-compute stack)
```

## Security Considerations

### Applied Security Headers
- `X-Content-Type-Options: nosniff`
- `X-Frame-Options: SAMEORIGIN`
- `X-XSS-Protection: 1; mode=block`
- `Referrer-Policy: strict-origin-when-cross-origin`
- `Strict-Transport-Security: max-age=31536000`
- Permissions-Policy (disables unnecessary features)

### Request Limits
- **Max body size**: 50MB (sufficient for document uploads)
- **Timeouts**: Extended (300s read/write) for long RAG operations

### Access Control (Recommended)

**Current Status**: The Cloudflare Tunnel for `api.datacrew.space` is already configured and routing traffic.

**Access Authentication**: Check if a wildcard access policy (`*.datacrew.space`) exists. If so, `api.datacrew.space` may already be covered. Verify by checking the tunnel route's Access setting in the Cloudflare dashboard.

**To add authentication via Cloudflare Access** (if not already covered by wildcard):

1. **Via Cloudflare Dashboard** (Recommended):
   - Go to https://one.dash.cloudflare.com/
   - Access → Applications → Add an application
   - Select **Self-hosted**
   - Configure:
     - **Application name**: `Lambda API`
     - **Application domain**: `api.datacrew.space`
   - Add a policy with your access rules (emails, Google OAuth, etc.)
   - Link the application to your tunnel route (Networks → Tunnels → Your tunnel → Edit route → Access)

2. **Verify Access Application**:
   ```bash
   python3 00-infrastructure/scripts/manage-cloudflare-access.py --list
   # Look for "api.datacrew.space" in the output
   ```

**Security Note**: Without Cloudflare Access, anyone on the internet can access your API endpoints. It's strongly recommended to enable authentication before using the external URL in production.

**See**: [cloudflare-access-setup skill](../../.cursor/skills/cloudflare-access-setup/SKILL.md) for detailed setup instructions.

## Troubleshooting

### Route Not Working

1. **Check Caddy configuration**:
   ```bash
   docker exec caddy caddy validate --config /etc/caddy/Caddyfile
   docker logs caddy --tail 50
   ```

2. **Check Cloudflare Tunnel**:
   ```bash
   docker logs cloudflared --tail 50
   ```

3. **Verify tunnel routes**:
   - Go to Cloudflare Dashboard → Networks → Tunnels
   - Click on your tunnel → Public Hostname
   - Verify `api.datacrew.space` routes to `http://caddy:80`
   - If Postman was using this, the route should now point to Caddy/Lambda

4. **Check lambda-server**:
   ```bash
   docker ps | grep lambda-server
   docker logs lambda-server --tail 50
   ```

### DNS Issues

If DNS doesn't resolve:
1. Check Cloudflare DNS records (should have CNAME for `api`)
2. Wait a few minutes for DNS propagation
3. Clear local DNS cache: `sudo systemd-resolve --flush-caches` (Linux)

### 502/504 Errors

If you get gateway errors:
1. Ensure lambda-server is running: `docker ps | grep lambda-server`
2. Check MongoDB is accessible: `curl http://lambda-server:8000/health/mongodb`
3. Verify network connectivity: `docker exec lambda-server ping -c 3 mongodb`

## Rollback

To remove the api.datacrew.space route:

```bash
# Remove from Cloudflare
python 00-infrastructure/scripts/setup-cloudflare-tunnel-routes.py --remove api.datacrew.space

# Remove from Caddyfile (or comment out the @lambda_api section)
# Then reload:
docker exec caddy caddy reload --config /etc/caddy/Caddyfile
```

## Related Documentation

- [Lambda Stack README](../README.md)
- [Lambda AGENTS.md](../AGENTS.md)
- [cloudflare-access-setup skill](../../.cursor/skills/cloudflare-access-setup/SKILL.md)
- [Caddy Configuration](../../00-infrastructure/caddy/QUICK_REFERENCE.md)
