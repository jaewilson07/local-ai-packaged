# Auth Project - Cloudflare Access Authentication

This project implements centralized header-based authentication using Cloudflare Access (Zero Trust) with Just-In-Time (JIT) user provisioning and strict data isolation across multiple data stores.

## Related API Documentation

- **[API Strategy](../../../docs/API_STRATEGY.md)** - Route naming conventions, error handling, and API standards

## Overview

The auth system provides:
- **JWT Validation**: Validates Cloudflare Access JWTs from `Cf-Access-Jwt-Assertion` header
- **API Token Authentication**: Bearer tokens for headless automation (scripts, n8n, webhooks)
- **Internal Network Bypass**: Docker service communication via X-User-Email header
- **JIT Provisioning**: Automatically creates users in Supabase, Neo4j, and MinIO on first visit
- **Data Isolation**: Enforces user-scoped data access across all data stores
- **Admin Override**: Admins can view all data across all services

## Architecture

```
                              ┌─────────────────────────────────────────────┐
                              │           Authentication Layer              │
                              │                                             │
Browser ──────────────────────┼──► Cf-Access-Jwt-Assertion ──────┐         │
                              │                                   │         │
Python Scripts ───────────────┼──► Authorization: Bearer token ──┼──► get_current_user
                              │                                   │         │
n8n Workflows ────────────────┼──► Authorization: Bearer token ──┘         │
                              │                                             │
Docker Services ──────────────┼──► X-User-Email (internal network) ───────►│
                              │                                             │
                              └─────────────────────────────────────────────┘
                                                    │
                                                    ▼
                                    JIT Provisioning (Supabase, Neo4j, MinIO)
                                                    │
                                                    ▼
                                    Data Isolation Enforcement (RLS, User Anchoring)
```

## Authentication Methods

The system supports multiple authentication methods (in priority order):

### 1. Cloudflare Access JWT (Browser Access)

For browser-based access via Cloudflare Access:

```bash
curl -H "Cf-Access-Jwt-Assertion: <jwt-token>" https://api.example.com/api/me
```

### 2. API Token (Automation - Recommended for Scripts)

For headless automation (scripts, n8n, cron jobs, webhooks):

```bash
# Generate token once (requires existing auth)
curl -X POST https://api.example.com/api/me/token \
  -H "Cf-Access-Jwt-Assertion: <jwt>"
# Returns: {"token": "lat_abc123...", "created_at": "..."}

# Use token in automation
curl -H "Authorization: Bearer lat_abc123..." https://api.example.com/api/v1/...
```

Tokens are prefixed with `lat_` (Lambda API Token) for easy identification.

### 3. Internal Network (Docker Services)

For Docker container communication within the `ai-network`:

```bash
# From within Docker network
curl -H "X-User-Email: user@example.com" http://lambda-server:8000/api/v1/...
```

Internal network detection is based on IP ranges: `172.16.0.0/12`, `10.0.0.0/8`, `192.168.0.0/16`, `127.0.0.0/8`

### 4. Development Mode

For local development without authentication:

```bash
# Set environment variable
export DEV_MODE=true
export DEV_USER_EMAIL=dev@example.com

# Requests without auth headers will use DEV_USER_EMAIL
curl http://localhost:8000/api/me
```

## API Token Management

### Generate Primary Token

```bash
POST /api/me/token
```

Creates or regenerates the user's primary API token. The token is only returned once - store it securely!

**Response:**
```json
{
  "token": "lat_abc123def456...",
  "created_at": "2024-01-20T12:00:00Z",
  "message": "Token created successfully. Store it securely!"
}
```

### Get Token Info

```bash
GET /api/me/token
```

Returns token metadata (not the token itself).

**Response:**
```json
{
  "has_token": true,
  "created_at": "2024-01-20T12:00:00Z",
  "token_prefix": "lat_"
}
```

### Revoke Token

```bash
DELETE /api/me/token
```

Revokes the primary API token immediately.

### Named Tokens (Multiple Tokens)

For advanced use cases, you can create multiple named tokens with optional scopes and expiration:

```bash
# Create named token
POST /api/me/tokens
{
  "name": "n8n-production",
  "scopes": ["workflows:read", "workflows:execute"],
  "expires_in_days": 90
}

# List all named tokens
GET /api/me/tokens

# Revoke by ID or name
DELETE /api/me/tokens/{token_id}
DELETE /api/me/tokens/name/{token_name}
```

## Sample Script Authentication

For Python scripts, use the `sample/shared/auth_helpers.py` module:

```python
from sample.shared.auth_helpers import get_api_base_url, get_auth_headers

api_base_url = get_api_base_url()
headers = get_auth_headers()

response = requests.get(f"{api_base_url}/api/v1/endpoint", headers=headers)
```

**Environment Variables:**
- `LAMBDA_API_TOKEN` - API token for automation (preferred)
- `CF_ACCESS_JWT` - Cloudflare Access JWT (for external access)
- `CLOUDFLARE_EMAIL` - User email (for internal network identification)
- `API_BASE_URL` - API base URL (defaults to `http://lambda-server:8000`)

## Security Considerations

1. **Token Storage**: API tokens are stored hashed (SHA-256) in the database
2. **Token Prefix**: Tokens use `lat_` prefix for easy identification in logs
3. **Internal Network**: X-User-Email bypass only works from Docker network IP ranges
4. **Token Generation**: Requires existing authentication (JWT or existing token)
5. **Immediate Revocation**: Tokens can be revoked immediately via API
6. **Named Token Expiration**: Named tokens support optional expiration dates

## Configuration

### Required Environment Variables

```bash
# Cloudflare Access
CLOUDFLARE_AUTH_DOMAIN=https://<your-team>.cloudflareaccess.com
CLOUDFLARE_AUD_TAG=<your-audience-tag>

# Supabase
SUPABASE_DB_URL=postgresql://postgres:password@supabase-db:5432/postgres
SUPABASE_SERVICE_KEY=<service-role-key>  # Optional, for admin operations

# MinIO (Supabase Storage)
MINIO_ENDPOINT=http://supabase-minio:9020
MINIO_ACCESS_KEY=${SUPABASE_MINIO_ROOT_USER}
MINIO_SECRET_KEY=${SUPABASE_MINIO_ROOT_PASSWORD}
```

### Getting Your AUD Tag

**What is the AUD Tag?**

The **AUD Tag** (Application Audience Tag) is a unique 64-character hexadecimal identifier that Cloudflare generates for each Access application. It's used in JWT token validation to ensure tokens are only accepted from the correct application, preventing token reuse attacks.

**Why is it Required?**

When Cloudflare Access generates a JWT token for an authenticated user, it includes an `aud` (audience) claim set to your application's AUD tag. The Lambda server validates this claim matches your configured `CLOUDFLARE_AUD_TAG` before granting access. This ensures:

- Tokens from other Access applications are rejected
- Only tokens intended for your specific application are accepted
- Security is maintained even if someone obtains a valid JWT from a different application

**How to Get Your AUD Tag:**

**Method 1: Using the Script (Recommended)**
```bash
cd /home/jaewilson07/GitHub/local-ai-packaged
python3 00-infrastructure/scripts/get-lambda-api-aud-tag.py
```

This script automatically queries the Cloudflare API to retrieve the AUD tag for your application.

**Method 2: From Cloudflare Dashboard**
1. Go to [Cloudflare One Dashboard](https://one.dash.cloudflare.com/)
2. Navigate to **Access controls** > **Applications**
3. Select your application (e.g., "Lambda API" for `api.datacrew.space`)
4. In the **Basic information** tab, copy the **Application Audience (AUD) Tag**

**Method 3: From Cloudflare API**
```bash
curl -X GET "https://api.cloudflare.com/client/v4/accounts/{account_id}/access/apps" \
  -H "Authorization: Bearer YOUR_API_TOKEN" \
  | jq '.result[] | select(.domain=="api.datacrew.space") | .aud'
```

**Setting the AUD Tag:**

Once you have the AUD tag, configure it in your environment:

```bash
# In docker-compose.yml or .env
CLOUDFLARE_AUD_TAG=e869f0dbb027893e1c9ded98f81e6c85420c574098c895a51f79a1e9930c948c

# Or via Infisical (production)
infisical secrets set CLOUDFLARE_AUD_TAG=e869f0dbb027893e1c9ded98f81e6c85420c574098c895a51f79a1e9930c948c
```

**Current AUD Tag for Lambda API:**
```
e869f0dbb027893e1c9ded98f81e6c85420c574098c895a51f79a1e9930c948c
```

This is already configured in `04-lambda/docker-compose.yml` as a default value.

## Usage

### Option 1: FastAPI Dependency (Recommended)

Use the `get_current_user` dependency to protect endpoints explicitly:

```python
from fastapi import Depends
from server.projects.auth.dependencies import get_current_user
from server.projects.auth.models import User

@router.get("/protected")
async def protected_endpoint(user: User = Depends(get_current_user)):
    """This endpoint requires authentication."""
    return {"message": f"Hello, {user.email}!"}
```

### Option 2: Middleware (Optional)

For automatic protection of all routes (except excluded paths), you can use the middleware:

```python
# In main.py, add after CORS middleware:
from server.projects.auth.middleware import AuthMiddleware

app.add_middleware(
    AuthMiddleware,
    exclude_paths=["/health", "/docs", "/openapi.json", "/mcp", "/mcp-info", "/"],
    exclude_path_prefixes=["/static", "/public"]
)
```

**When using middleware:**
- All routes are automatically protected (except excluded paths)
- User is available in `request.state.user`
- Access user in endpoints:
  ```python
  @router.get("/protected")
  async def protected_endpoint(request: Request):
      user = request.state.user  # User object from middleware
      return {"message": f"Hello, {user.email}!"}
  ```

**Note:** You can use both middleware and dependencies together. Middleware provides automatic protection, while dependencies allow explicit control per endpoint.

### API Endpoints

#### `GET /api/me`

Returns the current user's profile.

**Response:**
```json
{
  "uid": "uuid-1234",
  "email": "alice@gmail.com",
  "role": "admin",
  "tier": "pro",
  "services_enabled": ["supabase", "immich", "n8n"]
}
```

#### `GET /api/me/data`

Get summary of data across all services the user has access to.

**Response:**
```json
{
  "rag": {
    "mongodb_documents": 150,
    "mongodb_chunks": 1200,
    "mongodb_sources": 25,
    "supabase_items": 50,
    "supabase_workflows": 10,
    "total_data_points": 1435
  },
  "immich": {
    "total_photos": 0,
    "total_videos": 0,
    "total_albums": 0,
    "total_size_bytes": 0,
    "message": "Immich API integration not yet implemented"
  },
  "loras": {
    "total_models": 5,
    "total_size_bytes": 52428800,
    "models": [...]
  }
}
```

#### `GET /api/me/data/rag`

Get RAG data summary across MongoDB and Supabase.

- Returns document counts, chunk counts, and source information
- Regular users see only their own data
- Admin users see all data

#### `GET /api/me/data/immich`

Get Immich data summary (placeholder - API integration pending).

- Returns photo/video counts and storage information

#### `GET /api/me/data/loras`

Get LoRA models summary.

- Returns count and metadata for all LoRA models
- Regular users see only their own models
- Admin users see all models

## JIT Provisioning

When a user authenticates for the first time:

1. **Supabase**: Creates a row in `profiles` table with:
   - `id`: UUID (auto-generated)
   - `email`: User email (unique)
   - `role`: "user" (default)
   - `tier`: "free" (default)
   - `created_at`: Current timestamp

2. **Neo4j**: Creates a `:User {email: "..."}` node

3. **MinIO**: Creates a user folder structure (`user-{uuid}/`)

4. **MongoDB**: Creates a MongoDB user with RBAC role for RAG collections

5. **Immich**: Creates an Immich user account and generates an API key
   - User created with email matching Cloudflare Access email
   - API key auto-generated and stored in `profiles.immich_api_key`
   - API key can be retrieved via `/api/me/immich/api-key` endpoint

Provisioning failures are logged but don't block authentication.

## Data Isolation

### Supabase

- Application-level filtering by `owner_email`
- Admin users bypass filtering
- RLS can be enabled for additional security (requires custom policies)

### Neo4j

- All queries should be anchored to user node: `MATCH (u:User {email: $email})`
- Use `get_user_anchored_query()` helper from `Neo4jService`
- Admin users skip anchoring

### MinIO

- User folders organized by UUID: `user-{uuid}/`
- Admin users can access all folders
- Bucket: `user-data` (shared bucket with prefix-based organization)

### Immich

- Each user has their own Immich account (1:1 mapping with Cloudflare Access email)
- API keys stored in `profiles.immich_api_key` column
- Users can retrieve their API key via `/api/me/immich/api-key` endpoint
- Admin users can access all Immich accounts (via admin API key)

## Admin Override

Users with `role: "admin"` in Supabase can:
- View all data in Supabase (bypasses filtering)
- View all nodes in Neo4j (skips user anchoring)
- View all images in MinIO (accesses all folders)

Check admin status:
```python
from server.projects.auth.services.auth_service import AuthService
from server.projects.auth.config import config

auth_service = AuthService(config)
is_admin = await auth_service.is_admin(user.email)
```

## Project Structure

```
src/services/auth/
├── __init__.py
├── config.py              # Project configuration
├── dependencies.py        # FastAPI dependencies
├── models.py              # Pydantic models
├── services/
│   ├── __init__.py
│   ├── jwt_service.py     # JWT validation
│   ├── supabase_service.py # User provisioning & management
│   ├── neo4j_service.py  # Neo4j provisioning & anchoring
│   ├── minio_service.py   # MinIO provisioning
│   ├── mongodb_service.py # MongoDB provisioning
│   └── auth_service.py    # Auth helpers (admin checks)
└── README.md

# Note: ImmichService is located in services/external/immich/client.py
# and is used for Immich user provisioning during JIT authentication.
```

## Security Considerations

1. **JWT Validation**: Always validates signature, audience, and issuer
2. **Public Key Caching**: Keys cached for 1 hour to reduce API calls
3. **Error Handling**: Authentication failures return 401/403, don't expose internals
4. **Caddy Security**: Should be configured to only accept traffic from Cloudflare IPs or via Tunnel

## Testing

### Manual Testing

1. **Get a valid JWT**: Access your application through Cloudflare Access
2. **Test /api/me**:
   ```bash
   curl -H "Cf-Access-Jwt-Assertion: <token>" http://localhost:8000/api/me
   ```

3. **Test data isolation**: Create test data for different users and verify isolation

### Data Summary Endpoints

- `/api/me/data`: Get complete data summary across all services
- `/api/me/data/rag`: Get RAG data summary (MongoDB + Supabase)
- `/api/me/data/immich`: Get Immich data summary (placeholder)
- `/api/me/data/loras`: Get LoRA models summary
- `/api/me/immich/api-key`: Get user's Immich API key (provisions on-demand if missing)
- `/api/me/discord/link`: Link Discord account to Cloudflare-authenticated user

## Troubleshooting

### JWT Validation Fails

- Check `CLOUDFLARE_AUTH_DOMAIN` is correct
- Verify `CLOUDFLARE_AUD_TAG` matches your application's AUD tag
- Ensure JWT is from the correct Cloudflare Access application

### Provisioning Fails

- Check database connections (Supabase, Neo4j)
- Verify MinIO credentials and endpoint
- Check logs for specific error messages
- Note: Provisioning failures don't block authentication

### Data Isolation Issues

- Verify user email matches in all queries
- Check admin status if expecting to see all data
- Ensure queries use user anchoring for Neo4j

## Immich Integration

Immich users are automatically provisioned during JIT authentication:

1. **User Creation**: Immich user created with email matching Cloudflare Access email
2. **API Key Generation**: API key auto-generated and stored in Supabase `profiles` table
3. **Retrieval**: Users can get their API key via `/api/me/immich/api-key` endpoint
4. **Discord Bot**: Discord bot can upload to user-specific Immich accounts (requires Discord account linking)

### Configuration

Required environment variables:
- `IMMICH_SERVER_URL`: Immich server URL (default: `http://immich-server:2283`)
- `IMMICH_ADMIN_API_KEY`: Admin API key for user provisioning (get from Immich admin panel)

### Discord Account Linking

Users can link their Discord account to their Cloudflare-authenticated account:

**Via Discord Bot (Recommended):**
1. In Discord, use the `/link_discord` slash command
2. Enter your Cloudflare Access email when prompted
3. Discord bot calls Lambda API to link accounts

**Via API (Direct):**
1. Authenticate via Cloudflare Access (browser) or API token
2. Call `POST /api/v1/auth/me/discord/link` with `discord_user_id` parameter
3. Discord user ID stored in `profiles.discord_user_id` column

**After Linking:**
- Discord bot can look up users by Discord ID via `GET /api/v1/auth/user/by-discord/{discord_user_id}`
- Bot retrieves user's Immich API key for personal uploads
- Uploads go to user's personal Immich library instead of shared account

### Discord Bot Authentication

The Discord bot can authenticate with Lambda API in two ways:

1. **Bearer Token (Recommended for production)**:
   ```bash
   # Generate token via Cloudflare Access authenticated session
   POST /api/v1/auth/me/token

   # Discord bot uses token in requests
   Authorization: Bearer lat_abc123...
   ```

2. **Internal Network (Docker only)**:
   ```bash
   # From within ai-network Docker network
   X-User-Email: bot-owner@example.com
   ```

Configure in Discord bot's environment:
- `LAMBDA_API_TOKEN`: API token for external access (preferred)
- `CLOUDFLARE_EMAIL`: Fallback for internal network auth

## Future Enhancements

- [ ] Supabase RLS policies with session variables
- [ ] Immich API integration for image statistics (currently placeholder)
- [ ] User role/tier management endpoints
- [ ] Audit logging for data access
- [ ] Rate limiting per user
