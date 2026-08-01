-- Migration 016: Add 'Pushup' to the lift_type enum.
-- Enables Pushup Challenges (rep-count leaderboards, metric "reps").
--
-- IMPORTANT: ALTER TYPE ... ADD VALUE is non-transactional in PostgreSQL.
-- This migration must NOT be wrapped in BEGIN/COMMIT.

ALTER TYPE lift_type ADD VALUE IF NOT EXISTS 'Pushup';
