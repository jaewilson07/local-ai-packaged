"""FastAPI router for blob storage API."""

import logging
import mimetypes
from uuid import UUID

from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile
from fastapi.responses import StreamingResponse

from server.projects.auth.dependencies import User, get_current_user
from server.projects.blob_storage.dependencies import BlobStorageDeps
from server.projects.blob_storage.models import (
    DeleteFileResponse,
    FileUrlResponse,
    ListFilesResponse,
    UploadFileResponse,
)
from server.projects.blob_storage.tools import (
    delete_file_tool,
    download_file_tool,
    get_file_url_tool,
    list_files_tool,
    upload_file_tool,
)
from server.projects.shared.context_helpers import create_run_context

router = APIRouter()
logger = logging.getLogger(__name__)


@router.post("/upload", response_model=UploadFileResponse)
async def upload_file(
    file: UploadFile = File(...),
    user: User = Depends(get_current_user),
):
    """
    Upload a file to user's blob storage.

    Files are stored in MinIO under `user-{uuid}/{filename}`.

    **Request:**
    - Content-Type: `multipart/form-data`
    - Body: Form data with `file` field

    **Response:**
    ```json
    {
        "success": true,
        "key": "user-1234-5678/myfile.jpg",
        "filename": "myfile.jpg",
        "size": 1024
    }
    ```

    **Example Usage:**
    ```bash
    curl -X POST http://localhost:8000/api/v1/storage/upload \
      -H "Authorization: Bearer <token>" \
      -F "file=@myfile.jpg"
    ```
    """
    try:
        user_id = UUID(user.uid)
    except (ValueError, AttributeError):
        raise HTTPException(status_code=400, detail="Invalid user ID format")

    # Read file content
    file_data = await file.read()
    filename = file.filename or "unnamed"

    # Determine content type
    content_type = file.content_type
    if not content_type:
        content_type, _ = mimetypes.guess_type(filename)

    # Use tools pattern
    try:
        deps = BlobStorageDeps.from_settings()
        await deps.initialize()

        ctx = create_run_context(deps)

        result = await upload_file_tool(
            ctx=ctx,
            user_id=user_id,
            file_data=file_data,
            filename=filename,
            content_type=content_type,
        )

        await deps.cleanup()

        return result
    except Exception as e:
        logger.exception(f"Failed to upload file for user {user_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to upload file: {e!s}")


@router.get("/list", response_model=ListFilesResponse)
async def list_files(
    prefix: str | None = Query(None, description="Prefix to filter files (within user folder)"),
    user: User = Depends(get_current_user),
):
    """
    List files for the authenticated user.

    **Query Parameters:**
    - `prefix` (optional): Filter files by prefix (e.g., "loras/" for LoRA models)

    **Response:**
    ```json
    {
        "files": [
            {
                "key": "user-1234-5678/myfile.jpg",
                "filename": "myfile.jpg",
                "size": 1024,
                "last_modified": "2024-01-01T00:00:00",
                "etag": "abc123"
            }
        ],
        "count": 1,
        "prefix": "loras/"
    }
    ```

    **Example Usage:**
    ```bash
    # List all files
    curl http://localhost:8000/api/v1/storage/list

    # List files with prefix
    curl "http://localhost:8000/api/v1/storage/list?prefix=loras/"
    ```
    """
    try:
        user_id = UUID(user.uid)
    except (ValueError, AttributeError):
        raise HTTPException(status_code=400, detail="Invalid user ID format")

    try:
        deps = BlobStorageDeps.from_settings()
        await deps.initialize()

        ctx = create_run_context(deps)

        result = await list_files_tool(ctx=ctx, user_id=user_id, prefix=prefix)

        await deps.cleanup()

        return result
    except Exception as e:
        logger.exception(f"Failed to list files for user {user_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to list files: {e!s}")


@router.get("/download/{filename:path}")
async def download_file(
    filename: str,
    user: User = Depends(get_current_user),
):
    """
    Download a file from user's blob storage.

    **Path Parameters:**
    - `filename`: Filename to download (within user folder)

    **Response:**
    - Content-Type: Based on file type
    - Body: File content as binary stream

    **Example Usage:**
    ```bash
    curl -O http://localhost:8000/api/v1/storage/download/myfile.jpg
    ```
    """
    try:
        user_id = UUID(user.uid)
    except (ValueError, AttributeError):
        raise HTTPException(status_code=400, detail="Invalid user ID format")

    try:
        deps = BlobStorageDeps.from_settings()
        await deps.initialize()

        ctx = create_run_context(deps)

        file_data = await download_file_tool(ctx=ctx, user_id=user_id, filename=filename)

        await deps.cleanup()

        # Determine content type
        content_type, _ = mimetypes.guess_type(filename)
        if not content_type:
            content_type = "application/octet-stream"

        logger.info(f"Downloaded file {filename} for user {user_id}")

        return StreamingResponse(
            iter([file_data]),
            media_type=content_type,
            headers={"Content-Disposition": f'attachment; filename="{filename}"'},
        )
    except ValueError as e:
        if "not found" in str(e).lower():
            raise HTTPException(status_code=404, detail=f"File not found: {filename}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.exception(f"Failed to download file {filename} for user {user_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to download file: {e!s}")


@router.delete("/delete/{filename:path}", response_model=DeleteFileResponse)
async def delete_file(
    filename: str,
    user: User = Depends(get_current_user),
):
    """
    Delete a file from user's blob storage.

    **Path Parameters:**
    - `filename`: Filename to delete (within user folder)

    **Response:**
    ```json
    {
        "success": true,
        "key": "user-1234-5678/myfile.jpg",
        "message": "File deleted successfully"
    }
    ```

    **Example Usage:**
    ```bash
    curl -X DELETE http://localhost:8000/api/v1/storage/delete/myfile.jpg
    ```
    """
    try:
        user_id = UUID(user.uid)
    except (ValueError, AttributeError):
        raise HTTPException(status_code=400, detail="Invalid user ID format")

    try:
        deps = BlobStorageDeps.from_settings()
        await deps.initialize()

        ctx = create_run_context(deps)

        result = await delete_file_tool(ctx=ctx, user_id=user_id, filename=filename)

        await deps.cleanup()

        return result
    except ValueError as e:
        if "not found" in str(e).lower():
            raise HTTPException(status_code=404, detail=f"File not found: {filename}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.exception(f"Failed to delete file {filename} for user {user_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to delete file: {e!s}")


@router.get("/url/{filename:path}", response_model=FileUrlResponse)
async def get_file_url(
    filename: str,
    expires_in: int = Query(
        3600, ge=60, le=604800, description="URL expiration time in seconds (60-604800)"
    ),
    user: User = Depends(get_current_user),
):
    """
    Generate a presigned URL for a file.

    **Path Parameters:**
    - `filename`: Filename to generate URL for

    **Query Parameters:**
    - `expires_in` (optional, default: 3600): URL expiration time in seconds (60-604800)

    **Response:**
    ```json
    {
        "url": "http://minio:9020/user-data/user-1234-5678/myfile.jpg?X-Amz-Algorithm=...",
        "expires_in": 3600,
        "key": "user-1234-5678/myfile.jpg"
    }
    ```

    **Example Usage:**
    ```bash
    curl "http://localhost:8000/api/v1/storage/url/myfile.jpg?expires_in=7200"
    ```
    """
    try:
        user_id = UUID(user.uid)
    except (ValueError, AttributeError):
        raise HTTPException(status_code=400, detail="Invalid user ID format")

    try:
        deps = BlobStorageDeps.from_settings()
        await deps.initialize()

        ctx = create_run_context(deps)

        result = await get_file_url_tool(
            ctx=ctx, user_id=user_id, filename=filename, expires_in=expires_in
        )

        await deps.cleanup()

        return result
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.exception(f"Failed to generate URL for {filename} for user {user_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to generate URL: {e!s}")
