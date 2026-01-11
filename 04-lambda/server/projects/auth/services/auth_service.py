"""Authentication helper service."""

import logging

from server.projects.auth.config import AuthConfig
from server.projects.auth.services.supabase_service import SupabaseService

logger = logging.getLogger(__name__)


class AuthService:
    """Helper service for authentication operations."""

    def __init__(self, config: AuthConfig):
        """
        Initialize auth service.

        Args:
            config: Auth configuration
        """
        self.config = config
        self.supabase_service = SupabaseService(config)

    async def is_admin(self, email: str) -> bool:
        """
        Check if user is an admin.

        Args:
            email: User email address

        Returns:
            True if user has admin role, False otherwise
        """
        return await self.supabase_service.is_admin(email)
