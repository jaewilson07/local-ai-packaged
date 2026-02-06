"""Blob Storage project agent for file management."""

import logging
from uuid import UUID

from pydantic import BaseModel, Field
from pydantic_ai import Agent, RunContext
from app.services.storage.blob_storage.dependencies import BlobStorageDeps
from app.services.storage.blob_storage.tools import (
    delete_file_tool,
    download_file_tool,
    get_file_url_tool,
    list_files_tool,
    upload_file_tool,
)

from shared.llm import get_llm_model

logger = logging.getLogger(__name__)


class BlobStorageState(BaseModel):
    """Minimal shared state for the Blob Storage agent."""


BLOB_STORAGE_SYSTEM_PROMPT = """You are a blob storage management agent that helps users manage their files.

You can:
- Upload files to user's blob storage
- List files in user's storage (with optional prefix filtering)
- Download files from user's storage
- Delete files from user's storage
- Generate presigned URLs for file access

All operations are scoped to the authenticated user's storage space.
Files are stored in MinIO under user-specific prefixes for data isolation.
"""


blob_storage_agent = Agent(
    model=get_llm_model(),
    system_prompt=BLOB_STORAGE_SYSTEM_PROMPT,
    deps_type=BlobStorageDeps,
    state_type=BlobStorageState,
)


@blob_storage_agent.tool
async def upload_file(
    ctx: RunContext[BlobStorageDeps],
    user_id: str = Field(..., description="User UUID"),
    file_data: str = Field(..., description="File content as base64-encoded string"),
    filename: str = Field(..., description="Filename"),
    content_type: str | None = Field(
        None, description="Content type (auto-detected if not provided)"
    ),
) -> dict:
    """
    Upload a file to user's blob storage.

    Args:
        user_id: User UUID as string
        file_data: File content as base64-encoded string
        filename: Filename
        content_type: Optional content type

    Returns:
        Upload response with file key and metadata
    """
    import base64

    try:
        user_uuid = UUID(user_id)
        file_bytes = base64.b64decode(file_data)

        result = await upload_file_tool(
            ctx=ctx,
            user_id=user_uuid,
            file_data=file_bytes,
            filename=filename,
            content_type=content_type,
        )

        return result.model_dump()
    except Exception as e:
        logger.exception("agent_tool_error: upload_file")
        raise RuntimeError(f"Failed to upload file: {e}") from e


@blob_storage_agent.tool
async def list_files(
    ctx: RunContext[BlobStorageDeps],
    user_id: str = Field(..., description="User UUID"),
    prefix: str | None = Field(None, description="Prefix to filter files"),
) -> dict:
    """
    List files for a user.

    Args:
        user_id: User UUID as string
        prefix: Optional prefix to filter files

    Returns:
        List of files with metadata
    """
    try:
        user_uuid = UUID(user_id)

        result = await list_files_tool(ctx=ctx, user_id=user_uuid, prefix=prefix)

        return result.model_dump()
    except Exception as e:
        logger.exception("agent_tool_error: list_files")
        raise RuntimeError(f"Failed to list files: {e}") from e


@blob_storage_agent.tool
async def download_file(
    ctx: RunContext[BlobStorageDeps],
    user_id: str = Field(..., description="User UUID"),
    filename: str = Field(..., description="Filename to download"),
) -> dict:
    """
    Download a file from user's blob storage.

    Args:
        user_id: User UUID as string
        filename: Filename to download

    Returns:
        File content as base64-encoded string
    """
    import base64

    try:
        user_uuid = UUID(user_id)

        file_data = await download_file_tool(ctx=ctx, user_id=user_uuid, filename=filename)

        return {
            "success": True,
            "filename": filename,
            "data": base64.b64encode(file_data).decode("utf-8"),
            "size": len(file_data),
        }
    except Exception as e:
        logger.exception("agent_tool_error: download_file")
        raise RuntimeError(f"Failed to download file: {e}") from e


@blob_storage_agent.tool
async def delete_file(
    ctx: RunContext[BlobStorageDeps],
    user_id: str = Field(..., description="User UUID"),
    filename: str = Field(..., description="Filename to delete"),
) -> dict:
    """
    Delete a file from user's blob storage.

    Args:
        user_id: User UUID as string
        filename: Filename to delete

    Returns:
        Delete response with status
    """
    try:
        user_uuid = UUID(user_id)

        result = await delete_file_tool(ctx=ctx, user_id=user_uuid, filename=filename)

        return result.model_dump()
    except Exception as e:
        logger.exception("agent_tool_error: delete_file")
        raise RuntimeError(f"Failed to delete file: {e}") from e


@blob_storage_agent.tool
async def get_file_url(
    ctx: RunContext[BlobStorageDeps],
    user_id: str = Field(..., description="User UUID"),
    filename: str = Field(..., description="Filename to generate URL for"),
    expires_in: int = Field(3600, description="URL expiration time in seconds"),
) -> dict:
    """
    Generate a presigned URL for a file.

    Args:
        user_id: User UUID as string
        filename: Filename to generate URL for
        expires_in: URL expiration time in seconds (default: 3600)

    Returns:
        Presigned URL response
    """
    try:
        user_uuid = UUID(user_id)

        result = await get_file_url_tool(
            ctx=ctx, user_id=user_uuid, filename=filename, expires_in=expires_in
        )

        return result.model_dump()
    except Exception as e:
        logger.exception("agent_tool_error: get_file_url")
        raise RuntimeError(f"Failed to generate file URL: {e}") from e
