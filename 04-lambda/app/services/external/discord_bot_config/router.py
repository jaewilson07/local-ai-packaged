"""FastAPI router for Discord bot configuration management.

This router provides endpoints for managing Discord bot configuration.
Configuration is stored in Supabase using the hierarchical preferences system,
replacing the previous MongoDB-based storage.

Migration Note:
    As of 2026-01-20, Discord bot configuration has been migrated from MongoDB
    to Supabase preferences. The API remains backward-compatible.
    See: 01-data/supabase/migrations/010_discord_preferences.sql
"""

import logging

from fastapi import APIRouter, Depends, HTTPException
from app.services.auth.config import config as auth_config
from app.services.auth.dependencies import User, get_current_user
from app.services.auth.services.auth_service import AuthService
from app.services.preferences.discord_service import (
    AVAILABLE_CAPABILITIES,
    CapabilityInfo,
    DiscordBotConfig,
    DiscordBotConfigUpdate,
    DiscordConfigService,
    validate_capabilities,
)

router = APIRouter(prefix="/api/v1/admin", tags=["admin", "discord"])
logger = logging.getLogger(__name__)


def get_config_service() -> DiscordConfigService:
    """Get Discord config service instance (Supabase-based)."""
    return DiscordConfigService()


async def require_admin(user: User = Depends(get_current_user)) -> User:
    """Dependency to ensure user is an admin."""
    auth_service = AuthService(auth_config)
    is_admin = await auth_service.is_admin(user.email)

    if not is_admin:
        raise HTTPException(
            status_code=403,
            detail="Admin access required. This endpoint is only available to users with admin role.",
        )

    return user


@router.get("/discord/capabilities", response_model=list[CapabilityInfo])
async def list_available_capabilities(
    user: User = Depends(get_current_user),
) -> list[CapabilityInfo]:
    """
    List all available Discord bot capabilities.

    Returns information about each capability including:
    - Name and description
    - Requirements (dependencies needed)
    - Settings schema (for capability-specific configuration)

    This endpoint is read-only and available to all authenticated users.
    """
    return AVAILABLE_CAPABILITIES


@router.get("/discord/config", response_model=DiscordBotConfig)
async def get_discord_bot_config(
    config_id: str = "global",
    user: User = Depends(get_current_user),
) -> DiscordBotConfig:
    """
    Get Discord bot configuration.

    Args:
        config_id: Configuration identifier ('global' for bot-wide config, or guild_id for per-guild)

    Returns:
        Current Discord bot configuration including enabled capabilities and their settings.
    """
    service = get_config_service()
    config = await service.get_config(config_id)
    return config


@router.put("/discord/config", response_model=DiscordBotConfig)
async def update_discord_bot_config(
    update: DiscordBotConfigUpdate,
    config_id: str = "global",
    user: User = Depends(require_admin),
) -> DiscordBotConfig:
    """
    Update Discord bot configuration (admin only).

    Args:
        update: Configuration update (enabled_capabilities and/or capability_settings)
        config_id: Configuration identifier ('global' for bot-wide config, or guild_id for per-guild)

    Returns:
        Updated Discord bot configuration.

    Raises:
        400: If invalid capability names are provided
        403: If user is not an admin
    """
    # Validate capability names if provided
    if update.enabled_capabilities is not None:
        invalid = validate_capabilities(update.enabled_capabilities)
        if invalid:
            valid_names = [cap.name for cap in AVAILABLE_CAPABILITIES]
            raise HTTPException(
                status_code=400,
                detail=f"Invalid capability names: {invalid}. Valid options are: {valid_names}",
            )

    # Validate capability settings keys if provided
    if update.capability_settings is not None:
        invalid_settings = validate_capabilities(list(update.capability_settings.keys()))
        if invalid_settings:
            valid_names = [cap.name for cap in AVAILABLE_CAPABILITIES]
            raise HTTPException(
                status_code=400,
                detail=f"Invalid capability names in settings: {invalid_settings}. Valid options are: {valid_names}",
            )

    service = get_config_service()
    config = await service.update_config(
        config_id=config_id,
        enabled_capabilities=update.enabled_capabilities,
        capability_settings=update.capability_settings,
        updated_by=user.email,
    )

    logger.info(
        f"Discord bot config updated by {user.email}: "
        f"capabilities={config.enabled_capabilities}"
    )

    return config


@router.post("/discord/config/capability/{capability_name}", response_model=DiscordBotConfig)
async def add_capability(
    capability_name: str,
    config_id: str = "global",
    user: User = Depends(require_admin),
) -> DiscordBotConfig:
    """
    Add a capability to the enabled list (admin only).

    Args:
        capability_name: Name of the capability to enable
        config_id: Configuration identifier

    Returns:
        Updated Discord bot configuration.
    """
    invalid = validate_capabilities([capability_name])
    if invalid:
        valid_names = [cap.name for cap in AVAILABLE_CAPABILITIES]
        raise HTTPException(
            status_code=400,
            detail=f"Invalid capability: {capability_name}. Valid options are: {valid_names}",
        )

    service = get_config_service()
    config = await service.add_capability(
        capability=capability_name,
        config_id=config_id,
        updated_by=user.email,
    )

    logger.info(f"Capability '{capability_name}' added by {user.email}")

    return config


@router.delete("/discord/config/capability/{capability_name}", response_model=DiscordBotConfig)
async def remove_capability(
    capability_name: str,
    config_id: str = "global",
    user: User = Depends(require_admin),
) -> DiscordBotConfig:
    """
    Remove a capability from the enabled list (admin only).

    Args:
        capability_name: Name of the capability to disable
        config_id: Configuration identifier

    Returns:
        Updated Discord bot configuration.
    """
    service = get_config_service()
    config = await service.remove_capability(
        capability=capability_name,
        config_id=config_id,
        updated_by=user.email,
    )

    logger.info(f"Capability '{capability_name}' removed by {user.email}")

    return config


@router.put(
    "/discord/config/capability/{capability_name}/settings",
    response_model=DiscordBotConfig,
)
async def update_capability_settings(
    capability_name: str,
    settings: dict,
    config_id: str = "global",
    user: User = Depends(require_admin),
) -> DiscordBotConfig:
    """
    Update settings for a specific capability (admin only).

    Args:
        capability_name: Name of the capability to configure
        settings: Settings dictionary to merge with existing settings
        config_id: Configuration identifier

    Returns:
        Updated Discord bot configuration.
    """
    invalid = validate_capabilities([capability_name])
    if invalid:
        valid_names = [cap.name for cap in AVAILABLE_CAPABILITIES]
        raise HTTPException(
            status_code=400,
            detail=f"Invalid capability: {capability_name}. Valid options are: {valid_names}",
        )

    service = get_config_service()
    config = await service.update_capability_settings(
        capability=capability_name,
        settings=settings,
        config_id=config_id,
        updated_by=user.email,
    )

    logger.info(f"Capability '{capability_name}' settings updated by {user.email}: {settings}")

    return config
