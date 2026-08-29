-- Migration 017: Bowling score sheets (photographed RESULTS / lane screens).
--
-- One BowlingScoreSheet per photo, one BowlingGame per (player, game). Games
-- stay unclaimed (user_id NULL) until the uploader picks their row on the
-- review page — league-mates are stored by name only and are never ranked.

BEGIN;

CREATE TABLE IF NOT EXISTS "BowlingScoreSheet" (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES "User"(id) ON DELETE CASCADE,
    sheet_type TEXT NOT NULL CHECK (sheet_type IN ('night', 'game')),
    played_on DATE NOT NULL,
    image_url TEXT NOT NULL,
    parser TEXT,
    raw_parse JSONB,
    processing_status TEXT NOT NULL DEFAULT 'parsed'
        CHECK (processing_status IN ('parsed', 'failed', 'confirmed')),
    error_message TEXT,
    team_name TEXT,
    created_at TIMESTAMPTZ DEFAULT now(),
    updated_at TIMESTAMPTZ DEFAULT now()
);

CREATE TABLE IF NOT EXISTS "BowlingGame" (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    sheet_id UUID NOT NULL REFERENCES "BowlingScoreSheet"(id) ON DELETE CASCADE,
    user_id UUID REFERENCES "User"(id) ON DELETE SET NULL,
    player_name TEXT NOT NULL,
    game_number INT NOT NULL,
    total_score INT,
    hdcp INT,
    frames JSONB,
    computed_total INT,
    flagged BOOLEAN NOT NULL DEFAULT false,
    flag_reason TEXT,
    confidence REAL,
    played_on DATE NOT NULL,
    created_at TIMESTAMPTZ DEFAULT now(),
    UNIQUE (sheet_id, player_name, game_number)
);

CREATE INDEX IF NOT EXISTS idx_bowlinggame_user
    ON "BowlingGame" (user_id, played_on DESC);
CREATE INDEX IF NOT EXISTS idx_bowlingscoresheet_user
    ON "BowlingScoreSheet" (user_id, played_on DESC);

COMMIT;
