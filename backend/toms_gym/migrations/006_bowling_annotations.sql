-- Add annotation storage and frame extraction metadata to BowlingResult
ALTER TABLE "BowlingResult"
    ADD COLUMN IF NOT EXISTS annotation JSONB,
    ADD COLUMN IF NOT EXISTS frames_url TEXT;
