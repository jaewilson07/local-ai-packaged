-- Migration: ComfyUI Workflow Versioning
-- Description: Adds versioning support to comfyui_workflows table
-- Created: 2026-01-20

-- Add versioning columns to comfyui_workflows
ALTER TABLE comfyui_workflows
ADD COLUMN IF NOT EXISTS workflow_group_id UUID,
ADD COLUMN IF NOT EXISTS version INTEGER DEFAULT 1,
ADD COLUMN IF NOT EXISTS is_pinned BOOLEAN DEFAULT true,
ADD COLUMN IF NOT EXISTS version_notes TEXT,
ADD COLUMN IF NOT EXISTS parent_version_id UUID REFERENCES comfyui_workflows(id) ON DELETE SET NULL;

-- Add status and parameter_schema columns if they don't exist (needed for workflow management)
ALTER TABLE comfyui_workflows
ADD COLUMN IF NOT EXISTS status TEXT DEFAULT 'draft',
ADD COLUMN IF NOT EXISTS parameter_schema JSONB;

-- Add minio_paths and immich_asset_ids to workflow_runs if they don't exist
ALTER TABLE comfyui_workflow_runs
ADD COLUMN IF NOT EXISTS minio_paths TEXT[],
ADD COLUMN IF NOT EXISTS immich_asset_ids TEXT[];

-- Add character_name, version, and is_active to lora_models if they don't exist
ALTER TABLE comfyui_lora_models
ADD COLUMN IF NOT EXISTS character_name TEXT,
ADD COLUMN IF NOT EXISTS version INTEGER DEFAULT 1,
ADD COLUMN IF NOT EXISTS is_active BOOLEAN DEFAULT true;

-- Backfill: set workflow_group_id = id for existing workflows (first version of each workflow)
UPDATE comfyui_workflows
SET workflow_group_id = id
WHERE workflow_group_id IS NULL;

-- Make workflow_group_id NOT NULL after backfill
ALTER TABLE comfyui_workflows
ALTER COLUMN workflow_group_id SET NOT NULL;

-- Indexes for version queries
CREATE INDEX IF NOT EXISTS idx_comfyui_workflows_group_id
ON comfyui_workflows(workflow_group_id);

CREATE INDEX IF NOT EXISTS idx_comfyui_workflows_version
ON comfyui_workflows(workflow_group_id, version);

-- Partial index for finding pinned versions quickly
CREATE INDEX IF NOT EXISTS idx_comfyui_workflows_pinned
ON comfyui_workflows(workflow_group_id)
WHERE is_pinned = true;

-- Unique constraint: only one pinned version per group per user
-- This ensures data integrity - a user can only have one active version
CREATE UNIQUE INDEX IF NOT EXISTS idx_comfyui_workflows_unique_pinned
ON comfyui_workflows(workflow_group_id, user_id)
WHERE is_pinned = true;

-- Index for parent version lookups (for version history traversal)
CREATE INDEX IF NOT EXISTS idx_comfyui_workflows_parent
ON comfyui_workflows(parent_version_id);

-- Update RLS policies to handle versioning
-- Users can see all versions of workflows they own or that are public
DROP POLICY IF EXISTS "Users see own workflows" ON comfyui_workflows;
CREATE POLICY "Users see own workflows"
    ON comfyui_workflows FOR SELECT
    USING (user_id = auth.uid() OR is_public = true);

-- Function to ensure only one pinned version per workflow group
CREATE OR REPLACE FUNCTION ensure_single_pinned_version()
RETURNS TRIGGER AS $$
BEGIN
    -- If we're pinning this version, unpin all other versions in the same group for this user
    IF NEW.is_pinned = true THEN
        UPDATE comfyui_workflows
        SET is_pinned = false
        WHERE workflow_group_id = NEW.workflow_group_id
          AND user_id = NEW.user_id
          AND id != NEW.id
          AND is_pinned = true;
    END IF;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Trigger to maintain single pinned version constraint
DROP TRIGGER IF EXISTS trigger_ensure_single_pinned ON comfyui_workflows;
CREATE TRIGGER trigger_ensure_single_pinned
    BEFORE INSERT OR UPDATE OF is_pinned ON comfyui_workflows
    FOR EACH ROW
    WHEN (NEW.is_pinned = true)
    EXECUTE FUNCTION ensure_single_pinned_version();

-- Function to get the next version number for a workflow group
CREATE OR REPLACE FUNCTION get_next_workflow_version(p_workflow_group_id UUID)
RETURNS INTEGER AS $$
DECLARE
    max_version INTEGER;
BEGIN
    SELECT COALESCE(MAX(version), 0) INTO max_version
    FROM comfyui_workflows
    WHERE workflow_group_id = p_workflow_group_id;

    RETURN max_version + 1;
END;
$$ LANGUAGE plpgsql;
