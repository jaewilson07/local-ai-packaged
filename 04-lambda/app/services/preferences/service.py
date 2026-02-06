"""Preferences service for managing user and organization preferences."""

import json
from typing import Any
from uuid import UUID

from app.services.database.supabase.client import SupabaseClient
from app.services.database.supabase.config import SupabaseConfig
from app.services.preferences.config import FALLBACK_DEFAULTS
from app.services.preferences.models import PreferenceDefinition


class PreferencesService:
    """Service for managing hierarchical user preferences.

    Resolution order: User → Organization → System → Fallback

    Examples:
        >>> prefs = PreferencesService()
        >>> folder_id = await prefs.get(user.id, "google_drive.default_folder_id")
        >>> await prefs.set(user.id, "google_drive.default_folder_id", "abc123")
    """

    def __init__(self, supabase_config: SupabaseConfig | None = None):
        """Initialize preferences service.

        Args:
            supabase_config: Supabase configuration (creates new if not provided)
        """
        self.supabase = SupabaseClient(supabase_config or SupabaseConfig())

    async def get(
        self, user_id: UUID, key: str, organization_id: UUID | None = None, default: Any = None
    ) -> Any:
        """Get preference value with hierarchical resolution.

        Resolution order: User → Organization → System → Provided default → Fallback

        Args:
            user_id: User UUID
            key: Preference key (e.g., 'google_drive.default_folder_id')
            organization_id: Optional organization UUID (future - Phase 2)
            default: Fallback value if not found anywhere

        Returns:
            Preference value (type varies by preference definition)

        Examples:
            >>> folder_id = await prefs.get(user.id, "google_drive.default_folder_id")
            >>> temperature = await prefs.get(user.id, "llm.temperature", default=0.5)
        """
        try:
            pool = await self.supabase._get_pool()
            async with pool.acquire() as conn:
                # 1. Check user preferences
                user_pref = await conn.fetchrow(
                    "SELECT value FROM user_preferences WHERE user_id = $1 AND preference_key = $2",
                    user_id,
                    key,
                )
                if user_pref:
                    return user_pref["value"]

                # 2. Check organization preferences (if org_id provided)
                if organization_id:
                    org_pref = await conn.fetchrow(
                        "SELECT value FROM organization_preferences WHERE organization_id = $1 AND preference_key = $2",
                        organization_id,
                        key,
                    )
                    if org_pref:
                        return org_pref["value"]

                # 3. Fallback to system default
                sys_pref = await conn.fetchrow(
                    "SELECT default_value FROM preference_definitions WHERE key = $1", key
                )
                if sys_pref and sys_pref["default_value"] is not None:
                    return sys_pref["default_value"]
        except Exception as e:
            # Log error but don't fail - use fallback
            print(f"Error fetching preference {key}: {e}")

        # 4. Return provided default or fallback
        if default is not None:
            return default
        return FALLBACK_DEFAULTS.get(key)

    async def set(self, user_id: UUID, key: str, value: Any, validate: bool = True) -> None:
        """Set user preference value.

        Args:
            user_id: User UUID
            key: Preference key
            value: Preference value (will be stored as JSONB)
            validate: Whether to validate against schema (future enhancement)

        Raises:
            ValueError: If preference key not defined or not user-configurable

        Examples:
            >>> await prefs.set(user.id, "google_drive.default_folder_id", "abc123")
            >>> await prefs.set(user.id, "llm.temperature", 0.8)
        """
        pool = await self.supabase._get_pool()
        async with pool.acquire() as conn:
            # Validate preference exists and is user-configurable
            definition = await conn.fetchrow(
                "SELECT * FROM preference_definitions WHERE key = $1", key
            )
            if not definition:
                raise ValueError(f"Preference key '{key}' not defined in system")

            if not definition["is_user_configurable"]:
                raise ValueError(f"Preference '{key}' is not user-configurable")

            # TODO: Validate value against JSON schema if enabled
            # if validate and definition['validation_schema']:
            #     jsonschema.validate(value, definition['validation_schema'])

            # Convert value to JSONB format
            jsonb_value = json.dumps(value) if not isinstance(value, str) else json.dumps(value)

            # Upsert user preference
            await conn.execute(
                """
                INSERT INTO user_preferences (user_id, preference_key, value)
                VALUES ($1, $2, $3::jsonb)
                ON CONFLICT (user_id, preference_key)
                DO UPDATE SET value = EXCLUDED.value, updated_at = NOW()
                """,
                user_id,
                key,
                jsonb_value,
            )

    async def get_all(
        self, user_id: UUID, category: str | None = None, organization_id: UUID | None = None
    ) -> dict[str, Any]:
        """Get all preferences for a user, optionally filtered by category.

        Args:
            user_id: User UUID
            category: Optional category filter (e.g., 'google_drive', 'llm')
            organization_id: Optional organization UUID (future - Phase 2)

        Returns:
            Dict mapping preference keys to resolved values

        Examples:
            >>> all_prefs = await prefs.get_all(user.id)
            >>> drive_prefs = await prefs.get_all(user.id, category="google_drive")
        """
        pool = await self.supabase._get_pool()
        async with pool.acquire() as conn:
            # Get all preference definitions
            query = "SELECT * FROM preference_definitions WHERE is_user_configurable = true"
            params = []
            if category:
                query += " AND category = $1"
                params.append(category)

            definitions = await conn.fetch(query, *params)

            # Build result with hierarchy resolution
            result = {}
            for defn in definitions:
                key = defn["key"]
                result[key] = await self.get(user_id, key, organization_id)

            return result

    async def delete(self, user_id: UUID, key: str) -> None:
        """Delete user preference (reverts to system/org default).

        Args:
            user_id: User UUID
            key: Preference key to delete

        Examples:
            >>> await prefs.delete(user.id, "google_drive.default_folder_id")
            >>> # User will now use org or system default
        """
        pool = await self.supabase._get_pool()
        async with pool.acquire() as conn:
            await conn.execute(
                "DELETE FROM user_preferences WHERE user_id = $1 AND preference_key = $2",
                user_id,
                key,
            )

    async def get_definitions(
        self, category: str | None = None, user_configurable_only: bool = True
    ) -> list[PreferenceDefinition]:
        """Get available preference definitions.

        Args:
            category: Optional category filter
            user_configurable_only: Only return user-configurable preferences

        Returns:
            List of preference definitions
        """
        pool = await self.supabase._get_pool()
        async with pool.acquire() as conn:
            query = "SELECT * FROM preference_definitions WHERE 1=1"
            params = []

            if user_configurable_only:
                query += " AND is_user_configurable = true"

            if category:
                params.append(category)
                query += f" AND category = ${len(params)}"

            rows = await conn.fetch(query, *params)
            return [PreferenceDefinition(**dict(row)) for row in rows]

    async def get_categories(self) -> list[str]:
        """Get all available preference categories.

        Returns:
            List of category names (sorted alphabetically)
        """
        pool = await self.supabase._get_pool()
        async with pool.acquire() as conn:
            rows = await conn.fetch(
                "SELECT DISTINCT category FROM preference_definitions ORDER BY category"
            )
            return [row["category"] for row in rows]

    async def get_source(self, user_id: UUID, key: str, organization_id: UUID | None = None) -> str:
        """Determine the source of a preference value.

        Args:
            user_id: User UUID
            key: Preference key
            organization_id: Optional organization UUID

        Returns:
            'user', 'organization', or 'system'
        """
        pool = await self.supabase._get_pool()
        async with pool.acquire() as conn:
            # Check user preference
            user_pref = await conn.fetchrow(
                "SELECT 1 FROM user_preferences WHERE user_id = $1 AND preference_key = $2",
                user_id,
                key,
            )
            if user_pref:
                return "user"

            # Check organization preference
            if organization_id:
                org_pref = await conn.fetchrow(
                    "SELECT 1 FROM organization_preferences WHERE organization_id = $1 AND preference_key = $2",
                    organization_id,
                    key,
                )
                if org_pref:
                    return "organization"

            return "system"
