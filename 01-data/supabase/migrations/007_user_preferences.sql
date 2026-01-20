-- ============================================================================
-- Migration: 007_user_preferences
-- Description: Add hierarchical user preferences system (System → Org → User)
-- Created: 2026-01-14
-- ============================================================================

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

CREATE INDEX IF NOT EXISTS idx_user_preferences_user_id ON user_preferences(user_id);
CREATE INDEX IF NOT EXISTS idx_user_preferences_key ON user_preferences(preference_key);
CREATE INDEX IF NOT EXISTS idx_user_preferences_updated ON user_preferences(updated_at);

CREATE INDEX IF NOT EXISTS idx_preference_definitions_category ON preference_definitions(category);
CREATE INDEX IF NOT EXISTS idx_preference_definitions_configurable ON preference_definitions(is_user_configurable);

CREATE INDEX IF NOT EXISTS idx_org_members_user_id ON organization_members(user_id);
CREATE INDEX IF NOT EXISTS idx_org_prefs_org_id ON organization_preferences(organization_id);

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
