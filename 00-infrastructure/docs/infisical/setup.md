# Infisical Setup Guide

Complete guide for setting up Infisical secret management in the local-ai-packaged project.

## Table of Contents

1. [Prerequisites](#prerequisites)
2. [Initial Setup](#initial-setup)
3. [Cloudflare Tunnel Configuration](#cloudflare-tunnel-configuration-optional)
4. [Google OAuth/SSO Setup](#google-oauthsso-setup-optional)
5. [CLI Setup & Authentication](#cli-setup--authentication)
6. [Verification](#verification)

---

## Prerequisites

1. **Infisical CLI installed** on your host machine
   - Installation: https://infisical.com/docs/cli/overview
   - Or use: `python setup/install_clis.py`
   - Verify: `infisical --version`

2. **Docker and Docker Compose** (already required for this project)

3. **Generated encryption keys** for Infisical (see Initial Setup)

4. **Cloudflare account** (optional, for production domain access)

5. **Google Cloud Platform account** (optional, for OAuth/SSO)

---

## Initial Setup

### Step 1: Generate Infisical Encryption Keys

Infisical requires two encryption keys. Generate them automatically or manually.

#### Option A: Automatic Generation (Recommended)

```bash
python 00-infrastructure/scripts/generate-env-passwords.py
```

This script will:
- Generate `INFISICAL_ENCRYPTION_KEY` (16-byte hex string)
- Generate `INFISICAL_AUTH_SECRET` (32-byte base64 string)
- Automatically add them to your `.env` file if they're missing
- Create a backup of your existing `.env` file

#### Option B: Manual Generation

**Linux/Mac:**
```bash
# Generate ENCRYPTION_KEY (16-byte hex string)
openssl rand -hex 16

# Generate AUTH_SECRET (32-byte base64 string)
openssl rand -base64 32
```

**Windows PowerShell:**
```powershell
# ENCRYPTION_KEY
-join ((1..16) | ForEach-Object { '{0:X2}' -f (Get-Random -Maximum 256) })

# AUTH_SECRET (base64)
[Convert]::ToBase64String((1..32 | ForEach-Object { Get-Random -Maximum 256 }))
```

Add these to your `.env` file:
```bash
INFISICAL_ENCRYPTION_KEY=<your-encryption-key>
INFISICAL_AUTH_SECRET=<your-auth-secret>
```

### Step 2: Configure Infisical Hostname

Add to your `.env` file:

**Option A: Localhost Only (Private Environment Default)**
```bash
# These are the defaults for private environment - no need to set if only using localhost
INFISICAL_HOSTNAME=:8020
INFISICAL_SITE_URL=http://localhost:8020
INFISICAL_HTTPS_ENABLED=false
```

**Option B: Cloudflare Only (Public Environment)**
```bash
INFISICAL_HOSTNAME=infisical.datacrew.space
INFISICAL_SITE_URL=https://infisical.datacrew.space
INFISICAL_HTTPS_ENABLED=true
```

**Option C: Both Localhost AND Cloudflare (Recommended for Private Environment)**
```bash
# Set Cloudflare domain for SITE_URL (enables Cloudflare access)
INFISICAL_HOSTNAME=infisical.datacrew.space
INFISICAL_SITE_URL=https://infisical.datacrew.space
INFISICAL_HTTPS_ENABLED=true

# Port 8020 is still exposed for localhost access via docker-compose.override.private.yml
# You can access via BOTH:
# - http://localhost:8020 (direct port mapping) - NOTE: Login may have cookie issues, use Cloudflare for login
# - https://infisical.datacrew.space (via Cloudflare Tunnel → Caddy) - Full functionality including login
```

**Important:** 
- The `SITE_URL` environment variable must match your Infisical URL exactly (including protocol) for OAuth redirects and cookies to work correctly.
- **For dual access (localhost + Cloudflare):** 
  - Set `INFISICAL_SITE_URL=https://infisical.datacrew.space` and `INFISICAL_HTTPS_ENABLED=true` in `.env`
  - **Use Cloudflare domain (`https://infisical.datacrew.space`) for login** - cookies/sessions work correctly
  - Localhost (`http://localhost:8020`) can be used for viewing/management, but login may fail due to cookie domain mismatch
  - Port mapping allows localhost access, but cookies are set for Cloudflare domain
- **For localhost only:** Leave defaults or set `INFISICAL_SITE_URL=http://localhost:8020` and `INFISICAL_HTTPS_ENABLED=false` in `.env`
- **CRITICAL:** When `SITE_URL` is set to Cloudflare domain, cookies are scoped to that domain. Accessing via `http://localhost:8020` will have cookie issues. Use `https://infisical.datacrew.space` for login.
- When using `docker-compose.override.private.yml` (private environment), the override file provides defaults for localhost if `INFISICAL_SITE_URL` is not explicitly set.
- For localhost access, Infisical will be available at `http://localhost:8020` via direct port mapping (bypassing Caddy).
- **Use `http://` NOT `https://` for localhost** - there's no SSL certificate for localhost.

### Step 3: Configure HTTPS Setting

**For localhost access:**
- Set `INFISICAL_HTTPS_ENABLED=false` in `.env` (or let the override file handle it)
- Access via `http://localhost:8020`
- The `docker-compose.override.private.yml` file automatically sets this for private environments

**For production behind Cloudflare Tunnel:**
- Set `INFISICAL_HTTPS_ENABLED=true` in `.env`
- Access via `https://infisical.datacrew.space`
- Secure cookies require HTTPS

**Critical:** Secure cookies require HTTPS. If `HTTPS_ENABLED=true` but you're accessing via HTTP, the browser will reject session cookies and you'll be immediately logged out.

### Step 4: Start Infisical Services

```bash
python start_services.py --profile cpu
```

Infisical will start automatically and wait for postgres/redis to be ready.

Verify services are running:
```bash
docker ps | grep infisical
```

Should show: `infisical-backend`, `infisical-db`, `infisical-redis`

### Step 5: Access Infisical UI and Create Admin Account

**Access Methods:**

1. **Localhost Access (Private Environment):**
   - Start services: `python start_services.py --environment private`
   - Access at: `http://localhost:8020/admin/signup`
   - Infisical is accessible directly via port mapping (bypasses Caddy)
   - **Default configuration:** Works automatically with no .env changes needed

2. **Cloudflare Access (Public Environment):**
   - Start services: `python start_services.py --environment public`
   - Access at: `https://infisical.datacrew.space/admin/signup`
   - Infisical is accessible via Cloudflare Tunnel → Caddy → Infisical backend
   - **Requires:** Cloudflare tunnel configured and `INFISICAL_SITE_URL=https://infisical.datacrew.space` in `.env`

3. **Dual Access (Both Localhost AND Cloudflare - Private Environment):**
   - Start services: `python start_services.py --environment private`
   - Set in `.env`:
     ```bash
     INFISICAL_SITE_URL=https://infisical.datacrew.space
     INFISICAL_HTTPS_ENABLED=true
     ```
   - Access via **BOTH**:
     - `http://localhost:8020` (direct port mapping) - **Use for viewing/managing, but login via Cloudflare**
     - `https://infisical.datacrew.space` (via Cloudflare Tunnel) - **Use for login and full functionality**
   - **Important:** 
     - **Use `http://localhost:8020` NOT `https://localhost:8020`** - there's no SSL for localhost
     - **Login via Cloudflare domain** (`https://infisical.datacrew.space`) - cookies work correctly
     - Localhost access works for viewing/managing secrets, but login may fail due to cookie domain mismatch
     - Cookies are set for `infisical.datacrew.space` domain, so browser won't send them to `localhost:8020`

**After Access:**

1. Create your admin account (first user becomes admin)
2. After signup, you'll be logged into the Infisical dashboard

**Configuration Notes:**

- **For localhost only:** Use defaults or set `INFISICAL_SITE_URL=http://localhost:8020` and `INFISICAL_HTTPS_ENABLED=false`
- **For Cloudflare only:** Set `INFISICAL_SITE_URL=https://infisical.datacrew.space` and `INFISICAL_HTTPS_ENABLED=true`
- **For both:** Set Cloudflare values in `.env` - localhost port will still be exposed in private environment
- If you see an error about email service not configured, see the troubleshooting guide

### Step 6: Create Organization and Project

1. In the Infisical UI, create a new **Organization** (if needed)
   - Name it (e.g., "DataCrew" or "Personal")
   - Click **"Create"**

2. Create a new **Project**
   - Project Name: `local-ai-packaged`
   - Description: (optional) "Local AI Packaged Services"
   - Click **"Create Project"**

3. Select or create environments:
   - `development` (for local development)
   - `production` (for production deployments)

---

## Cloudflare Tunnel Configuration (Optional)

Infisical CLI login requires a proper domain (not localhost) for OAuth redirects. This guide helps you set up Cloudflare tunnel to expose Infisical via `infisical.datacrew.space`.

### Step 1: Get Cloudflare Tunnel Token

**Option A: Via Cloudflare Dashboard (Recommended)**

1. Go to https://one.dash.cloudflare.com/
2. Navigate to **Networks** → **Tunnels**
3. Find your tunnel (or create a new one)
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
python3 00-infrastructure/docs/cloudflare/configure_hostnames.py
```

This will configure all services including `infisical.datacrew.space`.

### Step 3: Update Infisical SITE_URL

Once the tunnel is working, update Infisical to use the domain:

1. Edit `.env` file and change:
   ```bash
   # Change from:
   INFISICAL_SITE_URL=http://localhost:8020
   
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

---

## Google OAuth/SSO Setup (Optional)

Infisical supports Google Single Sign-On (SSO) for authentication. To enable it:

### Step 1: Create OAuth2 Application in Google Cloud Platform

1. **Go to Google Cloud Console:**
   - Navigate to [Google Cloud Console](https://console.cloud.google.com/)
   - Select or create a project

2. **Enable OAuth Consent Screen (if not already done):**
   - Go to **APIs & Services** → **OAuth consent screen**
   - Choose **External** (for personal Google accounts) or **Internal** (for Google Workspace)
   - Fill in required fields:
     - **App name**: `Infisical` (or your preferred name)
     - **User support email**: Your email
     - **Developer contact information**: Your email
   - Click **Save and Continue**
   - Add scopes: `openid`, `email`, `profile` (usually added by default)
   - Click **Save and Continue**

3. **Create OAuth Client ID:**
   - Go to **APIs & Services** → **Credentials**
   - Click **Create Credentials** → **OAuth client ID**
   - Choose **Web application**
   - **Name**: `Infisical SSO` (or your preferred name)
   - **Authorized redirect URIs**: Add this exact URI:
     - For local: `http://localhost:8020/api/v1/auth/oauth2/google/callback`
     - For production: `https://infisical.datacrew.space/api/v1/auth/oauth2/google/callback`
   - Click **Create**

4. **Copy Credentials:**
   - Copy the **Client ID** (looks like: `123456789-abcdefg.apps.googleusercontent.com`)
   - Copy the **Client Secret** (looks like: `GOCSPX-abcdefghijklmnopqrstuvwxyz`)
   - **Save these securely** - you'll need them in the next step

### Step 2: Configure Environment Variables

Add the Google OAuth credentials to your `.env` file:

```bash
# Google OAuth/SSO for Infisical
GOOGLE_CLIENT_ID=your-google-client-id-here
GOOGLE_CLIENT_SECRET=your-google-client-secret-here
```

**Important:** Make sure `INFISICAL_SITE_URL` matches your Infisical URL:
- For local: `INFISICAL_SITE_URL=http://localhost:8020`
- For production: `INFISICAL_SITE_URL=https://infisical.datacrew.space`

### Step 3: Restart Infisical

Restart the Infisical backend to load the new environment variables:

```bash
cd 00-infrastructure
docker compose restart infisical-backend
```

Wait for the container to be healthy:
```bash
docker ps | grep infisical-backend
# Should show "healthy" status
```

### Step 4: Enable Google SSO in Infisical UI

1. **Access Infisical:**
   - Open your Infisical UI (e.g., `http://localhost:8020` or `https://infisical.datacrew.space`)
   - Log in as an admin user

2. **Navigate to SSO Settings:**
   - Go to **Settings** → **SSO** (or **Organization Settings** → **SSO**)
   - Look for **Google SSO** or **OAuth Providers**

3. **Enable Google SSO:**
   - Toggle **Google SSO** to enabled
   - The system should automatically detect the `GOOGLE_CLIENT_ID` and `GOOGLE_CLIENT_SECRET` from environment variables
   - If prompted, verify the redirect URI matches what you configured in Google Cloud Console

4. **Test the Integration:**
   - Log out of Infisical
   - On the login page, you should see a **"Sign in with Google"** button
   - Click it and complete the OAuth flow
   - You should be redirected back to Infisical and logged in

---

## CLI Setup & Authentication

### Step 1: Install Infisical CLI

If not already installed:
```bash
python setup/install_clis.py
```

Or install manually: https://infisical.com/docs/cli/overview

Verify installation:
```bash
infisical --version
```

### Step 2: Login to Infisical CLI

**For production (with domain):**
```bash
infisical login --host=https://infisical.datacrew.space
```

**For local development:**
```bash
infisical login --host=http://localhost:8020
```

This will:
1. Open browser for authentication
2. Ask you to authorize the CLI
3. Store authentication token locally

### Step 3: Initialize Project in Repository

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

### Step 4: Create Machine Identity (Optional, for Automation)

For automated secret fetching (used by `start_services.py`):

1. In Infisical UI, go to **Settings** → **Machine Identities**
2. Click **"Create Machine Identity"**
3. Give it a name (e.g., "local-ai-package-cli")
4. Select your project and environment
5. Set appropriate permissions (read access to secrets)
6. Copy the **Client ID** and **Client Secret**

7. **Set environment variables** (not in .env, use your shell):
   ```bash
   export INFISICAL_MACHINE_CLIENT_ID=<client-id>
   export INFISICAL_MACHINE_CLIENT_SECRET=<client-secret>
   ```

8. **Authenticate using machine identity:**
   ```bash
   infisical login --method=universal-auth \
     --client-id=$INFISICAL_MACHINE_CLIENT_ID \
     --client-secret=$INFISICAL_MACHINE_CLIENT_SECRET
   ```

---

## Verification

### Check Project Initialization

```bash
# Check if project is initialized
cat .infisical.json

# Test secret export
infisical export --format=dotenv | head -5

# List secrets (should be empty initially)
infisical secrets
```

### Verify Services

```bash
# Check all Infisical containers
docker ps | grep infisical

# Check container health status
docker inspect infisical-backend --format='{{.State.Health.Status}}'

# Check container logs
docker logs infisical-backend --tail 50
```

### Test Secret Export

```bash
# Export secrets to test file
infisical export --format=dotenv > .env.infisical.test

# Check if secrets are exported
cat .env.infisical.test | head -10

# Clean up test file
rm .env.infisical.test
```

---

## Next Steps

After setup:
1. ✅ Infisical services running
2. ✅ Admin account created
3. ✅ Organization and project created
4. ✅ CLI authenticated and initialized
5. ⏭️ Add secrets from `.env` file (see [usage.md](./usage.md))
6. ⏭️ Test with `start_services.py --use-infisical`

## Related Documentation

- [Usage Guide](./usage.md) - Day-to-day operations and secret management
- [Design Documentation](./design.md) - Architecture and design decisions
- [Troubleshooting Guide](./troubleshooting_configuration.md) - Comprehensive troubleshooting
- [Infisical Official Documentation](https://infisical.com/docs)
