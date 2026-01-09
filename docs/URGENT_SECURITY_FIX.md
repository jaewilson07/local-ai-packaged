# ⚠️ URGENT: Secure Lambda MCP Server

## Current Security Status: ⚠️ VULNERABLE

**The Lambda MCP server at `https://api.datacrew.space` is currently publicly accessible without authentication.**

This means:
- ❌ **Anyone on the internet** can access your MCP tools
- ❌ **Anyone can** search your knowledge base
- ❌ **Anyone can** crawl websites and ingest content
- ❌ **Anyone can** execute N8N workflows
- ❌ **Anyone can** access your MongoDB RAG system
- ❌ **No authentication required**

## Immediate Action Required

### Step 1: Verify Current Protection Status

Check if Cloudflare Access is configured:

1. **Go to Cloudflare Dashboard**:
   - https://one.dash.cloudflare.com/
   - Networks → Tunnels → Your tunnel
   - Find the `api.datacrew.space` route
   - Check the **Access** column

2. **If it shows "None" or is empty**: ⚠️ **NOT PROTECTED**

### Step 2: Enable Cloudflare Access (Choose One)

#### Option A: Link Existing Wildcard Application (Fastest)

If you have a wildcard access policy for `*.datacrew.space`:

1. **Go to Networks → Tunnels → Your tunnel**
2. **Find `api.datacrew.space` route**
3. **Click Edit**
4. **Scroll to Access section**
5. **Select the wildcard application** (e.g., "Datacrew Wildcard Access")
6. **Click Save**

**That's it!** The API is now protected.

#### Option B: Create Specific Application for API

If no wildcard exists, create a dedicated application:

1. **Go to Access → Applications → Add an application**
2. **Select Self-hosted**
3. **Configure**:
   - **Application name**: `Lambda API`
   - **Application domain**: `api.datacrew.space`
   - **Session duration**: `24 hours`
4. **Add Policy**:
   - **Policy name**: `Lambda API Access`
   - **Action**: `Allow`
   - **Include Rules**:
     - **Emails**: `jaewilson07@gmail.com` (your email)
     - **Email domain**: `@datacrew.space` (optional)
   - **Identity Providers**: Google OAuth (if configured)
5. **Link to Tunnel Route**:
   - Networks → Tunnels → Your tunnel
   - Edit `api.datacrew.space` route
   - Under Access, select "Lambda API"
   - Save

### Step 3: Verify Protection

After enabling Cloudflare Access:

```bash
# This should redirect to Cloudflare Access login
curl -I https://api.datacrew.space/mcp/openapi.json
```

**Expected**: HTTP 302 redirect to Cloudflare Access login page

**If you get JSON back**: ⚠️ Still not protected - check tunnel route configuration

## Security Risks of Unprotected API

### What Attackers Can Do

1. **Access Your Knowledge Base**:
   - Search all your documents
   - View sensitive information
   - Export conversation data

2. **Abuse Your Resources**:
   - Crawl websites using your server (costs bandwidth/CPU)
   - Ingest malicious content into your RAG system
   - Execute expensive operations (deep crawls, LLM queries)

3. **Access Your Infrastructure**:
   - Query Neo4j knowledge graph
   - Execute N8N workflows
   - Access MongoDB data

4. **Rate Limiting Abuse**:
   - Overwhelm your server with requests
   - Cause denial of service

## Temporary Workaround (If You Can't Enable Access Immediately)

If you need to use the API immediately but can't set up Cloudflare Access right now:

1. **Use Internal Network Only**:
   - In Open WebUI, use `http://lambda-server:8000/mcp/openapi.json`
   - This only works if Open WebUI's backend proxies the request
   - Frontend can't access internal Docker hostnames

2. **Add API Key Authentication** (See [MCP Security Setup](./MCP_SECURITY_SETUP.md#option-2-api-key-authentication-alternative))

3. **Restrict at Network Level**:
   - Use Cloudflare Firewall Rules to block all traffic except your IP
   - Not recommended for production (IPs change)

## Best Practice: Defense in Depth

Even with Cloudflare Access, consider:

1. **API Key Authentication** (application-level)
2. **Rate Limiting** (Cloudflare or application-level)
3. **IP Allowlisting** (if you have static IPs)
4. **Monitoring** (Cloudflare Analytics + application logs)

## Verification Checklist

After securing:

- [ ] Cloudflare Access application created/linked
- [ ] Tunnel route shows Access application in dashboard
- [ ] `curl https://api.datacrew.space/mcp/openapi.json` redirects to login
- [ ] Authenticated users can access the API
- [ ] Unauthenticated users are blocked

## References

- [MCP Security Setup Guide](./MCP_SECURITY_SETUP.md)
- [Cloudflare Access Documentation](https://developers.cloudflare.com/cloudflare-one/policies/access/)
- [Manage Cloudflare Access Script](../00-infrastructure/scripts/manage-cloudflare-access.py)

