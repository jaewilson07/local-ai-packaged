# Neo4j Cloudflare Access Setup Guide

This guide explains how to set up Cloudflare Access protection for Neo4j Browser UI, enabling Google OAuth authentication before users reach Neo4j.

## Overview

Since Neo4j Community Edition does not support OIDC/SSO natively, we use a **layered protection approach**:

1. **Cloudflare Access**: Protects the web UI with Google OAuth
2. **Neo4j Native Auth**: Users still authenticate with Neo4j username/password

This provides an additional security layer while maintaining compatibility with Community Edition.

## Prerequisites

- Cloudflare account with Zero Trust enabled
- Google OAuth identity provider configured in Cloudflare Access
- Standard reusable access policy created (see `manage-cloudflare-access.py`)
- Neo4j tunnel route configured (see `setup-cloudflare-tunnel-routes.py`)

## Quick Setup

### Automated Setup (Recommended)

Run the setup script:

```bash
cd /home/jaewilson07/GitHub/local-ai-packaged
python 00-infrastructure/scripts/setup-neo4j-access.py
```

This script will:
- ✅ Create Cloudflare Access application for `neo4j.datacrew.space`
- ✅ Link to standard reusable access policy (if available)
- ✅ Link Access application to tunnel route

### Manual Setup

If you prefer to set up manually:

1. **Create Access Application**:
   - Go to https://one.dash.cloudflare.com/
   - Access → Applications → Add an application
   - Select **Self-hosted**
   - Configure:
     - Application name: `Neo4j`
     - Application domain: `neo4j.datacrew.space`
     - Session duration: `24 hours` (or your preference)

2. **Add Access Policy**:
   - Go to the Neo4j application → Policies
   - Click **Add a policy**
   - Select **Standard Access Policy** (reusable policy)
   - Or create a new policy with your access rules

3. **Link to Tunnel Route**:
   - Go to Networks → Tunnels → Your tunnel
   - Configure → Public Hostnames
   - Find route for `neo4j.datacrew.space`
   - Click **Edit**
   - Under **Access**, select **Neo4j** application
   - Click **Save**

## Verification

1. **Check Access Application**:
   ```bash
   # List all applications
   python 00-infrastructure/scripts/manage-cloudflare-access.py --list
   ```

2. **Test Access**:
   - Visit https://neo4j.datacrew.space
   - You should be prompted to authenticate with Google OAuth
   - After authentication, you'll reach Neo4j Browser
   - You'll still need to log in with Neo4j credentials

## Configuration Details

### Access Application Settings

- **Domain**: `neo4j.datacrew.space`
- **Type**: Self-hosted
- **Session Duration**: 24 hours (configurable)
- **Policy**: Standard Access Policy (reusable)

### Cloudflare Access Headers

When a user authenticates via Cloudflare Access, the following headers are added to requests:

- `CF-Access-Authenticated-User-Email`: User's email address
- `CF-Access-JWT-Assertion`: JWT token with user claims

These headers can be used by application code to identify the authenticated user.

## Troubleshooting

### Access Application Not Created

- Verify Cloudflare API credentials are correct
- Check that you have Access permissions in your API token
- Ensure account ID is correct

### Access Not Prompting for Authentication

- Verify Access application is linked to tunnel route
- Check that access policy is configured correctly
- Clear browser cache and cookies
- Verify tunnel route is active

### Users Can't Access After Authentication

- Check Neo4j container is running: `docker ps | grep neo4j`
- Verify Caddy routing: `docker logs caddy | grep neo4j`
- Check Neo4j logs: `docker logs neo4j`

## Next Steps

After setting up Cloudflare Access:

1. **Configure Neo4j Authentication**: See [Authentication Flow](authentication-flow.md)
2. **Set Up Data Isolation**: See [Data Isolation](data-isolation.md)
3. **Configure Programmatic Access**: See [Bolt API Authentication](bolt-api-authentication.md)

## Related Documentation

- [Authentication Flow](authentication-flow.md) - Two-step authentication process
- [Data Isolation](data-isolation.md) - User-specific data access patterns
- [User Management](user-management.md) - Managing Neo4j user accounts
- [Bolt API Authentication](bolt-api-authentication.md) - Programmatic access guide

