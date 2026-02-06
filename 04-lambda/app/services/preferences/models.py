"""Pydantic models for preferences API."""

from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field


class PreferenceDefinition(BaseModel):
    """Preference definition model."""

    key: str
    category: str
    data_type: str
    default_value: Any | None = None
    validation_schema: dict | None = None
    description: str | None = None
    is_user_configurable: bool = True
    is_org_configurable: bool = False


class UserPreference(BaseModel):
    """User preference model."""

    id: UUID
    user_id: UUID
    preference_key: str
    value: Any
    created_at: str
    updated_at: str


class PreferenceUpdateRequest(BaseModel):
    """Request model for updating a preference."""

    value: Any = Field(..., description="Preference value (type depends on preference)")


class PreferenceResponse(BaseModel):
    """Response model for preference value."""

    key: str
    value: Any
    source: str = Field(..., description="Source of value: 'user', 'organization', or 'system'")


class PreferencesListResponse(BaseModel):
    """Response model for listing preferences."""

    preferences: dict[str, Any]
    category: str | None = None


class PreferenceDefinitionResponse(BaseModel):
    """Response model for preference definition."""

    key: str
    category: str
    data_type: str
    default_value: Any | None
    description: str | None
    is_user_configurable: bool


class CategoriesResponse(BaseModel):
    """Response model for categories list."""

    categories: list[str]
