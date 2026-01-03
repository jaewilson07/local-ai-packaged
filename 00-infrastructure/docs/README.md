# Infrastructure Stack Documentation

## Overview

The infrastructure stack provides core connectivity, security, and secret management services for the AI Homelab.

## Quick Links

- **[Quick Start Guide](./QUICK_START.md)** - Get started quickly
- **[Architecture Overview](./ARCHITECTURE.md)** - Detailed architecture documentation
- **[Infrastructure Status](./INFRASTRUCTURE_STATUS.md)** - Current status and configuration
- **[Stack Management](./STACK_MANAGEMENT.md)** - Managing stacks and services
- **[Architecture Decisions](./ARCHITECTURE_DECISIONS.md)** - Design decisions and rationale

## Service-Specific Documentation

### Cloudflare Tunnel
- **[Setup Guide](./cloudflare/setup.md)** - Setting up Cloudflare Tunnel
- **[Caddy Integration](./cloudflare/caddy-integration.md)** - How Caddy and Cloudflare work together
- **[Design Choices](./cloudflare/design-choices.md)** - Cloudflare design decisions
- **[Email Health](./cloudflare/email-health.md)** - Email DNS configuration

### Infisical
- **[Setup Guide](../../docs/infisical/setup.md)** - Setting up Infisical
- **[Usage Guide](../../docs/infisical/usage.md)** - Using Infisical for secrets
- **[Conflicts & Troubleshooting](../../docs/infisical/conflicts.md)** - Resolving Docker Compose conflicts

## Migration Documentation

- **[Refactor Summary](./migration/REFACTOR_SUMMARY.md)** - Summary of stack-based refactor
- **[Move Validation](./migration/MOVE_VALIDATION.md)** - Validation of directory moves

## Archive

Temporary review and status documents are archived in `docs/archive/`:
- Review summaries (merged into INFRASTRUCTURE_STATUS.md)
- Launch checklists (merged into INFRASTRUCTURE_STATUS.md)
- Status documents (merged into INFRASTRUCTURE_STATUS.md)

