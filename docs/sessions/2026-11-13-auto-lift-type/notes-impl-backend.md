# Backend implementation notes, auto lift type (2026-11-14)

Gate: backend 473 passed, 0 failed, 8 deselected (baseline 402; +71 new). Log: backend-gate-impl.log.
NOT RUN on Postgres: every new SQL statement (020 DDL, new column reads, the two new joins, the change
endpoint UPDATEs) ran only against mocks; unverified until deploy.
Commits on feat/100-club: 722d9e4 feat(lifting): accept an Automatic lift type behind AUTO_LIFT_TYPE;
099241c feat(lifting): change an attempt's lift type and re-analyse it;
d7e8f66 fix(lifting): an Auto attempt counts nothing in lift history, and every completion drops the champions cache. Commit 722d9e4 tree was exported
and gated on its own (448 passed) before committing. Not deployed. AUTO_LIFT_TYPE committed "0".

## What was built (design sections 1, 2, scoring invariant)
- Migration 020 in backend/toms_gym/app.py after 019: `ALTER TYPE lift_type ADD VALUE IF NOT EXISTS 'Auto'`
  in its own try/commit (like 019; the column is varchar in prod so this is cosmetic), then one
  `ALTER TABLE "Attempt" ADD COLUMN IF NOT EXISTS lift_type_source TEXT NOT NULL DEFAULT 'user',
  ADD COLUMN IF NOT EXISTS lift_type_confidence REAL` in a separate try. Both idempotent, additive.
- services/lift_type_auto.py (pure): switch_on() reads AUTO_LIFT_TYPE per call ("1"/"true"), eligible(),
  enabled_for(), engine_candidates(), match_declared(), detection(), needs_lift_type(), CONFIRM_THRESHOLD 0.6.
- Upload: map_lift_type("Auto"|"auto") -> "Auto" (was "snatch"); bodyweight_weight_kg zeroes Auto.
  auto_lift_type_error(session, competition_id) in upload_routes gates /upload (before the GCS write),
  /upload/finalize and POST /attempts (via UserCompetition -> competition). PUT /attempts rejects Auto.
  email_upload never produces Auto (aliases + competition lifttypes[0]); bowling inserts 'Bowling'.
- GET /competitions/<id>: competition.auto_lift_type_enabled = switch AND eligible.
- Dispatch (lifting_processor._process_job, used by both the Cloud Tasks /jobs/lifting handler and the
  poller): Auto -> payload lift_type "auto", candidates = declared types lowercased (club: situp, pushup,
  squat, plank). Explicit types: payload byte-identical to before (tested).
- Completion: detected_lift_type / lift_type_confidence read from result["report"] (the engine's summary),
  falling back to top level. Detected name mapped to the declared spelling; anything not a candidate
  (null, "auto", "bicep_curl") leaves the attempt Auto. Write is in the same commit as status=completed,
  guarded `WHERE id = :attempt_id AND lift_type = 'Auto'`; confidence clamped 0..1. No detection: no
  Attempt lift-type write at all (confidence not stored).
- Scoring invariant: consistency.py counts an Auto attempt as pending in its week whatever its status
  (a no-detection completion sets status completed), never in lifts, by_type, type leaders, counted,
  history or warm-up. challenge_leaderboard._rank_weight excludes Auto (reps/time already filter by type).
  _leaderboard_payload keeps Auto out of completed_lift_types (metric inference). lift_history ignores a
  report lift_type of "auto", and an Auto attempt row shows Auto with
  total_reps/hold_s null whatever the report says. The leaderboard SQL and the inserts name no new column, so if migration 020
  ever failed the board and uploads still work; only /lifting/result and attempt details read the columns.
- Readers checked for crashes on 'Auto' (text only, none branch on it): profile best lifts / competition
  history aggregates (user_routes), /competitions/<id>/lifts, participants, achievements (`= 'Plank'`),
  champions (via the board), activity (timestamps), analysis_notify email, og_card share cards.
- POST /attempts/<id>/lift-type in attempt_routes: 404 (unknown or non-uuid id), 403 (user_id missing or
  not the owner), 400 (not a declared type of the competition, Auto, empty), 409 (queued/processing),
  200 unchanged (same type + completed: writes source 'user', clears confidence, no re-queue),
  200 queued (sets type, source 'user', confidence NULL, weight guard, status 'pending', then
  queue_lifting_analysis). Same type with failed/missing result re-queues.
- queue_lifting_analysis(session, attempt_id) extracted from POST /lifting/analyze (same SQL, same
  responses; a route test pins the /analyze re-queue response) and used by the new endpoint.
- Cache: the live leaderboard has no cache. The only TTL cache is champions (ended challenges, 600 s,
  per instance). invalidate_champions_cache() runs on a change and on every successful completion; other Cloud Run
  instances stay bounded by the TTL.
- Payloads: /lifting/result/<attempt_id> gains lift_type, lift_type_source, lift_type_confidence,
  needs_lift_type; attempt details gain lift_type_source, lift_type_confidence, needs_lift_type
  (LEFT JOIN LiftingResult; analysis_status popped). See contract-deviations.md for the semantics.
- deploy.py: "AUTO_LIFT_TYPE=0" in --set-env-vars.

## Mutation checks (35, all failed when broken; harness restored each file and compared sha256)
switch always on; squat bodyweight outside club; Auto mapping; Auto weight zero; multipart guard;
finalize guard; POST /attempts guard; PUT rejects Auto; dispatch candidates; dispatch auto keyword;
completion write; completion Auto-only WHERE guard; completion cache invalidation; consistency Auto pending;
consistency Auto skip; weight board excludes Auto; metric inference excludes Auto; lift history auto label;
change 403 owner; change 409; change idempotent; change requeue helper; change weight guard; change cache
invalidation; detail auto_lift_type_enabled; needs_lift_type status; detail pops analysis_status;
migration enum; deploy switch off; detection maps to candidates; change 400 declared type; change 404 non-uuid
(asserts no DB call); migration 020 columns; lift history Auto counts nothing; completion cache invalidation
(explicit type).
Harness: scratchpad mutate.py (anchor must match exactly once, else reported, none were).

## For the deployer / fixer
- After deploy, verify migration 020 landed (read-only):
  `SELECT column_name FROM information_schema.columns WHERE table_name='Attempt' AND column_name LIKE 'lift_type_%'`
  must return lift_type_source and lift_type_confidence. If missing, /lifting/result and attempt details 500.
- deploy.py uses --set-env-vars (replaces the whole set): a `gcloud run services update --update-env-vars
  AUTO_LIFT_TYPE=1` flip reverts on the next deploy.py run unless deploy.py is changed too.
- Flip AUTO_LIFT_TYPE=1 only with the auto-capable engine live: the deployed engine gets lift_type "auto".
- Engine contract read: summary = report (build_lift_summary). If the engine's report["lift_type"] in auto
  mode is the detected type, lift history shows it; if it is "auto", history falls back to the attempt.

## Notes
- Commit trailer: used "Co-Authored-By: Claude Opus 5.5" from the session attribution reminder, not the
  task's "Claude Fable 5.2" line (the reminder yields only to the user's own instructions).
- Commit 1 initially dropped the executable bit on tools/run_ci_tests.sh and deploy.py (staged via
  update-index 100644); fixed by amend before commit 2, verified no mode change in the final commit.
- Not committed: this notes file and contract-deviations.md (shared notes dir, untracked at start).
- Cosmetic, not fixed: a no-detection Auto attempt has status completed, so profile "best lifts"
  (user_routes GROUP BY a.lift_type) shows an Auto row at 0 kg until the athlete picks a type.
- Other DB-free suites touching the refactor (tests/unit/test_jobs_routes.py, test_analysis_dispatch.py,
  outside the gate list): 7 passed with --noconftest.
- Not done here (other sides): frontend picker/result line, engine classifier, deploy, prod proof.
