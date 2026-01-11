# Security Considerations for Auth System

## Caddy Security Configuration

The system uses Cloudflare Tunnel, which means all traffic already comes through Cloudflare's network. Caddy is configured to trust Cloudflare IP ranges (see `00-infrastructure/caddy/Caddyfile` line 7).

**Current Setup:**
- Cloudflare Tunnel routes all traffic through Cloudflare's network
- Caddy trusts Cloudflare IP ranges for X-Forwarded-* headers
- No additional IP filtering needed when using Tunnel

**If Not Using Tunnel:**
If you're not using Cloudflare Tunnel and exposing Caddy directly, you should add IP filtering to only accept traffic from Cloudflare IP ranges. This can be done with a Caddy snippet:

```caddy
(cloudflare_only) {
    @not_cloudflare {
        not remote_ip 173.245.48.0/20 103.21.244.0/22 103.22.200.0/22 103.31.4.0/22 141.101.64.0/18 108.162.192.0/18 190.93.240.0/20 188.114.96.0/20 197.234.240.0/22 198.41.128.0/17 162.158.0.0/15 104.16.0.0/13 104.24.0.0/14 172.64.0.0/13 131.0.72.0/22
    }
    handle @not_cloudflare {
        respond "Forbidden" 403
    }
}
```

Then include `import cloudflare_only` in your API hostname block.

## JWT Validation Security

### Audience Tag Validation
The JWT validation **must** check the audience (`aud`) tag to prevent token reuse across applications. This is enforced in `JWTService.validate_and_extract_email()`.

**Configuration:**
- Set `CLOUDFLARE_AUD_TAG` to your application's unique AUD tag
- Get the AUD tag from Cloudflare One Dashboard > Applications > Your App > Basic Information

### Public Key Caching
Public keys are cached for 1 hour to reduce API calls to Cloudflare. Keys are automatically refreshed when cache expires.

**Security Note:** If Cloudflare rotates keys, cached keys may be invalid for up to 1 hour. This is acceptable for most use cases, but for critical applications, consider reducing cache TTL.

### Token Expiration
JWT tokens have expiration times set by Cloudflare Access. The validation automatically checks expiration and rejects expired tokens.

## Data Isolation Security

### Supabase
- Application-level filtering by `owner_email`
- Admin users bypass filtering (intentional for admin override)
- Consider enabling RLS with custom policies for additional security

### Neo4j
- All queries should be anchored to user node
- Admin users skip anchoring (intentional)
- Use `get_user_anchored_query()` helper to ensure proper anchoring

### MinIO
- User folders organized by UUID prefix
- Admin users can access all folders (intentional)
- Bucket permissions should restrict write access to service account only

## Error Handling

Authentication failures return appropriate HTTP status codes:
- `403 Forbidden`: Missing or invalid JWT header
- `401 Unauthorized`: Token validation failed (expired, invalid signature, etc.)

Error messages don't expose internal details to prevent information leakage.

## Provisioning Security

JIT provisioning failures are logged but don't block authentication. This ensures:
- Users can still access the system even if one data store is down
- Provisioning can be retried on subsequent requests
- System remains available during partial outages

**Security Consideration:** Ensure provisioning services have appropriate access controls to prevent unauthorized user creation.

## Admin Override

Admin users can view all data across all services. This is intentional for administrative purposes.

**Security Recommendations:**
- Limit admin role assignment to trusted users
- Consider audit logging for admin data access
- Implement role-based access control (RBAC) for fine-grained permissions

## Environment Variables

Sensitive configuration should be stored in:
- Infisical (recommended for production)
- `.env` file (development only, never commit)

Never hardcode secrets in code or commit them to version control.
