"""Authentication and identity management project.

This module provides authentication services for the Lambda server,
including JWT validation, user provisioning, and access control.

Import specific items from submodules:
    from services.auth.config import AuthConfig
    from services.auth.dependencies import get_current_user
    from services.auth.models import User
    from services.auth.router import router
"""

# Only export safe leaf items that don't cause circular imports
from .config import AuthConfig
from .models import User

__all__ = [
    "AuthConfig",
    "User",
]
