"""Data models for Discord bot configuration."""

from datetime import datetime

from pydantic import BaseModel, Field


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
    """Discord bot configuration stored in MongoDB."""

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
