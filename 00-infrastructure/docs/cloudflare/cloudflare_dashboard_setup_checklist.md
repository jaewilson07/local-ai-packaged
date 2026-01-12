# Cloudflare Access Dashboard Setup Checklist

**Use this checklist to track your progress through the manual dashboard configuration steps.**

## Prerequisites

- [ ] Cloudflare account with Zero Trust enabled
- [ ] Domain `datacrew.space` in Cloudflare
- [ ] Cloudflare Tunnel running and configured
- [ ] Google Cloud Platform account

## Phase 1: Google OAuth Setup

### Google Cloud Console
- [ ] Navigate to [Google Cloud Console](https://console.cloud.google.com/)
- [ ] Select or create a project
- [ ] Go to **APIs & Services** → **Credentials**
- [ ] Configure OAuth consent screen (if first time)
  - [ ] User Type: External (or Internal)
  - [ ] App name: `ComfyUI Access`
  - [ ] Support email: Your email
  - [ ] Developer contact: Your email
- [ ] Create OAuth Client ID
  - [ ] Application type: **Web application**
  - [ ] Name: `ComfyUI Cloudflare Access`
  - [ ] Authorized redirect URI: `https://comfyui.datacrew.space/cdn-cgi/access/callback`
  - [ ] Click **Create**
- [ ] **SAVE CREDENTIALS:**
  - [ ] Copy Client ID: `___________________________`
  - [ ] Copy Client Secret: `___________________________`
  - [ ] Store securely (you'll need these next)

## Phase 2: Cloudflare Access Application

### Zero Trust Dashboard
- [ ] Go to [Cloudflare Zero Trust Dashboard](https://one.dash.cloudflare.com/)
- [ ] Enable Zero Trust (if not already)
  - [ ] Click **Get Started**
  - [ ] Select **Free** plan
  - [ ] Complete setup wizard

### Add Google Identity Provider
- [ ] Go to **Access** → **Authentication** → **Login methods**
- [ ] Click **Add new**
- [ ] Select **Google**
- [ ] Enter Client ID: `___________________________`
- [ ] Enter Client Secret: `___________________________`
- [ ] Click **Save**
- [ ] Note provider name: `___________________________`

### Create Access Application
- [ ] Go to **Access** → **Applications**
- [ ] Click **Add an application**
- [ ] Select **Self-hosted**
- [ ] Configure:
  - [ ] Application name: `ComfyUI`
  - [ ] Session Duration: `24 hours` (or your preference)
  - [ ] Application Domain:
    - [ ] Subdomain: `comfyui`
    - [ ] Domain: `datacrew.space`
    - [ ] Full: `comfyui.datacrew.space`
- [ ] Click **Next**

### Configure Access Policy
- [ ] Policy Name: `ComfyUI Access Policy`
- [ ] Action: `Allow`
- [ ] Include Rules:
  - [ ] Add rule: `Emails ending in` → `@yourdomain.com`
  - [ ] OR specific emails: `your-email@example.com`
- [ ] Identity Providers:
  - [ ] Enable **Google** (the provider you created)
- [ ] Click **Next**
- [ ] Review and click **Add application**

### Link to Tunnel Route
- [ ] Go to **Networks** → **Tunnels**
- [ ] Find your tunnel (e.g., `datacrew-services`)
- [ ] Click **Configure** → **Public Hostnames**
- [ ] Find route for `comfyui.datacrew.space`
  - [ ] If missing, create it:
    - [ ] Subdomain: `comfyui`
    - [ ] Domain: `datacrew.space`
    - [ ] Service: `http://caddy:80`
    - [ ] Host Header: `comfyui.datacrew.space`
- [ ] Click **Edit** on the route
- [ ] Under **Access**, select **ComfyUI** application
- [ ] Click **Save**

## Phase 3: Service Token Setup

### Create Service Token
- [ ] Go to **Access** → **Service Tokens**
- [ ] Click **Create Service Token**
- [ ] Token name: `comfyui-api`
- [ ] Click **Create**
- [ ] **IMMEDIATELY COPY TOKEN:**
  - [ ] Client ID: `___________________________`
  - [ ] Client Secret: `___________________________` ⚠️ **SHOWN ONLY ONCE**
  - [ ] Store securely!

### Add Token to Access Policy
- [ ] Go to **Access** → **Applications** → **ComfyUI**
- [ ] Click on **ComfyUI Access Policy**
- [ ] Click **Edit**
- [ ] Under **Include Rules**, click **Add a rule**
- [ ] Select **Service Token**
- [ ] Select `comfyui-api`
- [ ] Click **Save**
- [ ] Save the policy

### Store Token Securely
- [ ] Add to `.env` file:
  ```bash
  COMFYUI_ACCESS_TOKEN=your-service-token-here
  ```
- [ ] OR store in Infisical:
  ```bash
  infisical secrets set COMFYUI_ACCESS_TOKEN=your-service-token-here
  ```

## Phase 4: Testing

### Browser Access Test
- [ ] Open incognito/private browser
- [ ] Visit `https://comfyui.datacrew.space`
- [ ] **Expected**: Cloudflare Access login page
- [ ] Click **Continue with Google**
- [ ] Complete OAuth flow
- [ ] **Expected**: Redirected to ComfyUI
- [ ] Verify ComfyUI loads correctly

### API Access Test
- [ ] Set token: `export COMFYUI_ACCESS_TOKEN=your-token`
- [ ] Run test script:
  ```bash
  python3 utils/test_comfyui_access.py
  ```
- [ ] **Expected**: Remote access test passes
- [ ] Test API call:
  ```bash
  curl -H "CF-Access-Token: $COMFYUI_ACCESS_TOKEN" \
       https://comfyui.datacrew.space/ai-dock/api/queue-info
  ```
- [ ] **Expected**: Returns queue info (not 403)

### Local Access Test
- [ ] Run local test:
  ```bash
  python3 02-compute/data/comfyui/sample_api_call.py
  ```
- [ ] **Expected**: Works without changes
- [ ] Verify no authentication errors

### Access Control Test
- [ ] Test with unauthorized email (if possible)
- [ ] **Expected**: Access denied
- [ ] Test with authorized email
- [ ] **Expected**: Access granted

## Verification

Run verification script:
```bash
python3 utils/verify_cloudflare_access.py
```

**Expected Results:**
- ✅ Tunnel route configured
- ✅ Service token set
- ✅ Remote access works with token
- ✅ Local access works unchanged

## Troubleshooting

### Access Denied in Browser
- [ ] Check email is in Access policy
- [ ] Verify Google OAuth provider is enabled
- [ ] Check Cloudflare Access logs
- [ ] Verify redirect URI matches exactly

### API Returns 403
- [ ] Verify service token is correct
- [ ] Check token is in Access policy
- [ ] Verify `CF-Access-Token` header is included
- [ ] Check token hasn't been revoked

### Local Scripts Fail
- [ ] Verify script uses `localhost:8188` (not domain)
- [ ] Check ComfyUI container is running
- [ ] This shouldn't happen - local access is unaffected

## Completion

Once all items are checked:
- [ ] All tests pass
- [ ] Browser access requires OAuth
- [ ] API access works with service token
- [ ] Local scripts work unchanged
- [ ] Documentation reviewed

**Congratulations! Cloudflare Access is fully configured.**

## Next Steps

1. Monitor Access logs for 24-48 hours
2. Add additional users as needed
3. Create additional service tokens for different integrations
4. Consider extending Access to other services
