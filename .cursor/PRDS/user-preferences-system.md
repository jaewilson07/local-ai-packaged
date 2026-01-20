# PRD: Hierarchical User Preferences System

**Status:** Draft  
**Version:** 1.0  
**Created:** 2026-01-14  
**Owner:** Engineering Team

---

## Executive Summary

### Problem Statement

The Lambda FastAPI application currently lacks a structured preferences system, requiring users to repeatedly specify configuration parameters (e.g., `folder_id` for Google Drive, default LLM models, crawl depth) on every API call or workflow execution. This creates:

- **Poor UX**: No preference persistence across sessions
- **API Complexity**: Excessive required parameters in endpoints
- **Scalability Issues**: No foundation for organization-level features
- **Maintenance Burden**: Hardcoded defaults scattered across services

### Proposed Solution

Implement a hierarchical preference system following industry best practices for multi-tenant SaaS:

```
System Defaults → Organization Settings → User Preferences
  (Lowest)            (Medium)              (Highest Priority)
```

**Phase 1 (MVP)**: User-level preferences only (System → User hierarchy)  
**Phase 2**: Organization-level preferences (full System → Org → User hierarchy)

### Success Metrics

| Metric | Target | Measurement |
|--------|--------|-------------|
| API Parameter Reduction | 30% fewer required params | Parameter count before/after |
| User Satisfaction | +20% in UX surveys | Post-release user survey |
| Support Ticket Reduction | -25% preference-related tickets | Support ticket analysis |
| Feature Adoption | 60% users configure ≥1 pref | Analytics tracking |

---

## Architecture Overview

### System Context Diagram

```
┌─────────────────────────────────────────────────────────────────┐
│                     Lambda FastAPI Application                   │
│                                                                   │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │                     API Layer (Routes)                    │  │
│  │                                                             │  │
│  │  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐      │  │
│  │  │  Google     │  │   RAG       │  │   Crawl     │ ...  │  │
│  │  │  Drive      │  │   Search    │  │   4AI       │      │  │
│  │  └──────┬──────┘  └──────┬──────┘  └──────┬──────┘      │  │
│  │         │                 │                 │              │  │
│  │         └─────────────────┼─────────────────┘              │  │
│  │                           │                                 │  │
│  │                    ┌──────▼──────┐                         │  │
│  │                    │ Preferences │ ◄──── User Context      │  │
│  │                    │   Service   │       (from auth)       │  │
│  │                    └──────┬──────┘                         │  │
│  └───────────────────────────┼─────────────────────────────────┘  │
│                               │                                    │
│  ┌────────────────────────────▼───────────────────────────────┐  │
│  │              Supabase Postgres Database                     │  │
│  │                                                              │  │
│  │  ┌──────────────────┐  ┌──────────────────┐               │  │
│  │  │ preference_      │  │ user_            │               │  │
│  │  │ definitions      │  │ preferences      │               │  │
│  │  │ (System)         │  │ (User)           │               │  │
│  │  └──────────────────┘  └──────────────────┘               │  │
│  │                                                              │  │
│  │  ┌──────────────────┐  ┌──────────────────┐               │  │
│  │  │ organizations    │  │ organization_    │               │  │
│  │  │ (Future)         │  │ preferences      │               │  │
│  │  │                  │  │ (Future)         │               │  │
│  │  └──────────────────┘  └──────────────────┘               │  │
│  └──────────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────┘
```

### Preference Resolution Flow

```
┌─────────────────────────────────────────────────────────────────┐
│                        API Request                               │
│  GET /api/v1/google-drive/files?folder_id=<not_specified>      │
└────────────────────────┬────────────────────────────────────────┘
                         │
                         ▼
         ┌───────────────────────────────┐
         │  FastAPI Route Handler        │
         │  - Extract User from JWT      │
         │  - Inject PreferencesService  │
         └───────────┬───────────────────┘
                     │
                     ▼
         ┌───────────────────────────────┐
         │  PreferencesService.get()     │
         │  key: "google_drive.          │
         │       default_folder_id"      │
         └───────────┬───────────────────┘
                     │
         ┌───────────▼────────────────────────────────────────────┐
         │  Hierarchical Resolution (Priority Order)              │
         │                                                         │
         │  1. ┌────────────────────────────────┐                │
         │     │ user_preferences table         │ ◄─── HIGHEST   │
         │     │ WHERE user_id = $user_id       │      PRIORITY  │
         │     │ AND preference_key = $key      │                │
         │     └────────────┬───────────────────┘                │
         │                  │ Found? ───► Return value            │
         │                  │ Not found? ▼                        │
         │                                                         │
         │  2. ┌────────────────────────────────┐                │
         │     │ organization_preferences       │                │
         │     │ WHERE org_id = $user.org_id    │ ◄─── FUTURE    │
         │     │ AND preference_key = $key      │      (Phase 2) │
         │     └────────────┬───────────────────┘                │
         │                  │ Found? ───► Return value            │
         │                  │ Not found? ▼                        │
         │                                                         │
         │  3. ┌────────────────────────────────┐                │
         │     │ preference_definitions         │                │
         │     │ WHERE key = $key               │ ◄─── SYSTEM    │
         │     │ RETURN default_value           │      DEFAULT   │
         │     └────────────┬───────────────────┘                │
         │                  │                                     │
         │                  ▼                                     │
         │     Return system default or provided fallback        │
         └───────────────────────────────────────────────────────┘
                     │
                     ▼
         ┌───────────────────────────────┐
         │  Google Drive Service         │
         │  Uses resolved folder_id      │
         │  to execute search            │
         └───────────────────────────────┘
```

### Data Model

```sql
┌──────────────────────────────────────────────────────────────────┐
│                    preference_definitions                         │
│  (System-wide preference catalog - managed by admins)            │
├──────────────────┬───────────────────────────────────────────────┤
│ id               │ UUID PRIMARY KEY                              │
│ key              │ TEXT UNIQUE (e.g., 'google_drive.folder_id') │
│ category         │ TEXT (e.g., 'google_drive', 'llm', 'ui')     │
│ data_type        │ TEXT ('string', 'integer', 'boolean', 'json')│
│ default_value    │ JSONB                                         │
│ validation_schema│ JSONB (JSON Schema)                           │
│ description      │ TEXT                                          │
│ is_user_configurable   │ BOOLEAN                                 │
│ is_org_configurable    │ BOOLEAN (future)                        │
│ created_at       │ TIMESTAMPTZ                                   │
└──────────────────┴───────────────────────────────────────────────┘
                          │
                          │ Referenced by
                          ▼
┌──────────────────────────────────────────────────────────────────┐
│                      user_preferences                             │
│  (User-specific overrides)                                       │
├──────────────────┬───────────────────────────────────────────────┤
│ id               │ UUID PRIMARY KEY                              │
│ user_id          │ UUID → profiles(id)                           │
│ preference_key   │ TEXT → preference_definitions(key)            │
│ value            │ JSONB (user's custom value)                   │
│ created_at       │ TIMESTAMPTZ                                   │
│ updated_at       │ TIMESTAMPTZ                                   │
│                  │                                               │
│ UNIQUE(user_id, preference_key)                                  │
└──────────────────────────────────────────────────────────────────┘

┌──────────────────────────────────────────────────────────────────┐
│                      organizations                                │
│  (Future - Phase 2)                                              │
├──────────────────┬───────────────────────────────────────────────┤
│ id               │ UUID PRIMARY KEY                              │
│ name             │ TEXT                                          │
│ slug             │ TEXT UNIQUE                                   │
│ plan             │ TEXT ('free', 'pro', 'team', 'enterprise')   │
│ created_at       │ TIMESTAMPTZ                                   │
└──────────────────┴───────────────────────────────────────────────┘
                          │
                          │
                          ▼
┌──────────────────────────────────────────────────────────────────┐
│                  organization_preferences                         │
│  (Org-level defaults - Phase 2)                                  │
├──────────────────┬───────────────────────────────────────────────┤
│ id               │ UUID PRIMARY KEY                              │
│ organization_id  │ UUID → organizations(id)                      │
│ preference_key   │ TEXT → preference_definitions(key)            │
│ value            │ JSONB                                         │
│ created_at       │ TIMESTAMPTZ                                   │
│ updated_at       │ TIMESTAMPTZ                                   │
│                  │                                               │
│ UNIQUE(organization_id, preference_key)                          │
└──────────────────────────────────────────────────────────────────┘

┌──────────────────────────────────────────────────────────────────┐
│                   organization_members                            │
│  (User → Organization mapping - Phase 2)                         │
├──────────────────┬───────────────────────────────────────────────┤
│ organization_id  │ UUID → organizations(id)                      │
│ user_id          │ UUID → profiles(id)                           │
│ role             │ TEXT ('owner', 'admin', 'member')            │
│ joined_at        │ TIMESTAMPTZ                                   │
│                  │                                               │
│ PRIMARY KEY (organization_id, user_id)                           │
└──────────────────────────────────────────────────────────────────┘
```

---

## Detailed Design

### 1. Database Schema

**Migration:** `01-data/supabase/migrations/007_user_preferences.sql`

```sql
-- ============================================================================
-- Preference System Schema
-- ============================================================================

-- System-wide preference definitions (managed by admins)
CREATE TABLE IF NOT EXISTS preference_definitions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    key TEXT UNIQUE NOT NULL,              -- e.g., 'google_drive.default_folder_id'
    category TEXT NOT NULL,                 -- e.g., 'google_drive', 'llm', 'ui'
    data_type TEXT NOT NULL CHECK (data_type IN ('string', 'integer', 'boolean', 'number', 'json')),
    default_value JSONB,                    -- System default
    validation_schema JSONB,                -- JSON Schema for validation
    description TEXT,
    is_user_configurable BOOLEAN DEFAULT true,
    is_org_configurable BOOLEAN DEFAULT false,  -- Future: org-level control
    created_at TIMESTAMPTZ DEFAULT NOW()
);

COMMENT ON TABLE preference_definitions IS 'System-wide catalog of available preferences';
COMMENT ON COLUMN preference_definitions.key IS 'Dot-notation preference key (e.g., google_drive.default_folder_id)';
COMMENT ON COLUMN preference_definitions.validation_schema IS 'JSON Schema for validating preference values';

-- User preference values (user-specific overrides)
CREATE TABLE IF NOT EXISTS user_preferences (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES profiles(id) ON DELETE CASCADE,
    preference_key TEXT NOT NULL,           -- FK to preference_definitions.key
    value JSONB NOT NULL,                   -- User's preference value
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),

    UNIQUE(user_id, preference_key),
    FOREIGN KEY (preference_key) REFERENCES preference_definitions(key) ON DELETE CASCADE
);

COMMENT ON TABLE user_preferences IS 'User-specific preference overrides';

-- Organization support (future-proofing - Phase 2)
CREATE TABLE IF NOT EXISTS organizations (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name TEXT NOT NULL,
    slug TEXT UNIQUE NOT NULL,
    plan TEXT DEFAULT 'free' CHECK (plan IN ('free', 'pro', 'team', 'enterprise')),
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

COMMENT ON TABLE organizations IS 'Organizations/teams for multi-tenant support (Phase 2)';

CREATE TABLE IF NOT EXISTS organization_members (
    organization_id UUID NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
    user_id UUID NOT NULL REFERENCES profiles(id) ON DELETE CASCADE,
    role TEXT DEFAULT 'member' CHECK (role IN ('owner', 'admin', 'member')),
    joined_at TIMESTAMPTZ DEFAULT NOW(),
    PRIMARY KEY (organization_id, user_id)
);

COMMENT ON TABLE organization_members IS 'User membership in organizations';

CREATE TABLE IF NOT EXISTS organization_preferences (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    organization_id UUID NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
    preference_key TEXT NOT NULL,
    value JSONB NOT NULL,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),

    UNIQUE(organization_id, preference_key),
    FOREIGN KEY (preference_key) REFERENCES preference_definitions(key) ON DELETE CASCADE
);

COMMENT ON TABLE organization_preferences IS 'Organization-level preference defaults (Phase 2)';

-- ============================================================================
-- Indexes
-- ============================================================================

CREATE INDEX idx_user_preferences_user_id ON user_preferences(user_id);
CREATE INDEX idx_user_preferences_key ON user_preferences(preference_key);
CREATE INDEX idx_user_preferences_updated ON user_preferences(updated_at);

CREATE INDEX idx_preference_definitions_category ON preference_definitions(category);
CREATE INDEX idx_preference_definitions_configurable ON preference_definitions(is_user_configurable);

CREATE INDEX idx_org_members_user_id ON organization_members(user_id);
CREATE INDEX idx_org_prefs_org_id ON organization_preferences(organization_id);

-- ============================================================================
-- Seed Data: Initial Preference Definitions
-- ============================================================================

INSERT INTO preference_definitions (key, category, data_type, default_value, description, is_user_configurable) VALUES
-- Google Drive preferences
('google_drive.default_folder_id', 'google_drive', 'string', '"root"'::jsonb, 'Default Google Drive folder for searches', true),
('google_drive.search_scope', 'google_drive', 'string', '"my_drive"'::jsonb, 'Default search scope: my_drive, shared_drives, or all', true),
('google_drive.page_size', 'google_drive', 'integer', '10'::jsonb, 'Default page size for Drive API queries', true),

-- LLM preferences
('llm.default_model', 'llm', 'string', '"llama3.2"'::jsonb, 'Default LLM model for inference', true),
('llm.temperature', 'llm', 'number', '0.7'::jsonb, 'Default temperature for LLM sampling', true),
('llm.max_tokens', 'llm', 'integer', '2048'::jsonb, 'Default max tokens for LLM responses', true),
('llm.provider', 'llm', 'string', '"ollama"'::jsonb, 'LLM provider: ollama, openai, anthropic', true),

-- Embedding preferences
('embeddings.model', 'embeddings', 'string', '"qwen3-embedding:4b"'::jsonb, 'Default embedding model', true),
('embeddings.provider', 'embeddings', 'string', '"ollama"'::jsonb, 'Embedding provider', true),

-- UI preferences
('ui.theme', 'ui', 'string', '"dark"'::jsonb, 'UI theme: dark or light', true),
('ui.items_per_page', 'ui', 'integer', '50'::jsonb, 'Default pagination size', true),
('ui.default_view', 'ui', 'string', '"grid"'::jsonb, 'Default view mode: grid or list', true),

-- Web crawling preferences
('crawl.max_depth', 'crawl', 'integer', '3'::jsonb, 'Maximum crawl depth for web scraping', true),
('crawl.max_pages', 'crawl', 'integer', '100'::jsonb, 'Maximum pages to crawl', true),
('crawl.timeout', 'crawl', 'integer', '30'::jsonb, 'Request timeout in seconds', true),

-- RAG preferences
('rag.search_mode', 'rag', 'string', '"hybrid"'::jsonb, 'Search mode: semantic, keyword, or hybrid', true),
('rag.top_k', 'rag', 'integer', '10'::jsonb, 'Number of results to return', true),
('rag.use_rerank', 'rag', 'boolean', 'true'::jsonb, 'Enable reranking of search results', true),

-- Workflow preferences
('workflows.auto_save', 'workflows', 'boolean', 'true'::jsonb, 'Auto-save workflow changes', true),

-- Notification preferences
('notifications.email_enabled', 'notifications', 'boolean', 'true'::jsonb, 'Enable email notifications', true),
('notifications.discord_enabled', 'notifications', 'boolean', 'false'::jsonb, 'Enable Discord notifications', true),

-- Immich preferences
('immich.auto_backup', 'immich', 'boolean', 'false'::jsonb, 'Enable automatic backups to Immich', true),
('immich.backup_folder', 'immich', 'string', '"/backups"'::jsonb, 'Default backup folder path', true)

ON CONFLICT (key) DO NOTHING;

-- ============================================================================
-- Helper Functions
-- ============================================================================

-- Function to get effective preference value with hierarchy
CREATE OR REPLACE FUNCTION get_user_preference(
    p_user_id UUID,
    p_key TEXT,
    p_organization_id UUID DEFAULT NULL
) RETURNS JSONB AS $$
DECLARE
    v_value JSONB;
BEGIN
    -- 1. Check user preferences
    SELECT value INTO v_value
    FROM user_preferences
    WHERE user_id = p_user_id AND preference_key = p_key;

    IF v_value IS NOT NULL THEN
        RETURN v_value;
    END IF;

    -- 2. Check organization preferences (if org_id provided)
    IF p_organization_id IS NOT NULL THEN
        SELECT value INTO v_value
        FROM organization_preferences
        WHERE organization_id = p_organization_id AND preference_key = p_key;

        IF v_value IS NOT NULL THEN
            RETURN v_value;
        END IF;
    END IF;

    -- 3. Return system default
    SELECT default_value INTO v_value
    FROM preference_definitions
    WHERE key = p_key;

    RETURN v_value;
END;
$$ LANGUAGE plpgsql STABLE;

COMMENT ON FUNCTION get_user_preference IS 'Resolve preference value with hierarchy: User → Organization → System';

-- ============================================================================
-- RLS Policies (Row Level Security)
-- ============================================================================

-- Users can only read preference definitions that are user-configurable
ALTER TABLE preference_definitions ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Users can view configurable preferences"
ON preference_definitions FOR SELECT
USING (is_user_configurable = true);

-- Users can only manage their own preferences
ALTER TABLE user_preferences ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Users can view own preferences"
ON user_preferences FOR SELECT
USING (user_id = auth.uid());

CREATE POLICY "Users can insert own preferences"
ON user_preferences FOR INSERT
WITH CHECK (user_id = auth.uid());

CREATE POLICY "Users can update own preferences"
ON user_preferences FOR UPDATE
USING (user_id = auth.uid())
WITH CHECK (user_id = auth.uid());

CREATE POLICY "Users can delete own preferences"
ON user_preferences FOR DELETE
USING (user_id = auth.uid());

-- ============================================================================
-- Triggers
-- ============================================================================

-- Update updated_at timestamp
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER update_user_preferences_updated_at
BEFORE UPDATE ON user_preferences
FOR EACH ROW
EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_organization_preferences_updated_at
BEFORE UPDATE ON organization_preferences
FOR EACH ROW
EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_organizations_updated_at
BEFORE UPDATE ON organizations
FOR EACH ROW
EXECUTE FUNCTION update_updated_at_column();
```

### 2. Service Layer

**File:** `04-lambda/src/services/preferences/service.py`

```python
"""Preferences service for managing user and organization preferences."""

from typing import Any
from uuid import UUID
import json
from pydantic import BaseModel, Field

from src.services.database.supabase.client import SupabaseClient
from src.services.database.supabase.config import SupabaseConfig


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


class PreferencesService:
    """Service for managing hierarchical user preferences."""

    def __init__(self, supabase_config: SupabaseConfig | None = None):
        """Initialize preferences service.

        Args:
            supabase_config: Supabase configuration (creates new if not provided)
        """
        self.supabase = SupabaseClient(supabase_config or SupabaseConfig())

    async def get(
        self,
        user_id: UUID,
        key: str,
        organization_id: UUID | None = None,
        default: Any = None
    ) -> Any:
        """Get preference value with hierarchical resolution.

        Resolution order: User → Organization → System → Provided default

        Args:
            user_id: User UUID
            key: Preference key (e.g., 'google_drive.default_folder_id')
            organization_id: Optional organization UUID (future - Phase 2)
            default: Fallback value if not found anywhere

        Returns:
            Preference value (type varies by preference definition)

        Example:
            >>> prefs = PreferencesService()
            >>> folder_id = await prefs.get(user.id, "google_drive.default_folder_id")
            >>> # Returns user's preference, or org default, or system default
        """
        pool = await self.supabase._get_pool()
        async with pool.acquire() as conn:
            # 1. Check user preferences
            user_pref = await conn.fetchrow(
                "SELECT value FROM user_preferences WHERE user_id = $1 AND preference_key = $2",
                user_id, key
            )
            if user_pref:
                return user_pref['value']

            # 2. Check organization preferences (if org_id provided)
            if organization_id:
                org_pref = await conn.fetchrow(
                    "SELECT value FROM organization_preferences WHERE organization_id = $1 AND preference_key = $2",
                    organization_id, key
                )
                if org_pref:
                    return org_pref['value']

            # 3. Fallback to system default
            sys_pref = await conn.fetchrow(
                "SELECT default_value FROM preference_definitions WHERE key = $1",
                key
            )
            if sys_pref and sys_pref['default_value'] is not None:
                return sys_pref['default_value']

            # 4. Return provided default
            return default

    async def set(
        self,
        user_id: UUID,
        key: str,
        value: Any,
        validate: bool = True
    ) -> None:
        """Set user preference value.

        Args:
            user_id: User UUID
            key: Preference key
            value: Preference value (will be stored as JSONB)
            validate: Whether to validate against schema (future enhancement)

        Raises:
            ValueError: If preference key not defined or not user-configurable

        Example:
            >>> await prefs.set(
            ...     user.id,
            ...     "google_drive.default_folder_id",
            ...     "1abc123xyz"
            ... )
        """
        pool = await self.supabase._get_pool()
        async with pool.acquire() as conn:
            # Validate preference exists and is user-configurable
            definition = await conn.fetchrow(
                "SELECT * FROM preference_definitions WHERE key = $1",
                key
            )
            if not definition:
                raise ValueError(f"Preference key '{key}' not defined in system")

            if not definition['is_user_configurable']:
                raise ValueError(f"Preference '{key}' is not user-configurable")

            # TODO: Validate value against JSON schema if enabled
            # if validate and definition['validation_schema']:
            #     jsonschema.validate(value, definition['validation_schema'])

            # Upsert user preference
            await conn.execute(
                """
                INSERT INTO user_preferences (user_id, preference_key, value)
                VALUES ($1, $2, $3)
                ON CONFLICT (user_id, preference_key)
                DO UPDATE SET value = EXCLUDED.value, updated_at = NOW()
                """,
                user_id, key, json.dumps(value)
            )

    async def get_all(
        self,
        user_id: UUID,
        category: str | None = None,
        organization_id: UUID | None = None
    ) -> dict[str, Any]:
        """Get all preferences for a user, optionally filtered by category.

        Args:
            user_id: User UUID
            category: Optional category filter (e.g., 'google_drive', 'llm')
            organization_id: Optional organization UUID (future - Phase 2)

        Returns:
            Dict mapping preference keys to resolved values

        Example:
            >>> prefs = await prefs.get_all(user.id, category="google_drive")
            >>> # {"google_drive.default_folder_id": "abc123", ...}
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
                key = defn['key']
                result[key] = await self.get(user_id, key, organization_id)

            return result

    async def delete(self, user_id: UUID, key: str) -> None:
        """Delete user preference (reverts to system/org default).

        Args:
            user_id: User UUID
            key: Preference key to delete

        Example:
            >>> await prefs.delete(user.id, "google_drive.default_folder_id")
            >>> # User will now use org or system default
        """
        pool = await self.supabase._get_pool()
        async with pool.acquire() as conn:
            await conn.execute(
                "DELETE FROM user_preferences WHERE user_id = $1 AND preference_key = $2",
                user_id, key
            )

    async def get_definitions(
        self,
        category: str | None = None,
        user_configurable_only: bool = True
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
            List of category names
        """
        pool = await self.supabase._get_pool()
        async with pool.acquire() as conn:
            rows = await conn.fetch(
                "SELECT DISTINCT category FROM preference_definitions ORDER BY category"
            )
            return [row['category'] for row in rows]
```

**File:** `04-lambda/src/services/preferences/models.py`

```python
"""Pydantic models for preferences API."""

from pydantic import BaseModel, Field
from typing import Any


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
```

### 3. API Endpoints

**File:** `04-lambda/src/services/preferences/router.py`

```python
"""REST API endpoints for user preferences management."""

from fastapi import APIRouter, Depends, HTTPException, Query
from uuid import UUID
from typing import Any

from src.services.auth.dependencies import get_current_user
from src.services.auth.models import User
from src.services.preferences.service import PreferencesService
from src.services.preferences.models import (
    PreferenceUpdateRequest,
    PreferenceResponse,
    PreferencesListResponse,
    PreferenceDefinitionResponse,
    CategoriesResponse
)
from src.services.database.supabase.config import SupabaseConfig


router = APIRouter(prefix="/api/v1/preferences", tags=["preferences"])


def get_preferences_service() -> PreferencesService:
    """Dependency to get preferences service."""
    return PreferencesService(SupabaseConfig())


@router.get("/", response_model=PreferencesListResponse)
async def list_preferences(
    user: User = Depends(get_current_user),
    category: str | None = Query(None, description="Filter by category"),
    prefs_service: PreferencesService = Depends(get_preferences_service)
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
    prefs_service: PreferencesService = Depends(get_preferences_service)
):
    """Get all available preference categories."""
    categories = await prefs_service.get_categories()
    return CategoriesResponse(categories=categories)


@router.get("/definitions", response_model=list[PreferenceDefinitionResponse])
async def list_definitions(
    user: User = Depends(get_current_user),
    category: str | None = Query(None, description="Filter by category"),
    prefs_service: PreferencesService = Depends(get_preferences_service)
):
    """Get preference definitions (available preferences).

    Returns metadata about each preference including:
    - Key, category, data type
    - System default value
    - Description
    - Whether user can configure it
    """
    definitions = await prefs_service.get_definitions(
        category=category,
        user_configurable_only=True
    )
    return [
        PreferenceDefinitionResponse(
            key=d.key,
            category=d.category,
            data_type=d.data_type,
            default_value=d.default_value,
            description=d.description,
            is_user_configurable=d.is_user_configurable
        )
        for d in definitions
    ]


@router.get("/{key}", response_model=PreferenceResponse)
async def get_preference(
    key: str,
    user: User = Depends(get_current_user),
    prefs_service: PreferencesService = Depends(get_preferences_service)
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

    # Determine source (simplified - could be enhanced to track actual source)
    pool = await prefs_service.supabase._get_pool()
    async with pool.acquire() as conn:
        user_pref = await conn.fetchrow(
            "SELECT 1 FROM user_preferences WHERE user_id = $1 AND preference_key = $2",
            user.id, key
        )
        source = "user" if user_pref else "system"

    return PreferenceResponse(key=key, value=value, source=source)


@router.put("/{key}")
async def update_preference(
    key: str,
    request: PreferenceUpdateRequest,
    user: User = Depends(get_current_user),
    prefs_service: PreferencesService = Depends(get_preferences_service)
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
    prefs_service: PreferencesService = Depends(get_preferences_service)
):
    """Delete user preference (revert to system/org default).

    Removes the user-specific override, causing the system or organization
    default to take effect.
    """
    await prefs_service.delete(user.id, key)
    return {"status": "deleted", "key": key}
```

### 4. Router Registration

**File:** `04-lambda/src/server/main.py` (modifications)

```python
# Add to imports
from src.services.preferences import router as preferences_router

# Add to router registration (around line 80)
app.include_router(
    preferences_router.router,
    tags=["preferences"]
)
```

---

## Integration Patterns

### Pattern 1: Route-Level Preference Resolution

**Before (hardcoded/manual parameters):**

```python
@router.post("/google-drive/search")
async def search_files(
    folder_id: str | None = None,  # User must specify every time
    user: User = Depends(get_current_user)
):
    google_drive = GoogleDrive(authenticator)
    files = await google_drive.search_files(folder_id=folder_id or "root")
    return files
```

**After (preference-aware):**

```python
@router.post("/google-drive/search")
async def search_files(
    folder_id: str | None = None,  # Optional override
    user: User = Depends(get_current_user),
    prefs: PreferencesService = Depends(get_preferences_service)
):
    # Resolve preference: explicit param → user pref → system default
    resolved_folder_id = folder_id or await prefs.get(
        user.id,
        "google_drive.default_folder_id",
        default="root"
    )

    google_drive = GoogleDrive(authenticator)
    files = await google_drive.search_files(folder_id=resolved_folder_id)
    return files
```

### Pattern 2: Dependency Injection with Preferences

**For complex services, pass PreferencesService to dependencies:**

```python
# In workflow dependencies (e.g., crawl4ai_rag/ai/dependencies.py)
class CrawlDependencies(BaseModel):
    user: User
    preferences: PreferencesService

    async def get_crawl_config(self) -> dict:
        """Get crawl configuration from preferences."""
        return {
            "max_depth": await self.preferences.get(
                self.user.id,
                "crawl.max_depth",
                default=3
            ),
            "max_pages": await self.preferences.get(
                self.user.id,
                "crawl.max_pages",
                default=100
            ),
            "timeout": await self.preferences.get(
                self.user.id,
                "crawl.timeout",
                default=30
            )
        }
```

### Pattern 3: Pydantic AI Agent Context

**For Pydantic AI agents with RunContext:**

```python
from pydantic_ai import Agent, RunContext

# Agent dependencies include preferences
class RAGDeps(BaseModel):
    user: User
    preferences: PreferencesService
    mongodb_client: MongoDBClient

    async def initialize(self):
        await self.mongodb_client.connect()

# Tool uses preferences via RunContext
@rag_agent.tool
async def semantic_search(
    ctx: RunContext[RAGDeps],
    query: str
) -> list[dict]:
    """Semantic search with user-preferred settings."""
    # Get user's preferred search mode
    search_mode = await ctx.deps.preferences.get(
        ctx.deps.user.id,
        "rag.search_mode",
        default="hybrid"
    )

    top_k = await ctx.deps.preferences.get(
        ctx.deps.user.id,
        "rag.top_k",
        default=10
    )

    # Use preferences in search
    results = await ctx.deps.mongodb_client.search(
        query=query,
        mode=search_mode,
        limit=top_k
    )
    return results
```

---

## Implementation Roadmap

### Phase 1: MVP - User Preferences (4-6 weeks)

**Week 1-2: Foundation**
- [ ] Create database migration `007_user_preferences.sql`
- [ ] Run migration and verify schema
- [ ] Create `PreferencesService` class
- [ ] Create Pydantic models for API
- [ ] Unit tests for service layer (>80% coverage)

**Week 3: API Layer**
- [ ] Create preferences REST API router
- [ ] Register router in `main.py`
- [ ] Create FastAPI dependency factory
- [ ] Integration tests for endpoints
- [ ] API documentation (OpenAPI)

**Week 4: Service Integration**
- [ ] Integrate into Google Drive service/routes
- [ ] Integrate into RAG search routes
- [ ] Integrate into Crawl4AI workflow
- [ ] Update existing route handlers

**Week 5: Testing & Documentation**
- [ ] End-to-end testing with sample scripts
- [ ] Performance testing (preference resolution latency)
- [ ] Update `AGENTS.md` documentation
- [ ] Create user guide in `docs/`
- [ ] Create sample scripts in `sample/preferences/`

**Week 6: Deployment & Monitoring**
- [ ] Deploy to staging environment
- [ ] Monitor preference usage analytics
- [ ] Gather user feedback
- [ ] Bug fixes and refinements
- [ ] Production deployment

### Phase 2: Organization Support (Future - 8-10 weeks)

**Week 1-2: Organization Schema**
- [ ] Activate organization tables
- [ ] Create organization CRUD APIs
- [ ] Membership management endpoints
- [ ] Organization preference resolution

**Week 3-4: Multi-Tenant Updates**
- [ ] Update authentication to include org context
- [ ] Extend preference service for org hierarchy
- [ ] Update RLS policies for org isolation
- [ ] Organization admin UI

**Week 5-6: Billing Integration**
- [ ] Plan-based preference restrictions
- [ ] Usage tracking per organization
- [ ] Billing API integration
- [ ] Plan upgrade/downgrade workflows

**Week 7-8: Testing & Rollout**
- [ ] Multi-tenant testing
- [ ] Organization migration tools
- [ ] Documentation updates
- [ ] Gradual rollout to beta users

### Phase 3: Advanced Features (Future - TBD)

- [ ] Preference audit logging
- [ ] Preference history/versioning
- [ ] Bulk preference import/export
- [ ] Preference templates
- [ ] JSON Schema validation
- [ ] Preference recommendations (AI-powered)
- [ ] A/B testing via preferences
- [ ] Feature flags integration

---

## Success Metrics

### Key Performance Indicators

| Metric | Baseline | Target (3 months) | Measurement Method |
|--------|----------|-------------------|-------------------|
| **Adoption Rate** | 0% | 60% of users configure ≥1 pref | Analytics tracking |
| **API Complexity** | Avg 5 required params/endpoint | 3.5 required params | Code analysis |
| **Support Tickets** | 100/month preference-related | 75/month | Support system |
| **User Satisfaction** | Baseline survey score | +20% improvement | Post-release survey |
| **Preference Resolution Time** | N/A | <50ms p95 | APM monitoring |
| **Data Consistency** | N/A | 99.9% preference cache hit rate | Redis metrics |

### Monitoring Dashboards

**Operational Metrics:**
- Preference read/write latency
- Cache hit rates
- Error rates by endpoint
- Database query performance

**Business Metrics:**
- Most configured preferences (by category)
- Preference usage by user tier
- Feature adoption curves
- User retention correlation

---

## Risk Assessment

### Technical Risks

| Risk | Impact | Probability | Mitigation |
|------|--------|-------------|------------|
| **Database performance** | High | Medium | Index optimization, connection pooling |
| **Cache invalidation bugs** | Medium | Medium | Comprehensive testing, monitoring |
| **Schema migration failures** | High | Low | Tested migration rollback scripts |
| **Type coercion errors** | Medium | Medium | Strict JSON Schema validation |

### Product Risks

| Risk | Impact | Probability | Mitigation |
|------|--------|-------------|------------|
| **Low user adoption** | High | Medium | User education, sensible defaults |
| **Preference sprawl** | Medium | High | Strict governance, category review |
| **Breaking changes** | High | Low | Backward compatibility, versioning |
| **User confusion** | Medium | Medium | Clear UI, good documentation |

---

## Open Questions & Decisions

### Architecture Decisions

1. **Caching Strategy:**
   - **Question:** Redis cache for preferences or direct DB queries?
   - **Recommendation:** Start without caching (premature optimization), add Redis if latency >100ms p95
   - **Decision:** ⏳ Pending performance testing

2. **Validation Enforcement:**
   - **Question:** Strict JSON Schema validation or lenient type coercion?
   - **Recommendation:** Lenient for MVP, strict in Phase 2
   - **Decision:** ⏳ Pending team discussion

3. **Organization Hierarchy:**
   - **Question:** Single-level orgs or nested workspaces (Org → Team → User)?
   - **Recommendation:** Single-level for Phase 2, evaluate nesting later
   - **Decision:** ✅ Single-level organizations

### Product Decisions

1. **Default Overrides:**
   - **Question:** Can users override organization-enforced preferences?
   - **Recommendation:** Add  flag in definitions
   - **Decision:** ⏳ Pending product requirements

2. **Preference Discovery:**
   - **Question:** Auto-suggest preferences based on usage patterns?
   - **Recommendation:** Phase 3 feature (AI-powered recommendations)
   - **Decision:** ✅ Defer to Phase 3

3. **Audit Requirements:**
   - **Question:** Need full audit trail for compliance?
   - **Recommendation:** Add in Phase 2 if enterprise customers require it
   - **Decision:** ⏳ Pending business development feedback

---

## Appendix

### A. Preference Category Reference

**Complete list of proposed preference categories:**

| Category | Preferences | Priority |
|----------|-------------|----------|
| `google_drive` | default_folder_id, search_scope, page_size | Phase 1 |
| `llm` | default_model, temperature, max_tokens, provider | Phase 1 |
| `embeddings` | model, provider, dimension | Phase 1 |
| `ui` | theme, items_per_page, default_view | Phase 1 |
| `crawl` | max_depth, max_pages, timeout | Phase 1 |
| `rag` | search_mode, top_k, use_rerank | Phase 1 |
| `workflows` | default_workflow, auto_save | Phase 1 |
| `notifications` | email_enabled, discord_enabled | Phase 2 |
| `immich` | auto_backup, backup_folder | Phase 2 |
| `comfyui` | default_workflow, auto_download_models | Phase 2 |
| `n8n` | default_workflow, auto_activate | Phase 2 |
| `billing` | plan, usage_limits | Phase 2 (Org-level) |
| `security` | mfa_enabled, session_timeout | Phase 2 |
| `features` | graphiti_enabled, langfuse_enabled | Phase 3 (Feature flags) |

### B. API Examples

**Complete API usage examples:**

```bash
# 1. List all preferences
curl -X GET "https://api.example.com/api/v1/preferences" \
  -H "Cf-Access-Jwt-Assertion: $JWT_TOKEN"

# Response:
{
  "preferences": {
    "google_drive.default_folder_id": "root",
    "llm.default_model": "llama3.2",
    "llm.temperature": 0.7,
    "ui.theme": "dark",
    ...
  },
  "category": null
}

# 2. List preferences by category
curl -X GET "https://api.example.com/api/v1/preferences?category=google_drive" \
  -H "Cf-Access-Jwt-Assertion: $JWT_TOKEN"

# Response:
{
  "preferences": {
    "google_drive.default_folder_id": "root",
    "google_drive.search_scope": "my_drive",
    "google_drive.page_size": 10
  },
  "category": "google_drive"
}

# 3. Get specific preference
curl -X GET "https://api.example.com/api/v1/preferences/google_drive.default_folder_id" \
  -H "Cf-Access-Jwt-Assertion: $JWT_TOKEN"

# Response:
{
  "key": "google_drive.default_folder_id",
  "value": "13ICM72u7cnvCb0ATpVXdHWqxH1SmiG_Q",
  "source": "user"
}

# 4. Update preference
curl -X PUT "https://api.example.com/api/v1/preferences/google_drive.default_folder_id" \
  -H "Cf-Access-Jwt-Assertion: $JWT_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"value": "13ICM72u7cnvCb0ATpVXdHWqxH1SmiG_Q"}'

# Response:
{
  "status": "updated",
  "key": "google_drive.default_folder_id",
  "value": "13ICM72u7cnvCb0ATpVXdHWqxH1SmiG_Q"
}

# 5. Delete preference (revert to default)
curl -X DELETE "https://api.example.com/api/v1/preferences/google_drive.default_folder_id" \
  -H "Cf-Access-Jwt-Assertion: $JWT_TOKEN"

# Response:
{
  "status": "deleted",
  "key": "google_drive.default_folder_id"
}

# 6. List all categories
curl -X GET "https://api.example.com/api/v1/preferences/categories" \
  -H "Cf-Access-Jwt-Assertion: $JWT_TOKEN"

# Response:
{
  "categories": [
    "crawl",
    "embeddings",
    "google_drive",
    "immich",
    "llm",
    "notifications",
    "rag",
    "ui",
    "workflows"
  ]
}

# 7. List preference definitions
curl -X GET "https://api.example.com/api/v1/preferences/definitions?category=google_drive" \
  -H "Cf-Access-Jwt-Assertion: $JWT_TOKEN"

# Response:
[
  {
    "key": "google_drive.default_folder_id",
    "category": "google_drive",
    "data_type": "string",
    "default_value": "root",
    "description": "Default Google Drive folder for searches",
    "is_user_configurable": true
  },
  {
    "key": "google_drive.search_scope",
    "category": "google_drive",
    "data_type": "string",
    "default_value": "my_drive",
    "description": "Default search scope: my_drive, shared_drives, or all",
    "is_user_configurable": true
  }
]
```

### C. Database Query Examples

**Common SQL patterns:**

```sql
-- Get effective preference with hierarchy
SELECT get_user_preference(
    'user-uuid'::UUID,
    'google_drive.default_folder_id'
);

-- List all user overrides
SELECT
    p.key,
    p.category,
    p.default_value AS system_default,
    up.value AS user_value,
    up.updated_at
FROM preference_definitions p
LEFT JOIN user_preferences up
    ON p.key = up.preference_key
    AND up.user_id = 'user-uuid'::UUID
WHERE p.is_user_configurable = true
ORDER BY p.category, p.key;

-- Find users who customized specific preference
SELECT
    u.email,
    up.value,
    up.updated_at
FROM user_preferences up
JOIN profiles u ON up.user_id = u.id
WHERE up.preference_key = 'llm.default_model'
ORDER BY up.updated_at DESC;

-- Preference usage statistics
SELECT
    preference_key,
    COUNT(*) AS num_users,
    COUNT(DISTINCT value) AS unique_values
FROM user_preferences
GROUP BY preference_key
ORDER BY num_users DESC;
```

---

## Approval & Sign-Off

**Stakeholders:**

| Role | Name | Sign-Off | Date |
|------|------|----------|------|
| Engineering Lead | TBD | ⏳ Pending | - |
| Product Manager | TBD | ⏳ Pending | - |
| Backend Engineer | TBD | ⏳ Pending | - |
| QA Lead | TBD | ⏳ Pending | - |

**Review History:**

- 2026-01-14: Initial PRD draft created
- TBD: Technical review
- TBD: Product review
- TBD: Final approval

---

**Document End**
