# Infisical Project Setup: local-ai-packaged

## Quick Start

### Step 1: Fix Database Connection (if needed)

The password contains special characters. I've added `INFISICAL_POSTGRES_PASSWORD_URL_ENCODED` to your `.env` file. The container should restart and connect properly.

**Check if Infisical is running:**
```bash
docker logs infisical-backend --tail 20
```

Look for "Server started" or "listening" messages.

### Step 2: Access Infisical UI

**Option A: Check if accessible via Caddy**
```bash
# Check INFISICAL_HOSTNAME in .env
grep INFISICAL_HOSTNAME .env
# Access via that hostname
```

**Option B: Direct container access**
```bash
# Get container IP
docker inspect infisical-backend --format='{{range .NetworkSettings.Networks}}{{.IPAddress}}{{end}}'

# Or check if port is exposed
docker port infisical-backend
```

**Option C: Temporary port forward**
```bash
# If needed, you can temporarily expose the port
docker run -d --name infisical-proxy --network ai-network -p 8010:8080 nginx:alpine \
  sh -c 'echo "server { listen 80; location / { proxy_pass http://infisical-backend:8080; } }" > /etc/nginx/conf.d/default.conf && nginx -g "daemon off;"'
```

### Step 3: Create Admin Account

1. Open Infisical UI in browser (from Step 2)
2. Navigate to `/admin/signup`
3. Create your admin account (first user becomes admin)

### Step 4: Create Organization

1. In Infisical UI, click **"Create Organization"**
2. Name it (e.g., "DataCrew" or "Personal")
3. Click **"Create"**

### Step 5: Create Project "local-ai-packaged"

1. In your organization, click **"Create Project"**
2. **Project Name:** `local-ai-packaged`
3. **Description:** (optional) "Local AI Packaged Services"
4. Click **"Create Project"**

### Step 6: Create Environments

After creating the project, environments may be created automatically, or you can add them:

1. **Development Environment:**
   - Name: `development`
   - Description: "Local development environment"

2. **Production Environment:**
   - Name: `production`
   - Description: "Production environment"

### Step 7: Authenticate CLI

```bash
# Login to Infisical CLI
infisical login

# If browser doesn't open, specify host:
infisical login --host=http://localhost:8010
```

This will:
1. Open browser for authentication
2. Ask you to authorize the CLI
3. Store authentication token locally

### Step 8: Initialize Project in Repository

```bash
cd /home/jaewilson07/GitHub/local-ai-packaged

# Initialize Infisical in this directory
infisical init

# This will prompt you to:
# 1. Select organization
# 2. Select project (choose "local-ai-packaged")
# 3. Select environment (choose "development")
# 4. Create .infisical.json config file
```

### Step 9: Verify Setup

```bash
# Check if project is initialized
cat .infisical.json

# Test secret export
infisical export --format=dotenv | head -5

# List secrets (should be empty initially)
infisical secrets
```

### Step 10: Add Secrets

**Option A: Via UI (Recommended for first-time)**
1. Go to Infisical UI
2. Select project: `local-ai-packaged`
3. Select environment: `development`
4. Click "Add Secret"
5. Add secrets from your `.env` file:
   - `POSTGRES_PASSWORD`
   - `CLOUDFLARE_API_TOKEN`
   - `CLOUDFLARE_TUNNEL_TOKEN`
   - `INFISICAL_POSTGRES_PASSWORD`
   - `INFISICAL_ENCRYPTION_KEY`
   - `INFISICAL_AUTH_SECRET`
   - And other sensitive secrets

**Option B: Via CLI**
```bash
# Add secrets one by one
infisical secrets set POSTGRES_PASSWORD "your-password"
infisical secrets set CLOUDFLARE_API_TOKEN "your-token"
infisical secrets set CLOUDFLARE_TUNNEL_TOKEN "your-tunnel-token"
```

## Troubleshooting

### Infisical Backend Not Starting

**Check logs:**
```bash
docker logs infisical-backend --tail 50
```

**Common issues:**
- Database connection errors → Password may need URL encoding (already fixed)
- Health check failing → Wait a bit longer, health check has 30s start period

### Infisical UI Not Accessible

**Check if backend is healthy:**
```bash
docker ps | grep infisical-backend
# Should show "healthy" status
```

**Check container health:**
```bash
docker inspect infisical-backend --format='{{.State.Health.Status}}'
```

**Access directly:**
```bash
# Test health endpoint
docker exec infisical-backend wget -qO- http://localhost:8080/api/health
```

### CLI Authentication Issues

**Re-authenticate:**
```bash
infisical logout
infisical login
```

**Check authentication:**
```bash
infisical secrets  # Should show secrets or empty list (not error)
```

## Optional: Enable Google OAuth/SSO

Infisical supports Google Single Sign-On for easier authentication:

1. **Create Google OAuth2 Application:**
   - Go to [Google Cloud Console](https://console.cloud.google.com/)
   - Navigate to **APIs & Services** → **Credentials**
   - Create **OAuth client ID** (Web application)
   - Add redirect URI: `http://localhost:8010/api/v1/auth/oauth2/google/callback` (or your production URL)
   - Copy Client ID and Client Secret

2. **Add to `.env` file:**
   ```bash
   GOOGLE_CLIENT_ID=your-client-id
   GOOGLE_CLIENT_SECRET=your-client-secret
   ```

3. **Restart Infisical:**
   ```bash
   cd 00-infrastructure
   docker compose restart infisical-backend
   ```

4. **Enable in UI:**
   - Go to **Settings** → **SSO** in Infisical
   - Enable Google SSO
   - Users can now sign in with Google accounts

## Next Steps

After setup:
1. ✅ Project created: `local-ai-packaged`
2. ✅ Environments created: `development`, `production`
3. ✅ CLI authenticated and initialized
4. ⏭️ Add secrets from `.env` file
5. ⏭️ Test with `start_services.py --use-infisical`
6. ⏭️ (Optional) Enable Google OAuth/SSO for easier login

## Quick Reference

```bash
# Login
infisical login

# Initialize project
infisical init

# Add secret
infisical secrets set KEY "value"

# List secrets
infisical secrets

# Export secrets
infisical export --format=dotenv

# Use with start_services.py
python start_services.py --use-infisical
```
