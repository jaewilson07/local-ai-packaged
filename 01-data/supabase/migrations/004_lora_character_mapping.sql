-- Migration: LoRA Character Mapping
-- Description: Adds character_name field to comfyui_lora_models table for character-based LoRA selection
-- Created: 2025

-- Add character_name field to comfyui_lora_models
ALTER TABLE comfyui_lora_models
ADD COLUMN IF NOT EXISTS character_name TEXT;

-- Add index for character lookups
CREATE INDEX IF NOT EXISTS idx_comfyui_lora_models_character_name
ON comfyui_lora_models(character_name)
WHERE character_name IS NOT NULL;

-- Note: tags[] can also contain character names for flexible matching
