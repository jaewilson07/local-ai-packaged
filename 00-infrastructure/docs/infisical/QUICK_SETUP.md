# Quick Setup: Infisical Project "local-aipackaged"

## Step-by-Step Guide

### Prerequisites Check

1. **Infisical is running:**
   ```bash
   docker ps | grep infisical
   ```
   Should show: `infisical-backend`, `infisical-db`, `infisical-redis`

2. **Infisical CLI is installed:**
   ```bash
   infisical --version
   ```

### Step 1: Access Infisical UI

**Option A: Via Caddy (if configured)**
- URL: Check your `INFISICAL_HOSTNAME` in `.env`
- Default: `http://localhost:8010` (if INFISICAL_HOSTNAME=:8010)

**Option B: Direct container access**
```bash
# Get container IP
docker inspect infisical-backend --format='{{range .NetworkSettings.Networks}}{{.IPAddress}}{{end}}'

# Or access via port (if exposed)
# Check: docker port infisical-backend
```

**Option C: Port forward (temporary)**
```bash
# If not accessible, temporarily expose port
docker port infisical-backend 8080
# Then access: http://localhost:<mapped-port>
```

### Step 2: Configure SMTP (Required for Signup)

Infisical requires SMTP configuration for email signup, invitations, and password resets.

**Option A: Configure SMTP in `.env` file:**

Add these variables to your `.env` file:
```bash
SMTP_HOST=smtp.sendgrid.net  # or your SMTP provider
SMTP_PORT=587
SMTP_USERNAME=your_smtp_username
SMTP_PASSWORD=your_smtp_password
SMTP_FROM_ADDRESS=your_email@example.com
SMTP_FROM_NAME=Infisical
```

**Option B: Use Google OAuth (Alternative to Email Signup):**

If you have Google OAuth configured, you can sign in with Google instead:
1. Add `GOOGLE_CLIENT_ID` and `GOOGLE_CLIENT_SECRET` to `.env`
2. Restart Infisical: `docker compose restart infisical-backend`
3. Use "Sign in with Google" on the login page

**Option C: Create User via Database (Advanced):**

If you need to create a user without SMTP, you can manually insert into the database.
See troubleshooting section below.

### Step 3: Create Admin Account

1. Open Infisical UI in browser
2. Navigate to `/admin/signup`
3. Create your admin account (first user becomes admin)
   - If SMTP is configured, you'll receive a verification email
   - If using Google OAuth, use "Sign in with Google"

### Step 3: Create Organization

1. In Infisical UI, click **"Create Organization"**
2. Name it (e.g., "DataCrew" or "Personal")
3. Click **"Create"**

### Step 4: Create Project "local-aipackaged"

1. In your organization, click **"Create Project"**
2. **Project Name:** `local-aipackaged`
3. **Description:** (optional) "Local AI Packaged Services"
4. Click **"Create Project"**

### Step 5: Create Environments

After creating the project, set up environments:

1. **Development Environment:**
   - Click "Add Environment"
   - Name: `development`
   - Description: "Local development environment"

2. **Production Environment:**
   - Click "Add Environment"
   - Name: `production`
   - Description: "Production environment"

### Step 6: Authenticate CLI

```bash
# Login to Infisical CLI
infisical login

# This will:
# 1. Open browser for authentication
# 2. Ask you to authorize the CLI
# 3. Store authentication token locally
```

### Step 7: Initialize Project in Repository

```bash
cd /home/jaewilson07/GitHub/local-ai-packaged

# Initialize Infisical in this directory
infisical init

# This will:
# 1. Ask you to select organization
# 2. Ask you to select project (choose "local-aipackaged")
# 3. Ask you to select environment (choose "development")
# 4. Create .infisical.json config file
```

### Step 8: Verify Setup

```bash
# Check if project is initialized
cat .infisical.json

# Test secret export
infisical export --format=dotenv | head -5

# List secrets (should be empty initially)
infisical secrets
```

### Step 9: Add Secrets

**Option A: Via UI (Recommended for first-time)**
1. Go to Infisical UI
2. Select project: `local-aipackaged`
3. Select environment: `development`
4. Click "Add Secret"
5. Add secrets from your `.env` file (passwords, API keys, tokens)

**Option B: Via CLI**
```bash
# Add a secret
infisical secrets set POSTGRES_PASSWORD "your-password"

# Add multiple secrets
infisical secrets set CLOUDFLARE_API_TOKEN "your-token"
infisical secrets set CLOUDFLARE_TUNNEL_TOKEN "your-tunnel-token"
```

### Step 10: Test Integration

```bash
# Export secrets to test file
infisical export --format=dotenv > .env.infisical.test

# Check if secrets are exported
cat .env.infisical.test | head -10

# Clean up test file
rm .env.infisical.test
```

## Troubleshooting

### Infisical UI Not Accessible

**Check if Infisical is healthy:**
```bash
docker logs infisical-backend --tail 50
```

**Check database connection:**
- Infisical needs to connect to PostgreSQL
- Verify `INFISICAL_POSTGRES_PASSWORD` is set correctly
- Check if password needs URL encoding (if it contains special characters)

**Access directly:**
```bash
# Get container IP and access directly
docker exec -it infisical-backend wget -qO- http://localhost:8080/api/health
```

### CLI Authentication Issues

**Re-authenticate:**
```bash
infisical logout
infisical login
```

**Check authentication:**
```bash
# This should show your logged-in status
infisical secrets
```

### Project Not Found

**List available projects:**
```bash
# After logging in, you should see projects
infisical projects
```

**Re-initialize:**
```bash
rm .infisical.json
infisical init
```

### Email Service Not Configured

**Error:** "The administrators of this Infisical instance have not yet set up an email service provider required to perform this action"

**Solution 1: Configure SMTP (Recommended)**

Add SMTP configuration to your `.env` file:
```bash
SMTP_HOST=smtp.sendgrid.net  # or smtp.gmail.com, smtp.mailgun.org, etc.
SMTP_PORT=587
SMTP_USERNAME=your_smtp_username
SMTP_PASSWORD=your_smtp_password
SMTP_FROM_ADDRESS=your_email@example.com
SMTP_FROM_NAME=Infisical
```

Then restart Infisical:
```bash
cd 00-infrastructure
docker compose restart infisical-backend
```

**Solution 2: Use Google OAuth**

If you have Google OAuth configured, you can sign in with Google instead of email:
1. Add `GOOGLE_CLIENT_ID` and `GOOGLE_CLIENT_SECRET` to `.env`
2. Restart Infisical
3. Use "Sign in with Google" on the login page

**Solution 3: Create User via Database (Advanced)**

If you need to create a user without SMTP, you can manually insert into the database.
⚠️ **Warning:** This is an advanced workaround and may not work with all Infisical features.

```bash
# Connect to the database
docker exec -it infisical-db psql -U postgres -d postgres

# Note: This requires knowledge of Infisical's database schema and password hashing
# It's recommended to configure SMTP instead
```

## Next Steps

After setup:
1. ✅ Project created: `local-aipackaged`
2. ✅ Environments created: `development`, `production`
3. ✅ CLI authenticated and initialized
4. ⏭️ Add secrets from `.env` file
5. ⏭️ Test with `start_services.py --use-infisical`

## Quick Reference

```bash
# Login
infisical login

# Initialize project
infisical init

# Add secret
infisical secrets set KEY "value"

# List secrets
infisical secrets

# Export secrets
infisical export --format=dotenv

# Use with start_services.py
python start_services.py --use-infisical
```

