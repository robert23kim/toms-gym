-- Migration 015: chosen avatar on User (challenge champions feature,
-- docs/superpowers/specs/2026-08-01-challenge-champions-design.md).
--
-- Stores a catalog key from services/achievements.py AVATAR_CATALOG (not a
-- URL) — resolution to a DiceBear URL happens server-side, so the catalog can
-- move without touching stored rows. Applied at startup via
-- app.run_startup_migrations (startup-migration pattern, like 013/014).

ALTER TABLE "User" ADD COLUMN IF NOT EXISTS avatar TEXT;
