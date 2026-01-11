# Open WebUI Google OAuth Setup Guide

This guide explains how to configure Google OAuth authentication for Open WebUI, allowing users to sign in with their Google accounts.

## Overview

Open WebUI supports Google OAuth (Single Sign-On) authentication, which allows users to:
- Sign in using their Google account
- Automatically create accounts on first sign-in (if enabled)
- Use existing Google credentials without creating a separate Open WebUI account

## Prerequisites

- Google Cloud Console account
- Access to create OAuth 2.0 credentials
- Open WebUI instance accessible via a public URL (for OAuth callback)

## Step 1: Create Google OAuth Client

### 1.1 Access Google Cloud Console

1. Navigate to [Google Cloud Console](https://console.cloud.google.com/)
2. Select your project or create a new one
3. Go to **APIs & Services** → **Credentials**

### 1.2 Create OAuth 2.0 Client ID

1. Click **Create Credentials** → **OAuth client ID**
2. If prompted, configure the OAuth consent screen first:
   - **User Type**: Choose "External" (for public use) or "Internal" (for Google Workspace)
   - **App Name**: Enter a name (e.g., "Open WebUI")
   - **User support email**: Your email
   - **Developer contact**: Your email
   - Click **Save and Continue**
   - Add scopes (at minimum, `email` and `profile`)
   - Add test users if in testing mode
   - Click **Save and Continue**

### 1.3 Configure OAuth Client

1. **Application type**: Select **Web application**
2. **Name**: Give it a descriptive name (e.g., "Open WebUI OAuth Client")
3. **Authorized redirect URIs**: Add your Open WebUI callback URL:
   - **For domain access (HTTPS)**: `https://<your-openwebui-domain>/oauth/google/callback`
     - Example: `https://webui.datacrew.space/oauth/google/callback`
   - **For local development (HTTP)**: `http://<your-open-webui-domain>/oauth/google/callback`
     - Example: `http://localhost:8080/oauth/google/callback`
     - Note: Local development may have limitations with Google OAuth
   - **Important**: The redirect URI must match exactly (including protocol and port)
4. Click **Create**
5. **Save the Client ID and Client Secret** - you'll need these for configuration

## Step 2: Configure Environment Variables

### 2.1 Add to `.env` File

Add the following variables to your root `.env` file:

```bash
############
# Open WebUI Google OAuth Configuration
############
# Enable OAuth signup (allows automatic account creation on first Google sign-in)
ENABLE_OAUTH_SIGNUP=true

# Google OAuth Client ID (from Google Cloud Console)
# Note: If you already have CLIENT_ID_GOOGLE_LOGIN set (e.g., for Infisical),
# it will be automatically used. Otherwise, set GOOGLE_CLIENT_ID:
GOOGLE_CLIENT_ID=your-google-client-id.apps.googleusercontent.com
# OR reuse existing: CLIENT_ID_GOOGLE_LOGIN (already configured)

# Google OAuth Client Secret (from Google Cloud Console)
# Note: If you already have CLIENT_SECRET_GOOGLE_LOGIN set (e.g., for Infisical),
# it will be automatically used. Otherwise, set GOOGLE_CLIENT_SECRET:
GOOGLE_CLIENT_SECRET=your-google-client-secret-here
# OR reuse existing: CLIENT_SECRET_GOOGLE_LOGIN (already configured)

# OpenID Provider URL (required for proper logout functionality)
OPENID_PROVIDER_URL=https://accounts.google.com/.well-known/openid-configuration

# Merge accounts by email (optional - allows logging into account matching OAuth email)
OAUTH_MERGE_ACCOUNTS_BY_EMAIL=true

# Disable login form when OAuth signup is enabled (prevents login issues)
# Set to false if you want OAuth-only authentication
ENABLE_LOGIN_FORM=false
```

### 2.2 Security Best Practices

**For Production:**
- Store `GOOGLE_CLIENT_SECRET` in Infisical (not in `.env` file)
- Use strong, unique client secrets
- Regularly rotate OAuth credentials
- Restrict OAuth consent screen to verified domains

**For Local Development:**
- You can use `.env` file directly
- Note: Google OAuth may require HTTPS for production use

### 2.3 Using Infisical (Recommended for Production)

1. **Add secrets to Infisical:**
   ```bash
   # Access Infisical UI
   # Navigate to your project → Add secrets:
   # - GOOGLE_CLIENT_ID
   # - GOOGLE_CLIENT_SECRET
   # - ENABLE_OAUTH_SIGNUP (optional, can be in .env)
   ```

2. **Sync from Infisical:**
   ```bash
   python start_services.py --profile cpu
   # Secrets will be automatically exported to .env.infisical
   ```

## Step 3: Configure Hostname (If Using Domain)

If you're using a custom domain (e.g., `webui.datacrew.space`), ensure:

1. **Set `WEBUI_HOSTNAME` in `.env`:**
   ```bash
   WEBUI_HOSTNAME=webui.datacrew.space
   ```

2. **Verify Caddy Configuration:**
   - Check that Caddy is configured to route traffic to Open WebUI
   - Verify SSL certificate is valid

3. **Update Google OAuth Redirect URI:**
   - In Google Cloud Console, ensure the redirect URI matches your domain:
     - `https://webui.datacrew.space/oauth/google/callback`

## Step 4: Restart Open WebUI

After configuring environment variables:

```bash
# Restart Open WebUI service
cd 03-apps
docker compose restart open-webui

# Or restart the entire apps stack
python start_services.py --stack apps --action restart
```

## Step 5: Verify Configuration

### 5.1 Check Logs

```bash
docker logs open-webui | grep -i oauth
```

Look for:
- OAuth configuration loaded successfully
- No errors related to Google OAuth

### 5.2 Test Sign-In

1. Navigate to your Open WebUI instance
2. Look for a **"Sign in with Google"** button on the login page
3. Click the button and complete the OAuth flow
4. Verify that you're signed in with your Google account

## Configuration Options

### Required Environment Variables

- **`GOOGLE_CLIENT_ID`**: Your Google OAuth Client ID from Google Cloud Console
- **`GOOGLE_CLIENT_SECRET`**: Your Google OAuth Client Secret from Google Cloud Console
- **`OPENID_PROVIDER_URL`**: Set to `https://accounts.google.com/.well-known/openid-configuration` for proper logout functionality

### Optional Environment Variables

- **`ENABLE_OAUTH_SIGNUP=true`**: Allows automatic account creation when users sign in with Google for the first time
  - **Note**: When set to `true`, it's recommended to set `ENABLE_LOGIN_FORM=false` to prevent login issues
- **`OAUTH_MERGE_ACCOUNTS_BY_EMAIL=true`**: Allows logging into an account that matches the email address provided by the OAuth provider
  - **Security Note**: This can be insecure if the OAuth provider does not verify email addresses
- **`ENABLE_LOGIN_FORM=false`**: Disables the traditional login form when OAuth signup is enabled
  - Prevents confusion and login issues when using OAuth-only authentication

### Multiple OAuth Providers

**Note**: Open WebUI currently supports configuring only one OAuth provider at a time. You cannot simultaneously configure both Google and Microsoft OAuth.

## Troubleshooting

### OAuth Button Not Appearing

1. **Check environment variables:**
   ```bash
   docker exec open-webui env | grep -i google
   ```
   Verify `GOOGLE_CLIENT_ID` and `GOOGLE_CLIENT_SECRET` are set

2. **Check Open WebUI logs:**
   ```bash
   docker logs open-webui | grep -i error
   ```

3. **Verify redirect URI matches:**
   - Check Google Cloud Console → OAuth client → Authorized redirect URIs
   - Must exactly match: `https://<your-domain>/oauth/google/callback`

### "Redirect URI Mismatch" Error

- **Cause**: The redirect URI in Google Cloud Console doesn't match the actual callback URL
- **Solution**:
  1. Check your `WEBUI_HOSTNAME` environment variable
  2. Verify the redirect URI in Google Cloud Console matches exactly:
     - `https://<WEBUI_HOSTNAME>/oauth/google/callback`
  3. Ensure no trailing slashes or protocol mismatches

### "Invalid Client" Error

- **Cause**: Incorrect `GOOGLE_CLIENT_ID` or `GOOGLE_CLIENT_SECRET`
- **Solution**:
  1. Verify credentials in Google Cloud Console
  2. Check environment variables are correctly set
  3. Restart Open WebUI after updating credentials

### OAuth Works But Account Not Created

- **Cause**: `ENABLE_OAUTH_SIGNUP=false` or account creation disabled
- **Solution**: Set `ENABLE_OAUTH_SIGNUP=true` in `.env` and restart

### Local Development Issues

- **Problem**: Google OAuth may not work with `localhost` in production OAuth clients
- **Solution**:
  - Use a domain with proper SSL (recommended)
  - Or create a separate OAuth client for local development
  - Or use port forwarding with a service like ngrok for testing

## Security Considerations

1. **Client Secret Security**:
   - Never commit `GOOGLE_CLIENT_SECRET` to version control
   - Use Infisical or similar secret management for production
   - Rotate secrets periodically

2. **OAuth Consent Screen**:
   - Verify your domain in Google Cloud Console
   - Use "Internal" user type for Google Workspace organizations
   - Restrict access to verified domains

3. **HTTPS Required**:
   - Google OAuth requires HTTPS for production use
   - Ensure your domain has a valid SSL certificate
   - Caddy automatically handles SSL via Let's Encrypt

## Integration with Existing Features

Google OAuth works seamlessly with:
- **PostgreSQL Storage**: User accounts are stored in PostgreSQL
- **Conversation Memory**: Conversations are linked to OAuth-authenticated users
- **MCP Tools**: All MCP tools work with OAuth-authenticated users
- **Topic Classification**: Topics are associated with user accounts

## References

- [Open WebUI SSO Documentation](https://docs.openwebui.com/features/sso/)
- [Google OAuth 2.0 Documentation](https://developers.google.com/identity/protocols/oauth2)
- [Google Cloud Console](https://console.cloud.google.com/)

## Next Steps

After setting up Google OAuth:
1. Test sign-in with multiple Google accounts
2. Verify user data is stored correctly in PostgreSQL
3. Test conversation export and topic classification with OAuth users
4. Configure additional OAuth providers if needed (requires Open WebUI update)
