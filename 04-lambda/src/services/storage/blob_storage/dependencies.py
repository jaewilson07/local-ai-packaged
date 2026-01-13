"""Dependencies for Blob Storage project."""

import logging
from dataclasses import dataclass

from src.services.storage.minio import MinIOClient, MinIOConfig

from shared.dependencies import BaseDependencies

logger = logging.getLogger(__name__)


@dataclass
class BlobStorageDeps(BaseDependencies):
    """Dependencies for Blob Storage project."""

    # MinIO service
    minio_service: MinIOClient | None = None

    async def initialize(self) -> None:
        """Initialize MinIO service."""
        if not self.minio_service:
            minio_config = MinIOConfig()
            self.minio_service = MinIOClient(minio_config)
            logger.info("blob_storage_deps_initialized")

    async def cleanup(self) -> None:
        """Clean up MinIO service."""
        if self.minio_service:
            # MinIO client (boto3) doesn't need explicit cleanup
            self.minio_service = None
            logger.info("blob_storage_deps_cleaned_up")
            logger.info("blob_storage_deps_cleaned_up")

    @classmethod
    def from_settings(
        cls, minio_service: MinIOClient | None = None, **overrides
    ) -> "BlobStorageDeps":
        """
        Create dependencies from application settings.

        Args:
            minio_service: Optional pre-initialized MinIO service
            **overrides: Additional overrides

        Returns:
            BlobStorageDeps instance
        """
        return cls(minio_service=minio_service, **overrides)


# Legacy helper functions for backward compatibility
def get_minio_service() -> MinIOClient:
    """
    Get MinIO service instance (legacy helper).

    Returns:
        MinIOClient instance
    """
    minio_config = MinIOConfig()
    return MinIOClient(minio_config)
