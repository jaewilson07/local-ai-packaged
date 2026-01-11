-- Migration: Workflow Publishing Status
-- Description: Adds status and published_at fields to comfyui_workflows table
-- Created: 2025

-- Add status field to comfyui_workflows
ALTER TABLE comfyui_workflows 
ADD COLUMN IF NOT EXISTS status TEXT DEFAULT 'draft' 
CHECK (status IN ('draft', 'published', 'archived'));

-- Add published_at timestamp
ALTER TABLE comfyui_workflows 
ADD COLUMN IF NOT EXISTS published_at TIMESTAMPTZ;

-- Create index for published workflows
CREATE INDEX IF NOT EXISTS idx_comfyui_workflows_status 
ON comfyui_workflows(status) 
WHERE status = 'published';

-- Update existing public workflows to published status
UPDATE comfyui_workflows 
SET status = 'published', published_at = created_at 
WHERE is_public = true AND status = 'draft';
