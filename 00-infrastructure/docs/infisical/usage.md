# Why and How We Use Infisical

This document explains the rationale behind using Infisical for secret management and how it integrates with this project.

## Why Infisical?

### Problem: Secret Management Challenges

Managing secrets in a self-hosted environment presents several challenges:

1. **Security Risks:**
   - `.env` files can be accidentally committed to version control
   - Secrets stored in plain text are vulnerable to exposure
   - No centralized way to rotate or audit secrets

2. **Operational Complexity:**
   - Secrets scattered across multiple `.env` files
   - Difficult to share secrets across team members securely
   - No version history for secret changes
   - Manual synchronization between environments

3. **Scalability Issues:**
   - Adding new services requires updating multiple files
   - No easy way to manage secrets for multiple environments
   - Difficult to maintain consistency across deployments

### Solution: Infisical

Infisical is an open-source secret management platform that provides:

✅ **Centralized Secret Storage** - All secrets in one secure location  
✅ **Web UI** - Easy-to-use interface for managing secrets  
✅ **CLI Integration** - Automated secret fetching for scripts  
✅ **Environment Management** - Separate secrets for dev/prod  
✅ **Audit Logging** - Track who accessed what secrets and when  
✅ **Version History** - See changes to secrets over time  
✅ **Team Collaboration** - Share secrets securely with team members  
✅ **Self-Hosted** - Complete control over your secrets (no cloud dependency)

## How We Use Infisical

### Architecture

```
┌─────────────────┐
│   Infisical UI  │  ← Manage secrets via web interface
│   (Port 8010)   │
└────────┬────────┘
         │
         │ Stores secrets in
         ▼
┌─────────────────┐
│   PostgreSQL     │  ← Infisical database (via Supabase)
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

### Integration Flow

1. **Secret Storage:**
   - Secrets are stored in Infisical (via web UI or CLI)
   - Organized by project and environment (development/production)

2. **Secret Export:**
   - `start_services.py` calls `export_infisical_secrets()`
   - Infisical CLI exports secrets to `.env.infisical` file
   - Format: Standard `.env` format (KEY=VALUE)

3. **Service Startup:**
   - Docker Compose reads `.env.infisical` as an env file
   - Services receive secrets as environment variables
   - Works seamlessly with existing Docker Compose setup

4. **Fallback:**
   - If Infisical is unavailable, falls back to `.env` file
   - Ensures services can start even if Infisical is down

### Code Integration

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

## Secret Synchronization

### How Secrets Are Synced

**From Infisical to Services:**

1. **Automatic Sync (Default):**
   ```bash
   python start_services.py --profile cpu
   # Automatically exports secrets from Infisical
   # Services use .env.infisical file
   ```

2. **Manual Export:**
   ```bash
   infisical export --format=dotenv > .env.infisical
   ```

3. **CLI Access:**
   ```bash
   infisical secrets  # View secrets
   infisical run -- your-command  # Run command with secrets
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

### Sync Workflow

**Initial Setup:**
1. Create `.env` file with all secrets (one-time)
2. Start Infisical: `python start_services.py`
3. Access Infisical UI: `http://localhost:8010`
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

## Benefits in Practice

### Security

- **No secrets in version control** - `.env` files only contain non-sensitive config
- **Encrypted storage** - Secrets encrypted at rest in PostgreSQL
- **Access control** - Who can access which secrets
- **Audit trail** - See who changed what and when

### Operational Efficiency

- **Single source of truth** - All secrets in one place
- **Easy rotation** - Update once, all services get new value
- **Environment separation** - Different secrets for dev/prod
- **Team collaboration** - Share secrets securely

### Developer Experience

- **Web UI** - No need to edit `.env` files manually
- **CLI integration** - Works with existing scripts
- **Automatic sync** - No manual copying needed
- **Fallback support** - Can still use `.env` if needed

## Migration Strategy

### Phase 1: Hybrid Approach (Current)

- Keep non-sensitive config in `.env`
- Store sensitive secrets in Infisical
- Services read from both (Infisical takes precedence)

**Benefits:**
- Gradual migration
- Can test Infisical without breaking existing setup
- Easy rollback if needed

### Phase 2: Full Migration (Future)

- All secrets in Infisical
- `.env` only for non-sensitive configuration
- Machine identities for automated access

**Benefits:**
- Complete security
- Centralized management
- Better auditability

## Usage Examples

### Viewing Secrets

**Via Web UI:**
1. Navigate to `http://localhost:8010`
2. Select project and environment
3. View all secrets in organized folders

**Via CLI:**
```bash
infisical secrets  # List all secrets
infisical secrets get POSTGRES_PASSWORD  # Get specific secret
```

### Updating Secrets

**Via Web UI:**
1. Navigate to secret in Infisical UI
2. Click "Edit"
3. Update value
4. Save

**Via CLI:**
```bash
infisical secrets set POSTGRES_PASSWORD "new-password"
```

### Adding New Secrets

**Via Web UI:**
1. Click "Add Secret"
2. Enter key and value
3. Select folder (optional)
4. Save

**Via CLI:**
```bash
infisical secrets set NEW_API_KEY "value"
```

## Troubleshooting

### Secrets Not Syncing

**Check Infisical CLI:**
```bash
infisical --version  # Verify CLI installed
infisical login      # Verify authentication
infisical init       # Verify project configured
```

**Check Export:**
```bash
infisical export --format=dotenv > .env.test
cat .env.test  # Verify secrets exported
```

**Check Service Logs:**
```bash
docker logs comfyui  # Check if service has secrets
```

### Infisical Not Starting

**Check Dependencies:**
- PostgreSQL must be running (via Supabase)
- Redis must be running (via Supabase)
- Check logs: `docker logs infisical`

**Check Configuration:**
- Verify `INFISICAL_ENCRYPTION_KEY` in `.env`
- Verify `INFISICAL_AUTH_SECRET` in `.env`
- Verify `INFISICAL_HOSTNAME` in `.env`

### Fallback to .env

If Infisical is unavailable, services automatically fall back to `.env`:

```bash
# Disable Infisical explicitly
python start_services.py --skip-infisical
```

## Best Practices

1. **Never commit secrets** - Use Infisical for all sensitive values
2. **Use environment separation** - Different secrets for dev/prod
3. **Rotate regularly** - Update secrets periodically
4. **Use machine identities** - For automated access (CI/CD)
5. **Audit access** - Review who accessed what secrets
6. **Backup Infisical data** - Infisical data is in PostgreSQL (already backed up)

## Related Documentation

- [Infisical Setup Guide](./setup.md) - Initial setup and configuration
- [Infisical Conflicts Guide](./conflicts.md) - Resolving Docker Compose conflicts
- [Environment Setup](../../utils/setup/env/README.md) - Setting up `.env` file
- [Main README](../../README.md) - Project overview
- [Infrastructure Documentation](../../00-infrastructure/docs/README.md) - Infrastructure stack overview

## References

- [Infisical Documentation](https://infisical.com/docs)
- [Infisical GitHub](https://github.com/Infisical/infisical)
- [Secret Management Best Practices](https://infisical.com/docs/documentation/platform/secret-management)

