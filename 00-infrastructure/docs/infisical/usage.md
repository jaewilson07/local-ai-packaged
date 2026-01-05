# Infisical Usage Guide

Day-to-day operations, secret management, and best practices for using Infisical with local-ai-packaged.

## Table of Contents

1. [How Secrets Are Synced](#how-secrets-are-synced)
2. [Managing Secrets](#managing-secrets)
3. [Using with start_services.py](#using-with-start_servicespy)
4. [Migration Strategy](#migration-strategy)
5. [Best Practices](#best-practices)
6. [Quick Reference](#quick-reference)

---

## How Secrets Are Synced

### Integration Flow

Infisical integrates with the local-ai-packaged project through a simple export mechanism:

```
┌─────────────────┐
│   Infisical UI  │  ← Manage secrets via web interface
│   (Port 8020)   │
└────────┬────────┘
         │
         │ Stores secrets in
         ▼
┌─────────────────┐
│   PostgreSQL     │  ← Infisical database
└─────────────────┘
         │
         │ CLI fetches secrets
         ▼
┌─────────────────┐
│  start_services  │  ← Exports secrets to .env.infisical
│      .py         │
└────────┬────────┘
         │
         │ Uses .env.infisical
         ▼
┌─────────────────┐
│ Docker Compose   │  ← Services read secrets from env file
│   Services       │
└─────────────────┘
```

### Automatic Sync (Default)

When you start services, secrets are automatically exported from Infisical:

```bash
python start_services.py --profile cpu
# Automatically exports secrets from Infisical
# Services use .env.infisical file
```

The integration is handled in `start_services.py`:

```python
def export_infisical_secrets(env_file_path=".env.infisical"):
    """Export secrets from Infisical to a temporary .env file."""
    # Checks for Infisical CLI
    # Exports secrets using: infisical export --format=dotenv
    # Returns path to .env.infisical file

def start_local_ai(profile=None, environment=None, use_infisical=False):
    """Start the local AI services."""
    if use_infisical:
        infisical_env_file = export_infisical_secrets()
        if infisical_env_file:
            cmd.extend(["--env-file", infisical_env_file])
            # Docker Compose uses .env.infisical for secrets
```

### Manual Export

You can manually export secrets at any time:

```bash
# Export to file
infisical export --format=dotenv > .env.infisical

# View secrets in terminal
infisical export --format=dotenv
```

### Fallback Behavior

If Infisical is unavailable, services automatically fall back to `.env`:

```bash
# Disable Infisical explicitly
python start_services.py --skip-infisical
```

### What Gets Synced

**Secrets stored in Infisical:**
- Database passwords (PostgreSQL, MongoDB, ClickHouse)
- API keys (N8N, JWT secrets)
- Encryption keys (N8N, Langfuse)
- Service credentials (Neo4j, MinIO)
- Docker Hub credentials
- Cloudflare tokens

**Configuration in `.env` (not synced):**
- Hostnames (N8N_HOSTNAME, WEBUI_HOSTNAME, etc.)
- Port numbers
- Non-sensitive configuration
- Infisical configuration itself

---

## Managing Secrets

### Adding Secrets

#### Option A: Via UI (Recommended for First-Time)

1. Go to Infisical UI (`http://localhost:8020` or `https://infisical.datacrew.space`)
2. Select project: `local-ai-packaged`
3. Select environment: `development`
4. Click **"Add Secret"**
5. Add secrets from your `.env` file:
   - `POSTGRES_PASSWORD`
   - `CLOUDFLARE_API_TOKEN`
   - `CLOUDFLARE_TUNNEL_TOKEN`
   - `INFISICAL_POSTGRES_PASSWORD`
   - `INFISICAL_ENCRYPTION_KEY`
   - `INFISICAL_AUTH_SECRET`
   - And other sensitive secrets

#### Option B: Via CLI

```bash
# Add secrets one by one
infisical secrets set POSTGRES_PASSWORD "your-password"
infisical secrets set CLOUDFLARE_API_TOKEN "your-token"
infisical secrets set CLOUDFLARE_TUNNEL_TOKEN "your-tunnel-token"

# Add multiple secrets interactively
infisical secrets set
```

### Viewing Secrets

#### Via Web UI

1. Navigate to `http://localhost:8020` or `https://infisical.datacrew.space`
2. Select project and environment
3. View all secrets in organized folders

#### Via CLI

```bash
# List all secrets
infisical secrets

# Get specific secret
infisical secrets get POSTGRES_PASSWORD

# Export all secrets (formatted)
infisical export --format=dotenv
```

### Updating Secrets

#### Via Web UI

1. Navigate to secret in Infisical UI
2. Click **"Edit"**
3. Update value
4. Click **"Save"**
5. Restart services to apply: `python start_services.py`

#### Via CLI

```bash
# Update a secret
infisical secrets set POSTGRES_PASSWORD "new-password"

# Restart services to apply changes
python start_services.py --profile cpu
```

### Deleting Secrets

#### Via Web UI

1. Navigate to secret in Infisical UI
2. Click **"Delete"**
3. Confirm deletion

#### Via CLI

```bash
# Delete a secret
infisical secrets delete POSTGRES_PASSWORD
```

---

## Using with start_services.py

### Basic Usage

```bash
# Start with Infisical (automatic secret export)
python start_services.py --profile cpu

# Start specific stack with Infisical
python start_services.py --stack infrastructure --use-infisical

# Start without Infisical (use .env file)
python start_services.py --skip-infisical
```

### How It Works

1. `start_services.py` checks if Infisical CLI is available
2. If available, it runs `infisical export --format=dotenv > .env.infisical`
3. Docker Compose uses `.env.infisical` as an additional env file
4. Services receive secrets as environment variables
5. If Infisical is unavailable, falls back to `.env` file

### Workflow Examples

**Initial Setup:**
1. Create `.env` file with all secrets (one-time)
2. Start Infisical: `python start_services.py`
3. Access Infisical UI: `http://localhost:8020`
4. Migrate secrets from `.env` to Infisical (via UI or CLI)
5. Remove secrets from `.env`, keep only non-sensitive config

**Daily Usage:**
1. Manage secrets in Infisical UI
2. Start services: `python start_services.py`
3. Secrets automatically exported and used by services

**Updating Secrets:**
1. Update secret in Infisical UI
2. Restart services: `python start_services.py`
3. New secret value automatically used

---

## Migration Strategy

### Phase 1: Hybrid Approach (Current)

**Keep non-sensitive config in `.env`**
- Hostnames, ports, feature flags
- Non-sensitive configuration

**Store sensitive secrets in Infisical**
- Passwords, API keys, tokens
- Encryption keys, credentials

**Services read from both**
- Infisical takes precedence
- Falls back to `.env` if Infisical unavailable

**Benefits:**
- Gradual migration
- Can test Infisical without breaking existing setup
- Easy rollback if needed

### Phase 2: Full Migration (Future)

**All secrets in Infisical**
- Complete centralized management
- No secrets in `.env` file

**`.env` only for non-sensitive configuration**
- Hostnames, ports, URLs
- Feature flags, debug settings

**Machine identities for automated access**
- CI/CD pipelines
- Automated deployments

**Benefits:**
- Complete security
- Centralized management
- Better auditability

---

## Best Practices

### Security

1. **Never commit secrets to git**
   - Use Infisical for all sensitive values
   - Keep `.env` file in `.gitignore`
   - Never commit encryption keys or auth secrets

2. **Rotate encryption keys periodically**
   - Generate new keys and migrate data
   - Update `.env` file with new keys
   - Restart Infisical services

3. **Use machine identities for production**
   - Don't use personal logins for automated access
   - Create machine identities with minimal required permissions
   - Rotate machine identity credentials regularly

4. **Limit permissions**
   - Give machine identities only the access they need
   - Use environment-specific access when possible
   - Review and audit access regularly

5. **Audit access**
   - Use Infisical's audit logs to track secret access
   - Review who accessed what secrets and when
   - Set up alerts for suspicious activity

6. **Backup Infisical data**
   - Infisical data is stored in PostgreSQL (already backed up)
   - Regularly backup the `infisical-db` volume
   - Test restore procedures

7. **Use HTTPS in production**
   - Always use `https://` for production `INFISICAL_SITE_URL`
   - Set `HTTPS_ENABLED=true` for production
   - Google requires HTTPS for production OAuth redirects (except localhost)

8. **Keep Infisical updated**
   - Regularly update Infisical Docker image
   - Check for security patches
   - Review changelog for breaking changes

### Operational

1. **Use environment separation**
   - Different secrets for dev/prod
   - Never use production secrets in development
   - Use separate projects or environments

2. **Document secret purposes**
   - Add comments/descriptions to secrets in Infisical UI
   - Document which services use which secrets
   - Keep a secret inventory

3. **Regular secret rotation**
   - Rotate secrets periodically
   - Update secrets in Infisical (services automatically get new values)
   - Remove old/unused secrets

4. **Monitor secret usage**
   - Check which secrets are actually being used
   - Remove unused secrets
   - Consolidate duplicate secrets

5. **Team collaboration**
   - Use Infisical's team features for collaboration
   - Set appropriate permissions for team members
   - Use folders to organize secrets

### Developer Experience

1. **Web UI for management**
   - Use UI for adding/updating secrets
   - Easier than editing `.env` files manually
   - Visual organization with folders

2. **CLI for automation**
   - Use CLI in scripts and CI/CD
   - Automated secret fetching
   - Works with existing workflows

3. **Automatic sync**
   - No manual copying needed
   - Secrets automatically exported on service start
   - Fallback to `.env` if Infisical unavailable

---

## Quick Reference

### Common CLI Commands

```bash
# Login
infisical login --host=https://infisical.datacrew.space

# Initialize project
infisical init

# List secrets
infisical secrets

# Get specific secret
infisical secrets get POSTGRES_PASSWORD

# Set secret
infisical secrets set KEY "value"

# Delete secret
infisical secrets delete KEY

# Export secrets
infisical export --format=dotenv

# Export to file
infisical export --format=dotenv > .env.infisical

# Run command with secrets
infisical run -- your-command

# Use with start_services.py
python start_services.py --use-infisical
```

### Environment Variables Reference

**Required for Infisical:**
```bash
INFISICAL_ENCRYPTION_KEY=<16-byte-hex-string>
INFISICAL_AUTH_SECRET=<32-byte-base64-string>
INFISICAL_HOSTNAME=:8020  # or infisical.datacrew.space
INFISICAL_SITE_URL=http://localhost:8020  # or https://infisical.datacrew.space
INFISICAL_HTTPS_ENABLED=false  # or true for production
```

**Database Configuration:**
```bash
INFISICAL_POSTGRES_HOST=infisical-db
INFISICAL_POSTGRES_PORT=5432
INFISICAL_POSTGRES_DATABASE=postgres
INFISICAL_POSTGRES_USERNAME=postgres
INFISICAL_POSTGRES_PASSWORD=<password>
```

**Optional - Google OAuth:**
```bash
GOOGLE_CLIENT_ID=<client-id>
GOOGLE_CLIENT_SECRET=<client-secret>
```

**Optional - SMTP:**
```bash
SMTP_HOST=smtp.sendgrid.net
SMTP_PORT=587
SMTP_USERNAME=<username>
SMTP_PASSWORD=<password>
SMTP_FROM_ADDRESS=<email>
SMTP_FROM_NAME=Infisical
```

### Service URLs

- **Local UI**: `http://localhost:8020`
- **Production UI**: `https://infisical.datacrew.space`
- **Admin Signup**: `/admin/signup`
- **Health Check**: `/api/health`

### Container Names

- `infisical-backend` - Main Infisical application
- `infisical-db` - PostgreSQL database
- `infisical-redis` - Redis cache

### Useful Commands

```bash
# Check Infisical services
docker ps | grep infisical

# View Infisical logs
docker logs infisical-backend --tail 50

# Check health
docker exec infisical-backend wget -qO- http://localhost:8080/api/health

# Restart Infisical
docker restart infisical-backend

# Export secrets for debugging
infisical export --format=dotenv | grep -i postgres
```

---

## Related Documentation

- [Setup Guide](./setup.md) - Initial setup and configuration
- [Design Documentation](./design.md) - Architecture and design decisions
- [Troubleshooting Guide](./troubleshooting_configuration.md) - Comprehensive troubleshooting
- [Infisical Official Documentation](https://infisical.com/docs)
- [Infisical GitHub](https://github.com/Infisical/infisical)
