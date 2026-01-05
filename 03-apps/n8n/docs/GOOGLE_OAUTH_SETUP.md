# n8n Google OAuth (OIDC) Setup Guide

This guide explains how to configure Google OAuth authentication for n8n using OpenID Connect (OIDC), allowing users to sign in with their Google accounts.

## Overview

n8n supports Google OAuth via **OpenID Connect (OIDC)** for Single Sign-On (SSO) authentication, which allows users to:
- Sign in using their Google account
- Automatically create accounts on first sign-in
- Use existing Google credentials without creating a separate n8n account

**Important**: n8n OIDC is configured through the **web UI** (Settings > SSO), not environment variables. However, you can reuse your existing Google OAuth credentials (`CLIENT_ID_GOOGLE_LOGIN`, `CLIENT_SECRET_GOOGLE_LOGIN`, and `OPENID_PROVIDER_URL`).

## Prerequisites

- Google Cloud Console account with existing OAuth 2.0 credentials
- Existing environment variables: `CLIENT_ID_GOOGLE_LOGIN`, `CLIENT_SECRET_GOOGLE_LOGIN`, and `OPENID_PROVIDER_URL`
- n8n instance accessible via a public URL (for OAuth callback)
- n8n instance configured with `N8N_ENCRYPTION_KEY` and `N8N_USER_MANAGEMENT_JWT_SECRET`
- Admin access to n8n web UI

## Step 1: Configure Google Cloud Console

### 1.1 Verify Existing OAuth Credentials

You already have Google OAuth credentials configured:
- **Client ID**: `CLIENT_ID_GOOGLE_LOGIN` (from your `.env` file)
- **Client Secret**: `CLIENT_SECRET_GOOGLE_LOGIN` (from your `.env` file)
- **OpenID Provider URL**: `OPENID_PROVIDER_URL` (typically `https://accounts.google.com/.well-known/openid-configuration`)

### 1.2 Add n8n Redirect URI

1. Navigate to [Google Cloud Console](https://console.cloud.google.com/)
2. Go to **APIs & Services** → **Credentials**
3. Find your existing OAuth 2.0 Client ID (the one used for `CLIENT_ID_GOOGLE_LOGIN`)
4. Click **Edit**
5. Under **Authorized redirect URIs**, add:
   - **For domain access (HTTPS)**: `https://n8n.datacrew.space/rest/sso/oidc/callback`
     - Example: `https://n8n.datacrew.space/rest/sso/oidc/callback`
   - **For local development (HTTP)**: `http://localhost:5678/rest/sso/oidc/callback` (optional)
6. Under **Authorized JavaScript origins**, ensure you have:
   - `https://n8n.datacrew.space` (or your n8n domain)
7. Click **Save**

**Note**: The redirect URI for n8n OIDC is `/rest/sso/oidc/callback`, not `/rest/oauth2-credential/callback` (which is for workflow OAuth credentials).

## Step 2: Configure OIDC in n8n Web UI

n8n OIDC is configured through the web interface, not environment variables. Follow these steps:

### 2.1 Access n8n Settings

1. Log in to your n8n instance at `https://n8n.datacrew.space` (or your configured domain)
2. Navigate to **Settings** → **SSO** (Single Sign-On)
3. You should see the OIDC configuration section

### 2.2 Configure OIDC Settings

1. Under **Select Authentication Protocol**, choose **OIDC** from the dropdown
2. **Copy the Redirect URL** displayed by n8n (it should be: `https://n8n.datacrew.space/rest/sso/oidc/callback`)
   - Verify this matches what you added to Google Cloud Console
3. Enter the following configuration:
   - **Discovery Endpoint**: Use your `OPENID_PROVIDER_URL` value
     - Typically: `https://accounts.google.com/.well-known/openid-configuration`
     - This is the value from your `.env` file: `${OPENID_PROVIDER_URL}`
   - **Client ID**: Enter your `CLIENT_ID_GOOGLE_LOGIN` value
     - This is the value from your `.env` file: `${CLIENT_ID_GOOGLE_LOGIN}`
   - **Client Secret**: Enter your `CLIENT_SECRET_GOOGLE_LOGIN` value
     - This is the value from your `.env` file: `${CLIENT_SECRET_GOOGLE_LOGIN}`
4. Click **Save settings**
5. **Activate OIDC** by toggling it on (if there's an activation toggle)

### 2.3 Verify Configuration

After saving, n8n should:
- Display the OIDC configuration as active
- Show the redirect URL that should be configured in Google Cloud Console
- Allow users to sign in with Google

## Step 3: Test the Configuration

### 3.1 Test OAuth Login

1. Log out of n8n (or use an incognito/private browser window)
2. Navigate to `https://n8n.datacrew.space`
3. You should see a **"Sign in with Google"** or **"Sign in with OIDC"** button
4. Click the button and complete the OAuth flow
5. Verify that you're signed in with your Google account

### 3.2 Verify User Creation

- On first sign-in, n8n should automatically create a user account
- Subsequent sign-ins should use the existing account

## Configuration Summary

### Google Cloud Console Configuration

- **Authorized redirect URIs**: `https://n8n.datacrew.space/rest/sso/oidc/callback`
- **Authorized JavaScript origins**: `https://n8n.datacrew.space`
- **OAuth Client**: Reuse existing client (same as `CLIENT_ID_GOOGLE_LOGIN`)

### n8n OIDC Configuration (via UI)

- **Discovery Endpoint**: `https://accounts.google.com/.well-known/openid-configuration` (from `OPENID_PROVIDER_URL`)
- **Client ID**: Value from `CLIENT_ID_GOOGLE_LOGIN`
- **Client Secret**: Value from `CLIENT_SECRET_GOOGLE_LOGIN`
- **Redirect URL**: `https://n8n.datacrew.space/rest/sso/oidc/callback` (displayed by n8n)

### Environment Variables (Already Configured)

You don't need to add any new environment variables. n8n OIDC uses the values you configure in the UI, which you can copy from your existing `.env` file:

```bash
# These are already in your .env file
CLIENT_ID_GOOGLE_LOGIN=your-google-client-id.apps.googleusercontent.com
CLIENT_SECRET_GOOGLE_LOGIN=your-google-client-secret
OPENID_PROVIDER_URL=https://accounts.google.com/.well-known/openid-configuration
```

## Troubleshooting

### OIDC Option Not Available in Settings

- **Cause**: OIDC may require n8n Enterprise edition, or your n8n version may not support it
- **Solution**: 
  1. Check your n8n version: `docker exec n8n n8n --version`
  2. Verify OIDC support in your n8n edition
  3. Update n8n if needed: `docker pull n8nio/n8n:latest`

### "Redirect URI Mismatch" Error

- **Cause**: The redirect URI in Google Cloud Console doesn't match n8n's expected callback URL
- **Solution**: 
  1. Check the redirect URL displayed in n8n Settings > SSO
  2. Ensure it exactly matches the URI in Google Cloud Console
  3. The correct path is `/rest/sso/oidc/callback` (not `/rest/oauth2-credential/callback`)

### "Invalid Client ID or Secret" Error

- **Cause**: The Client ID or Secret entered in n8n UI doesn't match your Google OAuth credentials
- **Solution**: 
  1. Verify `CLIENT_ID_GOOGLE_LOGIN` and `CLIENT_SECRET_GOOGLE_LOGIN` in your `.env` file
  2. Copy the exact values (no extra spaces) into n8n Settings > SSO
  3. Ensure you're using the same OAuth client in Google Cloud Console

### OIDC Button Not Appearing on Login Page

- **Cause**: OIDC may not be activated, or configuration is incomplete
- **Solution**: 
  1. Check n8n Settings > SSO to ensure OIDC is activated
  2. Verify all required fields are filled in
  3. Restart n8n: `docker compose -p localai-apps restart n8n`
  4. Clear browser cache and try again

### Discovery Endpoint Error

- **Cause**: The `OPENID_PROVIDER_URL` may be incorrect or unreachable
- **Solution**: 
  1. Verify `OPENID_PROVIDER_URL` in your `.env` file
  2. It should be: `https://accounts.google.com/.well-known/openid-configuration`
  3. Test the URL in a browser to ensure it's accessible
  4. Use this exact URL in n8n Settings > SSO > Discovery Endpoint

## Security Best Practices

1. **Reuse Existing Credentials**: You're already reusing your Google OAuth credentials, which is good for consistency
2. **Restrict Access**: Consider restricting OAuth consent screen to specific domains or users in Google Cloud Console
3. **Regular Rotation**: Rotate OAuth client secrets periodically
4. **HTTPS Only**: Always use HTTPS for production deployments
5. **Monitor Access**: Review n8n user accounts regularly to ensure only authorized users have access

## Additional Resources

- [n8n OIDC Documentation](https://docs.n8n.io/user-management/oidc/setup/)
- [Google OAuth 2.0 Documentation](https://developers.google.com/identity/protocols/oauth2)
- [OpenID Connect Specification](https://openid.net/specs/openid-connect-core-1_0.html)
- [n8n GitHub Repository](https://github.com/n8n-io/n8n)

## Notes

- **OIDC vs OAuth2 Credentials**: n8n uses OIDC for **user authentication** (SSO), while OAuth2 credentials are used for **workflow integrations** (e.g., Google Sheets, Google Drive). These are separate features.
- **UI Configuration**: Unlike some other services, n8n OIDC is configured through the web UI, not environment variables. This allows for easier management and testing.
- **Redirect URI**: The OIDC redirect URI (`/rest/sso/oidc/callback`) is different from workflow OAuth redirect URIs (`/rest/oauth2-credential/callback`).
- **Reusing Credentials**: You can safely reuse the same Google OAuth client for multiple services (Infisical, Open WebUI, n8n) as long as all redirect URIs are properly configured in Google Cloud Console.

---

**Last Updated**: Based on n8n official documentation  
**Configuration Method**: Web UI (Settings > SSO)  
**Credentials Source**: Reuses existing `CLIENT_ID_GOOGLE_LOGIN`, `CLIENT_SECRET_GOOGLE_LOGIN`, and `OPENID_PROVIDER_URL`
