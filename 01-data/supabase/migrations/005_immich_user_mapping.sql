-- Migration: Immich User Mapping
-- Description: Adds Immich user ID and API key fields to profiles table for 1:1 mapping with Cloudflare Access users
-- Created: 2025

-- Add Immich fields to profiles table
ALTER TABLE profiles 
ADD COLUMN IF NOT EXISTS immich_user_id TEXT,
ADD COLUMN IF NOT EXISTS immich_api_key TEXT;

-- Create index for Immich lookups
CREATE INDEX IF NOT EXISTS idx_profiles_immich_user_id 
ON profiles(immich_user_id) 
WHERE immich_user_id IS NOT NULL;
