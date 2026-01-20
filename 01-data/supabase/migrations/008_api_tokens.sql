-- Migration: API Tokens for Automation Authentication
-- Description: Adds API token support for headless automation (scripts, n8n, webhooks)
-- Created: 2026-01-20

-- Personal API token in profiles (simple single-token approach)
-- This is the primary method - one token per user for automation
ALTER TABLE profiles ADD COLUMN IF NOT EXISTS api_token_hash TEXT;
ALTER TABLE profiles ADD COLUMN IF NOT EXISTS api_token_created_at TIMESTAMPTZ;

-- Create index for fast token lookup
CREATE INDEX IF NOT EXISTS idx_profiles_api_token_hash ON profiles(api_token_hash) WHERE api_token_hash IS NOT NULL;

-- Optional: Multiple tokens table for advanced use cases
-- Allows users to have multiple named tokens with different scopes/expiration
CREATE TABLE IF NOT EXISTS api_tokens (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES profiles(id) ON DELETE CASCADE,
    name TEXT NOT NULL,
    token_hash TEXT NOT NULL,  -- Store hashed, not plaintext
    scopes TEXT[] DEFAULT '{}',
    expires_at TIMESTAMPTZ,
    last_used_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    CONSTRAINT unique_user_token_name UNIQUE (user_id, name)
);

-- Create indexes for api_tokens table
CREATE INDEX IF NOT EXISTS idx_api_tokens_user_id ON api_tokens(user_id);
CREATE INDEX IF NOT EXISTS idx_api_tokens_token_hash ON api_tokens(token_hash);
CREATE INDEX IF NOT EXISTS idx_api_tokens_expires_at ON api_tokens(expires_at) WHERE expires_at IS NOT NULL;

-- Enable Row Level Security on api_tokens
ALTER TABLE api_tokens ENABLE ROW LEVEL SECURITY;

-- RLS Policies for api_tokens
-- Users can only see their own tokens
CREATE POLICY "Users see own tokens"
    ON api_tokens FOR SELECT
    USING (user_id IN (SELECT id FROM profiles WHERE email = current_user));

-- Users can create tokens for themselves
CREATE POLICY "Users create own tokens"
    ON api_tokens FOR INSERT
    WITH CHECK (user_id IN (SELECT id FROM profiles WHERE email = current_user));

-- Users can delete their own tokens
CREATE POLICY "Users delete own tokens"
    ON api_tokens FOR DELETE
    USING (user_id IN (SELECT id FROM profiles WHERE email = current_user));

-- Function to update last_used_at on token use
CREATE OR REPLACE FUNCTION update_token_last_used()
RETURNS TRIGGER AS $$
BEGIN
    -- This would be called from application code, not a trigger
    -- Keeping as reference for the pattern
    NEW.last_used_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Add comment for documentation
COMMENT ON TABLE api_tokens IS 'API tokens for automation authentication. Tokens are stored hashed (SHA-256). Supports multiple named tokens per user with optional scopes and expiration.';
COMMENT ON COLUMN profiles.api_token_hash IS 'Primary API token hash (SHA-256) for simple single-token automation. Use api_tokens table for multiple tokens.';
COMMENT ON COLUMN profiles.api_token_created_at IS 'Timestamp when the primary API token was created/regenerated.';
