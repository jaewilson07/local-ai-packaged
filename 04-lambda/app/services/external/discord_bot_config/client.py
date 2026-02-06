"""Discord bot configuration client.

This module provides a unified interface for managing Discord bot configuration.
"""

import logging
from typing import Any

from .models import DiscordBotConfig
from .store import DiscordBotConfigStore

logger = logging.getLogger(__name__)


class DiscordBotConfigClient:
    """Client for Discord bot configuration management."""

    def __init__(self, mongodb_url: str, db_name: str = "localai", db: Any | None = None):
        """
        Initialize the Discord bot config client.

        Args:
            mongodb_url: MongoDB connection URL
            db_name: Database name
            db: Optional existing database instance (for dependency injection)
        """
        self.store = DiscordBotConfigStore(
            mongodb_url=mongodb_url,
            db_name=db_name,
            db=db,
        )

    async def get_config(self, config_id: str = "global") -> DiscordBotConfig:
        """
        Get bot configuration.

        Args:
            config_id: Configuration identifier ('global' or guild_id)

        Returns:
            DiscordBotConfig instance
        """
        return await self.store.get_config(config_id)

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
            config_id: Configuration identifier
            enabled_capabilities: List of capability names to enable
            capability_settings: Per-capability settings
            updated_by: Email of admin making the update

        Returns:
            Updated DiscordBotConfig instance
        """
        return await self.store.update_config(
            config_id=config_id,
            enabled_capabilities=enabled_capabilities,
            capability_settings=capability_settings,
            updated_by=updated_by,
        )

    async def enable_capability(
        self,
        config_id: str,
        capability_name: str,
        updated_by: str | None = None,
    ) -> DiscordBotConfig:
        """
        Enable a single capability.

        Args:
            config_id: Configuration identifier
            capability_name: Name of capability to enable
            updated_by: Email of admin making the update

        Returns:
            Updated DiscordBotConfig instance
        """
        return await self.store.enable_capability(
            config_id=config_id,
            capability_name=capability_name,
            updated_by=updated_by,
        )

    async def disable_capability(
        self,
        config_id: str,
        capability_name: str,
        updated_by: str | None = None,
    ) -> DiscordBotConfig:
        """
        Disable a single capability.

        Args:
            config_id: Configuration identifier
            capability_name: Name of capability to disable
            updated_by: Email of admin making the update

        Returns:
            Updated DiscordBotConfig instance
        """
        return await self.store.disable_capability(
            config_id=config_id,
            capability_name=capability_name,
            updated_by=updated_by,
        )

    async def update_capability_settings(
        self,
        config_id: str,
        capability_name: str,
        settings: dict[str, Any],
        updated_by: str | None = None,
    ) -> DiscordBotConfig:
        """
        Update settings for a specific capability.

        Args:
            config_id: Configuration identifier
            capability_name: Name of capability
            settings: Settings dictionary for the capability
            updated_by: Email of admin making the update

        Returns:
            Updated DiscordBotConfig instance
        """
        return await self.store.update_capability_settings(
            config_id=config_id,
            capability_name=capability_name,
            settings=settings,
            updated_by=updated_by,
        )

    async def close(self):
        """Close the MongoDB connection."""
        if self.store.client is not None:
            self.store.client.close()
