# Infisical Setup and Migration Guide

This guide will help you set up Infisical for managing secrets in your local AI package and migrate existing secrets from `.env` files.

## Prerequisites

1. **Infisical CLI installed** on your host machine (where `start_services.py` runs)
   - Installation: https://infisical.com/docs/cli/overview
   - Verify: `infisical --version`

2. **Docker and Docker Compose** (already required for this project)

3. **Generated encryption keys** for Infisical (see below)

## Step 1: Generate Infisical Encryption Keys

Infisical requires two encryption keys. Generate them using the following commands:

```bash
# Generate ENCRYPTION_KEY (16-byte hex string)
openssl rand -hex 16

# Generate AUTH_SECRET (32-byte base64 string)
openssl rand -base64 32
```

**Windows PowerShell alternative:**
```powershell
# ENCRYPTION_KEY
-join ((1..16) | ForEach-Object { '{0:X2}' -f (Get-Random -Maximum 256) })

# AUTH_SECRET (base64)
[Convert]::ToBase64String((1..32 | ForEach-Object { Get-Random -Maximum 256 }))
```

Add these to your `.env` file:
```bash
INFISICAL_ENCRYPTION_KEY=<your-encryption-key>
INFISICAL_AUTH_SECRET=<your-auth-secret>
```

## Step 2: Configure Infisical Hostname

Add to your `.env` file:

```bash
# For local development (port-based)
INFISICAL_HOSTNAME=:8010

# For production (domain-based)
# INFISICAL_HOSTNAME=infisical.yourdomain.com
```

Also set the SITE_URL (used for OAuth redirects):
```bash
# For local development
INFISICAL_SITE_URL=http://localhost:8010

# For production
# INFISICAL_SITE_URL=https://infisical.yourdomain.com
```

## Step 3: Start Infisical

Run the startup script:
```bash
python start_services.py --profile cpu
```

Infisical will start automatically and wait for postgres/redis to be ready.

## Step 4: Access Infisical UI and Create Admin Account

1. Open your browser and navigate to:
   - **Local**: `http://localhost:8010/admin/signup`
   - **Production**: `https://infisical.yourdomain.com/admin/signup`

2. Create your admin account (first user becomes admin)

3. After signup, you'll be logged into the Infisical dashboard

## Step 5: Create Organization and Project

1. In the Infisical UI, create a new **Organization** (if needed)
2. Create a new **Project** (e.g., "local-ai-package")
3. Select or create environments:
   - `development` (for local development)
   - `production` (for production deployments)

## Step 6: Migrate Secrets from .env to Infisical

### Option A: Using the Web UI (Recommended for first-time setup)

1. Navigate to your project in the Infisical UI
2. Select the `development` environment
3. Click **"Add Secret"** or drag-and-drop your `.env` file
4. For each secret from your `.env`:
   - Click **"Add Secret"**
   - Enter the key name (e.g., `POSTGRES_PASSWORD`)
   - Enter the value
   - Click **"Save"**

### Option B: Using the CLI

1. **Authenticate with Infisical CLI:**
   ```bash
   infisical login
   ```
   Follow the browser-based authentication flow.

2. **Initialize Infisical in your project:**
   ```bash
   cd /path/to/local-ai-packaged
   infisical init
   ```
   Select your organization and project when prompted.

3. **Import secrets from .env file:**
   ```bash
   # Read your .env file and add secrets one by one
   # Or use the UI for bulk import
   ```

## Step 7: Create Machine Identity for CLI Access

For automated secret fetching (used by `start_services.py`):

1. In Infisical UI, go to **Settings** → **Machine Identities**
2. Click **"Create Machine Identity"**
3. Give it a name (e.g., "local-ai-package-cli")
4. Select your project and environment
5. Set appropriate permissions (read access to secrets)
6. Copy the **Client ID** and **Client Secret**

7. **Set environment variables** (not in .env, use your shell):
   ```bash
   export INFISICAL_MACHINE_CLIENT_ID=<client-id>
   export INFISICAL_MACHINE_CLIENT_SECRET=<client-secret>
   ```

8. **Authenticate using machine identity:**
   ```bash
   infisical login --method=universal-auth \
     --client-id=$INFISICAL_MACHINE_CLIENT_ID \
     --client-secret=$INFISICAL_MACHINE_CLIENT_SECRET
   ```

## Step 8: Test Secret Export

Verify that secrets can be exported:

```bash
infisical export --format=dotenv > .env.infisical.test
cat .env.infisical.test
```

If this works, `start_services.py` will automatically use Infisical secrets when starting services.

## Step 9: Update Your Workflow

After migration:

1. **Keep non-sensitive config in `.env`** (hostnames, ports, etc.)
2. **Store sensitive secrets in Infisical** (passwords, API keys, tokens)
3. **Use Infisical UI** to manage secrets going forward
4. **Use CLI** for automation and CI/CD

## Troubleshooting

### Infisical UI not accessible

- Check Caddy configuration: `docker logs caddy`
- Verify `INFISICAL_HOSTNAME` is set correctly in `.env`
- Check Infisical container: `docker logs infisical`

### CLI authentication fails

- Make sure you've run `infisical login` or set machine identity
- Check token expiration: `infisical token renew`
- Verify project configuration: `infisical init`

### Secrets not exporting

- Verify you're authenticated: `infisical secrets`
- Check project and environment are correct
- Ensure secrets exist in the selected environment

### Health check failures

- Check Infisical logs: `docker logs infisical`
- Verify postgres and redis are running
- Check database connection string in Infisical environment variables

## Security Best Practices

1. **Never commit secrets to git** - Use Infisical for all sensitive values
2. **Rotate encryption keys periodically** - Generate new keys and migrate data
3. **Use machine identities** for production (not personal logins)
4. **Limit permissions** - Give machine identities only the access they need
5. **Audit access** - Use Infisical's audit logs to track secret access
6. **Backup Infisical data** - Infisical data is stored in Postgres (already backed up)

## Next Steps

- Explore Infisical features: folders, tags, comments, versioning
- Set up personal overrides for local development
- Configure secret scanning to prevent leaks
- Integrate with CI/CD pipelines

For more information, see: https://infisical.com/docs

