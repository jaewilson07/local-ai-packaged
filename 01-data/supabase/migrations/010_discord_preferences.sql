-- ============================================================================
-- Migration: 010_discord_preferences
-- Description: Add Discord bot configuration as Supabase preferences
-- Purpose: Consolidate Discord bot config from MongoDB to Supabase preferences
-- Created: 2026-01-20
-- ============================================================================

-- ============================================================================
-- Discord Preference Definitions
-- ============================================================================
-- These preferences replace the discord_bot_config MongoDB collection.
-- They use the existing hierarchical preferences system (User → Org → System).
--
-- Key mapping from MongoDB discord_bot_config:
--   enabled_capabilities -> discord.enabled_capabilities (admin-only)
--   capability_settings.* -> discord.capability.* (varies by setting)
-- ============================================================================

-- Insert Discord-specific preference definitions
INSERT INTO preference_definitions (key, category, data_type, default_value, validation_schema, description, is_user_configurable) VALUES

-- Core Discord preferences (admin-enforced, not user-configurable)
('discord.enabled_capabilities', 'discord', 'json', '["echo"]'::jsonb,
    '{
        "type": "array",
        "items": {
            "type": "string",
            "enum": ["echo", "upload", "character", "notification"]
        }
    }'::jsonb,
    'List of enabled Discord bot capabilities. Admin-only setting that controls which features are available.',
    false),

-- Per-capability settings (some user-configurable, some admin-only)

-- Upload capability settings
('discord.capability.upload.channel_id', 'discord', 'string', null,
    '{"type": ["string", "null"]}'::jsonb,
    'Channel ID to restrict uploads to (optional). Leave null to allow uploads in any channel.',
    false),

-- Character capability settings
('discord.capability.character.default_persona_id', 'discord', 'string', null,
    '{"type": ["string", "null"]}'::jsonb,
    'Default persona ID for character interactions. Can be overridden per channel.',
    true),

('discord.capability.character.engagement_probability', 'discord', 'number', '0.3'::jsonb,
    '{
        "type": "number",
        "minimum": 0,
        "maximum": 1
    }'::jsonb,
    'Probability of character engaging in conversation (0-1). Higher values mean more frequent engagement.',
    false),

('discord.capability.character.engagement_check_interval', 'discord', 'integer', '60'::jsonb,
    '{
        "type": "integer",
        "minimum": 10,
        "maximum": 3600
    }'::jsonb,
    'Seconds between engagement checks. Lower values mean more responsive but higher resource usage.',
    false),

-- Notification capability settings
('discord.capability.notification.poll_interval', 'discord', 'integer', '300'::jsonb,
    '{
        "type": "integer",
        "minimum": 30,
        "maximum": 3600
    }'::jsonb,
    'Seconds between Immich polls for face detection notifications.',
    false),

-- User-configurable Discord preferences
('discord.chat_mode', 'discord', 'string', '"echo"'::jsonb,
    '{
        "type": "string",
        "enum": ["echo", "basic_llm", "llm_rag", "llm_rag_personality"]
    }'::jsonb,
    'Chat mode for Discord interactions: echo (simple), basic_llm (LLM only), llm_rag (LLM with RAG), llm_rag_personality (full persona)',
    true),

('discord.personality_id', 'discord', 'string', null,
    '{"type": ["string", "null"]}'::jsonb,
    'Persona ID for personalized Discord interactions. Null uses default personality.',
    true),

('discord.rag_collection', 'discord', 'string', '"documents"'::jsonb,
    '{"type": "string"}'::jsonb,
    'MongoDB collection name for RAG document retrieval.',
    true),

('discord.notifications_enabled', 'discord', 'boolean', 'true'::jsonb,
    '{"type": "boolean"}'::jsonb,
    'Enable Discord notifications for background events (face detection, etc.)',
    true)

ON CONFLICT (key) DO UPDATE SET
    description = EXCLUDED.description,
    validation_schema = EXCLUDED.validation_schema,
    default_value = EXCLUDED.default_value;

-- ============================================================================
-- Guild-specific preferences table (optional extension)
-- ============================================================================
-- For per-guild configuration, we use the organization concept.
-- Each Discord guild maps to an organization.
-- Guild admins can set organization-level preferences that override system defaults.

-- Note: Guild → Organization mapping is handled by application logic.
-- When a Discord guild admin updates settings, the application:
-- 1. Creates an organization record for the guild (if not exists)
-- 2. Updates organization_preferences for that guild

-- ============================================================================
-- Helper function for Discord preferences
-- ============================================================================

-- Function to get Discord config as a single JSON object (for API compatibility)
CREATE OR REPLACE FUNCTION get_discord_config(
    p_user_id UUID DEFAULT NULL,
    p_guild_id TEXT DEFAULT NULL
) RETURNS JSONB AS $$
DECLARE
    v_org_id UUID;
    v_capabilities JSONB;
    v_settings JSONB;
    v_result JSONB;
BEGIN
    -- Get organization ID from guild_id if provided
    IF p_guild_id IS NOT NULL THEN
        SELECT id INTO v_org_id
        FROM organizations
        WHERE slug = 'discord-' || p_guild_id;
    END IF;

    -- Get enabled capabilities
    v_capabilities := COALESCE(
        get_user_preference(p_user_id, 'discord.enabled_capabilities', v_org_id),
        '["echo"]'::jsonb
    );

    -- Build capability settings object
    v_settings := jsonb_build_object(
        'upload', jsonb_build_object(
            'upload_channel_id', get_user_preference(p_user_id, 'discord.capability.upload.channel_id', v_org_id)
        ),
        'character', jsonb_build_object(
            'default_persona_id', get_user_preference(p_user_id, 'discord.capability.character.default_persona_id', v_org_id),
            'engagement_probability', get_user_preference(p_user_id, 'discord.capability.character.engagement_probability', v_org_id),
            'engagement_check_interval', get_user_preference(p_user_id, 'discord.capability.character.engagement_check_interval', v_org_id)
        ),
        'notification', jsonb_build_object(
            'poll_interval', get_user_preference(p_user_id, 'discord.capability.notification.poll_interval', v_org_id)
        )
    );

    -- Build result matching MongoDB discord_bot_config structure
    v_result := jsonb_build_object(
        'config_id', COALESCE(p_guild_id, 'global'),
        'enabled_capabilities', v_capabilities,
        'capability_settings', v_settings
    );

    RETURN v_result;
END;
$$ LANGUAGE plpgsql STABLE;

COMMENT ON FUNCTION get_discord_config IS 'Get Discord bot configuration as a JSON object compatible with MongoDB schema';

-- ============================================================================
-- Index for Discord preferences
-- ============================================================================

-- Index for faster Discord category lookups
CREATE INDEX IF NOT EXISTS idx_preference_definitions_discord
    ON preference_definitions(key)
    WHERE category = 'discord';
