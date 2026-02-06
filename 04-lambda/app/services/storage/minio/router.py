"""MinIO storage router."""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from .client import MinIOClient
from .config import MinIOConfig

router = APIRouter(prefix="/minio", tags=["MinIO"])


class HealthResponse(BaseModel):
    """Health check response."""

    status: str
    service: str


@router.get("/health", response_model=HealthResponse)
async def health_check():
    """Check MinIO storage connection health."""
    try:
        config = MinIOConfig()
        client = MinIOClient(config)

        # Test connection by checking if S3 client can be created
        s3_client = client._get_s3_client()

        # Try to list buckets as a health check
        s3_client.list_buckets()

        return HealthResponse(status="healthy", service="minio")
    except Exception as e:
        raise HTTPException(status_code=503, detail=f"MinIO unavailable: {e!s}")
