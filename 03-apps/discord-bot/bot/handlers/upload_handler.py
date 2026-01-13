"""
DEPRECATED: Legacy upload handler.

This module is deprecated. Upload logic has been migrated to:
    bot.capabilities.upload.UploadCapability

This file is kept for backward compatibility only.
"""

import logging
import warnings

from discord import Message

from bot.immich_client import ImmichClient

logger = logging.getLogger(__name__)

# Emit deprecation warning when module is imported
warnings.warn(
    "bot.handlers.upload_handler is deprecated. "
    "Use bot.capabilities.upload.UploadCapability instead.",
    DeprecationWarning,
    stacklevel=2,
)


async def handle_upload(message: Message, immich_client: ImmichClient) -> None:
    """
    DEPRECATED: Handle file upload from Discord message.

    This function is deprecated. Upload logic has been migrated to
    UploadCapability._handle_uploads().

    Args:
        message: The Discord message
        immich_client: The Immich client for uploading files
    """
    warnings.warn(
        "handle_upload() is deprecated. Use UploadCapability instead.",
        DeprecationWarning,
        stacklevel=2,
    )

    # Import here to avoid circular imports
    from bot.capabilities.upload import UploadCapability

    # Create a temporary capability instance to delegate
    # This maintains backward compatibility while encouraging migration
    capability = UploadCapability(client=None, immich_client=immich_client)  # type: ignore
    await capability._handle_uploads(message)
