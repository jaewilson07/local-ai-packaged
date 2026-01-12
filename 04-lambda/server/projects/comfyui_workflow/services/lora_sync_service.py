"""LoRA model sync service for ComfyUI."""

import logging
from pathlib import Path
from uuid import UUID

from server.projects.auth.services.minio_service import MinIOService

logger = logging.getLogger(__name__)


class LoRASyncService:
    """Service for syncing LoRA models from MinIO or Google Drive to ComfyUI data directory."""

    def __init__(
        self,
        minio_service: MinIOService,
        google_drive_service: object | None = None,
        comfyui_lora_base_path: str = "/basedir/models/loras",
    ):
        """
        Initialize LoRA sync service.

        Args:
            minio_service: MinIO service for file operations
            google_drive_service: Optional Google Drive service for downloading from Google Drive
            comfyui_lora_base_path: Base path for LoRA models in ComfyUI (default: /basedir/models/loras)
        """
        self.minio_service = minio_service
        self.google_drive_service = google_drive_service
        self.comfyui_lora_base_path = Path(comfyui_lora_base_path)

    async def ensure_lora_synced(self, user_id: UUID, lora_filename: str) -> str | None:
        """
        Ensure a LoRA model is synced to ComfyUI data directory.

        This method:
        1. Checks if LoRA exists in ComfyUI: /basedir/models/loras/user-{uuid}/{filename}
        2. If missing, downloads from MinIO and copies to ComfyUI
        3. Returns the path that ComfyUI should use

        Args:
            user_id: User UUID
            lora_filename: LoRA filename (e.g., "my-lora.safetensors")

        Returns:
            ComfyUI path to use (e.g., "user-{uuid}/my-lora.safetensors") or None if sync failed
        """
        user_prefix = f"user-{user_id}"
        comfyui_path = self.comfyui_lora_base_path / user_prefix / lora_filename

        # Check if file already exists in ComfyUI
        if comfyui_path.exists():
            logger.debug(f"LoRA already synced: {comfyui_path}")
            return f"{user_prefix}/{lora_filename}"

        # File doesn't exist, need to sync from MinIO
        logger.info(f"Syncing LoRA from MinIO: {lora_filename} for user {user_id}")

        try:
            # Download from MinIO
            file_data = await self.minio_service.download_file(
                user_id=user_id, object_key=f"loras/{lora_filename}"
            )

            # Create user directory if it doesn't exist
            comfyui_path.parent.mkdir(parents=True, exist_ok=True)

            # Write file to ComfyUI data directory
            with comfyui_path.open("wb") as f:
                f.write(file_data)

            logger.info(f"Synced LoRA to ComfyUI: {comfyui_path}")
            return f"{user_prefix}/{lora_filename}"

        except Exception as e:
            logger.exception(f"Failed to sync LoRA {lora_filename} for user {user_id}: {e}")
            return None

    async def sync_user_loras(self, user_id: UUID) -> int:
        """
        Sync all LoRA models for a user from MinIO to ComfyUI.

        Args:
            user_id: User UUID

        Returns:
            Number of LoRAs synced
        """
        try:
            # List all LoRA files for user in MinIO
            files = await self.minio_service.list_files(user_id=user_id, prefix="loras/")

            synced_count = 0
            for file_info in files:
                filename = file_info.get("filename", "")
                if filename and filename.endswith((".safetensors", ".ckpt", ".pt")):
                    # Remove "loras/" prefix if present
                    if filename.startswith("loras/"):
                        filename = filename[6:]

                    result = await self.ensure_lora_synced(user_id, filename)
                    if result:
                        synced_count += 1

            logger.info(f"Synced {synced_count} LoRA models for user {user_id}")
            return synced_count

        except Exception as e:
            logger.exception(f"Failed to sync user LoRAs for {user_id}: {e}")
            return 0

    async def sync_from_google_drive(
        self, user_id: UUID, google_drive_file_id: str, lora_filename: str | None = None
    ) -> str | None:
        """
        Sync a LoRA model from Google Drive to ComfyUI data directory.

        This method:
        1. Downloads the file from Google Drive
        2. Uses the provided filename or extracts from Google Drive metadata
        3. Saves to ComfyUI data directory
        4. Returns the path that ComfyUI should use

        Args:
            user_id: User UUID
            google_drive_file_id: Google Drive file ID
            lora_filename: Optional filename to use (if not provided, will use Google Drive file name)

        Returns:
            ComfyUI path to use (e.g., "user-{uuid}/my-lora.safetensors") or None if sync failed
        """
        if not self.google_drive_service:
            logger.error("Google Drive service not available")
            return None

        try:
            # Get file metadata to determine filename if not provided
            if not lora_filename:
                file_metadata = self.google_drive_service.api.get_file_metadata(
                    google_drive_file_id, fields="name"
                )
                lora_filename = file_metadata.get("name", "lora.safetensors")

            # Ensure filename has valid extension
            if not lora_filename.endswith((".safetensors", ".ckpt", ".pt")):
                logger.warning(f"LoRA filename {lora_filename} doesn't have standard extension")

            user_prefix = f"user-{user_id}"
            comfyui_path = self.comfyui_lora_base_path / user_prefix / lora_filename

            # Check if file already exists in ComfyUI
            if comfyui_path.exists():
                logger.debug(f"LoRA already synced: {comfyui_path}")
                return f"{user_prefix}/{lora_filename}"

            # Download from Google Drive
            logger.info(
                f"Downloading LoRA from Google Drive: {google_drive_file_id} for user {user_id}"
            )
            file_data = self.google_drive_service.download_file(google_drive_file_id)

            # Create user directory if it doesn't exist
            comfyui_path.parent.mkdir(parents=True, exist_ok=True)

            # Write file to ComfyUI data directory
            with comfyui_path.open("wb") as f:
                f.write(file_data)

            logger.info(f"Synced LoRA from Google Drive to ComfyUI: {comfyui_path}")
            return f"{user_prefix}/{lora_filename}"

        except Exception as e:
            logger.exception(
                f"Failed to sync LoRA from Google Drive {google_drive_file_id} for user {user_id}: {e}"
            )
            return None
