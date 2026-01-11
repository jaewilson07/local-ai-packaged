-- Migration: Workflow Parameter Schema
-- Description: Adds parameter_schema JSONB field to comfyui_workflows table
-- Created: 2025

-- Add parameter_schema JSONB field
ALTER TABLE comfyui_workflows 
ADD COLUMN IF NOT EXISTS parameter_schema JSONB;

-- Example parameter_schema structure:
-- {
--   "num_images": {"type": "integer", "default": 1, "min": 1, "max": 10},
--   "prompt": {"type": "string", "required": true},
--   "lora_character": {"type": "string", "required": false},
--   "lora_custom": {"type": "string", "required": false}
-- }
