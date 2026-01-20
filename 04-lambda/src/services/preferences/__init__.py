"""Preferences service module for managing hierarchical user preferences.

This module provides a centralized service for managing user, organization,
and system-level preferences with hierarchical resolution:

    System Defaults → Organization Settings → User Preferences
       (Lowest)            (Medium)              (Highest Priority)

Phase 1 (MVP): User-level preferences only (System → User hierarchy)
Phase 2: Organization-level preferences (full System → Org → User hierarchy)

Discord Bot Configuration:
    The discord_service module provides backward-compatible API for Discord bot
    configuration, migrating from MongoDB to Supabase preferences.
"""

from .config import PreferenceCategories, PreferenceKeys
from .discord_service import (
    AVAILABLE_CAPABILITIES,
    CapabilityInfo,
    DiscordBotConfig,
    DiscordBotConfigUpdate,
    DiscordConfigService,
    DiscordPreferenceKeys,
    get_capability_info,
    validate_capabilities,
)
from .models import (
    CategoriesResponse,
    PreferenceDefinition,
    PreferenceDefinitionResponse,
    PreferenceResponse,
    PreferencesListResponse,
    PreferenceUpdateRequest,
    UserPreference,
)
from .service import PreferencesService

__all__ = [
    # Core preferences
    "PreferencesService",
    "PreferenceDefinition",
    "UserPreference",
    "PreferenceUpdateRequest",
    "PreferenceResponse",
    "PreferencesListResponse",
    "PreferenceDefinitionResponse",
    "CategoriesResponse",
    "PreferenceCategories",
    "PreferenceKeys",
    # Discord configuration
    "DiscordConfigService",
    "DiscordBotConfig",
    "DiscordBotConfigUpdate",
    "CapabilityInfo",
    "AVAILABLE_CAPABILITIES",
    "get_capability_info",
    "validate_capabilities",
    "DiscordPreferenceKeys",
]
