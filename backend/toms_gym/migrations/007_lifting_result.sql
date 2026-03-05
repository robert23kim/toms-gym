-- Migration 007: Add Lifting analysis support

CREATE TABLE IF NOT EXISTS "LiftingResult" (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    attempt_id UUID REFERENCES "Attempt"(id) ON DELETE CASCADE UNIQUE,
    processing_status TEXT NOT NULL DEFAULT 'queued',
    annotated_video_url TEXT,
    summary_url TEXT,
    report JSONB,
    processing_time_s DECIMAL(8,2),
    error_message TEXT,
    created_at TIMESTAMPTZ DEFAULT now(),
    updated_at TIMESTAMPTZ DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_lifting_result_processing_status
    ON "LiftingResult" (processing_status);
