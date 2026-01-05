# Cloudflare Tunnel Setup Guide

This guide will walk you through setting up Cloudflare Tunnel (Cloudflared) to expose your Docker services under `datacrew.space` subdomains without requiring port forwarding.

## Quick Start (Automated)

**Recommended:** Use the automated setup script:

```bash
python setup/cloudflare/setup_tunnel.py
```

This script will:

- Check for cloudflared CLI installation
- Authenticate with Cloudflare
- Create a tunnel
- Configure routes for all services
- Generate tunnel token and update `.env` file

**Prerequisites for automated setup:**

- `cloudflared` CLI installed (see installation below)
- Domain `datacrew.space` added to Cloudflare account
- Nameservers updated in Squarespace (can be done after tunnel setup)

## Architecture Decisions

### Why Cloudflare Tunnel vs Direct DNS

**Decision:** Use Cloudflare Tunnel instead of direct DNS with port forwarding.

**Rationale:**
- No port forwarding required - works behind NAT/firewalls
- Works with dynamic IP addresses
- Origin IP completely hidden from public
- Free SSL certificates automatically provisioned
- DDoS protection included
- No firewall/router configuration needed
- Perfect for home servers or any environment where ports can't be opened

**Trade-offs:**
- Requires Cloudflare account (free tier works)
- All traffic routes through Cloudflare (acceptable for most use cases)
- Slight latency increase (minimal in practice)

### Service Routing Strategy

**Decision:** Route all services through Caddy, then through Cloudflare Tunnel.

**Architecture:**
```
Internet → Cloudflare Tunnel → Caddy (reverse proxy) → Services
```

**Rationale:**
- Caddy provides local reverse proxy and SSL termination
- Single entry point simplifies routing
- Caddy handles hostname-based routing internally
- Cloudflare Tunnel only needs to route to Caddy (port 80)
- Easier to add/remove services without touching Cloudflare config

**Alternative Considered:**
- Direct routing from Cloudflare Tunnel to each service
- Rejected because it would require more Cloudflare configuration changes

**For detailed information:** See [Caddy and Cloudflare Integration](./caddy-integration.md)

## Manual Setup

If you prefer to set up manually or the automated script doesn't work for your setup, follow the steps below.

## Prerequisites

- A Cloudflare account (free tier works)
- Your domain `datacrew.space` added to Cloudflare
- Access to your Squarespace DNS settings (to point nameservers to Cloudflare)
- `cloudflared` CLI installed (for automated setup)

## Installing cloudflared CLI

**Windows (PowerShell):**

```powershell
winget install --id Cloudflare.cloudflared
```

**macOS:**

```bash
brew install cloudflared
```

**Linux:**

```bash
# Download from GitHub releases
wget https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-linux-amd64
chmod +x cloudflared-linux-amd64
sudo mv cloudflared-linux-amd64 /usr/local/bin/cloudflared
```

Or visit: https://developers.cloudflare.com/cloudflare-one/connections/connect-apps/install-and-setup/installation/

Verify installation:

```bash
cloudflared --version
```

## Step 1: Add Domain to Cloudflare

1. Log in to your [Cloudflare dashboard](https://dash.cloudflare.com/)
2. Click **Add a Site**
3. Enter `datacrew.space` and click **Add site**
4. Select the **Free** plan and click **Continue**
5. Cloudflare will scan your existing DNS records automatically
6. **DO NOT** click Continue yet - proceed to Step 2 first to verify and copy records

## Step 2: Copy DNS Records (CRITICAL - Prevents Email/Website Issues)

⚠️ **IMPORTANT:** Before switching nameservers, you must copy all existing DNS records to Cloudflare to prevent service interruptions, especially email.

### Configuration Challenge: DNS Record Migration

**Issue:** When switching nameservers to Cloudflare, existing DNS records must be copied to prevent service interruption.

**Solution:**
- Created comprehensive guide for copying DNS records before switching
- Automated script (`setup_dns.py`) to bulk-add DNS records
- Verification steps using MXToolbox before switching nameservers

**Lessons Learned:**
- Always copy ALL DNS records before switching nameservers
- Email records are critical - missing them breaks email delivery
- Custom service records (Postman, Domo, Circle) also need to be migrated

### 2.1: View Current DNS Records

**From Squarespace:**

1. Log in to your Squarespace account
2. Go to **Settings** → **Domains** → **datacrew.space** → **DNS Settings**
3. Take a screenshot or write down ALL DNS records

**From Google Workspace Admin (if using Google Workspace email):**

1. Log in to [Google Admin Console](https://admin.google.com/)
2. Go to **Apps** → **Google Workspace** → **Gmail**
3. Navigate to **Email routing** or **DNS settings**
4. Note all MX, SPF, DKIM, and DMARC records

**Using MXToolbox (Recommended for verification):**

1. Visit [MXToolbox](https://mxtoolbox.com/)
2. Enter `datacrew.space` and run:
   - **MX Lookup** - Shows mail server records
   - **DNS Lookup** - Shows all DNS records
   - **SPF Record Lookup** - Shows SPF records
   - **DMARC Lookup** - Shows DMARC records
3. Save or screenshot all results

### 2.2: Copy Records to Cloudflare

**Option A: Automated via CLI (Recommended)**

Use the automated script to add all DNS records:

1. **Get Cloudflare API Token:**

   - Go to https://dash.cloudflare.com/profile/api-tokens
   - Click **Create Token**
   - Use **Edit zone DNS** template
   - Select your zone (`datacrew.space`)
   - Copy the token

2. **Run the script:**

   ```bash
   python setup/cloudflare/setup_dns.py
   ```

3. The script will:

   - Automatically get your Zone ID
   - Add all DNS records (MX, TXT, CNAME, A records)
   - Skip records that already exist
   - Set correct proxy settings (MX records DNS only, others as configured)

4. **After running, you still need to:**
   - Add DKIM record from Google Workspace Admin Console (manual)
   - Add DMARC record if you have one (manual)
   - Verify all MX records are DNS only (grey cloud) in dashboard

**Option B: Manual via Dashboard**

In the Cloudflare dashboard (where you added the domain):

1. Review the DNS records Cloudflare detected automatically
2. **Manually verify and add any missing records**, especially:

   **Email Records (Google Workspace):**

   - **MX Records** - You need 5 MX records with these exact values:
     - Priority 1: `aspmx.l.google.com`
     - Priority 5: `alt1.aspmx.l.google.com`
     - Priority 5: `alt2.aspmx.l.google.com`
     - Priority 10: `alt3.aspmx.l.google.com`
     - Priority 10: `alt4.aspmx.l.google.com`
     - **Important:** All MX records must be set to **DNS only** (grey cloud) in Cloudflare
   - **TXT Records** - Google site verification (e.g., `google-site-verification=...`)
   - **TXT Records** - SPF record (e.g., `v=spf1 include:_spf.google.com ~all`)
   - **TXT Records** - DKIM record (from Google Admin Console)
   - **TXT Records** - DMARC record (e.g., `v=DMARC1; p=none; rua=mailto:...`)
   - **Note:** Multiple TXT records with the same name (`@`) are allowed and will appear as separate records in Cloudflare

   **Website Records:**

   - **A Records** - For your main website
   - **CNAME Records** - For subdomains (www, etc.)
   - **TXT Records** - Any verification records

   **Custom Service Records:**

   - **Postman API** - CNAME records for Postman API hosting
   - **Domo Library** - A records for Domo library service
   - **Circle Community** - CNAME record for Circle community platform
   - **Postman Verification** - TXT record for Postman domain verification

   **Squarespace Domain Connect (Optional but recommended):**

   - **CNAME Record** - `_domainconnect` → `_domainconnect.domains.squarespace.com`
     - This allows Squarespace to manage your domain settings
     - You can keep this if you want Squarespace integration, or remove it if not needed

3. For each record Cloudflare didn't detect:

   - Click **Add record**
   - Select the correct **Type** (A, CNAME, MX, TXT, etc.)
   - Enter the **Name** (use `@` for root domain, or subdomain name)
   - Enter the **Content/Value** exactly as it appears in Squarespace/Google
   - For MX records, enter the **Priority** value
   - Click **Save**

4. **Double-check all records match exactly** - Typos will break services!

### 2.3: Verify Records Before Switching

Before updating nameservers, verify your records are correct:

1. In Cloudflare, go to **DNS** → **Records**
2. Compare each record with your saved records from Squarespace/Google
3. Use [MXToolbox](https://mxtoolbox.com/) to verify:
   - Cloudflare should show your records (may take a few minutes)
   - All MX, SPF, DKIM, DMARC records should match

**Google Workspace MX Records (for datacrew.space):**

```text
Type: MX
Name: @
Priority: 1
Content: aspmx.l.google.com

Type: MX
Name: @
Priority: 5
Content: alt1.aspmx.l.google.com

Type: MX
Name: @
Priority: 5
Content: alt2.aspmx.l.google.com

Type: MX
Name: @
Priority: 10
Content: alt3.aspmx.l.google.com

Type: MX
Name: @
Priority: 10
Content: alt4.aspmx.l.google.com
```

**Additional Google Workspace Records to Add:**

```text
Type: TXT
Name: @
Content: google-site-verification=uZqWkV9T5euAZHiQiy3IZd9lc3iErKCzCkM4Vdk7wRE

Type: TXT
Name: @
Content: v=spf1 include:_spf.google.com ~all

Type: TXT
Name: google._domainkey
Content: (your DKIM key from Google Admin - get this from Google Workspace Admin Console)

Type: TXT
Name: _dmarc
Content: v=DMARC1; p=none; rua=mailto:your-email@datacrew.space
```

**Note:** You can have multiple TXT records with the same name (`@`). Cloudflare will show them as separate records, which is correct.

**Squarespace Domain Connect Record (Optional):**

```text
Type: CNAME
Name: _domainconnect
Content: _domainconnect.domains.squarespace.com
```

**Custom Service Records (for datacrew.space):**

```text
Type: CNAME
Name: api
Content: phs.getpostman.com

Type: A
Name: domolibrary
Content: 185.199.108.153

Type: A
Name: domolibrary
Content: 185.199.109.153

Type: TXT
Name: @
Content: postman-domain-verification=9fdabc206f5846514ace93f25cf690ab1afb756f866014a4d323c89928cc7d800d5d558dcc24954542eb8c96b604c3b71874a7f77f60e79b7b145e19b6457b0e

Type: CNAME
Name: community
Content: datacrew.circle.so

Type: CNAME
Name: api.datacrew.space
Content: phs.getpostman.com
```

**Note on `api` and `api.datacrew.space` CNAME records:**

- You have both `api` CNAME and `api.datacrew.space` CNAME pointing to the same destination
- In Cloudflare, you only need **one** `api` CNAME record (Cloudflare automatically appends the domain)
- When adding to Cloudflare:
  - Type: CNAME
  - Name: `api` (not `api.datacrew.space`)
  - Content: `phs.getpostman.com`
- Cloudflare will automatically make this work for both `api.datacrew.space` and `api` subdomain
- You can remove the duplicate `api.datacrew.space` record if it exists

**Important Notes:**

- All MX records must be set to **DNS only** (grey cloud icon) in Cloudflare - do NOT proxy them
- The `_domainconnect` CNAME can be proxied (orange cloud) or DNS only - either works
- Custom service records (Postman, Domo, Circle) can be proxied (orange cloud) for DDoS protection, or DNS only - your choice
- For `domolibrary` with two A records: Cloudflare allows multiple A records with the same name - add both IP addresses as separate records
- TTL can be set to "Auto" in Cloudflare (it will use Cloudflare's default)
- Priority values (1, 5, 5, 10, 10) must match exactly
- The `@` symbol means the root domain (datacrew.space)
- The `_domainconnect` record is used by Squarespace for domain management - you can keep it if you use Squarespace features, or remove it if not needed
- Multiple TXT records with the same name (`@`) are allowed - add them as separate records

## Step 3: Update Nameservers in Squarespace

⚠️ **Only proceed after verifying all DNS records are correctly copied in Step 2!**

Cloudflare will provide you with two nameservers (e.g., `alice.ns.cloudflare.com` and `bob.ns.cloudflare.com`).

1. In Cloudflare dashboard, note the two nameservers shown (usually at the top of the DNS page)
2. Log in to your Squarespace account
3. Go to **Settings** → **Domains** → **datacrew.space**
4. Click **Use Squarespace Nameservers** (if enabled) and switch to **Use Third-Party Nameservers**
5. Enter the two Cloudflare nameservers exactly as provided
6. Save the changes

**Note:** DNS propagation can take up to 24 hours, but usually completes within 2-4 hours.

### DNS Propagation Handling

**Challenge:** DNS changes can take up to 24 hours to propagate.

**Solution:**
- Document expected propagation times
- Provide verification commands and tools
- Set expectations in setup guide
- Use DNS checker tools to verify propagation

## Step 4: Verify Everything Works

After updating nameservers, wait 15-30 minutes, then verify:

### 4.1: Verify DNS Propagation

1. Use [MXToolbox DNS Propagation Checker](https://mxtoolbox.com/DNSLookup.aspx)
2. Enter `datacrew.space`
3. Check that records show Cloudflare's nameservers
4. Verify all your DNS records are present

### 4.2: Verify Website

1. Visit `https://datacrew.space` (or your main website URL)
2. Confirm it loads correctly
3. Check that SSL certificate is valid (Cloudflare provides free SSL)

### 4.3: Verify Email (Google Workspace)

1. **Send a test email** to an external address (e.g., Gmail)
2. **Receive a test email** from an external address
3. Check [Google Admin Console](https://admin.google.com/) → **Apps** → **Google Workspace** → **Gmail** → **Email routing**
4. Verify no delivery issues are reported

**If email is not working:**

- Double-check MX records in Cloudflare match Google's requirements
- Verify SPF, DKIM, and DMARC records are correct
- Wait a bit longer for DNS propagation (can take up to 24 hours)
- Check Google Workspace admin console for any errors

### 4.4: Verify Cloudflare Status

1. In Cloudflare dashboard, check that your domain shows as **Active**
2. SSL/TLS encryption mode should be set (default is fine)
3. Verify DNS record proxy status:
   - **Email records (MX, TXT for SPF/DKIM/DMARC)**: Must be **DNS only** (grey cloud icon) - click the orange cloud to toggle
   - **Website records (A, CNAME)**: Can be **Proxied** (orange cloud) for DDoS protection
   - **Important:** If email records are proxied, email will break!

**To fix email records if they're proxied:**

1. Go to **DNS** → **Records** in Cloudflare
2. Find all MX records and TXT records related to email (SPF, DKIM, DMARC)
3. Click the orange cloud icon to make them **DNS only** (grey cloud)
4. Wait a few minutes for changes to propagate

### Configuration Challenge: Email Records Must Be DNS Only

**Issue:** MX, SPF, DKIM, and DMARC records must be set to "DNS only" (grey cloud) in Cloudflare, not proxied.

**Solution:**
- All email-related DNS records are explicitly set to DNS only
- Created automated script (`setup_dns.py`) to ensure correct proxy settings
- Documented in setup guide with clear warnings

**Why:** Email servers need direct DNS resolution, not proxied traffic.

## Step 5: Set Up Google Workspace Email Authentication (SPF, DKIM, DMARC)

⚠️ **CRITICAL:** DMARC relies on SPF and DKIM to work correctly. **You must set up SPF and DKIM first** before adding DMARC. If you enable DMARC without SPF and DKIM properly configured, it can block your legitimate emails.

### Configuration Challenge: DMARC Setup Sequence

**Issue:** DMARC must be set up after SPF and DKIM, or it can block legitimate emails.

**Solution:**
- Documented phased approach: SPF → DKIM → DMARC
- Start with `p=none` (monitoring mode) for safety
- Gradual enforcement: `p=none` → `p=quarantine` → `p=reject`
- Clear warnings in documentation about setup order

**Why:** DMARC relies on SPF and DKIM to authenticate emails. If they're not set up first, DMARC will fail authentication.

### Phase 1: The Safety Check (Set Up SPF and DKIM First)

#### Step 5.1: Verify/Add SPF Record

1. **Check if SPF record exists:**

   - In Cloudflare, go to **DNS** → **Records**
   - Look for a TXT record with name `@` containing `v=spf1 include:_spf.google.com`
   - If it doesn't exist, add it:

2. **Add SPF Record in Cloudflare:**

   - Click **Add record**
   - **Type:** `TXT`
   - **Name:** `@`
   - **Content:** `v=spf1 include:_spf.google.com ~all`
   - **Proxy status:** DNS only (grey cloud) - **DO NOT proxy this**
   - Click **Save**

3. **Verify SPF record:**
   - Use [MXToolbox SPF Record Lookup](https://mxtoolbox.com/spf.aspx)
   - Enter `datacrew.space`
   - Verify the record shows: `v=spf1 include:_spf.google.com ~all`

#### Step 5.2: Set Up DKIM (DomainKeys Identified Mail)

1. **Generate DKIM Key in Google Workspace:**

   - Log in to [Google Admin Console](https://admin.google.com/)
   - Go to **Apps** → **Google Workspace** → **Gmail**
   - Click **Authenticate email** (or navigate to **Email routing** → **Authenticate email**)
   - If a DKIM key doesn't exist, click **Generate new record**
   - Google will generate a TXT record for you

2. **Copy the DKIM Record:**

   - Google will show you:
     - **Host name:** `google._domainkey` (or similar)
     - **TXT record value:** A long string starting with `v=DKIM1; k=rsa; p=...`
   - **Important:** Copy the entire TXT record value exactly as shown

3. **Add DKIM Record to Cloudflare:**

   - In Cloudflare, go to **DNS** → **Records**
   - Click **Add record**
   - **Type:** `TXT`
   - **Name:** `google._domainkey` (use exactly what Google provided)
   - **Content:** Paste the entire DKIM value from Google (the long string)
   - **Proxy status:** DNS only (grey cloud) - **DO NOT proxy this**
   - Click **Save**

4. **Start Authentication in Google:**

   - **Important:** After adding the DNS record, wait 5-10 minutes for DNS propagation
   - Go back to Google Admin Console → **Apps** → **Google Workspace** → **Gmail** → **Authenticate email**
   - Click **Start Authentication** button
   - Google will verify the DNS record and start signing your emails

5. **Verify DKIM is Working:**
   - Wait 24-48 hours after starting authentication
   - Send a test email to an external address (e.g., Gmail)
   - Check the email headers - you should see `DKIM-Signature` header
   - Or use [MXToolbox Email Health Check](https://mxtoolbox.com/emailhealth/datacrew.space/) to verify

### Phase 2: Add DMARC Record (Only After SPF and DKIM Are Set Up)

⚠️ **DO NOT add DMARC until SPF and DKIM are verified and working!**

Once both SPF and DKIM are set up and verified:

1. **Add DMARC Record in Cloudflare:**

   - In Cloudflare, go to **DNS** → **Records**
   - Click **Add record**
   - **Type:** `TXT`
   - **Name:** `_dmarc` (Cloudflare will automatically append your domain)
   - **Content:** `v=DMARC1; p=none; rua=mailto:admin@datacrew.space`
     - Replace `admin@datacrew.space` with the email where you want to receive DMARC reports
   - **Proxy status:** DNS only (grey cloud) - **DO NOT proxy this**
   - Click **Save**

2. **Verify DMARC Record:**
   - Use [MXToolbox DMARC Lookup](https://mxtoolbox.com/dmarc.aspx)
   - Enter `datacrew.space`
   - Verify the record is found and shows your policy

### Phase 3: Monitor and Gradually Enforce

#### Understanding DMARC Policy Levels

- **`p=none`** (Monitoring Mode - Start Here):

  - ✅ Fixes the MXToolbox warning
  - ✅ Does NOT block any emails
  - ✅ Sends you daily reports about email authentication
  - ✅ Safe to use immediately

- **`p=quarantine`** (Intermediate):

  - Emails that fail authentication go to spam folder
  - Use this after monitoring for a few weeks

- **`p=reject`** (Strict):
  - Emails that fail authentication are rejected
  - Only use this after you're 100% sure all legitimate email passes

#### Monitoring Process

1. **Monitor Reports (2-4 weeks):**

   - Check the email address you specified in `rua=mailto:...` for daily DMARC reports
   - These reports show which emails passed/failed authentication
   - Look for legitimate emails (from your billing software, marketing tools, etc.) that are failing

2. **Fix Any Issues:**

   - If legitimate emails are failing SPF, add their sending servers to your SPF record
   - Example: `v=spf1 include:_spf.google.com include:mailgun.org ~all` (if using Mailgun)
   - If DKIM is failing, verify the DKIM key is correct in DNS

3. **Gradually Enforce:**
   - After 2-4 weeks of monitoring with no issues:
   - Change `p=none` to `p=quarantine` (test for another week)
   - If still no issues, change to `p=reject` (full enforcement)

### Quick Reference: DMARC Record Examples

**Monitoring Mode (Start Here):**

```text
v=DMARC1; p=none; rua=mailto:admin@datacrew.space
```

**With Reporting and Feedback:**

```text
v=DMARC1; p=none; rua=mailto:admin@datacrew.space; ruf=mailto:admin@datacrew.space; fo=1
```

**Quarantine Mode (After Monitoring):**

```text
v=DMARC1; p=quarantine; rua=mailto:admin@datacrew.space
```

**Reject Mode (Full Enforcement):**

```text
v=DMARC1; p=reject; rua=mailto:admin@datacrew.space
```

### Email Health Monitoring

**Solution:** Use MXToolbox for ongoing email health monitoring.

**Process:**
1. Regular checks at https://mxtoolbox.com/emailhealth/datacrew.space/
2. Address warnings and errors promptly
3. Monitor DMARC reports (when enabled)
4. Document fixes in this file

### Additional Resources

- [How to Setup Google Workspace SPF, DKIM, DMARC Records (Video)](https://www.youtube.com/watch?v=P17CtUQcHA0)
- [MXToolbox Email Health Check](https://mxtoolbox.com/emailhealth/datacrew.space/)
- [Google Workspace Email Authentication Guide](https://support.google.com/a/answer/174124)

## Step 6: Create a Cloudflare Tunnel

1. In the Cloudflare dashboard, go to **Zero Trust** (or visit [one.dash.cloudflare.com](https://one.dash.cloudflare.com/))
2. If this is your first time, you'll need to set up Zero Trust (it's free)
3. Navigate to **Networks** → **Tunnels**
4. Click **Create a tunnel**
5. Select **Cloudflared** as the connector type
6. Give your tunnel a name (e.g., `datacrew-services`)
7. Click **Save tunnel**

## Step 7: Generate Tunnel Token

1. After creating the tunnel, you'll see a **Token** field
2. Click **Copy** to copy the token
3. **Important:** Save this token securely - you'll need it for your `.env` file

The token will look something like:

```
eyJhIjoi...very-long-token-string...xyz123
```

### Configuration Challenge: Tunnel Token Management

**Issue:** Tunnel tokens are long and need to be securely stored in `.env` file.

**Solution:**
- Token stored in `.env` file (not committed to git)
- Automated setup script generates and updates token
- Clear instructions for manual token retrieval if needed

**Future Consideration:** Consider using Infisical for tunnel token storage.

## Step 8: Configure Tunnel Routes

After creating the tunnel, you need to configure public hostnames (routes) for each service:

1. In the tunnel details page, click **Configure** under **Public Hostnames**
2. Click **Add a public hostname**
3. For each service, add a route:

### N8N

- **Subdomain:** `n8n`
- **Domain:** `datacrew.space`
- **Service Type:** `HTTP`
- **URL:** `http://caddy:80`
- **Additional Settings:**
  - **Host Header:** `n8n.datacrew.space`
  - Click **Save hostname**

### Open WebUI

- **Subdomain:** `webui`
- **Domain:** `datacrew.space`
- **Service Type:** `HTTP`
- **URL:** `http://caddy:80`
- **Host Header:** `webui.datacrew.space`
- Click **Save hostname**

### Flowise

- **Subdomain:** `flowise`
- **Domain:** `datacrew.space`
- **Service Type:** `HTTP`
- **URL:** `http://caddy:80`
- **Host Header:** `flowise.datacrew.space`
- Click **Save hostname**

### Langfuse

- **Subdomain:** `langfuse`
- **Domain:** `datacrew.space`
- **Service Type:** `HTTP`
- **URL:** `http://caddy:80`
- **Host Header:** `langfuse.datacrew.space`
- Click **Save hostname**

### Supabase

- **Subdomain:** `supabase`
- **Domain:** `datacrew.space`
- **Service Type:** `HTTP`
- **URL:** `http://caddy:80`
- **Host Header:** `supabase.datacrew.space`
- Click **Save hostname**

### Neo4j

- **Subdomain:** `neo4j`
- **Domain:** `datacrew.space`
- **Service Type:** `HTTP`
- **URL:** `http://caddy:80`
- **Host Header:** `neo4j.datacrew.space`
- Click **Save hostname**

### ComfyUI

- **Subdomain:** `comfyui`
- **Domain:** `datacrew.space`
- **Service Type:** `HTTP`
- **URL:** `http://caddy:80`
- **Host Header:** `comfyui.datacrew.space`
- Click **Save hostname**

### Configuration Challenge: Hostname Configuration

**Issue:** Services need hostnames configured in both Caddy and Cloudflare Tunnel.

**Solution:**
- Environment variables for each service hostname (e.g., `N8N_HOSTNAME=n8n.datacrew.space`)
- Caddy reads hostnames from environment variables
- Cloudflare Tunnel routes configured with matching hostnames
- Automated script (`setup/cloudflare/configure_hostnames.py`) to sync configurations

**Why:** Ensures consistency between Caddy routing and Cloudflare Tunnel routing.

## Step 9: Configure Environment Variables

1. Create a `.env` file in the project root (copy from `.env.example` if it exists)
2. Add your Cloudflare Tunnel token:

```bash
CLOUDFLARE_TUNNEL_TOKEN=your-token-here
```

3. Configure all hostname environment variables:

```bash
############
# Caddy Hostname Configuration (for datacrew.space)
############
N8N_HOSTNAME=n8n.datacrew.space
WEBUI_HOSTNAME=webui.datacrew.space
FLOWISE_HOSTNAME=flowise.datacrew.space
SUPABASE_HOSTNAME=supabase.datacrew.space
OLLAMA_HOSTNAME=ollama.datacrew.space
SEARXNG_HOSTNAME=searxng.datacrew.space
LANGFUSE_HOSTNAME=langfuse.datacrew.space
NEO4J_HOSTNAME=neo4j.datacrew.space
COMFYUI_HOSTNAME=comfyui.datacrew.space
```

**Note:** For local development without Cloudflare Tunnel, you can use port-based hostnames:

```bash
N8N_HOSTNAME=:8001
WEBUI_HOSTNAME=:8002
# etc.
```

### Configuration Files

**Key Files:**
- `Caddyfile` - Caddy reverse proxy configuration
- `.env` - Environment variables (hostnames, tunnel token)
- `docker-compose.yml` - Service definitions
- Cloudflare Dashboard - Tunnel and DNS configuration

**Environment Variables:**
- `CLOUDFLARE_TUNNEL_TOKEN` - Tunnel authentication token
- `N8N_HOSTNAME`, `WEBUI_HOSTNAME`, etc. - Service hostnames

## Step 10: Start Services

1. Make sure your `.env` file is configured with all required variables (see README.md for the complete list)
2. Start the services with your preferred profile:

```bash
python start_services.py --profile gpu-nvidia
```

Or for CPU-only:

```bash
python start_services.py --profile cpu
```

3. Verify the cloudflared container is running:

```bash
docker ps | grep cloudflared
```

4. Check cloudflared logs to ensure the tunnel is connected:

```bash
docker logs cloudflared
```

You should see messages like:

```
2024-01-01T12:00:00Z INF Connection established connIndex=0
```

## Step 11: Verify DNS and SSL

1. Wait for DNS propagation (can take a few hours)
2. Check DNS resolution:

   ```bash
   dig n8n.datacrew.space
   ```

   Or use an online tool like [dnschecker.org](https://dnschecker.org/)

3. Once DNS has propagated, test each subdomain:

   - `https://n8n.datacrew.space`
   - `https://webui.datacrew.space`
   - `https://flowise.datacrew.space`
   - etc.

4. SSL certificates are automatically provisioned by Cloudflare - no additional configuration needed!

## Troubleshooting

### Tunnel Not Connecting

1. Verify your tunnel token is correct in `.env`
2. Check cloudflared logs: `docker logs cloudflared`
3. Ensure the cloudflared container can reach the Caddy container (they're on the same Docker network)
4. Check Cloudflare dashboard for tunnel status

### DNS Not Resolving

1. Verify nameservers are correctly set in Squarespace
2. Check DNS propagation using [dnschecker.org](https://dnschecker.org/)
3. Ensure DNS records are created in Cloudflare (they're auto-created when you add public hostnames)
4. Check DNS propagation status

### Services Not Accessible

1. Verify Caddy is running: `docker ps | grep caddy`
2. Check Caddy logs: `docker logs caddy`
3. Verify hostname environment variables are set correctly in `.env`
4. Ensure the service containers are running: `docker ps`

### Email Not Working

1. Verify MX records are DNS only (not proxied)
2. Check SPF, DKIM, DMARC records exist
3. Wait for DNS propagation
4. Verify MX records in Cloudflare match Google's requirements

### SSL Certificate Issues

Cloudflare handles SSL automatically. If you see certificate errors:

1. Ensure DNS is fully propagated
2. Check that the domain is properly added to Cloudflare
3. Verify SSL/TLS encryption mode in Cloudflare dashboard (should be "Full" or "Full (strict)")

## Solutions and Workarounds

### Automated Setup Scripts

Created several Python scripts to automate common tasks:

1. **`setup/cloudflare/setup_tunnel.py`** - Creates Cloudflare Tunnel and generates token
2. **`setup/cloudflare/setup_dns.py`** - Adds DNS records to Cloudflare (with correct proxy settings)
3. **`setup/cloudflare/setup_tunnel_routes.py`** - Configures public hostnames in tunnel
4. **`setup/cloudflare/configure_hostnames.py`** - Syncs hostname configuration
5. **`setup/cloudflare/update_env_tunnel.py`** - Updates `.env` with tunnel token
6. **`setup/cloudflare/validate_setup.py`** - Validates Cloudflare configuration

**Benefits:**
- Reduces manual errors
- Ensures consistent configuration
- Faster setup process
- Repeatable for multiple environments

## Future Considerations

### Cloud Service Integration

**Planned:** Add cloud services (e.g., RunPod for ComfyUI) to the stack.

**Approach:**
- Option 1: Proxy through Caddy (add route in Caddyfile)
- Option 2: Direct tunnel route to cloud service
- Decision will depend on service requirements

**When you're ready to add cloud services (e.g., RunPod for ComfyUI), you can:**

#### Option 1: Proxy Through Caddy

Add a new route in Cloudflare Tunnel:

- **Subdomain:** `comfyui-cloud`
- **Domain:** `datacrew.space`
- **Service Type:** `HTTP`
- **URL:** `http://caddy:80`
- **Host Header:** `comfyui-cloud.datacrew.space`

Then update your Caddyfile to proxy to the external service (see commented example in Caddyfile).

#### Option 2: Direct Tunnel Route

Create a separate route directly to the cloud service:

- **Subdomain:** `comfyui-cloud`
- **Domain:** `datacrew.space`
- **Service Type:** `HTTP`
- **URL:** `https://your-runpod-instance.runpod.net`
- **Host Header:** `your-runpod-instance.runpod.net`

### Access Control

**Consideration:** Add Cloudflare Access policies for sensitive services.

**Benefits:**
- Additional security layer
- User authentication before service access
- Audit logging

### Rate Limiting

**Consideration:** Configure WAF rate limiting in Cloudflare dashboard.

**Use Case:** Protect services from abuse and DDoS attacks.

### Monitoring and Observability

**Future Enhancement:** Set up Cloudflare Analytics and monitoring.

**Potential:**
- Traffic analytics
- Error rate monitoring
- Performance metrics

## Security Considerations

- **No port forwarding needed** - Your firewall can remain closed
- **Origin IP hidden** - Cloudflare proxies all traffic, hiding your home IP
- **DDoS protection** - Built into Cloudflare's network
- **Access control** - Consider adding Cloudflare Access policies for sensitive services
- **Rate limiting** - Configure in Cloudflare dashboard under Security → WAF

## Additional Resources

- [Cloudflare Tunnel Documentation](https://developers.cloudflare.com/cloudflare-one/connections/connect-apps/)
- [Cloudflare Zero Trust Dashboard](https://one.dash.cloudflare.com/)
- [Cloudflare Community Forums](https://community.cloudflare.com/)
- [MXToolbox Email Health Check](https://mxtoolbox.com/emailhealth/datacrew.space/)
- [Email Health Troubleshooting](./email-health.md)

