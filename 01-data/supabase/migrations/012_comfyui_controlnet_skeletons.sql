-- Migration: Create comfyui_controlnet_skeletons table
-- Description: Store ControlNet skeleton images with metadata for semantic search
-- Author: AI Assistant
-- Date: 2026-01-20

-- Create the controlnet skeletons table
CREATE TABLE IF NOT EXISTS comfyui_controlnet_skeletons (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    name TEXT NOT NULL,
    description TEXT,
    minio_path TEXT NOT NULL,
    preprocessor_type TEXT NOT NULL, -- 'canny', 'depth', 'openpose', etc.
    tags TEXT[] DEFAULT '{}',
    embedding_id TEXT, -- MongoDB document ID containing the embedding
    is_public BOOLEAN DEFAULT true,
    metadata JSONB DEFAULT '{}', -- Flexible storage for pose data, dimensions, etc.
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Create indexes for common queries
CREATE INDEX IF NOT EXISTS idx_controlnet_skeletons_user_id
    ON comfyui_controlnet_skeletons(user_id);

CREATE INDEX IF NOT EXISTS idx_controlnet_skeletons_preprocessor_type
    ON comfyui_controlnet_skeletons(preprocessor_type);

CREATE INDEX IF NOT EXISTS idx_controlnet_skeletons_is_public
    ON comfyui_controlnet_skeletons(is_public);

CREATE INDEX IF NOT EXISTS idx_controlnet_skeletons_tags
    ON comfyui_controlnet_skeletons USING GIN(tags);

CREATE INDEX IF NOT EXISTS idx_controlnet_skeletons_created_at
    ON comfyui_controlnet_skeletons(created_at DESC);

-- Enable Row Level Security
ALTER TABLE comfyui_controlnet_skeletons ENABLE ROW LEVEL SECURITY;

-- Policy: Users can view their own skeletons
CREATE POLICY controlnet_skeletons_select_own
    ON comfyui_controlnet_skeletons
    FOR SELECT
    USING (auth.uid() = user_id);

-- Policy: Users can view all public skeletons
CREATE POLICY controlnet_skeletons_select_public
    ON comfyui_controlnet_skeletons
    FOR SELECT
    USING (is_public = true);

-- Policy: Users can insert their own skeletons
CREATE POLICY controlnet_skeletons_insert_own
    ON comfyui_controlnet_skeletons
    FOR INSERT
    WITH CHECK (auth.uid() = user_id);

-- Policy: Users can update their own skeletons
CREATE POLICY controlnet_skeletons_update_own
    ON comfyui_controlnet_skeletons
    FOR UPDATE
    USING (auth.uid() = user_id);

-- Policy: Users can delete their own skeletons
CREATE POLICY controlnet_skeletons_delete_own
    ON comfyui_controlnet_skeletons
    FOR DELETE
    USING (auth.uid() = user_id);

-- Create updated_at trigger
CREATE OR REPLACE FUNCTION update_controlnet_skeletons_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trigger_controlnet_skeletons_updated_at
    BEFORE UPDATE ON comfyui_controlnet_skeletons
    FOR EACH ROW
    EXECUTE FUNCTION update_controlnet_skeletons_updated_at();

-- Add comment to table
COMMENT ON TABLE comfyui_controlnet_skeletons IS
    'Stores ControlNet skeleton images with metadata for semantic search and reuse in ComfyUI workflows';
