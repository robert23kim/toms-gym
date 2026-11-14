# Automatic lift type

Design: `docs/plans/2026-11-13-auto-lift-type.md`. Session: `docs/sessions/2026-11-13-auto-lift-type.md`. Backend and frontend deployed 2026-11-14 with the **switch off** (`AUTO_LIFT_TYPE=0`), so nothing here is visible to athletes yet; the auto-capable engine went live the same day (see Engine).

## What it does
An athlete on an all-bodyweight board with 2+ lift types picks "Automatic" (first option, default) and posts `lift_type: Auto`, weight 0. The engine classifies the clip, the backend writes the detected type, and the result page says "Counted as X · Automatic". Below 0.6 confidence it asks "Is this a X?" with Yes / Change. The owner can Change the type, which re-queues analysis.

## The switch
- Env `AUTO_LIFT_TYPE`, read per call, default off. `deploy.py` commits `AUTO_LIFT_TYPE=0` as a non-secret env var.
- `GET /competitions/<id>` returns `competition.auto_lift_type_enabled` = switch AND eligible (all bodyweight, 2+ types). The frontend shows Automatic only when it is exactly `true`.
- With the switch off every insert site (`/upload`, `/upload/finalize`, `POST /attempts`, `/submit_attempt`) answers 400 to `Auto`, and `POST /attempts/<id>/lift-type` also answers 400 (so Change and re-analyse are off too; the 403 owner check is unreachable until it is on).
- Flip: `gcloud run services update my-python-backend --region=us-east1 --update-env-vars AUTO_LIFT_TYPE=1`, and change the value in `deploy.py` so the next deploy does not revert it. The auto-capable engine is live since 2026-11-14 (`bowling-service-00057-qag`); any earlier revision treats `auto` as bicep curl, so set the switch back to 0 before rolling the engine back.

## Backend
- Migration 020 (inline in `app.py`): `ALTER TYPE lift_type ADD VALUE IF NOT EXISTS 'Auto'`, `Attempt.lift_type_source TEXT NOT NULL DEFAULT 'user'`, `Attempt.lift_type_confidence REAL`. Checks `information_schema` first and takes `SET LOCAL lock_timeout 5s`; if the first-boot ALTER times out the instance 500s on result endpoints until a later boot lands it. Check both columns exist after deploy.
- Dispatch (`lifting_processor._process_job`, shared by Cloud Tasks and the poller): for Auto sends `lift_type: "auto"` plus `candidates` (the competition's types, lowercase). Explicit-type payload is byte-identical to before. The DB lock is released before the engine call.
- Completion: reads `detected_lift_type` / `lift_type_confidence` from `result['report']` (top-level fallback), writes the declared spelling with source `auto`, guarded `WHERE lift_type = 'Auto'`, same transaction as `status=completed`. No detection leaves it Auto (`needs_lift_type` true).
- Scoring invariant (`consistency.py`): an Auto attempt is pending whatever its status; never counts in lifts, by_type, leaders, history or warm-up; `_rank_weight` excludes it; profile best lifts exclude it.
- `POST /attempts/<id>/lift-type {lift_type, user_id}`: 404 unknown, 400 switch off / ineligible board / not a declared type / Auto, 403 not owner, 409 analysis queued or processing, 200 `unchanged` (same type, completed: source `user`, no re-queue) or 200 `queued` (re-queues via `queue_lifting_analysis`, extracted from `/lifting/analyze`).
- `/lifting/result/<id>` and attempt detail gain `lift_type_source`, `lift_type_confidence`, `needs_lift_type`.
- Champions TTL cache is dropped on a type change and on completion, per instance (600 s bound elsewhere).

## Frontend
- Automatic in `ChallengeDetail` and `UploadVideo` (`data-testid=lift-type-automatic`). `LiftTypeLine` on `AnalysisStatus` and `VideoPlayer`: Automatic / manual / confirm / unknown states; Change is owner-only and opens a sheet of the board's types; Re-analyze is disabled until the pick differs. Both pages read the flag from the competition fetch.
- `lib/identity.ts` (`getUserId`, `getEmail`, `remember`, `forget`, `restoreIdentity`) is the only place that touches the `userId`/`userEmail` keys. `remember` of a different id drops the old email. Email inputs are pre-filled and editable across upload, find-profile, sign-in, feedback, golf and bowling forms.
- Native mirror: `@capacitor/preferences` 7.0.4, native-only, every call in try/catch, restore gives up after 1.5 s; `main.tsx` renders after `restoreIdentity()`. Forget Me clears both stores. Phones now get Forget Me on their own profile.

## Engine
**Deployed 2026-11-14**: `bowling-service-00057-qag`, image `gcr.io/toms-gym/bowling-service:auto-7e0169c` (digest `sha256:919848fb…a251`), branch `feat/auto-lift-type-perf` at `7e0169c` (worktree `~/code/bowling-app/auto-perf-engine`), which is `feat/auto-lift-type` rebased onto `perf/engine-2026-11-13` `f198bac` plus the rep-count guard, and is now the engine repo's `main`. The three perf env flags carried over. Rollback: route traffic to `bowling-service-00054-zj5`. The backend switch is still `AUTO_LIFT_TYPE=0`.

`POST /analyze-lift` takes `lift_type: "auto"` + `candidates`; only situp, pushup, squat, plank are classified. Auto adds `detected_lift_type`, `lift_type_confidence`, `lift_type_scores` to the report. No detection: HTTP 200, `annotated_video_url` null, detected null, confidence 0. `auto` without candidates: 400. Details and wire clarifications: `docs/sessions/2026-11-13-auto-lift-type/contract-deviations.md`.

**Rep-count guard** (`rep_count_contradicts`): for a rep lift the engine counts reps before rendering; if the count is more than 2.5x the busiest joint's cycle count and at least 5 above it, it returns the no-detection report plus `lift_type_rejected: {lift_type, reps, cycles}`. The attempt stays `Auto` (pending, never scored) and the app asks. Lowering the confidence would not have been enough: a sub-0.6 guess still carries the detected type and scores.

Eval (51 labelled clips, rule-based, rules frozen before the held-out half): overall 48/51 = 94.1%; held-out 29/32 = 90.6%; per type situp 10/11, pushup 16/17, squat 1/1, plank 21/22. **Squat rests on one clip.** Misses: a plank filmed from the feet read pushup at 1.00 (162 reps against 38 cycles), now dropped by the guard, so it asks; a crunch-depth situp with no detection (asks); **knee pushups from the front quarter read plank at 0.91, still silent**: a plank has no rep count to compare. The guard fires on that one clip only (widest gap on a correct clip is 39 against 21); its threshold was chosen knowing that clip, which is its only positive example.

Proof on Cloud Run 2026-11-14 (no-traffic tag, then the live URL; throwaway `auto-proof-*` attempt ids): explicit squat/pushup/situp/plank reports equal the `00054` deploy proof apart from clip URLs; the plank from the feet returns no detection with `lift_type_rejected` (164 against 40 on Linux pose); the 10 s plank fixture reads plank at 0.556 (asks).

**Auto is slower than an explicit type**: its pose pass may stop early for a plank, so it runs on one worker and does not use `LIFT_POSE_WORKERS`. Cloud Run, same clip, explicit vs auto: pushup 23 s vs 60 s, squat 19 s vs 40 s, plank (82 s hold) 40 s vs 60 s; a misread 141 s plank took 231 s. Follow-up: let the candidates pass use the parallel workers once the clip is known not to be a hold.

## Tests
`tests/test_lift_type_auto.py` (DB-free) and `tests/test_lift_type_auto_pg.py` (7 tests, skipped unless `AUTO_LIFT_PG_URL` points at a throwaway local Postgres; refuses ports 5432/5433 and a database named `postgres`), both in `tools/run_ci_tests.sh`. Frontend: `lib/identity` tests, page tests for the line and sheet, `main.test.tsx`, `emailPrefill.test.tsx`.

## Open follow-ups
- Flip the switch (Tom's call), then run one real automatic upload and one re-analysis with a test account (the backend path was never exercised in prod; only direct engine calls were).
- Knee pushups read as a plank stay silent; auto does not use the parallel pose workers.
- New SQL was proven on a throwaway Postgres, not prod beyond the migration columns.
- Install the new APK on a real phone (emulator only).
- Reword "Is this a pushup?" is Tom's call. Pre-existing: `/profile` overflows at 390 with a long email handle; `/challenges/<id>/upload` submit sits under the tab bar at 390.
