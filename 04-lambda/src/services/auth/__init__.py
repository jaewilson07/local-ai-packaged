"""Authentication and identity management project.

This module provides authentication services for the Lambda server,
including JWT validation, user provisioning, and access control.
"""

# Core auth components
from .config import AuthConfig
from .dependencies import get_current_user

# Sub-services (organized imports)
from .jwt import JWTService
from .middleware import AuthMiddleware
from .models import User
from .router import router as auth_router

# Keep backward compatibility with old import paths
from .services.auth_service import AuthService

__all__ = [
    "AuthConfig",
    "AuthMiddleware",
    "AuthService",
    "JWTService",
    "User",
    "auth_router",
    "get_current_user",
]
