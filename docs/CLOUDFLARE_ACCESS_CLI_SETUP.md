# Cloudflare Access Setup via CLI/API

## Overview

While `cloudflared` CLI doesn't directly support creating Access applications, you can use the Cloudflare API via a Python script to automate the setup.

## Quick Setup

Run the automated script:

```bash
python3 00-infrastructure/scripts/setup-lambda-api-access.py
```

This script will:
1. ✅ Create Cloudflare Access application for `api.datacrew.space`
2. ✅ Apply standard access policy (or create one if needed)
3. ✅ Link Access application to tunnel route
4. ✅ Verify the configuration

## Prerequisites

### Required Environment Variables

Set in Infisical or `.env`:

```bash
# Cloudflare API Authentication (one of these)
CLOUDFLARE_API_TOKEN=your-api-token
# OR
CLOUDFLARE_EMAIL=your-email@example.com
CLOUDFLARE_API_KEY=your-global-api-key

# Cloudflare Account/Tunnel IDs
CLOUDFLARE_ACCOUNT_ID=your-account-id
CLOUDFLARE_TUNNEL_ID=your-tunnel-id

# Access Policy Configuration
CLOUDFLARE_ACCESS_EMAILS=jaewilson07@gmail.com,user2@example.com
CLOUDFLARE_ACCESS_EMAIL_DOMAIN=@datacrew.space  # Optional
GOOGLE_IDP_ID=your-google-idp-id  # Optional, for Google OAuth
```

### Get Your Tunnel ID

```bash
# List all tunnels
cloudflared tunnel list

# Or check your .env file
grep CLOUDFLARE_TUNNEL_ID .env
```

## What the Script Does

### Step 1: Create Access Application

Creates a Cloudflare Access application:
- **Name**: `Lambda API`
- **Domain**: `api.datacrew.space`
- **Type**: Self-hosted
- **Session Duration**: 24 hours

### Step 2: Apply Access Policy

Uses one of:
- **Standard Reusable Policy** (if exists) - Recommended
- **New Policy** with your email/domain rules

### Step 3: Link to Tunnel Route

Updates the tunnel configuration to link the Access application to the `api.datacrew.space` route.

## Manual Alternative: Using Cloudflare API Directly

If you prefer to use the API directly:

### 1. Create Access Application

```bash
curl -X POST "https://api.cloudflare.com/client/v4/accounts/{ACCOUNT_ID}/access/apps" \
  -H "Authorization: Bearer {API_TOKEN}" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Lambda API",
    "domain": "api.datacrew.space",
    "type": "self_hosted",
    "session_duration": "24h",
    "policies": [{
      "name": "Lambda API Access",
      "decision": "allow",
      "include": [{"email": {"email": "jaewilson07@gmail.com"}}]
    }]
  }'
```

### 2. Link to Tunnel Route

```bash
# Get current tunnel config
curl "https://api.cloudflare.com/client/v4/accounts/{ACCOUNT_ID}/cfd_tunnel/{TUNNEL_ID}/configurations" \
  -H "Authorization: Bearer {API_TOKEN}"

# Update config to add access.app_id to api.datacrew.space route
curl -X PUT "https://api.cloudflare.com/client/v4/accounts/{ACCOUNT_ID}/cfd_tunnel/{TUNNEL_ID}/configurations" \
  -H "Authorization: Bearer {API_TOKEN}" \
  -H "Content-Type: application/json" \
  -d '{
    "config": {
      "ingress": [
        {
          "hostname": "api.datacrew.space",
          "service": "http://caddy:80",
          "access": {"app_id": "{APP_ID}"}
        },
        ...
      ]
    }
  }'
```

## Verification

After running the script:

```bash
# Should redirect to Cloudflare Access login
curl -I https://api.datacrew.space/mcp/openapi.json
```

**Expected**: HTTP 302 redirect to Cloudflare Access

**If you get JSON**: Still not protected - check tunnel route configuration

## Troubleshooting

### Script Fails: "API token or email+API key must be provided"

**Solution**: Set authentication in Infisical or `.env`:
```bash
infisical secrets set CLOUDFLARE_API_TOKEN=your-token
```

### Script Fails: "Tunnel route not found"

**Solution**: Create the tunnel route first:
```bash
python3 00-infrastructure/scripts/setup-cloudflare-tunnel-routes.py
```

### Access Application Created But Not Linked

**Solution**: Link manually in dashboard:
1. Go to https://one.dash.cloudflare.com/
2. Networks → Tunnels → Your tunnel
3. Find `api.datacrew.space` route
4. Edit → Access → Select "Lambda API"

## Using Wildcard Access Policy

If you have a wildcard access policy (`*.datacrew.space`), you can link it directly:

```bash
# The script will automatically use the wildcard policy if it exists
# Or link manually in dashboard (faster)
```

## References

- [Cloudflare Access API Documentation](https://developers.cloudflare.com/api/operations/access-applications-list-access-applications)
- [Cloudflare Tunnel API Documentation](https://developers.cloudflare.com/api/operations/cloudflare-tunnel-get-cloudflare-tunnel-configuration)
- [MCP Security Setup Guide](./MCP_SECURITY_SETUP.md)
- [Urgent Security Fix](./URGENT_SECURITY_FIX.md)

