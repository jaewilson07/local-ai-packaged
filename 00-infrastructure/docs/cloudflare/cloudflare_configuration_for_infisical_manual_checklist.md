# Cloudflare Configuration Manual Checklist for Infisical

Since the API token lacks permissions, use this checklist to verify settings manually in the Cloudflare dashboard.

## Quick Access Links

- **Cloudflare Dashboard**: https://dash.cloudflare.com/
- **Zero Trust Dashboard**: https://one.dash.cloudflare.com/
- **API Tokens**: https://dash.cloudflare.com/profile/api-tokens

## Checklist

### ✅ 1. SSL/TLS Mode (CRITICAL)

**Location**: Dashboard → Your Domain (`datacrew.space`) → **SSL/TLS**

**Check**:
- [ ] SSL/TLS encryption mode is set to **"Full"** or **"Full (strict)"**
- [ ] **NOT** set to "Flexible" (this breaks secure cookies!)

**If wrong, fix it**:
1. Click **SSL/TLS** in sidebar
2. Under **SSL/TLS encryption mode**, select **"Full"**
3. Click **Save**

**Why**: "Flexible" mode terminates SSL at Cloudflare but sends HTTP to your origin, breaking secure cookies and sessions.

---

### ✅ 2. Page Rules for API Caching

**Location**: Dashboard → Your Domain → **Rules** → **Page Rules**

**Check**:
- [ ] There's a page rule for `infisical.datacrew.space/api/*`
- [ ] Cache Level is set to **"Bypass"**

**If missing, create it**:
1. Click **Create Page Rule**
2. **URL**: `infisical.datacrew.space/api/*`
3. **Settings**:
   - Cache Level: **Bypass** ✓
   - Disable Apps: **On** ✓
   - Disable Performance: **On** ✓
4. Click **Save and Deploy**

**Why**: API endpoints should never be cached, especially POST requests.

---

### ✅ 3. Transform Rules (Header Modifications)

**Location**: Dashboard → Your Domain → **Rules** → **Transform Rules**

**Check**:
- [ ] No Transform Rules modify headers for `infisical.datacrew.space`
- [ ] No rules remove or change `Content-Type` header

**If found, disable them**:
1. Find any rules affecting Infisical
2. Click the rule → **Edit**
3. Either:
   - **Disable** the rule, OR
   - **Remove** `Content-Type` from header modifications

**Why**: Transform Rules that modify `Content-Type` will cause HTTP 415 errors.

---

### ✅ 4. Cloudflare Access

**Location**: Zero Trust Dashboard → **Access** → **Applications**

**Check**:
- [ ] No Access application exists for `infisical.datacrew.space`
- [ ] OR if it exists, it's properly configured

**If Access is enabled and causing issues**:
1. Go to **Access** → **Applications**
2. Find application for Infisical
3. Either:
   - **Delete** it (if not needed), OR
   - **Edit** it to ensure your email is in the policy

**Why**: Cloudflare Access can interfere with Infisical's own authentication system.

---

### ✅ 5. Browser Integrity Check

**Location**: Dashboard → Your Domain → **Security** → **Settings**

**Check**:
- [ ] Browser Integrity Check is set to **"Medium"** or **"Low"**
- [ ] **NOT** set to "High" or "I'm Under Attack"

**If too strict, fix it**:
1. Go to **Security** → **Settings**
2. Find **Browser Integrity Check**
3. Set to **"Medium"**
4. Click **Save**

**Why**: Too strict settings can block legitimate browser requests.

---

### ✅ 6. Cache Settings

**Location**: Dashboard → Your Domain → **Caching** → **Configuration**

**Check**:
- [ ] Caching level is appropriate
- [ ] Browser Cache TTL is set to **"Respect Existing Headers"**

**Recommended**:
- Caching Level: **Standard**
- Browser Cache TTL: **Respect Existing Headers**

---

### ✅ 7. Purge Cache

**After making changes**:

**Location**: Dashboard → Your Domain → **Caching** → **Purge Cache**

**Action**:
1. Click **Purge Everything**
2. Wait 1-2 minutes for propagation

---

## Testing After Changes

1. **Purge Cloudflare cache** (see above)
2. **Clear browser cache and cookies** for `infisical.datacrew.space`
3. **Hard refresh**: `Ctrl+Shift+R` (Windows/Linux) or `Cmd+Shift+R` (Mac)
4. **Try logging in** to Infisical
5. **Check browser console** (F12) for errors

## Most Critical Issues

**Priority order**:

1. **SSL/TLS Mode = "Flexible"** ← Fix this FIRST!
2. **Caching enabled for `/api/*`** ← Fix this SECOND!
3. **Transform Rules modifying Content-Type** ← Fix this THIRD!

## Update API Token Permissions (Optional)

If you want to use the automated script, update your API token:

1. Go to https://dash.cloudflare.com/profile/api-tokens
2. Find your token (or create new one)
3. Add these permissions:
   - **Zone** → **Zone Settings** → **Read** + **Edit**
   - **Zone** → **Page Rules** → **Read** + **Edit**
   - **Zone** → **Cache Purge** → **Edit**
4. Save and update `.env` file with new token

Then run:
```bash
python3 utils/check-cloudflare-config.py --fix-all
```
