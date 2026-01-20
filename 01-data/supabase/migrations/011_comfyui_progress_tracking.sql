-- Migration: ComfyUI Workflow Progress Tracking
-- Description: Adds progress tracking columns to comfyui_workflow_runs for granular status updates
-- Created: 2026-01-20

-- Add progress tracking columns to comfyui_workflow_runs
ALTER TABLE comfyui_workflow_runs
ADD COLUMN IF NOT EXISTS progress_message TEXT,
ADD COLUMN IF NOT EXISTS images_completed INTEGER DEFAULT 0,
ADD COLUMN IF NOT EXISTS images_total INTEGER,
ADD COLUMN IF NOT EXISTS optimized_prompt TEXT;

-- Add index for status filtering (useful for finding active runs)
CREATE INDEX IF NOT EXISTS idx_comfyui_workflow_runs_status_started
ON comfyui_workflow_runs(status, started_at DESC)
WHERE status NOT IN ('completed', 'failed');

-- Comment on new columns
COMMENT ON COLUMN comfyui_workflow_runs.progress_message IS 'Human-readable status message for current operation';
COMMENT ON COLUMN comfyui_workflow_runs.images_completed IS 'Number of images successfully uploaded so far';
COMMENT ON COLUMN comfyui_workflow_runs.images_total IS 'Expected total number of images (from batch_size)';
COMMENT ON COLUMN comfyui_workflow_runs.optimized_prompt IS 'The enhanced/optimized prompt after LLM rewriting';
