-- Migration 019: Add 'Situp' to the lift_type enum.
-- Enables Situp Challenges (rep-count leaderboards, metric "reps").
--
-- IMPORTANT: ALTER TYPE ... ADD VALUE is non-transactional in PostgreSQL.
-- This migration must NOT be wrapped in BEGIN/COMMIT.

ALTER TYPE lift_type ADD VALUE IF NOT EXISTS 'Situp';
