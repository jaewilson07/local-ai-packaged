# ComfyUI Domain Access and Authentication Setup

This guide explains how to access ComfyUI via `comfyui.datacrew.space` and configure authentication for both web UI and API access.

## Overview

ComfyUI can be accessed through:
1. **Local access**: `http://localhost:8188` (direct port mapping)
2. **Domain access**: `https://comfyui.datacrew.space` (via Cloudflare Tunnel → Caddy)

Authentication is handled at two levels:
1. **ComfyUI built-in authentication** (WEB_USER/WEB_PASSWORD) - Required for all access
2. **Cloudflare Access** (optional) - Additional layer for domain access

## Step 1: Configure Environment Variables

### Add to `.env` file:

```bash
############
# ComfyUI Configuration
############
COMFYUI_HOSTNAME=comfyui.datacrew.space
COMFYUI_WEB_USER=your-username-here
COMFYUI_WEB_PASSWORD=your-secure-password-here
```

**Security Notes:**
- Use strong passwords (XKCD-style passphrases recommended)
- Store `COMFYUI_WEB_PASSWORD` in Infisical for production
- Never commit passwords to git

### Generate Secure Password:

```bash
# Using the project password generator
python setup/generate-env-passwords.py

# Or manually generate XKCD-style passphrase
xkcdpass -n 4  # Example: "correct-horse-battery-staple"
```

## Step 2: Restart ComfyUI

After updating environment variables:

```bash
cd 02-compute
docker compose restart comfyui
```

Or restart the entire compute stack:

```bash
python start_services.py --stack compute --profile gpu-nvidia
```

## Step 3: Configure Cloudflare Tunnel Route

### Option A: Using Cloudflare Dashboard (Recommended)

1. Go to [Cloudflare Zero Trust Dashboard](https://one.dash.cloudflare.com/)
2. Navigate to **Networks** → **Tunnels**
3. Find your tunnel (e.g., `datacrew-services`)
4. Click **Configure** → **Public Hostnames** tab
5. Click **Add a public hostname**
6. Configure:
   - **Subdomain**: `comfyui`
   - **Domain**: `datacrew.space`
   - **Service**: `http://caddy:80`
   - **HTTP Host Header**: `comfyui.datacrew.space`
7. Click **Save hostname**

### Option B: Using API Script

```bash
# Ensure you have Cloudflare credentials in .env
python 00-infrastructure/docs/cloudflare/setup_tunnel_routes.py
```

## Step 4: Configure Cloudflare Access (Optional but Recommended)

Cloudflare Access adds an additional authentication layer for domain access. This is separate from ComfyUI's built-in authentication.

### Step 4.1: Create Access Application

1. In Zero Trust dashboard, go to **Access** → **Applications**
2. Click **Add an application** → **Self-hosted**
3. Configure:
   - **Application name**: `ComfyUI`
   - **Session Duration**: `24 hours` (or your preference)
   - **Application Domain**: `comfyui.datacrew.space`
4. Click **Next**

### Step 4.2: Configure Access Policy

1. **Policy Name**: `ComfyUI Access Policy`
2. **Action**: `Allow`
3. **Include Rules**: Choose who can access:
   - **Emails ending in**: `@yourdomain.com` (or specific emails)
   - **Email**: `user@example.com` (for specific users)
   - **Service Token**: (for API access - see Step 5)
4. **Identity Providers**: Enable your preferred method:
   - **Google OAuth** (requires Google Cloud setup)
   - **Email OTP** (one-time password via email)
   - **Service Token** (for API access)
5. Click **Next** → **Add application**

### Step 4.3: Link Application to Tunnel Route

1. Go back to **Networks** → **Tunnels** → Your tunnel
2. Find the `comfyui.datacrew.space` route
3. Click **Edit**
4. Scroll to **Access** section
5. Select **ComfyUI** application (created above)
6. Click **Save**

## Step 5: API Authentication

ComfyUI API supports multiple authentication methods:

### Method 1: Basic Authentication (Username/Password)

```bash
curl -u "username:password" \
  http://localhost:8188/api/v1/prompts
```

For domain access:
```bash
curl -u "username:password" \
  https://comfyui.datacrew.space/api/v1/prompts
```

### Method 2: Bearer Token (Service Token)

If using Cloudflare Access:

1. **Create Service Token**:
   - Go to **Access** → **Service Tokens**
   - Click **Create Service Token**
   - Name: `comfyui-api`
   - Copy the token (shown only once!)

2. **Add to `.env`**:
   ```bash
   COMFYUI_ACCESS_TOKEN=your-service-token-here
   ```

3. **Use in API calls**:
   ```bash
   curl -H "CF-Access-Token: your-service-token" \
     https://comfyui.datacrew.space/api/v1/prompts
   ```

### Method 3: Get Authentication Token from Container

The ComfyUI container generates authentication tokens automatically:

```bash
# Get authentication information
bash 02-compute/comfyui/scripts/get_auth_token.sh
```

This will show:
- Username and password
- WEB_TOKEN (Bearer token)
- WEB_PASSWORD_B64 (base64 encoded password)
- Basic Auth token

### Method 4: Using Python Client

```python
from utils.comfyui_api_client import get_comfyui_client

# Local access (no Cloudflare token needed)
client = get_comfyui_client("http://localhost:8188")

# Domain access (requires Cloudflare Access token)
client = get_comfyui_client(
    "https://comfyui.datacrew.space",
    access_token=os.getenv("COMFYUI_ACCESS_TOKEN")
)
```

## Step 6: Verify Access

### Test Local Access:

```bash
# Check if ComfyUI is running
curl http://localhost:8188/

# Test API with authentication
curl -u "username:password" \
  http://localhost:8188/api/v1/system_stats
```

### Test Domain Access:

```bash
# Check if domain resolves
curl https://comfyui.datacrew.space/

# Test API with authentication
curl -u "username:password" \
  https://comfyui.datacrew.space/api/v1/system_stats
```

## Authentication Flow

### For Web UI Access:

1. **Local**: `http://localhost:8188`
   - ComfyUI login page → Enter WEB_USER/WEB_PASSWORD

2. **Domain**: `https://comfyui.datacrew.space`
   - Cloudflare Access challenge (if enabled) → OAuth/Email OTP
   - ComfyUI login page → Enter WEB_USER/WEB_PASSWORD

### For API Access:

1. **Local**: `http://localhost:8188/api/*`
   - Basic Auth: `-u "username:password"`
   - Bearer Token: `-H "Authorization: Bearer <token>"`

2. **Domain**: `https://comfyui.datacrew.space/api/*`
   - Cloudflare Access: `-H "CF-Access-Token: <service-token>"`
   - ComfyUI Auth: `-u "username:password"` or Bearer token

## Troubleshooting

### Issue: Cannot access via domain

**Check:**
1. Cloudflare tunnel route is configured correctly
2. `COMFYUI_HOSTNAME` is set in `.env`
3. Caddy is running: `docker ps | grep caddy`
4. ComfyUI is running: `docker ps | grep comfyui`

**Verify:**
```bash
# Check Caddy logs
docker logs caddy | grep comfyui

# Check ComfyUI logs
docker logs comfyui | tail -50
```

### Issue: Authentication fails

**Check:**
1. Environment variables are set correctly
2. Container was restarted after env changes
3. Password doesn't contain special characters that need escaping

**Verify:**
```bash
# Check environment variables in container
docker exec comfyui env | grep WEB_

# Get authentication tokens
bash 02-compute/comfyui/scripts/get_auth_token.sh
```

### Issue: Cloudflare Access not working

**Check:**
1. Access application is created and linked to tunnel route
2. Access policy includes your email/service token
3. Identity provider is configured correctly

**Verify:**
- Check Cloudflare Zero Trust dashboard
- Review tunnel route configuration
- Test with service token

## Security Best Practices

1. **Use strong passwords**: XKCD-style passphrases (4+ words)
2. **Enable Cloudflare Access**: Adds additional security layer
3. **Use Service Tokens for API**: More secure than username/password
4. **Store secrets in Infisical**: Don't commit to git
5. **Rotate credentials regularly**: Especially if compromised
6. **Limit Access Policies**: Only allow necessary users/emails
7. **Monitor Access Logs**: Review Cloudflare Zero Trust logs regularly

## Related Documentation

- [Cloudflare Access Setup](../00-infrastructure/docs/cloudflare/access-setup.md)
- [ComfyUI Access Implementation](../00-infrastructure/docs/cloudflare/comfyui-access-implementation.md)
- [Caddy Integration](../00-infrastructure/docs/cloudflare/caddy-integration.md)
- [Environment Variables](../00-infrastructure/docs/cloudflare/ENV_VARIABLES.md)
