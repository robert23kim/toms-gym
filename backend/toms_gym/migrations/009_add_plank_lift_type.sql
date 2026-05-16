-- Migration 009: Add 'Plank' to the lift_type enum.
-- Enables Plank Challenges and plank video uploads in toms_gym.
--
-- IMPORTANT: ALTER TYPE ... ADD VALUE is non-transactional in PostgreSQL.
-- This migration must NOT be wrapped in BEGIN/COMMIT.

ALTER TYPE lift_type ADD VALUE 'Plank';
