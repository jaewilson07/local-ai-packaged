# Infisical Troubleshooting Guide

Comprehensive troubleshooting guidance for Infisical connection, authentication, and infrastructure issues.

## Table of Contents

1. [Docker Compose Conflicts](#docker-compose-conflicts)
2. [Connection Issues](#connection-issues)
3. [Authentication Problems](#authentication-problems)
4. [Infrastructure Issues](#infrastructure-issues)
5. [Diagnostic Commands Reference](#diagnostic-commands-reference)
6. [Troubleshooting Decision Tree](#troubleshooting-decision-tree)
7. [Historical Troubleshooting Sessions](#historical-troubleshooting-sessions)

---

## Docker Compose Conflicts

### The Problem

When starting services, you may encounter errors like:
```
services.storage conflicts with imported resource
services.imgproxy conflicts with imported resource
```

### Root Cause

The conflict occurs because of how Docker Compose handles included files:

1. **Main compose file structure** (`docker-compose.yml`):
   ```yaml
   include:
     - ./supabase/docker/docker-compose.yml
     - ./supabase/docker/docker-compose.s3.yml

   services:
     infisical:
       # ... Infisical service definition
     # ... other local AI services
   ```

2. **Current startup sequence**:
   - Step 1: Start Supabase using `supabase/docker/docker-compose.yml` directly
   - Step 2: Try to start Infisical using `docker-compose.yml` (which includes Supabase files)
   - **Conflict**: Docker Compose sees Supabase services defined twice (once from the direct file, once from the include)

### Solutions

**Solution 1: Use Unified Compose (Recommended)**

Start everything together using the main `docker-compose.yml` file. This avoids conflicts because all services are managed in one compose context.

**Pros:**
- No conflicts
- All services in one project
- Easier to manage

**Cons:**
- Need to start services in the right order
- All services must be defined in or included by the main compose file

**Solution 2: Use Docker Run for Infisical (Current Workaround)**

Start Infisical using `docker run` instead of `docker compose`. This bypasses the compose file conflicts.

**Pros:**
- Works immediately
- No compose file conflicts
- Can connect to existing network

**Cons:**
- Not managed by Docker Compose
- Manual container management
- Health checks and dependencies handled manually

**Solution 3: Separate Compose Files**

Create a separate compose file for Infisical that doesn't include Supabase files.

**Pros:**
- Clean separation
- No conflicts

**Cons:**
- More files to maintain
- Services in different compose projects

### Recommended Approach

For your use case (needing both Supabase and Infisical to start together), **Solution 1** is best:

1. Use the main `docker-compose.yml` for everything
2. Start services in phases:
   - Phase 1: Supabase services (db, auth, storage, etc.)
   - Phase 2: Redis (dependency for Infisical)
   - Phase 3: Infisical
   - Phase 4: Local AI services (Ollama, n8n, etc.)

This ensures:
- ✅ No conflicts (single compose context)
- ✅ Proper dependency ordering
- ✅ All services managed together
- ✅ Easy to start/stop everything

---

## Connection Issues

### "I can't connect to Infisical UI"

**Symptoms:**
- Browser shows "Connection refused" or "Site can't be reached"
- Timeout errors
- DNS resolution failures

**Diagnostic Steps:**

1. **Check container status:**
   ```bash
   docker ps | grep infisical
   ```
   Should show: `infisical-backend`, `infisical-db`, `infisical-redis` all with "Up" status

2. **Check container health:**
   ```bash
   docker inspect infisical-backend --format='{{.State.Health.Status}}'
   ```
   Should show: `healthy`

3. **Check container logs:**
   ```bash
   docker logs infisical-backend --tail 50
   ```
   Look for errors, connection issues, or startup problems

4. **Check Caddy routing:**
   ```bash
   docker ps | grep caddy
   docker logs caddy --tail 50 | grep infisical
   ```

5. **Check Cloudflare tunnel (if using production):**
   ```bash
   docker ps | grep cloudflared
   docker logs cloudflared --tail 20
   ```
   Should show "Connection established" or similar

6. **Test direct container access:**
   ```bash
   docker exec infisical-backend wget -qO- http://localhost:8080/api/health
   ```
   Should return health status

**Solutions:**

- **Container not running:** Start services: `python start_services.py`
- **Health check failing:** Check database connection, wait for health check (30s start period)
- **Caddy not routing:** Verify Caddyfile configuration, restart Caddy: `docker restart caddy`
- **Cloudflare tunnel down:** Check tunnel token, verify tunnel route in Cloudflare dashboard
- **DNS issues:** Verify DNS records point to Cloudflare tunnel

### HTTP 500 / HTTP 415 Errors (Missing Content-Type Header)

**Symptoms:**
- After logging in and selecting an organization, you get HTTP 500 errors
- Backend logs show: `"Unsupported Media Type: undefined"` (HTTP 415)
- Error code: `FST_ERR_CTP_INVALID_MEDIA_TYPE`
- Endpoint: `POST /api/v1/auth/token`

**Root Cause:**
The Infisical frontend sends POST requests to `/api/v1/auth/token` **without the required `Content-Type: application/json` header**. Fastify (Infisical's web framework) rejects these requests because it cannot parse the request body without knowing the content type.

**Diagnostic Steps:**

1. **Check browser Network tab:**
   - Open DevTools (F12) → **Network** tab
   - Try logging in again
   - Find the failed `POST /api/v1/auth/token` request
   - Click on it → **Headers** tab → **Request Headers**
   - **Check if `Content-Type: application/json` is present**

   **If Content-Type is MISSING in browser:**
   - The browser/frontend JavaScript is not sending it
   - This could be a frontend bug or Cloudflare stripping it

   **If Content-Type is PRESENT in browser but backend receives it as undefined:**
   - Cloudflare or Caddy is stripping/modifying it
   - Check Transform Rules

2. **Check backend logs:**
   ```bash
   docker logs infisical-backend --tail 50 --follow | grep "auth/token"
   ```
   Look for: `FST_ERR_CTP_INVALID_MEDIA_TYPE` or `Unsupported Media Type: undefined`

3. **Check Caddy configuration:**
   ```bash
   cat 00-infrastructure/caddy/Caddyfile | grep -A 10 infisical
   ```
   Should show proper header forwarding via `standard_proxy` snippet

**Solutions (Try in Order):**

1. **Clear Browser Cache and Cookies ⭐ (Most Common Fix)**
   ```bash
   # Clear all cookies for infisical.datacrew.space
   # Chrome: Settings → Privacy → Clear browsing data → Cookies
   # Firefox: Settings → Privacy → Clear Data → Cookies

   # Then hard refresh: Ctrl+Shift+R (Windows/Linux) or Cmd+Shift+R (Mac)
   ```

2. **Use Incognito/Private Window**
   - Open an incognito/private window
   - Navigate to `https://infisical.datacrew.space`
   - Log in and try again
   - If it works, the issue is browser cache/cookies/extensions

3. **Check Browser Extensions**
   - Disable browser extensions (especially ad blockers, privacy tools) that might modify headers
   - Try logging in
   - If it works, re-enable extensions one by one to find the culprit

4. **Check Cloudflare Transform Rules**
   - Go to: https://dash.cloudflare.com/
   - Select domain: `datacrew.space`
   - Go to **Rules** → **Transform Rules**
   - Look for any rules affecting `infisical.datacrew.space` or `/api/*`
   - **Disable any rules that modify `Content-Type` header**

5. **Check Cloudflare SSL/TLS Mode**
   - Go to Cloudflare Dashboard → Your Domain → **SSL/TLS**
   - Set **SSL/TLS encryption mode** to **"Full"** or **"Full (strict)"**
   - **NOT "Flexible"** - this breaks secure cookies

6. **Check Cloudflare Caching**
   - Go to Cloudflare Dashboard → **Rules** → **Page Rules**
   - Create a new rule:
     - **URL Pattern**: `infisical.datacrew.space/api/*`
     - **Settings**:
       - Cache Level: **Bypass**
       - Disable Performance
   - Save and wait 1-2 minutes for propagation

7. **Restart Infisical Backend**
   ```bash
   docker restart infisical-backend
   ```

8. **Try Different Browser**
   - Chrome
   - Firefox
   - Edge
   - Safari

9. **Browser Console Workaround (Temporary)**
   Run this in browser console (F12) on the Infisical page:
   ```javascript
   // Temporary Fix for Infisical Missing Content-Type Header
   (function() {
     console.log('🔧 Applying Infisical Content-Type header fix...');

     const originalFetch = window.fetch;
     window.fetch = function(...args) {
       const url = typeof args[0] === 'string' ? args[0] : args[0]?.url || '';
       const options = args[1] || {};

       // Fix POST requests to Infisical API that are missing Content-Type
       if (url.includes('/api/v1/auth/token') && options.method === 'POST') {
         if (!options.headers) {
           options.headers = {};
         }

         // Convert Headers object to plain object if needed
         if (options.headers instanceof Headers) {
           const headersObj = {};
           options.headers.forEach((value, key) => {
             headersObj[key] = value;
           });
           options.headers = headersObj;
         }

         // Add Content-Type if missing
         if (!options.headers['Content-Type'] && !options.headers['content-type']) {
           options.headers['Content-Type'] = 'application/json';
           console.log('✅ Added Content-Type header to request:', url);
         }
       }

       return originalFetch.apply(this, args);
     };

     console.log('✅ Fix applied! Try logging in again.');
   })();
   ```

**Note:** This is a known issue with Infisical's frontend. The proper fix would be to update the frontend JavaScript to always include `Content-Type: application/json` for POST requests, but since this is a self-hosted instance, we've documented workarounds.

### Login Loop / Session Issues

**Symptoms:**
- Login appears successful but immediately logs out
- Redirect loops
- "Session expired" errors immediately after login
- Cookies not being set or rejected
- Can't login via `http://localhost:8020` when `SITE_URL` is set to Cloudflare domain

**Root Causes:**

1. **SITE_URL Domain Mismatch (Most Common for Dual Access)**
   - `INFISICAL_SITE_URL=https://infisical.datacrew.space` but accessing via `http://localhost:8020`
   - Cookies are set for `infisical.datacrew.space` domain, browser won't send them to `localhost:8020`
   - **Solution:** Use `https://infisical.datacrew.space` for login, or set `INFISICAL_SITE_URL=http://localhost:8020` for localhost-only access

2. **SSL/HTTPS Misconfiguration**
   - `HTTPS_ENABLED=true` but accessing via HTTP
   - Browser rejects secure cookies when accessed via HTTP
   - **Solution:** Use `https://` URL or set `HTTPS_ENABLED=false` for HTTP access

3. **SITE_URL Protocol Mismatch**
   - `INFISICAL_SITE_URL` doesn't match the actual URL you're accessing
   - Must match exactly including protocol (http vs https)
   - **Solution:** Ensure `SITE_URL` matches the URL you're using (including protocol)

4. **Secure Cookie Rejection**
   - Browser security settings blocking cookies
   - CORS issues
   - **Solution:** Clear browser cache/cookies, check browser security settings

5. **Browser Extension Interference**
   - Privacy extensions blocking cookies
   - Ad blockers modifying requests
   - **Solution:** Try incognito/private window, disable extensions

**Diagnostic Steps:**

1. **Verify HTTPS_ENABLED setting:**
   ```bash
   docker exec infisical-backend printenv | grep HTTPS_ENABLED
   ```
   - Should be `HTTPS_ENABLED=true` for production (https://)
   - Should be `HTTPS_ENABLED=false` for local (http://localhost)

2. **Verify SITE_URL matches access URL:**
   ```bash
   docker exec infisical-backend printenv | grep SITE_URL
   ```
   - For production: `SITE_URL=https://infisical.datacrew.space`
   - For local: `SITE_URL=http://localhost:8020`
   - Must match exactly what you see in browser address bar

3. **Check browser cookies:**
   - Open DevTools (F12) → **Application** tab → **Cookies**
   - Check if cookies are being set for `infisical.datacrew.space`
   - Look for `Secure` flag (should be set for HTTPS)

4. **Check Caddy X-Forwarded-Proto header:**
   ```bash
   cat 00-infrastructure/caddy/Caddyfile | grep X-Forwarded-Proto
   ```
   Should show: `header_up X-Forwarded-Proto https`

**Solutions:**

1. **Fix SITE_URL Domain Mismatch (For Dual Access):**
   - **Problem:** `SITE_URL=https://infisical.datacrew.space` but accessing via `http://localhost:8020`
   - **Solution:**
     - **Option A (Recommended):** Use `https://infisical.datacrew.space` for login - cookies work correctly
     - **Option B:** Set `INFISICAL_SITE_URL=http://localhost:8020` and `INFISICAL_HTTPS_ENABLED=false` for localhost-only access
     - **Option C:** Accept that localhost access is view-only when `SITE_URL` is set to Cloudflare domain
   - Restart Infisical: `docker restart infisical-backend`

2. **Fix HTTPS_ENABLED:**
   - For production/Cloudflare: Set `HTTPS_ENABLED=true` in `.env`
   - For localhost-only: Set `HTTPS_ENABLED=false` in `.env`
   - Must match the protocol of `SITE_URL`
   - Restart Infisical: `docker restart infisical-backend`

3. **Fix SITE_URL Protocol:**
   - Update `.env` file to match your actual access URL exactly (including protocol)
   - `http://localhost:8020` for localhost
   - `https://infisical.datacrew.space` for Cloudflare
   - Restart Infisical: `docker restart infisical-backend`

4. **Use Correct URL:**
   - **For localhost:** Use `http://localhost:8020` NOT `https://localhost:8020` (no SSL certificate)
   - **For Cloudflare:** Use `https://infisical.datacrew.space`
   - **For login with dual access:** Use Cloudflare domain (`https://infisical.datacrew.space`)

5. **Clear Browser Cache and Cookies:**
   - Clear all cookies for both `localhost` and `infisical.datacrew.space`
   - Clear browser cache
   - Hard refresh: `Ctrl+Shift+R` (Windows/Linux) or `Cmd+Shift+R` (Mac)

6. **Try Incognito/Private Window:**
   - Rules out browser extensions and cache issues

7. **Disable Browser Extensions:**
   - Temporarily disable all extensions
   - Try logging in
   - Re-enable one by one to find culprit

### "Access Restricted" Error

**Symptoms:**
- After logging in and selecting an organization/department, you get an "Access Restricted" error
- User can authenticate but cannot access the organization

**Root Cause:**
The user account exists but has **no organization membership** in the `org_memberships` table. This causes Infisical to deny access even though the user can authenticate.

**Diagnostic Steps:**

1. **Check if user has organization membership:**
   ```bash
   docker exec infisical-db psql -U postgres -d postgres -c \
     "SELECT u.email, om.role, om.status, o.name as org_name \
      FROM users u \
      LEFT JOIN org_memberships om ON u.id = om.\"userId\" \
      LEFT JOIN organizations o ON om.\"orgId\" = o.id \
      WHERE u.email = 'YOUR_EMAIL@example.com';"
   ```

   If `role` and `status` are empty, the user has no membership.

2. **Get User and Organization IDs:**
   ```bash
   # Get user ID
   docker exec infisical-db psql -U postgres -d postgres -c \
     "SELECT id, email FROM users WHERE email = 'YOUR_EMAIL@example.com';"

   # Get organization ID
   docker exec infisical-db psql -U postgres -d postgres -c \
     "SELECT id, name FROM organizations;"
   ```

**Solution:**

Add organization membership:
```bash
docker exec infisical-db psql -U postgres -d postgres -c \
  "INSERT INTO org_memberships (\"userId\", \"orgId\", role, status) \
   VALUES ('USER_ID_HERE', 'ORG_ID_HERE', 'admin', 'accepted') \
   ON CONFLICT DO NOTHING;"
```

Replace:
- `USER_ID_HERE` with the user ID from diagnostic step 2
- `ORG_ID_HERE` with the organization ID from diagnostic step 2

**Common Roles:**
- `admin` - Full access to organization
- `member` - Standard member access
- `viewer` - Read-only access

**Status Values:**
- `accepted` - Active membership
- `invited` - Pending invitation
- `rejected` - Rejected invitation

**Prevention:**
- Always create users through the Infisical UI (`/admin/signup`)
- Use the UI to add users to organizations
- Avoid manual database modifications unless necessary

### Cloudflare Configuration Issues

**Symptoms:**
- Login works locally but fails via Cloudflare tunnel
- Headers being modified or stripped
- SSL/TLS errors
- Caching issues

**Common Cloudflare Issues:**

1. **SSL/TLS Mode Must Be "Full" or "Full (strict)"**
   - **NOT "Flexible"** - this breaks secure cookies
   - Go to Cloudflare Dashboard → Your Domain → **SSL/TLS**
   - Set **SSL/TLS encryption mode** to **"Full"** or **"Full (strict)"**

2. **Caching Must Bypass `/api/*` Paths**
   - Go to Cloudflare Dashboard → **Rules** → **Page Rules**
   - Create a new rule:
     - **URL Pattern**: `infisical.datacrew.space/api/*`
     - **Settings**:
       - Cache Level: **Bypass**
       - Disable Performance
   - Save and wait 1-2 minutes for propagation

3. **Transform Rules Must Not Modify `Content-Type` Header**
   - Go to Cloudflare Dashboard → **Rules** → **Transform Rules**
   - Check for any rules affecting `infisical.datacrew.space` or `/api/*`
   - **Disable or delete** any rules that modify `Content-Type` header

4. **Cloudflare Access Interference**
   - Go to Cloudflare Zero Trust → **Access** → **Applications**
   - Look for an application named "Infisical" or matching `infisical.datacrew.space`
   - If found, either:
     - **Option A:** Remove Access (if not needed)
     - **Option B:** Configure Access properly

5. **Browser Integrity Check Too Strict**
   - Go to Cloudflare Dashboard → **Security** → **Settings**
   - Find **Browser Integrity Check**
   - Try setting to **"Medium"** or **"Low"**

6. **Tunnel Origin Request Settings**
   - Go to **Networks** → **Tunnels** → Your tunnel
   - Click **Configure** → Find `infisical.datacrew.space` route
   - Click **Edit** → **Additional application settings**
   - Under **Origin Request**, ensure:
     - **HTTP Host Header**: `infisical.datacrew.space` ✓
     - **No additional header modifications**

**Recommended Cloudflare Settings for Infisical:**

- **SSL/TLS**: Full (strict)
- **Minimum TLS Version**: 1.2
- **Cache Level**: Bypass (for `/api/*`)
- **Browser Cache TTL**: Respect Existing Headers
- **Browser Integrity Check**: Medium
- **Challenge Passage**: 30 minutes
- **Security Level**: Medium
- **Transform Rules**: None (don't modify request/response headers)

### Caddy Reverse Proxy Issues

**Symptoms:**
- Headers not being forwarded
- Routing not working
- Timeout errors

**Diagnostic Steps:**

1. **Check Caddy configuration:**
   ```bash
   cat 00-infrastructure/caddy/Caddyfile | grep -A 20 infisical
   ```

2. **Check Caddy logs:**
   ```bash
   docker logs caddy --tail 50 | grep infisical
   ```

3. **Test direct connection:**
   ```bash
   docker exec caddy curl -X POST http://infisical-backend:8080/api/v1/auth/token \
     -H "Content-Type: application/json" \
     -H "Host: infisical.datacrew.space" \
     -d '{}' \
     -v
   ```

**Solutions:**

1. **Verify Caddyfile configuration:**
   ```caddy
   {$INFISICAL_HOSTNAME} {
       import security_headers
       reverse_proxy infisical-backend:8080 {
           import standard_proxy
           transport http {
               read_timeout 300s
               write_timeout 300s
           }
       }
   }
   ```

2. **Restart Caddy:**
   ```bash
   docker restart caddy
   ```

3. **Check for header modifications:**
   - Ensure `standard_proxy` snippet forwards all headers
   - Don't add custom header modifications unless necessary

### Database Connection Issues

**Symptoms:**
- Infisical backend won't start
- Health check failures
- Database connection errors in logs

**Diagnostic Steps:**

1. **Check database container:**
   ```bash
   docker ps | grep infisical-db
   docker logs infisical-db --tail 20
   ```

2. **Check database connection string:**
   ```bash
   docker exec infisical-backend printenv | grep POSTGRES
   ```

3. **Test database connection:**
   ```bash
   docker exec infisical-db psql -U postgres -d postgres -c "SELECT 1;"
   ```

**Solutions:**

1. **Password Encoding Issues:**
   - If password contains special characters, it may need URL encoding
   - Check `INFISICAL_POSTGRES_PASSWORD_URL_ENCODED` in `.env`
   - Use URL-encoded version in connection string if needed

2. **Database Not Ready:**
   - Wait for database to be healthy before starting Infisical backend
   - Check health: `docker inspect infisical-db --format='{{.State.Health.Status}}'`

3. **Connection String Issues:**
   - Verify `INFISICAL_POSTGRES_HOST`, `INFISICAL_POSTGRES_PORT`, `INFISICAL_POSTGRES_DATABASE` are correct
   - Check network connectivity: `docker exec infisical-backend ping infisical-db`

---

## Authentication Problems

### CLI Authentication Failures

**Symptoms:**
- `infisical login` fails
- Browser OAuth redirect fails
- Token storage issues

**Diagnostic Steps:**

1. **Check CLI installation:**
   ```bash
   infisical --version
   ```

2. **Check authentication status:**
   ```bash
   infisical secrets  # Should show secrets or empty list (not error)
   ```

3. **Check CLI config:**
   ```bash
   cat ~/.infisical/infisical-config.json
   ```

**Solutions:**

1. **Re-authenticate:**
   ```bash
   infisical logout
   infisical login --host=https://infisical.datacrew.space
   ```

2. **Clear CLI config:**
   ```bash
   rm -f ~/.infisical/infisical-config.json
   infisical login --host=https://infisical.datacrew.space
   ```

3. **Verify domain accessibility:**
   - Check Cloudflare tunnel is working
   - Test: `curl -I https://infisical.datacrew.space`

4. **Check OAuth redirect URI:**
   - Must match `INFISICAL_SITE_URL` exactly
   - Verify in browser during login flow

### UI Login Failures

**Symptoms:**
- Can't log in via web UI
- Login form not working
- Session not persisting

**Solutions:**

- See [HTTP 500 / HTTP 415 Errors](#http-500--http-415-errors-missing-content-type-header) section
- See [Login Loop / Session Issues](#login-loop--session-issues) section
- Clear browser cache and cookies
- Try incognito/private window
- Check browser console for JavaScript errors

### Machine Identity Issues

**Symptoms:**
- Automated secret fetching fails
- `start_services.py --use-infisical` fails

**Solutions:**

1. **Verify machine identity is set up:**
   - Check Infisical UI → Settings → Machine Identities
   - Verify client ID and secret are correct

2. **Set environment variables:**
   ```bash
   export INFISICAL_MACHINE_CLIENT_ID=<client-id>
   export INFISICAL_MACHINE_CLIENT_SECRET=<client-secret>
   ```

3. **Authenticate with machine identity:**
   ```bash
   infisical login --method=universal-auth \
     --client-id=$INFISICAL_MACHINE_CLIENT_ID \
     --client-secret=$INFISICAL_MACHINE_CLIENT_SECRET
   ```

---

## Infrastructure Issues

### Service Startup Failures

**Symptoms:**
- Containers won't start
- Health check failures
- Dependency errors

**Diagnostic Steps:**

1. **Check container status:**
   ```bash
   docker ps -a | grep infisical
   ```

2. **Check container logs:**
   ```bash
   docker logs infisical-backend --tail 50
   docker logs infisical-db --tail 20
   docker logs infisical-redis --tail 20
   ```

3. **Check dependencies:**
   ```bash
   docker ps | grep -E "(postgres|redis)"
   ```

**Solutions:**

1. **Start dependencies first:**
   ```bash
   # Start database and Redis first
   docker compose up -d infisical-db infisical-redis

   # Wait for them to be healthy
   docker ps | grep -E "(infisical-db|infisical-redis)"

   # Then start backend
   docker compose up -d infisical-backend
   ```

2. **Check health checks:**
   - Health check has 30s start period
   - Wait a bit longer if containers are still starting

3. **Verify network connectivity:**
   ```bash
   docker exec infisical-backend ping infisical-db
   docker exec infisical-backend ping infisical-redis
   ```

### Email Service Not Configured

**Symptoms:**
- Error: "The administrators of this Infisical instance have not yet set up an email service provider required to perform this action"
- Can't create admin account via email signup

**Solutions:**

**Solution 1: Configure SMTP (Recommended)**

Add SMTP configuration to your `.env` file:
```bash
SMTP_HOST=smtp.sendgrid.net  # or smtp.gmail.com, smtp.mailgun.org, etc.
SMTP_PORT=587
SMTP_USERNAME=your_smtp_username
SMTP_PASSWORD=your_smtp_password
SMTP_FROM_ADDRESS=your_email@example.com
SMTP_FROM_NAME=Infisical
```

Then restart Infisical:
```bash
cd 00-infrastructure
docker compose restart infisical-backend
```

**Solution 2: Use Google OAuth**

If you have Google OAuth configured, you can sign in with Google instead of email:
1. Add `GOOGLE_CLIENT_ID` and `GOOGLE_CLIENT_SECRET` to `.env`
2. Restart Infisical
3. Use "Sign in with Google" on the login page

**Solution 3: Create User via Database (Advanced)**

If you need to create a user without SMTP, you can manually insert into the database.
⚠️ **Warning:** This is an advanced workaround and may not work with all Infisical features.

```bash
# Connect to the database
docker exec -it infisical-db psql -U postgres -d postgres

# Note: This requires knowledge of Infisical's database schema and password hashing
# It's recommended to configure SMTP instead
```

---

## Diagnostic Commands Reference

### Container Health Checks

```bash
# Check all Infisical containers
docker ps | grep infisical

# Check container health status
docker inspect infisical-backend --format='{{.State.Health.Status}}'

# Check container logs
docker logs infisical-backend --tail 50
docker logs infisical-db --tail 20
docker logs infisical-redis --tail 20

# Follow logs in real-time
docker logs infisical-backend --tail 50 --follow
```

### Network Diagnostics

```bash
# Test container-to-container connectivity
docker exec infisical-backend ping infisical-db
docker exec infisical-backend ping infisical-redis

# Test HTTP connectivity
docker exec infisical-backend wget -qO- http://localhost:8080/api/health

# Test from Caddy to Infisical
docker exec caddy curl -X POST http://infisical-backend:8080/api/v1/auth/token \
  -H "Content-Type: application/json" \
  -H "Host: infisical.datacrew.space" \
  -d '{}' \
  -v

# Check network configuration
docker network inspect ai-network | grep -A 10 infisical
```

### Database Queries

```bash
# Check user and organization membership
docker exec infisical-db psql -U postgres -d postgres -c \
  "SELECT u.email, om.role, om.status, o.name as org_name \
   FROM users u \
   LEFT JOIN org_memberships om ON u.id = om.\"userId\" \
   LEFT JOIN organizations o ON om.\"orgId\" = o.id \
   WHERE u.email = 'YOUR_EMAIL@example.com';"

# List all users
docker exec infisical-db psql -U postgres -d postgres -c \
  "SELECT id, email FROM users;"

# List all organizations
docker exec infisical-db psql -U postgres -d postgres -c \
  "SELECT id, name FROM organizations;"
```

### Browser Debugging

**Browser Console Commands:**
```javascript
// Check cookies
console.log("Cookies:", document.cookie);

// Test fetch request
fetch("https://infisical.datacrew.space/api/v1/auth/token", {
  method: "POST",
  headers: {
    "Content-Type": "application/json"
  },
  body: JSON.stringify({}),
  credentials: "include"
}).then(r => {
  console.log("Status:", r.status);
  return r.text();
}).then(text => {
  console.log("Response:", text);
});
```

**Network Tab Inspection:**
1. Open DevTools (F12) → **Network** tab
2. Try logging in
3. Find the failed request to `/api/v1/auth/token`
4. Check **Request Headers** for `Content-Type`
5. Check **Response** for error details

### Cloudflare Checks

```bash
# Check Cloudflare tunnel status
docker ps | grep cloudflared
docker logs cloudflared --tail 20

# Test domain accessibility
curl -I https://infisical.datacrew.space

# Check DNS resolution
nslookup infisical.datacrew.space
```

**Manual Dashboard Checks:**
1. Go to: https://dash.cloudflare.com/
2. Select domain: `datacrew.space`
3. Check **SSL/TLS** settings (must be "Full" or "Full (strict)")
4. Check **Rules** → **Page Rules** (bypass cache for `/api/*`)
5. Check **Rules** → **Transform Rules** (no Content-Type modifications)
6. Check **Networks** → **Tunnels** (tunnel status and routes)

### Caddy Verification

```bash
# Check Caddy configuration
cat 00-infrastructure/caddy/Caddyfile | grep -A 20 infisical

# Check Caddy logs
docker logs caddy --tail 50 | grep infisical

# Reload Caddy configuration
docker exec caddy caddy reload --config /etc/caddy/Caddyfile

# Restart Caddy
docker restart caddy
```

---

## Troubleshooting Decision Tree

```
Can't connect to Infisical UI?
├─ Container running?
│  ├─ No → Start services: python start_services.py
│  └─ Yes → Check logs: docker logs infisical-backend --tail 50
│
├─ Caddy routing?
│  ├─ Check Caddyfile: cat 00-infrastructure/caddy/Caddyfile | grep infisical
│  └─ Restart Caddy: docker restart caddy
│
├─ Cloudflare tunnel? (production only)
│  ├─ Check tunnel status: docker ps | grep cloudflared
│  ├─ Check tunnel logs: docker logs cloudflared --tail 20
│  └─ Verify route in Cloudflare dashboard
│
└─ DNS resolution?
   └─ Check DNS: nslookup infisical.datacrew.space

Getting HTTP 500 on login?
├─ Check browser Network tab for Content-Type header
│  └─ Missing? → Clear browser cache/cookies, try incognito mode
│
├─ Check Cloudflare Transform Rules
│  └─ Disable rules modifying Content-Type header
│
├─ Check Cloudflare SSL/TLS mode
│  └─ Must be "Full" or "Full (strict)", not "Flexible"
│
├─ Check Cloudflare caching
│  └─ Bypass cache for /api/* paths
│
└─ Check Caddy configuration
   └─ Verify header forwarding, restart Caddy

Getting "Access Restricted" after login?
└─ Check database for organization membership
   └─ Add membership if missing (see troubleshooting section)

CLI authentication fails?
├─ Verify domain accessible: curl -I https://infisical.datacrew.space
├─ Clear CLI config: rm -f ~/.infisical/infisical-config.json
└─ Re-authenticate: infisical login --host=https://infisical.datacrew.space

Services won't start?
├─ Check Docker Compose conflicts (see conflicts section)
├─ Check database connection
└─ Check health check failures (wait 30s for startup)
```

---

## Historical Troubleshooting Sessions

### 2026-01-03: Login Troubleshooting Session

**Issue Description:**
User experienced an "immediate logout after login" loop. Specifically, after successful authentication and selecting an organization, the UI displayed "access restricted" and redirected back to the login page.

**Progress Log:**

#### 1. Database Restoration
- **Problem**: Infisical was pointing to a new, empty volume (`localai_infisical-pg-data`), causing a "User not found" error.
- **Action**: Identified that the user data existed in an older volume (`00-infrastructure_infisical-pg-data`).
- **Resolution**: Migrated the PostgreSQL data from the old volume to the active one.
- **Result**: User `jaewilson07@gmail.com` can now successfully authenticate.

#### 2. Login Loop / Access Restriction
- **Symptoms**: After selecting "Admin Org", the user is booted.
- **Log Analysis**:
    - Backend logs show `statusCode: 200` for `/api/v3/auth/select-organization`.
    - Follow-up requests to `/api/v1/auth/token` fail with `Unsupported Media Type: undefined` (HTTP 415) and `statusCode: 500`.
- **Environment Verification**:
    - `SITE_URL` is set to `https://infisical.datacrew.space`.
    - `HTTPS_ENABLED` is set to `true`.
    - `TRUST_PROXY` is set to `true`.
    - `AUTH_SECRET` is persistent.

**Troubleshooting Checklist Status (Current Configuration):**

| Feature | Status | Value (Current) |
|---------|--------|-----------------|
| `SITE_URL` | ✅ Set | `https://infisical.datacrew.space` |
| `HTTPS_ENABLED` | ✅ Restored | `true` (Correct production setting) |
| `AUTH_SECRET` | ✅ Set | (Persistent string) |
| `TRUST_PROXY` | ✅ Set | `true` |
| **RBAC / Membership** | ✅ Fixed | User manually linked to Org |

**Actions Taken:**
- **2026-01-03 14:45**: Changed `HTTPS_ENABLED` to `false` (Attempt 1 - Failed).
- **2026-01-03 14:55**: Identified root cause: **Missing Organization Membership**.
    - The user `jaewilson07@gmail.com` existed in the database.
    - The organization "Admin Org" existed.
    - However, the `org_memberships` table had **0 rows** for this user, likely lost during a previous volume reset or migration glitch.
    - **Fix:** Manually inserted the membership record into PostgreSQL:
      ```sql
      INSERT INTO org_memberships ("userId", "orgId", role, status)
      VALUES ('...', '...', 'admin', 'accepted');
      ```
- **2026-01-03 15:00**: Reverted `HTTPS_ENABLED` back to `true` (Correct setting) and restarted services.

**Resolution:**
The "access restricted" loop was caused by the user account lacking a link to any organization in the database. With the database link restored, the user should now be able to access the dashboard.

---

### 2026-01-04: HTTP 500 and CSP Troubleshooting Session

**Issue Description:**
After resolving the organization membership issue, the user could select their organization but encountered HTTP 500 errors when the frontend tried to refresh the auth token. Additionally, browser console showed CSP (Content-Security-Policy) warnings.

**Browser Console Errors Observed:**
```
POST https://infisical.datacrew.space/api/v1/auth/token 500 (Internal Server Error)
Ignoring duplicate Content-Security-Policy directive 'connect-src'.
Loading the script 'https://static.cloudflareinsights.com/beacon.min.js/...' violates Content Security Policy
```

**Root Cause Analysis:**

1. **HTTP 500 / Missing Content-Type Header**
   - The Infisical frontend's XHR requests to `/api/v1/auth/token` were not including `Content-Type: application/json`
   - Fastify (Infisical's backend) requires this header to parse request bodies
   - Error in backend logs: `FST_ERR_CTP_INVALID_MEDIA_TYPE` / `Unsupported Media Type: undefined`

2. **Duplicate CSP Directive Warning**
   - Caddy was sending its own CSP headers via `csp_standard` snippet
   - Infisical also sends its own CSP headers
   - Browser was receiving duplicate/conflicting CSP directives

3. **Cloudflare Insights Script Blocked**
   - Caddy's CSP didn't include `static.cloudflareinsights.com` in `script-src`
   - Not critical for functionality but caused console warnings

**Actions Taken:**

1. **2026-01-04 09:15**: Added Content-Type header injection at Caddy level
   - Modified Caddyfile to add `Content-Type: application/json` for POST/PUT/PATCH requests to `/api/*`
   - This works around the Infisical frontend bug
   ```caddy
   # FIX: Infisical frontend bug - add missing Content-Type header for API POST requests
   @api_post {
       method POST PUT PATCH
       path /api/*
   }
   request_header @api_post Content-Type application/json
   ```

2. **2026-01-04 09:16**: Removed conflicting CSP headers for Infisical
   - Removed `import csp_standard` from Infisical's handle block
   - Let Infisical handle its own CSP headers (avoids duplicate directive warnings)
   ```caddy
   # NOTE: Not importing csp_standard - let Infisical handle its own CSP
   # Caddy's CSP conflicts with Infisical's built-in CSP headers
   import security_headers_base
   import infisical_cors
   # (removed: import csp_standard)
   ```

3. **2026-01-04 09:17**: Reloaded Caddy configuration
   ```bash
   docker exec caddy caddy reload --config /etc/caddy/Caddyfile
   ```

**Configuration Changes Made:**

| File | Change | Purpose |
|------|--------|---------|
| `00-infrastructure/caddy/Caddyfile` | Added conditional `request_header` for Content-Type | Fix missing Content-Type header bug |
| `00-infrastructure/caddy/Caddyfile` | Excluded `/api/v1/auth/token` from Content-Type injection | This endpoint uses cookies, not JSON body |
| `00-infrastructure/caddy/Caddyfile` | Removed `import csp_standard` for Infisical | Avoid duplicate CSP headers |

**Progress Notes:**

1. **First attempt** (adding Content-Type for all API POSTs):
   - Changed error from `FST_ERR_CTP_INVALID_MEDIA_TYPE` to `FST_ERR_CTP_EMPTY_JSON_BODY`
   - Root cause: Frontend sends POST to `/api/v1/auth/token` with NO body (uses cookies)
   - When we add `Content-Type: application/json`, Fastify expects a JSON body

2. **Second attempt** (excluding `/api/v1/auth/token` from Content-Type injection):
   - Allows the auth/token endpoint to work without Content-Type
   - Other endpoints still get the Content-Type fix

**Key Findings:**
- The `/api/v1/auth/token` endpoint is a **cookie-based token refresh** endpoint
- It sends POST requests with **cookies only, no JSON body**
- Adding Content-Type breaks it because Fastify then expects a body
- The original "Unsupported Media Type" error may have been from **different** API endpoints

**Verification Steps:**
1. Clear browser cookies for `infisical.datacrew.space`
2. Open incognito/private window
3. Navigate to `https://infisical.datacrew.space`
4. Log in with Google SSO
5. Select organization
6. Monitor browser console for any remaining errors

**Current Status:** Identified root cause - frontend sends POST with null body and no Content-Type.

**2026-01-04 09:45**: Further investigation via browser Network tab revealed:
- Request to `/api/v1/auth/token` sends `body: null` (empty)
- No `Content-Type` header
- Authorization via Bearer token in header

This is a confirmed Infisical frontend bug. The frontend sends POST requests without body or Content-Type, which Fastify rejects.

**Workaround - Browser Console Fix:**

Run this JavaScript in browser console (F12) on the Infisical page:

```javascript
// Fix for Infisical auth/token endpoint - patches fetch to add empty JSON body
(function() {
    const originalFetch = window.fetch;
    window.fetch = function(url, options = {}) {
        if (typeof url === 'string' && url.includes('/api/v1/auth/token') && options.method === 'POST') {
            if (!options.body || options.body === null) {
                options.body = '{}';
                options.headers = options.headers || {};
                if (options.headers instanceof Headers) {
                    options.headers.set('Content-Type', 'application/json');
                } else {
                    options.headers['Content-Type'] = 'application/json';
                }
                console.log('✅ Fixed auth/token request');
            }
        }
        return originalFetch.call(this, url, options);
    };
    console.log('🔧 Infisical fix applied - refresh page and try again');
})();
```

**Alternative - Tampermonkey/Greasemonkey Userscript:**

For a permanent fix without running console code each time, install Tampermonkey and create this userscript:

```javascript
// ==UserScript==
// @name         Infisical Auth Fix
// @namespace    http://datacrew.space/
// @version      1.0
// @description  Fix Infisical frontend bug with empty auth/token requests
// @match        https://infisical.datacrew.space/*
// @grant        none
// @run-at       document-start
// ==/UserScript==

(function() {
    'use strict';
    const originalFetch = window.fetch;
    window.fetch = function(url, options = {}) {
        if (typeof url === 'string' && url.includes('/api/v1/auth/token') && options.method === 'POST') {
            if (!options.body || options.body === null) {
                options.body = '{}';
                options.headers = options.headers || {};
                if (options.headers instanceof Headers) {
                    options.headers.set('Content-Type', 'application/json');
                } else {
                    options.headers['Content-Type'] = 'application/json';
                }
            }
        }
        return originalFetch.call(this, url, options);
    };
})();
```

**Root Cause:** Infisical frontend bug - sends POST requests to `/api/v1/auth/token` with `body: null` and no Content-Type header. Fastify (backend) rejects these requests.

---

**2026-01-04 10:15**: Applied permanent Fastify patch

**Solution - Fastify Patch (Permanent Fix):**

Created a patched version of Infisical's `app.mjs` that overrides the default JSON content-type parser to accept empty bodies:

1. **Patch file location**: `00-infrastructure/infisical/patches/app.mjs`
2. **Docker compose volume mount**: Mounts the patched file into the container
3. **What it does**: Custom `application/json` parser that returns `{}` for empty bodies instead of throwing `FST_ERR_CTP_EMPTY_JSON_BODY`

**Verification**: Look for this message in container logs:
```
[PATCH] Applied empty JSON body fix for Fastify
```

**Files Modified:**
- `00-infrastructure/infisical/patches/app.mjs` - Patched Fastify app with empty JSON body handler
- `00-infrastructure/infisical/docker-compose.yml` - Added volume mount for patch
- `00-infrastructure/caddy/Caddyfile` - Adds Content-Type header for API POST requests

**To apply patch to existing installation:**
```bash
# Recreate the Infisical backend container with the patch mounted
docker stop infisical-backend
docker rm infisical-backend
cd /path/to/local-ai-packaged
source .env
docker run -d \
  --name infisical-backend \
  --network ai-network \
  --restart unless-stopped \
  -e NODE_ENV=production \
  -e ENCRYPTION_KEY="$INFISICAL_ENCRYPTION_KEY" \
  -e AUTH_SECRET="$INFISICAL_AUTH_SECRET" \
  -e DB_CONNECTION_URI="postgresql://postgres:${INFISICAL_POSTGRES_PASSWORD}@infisical-db:5432/postgres" \
  -e REDIS_URL="redis://infisical-redis:6379" \
  -e SITE_URL="https://infisical.datacrew.space" \
  -e PORT=8080 \
  -e HOST=0.0.0.0 \
  -e TELEMETRY_ENABLED=false \
  -e TRUST_PROXY=true \
  -e HTTPS_ENABLED=true \
  -e GOOGLE_CLIENT_ID="$GOOGLE_CLIENT_ID" \
  -e GOOGLE_CLIENT_SECRET="$GOOGLE_CLIENT_SECRET" \
  -v $(pwd)/00-infrastructure/infisical/patches/app.mjs:/backend/dist/server/app.mjs:ro \
  infisical/infisical:latest
```

**Status**: ✅ RESOLVED - Fastify patch applied successfully.

---

## Related Documentation

- [Setup Guide](./setup.md) - Initial setup and configuration
- [Usage Guide](./usage.md) - Day-to-day operations and secret management
- [Design Documentation](./design.md) - Architecture and design decisions
- [Infisical Official Documentation](https://infisical.com/docs)
