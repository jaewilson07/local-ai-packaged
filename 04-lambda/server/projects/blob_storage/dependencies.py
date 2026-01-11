"""Dependencies for blob storage API."""

import logging
from typing import AsyncGenerator
from fastapi import Depends, HTTPException
from uuid import UUID

from server.projects.auth.dependencies import get_current_user, User
from server.projects.auth.services.minio_service import MinIOService
from server.projects.auth.config import config as auth_config

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
    except (ValueError, AttributeError) as e:
        logger.error(f"Invalid user ID: {user.uid if hasattr(user, 'uid') else 'unknown'}")
        raise HTTPException(status_code=400, detail="Invalid user ID format")
