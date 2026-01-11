"""LoRA resolution service for character-based and custom name lookup."""

import logging
from uuid import UUID

logger = logging.getLogger(__name__)


class LoRAResolutionService:
    """Service for resolving LoRA models by character name or custom name."""

    def __init__(self, supabase_store):
        """
        Initialize LoRA resolution service.

        Args:
            supabase_store: SupabaseWorkflowStore instance for database queries
        """
        self.store = supabase_store

    async def resolve_lora_by_character(self, user_id: UUID, character_name: str) -> dict | None:
        """
        Resolve LoRA model by character name.

        Looks for LoRAs where:
        - character_name matches exactly (case-insensitive)
        - OR tags array contains the character name

        Args:
            user_id: User UUID
            character_name: Character name (e.g., "Alyx")

        Returns:
            LoRA model dict with 'filename' and 'minio_path', or None if not found
        """
        try:
            # Get all user's LoRAs
            loras = await self.store.list_lora_models(user_id=user_id, limit=100, offset=0)

            character_lower = character_name.lower()

            # First, try exact match on character_name
            for lora in loras:
                if lora.character_name and lora.character_name.lower() == character_lower:
                    logger.info(
                        f"Found LoRA by character_name: {lora.name} for character '{character_name}'"
                    )
                    return {
                        "id": str(lora.id),
                        "name": lora.name,
                        "filename": lora.filename,
                        "minio_path": lora.minio_path,
                        "character_name": lora.character_name,
                    }

            # Then, try match in tags
            for lora in loras:
                if lora.tags:
                    for tag in lora.tags:
                        if tag.lower() == character_lower:
                            logger.info(
                                f"Found LoRA by tag: {lora.name} for character '{character_name}'"
                            )
                            return {
                                "id": str(lora.id),
                                "name": lora.name,
                                "filename": lora.filename,
                                "minio_path": lora.minio_path,
                                "character_name": lora.character_name,
                            }

            logger.warning(f"No LoRA found for character '{character_name}'")
            return None

        except Exception as e:
            logger.exception(f"Error resolving LoRA by character: {e}")
            return None

    async def resolve_lora_by_name(self, user_id: UUID, lora_name: str) -> dict | None:
        """
        Resolve LoRA model by friendly name.

        Args:
            user_id: User UUID
            lora_name: LoRA friendly name (e.g., "my_saved_lora")

        Returns:
            LoRA model dict with 'filename' and 'minio_path', or None if not found
        """
        try:
            # Get all user's LoRAs
            loras = await self.store.list_lora_models(user_id=user_id, limit=100, offset=0)

            lora_name_lower = lora_name.lower()

            # Try exact match first
            for lora in loras:
                if lora.name.lower() == lora_name_lower:
                    logger.info(f"Found LoRA by exact name: {lora.name}")
                    return {
                        "id": str(lora.id),
                        "name": lora.name,
                        "filename": lora.filename,
                        "minio_path": lora.minio_path,
                        "character_name": lora.character_name,
                    }

            # Try partial match
            for lora in loras:
                if lora_name_lower in lora.name.lower() or lora.name.lower() in lora_name_lower:
                    logger.info(f"Found LoRA by partial name: {lora.name}")
                    return {
                        "id": str(lora.id),
                        "name": lora.name,
                        "filename": lora.filename,
                        "minio_path": lora.minio_path,
                        "character_name": lora.character_name,
                    }

            logger.warning(f"No LoRA found with name '{lora_name}'")
            return None

        except Exception as e:
            logger.exception(f"Error resolving LoRA by name: {e}")
            return None

    async def resolve_loras(
        self, user_id: UUID, lora_character: str | None = None, lora_custom: str | None = None
    ) -> dict[str, str | None]:
        """
        Resolve multiple LoRAs (character and custom).

        Args:
            user_id: User UUID
            lora_character: Optional character name
            lora_custom: Optional custom LoRA name

        Returns:
            Dict mapping lora keys to file paths:
            {
                "character": "user-{uuid}/alix_lora.safetensors" or None,
                "custom": "user-{uuid}/my_lora.safetensors" or None
            }
        """
        resolved = {"character": None, "custom": None}

        if lora_character:
            lora = await self.resolve_lora_by_character(user_id, lora_character)
            if lora:
                # Extract just the filename for ComfyUI path
                resolved["character"] = lora["filename"]

        if lora_custom:
            lora = await self.resolve_lora_by_name(user_id, lora_custom)
            if lora:
                resolved["custom"] = lora["filename"]

        return resolved
