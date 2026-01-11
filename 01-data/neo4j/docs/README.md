# Neo4j Documentation

This directory contains documentation for Neo4j setup, authentication, and data isolation when using Cloudflare Access.

## Overview

Neo4j is configured with Cloudflare Access protection for the web UI, while using native authentication for database access. Since Neo4j Community Edition does not support OIDC/SSO, we use a layered protection approach.

## Documentation Index

### Setup Guides

- **[Cloudflare Access Setup](cloudflare-access-setup.md)** - Initial setup guide for protecting Neo4j with Cloudflare Access
  - Automated setup script
  - Manual setup instructions
  - Verification steps

### Authentication

- **[Authentication Flow](authentication-flow.md)** - Two-step authentication process
  - Cloudflare Access (Google OAuth)
  - Neo4j native authentication
  - Session management
  - Security considerations

### Data Management

- **[Data Isolation](data-isolation.md)** - Ensuring users only access their own data
  - Property-based filtering (recommended)
  - Relationship-based isolation
  - Label-based isolation
  - Implementation examples (Python, JavaScript)
  - Security best practices

- **[User Management](user-management.md)** - Managing Neo4j user accounts
  - Shared account strategy (recommended)
  - Per-user accounts strategy
  - User provisioning
  - Password management

### Programmatic Access

- **[Bolt API Authentication](bolt-api-authentication.md)** - Programmatic access guide
  - Connection methods
  - Authentication patterns
  - Extracting user identity
  - Complete examples (Python, JavaScript)
  - Security best practices

## Quick Start

1. **Set up Cloudflare Access**:
   ```bash
   python 00-infrastructure/scripts/setup-neo4j-access.py
   ```

2. **Configure Neo4j authentication**:
   - Set `NEO4J_AUTH` in `.env` or Infisical
   - Format: `username/password`

3. **Implement data isolation**:
   - See [Data Isolation](data-isolation.md) for patterns
   - Always filter queries by `userId`

4. **Test access**:
   - Visit `https://neo4j.datacrew.space`
   - Authenticate with Google OAuth
   - Log in with Neo4j credentials

## Architecture

```
User → Cloudflare Access (Google OAuth) → Neo4j Browser UI → Neo4j Native Auth → Neo4j Database
                                                                    ↓
                                                          Application Layer (data isolation)
                                                                    ↓
                                                          Bolt API (native auth)
```

## Key Concepts

### Two-Step Authentication

1. **Cloudflare Access**: Protects web UI, authenticates via Google OAuth
2. **Neo4j Native Auth**: Required for database access (Community Edition limitation)

### Data Isolation

- **Application-Layer**: All queries filtered by `userId` property
- **User Identity**: Extracted from Cloudflare Access headers
- **Pattern**: Property-based filtering (recommended)

### User Management

- **Shared Account**: All users share Neo4j credentials (recommended)
- **Per-User Accounts**: Each user has own Neo4j account (complex)

## Related Scripts

- `00-infrastructure/scripts/setup-neo4j-access.py` - Create Cloudflare Access application
- `00-infrastructure/scripts/setup-cloudflare-tunnel-routes.py` - Configure tunnel routes
- `00-infrastructure/scripts/manage-cloudflare-access.py` - Manage access policies

## Troubleshooting

### Access Issues

- Verify Cloudflare Access application is created and linked
- Check tunnel route configuration
- Verify access policy is applied

### Authentication Issues

- Verify `NEO4J_AUTH` environment variable is set
- Check Neo4j container is running
- Review Neo4j logs: `docker logs neo4j`

### Data Isolation Issues

- Ensure all queries filter by `userId`
- Verify user identity is extracted from headers
- Check application logs for query patterns

## Additional Resources

- [Neo4j Operations Manual](https://neo4j.com/docs/operations-manual/current/)
- [Neo4j Python Driver](https://neo4j.com/docs/python-manual/current/)
- [Cloudflare Access Documentation](https://developers.cloudflare.com/cloudflare-one/policies/access/)
