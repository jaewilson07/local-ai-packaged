# ComfyUI Quick Setup Guide

Quick reference for setting up ComfyUI domain access and authentication.

## Prerequisites

- ✅ ComfyUI container is running
- ✅ Cloudflare Tunnel is configured
- ✅ Caddy reverse proxy is running

## Quick Steps

### 1. Add Environment Variables to `.env`

```bash
# ComfyUI Domain Configuration
COMFYUI_HOSTNAME=comfyui.datacrew.space

# ComfyUI Authentication (use strong passwords!)
COMFYUI_WEB_USER=your-username
COMFYUI_WEB_PASSWORD=your-secure-password-here
```

**Generate secure password:**
```bash
python setup/generate-env-passwords.py
# Or: xkcdpass -n 4
```

### 2. Restart ComfyUI

```bash
docker compose -p localai -f 02-compute/docker-compose.yml restart comfyui
```

### 3. Configure Cloudflare Tunnel Route

**Via Dashboard:**
1. Cloudflare Zero Trust → Networks → Tunnels
2. Your tunnel → Configure → Public Hostnames
3. Add hostname:
   - Subdomain: `comfyui`
   - Domain: `datacrew.space`
   - Service: `http://caddy:80`
   - Host Header: `comfyui.datacrew.space`

**Via Script:**
```bash
python 00-infrastructure/docs/cloudflare/setup_tunnel_routes.py
```

### 4. (Optional) Set Up Cloudflare Access

**Via CLI Script (Recommended):**
```bash
# Set access rules in .env (optional)
# COMFYUI_ACCESS_EMAILS=user@example.com,admin@example.com
# COMFYUI_ACCESS_EMAIL_DOMAIN=@yourdomain.com
# COMFYUI_CREATE_SERVICE_TOKEN=true

# Run the setup script
python3 00-infrastructure/docs/cloudflare/setup_comfyui_access.py
```

**Via Dashboard:**
1. Zero Trust → Access → Applications → Add application
2. Name: `ComfyUI`, Domain: `comfyui.datacrew.space`
3. Configure policy (who can access)
4. Link to tunnel route

See [CLI Access Setup](../../00-infrastructure/docs/cloudflare/CLI_ACCESS_SETUP.md) for detailed CLI instructions.

## Access URLs

- **Local**: `http://localhost:8188`
- **Domain**: `https://comfyui.datacrew.space`

## API Authentication

### Basic Auth (Username/Password)
```bash
curl -u "username:password" \
  https://comfyui.datacrew.space/api/v1/prompts
```

### Get Auth Tokens
```bash
bash 02-compute/comfyui/scripts/get_auth_token.sh
```

### Service Token (Cloudflare Access)
```bash
# Add to .env
COMFYUI_ACCESS_TOKEN=your-service-token

# Use in requests
curl -H "CF-Access-Token: $COMFYUI_ACCESS_TOKEN" \
  https://comfyui.datacrew.space/api/v1/prompts
```

## Verify Setup

```bash
# Check ComfyUI is running
docker ps | grep comfyui

# Test local access
curl http://localhost:8188/

# Test domain access
curl https://comfyui.datacrew.space/
```

## Full Documentation

See [DOMAIN_ACCESS.md](./DOMAIN_ACCESS.md) for detailed setup instructions.

