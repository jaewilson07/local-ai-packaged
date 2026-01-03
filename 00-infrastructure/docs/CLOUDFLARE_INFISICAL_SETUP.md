# Cloudflare Setup for Infisical Login

Infisical CLI login requires a proper domain (not localhost) for OAuth redirects. This guide will help you set up Cloudflare tunnel to expose Infisical via `infisical.datacrew.space`.

## Quick Setup Steps

### Step 1: Get Cloudflare Tunnel Token

**Option A: Via Cloudflare Dashboard (Recommended)**

1. Go to https://one.dash.cloudflare.com/
2. Navigate to **Networks** → **Tunnels**
3. Find your tunnel: `3885d13d-2d48-47ee-811c-878920be4d69` (or create a new one)
4. Click on the tunnel → **Configure**
5. Copy the **Token** shown at the top
6. Add to your `.env` file:
   ```bash
   CLOUDFLARE_TUNNEL_TOKEN=your_tunnel_token_here
   ```

**Option B: Create New Tunnel**

If the tunnel doesn't exist:
1. Go to https://one.dash.cloudflare.com/
2. Navigate to **Networks** → **Tunnels**
3. Click **Create a tunnel**
4. Name it: `datacrew-services`
5. Copy the **Token** shown
6. Add to `.env`: `CLOUDFLARE_TUNNEL_TOKEN=your_tunnel_token_here`

### Step 2: Configure Tunnel Route for Infisical

You need to add a public hostname for Infisical in the Cloudflare dashboard:

1. Go to your tunnel configuration: https://one.dash.cloudflare.com/ → **Networks** → **Tunnels** → Your tunnel
2. Click **Configure** → **Public Hostnames** tab
3. Click **Add a public hostname**
4. Configure:
   - **Subdomain**: `infisical`
   - **Domain**: `datacrew.space`
   - **Service**: `http://caddy:80`
   - **HTTP Host Header**: `infisical.datacrew.space`
5. Click **Save hostname**

**OR use the automated script:**

```bash
# Make sure you have CLOUDFLARE_API_TOKEN in .env
python3 00-infrastructure/docs/cloudflare/configure_hostnames.py
```

This will configure all services including `infisical.datacrew.space`.

### Step 3: Update Infisical SITE_URL

Once the tunnel is working, update Infisical to use the domain:

1. Edit `.env` file and change:
   ```bash
   # Change from:
   INFISICAL_SITE_URL=http://localhost:8010
   
   # To:
   INFISICAL_SITE_URL=https://infisical.datacrew.space
   ```

2. Restart Infisical:
   ```bash
   cd 00-infrastructure
   docker compose restart infisical-backend
   ```

### Step 4: Verify Tunnel is Working

```bash
# Check cloudflared container
docker ps | grep cloudflared
# Should show "Up" status, not "Restarting"

# Check logs
docker logs cloudflared --tail 20
# Should show "Connection established" or similar

# Test access
curl -I https://infisical.datacrew.space
# Should return 200 OK
```

### Step 5: Login to Infisical CLI

Now you can login with the domain:

```bash
infisical login --host=https://infisical.datacrew.space
```

This will:
1. Open your browser
2. Redirect to `https://infisical.datacrew.space` for authentication
3. Complete OAuth flow
4. Store authentication token locally

## Troubleshooting

### Cloudflared Container Restarting

**Issue**: Container keeps restarting
**Solution**: 
- Check if `CLOUDFLARE_TUNNEL_TOKEN` is set in `.env`
- Verify token is valid in Cloudflare dashboard
- Check logs: `docker logs cloudflared`

### Cannot Access infisical.datacrew.space

**Issue**: Domain not accessible
**Solution**:
- Verify tunnel route is configured in Cloudflare dashboard
- Check that Caddy is running: `docker ps | grep caddy`
- Verify DNS is pointing to Cloudflare (should be automatic with tunnel)

### Infisical Login Still Fails

**Issue**: Login redirects fail
**Solution**:
- Make sure `INFISICAL_SITE_URL` matches the domain you're accessing
- Clear browser cache/cookies
- Check Infisical logs: `docker logs infisical-backend --tail 50`

## Current Configuration

- **Domain**: `datacrew.space`
- **Tunnel ID**: `3885d13d-2d48-47ee-811c-878920be4d69`
- **Zone ID**: `77d3277e791671bfe46f0bac478a6f5b`
- **Infisical Hostname**: `infisical.datacrew.space`
- **Service Target**: `http://caddy:80` (Caddy reverse proxy)

## Next Steps After Setup

1. ✅ Cloudflare tunnel configured
2. ✅ Infisical accessible via domain
3. ⏭️ Login to Infisical CLI: `infisical login --host=https://infisical.datacrew.space`
4. ⏭️ Initialize project: `infisical init`
5. ⏭️ Add secrets from `.env` file

