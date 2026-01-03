# ComfyUI Cloudflare Access Implementation Guide

**Step-by-step guide for implementing Cloudflare Access for ComfyUI**

## Prerequisites Checklist

Before starting, ensure you have:
- [ ] Cloudflare account with Zero Trust enabled
- [ ] Domain `datacrew.space` configured in Cloudflare
- [ ] Cloudflare Tunnel already set up and running
- [ ] Google Cloud Platform account (for OAuth)
- [ ] Access to Cloudflare Zero Trust dashboard

## Quick Start

**Before manual setup, verify your environment:**
```bash
# Test local access (should work)
python3 utils/test_comfyui_access.py

# Verify configuration
python3 utils/verify_cloudflare_access.py
```

**Then follow the phases below for dashboard configuration.**

## Phase 1: Google OAuth Setup

### Step 1.1: Create Google OAuth Application

1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Select or create a project
3. Navigate to **APIs & Services** → **Credentials**
4. Click **Create Credentials** → **OAuth client ID**
5. If prompted, configure OAuth consent screen:
   - User Type: **External** (or Internal if using Google Workspace)
   - App name: `ComfyUI Access`
   - User support email: Your email
   - Developer contact: Your email
   - Click **Save and Continue**
6. Create OAuth Client ID:
   - Application type: **Web application**
   - Name: `ComfyUI Cloudflare Access`
   - **Authorized redirect URIs**: 
     ```
     https://comfyui.datacrew.space/cdn-cgi/access/callback
     ```
   - Click **Create**
7. **Save the credentials:**
   - Copy **Client ID**
   - Copy **Client Secret**
   - Store securely (you'll need these in Step 2.4)

## Phase 2: Cloudflare Access Application Setup

### Step 2.1: Access Zero Trust Dashboard

1. Go to [Cloudflare Zero Trust Dashboard](https://one.dash.cloudflare.com/)
2. If Zero Trust is not set up:
   - Click **Get Started**
   - Select **Free** plan (50 users)
   - Complete setup wizard

### Step 2.2: Configure Google OAuth Provider

1. In Zero Trust dashboard, go to **Access** → **Authentication** → **Login methods**
2. Click **Add new**
3. Select **Google**
4. Enter:
   - **Client ID**: (from Step 1.1)
   - **Client Secret**: (from Step 1.1)
5. Click **Save**
6. Note the provider name (usually "Google")

### Step 2.3: Create Access Application

1. Go to **Access** → **Applications**
2. Click **Add an application**
3. Select **Self-hosted**
4. Configure application:
   - **Application name**: `ComfyUI`
   - **Session Duration**: `24 hours` (or your preference)
   - **Application Domain**:
     - **Subdomain**: `comfyui`
     - **Domain**: `datacrew.space`
     - Full domain: `comfyui.datacrew.space`
5. Click **Next**

### Step 2.4: Configure Access Policy

1. **Policy Name**: `ComfyUI Access Policy`
2. **Action**: `Allow`
3. **Include Rules**:
   - Click **Add a rule**
   - Select **Emails ending in**
   - Enter: `@yourdomain.com` (or specific email addresses)
   - Click **Save**
4. **Identity Providers**:
   - Enable **Google** (the provider you created in Step 2.2)
5. Click **Next**
6. Review and click **Add application**

### Step 2.5: Link Application to Tunnel Route

1. Go to **Networks** → **Tunnels**
2. Find your tunnel (e.g., `datacrew-services`)
3. Click **Configure** → **Public Hostnames** tab
4. Find the route for `comfyui.datacrew.space`
   - If it doesn't exist, create it:
     - Click **Add a public hostname**
     - Subdomain: `comfyui`
     - Domain: `datacrew.space`
     - Service: `http://caddy:80`
     - HTTP Host Header: `comfyui.datacrew.space`
     - Click **Save hostname**
5. Click **Edit** on the `comfyui.datacrew.space` route
6. Scroll to **Access** section
7. Select **ComfyUI** application (created in Step 2.3)
8. Click **Save**

## Phase 3: Service Token Setup (for API Access)

### Step 3.1: Create Service Token

1. In Zero Trust dashboard, go to **Access** → **Service Tokens**
2. Click **Create Service Token**
3. Configure:
   - **Token name**: `comfyui-api`
   - **Client ID**: (auto-generated, note this)
   - **Client Secret**: (shown once, **COPY IMMEDIATELY**)
4. Click **Create**
5. **IMPORTANT**: Save the token securely - you won't be able to see it again!

### Step 3.2: Add Service Token to Access Policy

1. Go to **Access** → **Applications** → **ComfyUI**
2. Click on **ComfyUI Access Policy** (or create new policy)
3. Click **Edit**
4. Under **Include Rules**, click **Add a rule**
5. Select **Service Token**
6. Select `comfyui-api` token
7. Click **Save**
8. Save the policy

### Step 3.3: Store Service Token Securely

**Option A: Environment Variable (.env file)**
```bash
# Add to .env file
COMFYUI_ACCESS_TOKEN=your-service-token-here
```

**Option B: Infisical (Recommended)**
```bash
# Store in Infisical
infisical secrets set COMFYUI_ACCESS_TOKEN=your-service-token-here
```

**Option C: Export for Current Session**
```bash
export COMFYUI_ACCESS_TOKEN=your-service-token-here
```

## Phase 4: Testing

### Step 4.1: Test Browser Access

1. Open browser in incognito/private mode
2. Visit `https://comfyui.datacrew.space`
3. **Expected**: Cloudflare Access login page appears
4. Click **Continue with Google**
5. Complete Google OAuth flow
6. **Expected**: Redirected to ComfyUI interface
7. Verify you can use ComfyUI normally

### Step 4.2: Test API Access with Service Token

```bash
# Set token
export COMFYUI_ACCESS_TOKEN=your-service-token-here

# Test API call
curl -H "CF-Access-Token: $COMFYUI_ACCESS_TOKEN" \
     -H "Content-Type: application/json" \
     https://comfyui.datacrew.space/ai-dock/api/queue-info
```

**Expected**: Returns queue information (not 403 Forbidden)

### Step 4.3: Test Local Access (Should Work Unchanged)

```bash
# Test local script - should work without token
python 02-compute/data/comfyui/sample_api_call.py
```

**Expected**: Works without any changes

### Step 4.4: Test Remote API with Python Helper

```python
from utils.comfyui_api_client import get_comfyui_client

# This should work with COMFYUI_ACCESS_TOKEN set
session = get_comfyui_client("https://comfyui.datacrew.space")
response = session.get("https://comfyui.datacrew.space/ai-dock/api/queue-info")
print(response.status_code)  # Should be 200
```

## Phase 5: Verification

### Checklist

- [ ] Browser access requires Google OAuth login
- [ ] Authorized users can access ComfyUI
- [ ] Unauthorized users are blocked (test with different email)
- [ ] API calls with service token work
- [ ] API calls without service token are blocked (403)
- [ ] Local scripts using `localhost:8188` work unchanged
- [ ] Service-to-service calls using `http://comfyui:8188` work unchanged

### Troubleshooting

**Browser shows "Access Denied":**
- Check Access policy includes your email/domain
- Verify Google OAuth provider is enabled in policy
- Check Cloudflare Access logs in dashboard

**API returns 403 Forbidden:**
- Verify service token is correct
- Check token is added to Access policy
- Ensure `CF-Access-Token` header is included
- Verify token hasn't expired (service tokens don't expire, but check policy)

**Local scripts fail:**
- This shouldn't happen - local access is unaffected
- Check if script is accidentally using remote URL
- Verify ComfyUI container is running

## Next Steps

1. Monitor Access logs for first 24-48 hours
2. Add additional users to Access policy as needed
3. Create additional service tokens for different services/integrations
4. Consider extending Access to other services (N8N, WebUI, etc.)

## Rollback Procedure

If you need to disable Cloudflare Access:

1. Go to **Networks** → **Tunnels** → Your tunnel
2. Click **Configure** → **Public Hostnames**
3. Find `comfyui.datacrew.space` route
4. Click **Edit**
5. Under **Access**, select **None** (or remove the application)
6. Click **Save**

**Result**: ComfyUI returns to previous state (no authentication required)

## Support

- [Cloudflare Access Documentation](https://developers.cloudflare.com/cloudflare-one/policies/access/)
- [Zero Trust Dashboard](https://one.dash.cloudflare.com/)
- [ComfyUI API Access Audit](./comfyui-api-audit.md)

