---
name: cloudflare-access-setup
description: Setup Cloudflare Access for API authentication, retrieve AUD tags, configure JWT validation, and troubleshoot auth issues. Use when setting up Cloudflare Access, configuring Lambda server authentication, retrieving AUD tags, or troubleshooting JWT validation errors.
---

# Cloudflare Access Setup

Guide for setting up Cloudflare Access authentication for the Lambda API server, including automated and manual setup, AUD tag retrieval, and troubleshooting.

## Quick Setup (Automated)

Run the automated script to set up Cloudflare Access:

```bash
cd /home/jaewilson07/GitHub/local-ai-packaged
python3 00-infrastructure/scripts/setup-lambda-api-access.py
```

This script will:
1. Create Cloudflare Access application for `api.datacrew.space`
2. Apply standard access policy (or create one if needed)
3. Link Access application to tunnel route
4. Verify the configuration

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

## Understanding the AUD Tag

### What is the AUD Tag?

The **AUD Tag** (Application Audience Tag) is a unique 64-character hexadecimal identifier that Cloudflare generates for each Access application. It's used in JWT token validation to ensure tokens are only accepted from the correct application.

### Why is it Required?

When Cloudflare Access generates a JWT token for an authenticated user, it includes an `aud` (audience) claim set to your application's AUD tag. The Lambda server validates this claim matches your configured `CLOUDFLARE_AUD_TAG` before granting access. This ensures:

- Tokens from other Access applications are rejected
- Only tokens intended for your specific application are accepted
- Security is maintained even if someone obtains a valid JWT from a different application

### How to Get Your AUD Tag

**Method 1: Using the Script (Recommended)**

```bash
cd /home/jaewilson07/GitHub/local-ai-packaged
python3 00-infrastructure/scripts/get-lambda-api-aud-tag.py
```

**Method 2: From Cloudflare Dashboard**

1. Go to [Cloudflare One Dashboard](https://one.dash.cloudflare.com/)
2. Navigate to **Access controls** > **Applications**
3. Select your application (e.g., "Lambda API" for `api.datacrew.space`)
4. In the **Basic information** tab, copy the **Application Audience (AUD) Tag**

**Method 3: From Cloudflare API**

```bash
curl -X GET "https://api.cloudflare.com/client/v4/accounts/{account_id}/access/apps" \
  -H "Authorization: Bearer YOUR_API_TOKEN" \
  | jq '.result[] | select(.domain=="api.datacrew.space") | .aud'
```

### Setting the AUD Tag

Once you have the AUD tag, configure it in your environment:

```bash
# In docker-compose.yml or .env
CLOUDFLARE_AUD_TAG=e869f0dbb027893e1c9ded98f81e6c85420c574098c895a51f79a1e9930c948c

# Or via Infisical (production)
infisical secrets set CLOUDFLARE_AUD_TAG=e869f0dbb027893e1c9ded98f81e6c85420c574098c895a51f79a1e9930c948c
```

## Manual Setup via Cloudflare API

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
        }
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

**Test Authentication:**

```bash
# Get a valid JWT by accessing through browser, then:
curl -H "Cf-Access-Jwt-Assertion: <your-jwt-token>" https://api.datacrew.space/api/me
```

**Expected**: JSON response with user profile

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

### JWT Validation Errors

**Error**: `"Invalid token: Missing required audience (CLOUDFLARE_AUD_TAG)"`

**Solution**:
1. Verify AUD tag is correct:
   ```bash
   python3 00-infrastructure/scripts/get-lambda-api-aud-tag.py
   ```
2. Check environment variable is set:
   ```bash
   docker exec lambda-server env | grep CLOUDFLARE_AUD_TAG
   ```
3. Restart Lambda server if AUD tag was updated:
   ```bash
   docker compose -p localai-lambda restart lambda-server
   ```

**Error**: `"Invalid token: Invalid signature"`

**Solution**:
1. Verify `CLOUDFLARE_AUTH_DOMAIN` is correct (should match your Cloudflare team domain)
2. Check JWT is from the correct Access application
3. Ensure JWT hasn't expired (default: 24 hours)

**Error**: `"Missing Cf-Access-Jwt-Assertion header"`

**Solution**:
1. Verify request is going through Cloudflare Access (not direct to server)
2. Check Caddy is forwarding the header correctly
3. For internal network requests, use `http://lambda-server:8000` (bypasses Cloudflare Access)

### Lambda Server Can't Fetch Public Keys

**Error**: `"Failed to fetch public keys from Cloudflare"`

**Solution**:
1. Verify `CLOUDFLARE_AUTH_DOMAIN` is accessible from Lambda server
2. Check network connectivity:
   ```bash
   docker exec lambda-server curl -I https://your-team.cloudflareaccess.com/cdn-cgi/access/certs
   ```
3. Verify DNS resolution works inside container

## Internal vs External Authentication

**External Requests** (via Cloudflare Tunnel):
- Require Cloudflare Access JWT in `Cf-Access-Jwt-Assertion` header
- Go through `https://api.datacrew.space`

**Internal Requests** (Docker network):
- No authentication required (network isolation provides security)
- Use `http://lambda-server:8000`
- For Open WebUI, n8n, and other services on `ai-network`

## References

- [Cloudflare Access API Documentation](https://developers.cloudflare.com/api/operations/access-applications-list-access-applications)
- [Cloudflare Tunnel API Documentation](https://developers.cloudflare.com/api/operations/cloudflare-tunnel-get-cloudflare-tunnel-configuration)
- [Auth Project README](04-lambda/src/services/auth/README.md) - Detailed authentication system documentation
