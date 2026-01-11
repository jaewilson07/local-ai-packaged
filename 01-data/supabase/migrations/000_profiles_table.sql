-- Migration: User Profiles Table
-- Description: Creates the profiles table for user authentication and management
-- Created: 2024
-- This table stores user profile information including email, role, and tier
-- Used by the Lambda API authentication system

-- Create profiles table
CREATE TABLE IF NOT EXISTS profiles (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    email TEXT UNIQUE NOT NULL,
    role TEXT NOT NULL DEFAULT 'user',
    tier TEXT NOT NULL DEFAULT 'free',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Create index on email for fast lookups
CREATE INDEX IF NOT EXISTS idx_profiles_email ON profiles(email);

-- Create index on role for admin queries
CREATE INDEX IF NOT EXISTS idx_profiles_role ON profiles(role);

-- Create index on tier for tier-based queries
CREATE INDEX IF NOT EXISTS idx_profiles_tier ON profiles(tier);

-- Function to update updated_at timestamp
CREATE OR REPLACE FUNCTION update_profiles_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ language 'plpgsql';

-- Trigger to automatically update updated_at
CREATE TRIGGER update_profiles_updated_at
    BEFORE UPDATE ON profiles
    FOR EACH ROW
    EXECUTE FUNCTION update_profiles_updated_at();

-- Add comment to table
COMMENT ON TABLE profiles IS 'User profiles for authentication and authorization';
COMMENT ON COLUMN profiles.id IS 'Unique user identifier (UUID)';
COMMENT ON COLUMN profiles.email IS 'User email address (unique)';
COMMENT ON COLUMN profiles.role IS 'User role: user or admin';
COMMENT ON COLUMN profiles.tier IS 'User tier: free or pro';
COMMENT ON COLUMN profiles.created_at IS 'Timestamp when user was created';
COMMENT ON COLUMN profiles.updated_at IS 'Timestamp when user was last updated';
