"""Dependencies for blob storage API."""

import logging
from uuid import UUID

from fastapi import Depends, HTTPException

from server.projects.auth.config import config as auth_config
from server.projects.auth.dependencies import User, get_current_user
from server.projects.auth.services.minio_service import MinIOService

logger = logging.getLogger(__name__)


def get_minio_service() -> MinIOService:
    """
    Get MinIO service instance.

    Returns:
        MinIOService instance
    """
    return MinIOService(auth_config)


async def get_user_id(user: User = Depends(get_current_user)) -> UUID:
    """
    Extract user ID from authenticated user.

    Args:
        user: Authenticated user from get_current_user dependency

    Returns:
        User UUID

    Raises:
        HTTPException: If user ID is invalid
    """
    try:
        return UUID(user.uid)
    except (ValueError, AttributeError):
        logger.exception(f"Invalid user ID: {user.uid if hasattr(user, 'uid') else 'unknown'}")
        raise HTTPException(status_code=400, detail="Invalid user ID format")
