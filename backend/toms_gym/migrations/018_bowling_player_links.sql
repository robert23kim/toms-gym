-- Migration 018: remember which profile each name on a bowling sheet saves to,
-- per uploader, so one photo saves every league-mate without re-picking.

BEGIN;

CREATE TABLE IF NOT EXISTS "BowlingPlayerLink" (
    owner_user_id UUID NOT NULL REFERENCES "User"(id) ON DELETE CASCADE,
    player_name TEXT NOT NULL,
    user_id UUID NOT NULL REFERENCES "User"(id) ON DELETE CASCADE,
    created_at TIMESTAMPTZ DEFAULT now(),
    updated_at TIMESTAMPTZ DEFAULT now(),
    PRIMARY KEY (owner_user_id, player_name)
);

COMMIT;
