-- Migration 008: Fairway schema — Course/Tee/Round/HoleScore/HandicapSnapshot.
-- Greenfield migration (user confirmed no production golf data to preserve).
-- Rollback: DROP the five new tables + redeploy prior image.

BEGIN;

CREATE EXTENSION IF NOT EXISTS pg_trgm;

-- Drop old flat golf tables.
DROP TABLE IF EXISTS "GolfHoleScore" CASCADE;
DROP TABLE IF EXISTS "GolfHandicap" CASCADE;
DROP TABLE IF EXISTS "GolfRound"     CASCADE;

CREATE TABLE "Course" (
    id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name        TEXT NOT NULL,
    city        TEXT,
    state       TEXT,
    country     TEXT,
    latitude    DECIMAL(9,6),
    longitude   DECIMAL(9,6),
    holes       INTEGER NOT NULL DEFAULT 18 CHECK (holes IN (9, 18)),
    status      TEXT    NOT NULL DEFAULT 'pending' CHECK (status IN ('pending', 'verified')),
    created_at  TIMESTAMPTZ DEFAULT now()
);

CREATE INDEX idx_course_name_trgm ON "Course" USING GIN (name gin_trgm_ops);
CREATE INDEX idx_course_location  ON "Course" (latitude, longitude);

CREATE TABLE "Tee" (
    id                UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    course_id         UUID NOT NULL REFERENCES "Course"(id) ON DELETE CASCADE,
    name              TEXT NOT NULL,
    color_hex         TEXT,
    rating_18         DECIMAL(4,1),
    slope_18          INTEGER CHECK (slope_18 BETWEEN 55 AND 155),
    rating_9_front    DECIMAL(4,1),
    slope_9_front     INTEGER CHECK (slope_9_front BETWEEN 55 AND 155),
    rating_9_back     DECIMAL(4,1),
    slope_9_back      INTEGER CHECK (slope_9_back BETWEEN 55 AND 155),
    yardage           INTEGER,
    par               INTEGER,
    hole_pars         INTEGER[],
    hole_yardages     INTEGER[],
    hole_handicaps    INTEGER[],  -- per-hole stroke-allocation ranks (1..18); null -> flat NDB-10 fallback
    created_at        TIMESTAMPTZ DEFAULT now()
);

CREATE INDEX idx_tee_course_id ON "Tee" (course_id);

CREATE TABLE "Round" (
    id                   UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id              UUID NOT NULL REFERENCES "User"(id),
    course_id            UUID NOT NULL REFERENCES "Course"(id),
    tee_id               UUID REFERENCES "Tee"(id),
    played_on            DATE NOT NULL DEFAULT CURRENT_DATE,
    holes                INTEGER NOT NULL DEFAULT 18 CHECK (holes IN (9, 18)),
    scores               INTEGER[],
    total_score          INTEGER,
    front_nine           INTEGER,
    back_nine            INTEGER,
    score_differential   DECIMAL(5,1),
    scorecard_image_url  TEXT,
    ocr_raw              JSONB,
    ocr_confidence       DECIMAL(3,2),
    processing_status    TEXT DEFAULT 'pending',
    created_at           TIMESTAMPTZ DEFAULT now(),
    updated_at           TIMESTAMPTZ DEFAULT now()
);

CREATE INDEX idx_round_user_id    ON "Round" (user_id);
CREATE INDEX idx_round_played_on  ON "Round" (played_on DESC);
CREATE INDEX idx_round_course_id  ON "Round" (course_id);

CREATE TABLE "HoleScore" (
    id                    UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    round_id              UUID NOT NULL REFERENCES "Round"(id) ON DELETE CASCADE,
    hole_number           INTEGER NOT NULL CHECK (hole_number BETWEEN 1 AND 18),
    par                   INTEGER NOT NULL CHECK (par BETWEEN 3 AND 6),
    strokes               INTEGER CHECK (strokes >= 1),
    ocr_confidence        DECIMAL(3,2),
    manually_corrected    BOOLEAN DEFAULT false,
    UNIQUE (round_id, hole_number)
);

CREATE INDEX idx_hole_score_round_id ON "HoleScore" (round_id);

CREATE TABLE "HandicapSnapshot" (
    id                     UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id                UUID NOT NULL REFERENCES "User"(id),
    handicap_index         DECIMAL(4,1),
    rounds_used            INTEGER NOT NULL DEFAULT 0,
    differentials_used     JSONB,
    triggered_by_round_id  UUID REFERENCES "Round"(id) ON DELETE SET NULL,
    created_at             TIMESTAMPTZ DEFAULT now()
);

CREATE INDEX idx_handicap_snapshot_user_created
    ON "HandicapSnapshot" (user_id, created_at DESC);

COMMIT;
