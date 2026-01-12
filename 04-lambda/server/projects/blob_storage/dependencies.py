"""Dependencies for Blob Storage project."""

import logging
from dataclasses import dataclass

from server.projects.auth.config import config as auth_config
from server.projects.auth.services.minio_service import MinIOService
from server.projects.shared.dependencies import BaseDependencies

logger = logging.getLogger(__name__)


@dataclass
class BlobStorageDeps(BaseDependencies):
    """Dependencies for Blob Storage project."""

    # MinIO service
    minio_service: MinIOService | None = None

    async def initialize(self) -> None:
        """Initialize MinIO service."""
        if not self.minio_service:
            self.minio_service = MinIOService(auth_config)
            logger.info("blob_storage_deps_initialized")

    async def cleanup(self) -> None:
        """Clean up MinIO service."""
        if self.minio_service:
            await self.minio_service.close()
            self.minio_service = None
            logger.info("blob_storage_deps_cleaned_up")

    @classmethod
    def from_settings(
        cls, minio_service: MinIOService | None = None, **overrides
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
def get_minio_service() -> MinIOService:
    """
    Get MinIO service instance (legacy helper).

    Returns:
        MinIOService instance
    """
    return MinIOService(auth_config)
