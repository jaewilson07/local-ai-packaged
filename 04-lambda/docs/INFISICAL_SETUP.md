# Infisical Integration for Lambda Server

The Lambda server supports loading secrets from Infisical at runtime, providing centralized secrets management across all services.

## Overview

When configured, the Lambda server will:
1. Authenticate with Infisical using Machine Identity (Universal Auth)
2. Fetch all secrets from the specified project/environment
3. Inject secrets into environment variables before configuration loads
4. Fall back to `.env` file if Infisical is not configured or unavailable

## Setup Instructions

### 1. Create a Machine Identity

1. Log into Infisical at https://infisical.datacrew.space
2. Go to **Organization Settings** > **Machine Identities**
3. Click **Create Machine Identity**
4. Configure:
   - **Name**: `lambda-server` (or descriptive name)
   - **Auth Method**: **Universal Auth**
5. Save and copy the **Client ID** and **Client Secret**

### 2. Add Identity to Project

1. Go to your project in Infisical
2. Navigate to **Project Settings** > **Machine Identities**
3. Click **Add Machine Identity**
4. Select the identity you created
5. Grant **Read** permission (or higher if needed)
6. Select the environments the Lambda server should access (e.g., `dev`, `prod`)

### 3. Get Your Project ID

1. In Infisical, go to your project
2. Click **Project Settings**
3. Copy the **Project ID** from the settings page

### 4. Configure Environment Variables

Add to your `.env` file:

```bash
# Infisical Machine Identity (for Lambda server secrets)
INFISICAL_CLIENT_ID=your-client-id-here
INFISICAL_CLIENT_SECRET=your-client-secret-here
INFISICAL_PROJECT_ID=your-project-id-here
INFISICAL_ENVIRONMENT=dev  # or prod, staging, etc.
INFISICAL_HOST=https://infisical.datacrew.space
```

### 5. Restart Lambda Server

```bash
docker compose -p localai-lambda -f 04-lambda/docker-compose.yml up -d --force-recreate
```

## Secrets Naming Convention

Infisical secrets should match the environment variable names used by the Lambda server:

| Infisical Secret | Lambda Config Field | Description |
|------------------|---------------------|-------------|
| `POSTGRES_PASSWORD` | `postgres_password` | PostgreSQL password |
| `NEO4J_PASSWORD` | `neo4j_password` | Neo4j password |
| `MONGODB_URI` | `mongodb_uri` | MongoDB connection string |
| `LLM_API_KEY` | `llm_api_key` | OpenAI/Anthropic API key |
| `CLOUDFLARE_AUD_TAG` | `cloudflare_aud_tag` | Cloudflare Access audience tag |

## Priority Order

Secrets are loaded in this priority (highest to lowest):
1. **Environment variables** (set directly or via docker-compose)
2. **Infisical secrets** (fetched at runtime)
3. **`.env` file** (loaded via pydantic-settings)
4. **Default values** (hardcoded in config)

## Verification

Check if secrets are loaded from Infisical:

```bash
# View Lambda server logs
docker logs lambda-server 2>&1 | grep -i infisical
```

You should see:
```
Successfully authenticated with Infisical at https://infisical.datacrew.space
Loaded X secrets from Infisical (project=..., env=dev)
Injected X secrets from Infisical into environment
```

## Troubleshooting

### "INFISICAL_CLIENT_ID or INFISICAL_CLIENT_SECRET not set"
- Ensure both variables are set in `.env`
- Verify docker-compose passes them through

### "INFISICAL_PROJECT_ID not set"
- You need to specify which project contains the secrets
- Find your Project ID in Infisical project settings

### Authentication fails
- Verify Client ID and Secret are correct
- Check the Machine Identity has Universal Auth enabled
- Ensure the identity is added to the project with proper permissions

### Secrets not loading
- Verify the environment slug matches (e.g., `dev` vs `development`)
- Check the secret path (defaults to `/`)
- Ensure secrets are not nested in folders (use root path `/`)

## Security Considerations

- **Never commit** `INFISICAL_CLIENT_SECRET` to version control
- Use separate Machine Identities for each environment (dev/staging/prod)
- Regularly rotate Client Secrets
- Grant minimal permissions (read-only for Lambda server)

## Disabling Infisical

To disable Infisical and use only `.env`:
- Remove or leave empty: `INFISICAL_CLIENT_ID`
- The Lambda server will automatically fall back to `.env` loading
