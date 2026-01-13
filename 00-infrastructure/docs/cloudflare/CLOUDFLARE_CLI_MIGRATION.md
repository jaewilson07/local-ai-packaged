# Cloudflare CLI Migration Guide

## Quick Reference: Using cloudflared CLI

This guide shows how to use the `cloudflared` CLI to migrate Postman from `api.datacrew.space` to `postman.datacrew.space` and configure the Lambda RAG API.

## Prerequisites

1. **Install cloudflared CLI**:
   ```bash
   # macOS
   brew install cloudflared

   # Linux
   wget https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-linux-amd64
   chmod +x cloudflared-linux-amd64
   sudo mv cloudflared-linux-amd64 /usr/local/bin/cloudflared

   # Windows
   winget install --id Cloudflare.cloudflared
   ```

2. **Authenticate** (if not already done):
   ```bash
   cloudflared tunnel login
   ```
   This opens a browser to authenticate with your Cloudflare account.

3. **Get your tunnel ID**:
   ```bash
   # List all tunnels
   cloudflared tunnel list

   # Or check your .env file
   grep CLOUDFLARE_TUNNEL_ID .env
   ```

## Automated Migration Script

**Recommended approach** - Use the migration script:

```bash
# Dry run to see what will happen
python 00-infrastructure/scripts/migrate-postman-to-lambda-api.py --dry-run

# Execute the migration
python 00-infrastructure/scripts/migrate-postman-to-lambda-api.py
```

The script will:
1. Backup current Postman route information
2. Configure `api.datacrew.space` → Lambda RAG API
3. Optionally configure `postman.datacrew.space` → Postman service
4. Reload Caddy configuration
5. Test the new API endpoint

## Manual Commands (Alternative)

If you prefer to run commands manually:

### Step 1: List Current Tunnel Info

```bash
export TUNNEL_ID="your-tunnel-id"  # From .env file

# Get tunnel details
cloudflared tunnel info $TUNNEL_ID
```

### Step 2: Configure DNS Route for Lambda API

```bash
# Add DNS route for api.datacrew.space
cloudflared tunnel route dns $TUNNEL_ID api.datacrew.space
```

This creates/updates the DNS record to point to your tunnel.

### Step 3: Configure DNS Route for Postman (Optional)

```bash
# Add DNS route for postman.datacrew.space
cloudflared tunnel route dns $TUNNEL_ID postman.datacrew.space
```

### Step 4: View Current Routes

```bash
# List DNS routes
cloudflared tunnel route dns --filter-tunnel-id $TUNNEL_ID
```

### Step 5: Update Tunnel Configuration via API

Since this project uses **token-based tunnels**, the actual service routing is managed via the Cloudflare Dashboard or API, not a config file.

**Via Python Script** (recommended):
```bash
python 00-infrastructure/scripts/setup-cloudflare-tunnel-routes.py
```

This will configure the tunnel to route `api.datacrew.space` to `http://caddy:80`.

**Via Cloudflare Dashboard** (manual):
1. Go to https://dash.cloudflare.com
2. Navigate to **Networks** → **Tunnels**
3. Click on your tunnel
4. Go to **Public Hostname** tab
5. Edit or add route for `api.datacrew.space`:
   - **Hostname**: `api.datacrew.space`
   - **Service**: `http://caddy:80`
   - **Save**

### Step 6: Reload Caddy

```bash
# Reload Caddy configuration
docker exec caddy caddy reload --config /etc/caddy/Caddyfile

# Or restart if reload fails
docker restart caddy
```

### Step 7: Test the API

```bash
# Health check
curl https://api.datacrew.space/health

# MongoDB health
curl https://api.datacrew.space/health/mongodb

# RAG search
curl -X POST https://api.datacrew.space/api/v1/rag/search \
  -H "Content-Type: application/json" \
  -d '{"query": "test", "search_type": "hybrid"}'
```

## Cloudflare CLI Command Reference

### Tunnel Management

```bash
# List all tunnels
cloudflared tunnel list

# Get tunnel info
cloudflared tunnel info <tunnel-id>

# Delete a tunnel (careful!)
cloudflared tunnel delete <tunnel-id>
```

### DNS Route Management

```bash
# Add DNS route
cloudflared tunnel route dns <tunnel-id> <hostname>

# List DNS routes
cloudflared tunnel route dns

# Filter by tunnel
cloudflared tunnel route dns --filter-tunnel-id <tunnel-id>

# Delete DNS route
cloudflared tunnel route dns --delete <hostname>
```

### IP Route Management (Advanced)

```bash
# Add IP route (for private networks)
cloudflared tunnel route ip add <cidr> <tunnel-id>

# List IP routes
cloudflared tunnel route ip show

# Delete IP route
cloudflared tunnel route ip delete <cidr>
```

## Token-Based vs Config File Tunnels

This project uses **token-based tunnels**, which means:

- ✅ Routes managed via Cloudflare Dashboard or API
- ✅ No config file needed on the server
- ✅ Easier to update routes dynamically
- ✅ Token stored in `CLOUDFLARE_TUNNEL_TOKEN` env var

If you were using a config file tunnel, you'd have a `config.yml` like:

```yaml
tunnel: <tunnel-id>
credentials-file: /path/to/credentials.json

ingress:
  - hostname: api.datacrew.space
    service: http://caddy:80
  - hostname: postman.datacrew.space
    service: http://postman:3000
  - service: http_status:404
```

But with token-based tunnels, this is all managed in the Cloudflare Dashboard.

## Troubleshooting

### DNS Not Resolving

```bash
# Check DNS records
dig api.datacrew.space

# Or use Cloudflare DNS
dig @1.1.1.1 api.datacrew.space

# Clear local DNS cache (Linux)
sudo systemd-resolve --flush-caches

# Clear local DNS cache (macOS)
sudo dscacheutil -flushcache; sudo killall -HUP mDNSResponder
```

### Tunnel Not Running

```bash
# Check tunnel status
docker ps | grep cloudflared

# Check logs
docker logs cloudflared --tail 50

# Restart tunnel
docker restart cloudflared
```

### Routes Not Working

```bash
# Verify tunnel routes in dashboard
# Go to: https://dash.cloudflare.com → Networks → Tunnels → Public Hostname

# Check Caddy is routing correctly
docker exec caddy caddy validate --config /etc/caddy/Caddyfile
docker logs caddy --tail 50

# Test internal routing
docker exec caddy curl -H "Host: api.datacrew.space" http://localhost:80/health
```

## Cloudflare Access (Optional)

If you want to add authentication to the API:

### Via Cloudflare Dashboard

1. Go to **Zero Trust** → **Access** → **Applications**
2. Click **Add an application**
3. Choose **Self-hosted**
4. Configure:
   - **Application name**: Lambda RAG API
   - **Subdomain**: `api` | **Domain**: `datacrew.space`
   - **Session duration**: As needed
5. Create access policy (e.g., email domain, IP range)

### Via Script

```bash
python 00-infrastructure/scripts/manage-cloudflare-access.py \
  --create-policy \
  --application api.datacrew.space
```

## Next Steps

After migration:

1. ✅ Test all API endpoints
2. ✅ Update any client applications to use new URL
3. ✅ Update documentation with new URLs
4. ✅ Configure Cloudflare Access if needed
5. ✅ Set up monitoring/alerting
6. ✅ Update Postman collections with new base URL

## Related Documentation

- [Cloudflare Tunnel Documentation](https://developers.cloudflare.com/cloudflare-one/connections/connect-apps/)
- [cloudflared CLI Reference](https://developers.cloudflare.com/cloudflare-one/connections/connect-apps/install-and-setup/tunnel-guide/local/local-management/arguments/)
- [Lambda API Setup Guide](../../04-lambda/docs/API_CLOUDFLARE_SETUP.md)
