# Situp upload debug, pose tracking and set stats — 2026-09-13

## What this was
Tom uploaded the first real situp video (attempt `8211b5b2-5050-4364-9baf-94c71ac4fa21`, 101 s,
side-on, challenge `95b60b42-9220-4195-a659-b1d362093ea1`) and asked to verify it parsed. It had
not; this became a loop through three fixes: analysis OOM + rep counting, a jumping skeleton on the
annotated video, and pushup-style set data for situps.

## What changed
Engine — branch `feat/situp-config` in worktree `~/code/bowling-app/situp-engine` (unmerged,
unpushed, built on unmerged `feat/pushup-config`):
- `047b841` fix(lifting): metric clips stream rep by rep instead of buffering every frame between
  first and last rep (8.3 GB on this video → OOM-killed on all three Cloud Tasks retries).
- `05267b1` fix(situp): reps counted from the ear-hip-knee trunk lift (`compute_trunk_lift_angle`),
  mirrored-pose frames masked, `min_prominence_deg` 10, edge reps trimmed, ROM band 125/105.
  Decision by Tom: crunch-depth reps count.
- `553e881` feat(lifting): `pose/tracking.py` — whole-video nearest-body tracking + 0.37 s two-way
  Savitzky-Golay, behind `EXERCISE_CONFIGS[...]["pose_tracking"]` (situp only).
- `ba52024` feat(situp): metric rows `rom, control, hips_planted, feet_planted, tempo`; hips planted
  replaces body sway in situp form; every rep row carries `start_s/peak_s/end_s`.
- `13b49b5` fix(situp): annotated video no longer shows "Elbow drift" alerts or "Elbow: x-y deg"
  on situps (`signal_label` → "Trunk lift").
- Deployed revisions in order: `bowling-service-00051-k5f` → `00052-t58` → **`00053-fxm`** (live,
  image `gcr.io/toms-gym/bowling-service:situp-13b49b5`). Rollback `00052-t58`. Env vars, 8Gi and
  880 s timeout confirmed carried over each time.

Frontend — toms_gym `main` (unpushed), built by `doer-1` in a worktree then fast-forwarded:
- `63cacbb`, `d3c1555`, `d337e8f`, `6afe1e2`, `ad9f8f1`, `ad39bc7` — situp coaching keys/copy for
  Hips Planted / Feet Planted, `lib/setPace.ts`, `components/lifting/SetStats.tsx` under the Set
  Breakdown for pushup + situp (pace, clean streak, slowest/fastest rep, Start/Middle/End thirds).
- Deployed `my-frontend-00190-rtk` → **`my-frontend-00191-fvz`** (live).

Prod result for the attempt after final re-analysis: 68 reps, 65 clean, board 66.5, grade B, rank 1
(first successful run was 67 reps / 43 clean / board 55).

## What we learned
- MediaPipe on a lying body: the estimator's upright-lifter selector picked a mirrored ghost on
  232/3022 frames although the real body was a candidate on 195 of them; its OneEuro filter
  (`beta=0.5` on pixels) passed ~14 px/frame of jitter. Tracking + offline smoothing: 272 → 120 bad
  frames (77 unavoidable), knee jitter 14 → 5 px/frame, same rep tops.
- The old situp hip-angle signal moved ~10° on a crunch; the 26 reps originally reported were
  mirrored-pose glitches. Mask glitches by head/knee order, not angle magnitude (a magnitude
  despike that fixes crunches erases full-situp peaks).
- `score_body_sway` normalises by the torso length of the first 10 frames (athlete walking to the
  camera) and failed 67/68 still reps; per-rep travel scores need a noise floor measured on real
  footage (hips ~10-18 % of torso, feet ~9-15 % of shin).
- Neck pull is unmeasurable on this camera angle (head curl is most of a crunch, 37° median).
- Reps are segmented peak to peak, so any "pause between reps" is always 0 s.
- Local macOS MediaPipe vs prod Linux shifts borderline form scores (49 vs 43 clean on the
  pre-tracking engine), not rep counts.

## Still broken / next steps
- **Merge `feat/pushup-config` and `feat/situp-config`** (engine) and push; the next engine deploy
  from any other branch drops both configs. `feat/sam-lane-calibration` (another session) branches
  from `05267b1`, so it lacks the tracking/set-metric commits.
- **Push toms_gym `main`** (21 unpushed commits at session end).
- Tempo still uses the curl 1.5-2.5:1 target and fails 66/68 crunch reps; it is the top tip on the
  page. Needs a situp-specific target or removal.
- Pushups are also lying but still use the old pose selector; Set Stats only appears on pushups
  after re-analysis. Enabling `pose_tracking` for pushup would re-baseline their grades — decide first.
- No real full-depth situp footage; only synthetic full situps are validated.
- Situp attempt stored `weight 60` (bodyweight lift) — upload path should post 0.
- `AttemptHistory` rows still show raw `total_reps`, not board score.

## Verification
- Engine: lifting suite + `test_lift_summary.py` 230 passed, 2 skipped at `13b49b5`. The full suite
  was last run before `13b49b5`: failures matched base `d4d8bb2` (10 pre-existing bowling/benchmark)
  plus one new `test_lift_summary` failure, fixed and re-run in isolation — full suite not re-run.
  New guards (clip memory, real-footage rep tops, mirrored masking, edge trim, tracking selector,
  smoothing, situp metric rows, rep timing, hips/feet planted thresholds, situp alerts, overlay
  label) were each mutation-checked and seen to fail.
- Frontend: full jest 87 suites / 593 passed / 0 failed. `tsc -p tsconfig.app.json` has 43
  pre-existing errors, none in touched files (checked by `doer-1`); no lint script exists.
- Production: re-queued analysis via `POST /lifting/analyze/<attempt>` after each engine deploy;
  confirmed `completed` (no "Memory limit" logs checked on `00051`/`00052`; `00053` not checked), leaderboard row
  (score 66.5, 65 clean of 68), annotated video stills at 41.89/43.2/45.88/61.4 s (skeleton on the
  body, "Trunk lift" label, no elbow banner), and the result page at 390×844 via Playwright
  (Set Breakdown 5 rows, Set Stats card, no console errors, no horizontal overflow).
- Not verified: behaviour on any other user's situp or on a real pushup re-analysis.
