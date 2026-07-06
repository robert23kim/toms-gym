-- Migration 013: flag bot/e2e test users so they can be excluded from public
-- leaderboards and "Top Lifts This Month" (see T1, docs/plans/2026-07-06-ux-roadmap.md).
--
-- is_test defaults false. Real users (including golf guest users parsed from
-- scorecards, *@guest.tomsgym.local) stay false. Only automated bot/e2e
-- accounts get flagged. This is applied at startup via app.run_startup_migrations.

ALTER TABLE "User"
    ADD COLUMN IF NOT EXISTS is_test BOOLEAN NOT NULL DEFAULT false;

-- Backfill known bot/e2e accounts by name pattern.
-- IMPORTANT: never flag golf guest users (*@guest.tomsgym.local) — real people.
UPDATE "User"
SET is_test = true
WHERE is_test = false
  AND email NOT LIKE '%@guest.tomsgym.local'
  AND (
        name LIKE 'e2e-lift-%'
     OR name = 'T30G Upload Bot'
     OR email LIKE 'e2e-lift-%'
     OR email LIKE '%@e2e.tomsgym.local'
  );

-- Partial index: the common query path only filters on the (rare) test rows.
CREATE INDEX IF NOT EXISTS idx_user_is_test ON "User"(is_test) WHERE is_test = true;
