# Authentication Samples

This directory contains sample scripts for testing and demonstrating the Lambda API authentication system.

## Authentication Methods

The Lambda API supports multiple authentication methods (in priority order):

1. **Cloudflare Access JWT** - For browser-based external access through Cloudflare
2. **Bearer Token (API Token)** - For headless automation and scripts
3. **Internal Network (X-User-Email)** - For Docker service-to-service communication
4. **Development Mode** - Bypass authentication when `DEV_MODE=true`

## Scripts

### test_token_flow.py

End-to-end test for the API token authentication flow. Tests:
- Internal network authentication (X-User-Email)
- Token generation (primary and named tokens)
- Token authentication (Bearer token)
- Token info retrieval
- Protected endpoint access
- Token revocation

**Usage:**

```bash
# Run full test (generates token, tests, then revokes)
API_BASE_URL=http://localhost:8000 python test_token_flow.py

# Keep the token after testing (don't revoke)
python test_token_flow.py --keep-token

# Also test named token creation/revocation
python test_token_flow.py --test-named

# Test with an existing token
LAMBDA_API_TOKEN=lat_xxx python test_token_flow.py --use-existing
```

**Environment Variables:**
- `API_BASE_URL` - API base URL (defaults to http://localhost:8000)
- `CLOUDFLARE_EMAIL` - User email for internal network auth (loaded from .env)
- `LAMBDA_API_TOKEN` - Existing API token (when using --use-existing)

## Token Management API

### Generate Primary Token

```bash
# Using internal network auth
curl -X POST -H "X-User-Email: your@email.com" http://localhost:8000/api/me/token
```

Response:
```json
{
  "token": "lat_abc123...",
  "created_at": "2026-01-20T00:00:00Z"
}
```

### Get Token Info

```bash
curl -H "Authorization: Bearer lat_xxx..." http://localhost:8000/api/me/token
```

### Create Named Token

```bash
curl -X POST \
  -H "Authorization: Bearer lat_xxx..." \
  -H "Content-Type: application/json" \
  -d '{"name": "my-automation", "scopes": ["read", "write"]}' \
  http://localhost:8000/api/me/tokens
```

### List Named Tokens

```bash
curl -H "Authorization: Bearer lat_xxx..." http://localhost:8000/api/me/tokens
```

### Revoke Primary Token

```bash
curl -X DELETE -H "X-User-Email: your@email.com" http://localhost:8000/api/me/token
```

### Revoke Named Token

```bash
# By name
curl -X DELETE -H "Authorization: Bearer lat_xxx..." \
  http://localhost:8000/api/me/tokens/name/my-automation

# By ID
curl -X DELETE -H "Authorization: Bearer lat_xxx..." \
  http://localhost:8000/api/me/tokens/abc123-uuid
```

## Using Tokens in Scripts

```python
from sample.shared.auth_helpers import get_api_base_url, get_auth_headers

# Set LAMBDA_API_TOKEN environment variable
# export LAMBDA_API_TOKEN=lat_xxx...

api_base_url = get_api_base_url()
headers = get_auth_headers()  # Automatically uses LAMBDA_API_TOKEN

response = requests.get(f"{api_base_url}/api/v1/endpoint", headers=headers)
```

## Token Security

- Tokens start with `lat_` prefix for easy identification
- Tokens are stored as SHA-256 hashes in the database
- Primary tokens can be regenerated (old token is invalidated)
- Named tokens support scopes and expiration (optional)
- Revoked tokens are immediately rejected
