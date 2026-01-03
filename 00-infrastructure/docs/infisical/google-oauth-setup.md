# Google OAuth/SSO Setup for Infisical

This guide explains how to configure Google Single Sign-On (SSO) for your self-hosted Infisical instance, allowing users to authenticate using their Google accounts.

## Prerequisites

1. **Infisical is running and accessible**
2. **Google Cloud Platform account** with access to create OAuth2 applications
3. **Admin access to Infisical** (to enable SSO in settings)

## Step 1: Create OAuth2 Application in Google Cloud Platform

1. **Go to Google Cloud Console:**
   - Navigate to [Google Cloud Console](https://console.cloud.google.com/)
   - Select or create a project

2. **Enable Google+ API (if not already enabled):**
   - Go to **APIs & Services** → **Library**
   - Search for "Google+ API" or "People API"
   - Click **Enable** if not already enabled

3. **Create OAuth2 Credentials:**
   - Go to **APIs & Services** → **Credentials**
   - Click **Create Credentials** → **OAuth client ID**
   - If prompted, configure the OAuth consent screen first:
     - Choose **Internal** (for Google Workspace) or **External** (for personal accounts)
     - Fill in required fields (App name, User support email, Developer contact)
     - Add scopes: `openid`, `email`, `profile`
     - Save and continue

4. **Create OAuth Client ID:**
   - Application type: **Web application**
   - Name: `Infisical SSO` (or your preferred name)
   - **Authorized redirect URIs:**
     - For local development: `http://localhost:8010/api/v1/auth/oauth2/google/callback`
     - For production: `https://infisical.yourdomain.com/api/v1/auth/oauth2/google/callback`
     - **Important:** The redirect URI must match your `INFISICAL_SITE_URL` exactly
   - Click **Create**

5. **Copy Credentials:**
   - Copy the **Client ID** (looks like: `123456789-abcdefg.apps.googleusercontent.com`)
   - Copy the **Client Secret** (looks like: `GOCSPX-abcdefghijklmnopqrstuvwxyz`)
   - **Save these securely** - you'll need them in the next step

## Step 2: Configure Environment Variables

Add the Google OAuth credentials to your `.env` file:

```bash
# Google OAuth/SSO for Infisical
GOOGLE_CLIENT_ID=your-google-client-id-here
GOOGLE_CLIENT_SECRET=your-google-client-secret-here
```

**Important:** Make sure `INFISICAL_SITE_URL` matches your Infisical URL:
- For local: `INFISICAL_SITE_URL=http://localhost:8010`
- For production: `INFISICAL_SITE_URL=https://infisical.yourdomain.com`

## Step 3: Restart Infisical

Restart the Infisical backend to load the new environment variables:

```bash
cd 00-infrastructure
docker compose restart infisical-backend
```

Wait for the container to be healthy:
```bash
docker ps | grep infisical-backend
# Should show "healthy" status
```

## Step 4: Enable Google SSO in Infisical UI

1. **Access Infisical:**
   - Open your Infisical UI (e.g., `http://localhost:8010`)
   - Log in as an admin user

2. **Navigate to SSO Settings:**
   - Go to **Settings** → **SSO** (or **Organization Settings** → **SSO**)
   - Look for **Google SSO** or **OAuth Providers**

3. **Enable Google SSO:**
   - Toggle **Google SSO** to enabled
   - The system should automatically detect the `GOOGLE_CLIENT_ID` and `GOOGLE_CLIENT_SECRET` from environment variables
   - If prompted, verify the redirect URI matches what you configured in Google Cloud Console

4. **Test the Integration:**
   - Log out of Infisical
   - On the login page, you should see a **"Sign in with Google"** button
   - Click it and complete the OAuth flow
   - You should be redirected back to Infisical and logged in

## Step 5: Verify Configuration

### Check Environment Variables

Verify the variables are loaded in the container:

```bash
docker exec infisical-backend printenv | grep GOOGLE
```

Should show:
```
GOOGLE_CLIENT_ID=your-client-id
GOOGLE_CLIENT_SECRET=your-client-secret
```

### Test OAuth Flow

1. Log out of Infisical
2. Go to the login page
3. Click **"Sign in with Google"**
4. Complete Google authentication
5. Verify you're redirected back and logged in

## Troubleshooting

### "Redirect URI mismatch" Error

**Problem:** Google shows "Redirect URI mismatch" error

**Solution:**
- Verify the redirect URI in Google Cloud Console exactly matches:
  - `http://localhost:8010/api/v1/auth/oauth2/google/callback` (local)
  - `https://infisical.yourdomain.com/api/v1/auth/oauth2/google/callback` (production)
- Ensure `INFISICAL_SITE_URL` matches your actual Infisical URL
- Check for trailing slashes or protocol mismatches (http vs https)

### "Invalid client" Error

**Problem:** Google shows "Invalid client" error

**Solution:**
- Verify `GOOGLE_CLIENT_ID` and `GOOGLE_CLIENT_SECRET` are correct
- Check for extra spaces or quotes in `.env` file
- Ensure environment variables are loaded: `docker exec infisical-backend printenv | grep GOOGLE`
- Restart Infisical after adding variables

### Google SSO Button Not Appearing

**Problem:** "Sign in with Google" button doesn't appear on login page

**Solution:**
- Verify Google SSO is enabled in Infisical UI (Settings → SSO)
- Check Infisical logs: `docker logs infisical-backend | grep -i google`
- Ensure environment variables are set correctly
- Try clearing browser cache or using incognito mode

### OAuth Consent Screen Issues

**Problem:** Google shows consent screen errors

**Solution:**
- Complete OAuth consent screen configuration in Google Cloud Console
- Add required scopes: `openid`, `email`, `profile`
- For external apps, verify your domain or add test users
- Wait a few minutes after making changes (Google caches consent screen)

## Security Best Practices

1. **Keep Client Secret Secure:**
   - Never commit `GOOGLE_CLIENT_SECRET` to version control
   - Store in `.env` file (already in `.gitignore`)
   - Consider using Infisical itself to store the secret (meta!)

2. **Use HTTPS in Production:**
   - Always use `https://` for production `INFISICAL_SITE_URL`
   - Google requires HTTPS for production OAuth redirects (except localhost)

3. **Limit OAuth Scopes:**
   - Only request necessary scopes (`openid`, `email`, `profile`)
   - Don't request excessive permissions

4. **Regularly Rotate Credentials:**
   - Periodically regenerate Client Secret in Google Cloud Console
   - Update `.env` and restart Infisical

5. **Monitor OAuth Usage:**
   - Check Google Cloud Console for OAuth usage
   - Review Infisical audit logs for SSO logins

## Additional Resources

- [Infisical Google SSO Documentation](https://infisical.com/docs/documentation/platform/sso/google)
- [Google OAuth2 Setup Guide](https://developers.google.com/identity/protocols/oauth2)
- [Google Cloud Console](https://console.cloud.google.com/)

## Next Steps

After enabling Google SSO:
- Test login with multiple Google accounts
- Configure user permissions in Infisical
- Set up additional OAuth providers if needed (GitHub, etc.)
- Consider enabling SAML SSO for enterprise use (requires enterprise license)

