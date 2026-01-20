"""REST API endpoints for user preferences management."""

from fastapi import APIRouter, Depends, HTTPException, Query
from services.auth.dependencies import get_current_user
from services.auth.models import User
from services.database.supabase.config import SupabaseConfig
from services.preferences.models import (
    CategoriesResponse,
    PreferenceDefinitionResponse,
    PreferenceResponse,
    PreferencesListResponse,
    PreferenceUpdateRequest,
)
from services.preferences.service import PreferencesService

router = APIRouter(prefix="/api/v1/preferences", tags=["preferences"])


def get_preferences_service() -> PreferencesService:
    """Dependency to get preferences service."""
    return PreferencesService(SupabaseConfig())


@router.get("/", response_model=PreferencesListResponse)
async def list_preferences(
    user: User = Depends(get_current_user),
    category: str | None = Query(None, description="Filter by category"),
    prefs_service: PreferencesService = Depends(get_preferences_service),
):
    """Get all preferences for the current user.

    Optionally filter by category (e.g., 'google_drive', 'llm', 'ui').
    Returns resolved values using hierarchy: User → Organization → System.
    """
    preferences = await prefs_service.get_all(user.id, category=category)
    return PreferencesListResponse(preferences=preferences, category=category)


@router.get("/categories", response_model=CategoriesResponse)
async def list_categories(
    user: User = Depends(get_current_user),
    prefs_service: PreferencesService = Depends(get_preferences_service),
):
    """Get all available preference categories."""
    categories = await prefs_service.get_categories()
    return CategoriesResponse(categories=categories)


@router.get("/definitions", response_model=list[PreferenceDefinitionResponse])
async def list_definitions(
    user: User = Depends(get_current_user),
    category: str | None = Query(None, description="Filter by category"),
    prefs_service: PreferencesService = Depends(get_preferences_service),
):
    """Get preference definitions (available preferences).

    Returns metadata about each preference including:
    - Key, category, data type
    - System default value
    - Description
    - Whether user can configure it
    """
    definitions = await prefs_service.get_definitions(
        category=category, user_configurable_only=True
    )
    return [
        PreferenceDefinitionResponse(
            key=d.key,
            category=d.category,
            data_type=d.data_type,
            default_value=d.default_value,
            description=d.description,
            is_user_configurable=d.is_user_configurable,
        )
        for d in definitions
    ]


@router.get("/{key}", response_model=PreferenceResponse)
async def get_preference(
    key: str,
    user: User = Depends(get_current_user),
    prefs_service: PreferencesService = Depends(get_preferences_service),
):
    """Get specific preference value with source tracking.

    Returns the effective value and indicates whether it came from:
    - User-specific override
    - Organization default (future)
    - System default
    """
    # Get resolved value
    value = await prefs_service.get(user.id, key)

    if value is None:
        raise HTTPException(status_code=404, detail=f"Preference '{key}' not found")

    # Determine source
    source = await prefs_service.get_source(user.id, key)

    return PreferenceResponse(key=key, value=value, source=source)


@router.put("/{key}")
async def update_preference(
    key: str,
    request: PreferenceUpdateRequest,
    user: User = Depends(get_current_user),
    prefs_service: PreferencesService = Depends(get_preferences_service),
):
    """Update or create user preference.

    Sets a user-specific override for the given preference key.
    The value will be validated against the preference's schema.
    """
    try:
        await prefs_service.set(user.id, key, request.value, validate=True)
        return {"status": "updated", "key": key, "value": request.value}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.delete("/{key}")
async def delete_preference(
    key: str,
    user: User = Depends(get_current_user),
    prefs_service: PreferencesService = Depends(get_preferences_service),
):
    """Delete user preference (revert to system/org default).

    Removes the user-specific override, causing the system or organization
    default to take effect.
    """
    await prefs_service.delete(user.id, key)
    return {"status": "deleted", "key": key}
