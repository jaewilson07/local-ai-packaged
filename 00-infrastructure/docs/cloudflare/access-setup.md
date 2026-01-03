# Cloudflare Access Setup for Service Authentication

This guide explains how to use Cloudflare Access (Zero Trust) to add authentication to your services, including ComfyUI.

## Overview

**Cloudflare Access** provides authentication and authorization without requiring a separate Docker container. It integrates directly with your existing Cloudflare Tunnel setup.

### Benefits

- ✅ **No additional containers** - Authentication handled by Cloudflare
- ✅ **Multiple auth methods** - Email OTP, OAuth (Google, GitHub, etc.), Service Tokens
- ✅ **Centralized management** - Manage access policies in Cloudflare dashboard
- ✅ **Free tier available** - Up to 50 users free
- ✅ **Works with existing tunnel** - No changes to your current setup

## Architecture

```
Internet
   │
   ▼
Cloudflare Network (SSL/TLS + Access Authentication)
   │
   ▼
Cloudflare Tunnel (encrypted connection)
   │
   ▼
Caddy (reverse proxy)
   │
   ▼
ComfyUI (protected service)
```

## Setup Steps

### Step 1: Enable Cloudflare Zero Trust

1. Go to [Cloudflare Zero Trust Dashboard](https://one.dash.cloudflare.com/)
2. If you haven't set up Zero Trust yet:
   - Click **Get Started**
   - Select **Free** plan (50 users)
   - Complete the setup wizard

### Step 2: Create an Access Application

1. In Zero Trust dashboard, go to **Access** → **Applications**
2. Click **Add an application**
3. Select **Self-hosted**
4. Configure the application:
   - **Application name**: `ComfyUI`
   - **Session Duration**: Choose (e.g., 24 hours)
   - **Application Domain**: 
     - **Subdomain**: `comfyui`
     - **Domain**: `datacrew.space`
     - Full domain: `comfyui.datacrew.space`
5. Click **Next**

### Step 3: Configure Access Policy

1. **Policy Name**: `ComfyUI Access Policy`
2. **Action**: `Allow`
3. **Include Rules**: Choose who can access:
   
   **Option A: Email-based (Simple)**
   - Rule: `Emails` → `your-email@example.com`
   - Or: `Emails ending in` → `@yourdomain.com`
   
   **Option B: OAuth (Google/GitHub)**
   - Rule: `Emails` → `your-email@gmail.com`
   - Or add OAuth provider (see Step 4)
   
   **Option C: Service Token (API Access)**
   - Create a service token for programmatic access
   - Useful for API calls without browser

4. Click **Next**

### Step 4: Configure Identity Providers (Optional)

For OAuth login (Google, GitHub, etc.):

1. Go to **Access** → **Authentication** → **Login methods**
2. Click **Add new**
3. Choose provider (e.g., **Google**)
4. Follow OAuth setup instructions
5. Add the provider to your Access policy

### Step 5: Link Application to Tunnel

1. Go to **Networks** → **Tunnels** → Your tunnel
2. Click **Configure** → **Public Hostnames**
3. Find or create the route for `comfyui.datacrew.space`
4. Click **Edit** on the route
5. Under **Access**, select your **ComfyUI** application
6. Click **Save**

### Step 6: Test Access

1. Visit `https://comfyui.datacrew.space`
2. You should see Cloudflare Access login page
3. Authenticate using your configured method
4. After authentication, you'll be redirected to ComfyUI

## Access Methods

### Email One-Time Password (OTP)

**Best for**: Quick setup, personal use

1. In Access policy, add rule: `Emails` → `your-email@example.com`
2. When accessing, Cloudflare sends OTP to your email
3. Enter OTP to access

### OAuth Providers

**Best for**: Team access, SSO

Supported providers:
- Google
- GitHub
- Microsoft/Azure AD
- Okta
- Generic OAuth2

Setup:
1. Configure OAuth app in provider (Google Cloud, GitHub, etc.)
2. Add provider in Cloudflare Zero Trust
3. Add to Access policy

### Service Tokens

**Best for**: API access, automation

1. Go to **Access** → **Service Tokens**
2. Click **Create Service Token**
3. Name it (e.g., `comfyui-api`)
4. Copy the token (save securely!)
5. Use in API calls:
   ```bash
   curl -H "CF-Access-Token: your-service-token" \
     https://comfyui.datacrew.space/api/...
   ```

## Multiple Services

You can protect multiple services with different policies:

1. **ComfyUI** - Require authentication
2. **N8N** - Require authentication  
3. **Open WebUI** - Require authentication
4. **Public services** - No authentication (e.g., SearXNG)

Each service gets its own Access application and policy.

## Advanced Configuration

### Bypass for Specific IPs

In Access policy, add **Exclude** rule:
- Rule: `IP Address` → `your-office-ip/32`
- This allows access without authentication from that IP

### Time-based Access

Add **Include** rule with time restriction:
- Rule: `Emails` → `user@example.com`
- **Require**: `Valid Certificate` (for time-based access, use custom rules)

### Group-based Access

1. Create groups in **Access** → **Groups**
2. Add users to groups
3. In policy, use `Group` rule instead of `Email`

## Troubleshooting

### Access Page Not Showing

**Issue**: Direct access to service, no authentication prompt

**Solutions**:
1. Verify Access application is linked to tunnel route
2. Check that route has Access enabled in tunnel config
3. Clear browser cache and cookies
4. Check Cloudflare Zero Trust logs

### Authentication Fails

**Issue**: Can't authenticate after entering credentials

**Solutions**:
1. Verify email/identity provider is in Access policy
2. Check Zero Trust logs: **Access** → **Logs**
3. Verify session duration settings
4. Try different browser/incognito mode

### Service Token Not Working

**Issue**: API calls with service token return 403

**Solutions**:
1. Verify token is correct (no extra spaces)
2. Check token is added to Access policy
3. Verify header format: `CF-Access-Token: token`
4. Check token hasn't expired

## Comparison: Cloudflare Access vs Docker Auth Container

| Feature | Cloudflare Access | Docker Container (Authelia/Authentik) |
|---------|-------------------|----------------------------------------|
| **Setup Complexity** | Low (dashboard) | Medium (container + config) |
| **Maintenance** | Low (managed) | Medium (updates, config) |
| **Cost** | Free (50 users) | Free (self-hosted) |
| **Auth Methods** | OTP, OAuth, SAML | OTP, OAuth, LDAP, more |
| **User Management** | Cloudflare dashboard | Self-hosted |
| **Integration** | Works with tunnel | Requires forward_auth in Caddy |
| **Best For** | Simple, cloud-managed | Complex, self-hosted, many users |

## Recommendation

**Use Cloudflare Access if**:
- ✅ You want simple setup
- ✅ You have < 50 users (free tier)
- ✅ You're already using Cloudflare Tunnel
- ✅ You want cloud-managed authentication

**Use Docker Auth Container if**:
- ✅ You need > 50 users
- ✅ You want full self-hosting
- ✅ You need LDAP/Active Directory
- ✅ You want more control over auth flow

## Next Steps

1. ✅ Set up Cloudflare Zero Trust
2. ✅ Create Access application for ComfyUI
3. ✅ Configure access policy
4. ✅ Link to tunnel route
5. ✅ Test authentication
6. ⏭️ Add more services as needed

## ComfyUI-Specific Configuration

### API Access with Service Tokens

For programmatic access to ComfyUI API, use service tokens:

1. **Create Service Token** (see Step 3.1 above)
2. **Store Token Securely:**
   ```bash
   # In .env file
   COMFYUI_ACCESS_TOKEN=your-service-token-here
   ```
3. **Use Helper Function:**
   ```python
   from utils.comfyui_api_client import get_comfyui_client
   
   # Automatically handles token for remote URLs
   session = get_comfyui_client("https://comfyui.datacrew.space")
   response = session.post("https://comfyui.datacrew.space/ai-dock/api/payload", json=payload)
   ```

### Local vs Remote Access

**Local Access (No Token Needed):**
- Scripts using `http://localhost:8188` work unchanged
- Services using `http://comfyui:8188` (Docker network) work unchanged
- No authentication required

**Remote Access (Token Required):**
- Scripts using `https://comfyui.datacrew.space` need `CF-Access-Token` header
- Use `utils/comfyui_api_client.py` helper function
- Set `COMFYUI_ACCESS_TOKEN` environment variable

See `comfyui-api-audit.md` for detailed access pattern analysis.

## References

- [Cloudflare Access Documentation](https://developers.cloudflare.com/cloudflare-one/policies/access/)
- [Zero Trust Dashboard](https://one.dash.cloudflare.com/)
- [Access Policies Guide](https://developers.cloudflare.com/cloudflare-one/policies/access/policies/)
- [ComfyUI API Access Audit](../cloudflare/comfyui-api-audit.md)

