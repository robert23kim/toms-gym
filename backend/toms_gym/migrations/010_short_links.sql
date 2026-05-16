-- Migration 010: Short-link service for shareable URLs.
--
-- Powers the Share button on lift detail pages: clients POST a target URL,
-- the backend stores a random 6-char code, and GET /s/<code> redirects.

CREATE TABLE IF NOT EXISTS "ShortLink" (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    short_code TEXT NOT NULL UNIQUE,
    target_url TEXT NOT NULL,
    created_by_user_id UUID REFERENCES "User"(id) ON DELETE SET NULL,
    created_at TIMESTAMPTZ DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_short_link_short_code ON "ShortLink" (short_code);
