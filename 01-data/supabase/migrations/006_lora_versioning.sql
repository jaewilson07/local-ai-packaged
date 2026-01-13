-- Migration: LoRA Versioning
-- Description: Adds versioning support for LoRA models so users can roll back to previous versions
-- Created: 2026-01-12
--
-- Design:
-- - character_name is now required and serves as the unique identifier (trigger word)
-- - Each user can only have ONE active LoRA per character_name
-- - Multiple versions can exist (is_active=false for old versions)
-- - version number auto-increments per user+character_name
-- - parent_id links to the previous version for history tracking

-- Make character_name NOT NULL (new uploads require it)
-- Note: Existing records may have NULL, we'll handle this in app code
-- ALTER TABLE comfyui_lora_models ALTER COLUMN character_name SET NOT NULL;
-- ^ Commented out to avoid breaking existing data - enforce in app layer

-- Add versioning columns
ALTER TABLE comfyui_lora_models
ADD COLUMN IF NOT EXISTS version INTEGER DEFAULT 1;

ALTER TABLE comfyui_lora_models
ADD COLUMN IF NOT EXISTS is_active BOOLEAN DEFAULT TRUE;

ALTER TABLE comfyui_lora_models
ADD COLUMN IF NOT EXISTS parent_id UUID REFERENCES comfyui_lora_models(id) ON DELETE SET NULL;

ALTER TABLE comfyui_lora_models
ADD COLUMN IF NOT EXISTS replaced_at TIMESTAMPTZ;

-- Add unique constraint: only one ACTIVE LoRA per user+character_name
-- This uses a partial unique index to only enforce uniqueness where is_active=true
CREATE UNIQUE INDEX IF NOT EXISTS idx_comfyui_lora_models_active_character
ON comfyui_lora_models(user_id, character_name)
WHERE is_active = TRUE AND character_name IS NOT NULL;

-- Index for version history queries
CREATE INDEX IF NOT EXISTS idx_comfyui_lora_models_parent_id
ON comfyui_lora_models(parent_id)
WHERE parent_id IS NOT NULL;

-- Index for listing active LoRAs
CREATE INDEX IF NOT EXISTS idx_comfyui_lora_models_is_active
ON comfyui_lora_models(user_id, is_active)
WHERE is_active = TRUE;

-- Comment explaining the versioning model
COMMENT ON COLUMN comfyui_lora_models.version IS 'Version number, auto-incremented per user+character_name';
COMMENT ON COLUMN comfyui_lora_models.is_active IS 'TRUE for current active version, FALSE for archived versions';
COMMENT ON COLUMN comfyui_lora_models.parent_id IS 'Reference to the previous version this replaced';
COMMENT ON COLUMN comfyui_lora_models.replaced_at IS 'Timestamp when this version was deactivated/replaced';
