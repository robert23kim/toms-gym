-- Database schema for Tom's Gym
-- This schema is designed to be cloud-agnostic and can be deployed to any SQL database

-- Enable UUID extension if not already enabled
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- Create enum types
CREATE TYPE user_role AS ENUM ('admin', 'user', 'judge');
CREATE TYPE user_status AS ENUM ('active', 'inactive', 'locked');
CREATE TYPE competition_status AS ENUM ('upcoming', 'in_progress', 'completed', 'cancelled');
CREATE TYPE attempt_status AS ENUM ('pending', 'completed', 'failed');
CREATE TYPE gender AS ENUM ('male', 'female', 'other');
CREATE TYPE lift_type AS ENUM ('snatch', 'clean_and_jerk');
CREATE TYPE weight_class AS ENUM ('56kg', '62kg', '69kg', '77kg', '85kg', '94kg', '105kg', 'plus_105kg');
CREATE TYPE auth_method AS ENUM ('google', 'password');

-- Create User table with enhanced authentication fields
CREATE TABLE "User" (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    username VARCHAR(255) UNIQUE,
    email VARCHAR(255) UNIQUE NOT NULL,
    name VARCHAR(255) NOT NULL,
    password_hash VARCHAR(255),
    google_id VARCHAR(255) UNIQUE,
    role user_role NOT NULL DEFAULT 'user',
    status user_status NOT NULL DEFAULT 'active',
    auth_method auth_method,
    failed_login_attempts INTEGER DEFAULT 0,
    last_login_attempt TIMESTAMP WITH TIME ZONE,
    account_locked_until TIMESTAMP WITH TIME ZONE,
    password_reset_token VARCHAR(255),
    password_reset_expiry TIMESTAMP WITH TIME ZONE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Create Competition table
CREATE TABLE IF NOT EXISTS "Competition" (
    id UUID PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    description TEXT,
    start_date TIMESTAMP WITH TIME ZONE NOT NULL,
    end_date TIMESTAMP WITH TIME ZONE NOT NULL,
    status competition_status NOT NULL DEFAULT 'upcoming',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Create UserCompetition table
CREATE TABLE IF NOT EXISTS "UserCompetition" (
    id UUID PRIMARY KEY,
    user_id UUID REFERENCES "User"(id) ON DELETE CASCADE,
    competition_id UUID REFERENCES "Competition"(id) ON DELETE CASCADE,
    weight_class weight_class NOT NULL,
    gender gender NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(user_id, competition_id)
);

-- Create Attempt table
CREATE TABLE IF NOT EXISTS "Attempt" (
    id UUID PRIMARY KEY,
    user_competition_id UUID REFERENCES "UserCompetition"(id) ON DELETE CASCADE,
    lift_type lift_type NOT NULL,
    weight_kg DECIMAL(5,2) NOT NULL,
    status attempt_status NOT NULL DEFAULT 'pending',
    video_url TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Create SecurityAudit table for tracking security events
CREATE TABLE IF NOT EXISTS "SecurityAudit" (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    event_type VARCHAR(50) NOT NULL,
    user_id UUID REFERENCES "User"(id) ON DELETE SET NULL,
    ip_address VARCHAR(45),
    user_agent TEXT,
    details JSONB,
    success BOOLEAN NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Create TokenBlacklist table for tracking revoked tokens
CREATE TABLE IF NOT EXISTS "TokenBlacklist" (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    token_id VARCHAR(255) UNIQUE NOT NULL,
    user_id UUID REFERENCES "User"(id) ON DELETE CASCADE,
    expires_at TIMESTAMP WITH TIME ZONE NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Create UserSession table for tracking active sessions
CREATE TABLE IF NOT EXISTS "UserSession" (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES "User"(id) ON DELETE CASCADE,
    refresh_token_id VARCHAR(255) UNIQUE NOT NULL,
    ip_address VARCHAR(45),
    user_agent TEXT,
    expires_at TIMESTAMP WITH TIME ZONE NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    last_activity TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Create indexes for authentication
CREATE INDEX idx_user_email ON "User"(email);
CREATE INDEX idx_user_username ON "User"(username);
CREATE INDEX idx_user_google_id ON "User"(google_id);
CREATE INDEX idx_user_status ON "User"(status);

-- Create function to update timestamps
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ language 'plpgsql';

-- Create trigger for updating timestamps
CREATE TRIGGER update_user_updated_at
    BEFORE UPDATE ON "User"
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

-- Create indexes for performance
CREATE INDEX IF NOT EXISTS idx_user_email ON "User"(email);
CREATE INDEX IF NOT EXISTS idx_user_google_id ON "User"(google_id);
CREATE INDEX IF NOT EXISTS idx_competition_status ON "Competition"(status);
CREATE INDEX IF NOT EXISTS idx_attempt_status ON "Attempt"(status);
CREATE INDEX IF NOT EXISTS idx_security_audit_event_type ON "SecurityAudit"(event_type);
CREATE INDEX IF NOT EXISTS idx_security_audit_user_id ON "SecurityAudit"(user_id);
CREATE INDEX IF NOT EXISTS idx_token_blacklist_token_id ON "TokenBlacklist"(token_id);
CREATE INDEX IF NOT EXISTS idx_user_session_user_id ON "UserSession"(user_id);
CREATE INDEX IF NOT EXISTS idx_user_session_refresh_token ON "UserSession"(refresh_token_id);

-- Create function to clean up expired sessions
CREATE OR REPLACE FUNCTION cleanup_expired_sessions()
RETURNS void AS $$
BEGIN
    DELETE FROM "UserSession" WHERE expires_at < CURRENT_TIMESTAMP;
    DELETE FROM "TokenBlacklist" WHERE expires_at < CURRENT_TIMESTAMP;
END;
$$ LANGUAGE plpgsql; 