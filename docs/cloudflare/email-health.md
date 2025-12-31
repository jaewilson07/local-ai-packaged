# Email Health Troubleshooting Guide for datacrew.space

This guide helps you diagnose and fix email health issues reported by MXToolbox.

## Quick Diagnostic Steps

### Step 1: Check Current Email Health Status

1. Visit [MXToolbox Email Health Check](https://mxtoolbox.com/emailhealth/datacrew.space/)
2. Review the report and note all **Errors** and **Warnings**
3. Common issues include:
   - Missing or incorrect MX records
   - Missing SPF record
   - Missing DKIM record
   - Missing DMARC record
   - MX records being proxied (should be DNS only)
   - Blacklist issues
   - Mail server connectivity problems

### Step 2: Verify DNS Records in Cloudflare

1. Log in to [Cloudflare Dashboard](https://dash.cloudflare.com/)
2. Select your domain `datacrew.space`
3. Go to **DNS** → **Records**
4. Verify the following records exist:

#### Required MX Records (Google Workspace)

All MX records must be set to **DNS only** (grey cloud icon):

- **Type:** MX | **Name:** @ | **Priority:** 1 | **Content:** `aspmx.l.google.com` | **Proxy:** ❌ DNS only
- **Type:** MX | **Name:** @ | **Priority:** 5 | **Content:** `alt1.aspmx.l.google.com` | **Proxy:** ❌ DNS only
- **Type:** MX | **Name:** @ | **Priority:** 5 | **Content:** `alt2.aspmx.l.google.com` | **Proxy:** ❌ DNS only
- **Type:** MX | **Name:** @ | **Priority:** 10 | **Content:** `alt3.aspmx.l.google.com` | **Proxy:** ❌ DNS only
- **Type:** MX | **Name:** @ | **Priority:** 10 | **Content:** `alt4.aspmx.l.google.com` | **Proxy:** ❌ DNS only

#### Required TXT Records

All TXT records must be set to **DNS only** (grey cloud icon):

- **Type:** TXT | **Name:** @ | **Content:** `v=spf1 include:_spf.google.com ~all` | **Proxy:** ❌ DNS only
- **Type:** TXT | **Name:** `google._domainkey` | **Content:** (your DKIM key from Google) | **Proxy:** ❌ DNS only
- **Type:** TXT | **Name:** `_dmarc` | **Content:** `v=DMARC1; p=none; rua=mailto:admin@datacrew.space` | **Proxy:** ❌ DNS only

## Common Issues and Fixes

### Issue 1: MX Records Are Proxied (Orange Cloud)

**Symptom:** Email not working, MXToolbox shows mail server errors

**Fix:**
1. In Cloudflare DNS → Records, find all MX records
2. If they show an **orange cloud** icon, click it to toggle to **grey cloud** (DNS only)
3. Wait 5-10 minutes for changes to propagate
4. Re-check MXToolbox

### Issue 2: Missing SPF Record

**Symptom:** MXToolbox shows "SPF Record Not Found" or "SPF Record Invalid"

**Fix:**
1. In Cloudflare DNS → Records, click **Add record**
2. **Type:** `TXT`
3. **Name:** `@`
4. **Content:** `v=spf1 include:_spf.google.com ~all`
5. **Proxy status:** DNS only (grey cloud) - **DO NOT proxy**
6. Click **Save**
7. Wait 5-10 minutes, then verify at [MXToolbox SPF Lookup](https://mxtoolbox.com/spf.aspx)

### Issue 3: Missing DKIM Record

**Symptom:** MXToolbox shows "DKIM Record Not Found" or "DKIM Authentication Failed"

**Fix:**
1. **Get DKIM key from Google:**
   - Log in to [Google Admin Console](https://admin.google.com/)
   - Go to **Apps** → **Google Workspace** → **Gmail** → **Authenticate email**
   - If no DKIM key exists, click **Generate new record**
   - Copy the **Host name** (usually `google._domainkey`) and **TXT record value**

2. **Add to Cloudflare:**
   - In Cloudflare DNS → Records, click **Add record**
   - **Type:** `TXT`
   - **Name:** `google._domainkey` (use exactly what Google provided)
   - **Content:** Paste the entire DKIM value from Google
   - **Proxy status:** DNS only (grey cloud) - **DO NOT proxy**
   - Click **Save**

3. **Start Authentication in Google:**
   - Wait 5-10 minutes for DNS propagation
   - Go back to Google Admin Console → **Authenticate email**
   - Click **Start Authentication**
   - Wait 24-48 hours for DKIM to become active

4. **Verify:** Use [MXToolbox DKIM Lookup](https://mxtoolbox.com/dkim.aspx)

### Issue 4: Missing DMARC Record

**Symptom:** MXToolbox shows "DMARC Record Not Found" warning

**⚠️ IMPORTANT:** Only add DMARC after SPF and DKIM are set up and working!

**Fix:**
1. In Cloudflare DNS → Records, click **Add record**
2. **Type:** `TXT`
3. **Name:** `_dmarc`
4. **Content:** `v=DMARC1; p=none; rua=mailto:admin@datacrew.space`
   - Replace `admin@datacrew.space` with your email address
5. **Proxy status:** DNS only (grey cloud) - **DO NOT proxy**
6. Click **Save**
7. Wait 5-10 minutes, then verify at [MXToolbox DMARC Lookup](https://mxtoolbox.com/dmarc.aspx)

**Note:** Start with `p=none` (monitoring mode) - this is safe and won't block emails. After monitoring for 2-4 weeks, you can gradually move to `p=quarantine` and then `p=reject`.

### Issue 5: Incorrect MX Records

**Symptom:** MXToolbox shows wrong mail servers or missing MX records

**Fix:**
1. Verify you have exactly 5 MX records with these priorities:
   - Priority 1: `aspmx.l.google.com`
   - Priority 5: `alt1.aspmx.l.google.com`
   - Priority 5: `alt2.aspmx.l.google.com`
   - Priority 10: `alt3.aspmx.l.google.com`
   - Priority 10: `alt4.aspmx.l.google.com`

2. If any are missing or incorrect:
   - Delete incorrect records
   - Add correct records using the values above
   - Ensure all are DNS only (grey cloud)

3. Verify at [MXToolbox MX Lookup](https://mxtoolbox.com/mxlookup.aspx)

### Issue 6: DNS Propagation Issues

**Symptom:** Records look correct in Cloudflare but MXToolbox shows old values

**Fix:**
1. DNS changes can take up to 24 hours to propagate globally
2. Check propagation status at [DNS Checker](https://dnschecker.org/)
3. Enter your domain and select record type (MX, TXT, etc.)
4. Wait for all locations to show the new values
5. If still not propagating after 24 hours:
   - Double-check nameservers are correctly set
   - Verify records are saved correctly in Cloudflare
   - Clear DNS cache: `ipconfig /flushdns` (Windows) or `sudo dscacheutil -flushcache` (Mac)

### Issue 7: Blacklist Issues

**Symptom:** MXToolbox shows domain or IP on blacklists

**Fix:**
1. Check which blacklists you're on at [MXToolbox Blacklist Check](https://mxtoolbox.com/blacklists.aspx)
2. Most blacklists have automatic removal processes:
   - Wait 24-48 hours (many auto-remove after a period)
   - Visit the blacklist website and request removal
   - MXToolbox provides links to removal pages
3. Prevent future blacklisting:
   - Ensure SPF, DKIM, and DMARC are properly configured
   - Don't send spam or unsolicited emails
   - Use proper email authentication

### Issue 8: Mail Server Connectivity

**Symptom:** MXToolbox shows "Mail Server Not Responding" or connection timeouts

**Fix:**
1. This is usually not an issue with Google Workspace (they handle mail servers)
2. If you see this error:
   - Verify MX records point to Google servers (not your own)
   - Check that MX records are DNS only (not proxied)
   - Wait for DNS propagation
   - Google's mail servers are highly reliable - if they're down, it's a Google issue

## Automated Fix Script

You can use the existing `setup/cloudflare/setup_dns.py` script to add missing DNS records:

```bash
python setup/cloudflare/setup_dns.py
```

This will:
- Add all MX records
- Add SPF record
- Skip records that already exist
- Set correct proxy settings (DNS only for email records)

**Note:** You still need to manually add:
- DKIM record (from Google Admin Console)
- DMARC record (if you want one)

## Verification Checklist

After making changes, verify everything:

- [ ] All 5 MX records exist and are DNS only (grey cloud)
- [ ] SPF record exists and is DNS only
- [ ] DKIM record exists and is DNS only (if using Google Workspace)
- [ ] DMARC record exists and is DNS only (optional but recommended)
- [ ] All records verified at MXToolbox
- [ ] DNS propagation complete (check at dnschecker.org)
- [ ] Test email sending works
- [ ] Test email receiving works
- [ ] No blacklist issues

## Quick Verification Commands

### Check MX Records
```bash
# Windows PowerShell
nslookup -type=MX datacrew.space

# Linux/Mac
dig MX datacrew.space
```

### Check SPF Record
```bash
# Windows PowerShell
nslookup -type=TXT datacrew.space

# Linux/Mac
dig TXT datacrew.space
```

### Check DKIM Record
```bash
# Windows PowerShell
nslookup -type=TXT google._domainkey.datacrew.space

# Linux/Mac
dig TXT google._domainkey.datacrew.space
```

### Check DMARC Record
```bash
# Windows PowerShell
nslookup -type=TXT _dmarc.datacrew.space

# Linux/Mac
dig TXT _dmarc.datacrew.space
```

## Additional Resources

- [MXToolbox Email Health Check](https://mxtoolbox.com/emailhealth/datacrew.space/)
- [Cloudflare Setup Guide](./setup.md) - Full setup documentation
- [Google Workspace Email Authentication](https://support.google.com/a/answer/174124)
- [MXToolbox Tools](https://mxtoolbox.com/) - Various DNS and email diagnostic tools

## Need Help?

If you're still experiencing issues after following this guide:

1. Check the full [Cloudflare Setup Guide](./setup.md) for detailed instructions
2. Review MXToolbox error messages carefully - they often indicate the specific problem
3. Verify all records match exactly (typos will break things)
4. Wait for DNS propagation (can take up to 24 hours)
5. Check Google Workspace Admin Console for any email delivery issues


