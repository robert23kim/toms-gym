-- Migration 005: Add lane edge correction support to BowlingResult
-- Adds columns for auto-detected edges, manual corrections, and frame URL

ALTER TABLE "BowlingResult"
    ADD COLUMN IF NOT EXISTS lane_edges_auto JSONB,
    ADD COLUMN IF NOT EXISTS lane_edges_manual JSONB,
    ADD COLUMN IF NOT EXISTS frame_url TEXT;
