-- Migration: ComfyUI Workflow Management Tables
-- Description: Creates tables for storing ComfyUI workflow configs, execution history, and LoRA model metadata
-- Created: 2024

-- Workflow configs table
CREATE TABLE IF NOT EXISTS comfyui_workflows (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    name TEXT NOT NULL,
    description TEXT,
    workflow_json JSONB NOT NULL,
    is_public BOOLEAN DEFAULT false,
    tags TEXT[],
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Workflow execution history
CREATE TABLE IF NOT EXISTS comfyui_workflow_runs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    workflow_id UUID REFERENCES comfyui_workflows(id) ON DELETE SET NULL,
    user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    comfyui_request_id TEXT,
    status TEXT NOT NULL CHECK (status IN ('pending', 'running', 'completed', 'failed')),
    input_params JSONB,
    output_images TEXT[],
    error_message TEXT,
    started_at TIMESTAMPTZ DEFAULT NOW(),
    completed_at TIMESTAMPTZ
);

-- LoRA model metadata
CREATE TABLE IF NOT EXISTS comfyui_lora_models (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    name TEXT NOT NULL,
    filename TEXT NOT NULL,
    minio_path TEXT NOT NULL,
    file_size BIGINT,
    description TEXT,
    tags TEXT[],
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Create indexes for performance
CREATE INDEX IF NOT EXISTS idx_comfyui_workflows_user_id ON comfyui_workflows(user_id);
CREATE INDEX IF NOT EXISTS idx_comfyui_workflows_is_public ON comfyui_workflows(is_public);
CREATE INDEX IF NOT EXISTS idx_comfyui_workflows_created_at ON comfyui_workflows(created_at DESC);

CREATE INDEX IF NOT EXISTS idx_comfyui_workflow_runs_user_id ON comfyui_workflow_runs(user_id);
CREATE INDEX IF NOT EXISTS idx_comfyui_workflow_runs_workflow_id ON comfyui_workflow_runs(workflow_id);
CREATE INDEX IF NOT EXISTS idx_comfyui_workflow_runs_status ON comfyui_workflow_runs(status);
CREATE INDEX IF NOT EXISTS idx_comfyui_workflow_runs_started_at ON comfyui_workflow_runs(started_at DESC);

CREATE INDEX IF NOT EXISTS idx_comfyui_lora_models_user_id ON comfyui_lora_models(user_id);
CREATE INDEX IF NOT EXISTS idx_comfyui_lora_models_filename ON comfyui_lora_models(filename);

-- Enable Row Level Security
ALTER TABLE comfyui_workflows ENABLE ROW LEVEL SECURITY;
ALTER TABLE comfyui_workflow_runs ENABLE ROW LEVEL SECURITY;
ALTER TABLE comfyui_lora_models ENABLE ROW LEVEL SECURITY;

-- RLS Policies for comfyui_workflows
-- Users can see their own workflows or public ones
CREATE POLICY "Users see own workflows"
    ON comfyui_workflows FOR SELECT
    USING (auth.uid() = user_id OR is_public = true);

-- Users can create workflows for themselves
CREATE POLICY "Users create own workflows"
    ON comfyui_workflows FOR INSERT
    WITH CHECK (auth.uid() = user_id);

-- Users can update their own workflows
CREATE POLICY "Users update own workflows"
    ON comfyui_workflows FOR UPDATE
    USING (auth.uid() = user_id)
    WITH CHECK (auth.uid() = user_id);

-- Users can delete their own workflows
CREATE POLICY "Users delete own workflows"
    ON comfyui_workflows FOR DELETE
    USING (auth.uid() = user_id);

-- RLS Policies for comfyui_workflow_runs
-- Users can see their own workflow runs
CREATE POLICY "Users see own workflow runs"
    ON comfyui_workflow_runs FOR SELECT
    USING (auth.uid() = user_id);

-- Users can create workflow runs for themselves
CREATE POLICY "Users create own workflow runs"
    ON comfyui_workflow_runs FOR INSERT
    WITH CHECK (auth.uid() = user_id);

-- Users can update their own workflow runs
CREATE POLICY "Users update own workflow runs"
    ON comfyui_workflow_runs FOR UPDATE
    USING (auth.uid() = user_id)
    WITH CHECK (auth.uid() = user_id);

-- RLS Policies for comfyui_lora_models
-- Users can see their own LoRA models
CREATE POLICY "Users see own lora models"
    ON comfyui_lora_models FOR SELECT
    USING (auth.uid() = user_id);

-- Users can create LoRA models for themselves
CREATE POLICY "Users create own lora models"
    ON comfyui_lora_models FOR INSERT
    WITH CHECK (auth.uid() = user_id);

-- Users can update their own LoRA models
CREATE POLICY "Users update own lora models"
    ON comfyui_lora_models FOR UPDATE
    USING (auth.uid() = user_id)
    WITH CHECK (auth.uid() = user_id);

-- Users can delete their own LoRA models
CREATE POLICY "Users delete own lora models"
    ON comfyui_lora_models FOR DELETE
    USING (auth.uid() = user_id);

-- Function to update updated_at timestamp
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ language 'plpgsql';

-- Trigger to automatically update updated_at
CREATE TRIGGER update_comfyui_workflows_updated_at
    BEFORE UPDATE ON comfyui_workflows
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();
