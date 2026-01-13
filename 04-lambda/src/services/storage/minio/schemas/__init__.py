"""MinIO storage schemas."""

from pydantic import BaseModel, Field


class S3Object(BaseModel):
    """S3 object metadata."""

    key: str = Field(..., description="Full S3 object key")
    filename: str = Field(..., description="Filename without user prefix")
    size: int = Field(..., description="File size in bytes")
    last_modified: str = Field(..., description="Last modified timestamp (ISO format)")
    etag: str = Field(..., description="Entity tag for the object")
    content_type: str | None = Field(None, description="Content type of the object")


class UploadRequest(BaseModel):
    """Request to upload a file."""

    object_key: str = Field(..., description="Object key (filename) within user folder")
    content_type: str | None = Field(None, description="MIME type")
    metadata: dict[str, str] | None = Field(None, description="Additional metadata")


class UserBucketInfo(BaseModel):
    """User bucket/folder information."""

    user_id: str = Field(..., description="User UUID")
    folder_prefix: str = Field(..., description="MinIO folder prefix")
    exists: bool = Field(..., description="Whether user folder exists")
    file_count: int = Field(default=0, description="Number of files in user folder")
