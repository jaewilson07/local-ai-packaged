# Google OAuth Setup for Infisical

This guide will help you set up Google OAuth authentication for your Infisical instance at `https://infisical.datacrew.space`.

## Step 1: Create OAuth2 Application in Google Cloud Platform

1. **Go to Google Cloud Console:**
   - Navigate to [Google Cloud Console](https://console.cloud.google.com/)
   - Select or create a project

2. **Enable OAuth Consent Screen (if not already done):**
   - Go to **APIs & Services** → **OAuth consent screen**
   - Choose **External** (for personal Google accounts) or **Internal** (for Google Workspace)
   - Fill in required fields:
     - **App name**: `Infisical` (or your preferred name)
     - **User support email**: Your email
     - **Developer contact information**: Your email
   - Click **Save and Continue**
   - Add scopes: `openid`, `email`, `profile` (usually added by default)
   - Click **Save and Continue**
   - Add test users if needed (for external apps in testing mode)
   - Click **Save and Continue**

3. **Create OAuth Client ID:**
   - Go to **APIs & Services** → **Credentials**
   - Click **Create Credentials** → **OAuth client ID**
   - Choose **Web application**
   - **Name**: `Infisical SSO` (or your preferred name)
   - **Authorized redirect URIs**: Add this exact URI:
     ```
     https://infisical.datacrew.space/api/v1/auth/oauth2/google/callback
     ```
   - Click **Create**

4. **Copy Credentials:**
   - Copy the **Client ID** (looks like: `123456789-abcdefg.apps.googleusercontent.com`)
   - Copy the **Client Secret** (looks like: `GOCSPX-abcdefghijklmnopqrstuvwxyz`)
   - **Save these securely** - you'll need them in the next step

## Step 2: Add Credentials to `.env` File

Open your `.env` file in the project root and add/update these lines:

```bash
# Google OAuth/SSO for Infisical
GOOGLE_CLIENT_ID=your-google-client-id-here
GOOGLE_CLIENT_SECRET=your-google-client-secret-here
```

**Important:** 
- Replace `your-google-client-id-here` with your actual Client ID
- Replace `your-google-client-secret-here` with your actual Client Secret
- Make sure these are on separate lines and not commented out

## Step 3: Restart Infisical

Restart the Infisical backend to load the new environment variables:

```bash
cd 00-infrastructure
docker compose restart infisical-backend
```

Wait for the container to be healthy (about 30 seconds):

```bash
docker ps | grep infisical-backend
# Should show "healthy" status
```

## Step 4: Enable Google SSO in Infisical UI

1. **Access Infisical:**
   - Go to `https://infisical.datacrew.space`
   - You'll need to be logged in as an admin (or create an admin account first)

2. **Navigate to SSO Settings:**
   - Go to **Settings** → **SSO** (or **Organization Settings** → **SSO**)
   - Look for **Google SSO** or **OAuth Providers**

3. **Enable Google SSO:**
   - Toggle **Google SSO** to enabled
   - The system should automatically detect the `GOOGLE_CLIENT_ID` and `GOOGLE_CLIENT_SECRET` from environment variables
   - Verify the redirect URI matches: `https://infisical.datacrew.space/api/v1/auth/oauth2/google/callback`

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
2. Go to the login page at `https://infisical.datacrew.space`
3. Click **"Sign in with Google"**
4. Complete Google authentication
5. Verify you're redirected back and logged in

## Troubleshooting

### "Sign in with Google" button not appearing

- Check that `GOOGLE_CLIENT_ID` and `GOOGLE_CLIENT_SECRET` are set in `.env`
- Verify Infisical backend has been restarted
- Check container logs: `docker logs infisical-backend --tail 50`

### OAuth redirect error

- Verify the redirect URI in Google Cloud Console matches exactly:
  `https://infisical.datacrew.space/api/v1/auth/oauth2/google/callback`
- Check that `INFISICAL_SITE_URL` in `.env` is set to `https://infisical.datacrew.space`
- Ensure the redirect URI doesn't have a trailing slash

### "redirect_uri_mismatch" error

- The redirect URI in Google Cloud Console must match exactly what Infisical is sending
- Check the error message for the exact URI being used
- Update Google Cloud Console with the correct URI

### Can't enable SSO in UI

- You need to be logged in as an admin user
- The first user created in Infisical becomes the admin
- If you can't create an account due to email issues, you may need to configure SMTP first or use the database workaround

## Next Steps

After enabling Google SSO:
- Test login with multiple Google accounts
- Configure user permissions in Infisical
- Consider setting up additional OAuth providers (GitHub, etc.) if needed

## Security Notes

1. **Keep Credentials Secret:**
   - Never commit `.env` file to version control
   - Consider using Infisical itself to store the secret (meta!)

2. **Use HTTPS in Production:**
   - ✅ Already configured: `https://infisical.datacrew.space`
   - Google requires HTTPS for production OAuth redirects

3. **Limit OAuth Scopes:**
   - Only request necessary scopes (`openid`, `email`, `profile`)
   - Don't request excessive permissions

4. **Regularly Rotate Credentials:**
   - Periodically regenerate Client Secret in Google Cloud Console
   - Update `.env` and restart Infisical


