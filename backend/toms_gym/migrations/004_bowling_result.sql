-- Migration 004: Add Bowling support
-- Adds 'Bowling' to lift_type enum and creates BowlingResult table

-- Add Bowling to lift_type enum
ALTER TYPE lift_type ADD VALUE IF NOT EXISTS 'Bowling';

-- Create BowlingResult table
CREATE TABLE IF NOT EXISTS "BowlingResult" (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    attempt_id UUID REFERENCES "Attempt"(id) UNIQUE,
    processing_status TEXT DEFAULT 'queued',
    debug_video_url TEXT,
    trajectory_png_url TEXT,
    board_at_pins DECIMAL(5,2),
    entry_board DECIMAL(5,2),
    processing_time_s DECIMAL(8,2),
    detection_rate DECIMAL(5,2),
    error_message TEXT,
    created_at TIMESTAMPTZ DEFAULT now(),
    updated_at TIMESTAMPTZ DEFAULT now()
);

-- Index for polling queued jobs
CREATE INDEX IF NOT EXISTS idx_bowling_result_processing_status
    ON "BowlingResult" (processing_status);
