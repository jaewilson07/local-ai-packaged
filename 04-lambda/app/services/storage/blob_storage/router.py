"""Blob Storage REST API endpoint functions."""

import logging
from uuid import UUID

from app.services.storage.blob_storage.dependencies import BlobStorageDeps
from app.services.storage.blob_storage.models import (
    DeleteFileResponse,
    FileUrlResponse,
    ListFilesResponse,
    UploadFileResponse,
)
from app.services.storage.blob_storage.tools import (
    delete_file_tool,
    download_file_tool,
    get_file_url_tool,
    list_files_tool,
    upload_file_tool,
)

from app.core.context_helpers import create_run_context

logger = logging.getLogger(__name__)


async def upload_file_endpoint(
    user_id: UUID,
    file_data: bytes,
    filename: str,
    content_type: str | None = None,
) -> UploadFileResponse:
    """
    Upload file endpoint function for MCP tools.

    Args:
        user_id: User UUID
        file_data: File content as bytes
        filename: Filename
        content_type: Optional content type

    Returns:
        Upload response
    """
    deps = BlobStorageDeps.from_settings()
    await deps.initialize()

    try:
        ctx = create_run_context(deps)
        result = await upload_file_tool(
            ctx=ctx,
            user_id=user_id,
            file_data=file_data,
            filename=filename,
            content_type=content_type,
        )
        return result
    finally:
        await deps.cleanup()


async def list_files_endpoint(
    user_id: UUID,
    prefix: str | None = None,
) -> ListFilesResponse:
    """
    List files endpoint function for MCP tools.

    Args:
        user_id: User UUID
        prefix: Optional prefix to filter files

    Returns:
        List files response
    """
    deps = BlobStorageDeps.from_settings()
    await deps.initialize()

    try:
        ctx = create_run_context(deps)
        result = await list_files_tool(
            ctx=ctx,
            user_id=user_id,
            prefix=prefix,
        )
        return result
    finally:
        await deps.cleanup()


async def download_file_endpoint(
    user_id: UUID,
    filename: str,
) -> bytes:
    """
    Download file endpoint function for MCP tools.

    Args:
        user_id: User UUID
        filename: Filename to download

    Returns:
        File content as bytes
    """
    deps = BlobStorageDeps.from_settings()
    await deps.initialize()

    try:
        ctx = create_run_context(deps)
        result = await download_file_tool(
            ctx=ctx,
            user_id=user_id,
            filename=filename,
        )
        return result
    finally:
        await deps.cleanup()


async def delete_file_endpoint(
    user_id: UUID,
    filename: str,
) -> DeleteFileResponse:
    """
    Delete file endpoint function for MCP tools.

    Args:
        user_id: User UUID
        filename: Filename to delete

    Returns:
        Delete response
    """
    deps = BlobStorageDeps.from_settings()
    await deps.initialize()

    try:
        ctx = create_run_context(deps)
        result = await delete_file_tool(
            ctx=ctx,
            user_id=user_id,
            filename=filename,
        )
        return result
    finally:
        await deps.cleanup()


async def get_file_url_endpoint(
    user_id: UUID,
    filename: str,
    expires_in: int = 3600,
) -> FileUrlResponse:
    """
    Get file URL endpoint function for MCP tools.

    Args:
        user_id: User UUID
        filename: Filename to generate URL for
        expires_in: URL expiration time in seconds

    Returns:
        File URL response
    """
    deps = BlobStorageDeps.from_settings()
    await deps.initialize()

    try:
        ctx = create_run_context(deps)
        result = await get_file_url_tool(
            ctx=ctx,
            user_id=user_id,
            filename=filename,
            expires_in=expires_in,
        )
        return result
    finally:
        await deps.cleanup()
