"""Storage interface for Discord bot configuration."""

from datetime import datetime
from typing import Any

from pymongo import AsyncMongoClient

from .models import DiscordBotConfig


class DiscordBotConfigStore:
    """MongoDB store for Discord bot configuration."""

    COLLECTION_NAME = "discord_bot_config"

    def __init__(self, mongodb_url: str, db_name: str = "localai", db: Any | None = None):
        """
        Initialize MongoDB connection.

        Args:
            mongodb_url: MongoDB connection URL
            db_name: Database name
            db: Optional existing database instance (for dependency injection)
        """
        if db is not None:
            self.db: Any = db
            self.client = None
        else:
            self.client = AsyncMongoClient(mongodb_url)
            self.db: Any = self.client[db_name]

        self.config_collection = self.db[self.COLLECTION_NAME]

    async def get_config(self, config_id: str = "global") -> DiscordBotConfig:
        """
        Get bot configuration by ID.

        Args:
            config_id: Configuration identifier ('global' or guild_id)

        Returns:
            DiscordBotConfig instance (creates default if not exists)
        """
        doc = await self.config_collection.find_one({"_id": config_id})

        if doc:
            # Convert MongoDB _id to config_id
            doc["config_id"] = doc.pop("_id")
            return DiscordBotConfig(**doc)

        # Return default configuration if not found
        return DiscordBotConfig(config_id=config_id)

    async def update_config(
        self,
        config_id: str,
        enabled_capabilities: list[str] | None = None,
        capability_settings: dict[str, dict] | None = None,
        updated_by: str | None = None,
    ) -> DiscordBotConfig:
        """
        Update bot configuration.

        Args:
            config_id: Configuration identifier ('global' or guild_id)
            enabled_capabilities: List of capability names to enable (replaces current)
            capability_settings: Per-capability settings (merged with existing)
            updated_by: Email of admin making the update

        Returns:
            Updated DiscordBotConfig instance
        """
        # Get current config
        current = await self.get_config(config_id)

        # Build update document
        update_fields: dict[str, Any] = {
            "updated_at": datetime.utcnow(),
        }

        if updated_by is not None:
            update_fields["updated_by"] = updated_by

        if enabled_capabilities is not None:
            update_fields["enabled_capabilities"] = enabled_capabilities

        if capability_settings is not None:
            # Merge with existing settings
            merged_settings = dict(current.capability_settings)
            for cap_name, settings in capability_settings.items():
                if cap_name in merged_settings:
                    merged_settings[cap_name].update(settings)
                else:
                    merged_settings[cap_name] = settings
            update_fields["capability_settings"] = merged_settings

        # Upsert the configuration
        await self.config_collection.update_one(
            {"_id": config_id},
            {"$set": update_fields},
            upsert=True,
        )

        return await self.get_config(config_id)

    async def set_capabilities(
        self,
        capabilities: list[str],
        config_id: str = "global",
        updated_by: str | None = None,
    ) -> DiscordBotConfig:
        """
        Set enabled capabilities (convenience method).

        Args:
            capabilities: List of capability names to enable
            config_id: Configuration identifier
            updated_by: Email of admin making the update

        Returns:
            Updated DiscordBotConfig instance
        """
        return await self.update_config(
            config_id=config_id,
            enabled_capabilities=capabilities,
            updated_by=updated_by,
        )

    async def add_capability(
        self,
        capability: str,
        config_id: str = "global",
        updated_by: str | None = None,
    ) -> DiscordBotConfig:
        """
        Add a single capability to enabled list.

        Args:
            capability: Capability name to add
            config_id: Configuration identifier
            updated_by: Email of admin making the update

        Returns:
            Updated DiscordBotConfig instance
        """
        current = await self.get_config(config_id)
        if capability not in current.enabled_capabilities:
            capabilities = current.enabled_capabilities + [capability]
            return await self.set_capabilities(capabilities, config_id, updated_by)
        return current

    async def remove_capability(
        self,
        capability: str,
        config_id: str = "global",
        updated_by: str | None = None,
    ) -> DiscordBotConfig:
        """
        Remove a single capability from enabled list.

        Args:
            capability: Capability name to remove
            config_id: Configuration identifier
            updated_by: Email of admin making the update

        Returns:
            Updated DiscordBotConfig instance
        """
        current = await self.get_config(config_id)
        if capability in current.enabled_capabilities:
            capabilities = [c for c in current.enabled_capabilities if c != capability]
            return await self.set_capabilities(capabilities, config_id, updated_by)
        return current

    async def update_capability_settings(
        self,
        capability: str,
        settings: dict,
        config_id: str = "global",
        updated_by: str | None = None,
    ) -> DiscordBotConfig:
        """
        Update settings for a specific capability.

        Args:
            capability: Capability name
            settings: Settings dictionary to merge
            config_id: Configuration identifier
            updated_by: Email of admin making the update

        Returns:
            Updated DiscordBotConfig instance
        """
        return await self.update_config(
            config_id=config_id,
            capability_settings={capability: settings},
            updated_by=updated_by,
        )

    async def list_configs(self) -> list[DiscordBotConfig]:
        """
        List all configurations (global and per-guild).

        Returns:
            List of DiscordBotConfig instances
        """
        cursor = self.config_collection.find({})
        docs = await cursor.to_list(length=None)

        configs = []
        for doc in docs:
            doc["config_id"] = doc.pop("_id")
            configs.append(DiscordBotConfig(**doc))

        return configs

    async def delete_config(self, config_id: str) -> bool:
        """
        Delete a configuration (use with caution).

        Args:
            config_id: Configuration identifier

        Returns:
            True if deleted, False if not found
        """
        result = await self.config_collection.delete_one({"_id": config_id})
        return result.deleted_count > 0

    async def close(self):
        """Close MongoDB connection."""
        if self.client:
            await self.client.close()
