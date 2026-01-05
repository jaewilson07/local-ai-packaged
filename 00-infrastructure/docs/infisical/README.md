# Infisical Documentation

Documentation for Infisical secret management in the local-ai-packaged project.

## Overview

Infisical is an open-source secret management platform that provides centralized, secure storage for all sensitive configuration values. We use it to:

- Store passwords, API keys, and encryption keys securely
- Manage secrets across different environments (development/production)
- Provide audit logging and version history
- Enable team collaboration on secret management
- Self-hosted solution with complete control over your secrets

## Documentation Structure

This folder contains comprehensive documentation organized into focused guides:

### Core Documentation

1. **[setup.md](./setup.md)** - Initial Setup and Configuration
   - Prerequisites and installation
   - Generating encryption keys
   - Configuring hostname and HTTPS
   - Starting services
   - Creating admin account and organization
   - Cloudflare Tunnel setup (optional)
   - Google OAuth/SSO setup (optional)
   - CLI authentication

2. **[usage.md](./usage.md)** - Day-to-Day Operations
   - How secrets are synced
   - Adding, viewing, and updating secrets (UI and CLI)
   - Using with start_services.py
   - Migration strategy
   - Best practices
   - Quick reference commands

3. **[design.md](./design.md)** - Architecture and Design Decisions
   - Problem statement and why Infisical
   - Architecture overview
   - Integration with local-ai-packaged
   - Service dependencies
   - Network architecture
   - Security model
   - Benefits and trade-offs

4. **[troubleshooting_configuration.md](./troubleshooting_configuration.md)** - Comprehensive Troubleshooting
   - Docker Compose conflicts
   - Connection issues (HTTP errors, login loops)
   - Authentication problems (CLI, UI, machine identity)
   - Infrastructure issues
   - Diagnostic commands reference
   - Troubleshooting decision tree
   - Historical troubleshooting sessions

### Additional Resources

- **[INFRASTRUCTURE_STATUS.md](./INFRASTRUCTURE_STATUS.md)** - Infrastructure stack status and verification
- **[setup-project.py](./setup-project.py)** - Automated setup script for Infisical project

## Quick Start

### New Users

1. Start with [setup.md](./setup.md) to install and configure Infisical
2. Follow the setup guide to create your admin account and organization
3. Read [usage.md](./usage.md) to learn how to manage secrets
4. Refer to [troubleshooting_configuration.md](./troubleshooting_configuration.md) if you encounter issues

### Existing Users

- **Managing secrets**: See [usage.md](./usage.md)
- **Troubleshooting**: See [troubleshooting_configuration.md](./troubleshooting_configuration.md)
- **Understanding architecture**: See [design.md](./design.md)

## Common Tasks

### Initial Setup
```bash
# Generate encryption keys
python 00-infrastructure/scripts/generate-env-passwords.py

# Start services
python start_services.py --profile cpu

# Access Infisical UI
# http://localhost:8020 (local)
# https://infisical.datacrew.space (production)
```

### Managing Secrets
```bash
# Login to CLI
infisical login --host=https://infisical.datacrew.space

# Initialize project
infisical init

# Add a secret
infisical secrets set KEY "value"

# Export secrets
infisical export --format=dotenv
```

### Troubleshooting
```bash
# Check services
docker ps | grep infisical

# View logs
docker logs infisical-backend --tail 50

# Test health
docker exec infisical-backend wget -qO- http://localhost:8080/api/health
```

## Service URLs

- **Local UI**: `http://localhost:8020`
- **Production UI**: `https://infisical.datacrew.space`
- **Admin Signup**: `/admin/signup`
- **Health Check**: `/api/health`

## Container Names

- `infisical-backend` - Main Infisical application
- `infisical-db` - PostgreSQL database
- `infisical-redis` - Redis cache

## Related Documentation

- [Infrastructure AGENTS.md](../../AGENTS.md) - Infrastructure stack rules and patterns
- [Environment Setup](../../../utils/setup/env/README.md) - Setting up `.env` file
- [Main README](../../../README.md) - Project overview
- [Infisical Official Documentation](https://infisical.com/docs)

## Support

For issues and questions:
1. Check [troubleshooting_configuration.md](./troubleshooting_configuration.md)
2. Review [Infisical Official Documentation](https://infisical.com/docs)
3. Check [Infisical GitHub Issues](https://github.com/Infisical/infisical/issues)
