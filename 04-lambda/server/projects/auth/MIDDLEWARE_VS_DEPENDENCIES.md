# Authentication: Middleware vs Dependencies

This document explains when to use middleware vs dependencies for authentication in the Lambda server.

## Current Setup

✅ **Cloudflare Access is configured** for `api.datacrew.space`
- Access application created and linked to tunnel route
- JWT tokens are automatically injected by Cloudflare Access
- All requests to `api.datacrew.space` require Cloudflare Access authentication

## Two Approaches

### 1. Dependency-Based (Current/Recommended)

**Status:** ✅ Currently implemented and working

**How it works:**
- Explicitly add `Depends(get_current_user)` to endpoints that need auth
- Endpoints without the dependency are publicly accessible
- Full control over which endpoints require authentication

**Example:**
```python
from fastapi import Depends
from server.projects.auth.dependencies import get_current_user
from server.projects.auth.models import User

@router.get("/protected")
async def protected_endpoint(user: User = Depends(get_current_user)):
    return {"message": f"Hello, {user.email}!"}

@router.get("/public")
async def public_endpoint():
    # No auth required
    return {"message": "Public endpoint"}
```

**Pros:**
- ✅ Explicit and clear - you can see which endpoints require auth
- ✅ Flexible - mix protected and public endpoints easily
- ✅ Easy to test - can mock dependencies in tests
- ✅ FastAPI best practice

**Cons:**
- ⚠️ Must remember to add dependency to each protected endpoint
- ⚠️ Easy to accidentally expose an endpoint without auth

### 2. Middleware-Based (Optional Enhancement)

**Status:** ✅ Available but not enabled by default

**How it works:**
- Automatically validates JWT for all routes (except excluded paths)
- Adds user to `request.state.user` for easy access
- Can be combined with dependencies for fine-grained control

**Example:**
```python
# In main.py
from server.projects.auth.middleware import AuthMiddleware

app.add_middleware(
    AuthMiddleware,
    exclude_paths=["/health", "/docs", "/openapi.json", "/mcp", "/"],
    exclude_path_prefixes=["/static"]
)

# In endpoints
from fastapi import Request

@router.get("/protected")
async def protected_endpoint(request: Request):
    user = request.state.user  # Automatically set by middleware
    return {"message": f"Hello, {user.email}!"}
```

**Pros:**
- ✅ Automatic protection - all routes protected by default
- ✅ Less boilerplate - don't need to add dependency to each endpoint
- ✅ Centralized error handling
- ✅ User available in request state

**Cons:**
- ⚠️ Must explicitly exclude public endpoints
- ⚠️ Less explicit - harder to see which endpoints are protected
- ⚠️ Can be harder to test (need to mock middleware)

## Recommendation

**Use Dependencies (Current Approach):**
- ✅ Already implemented and working
- ✅ More explicit and maintainable
- ✅ Better for mixed public/protected APIs
- ✅ Easier to test

**Consider Middleware If:**
- You want "secure by default" (all routes protected except exclusions)
- Most/all endpoints require authentication
- You want centralized auth error handling
- You're building an internal API where everything should be protected

## Using Both Together

You can use both approaches together:

```python
# Middleware provides automatic protection
app.add_middleware(AuthMiddleware, exclude_paths=["/health", "/docs"])

# Dependencies provide explicit control for special cases
@router.get("/admin-only")
async def admin_endpoint(
    request: Request,
    user: User = Depends(get_current_user)  # Explicit dependency
):
    # Middleware already validated and set request.state.user
    # Dependency provides explicit type hint and can add additional checks
    if user.role != "admin":
        raise HTTPException(403, "Admin only")
    return {"admin": True}
```

## Current Implementation Status

- ✅ **Cloudflare Access**: Configured and linked to tunnel route
- ✅ **Dependency-based auth**: Implemented and working
- ✅ **Middleware-based auth**: Available but not enabled
- ✅ **JWT validation**: Working with Cloudflare Access
- ✅ **JIT provisioning**: Working for Supabase, Neo4j, MinIO

## Next Steps

1. **Keep using dependencies** (recommended) - explicit and maintainable
2. **Or enable middleware** if you want automatic protection:
   ```python
   # In main.py, uncomment and add:
   from server.projects.auth.middleware import AuthMiddleware

   app.add_middleware(
       AuthMiddleware,
       exclude_paths=["/health", "/docs", "/openapi.json", "/mcp", "/mcp-info", "/"]
   )
   ```

## Testing

Both approaches can be tested:

**Dependency testing:**
```python
from unittest.mock import patch
from server.projects.auth.dependencies import get_current_user

@patch("server.projects.auth.dependencies.JWTService")
async def test_endpoint(mock_jwt):
    # Mock JWT validation
    ...
```

**Middleware testing:**
```python
from fastapi.testclient import TestClient

client = TestClient(app)
response = client.get(
    "/protected",
    headers={"Cf-Access-Jwt-Assertion": "valid-jwt"}
)
```
