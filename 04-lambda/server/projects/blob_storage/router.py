"""FastAPI router for blob storage API."""

import logging
import mimetypes
from uuid import UUID

from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile
from fastapi.responses import StreamingResponse

from server.projects.auth.dependencies import User, get_current_user
from server.projects.auth.services.minio_service import MinIOService
from server.projects.blob_storage.dependencies import get_minio_service
from server.projects.blob_storage.models import (
    DeleteFileResponse,
    FileMetadata,
    FileUrlResponse,
    ListFilesResponse,
    UploadFileResponse,
)

router = APIRouter()
logger = logging.getLogger(__name__)


@router.post("/upload", response_model=UploadFileResponse)
async def upload_file(
    file: UploadFile = File(...),
    user: User = Depends(get_current_user),
    minio_service: MinIOService = Depends(get_minio_service),
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
    file_size = len(file_data)

    # Determine content type
    content_type = file.content_type
    if not content_type:
        content_type, _ = mimetypes.guess_type(file.filename or "")

    # Upload to MinIO
    try:
        object_key = await minio_service.upload_file(
            user_id=user_id,
            file_data=file_data,
            object_key=file.filename or "unnamed",
            content_type=content_type,
        )

        logger.info(f"Uploaded file {object_key} for user {user_id} ({file_size} bytes)")

        return UploadFileResponse(
            success=True, key=object_key, filename=file.filename or "unnamed", size=file_size
        )
    except Exception as e:
        logger.exception(f"Failed to upload file for user {user_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to upload file: {e!s}")


@router.get("/list", response_model=ListFilesResponse)
async def list_files(
    prefix: str | None = Query(None, description="Prefix to filter files (within user folder)"),
    user: User = Depends(get_current_user),
    minio_service: MinIOService = Depends(get_minio_service),
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
        files = await minio_service.list_files(user_id=user_id, prefix=prefix)

        file_metadata = [FileMetadata(**file_dict) for file_dict in files]

        return ListFilesResponse(files=file_metadata, count=len(file_metadata), prefix=prefix)
    except Exception as e:
        logger.exception(f"Failed to list files for user {user_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to list files: {e!s}")


@router.get("/download/{filename:path}")
async def download_file(
    filename: str,
    user: User = Depends(get_current_user),
    minio_service: MinIOService = Depends(get_minio_service),
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
        # Download file from MinIO
        file_data = await minio_service.download_file(user_id=user_id, object_key=filename)

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
    except Exception as e:
        error_code = getattr(e, "response", {}).get("Error", {}).get("Code", "")
        if error_code == "NoSuchKey":
            raise HTTPException(status_code=404, detail=f"File not found: {filename}")
        logger.exception(f"Failed to download file {filename} for user {user_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to download file: {e!s}")


@router.delete("/delete/{filename:path}", response_model=DeleteFileResponse)
async def delete_file(
    filename: str,
    user: User = Depends(get_current_user),
    minio_service: MinIOService = Depends(get_minio_service),
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
        deleted = await minio_service.delete_file(user_id=user_id, object_key=filename)

        if not deleted:
            raise HTTPException(status_code=404, detail=f"File not found: {filename}")

        user_prefix = minio_service._get_user_prefix(user_id)
        full_key = f"{user_prefix}{filename}"

        logger.info(f"Deleted file {full_key} for user {user_id}")

        return DeleteFileResponse(success=True, key=full_key, message="File deleted successfully")
    except HTTPException:
        raise
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
    minio_service: MinIOService = Depends(get_minio_service),
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
        url = await minio_service.get_file_url(
            user_id=user_id, object_key=filename, expires_in=expires_in
        )

        if not url:
            raise HTTPException(status_code=500, detail="Failed to generate presigned URL")

        user_prefix = minio_service._get_user_prefix(user_id)
        full_key = f"{user_prefix}{filename}"

        return FileUrlResponse(url=url, expires_in=expires_in, key=full_key)
    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"Failed to generate URL for {filename} for user {user_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to generate URL: {e!s}")
