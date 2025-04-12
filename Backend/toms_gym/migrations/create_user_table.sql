-- Create User table
CREATE TABLE IF NOT EXISTS "User" (
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

-- Create index for faster email lookup
CREATE INDEX IF NOT EXISTS idx_user_email ON "User"(email);

-- Create index for faster google_id lookup
CREATE INDEX IF NOT EXISTS idx_user_google_id ON "User"(google_id);

-- Create index for username lookup
CREATE INDEX IF NOT EXISTS idx_user_username ON "User"(username);

-- Create index for status lookup
CREATE INDEX IF NOT EXISTS idx_user_status ON "User"(status);

-- Create trigger for updating timestamps
CREATE TRIGGER IF NOT EXISTS update_user_updated_at
    BEFORE UPDATE ON "User"
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column(); 