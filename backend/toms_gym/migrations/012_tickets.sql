-- Migration 012: File-a-ticket feature (bug reports & feature requests).
--
-- Any visitor can file a ticket (no auth, email optional, user_id attached
-- when present). Tom triages by viewing the list and flipping status.

CREATE TABLE IF NOT EXISTS "Ticket" (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    type TEXT NOT NULL CHECK (type IN ('bug', 'feature')),
    title TEXT NOT NULL,
    description TEXT NOT NULL,
    page_url TEXT,
    contact_email TEXT,
    user_id UUID REFERENCES "User"(id) ON DELETE SET NULL,
    status TEXT NOT NULL DEFAULT 'open' CHECK (status IN ('open', 'in_progress', 'closed')),
    created_at TIMESTAMPTZ DEFAULT now(),
    updated_at TIMESTAMPTZ DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_ticket_status_created_at
    ON "Ticket" (status, created_at DESC);
