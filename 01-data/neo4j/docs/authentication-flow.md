# Neo4j Authentication Flow

This document explains the two-step authentication process for accessing Neo4j through Cloudflare Access.

## Overview

Since Neo4j Community Edition does not support OIDC/SSO, users authenticate in two steps:

1. **Cloudflare Access** (Google OAuth) - Protects web UI access
2. **Neo4j Native Authentication** (username/password) - Required for database access

## Authentication Flow Diagram

```
User → Cloudflare Access (Google OAuth) → Neo4j Browser UI → Neo4j Native Auth → Neo4j Database
```

## Step-by-Step Process

### Step 1: Cloudflare Access Authentication

When a user visits `https://neo4j.datacrew.space`:

1. **Cloudflare Access Check**: Cloudflare verifies if the user is authenticated
2. **Google OAuth Prompt**: If not authenticated, user is redirected to Google OAuth
3. **Google Login**: User authenticates with their Google account
4. **Access Granted**: Cloudflare validates the user and forwards the request to Neo4j

**Headers Added by Cloudflare Access**:
- `CF-Access-Authenticated-User-Email`: User's email (e.g., `user@example.com`)
- `CF-Access-JWT-Assertion`: JWT token with user claims

### Step 2: Neo4j Native Authentication

After passing Cloudflare Access, the user reaches Neo4j Browser:

1. **Neo4j Login Screen**: User sees Neo4j's native login form
2. **Enter Credentials**: User enters Neo4j username and password
3. **Database Access**: Neo4j validates credentials and grants access

**Neo4j Credentials**:
- **Username**: `neo4j` (default) or custom username
- **Password**: Set via `NEO4J_AUTH` environment variable

## Configuration

### Neo4j Authentication

Neo4j authentication is configured via environment variable:

```yaml
# docker-compose.yml
environment:
  NEO4J_AUTH: ${NEO4J_AUTH:-neo4j/password}
```

**Format**: `username/password`

**Example**:
```bash
NEO4J_AUTH=neo4j/my-secure-password-here
```

### Secure Password Generation

Generate a strong password using the project's password generator:

```bash
python setup/generate-env-passwords.py
```

Or manually:

```bash
# XKCD-style passphrase (recommended)
xkcdpass -n 4

# Or random hex
openssl rand -hex 32
```

## User Experience

### First-Time Access

1. User visits `https://neo4j.datacrew.space`
2. Cloudflare Access prompts for Google OAuth
3. User authenticates with Google
4. User reaches Neo4j Browser login screen
5. User enters Neo4j credentials
6. User gains access to Neo4j Browser

### Subsequent Access

1. User visits `https://neo4j.datacrew.space`
2. Cloudflare Access checks session (24-hour duration)
3. If session valid: User proceeds directly to Neo4j Browser
4. If session expired: User re-authenticates with Google
5. User enters Neo4j credentials (if not remembered by browser)

## Session Management

### Cloudflare Access Session

- **Duration**: 24 hours (configurable)
- **Storage**: Cloudflare-managed session cookies
- **Scope**: Per application (Neo4j)

### Neo4j Session

- **Duration**: Browser session (until logout or browser close)
- **Storage**: Neo4j-managed session
- **Scope**: Neo4j Browser only

## Security Considerations

### Why Two-Step Authentication?

1. **Cloudflare Access**:
   - Controls who can access the Neo4j web UI
   - Provides identity-based access control
   - Adds security layer before Neo4j

2. **Neo4j Native Auth**:
   - Required for database access (Community Edition limitation)
   - Protects actual database operations
   - Cannot be bypassed

### Best Practices

1. **Strong Neo4j Password**: Use XKCD-style passphrase or strong random password
2. **Store Credentials Securely**: Use Infisical for production
3. **Regular Password Rotation**: Update Neo4j password periodically
4. **Monitor Access**: Review Cloudflare Access logs regularly

## Alternative: Single Sign-On (Enterprise Only)

If seamless SSO is required, consider upgrading to **Neo4j Enterprise Edition**:

- **OIDC/SSO Support**: Native integration with identity providers
- **Single Authentication**: Users authenticate once via Google OAuth
- **Database-Level Isolation**: Advanced security features
- **Cost**: Requires Enterprise license (contact Neo4j for pricing)

## Troubleshooting

### User Can't Authenticate with Google

- Verify Google OAuth is configured in Cloudflare Access
- Check that user's email is in the access policy
- Verify Google OAuth credentials are correct

### User Can't Log Into Neo4j

- Verify `NEO4J_AUTH` environment variable is set correctly
- Check Neo4j container logs: `docker logs neo4j`
- Ensure Neo4j container is running: `docker ps | grep neo4j`

### Session Expires Too Quickly

- Adjust Cloudflare Access session duration in application settings
- Check browser cookie settings
- Verify time synchronization

## Related Documentation

- [Cloudflare Access Setup](cloudflare-access-setup.md) - Initial setup guide
- [User Management](user-management.md) - Managing Neo4j user accounts
- [Data Isolation](data-isolation.md) - User-specific data access
