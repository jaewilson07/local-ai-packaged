# Google SSO Setup for Infisical

## Overview

This guide documents the Google OAuth2 Single Sign-On (SSO) configuration for Infisical.

## Configuration Details

### Google OAuth2 Application

- **Client ID**: `YOUR_CLIENT_ID_HERE.apps.googleusercontent.com`
- **Project ID**: `homehub-483300`
- **Application Type**: Web Application

### Environment Variables

The following environment variables have been configured in `.env`:

```bash
CLIENT_ID_GOOGLE_LOGIN=YOUR_CLIENT_ID_HERE.apps.googleusercontent.com
CLIENT_SECRET_GOOGLE_LOGIN=YOUR_CLIENT_SECRET_HERE
INFISICAL_SITE_URL=https://infisical.datacrew.space
```

## Setup Steps Completed

1. ✅ Extracted Google OAuth2 credentials from client secret JSON file
2. ✅ Added `CLIENT_ID_GOOGLE_LOGIN` to `.env`
3. ✅ Added `CLIENT_SECRET_GOOGLE_LOGIN` to `.env`
4. ✅ Restarted Infisical backend to apply changes

## Required Google Cloud Console Configuration

### Authorized Redirect URIs

You **must** configure the following redirect URIs in your Google Cloud Console OAuth2 application:

1. **For Public Access** (via Cloudflare Tunnel):
   ```
   https://infisical.datacrew.space/api/v1/sso/google
   ```

2. **For Local Development**:
   ```
   http://localhost:8080/api/v1/sso/google
   ```

### Steps to Configure in Google Cloud Console

1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Navigate to **APIs & Services** > **Credentials**
3. Find your OAuth 2.0 Client ID: `YOUR_CLIENT_ID_HERE.apps.googleusercontent.com`
4. Click **Edit**
5. Under **Authorized redirect URIs**, add:
   - `https://infisical.datacrew.space/api/v1/sso/google`
   - `http://localhost:8080/api/v1/sso/google` (optional, for local dev)
6. Click **Save**

## Enabling Google SSO in Infisical

### Via Web UI

1. Access Infisical at: `https://infisical.datacrew.space`
2. Log in as an administrator
3. Navigate to **Organization Settings** > **Authentication**
4. Enable **Google SSO**
5. The Client ID and Client Secret are already configured via environment variables

### Via CLI

The Infisical CLI will automatically use Google SSO when configured:

```bash
# Interactive login (opens browser)
infisical login

# Non-interactive login (for containers/CI)
infisical login -i
```

## Testing the Configuration

### 1. Verify Infisical Backend is Running

```bash
docker logs infisical-backend --tail 20
```

### 2. Check Environment Variables

```bash
docker exec infisical-backend env | grep -E "CLIENT_ID_GOOGLE_LOGIN|SITE_URL"
```

### 3. Test Login via CLI

```bash
# Standard login (opens browser)
infisical login

# Container/headless login
infisical login -i
```

### 4. Test Login via Web UI

1. Navigate to `https://infisical.datacrew.space`
2. Click **Sign in with Google**
3. Authenticate with your Google account
4. You should be redirected back to Infisical

## Troubleshooting

### Error: "Redirect URI Mismatch"

**Cause**: The redirect URI in Google Cloud Console doesn't match the configured site URL.

**Solution**:
1. Check your `INFISICAL_SITE_URL` in `.env`
2. Ensure the redirect URI in Google Cloud Console matches: `{INFISICAL_SITE_URL}/api/v1/sso/google`
3. Wait a few minutes for Google's changes to propagate

### Error: "Invalid Client ID or Secret"

**Cause**: The environment variables are not being read by Infisical.

**Solution**:
```bash
# Restart Infisical backend
docker restart infisical-backend

# Verify environment variables are set
docker exec infisical-backend env | grep CLIENT_ID_GOOGLE_LOGIN
```

### Error: "SSO Not Enabled"

**Cause**: Google SSO is not enabled in Infisical organization settings.

**Solution**:
1. Log in to Infisical web UI as an admin
2. Go to **Organization Settings** > **Authentication**
3. Enable **Google SSO**

## Security Considerations

### Client Secret Protection

- ✅ Client secret is stored in `.env` (git-ignored)
- ✅ Never commit `.env` to version control
- ⚠️ Consider syncing to Infisical for centralized secret management:
  ```bash
  python3 00-infrastructure/scripts/sync-env-to-infisical.py
  ```

### Authorized Domains

Ensure only trusted domains are configured in Google Cloud Console:
- **Authorized JavaScript origins**: `https://infisical.datacrew.space`
- **Authorized redirect URIs**: `https://infisical.datacrew.space/api/v1/sso/google`

### User Access Control

After enabling Google SSO:
1. Configure organization-level access controls in Infisical
2. Set up role-based access control (RBAC)
3. Review and approve new user sign-ups

## Automation Script

The setup was automated using:

```bash
python3 00-infrastructure/scripts/setup-google-sso.py \
  --client-secret-file /path/to/client_secret.json
```

### Script Options

```bash
# Basic setup
python3 setup-google-sso.py --client-secret-file <path>

# Custom site URL
python3 setup-google-sso.py --client-secret-file <path> --site-url https://your-domain.com

# Sync to Infisical
python3 setup-google-sso.py --client-secret-file <path> --sync-to-infisical

# Skip restart
python3 setup-google-sso.py --client-secret-file <path> --no-restart
```

## Related Documentation

- [Infisical Google SSO Documentation](https://infisical.com/docs/documentation/platform/sso/google)
- [Google OAuth2 Setup Guide](https://developers.google.com/identity/protocols/oauth2)
- [Infisical CLI Usage](https://infisical.com/docs/cli/usage)
- [Infrastructure Stack Overview](./INFRASTRUCTURE_STATUS.md)

## Maintenance

### Rotating Client Secret

If you need to rotate the Google OAuth2 client secret:

1. Generate a new client secret in Google Cloud Console
2. Download the new `client_secret_*.json` file
3. Run the setup script again:
   ```bash
   python3 00-infrastructure/scripts/setup-google-sso.py \
     --client-secret-file /path/to/new_client_secret.json
   ```
4. The script will update the `.env` file and restart Infisical

### Disabling Google SSO

To disable Google SSO:

1. Remove from Infisical web UI: **Organization Settings** > **Authentication**
2. Optionally remove environment variables from `.env`:
   ```bash
   # Remove these lines from .env
   CLIENT_ID_GOOGLE_LOGIN=...
   CLIENT_SECRET_GOOGLE_LOGIN=...
   ```
3. Restart Infisical backend:
   ```bash
   docker restart infisical-backend
   ```

---

**Last Updated**: 2026-01-04  
**Configured By**: Automated setup script  
**Status**: ✅ Active
