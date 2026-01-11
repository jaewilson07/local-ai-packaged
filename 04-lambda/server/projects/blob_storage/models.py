"""Pydantic models for blob storage API."""

from pydantic import BaseModel, Field


class FileMetadata(BaseModel):
    """File metadata model."""

    key: str = Field(..., description="Full object key (user-{uuid}/filename)")
    filename: str = Field(..., description="Filename without user prefix")
    size: int = Field(..., description="File size in bytes")
    last_modified: str = Field(..., description="Last modified timestamp (ISO format)")
    etag: str | None = Field(None, description="ETag for file")


class ListFilesResponse(BaseModel):
    """Response model for listing files."""

    files: list[FileMetadata] = Field(..., description="List of file metadata")
    count: int = Field(..., description="Number of files")
    prefix: str | None = Field(None, description="Prefix used for filtering")


class UploadFileResponse(BaseModel):
    """Response model for file upload."""

    success: bool = Field(..., description="Whether upload was successful")
    key: str = Field(..., description="Full object key where file was stored")
    filename: str = Field(..., description="Filename")
    size: int = Field(..., description="File size in bytes")


class DeleteFileResponse(BaseModel):
    """Response model for file deletion."""

    success: bool = Field(..., description="Whether deletion was successful")
    key: str = Field(..., description="Object key that was deleted")
    message: str = Field(..., description="Status message")


class FileUrlResponse(BaseModel):
    """Response model for presigned URL generation."""

    url: str = Field(..., description="Presigned URL")
    expires_in: int = Field(..., description="URL expiration time in seconds")
    key: str = Field(..., description="Object key")
