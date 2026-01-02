# Documentation Index

This directory contains comprehensive documentation for the Local AI Package project.

## Architecture Documentation

- **[modular-compose-architecture.md](modular-compose-architecture.md)** - Complete guide to the modular Docker Compose architecture, including directory structure, component details, network configuration, and usage examples.

- **[ARCHITECTURE_DECISIONS.md](ARCHITECTURE_DECISIONS.md)** - Detailed explanation of why the modular architecture was chosen, including the problems it solves and the design decisions made.

- **[QUICK_START.md](QUICK_START.md)** - Quick reference guide for common operations with the modular compose architecture.

## Service-Specific Documentation

### Supabase
- **[supabase/README.md](supabase/README.md)** - Supabase integration overview
- **[supabase/storage.md](supabase/storage.md)** - Supabase storage configuration
- **[supabase/docker-directory-requirements.md](supabase/docker-directory-requirements.md)** - Requirements for Supabase docker directory

### Infisical
- **[infisical/README.md](infisical/README.md)** - Infisical secret management overview
- **[infisical/setup.md](infisical/setup.md)** - Infisical setup and migration guide
- **[infisical/usage.md](infisical/usage.md)** - Using Infisical for secret management

### Cloudflare
- **[cloudflare/setup.md](cloudflare/setup.md)** - Cloudflare Tunnel setup
- **[cloudflare/caddy-integration.md](cloudflare/caddy-integration.md)** - Caddy reverse proxy configuration
- **[cloudflare/design-choices.md](cloudflare/design-choices.md)** - Design decisions for Cloudflare integration
- **[cloudflare/email-health.md](cloudflare/email-health.md)** - Email health monitoring

## Getting Started

1. Start with the [Quick Start Guide](QUICK_START.md) for immediate usage
2. Read [modular-compose-architecture.md](modular-compose-architecture.md) to understand the architecture
3. Refer to service-specific docs as needed

## Migration

If you're migrating from the old architecture:
- See [MIGRATION_NOTES.md](../MIGRATION_NOTES.md) in the project root
- Review [archive/README.md](../archive/README.md) for archived files
- Check [ARCHITECTURE_DECISIONS.md](ARCHITECTURE_DECISIONS.md) for why changes were made
