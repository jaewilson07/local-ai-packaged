"""Core capability tools for Blob Storage project."""

import logging
import mimetypes
from uuid import UUID

from pydantic_ai import RunContext
from services.storage.blob_storage.dependencies import BlobStorageDeps
from services.storage.blob_storage.models import (
    DeleteFileResponse,
    FileMetadata,
    FileUrlResponse,
    ListFilesResponse,
    UploadFileResponse,
)

logger = logging.getLogger(__name__)


async def upload_file_tool(
    ctx: RunContext[BlobStorageDeps],
    user_id: UUID,
    file_data: bytes,
    filename: str,
    content_type: str | None = None,
) -> UploadFileResponse:
    """
    Upload a file to user's blob storage.

    Args:
        ctx: Agent runtime context with dependencies
        user_id: User UUID
        file_data: File content as bytes
        filename: Filename
        content_type: Content type (auto-detected if not provided)

    Returns:
        Upload response with file key and metadata
    """
    deps = ctx.deps
    if not deps.minio_service:
        await deps.initialize()

    file_size = len(file_data)

    # Determine content type
    if not content_type:
        content_type, _ = mimetypes.guess_type(filename)

    try:
        object_key = await deps.minio_service.upload_file(
            user_id=user_id,
            file_data=file_data,
            object_key=filename,
            content_type=content_type or "application/octet-stream",
        )

        logger.info(
            "file_uploaded",
            extra={"user_id": str(user_id), "object_key": object_key, "size": file_size},
        )

        return UploadFileResponse(success=True, key=object_key, filename=filename, size=file_size)
    except Exception as e:
        logger.exception("file_upload_failed", extra={"user_id": str(user_id), "error": str(e)})
        raise


async def list_files_tool(
    ctx: RunContext[BlobStorageDeps], user_id: UUID, prefix: str | None = None
) -> ListFilesResponse:
    """
    List files for a user.

    Args:
        ctx: Agent runtime context with dependencies
        user_id: User UUID
        prefix: Optional prefix to filter files

    Returns:
        List of files with metadata
    """
    deps = ctx.deps
    if not deps.minio_service:
        await deps.initialize()

    try:
        files = await deps.minio_service.list_files(user_id=user_id, prefix=prefix)

        file_metadata = [FileMetadata(**file_dict) for file_dict in files]

        logger.info(
            "files_listed",
            extra={"user_id": str(user_id), "count": len(file_metadata), "prefix": prefix},
        )

        return ListFilesResponse(files=file_metadata, count=len(file_metadata), prefix=prefix)
    except Exception as e:
        logger.exception("file_list_failed", extra={"user_id": str(user_id), "error": str(e)})
        raise


async def download_file_tool(
    ctx: RunContext[BlobStorageDeps], user_id: UUID, filename: str
) -> bytes:
    """
    Download a file from user's blob storage.

    Args:
        ctx: Agent runtime context with dependencies
        user_id: User UUID
        filename: Filename to download

    Returns:
        File content as bytes
    """
    deps = ctx.deps
    if not deps.minio_service:
        await deps.initialize()

    try:
        file_data = await deps.minio_service.download_file(user_id=user_id, object_key=filename)

        logger.info("file_downloaded", extra={"user_id": str(user_id), "filename": filename})

        return file_data
    except Exception as e:
        logger.exception(
            "file_download_failed",
            extra={"user_id": str(user_id), "filename": filename, "error": str(e)},
        )
        raise


async def delete_file_tool(
    ctx: RunContext[BlobStorageDeps], user_id: UUID, filename: str
) -> DeleteFileResponse:
    """
    Delete a file from user's blob storage.

    Args:
        ctx: Agent runtime context with dependencies
        user_id: User UUID
        filename: Filename to delete

    Returns:
        Delete response with status
    """
    deps = ctx.deps
    if not deps.minio_service:
        await deps.initialize()

    try:
        deleted = await deps.minio_service.delete_file(user_id=user_id, object_key=filename)

        if not deleted:
            raise ValueError(f"File not found: {filename}")

        user_prefix = deps.minio_service._get_user_prefix(user_id)
        full_key = f"{user_prefix}{filename}"

        logger.info("file_deleted", extra={"user_id": str(user_id), "key": full_key})

        return DeleteFileResponse(success=True, key=full_key, message="File deleted successfully")
    except Exception as e:
        logger.exception(
            "file_delete_failed",
            extra={"user_id": str(user_id), "filename": filename, "error": str(e)},
        )
        raise


async def get_file_url_tool(
    ctx: RunContext[BlobStorageDeps], user_id: UUID, filename: str, expires_in: int = 3600
) -> FileUrlResponse:
    """
    Generate a presigned URL for a file.

    Args:
        ctx: Agent runtime context with dependencies
        user_id: User UUID
        filename: Filename to generate URL for
        expires_in: URL expiration time in seconds (default: 3600)

    Returns:
        Presigned URL response
    """
    deps = ctx.deps
    if not deps.minio_service:
        await deps.initialize()

    try:
        url = await deps.minio_service.get_file_url(
            user_id=user_id, object_key=filename, expires_in=expires_in
        )

        if not url:
            raise ValueError("Failed to generate presigned URL")

        user_prefix = deps.minio_service._get_user_prefix(user_id)
        full_key = f"{user_prefix}{filename}"

        logger.info(
            "file_url_generated",
            extra={"user_id": str(user_id), "key": full_key, "expires_in": expires_in},
        )

        return FileUrlResponse(url=url, expires_in=expires_in, key=full_key)
    except Exception as e:
        logger.exception(
            "file_url_generation_failed",
            extra={"user_id": str(user_id), "filename": filename, "error": str(e)},
        )
        raise
