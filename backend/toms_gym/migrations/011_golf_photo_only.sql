-- Photo-only golf upload: a Round may exist before the user tells us the
-- course (picked on the review page). A round still cannot be CONFIRMED
-- without a course+tee — the differential needs rating/slope — so the
-- pending->ocr_complete->confirmed state machine is unchanged.
ALTER TABLE "Round" ALTER COLUMN course_id DROP NOT NULL;
