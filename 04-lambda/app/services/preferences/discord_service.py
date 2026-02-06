"""Discord bot configuration service using Supabase preferences.

This service provides backward-compatible API with the MongoDB discord_bot_config store,
but stores data in Supabase using the hierarchical preferences system.

Migration path from MongoDB:
    discord_bot_config.enabled_capabilities -> discord.enabled_capabilities (system default)
    discord_bot_config.capability_settings.* -> discord.capability.* preferences
"""

import json
import logging
from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field
from app.services.database.supabase.client import SupabaseClient
from app.services.database.supabase.config import SupabaseConfig

logger = logging.getLogger(__name__)


# ============================================================================
# Models (compatible with existing discord_bot_config models)
# ============================================================================


class CapabilityInfo(BaseModel):
    """Information about an available Discord bot capability."""

    name: str = Field(..., description="Capability identifier (e.g., 'echo', 'character')")
    description: str = Field(
        ..., description="Human-readable description of what the capability does"
    )
    requires: list[str] = Field(
        default_factory=list,
        description="List of requirements (e.g., 'Lambda API', 'Immich configured')",
    )
    settings_schema: dict = Field(
        default_factory=dict,
        description="JSON Schema for capability-specific settings",
    )


class DiscordBotConfig(BaseModel):
    """Discord bot configuration (compatible with MongoDB schema)."""

    config_id: str = Field(
        default="global",
        description="Configuration identifier ('global' or guild_id for per-guild config)",
    )
    enabled_capabilities: list[str] = Field(
        default_factory=lambda: ["echo"],
        description="List of enabled capability names",
    )
    capability_settings: dict[str, dict] = Field(
        default_factory=dict,
        description="Per-capability settings (keyed by capability name)",
    )
    updated_at: datetime = Field(
        default_factory=datetime.utcnow,
        description="When the configuration was last updated",
    )
    updated_by: str | None = Field(
        default=None,
        description="Email of the admin who last updated the configuration",
    )


class DiscordBotConfigUpdate(BaseModel):
    """Request model for updating Discord bot configuration."""

    enabled_capabilities: list[str] | None = Field(
        default=None,
        description="List of capability names to enable (replaces current list)",
    )
    capability_settings: dict[str, dict] | None = Field(
        default=None,
        description="Per-capability settings to update (merged with existing)",
    )


# Available capabilities registry - source of truth for what capabilities exist
AVAILABLE_CAPABILITIES: list[CapabilityInfo] = [
    CapabilityInfo(
        name="echo",
        description="Responds when @mentioned with a simple echo of the message",
        requires=[],
        settings_schema={},
    ),
    CapabilityInfo(
        name="upload",
        description="Handles file uploads to Immich photo management system and /claim_face command",
        requires=["Immich configured", "IMMICH_URL", "IMMICH_API_KEY"],
        settings_schema={
            "type": "object",
            "properties": {
                "upload_channel_id": {
                    "type": "string",
                    "description": "Channel ID to restrict uploads to (optional)",
                },
            },
        },
    ),
    CapabilityInfo(
        name="character",
        description="AI character interactions via Lambda API with persona support. Enables character_commands and character_mention capabilities.",
        requires=["Lambda API", "LAMBDA_API_URL"],
        settings_schema={
            "type": "object",
            "properties": {
                "default_persona_id": {
                    "type": "string",
                    "description": "Default persona ID for character interactions",
                },
                "engagement_probability": {
                    "type": "number",
                    "minimum": 0,
                    "maximum": 1,
                    "description": "Probability of character engaging in conversation (0-1)",
                },
                "engagement_check_interval": {
                    "type": "integer",
                    "minimum": 10,
                    "maximum": 3600,
                    "description": "Seconds between engagement checks (default: 60)",
                },
            },
        },
    ),
    CapabilityInfo(
        name="notification",
        description="Sends face-detection notifications to Discord users (legacy - to be migrated to Agent)",
        requires=["Immich configured", "IMMICH_URL", "IMMICH_API_KEY"],
        settings_schema={
            "type": "object",
            "properties": {
                "poll_interval": {
                    "type": "integer",
                    "minimum": 30,
                    "maximum": 3600,
                    "description": "Seconds between Immich polls (default from config)",
                },
            },
        },
    ),
]


def get_capability_info(name: str) -> CapabilityInfo | None:
    """Get capability info by name."""
    for cap in AVAILABLE_CAPABILITIES:
        if cap.name == name:
            return cap
    return None


def validate_capabilities(names: list[str]) -> list[str]:
    """Validate capability names and return list of invalid ones."""
    valid_names = {cap.name for cap in AVAILABLE_CAPABILITIES}
    return [name for name in names if name not in valid_names]


# ============================================================================
# Preference Key Constants for Discord
# ============================================================================


class DiscordPreferenceKeys:
    """Discord-specific preference key constants."""

    ENABLED_CAPABILITIES = "discord.enabled_capabilities"
    CHAT_MODE = "discord.chat_mode"
    PERSONALITY_ID = "discord.personality_id"
    RAG_COLLECTION = "discord.rag_collection"
    NOTIFICATIONS_ENABLED = "discord.notifications_enabled"

    # Capability settings
    UPLOAD_CHANNEL_ID = "discord.capability.upload.channel_id"
    CHARACTER_DEFAULT_PERSONA_ID = "discord.capability.character.default_persona_id"
    CHARACTER_ENGAGEMENT_PROBABILITY = "discord.capability.character.engagement_probability"
    CHARACTER_ENGAGEMENT_CHECK_INTERVAL = "discord.capability.character.engagement_check_interval"
    NOTIFICATION_POLL_INTERVAL = "discord.capability.notification.poll_interval"


# Fallback defaults for Discord preferences
DISCORD_FALLBACK_DEFAULTS = {
    DiscordPreferenceKeys.ENABLED_CAPABILITIES: ["echo"],
    DiscordPreferenceKeys.CHAT_MODE: "echo",
    DiscordPreferenceKeys.PERSONALITY_ID: None,
    DiscordPreferenceKeys.RAG_COLLECTION: "documents",
    DiscordPreferenceKeys.NOTIFICATIONS_ENABLED: True,
    DiscordPreferenceKeys.UPLOAD_CHANNEL_ID: None,
    DiscordPreferenceKeys.CHARACTER_DEFAULT_PERSONA_ID: None,
    DiscordPreferenceKeys.CHARACTER_ENGAGEMENT_PROBABILITY: 0.3,
    DiscordPreferenceKeys.CHARACTER_ENGAGEMENT_CHECK_INTERVAL: 60,
    DiscordPreferenceKeys.NOTIFICATION_POLL_INTERVAL: 300,
}


# ============================================================================
# Discord Configuration Service
# ============================================================================


class DiscordConfigService:
    """Service for managing Discord bot configuration via Supabase preferences.

    This service provides a backward-compatible API with the MongoDB store,
    but stores data in Supabase using the hierarchical preferences system.

    Example:
        >>> service = DiscordConfigService()
        >>> config = await service.get_config("global")
        >>> config = await service.update_config(
        ...     "global",
        ...     enabled_capabilities=["echo", "character"],
        ...     updated_by="admin@example.com"
        ... )
    """

    def __init__(self, supabase_config: SupabaseConfig | None = None):
        """Initialize Discord config service.

        Args:
            supabase_config: Supabase configuration (creates new if not provided)
        """
        self.supabase = SupabaseClient(supabase_config or SupabaseConfig())

    async def _get_org_id_for_guild(self, guild_id: str) -> UUID | None:
        """Get organization UUID for a Discord guild ID.

        Args:
            guild_id: Discord guild ID

        Returns:
            Organization UUID if exists, None otherwise
        """
        if guild_id == "global":
            return None

        try:
            pool = await self.supabase._get_pool()
            async with pool.acquire() as conn:
                row = await conn.fetchrow(
                    "SELECT id FROM organizations WHERE slug = $1", f"discord-{guild_id}"
                )
                return row["id"] if row else None
        except Exception as e:
            logger.warning(f"Error fetching org ID for guild {guild_id}: {e}")
            return None

    async def _ensure_org_for_guild(self, guild_id: str) -> UUID:
        """Ensure an organization exists for a Discord guild.

        Args:
            guild_id: Discord guild ID

        Returns:
            Organization UUID (created if not exists)
        """
        org_id = await self._get_org_id_for_guild(guild_id)
        if org_id:
            return org_id

        # Create organization for guild
        pool = await self.supabase._get_pool()
        async with pool.acquire() as conn:
            row = await conn.fetchrow(
                """
                INSERT INTO organizations (name, slug)
                VALUES ($1, $2)
                ON CONFLICT (slug) DO UPDATE SET name = EXCLUDED.name
                RETURNING id
                """,
                f"Discord Guild {guild_id}",
                f"discord-{guild_id}",
            )
            return row["id"]

    async def _get_preference(
        self, key: str, org_id: UUID | None = None, default: Any = None
    ) -> Any:
        """Get a preference value with fallback.

        Args:
            key: Preference key
            org_id: Optional organization ID for guild-specific settings
            default: Default value if not found

        Returns:
            Preference value
        """
        try:
            pool = await self.supabase._get_pool()
            async with pool.acquire() as conn:
                # Check organization preference first (for guild-specific)
                if org_id:
                    org_pref = await conn.fetchrow(
                        "SELECT value FROM organization_preferences WHERE organization_id = $1 AND preference_key = $2",
                        org_id,
                        key,
                    )
                    if org_pref:
                        return org_pref["value"]

                # Fall back to system default
                sys_pref = await conn.fetchrow(
                    "SELECT default_value FROM preference_definitions WHERE key = $1", key
                )
                if sys_pref and sys_pref["default_value"] is not None:
                    return sys_pref["default_value"]

        except Exception as e:
            logger.warning(f"Error fetching preference {key}: {e}")

        # Return fallback default
        if default is not None:
            return default
        return DISCORD_FALLBACK_DEFAULTS.get(key)

    async def _set_preference(self, key: str, value: Any, org_id: UUID | None = None) -> None:
        """Set a preference value.

        Args:
            key: Preference key
            value: Preference value
            org_id: Optional organization ID for guild-specific settings
        """
        pool = await self.supabase._get_pool()
        async with pool.acquire() as conn:
            # Convert value to JSONB format
            jsonb_value = json.dumps(value)

            if org_id:
                # Set organization preference
                await conn.execute(
                    """
                    INSERT INTO organization_preferences (organization_id, preference_key, value)
                    VALUES ($1, $2, $3::jsonb)
                    ON CONFLICT (organization_id, preference_key)
                    DO UPDATE SET value = EXCLUDED.value, updated_at = NOW()
                    """,
                    org_id,
                    key,
                    jsonb_value,
                )
            else:
                # Update system default (admin only)
                await conn.execute(
                    """
                    UPDATE preference_definitions
                    SET default_value = $2::jsonb
                    WHERE key = $1
                    """,
                    key,
                    jsonb_value,
                )

    async def get_config(self, config_id: str = "global") -> DiscordBotConfig:
        """Get bot configuration by ID.

        Args:
            config_id: Configuration identifier ('global' or guild_id)

        Returns:
            DiscordBotConfig instance
        """
        org_id = await self._get_org_id_for_guild(config_id) if config_id != "global" else None

        # Get enabled capabilities
        capabilities = await self._get_preference(
            DiscordPreferenceKeys.ENABLED_CAPABILITIES, org_id, default=["echo"]
        )

        # Build capability settings
        capability_settings = {
            "upload": {
                "upload_channel_id": await self._get_preference(
                    DiscordPreferenceKeys.UPLOAD_CHANNEL_ID, org_id
                ),
            },
            "character": {
                "default_persona_id": await self._get_preference(
                    DiscordPreferenceKeys.CHARACTER_DEFAULT_PERSONA_ID, org_id
                ),
                "engagement_probability": await self._get_preference(
                    DiscordPreferenceKeys.CHARACTER_ENGAGEMENT_PROBABILITY, org_id, default=0.3
                ),
                "engagement_check_interval": await self._get_preference(
                    DiscordPreferenceKeys.CHARACTER_ENGAGEMENT_CHECK_INTERVAL, org_id, default=60
                ),
            },
            "notification": {
                "poll_interval": await self._get_preference(
                    DiscordPreferenceKeys.NOTIFICATION_POLL_INTERVAL, org_id, default=300
                ),
            },
        }

        return DiscordBotConfig(
            config_id=config_id,
            enabled_capabilities=capabilities if isinstance(capabilities, list) else ["echo"],
            capability_settings=capability_settings,
            updated_at=datetime.utcnow(),
        )

    async def update_config(
        self,
        config_id: str,
        enabled_capabilities: list[str] | None = None,
        capability_settings: dict[str, dict] | None = None,
        updated_by: str | None = None,
    ) -> DiscordBotConfig:
        """Update bot configuration.

        Args:
            config_id: Configuration identifier ('global' or guild_id)
            enabled_capabilities: List of capability names to enable (replaces current)
            capability_settings: Per-capability settings (merged with existing)
            updated_by: Email of admin making the update

        Returns:
            Updated DiscordBotConfig instance
        """
        # Get or create organization for non-global configs
        org_id = None
        if config_id != "global":
            org_id = await self._ensure_org_for_guild(config_id)

        # Update enabled capabilities
        if enabled_capabilities is not None:
            await self._set_preference(
                DiscordPreferenceKeys.ENABLED_CAPABILITIES, enabled_capabilities, org_id
            )

        # Update capability settings
        if capability_settings is not None:
            for cap_name, settings in capability_settings.items():
                await self._update_capability_settings(cap_name, settings, org_id)

        logger.info(
            f"Discord config updated: config_id={config_id}, "
            f"capabilities={enabled_capabilities}, by={updated_by}"
        )

        return await self.get_config(config_id)

    async def _update_capability_settings(
        self, capability: str, settings: dict, org_id: UUID | None
    ) -> None:
        """Update settings for a specific capability.

        Args:
            capability: Capability name
            settings: Settings dictionary
            org_id: Optional organization ID
        """
        setting_key_map = {
            "upload": {
                "upload_channel_id": DiscordPreferenceKeys.UPLOAD_CHANNEL_ID,
            },
            "character": {
                "default_persona_id": DiscordPreferenceKeys.CHARACTER_DEFAULT_PERSONA_ID,
                "engagement_probability": DiscordPreferenceKeys.CHARACTER_ENGAGEMENT_PROBABILITY,
                "engagement_check_interval": DiscordPreferenceKeys.CHARACTER_ENGAGEMENT_CHECK_INTERVAL,
            },
            "notification": {
                "poll_interval": DiscordPreferenceKeys.NOTIFICATION_POLL_INTERVAL,
            },
        }

        cap_settings = setting_key_map.get(capability, {})
        for setting_name, value in settings.items():
            pref_key = cap_settings.get(setting_name)
            if pref_key:
                await self._set_preference(pref_key, value, org_id)

    async def set_capabilities(
        self,
        capabilities: list[str],
        config_id: str = "global",
        updated_by: str | None = None,
    ) -> DiscordBotConfig:
        """Set enabled capabilities (convenience method).

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
        """Add a single capability to enabled list.

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
        """Remove a single capability from enabled list.

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
        """Update settings for a specific capability.

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
        """List all configurations (global and per-guild).

        Returns:
            List of DiscordBotConfig instances
        """
        configs = []

        # Always include global config
        configs.append(await self.get_config("global"))

        # Get all Discord organizations
        try:
            pool = await self.supabase._get_pool()
            async with pool.acquire() as conn:
                rows = await conn.fetch(
                    "SELECT slug FROM organizations WHERE slug LIKE 'discord-%'"
                )
                for row in rows:
                    # Extract guild_id from slug (e.g., "discord-123456" -> "123456")
                    guild_id = row["slug"].replace("discord-", "")
                    configs.append(await self.get_config(guild_id))
        except Exception as e:
            logger.warning(f"Error listing Discord configs: {e}")

        return configs

    async def delete_config(self, config_id: str) -> bool:
        """Delete a configuration (use with caution).

        Args:
            config_id: Configuration identifier

        Returns:
            True if deleted, False if not found
        """
        if config_id == "global":
            logger.warning("Cannot delete global config")
            return False

        try:
            pool = await self.supabase._get_pool()
            async with pool.acquire() as conn:
                # Delete the organization (cascades to organization_preferences)
                result = await conn.execute(
                    "DELETE FROM organizations WHERE slug = $1", f"discord-{config_id}"
                )
                return "DELETE 1" in result
        except Exception as e:
            logger.error(f"Error deleting config {config_id}: {e}")
            return False

    async def close(self):
        """Close database connections (no-op for Supabase client)."""
        # Supabase client manages its own connection pool
