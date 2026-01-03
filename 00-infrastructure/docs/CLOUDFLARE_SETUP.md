# Cloudflare Setup Guide

## Cloudflare Credentials

You need **two different types** of Cloudflare tokens:

### 1. **API Token** (for programmatic access)
- **Purpose**: Used by setup scripts to manage DNS records and tunnels via API
- **Where to get it**: https://dash.cloudflare.com/profile/api-tokens
- **Permissions needed**: 
  - Zone → DNS → Edit
  - Account → Cloudflare Tunnel → Edit
- **Save in `.env` as**: `CLOUDFLARE_API_TOKEN=your_token_here`

### 2. **Tunnel Token** (for running the tunnel)
- **Purpose**: Used by the cloudflared container to connect to Cloudflare
- **Where to get it**: After creating a tunnel in Cloudflare Zero Trust dashboard
- **Save in `.env` as**: `CLOUDFLARE_TUNNEL_TOKEN=your_tunnel_token_here`

## Quick Setup Steps

### Step 1: Add API Token to .env

```bash
# Edit .env file and add:
CLOUDFLARE_API_TOKEN=your_api_token_here
```

### Step 2: Authenticate with Cloudflare CLI

```bash
cloudflared tunnel login
```

This will open a browser for authentication.

### Step 3: Create Tunnel and Get Tunnel Token

**Option A: Using the setup script (recommended)**
```bash
python3 utils/setup/cloudflare/setup_tunnel.py
```

**Option B: Manual setup**
1. Go to https://one.dash.cloudflare.com/
2. Navigate to **Networks** → **Tunnels**
3. Click **Create a tunnel**
4. Name it (e.g., `datacrew-services`)
5. Copy the **Token** shown
6. Add to `.env`: `CLOUDFLARE_TUNNEL_TOKEN=your_tunnel_token_here`

### Step 4: Configure Tunnel Routes

Add public hostnames for each service in the Cloudflare dashboard:
- Each service needs a route pointing to `http://caddy:80` with appropriate Host Header
- See `00-infrastructure/docs/cloudflare/setup.md` for detailed route configuration

### Step 5: Restart Infrastructure

```bash
./start-stack.sh infrastructure
```

## Current Status

Check your `.env` file for:
- ✅ `CLOUDFLARE_API_TOKEN` - For API access
- ⚠️ `CLOUDFLARE_TUNNEL_TOKEN` - For tunnel connection (needs to be set)

## Files Using These Tokens

- `utils/setup/cloudflare/setup_dns.py` - Uses `CLOUDFLARE_API_TOKEN`
- `utils/setup/cloudflare/setup_tunnel_routes.py` - Uses `CLOUDFLARE_API_TOKEN`
- `00-infrastructure/docker-compose.yml` - Uses `CLOUDFLARE_TUNNEL_TOKEN` (via environment variable)

