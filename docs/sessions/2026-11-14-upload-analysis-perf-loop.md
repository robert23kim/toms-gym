# Upload and analysis perf loop — 2026-11-14

## What this was
Tom asked for a dynamic workflow to measure upload and analysis times, run experiments, and implement and deploy any cheap or moderate wins, without colliding with the other Claude session (`toms-gym-f8`) deploying from the same checkout. Ran 2026-11-13 to 2026-11-14.

## What changed
- **Engine, live:** `bowling-service-00054-zj5` (100%, latest) built from the unmerged engine branch `perf/engine-2026-11-13` `f198bac` (worktree `~/code/bowling-app/perf-engine`, off `feat/situp-config` `93378b0`), image `gcr.io/toms-gym/bowling-service@sha256:42f105ddd88c070a6a92e52ac2eb290a1a0b9f8783987e7615c86bf8af596e11`.
  - `LIFT_POSE_WORKERS=4`: chunked parallel MediaPipe pose (`src/lifting/pose/parallel.py`).
  - `SKIP_METRIC_CLIPS_FOR=pushup,situp`: skips metric clips that the frontend never shows.
  - `LIFT_VIDEO_ENCODER=ffmpeg`: one libx264 encode instead of write-then-re-encode.
  - All three default off in code; unset = old path.
- **Frontend, live:** `my-frontend-00208-pgq`. Upload timing telemetry (`frontend/src/lib/uploadTiming.ts`, logged as `FRONTEND_ERROR action=upload-timing`) and removal of the realtime MediaRecorder compression fallback. Commits `4af22d5`, `962dd5b`, `c03c28b` on `feat/100-club`.
- **Backend:** not redeployed (`my-python-backend-00198-8kd`, `AUTO_LIFT_TYPE=0`).
- **APK** rebuilt and published: `apk/tomsgym-debug-20261114-030647.apk`, link `https://my-python-backend-quyiiugyoq-ue.a.run.app/s/mwZr9n` (expires ~2026-11-21).
- **Docs:** `docs/perf/2026-11-14-engine-perf-deploy.md` (live state, numbers, rollback), notes and harness in `docs/sessions/2026-11-13-perf-loop/`, engine line in `CLAUDE.md`. `feat/100-club` at `8f9deec` before this file.
- **Rejected:** cheaper inference (`num_poses`, frame stride, smaller input) changed rep counts on nearly every clip.
- **Cleaned up:** throwaway service `bowling-service-perf` and all `perf-bench-*` objects deleted.

### Numbers
| | Before | After |
|---|---|---|
| 8 real clips summed, Cloud Run | 953 s | 311 s |
| Pushup | 90–146 s | 25–32 s |
| Situp | 153–227 s | 45–63 s |
| Squat | 44 s | 17–23 s |
| Plank | unchanged | unchanged |

Upload: 28 real uploads, median 6.7 s, bound by the PUT and the phone's link. No speedup found; only telemetry shipped.

### Rollback
`gcloud run services update bowling-service --region=us-east1 --project=toms-gym --remove-env-vars LIFT_POSE_WORKERS,SKIP_METRIC_CLIPS_FOR,LIFT_VIDEO_ENCODER`, or route traffic to `bowling-service-00053-fxm`.

## What we learned
- **Cloud Run instance types score the same image and video differently.** 5 of 8 clips differ between two host classes (25 vs 26 reps on one pushup clip; a rep flipping clean/sloppy). Pre-existing, not caused by this change. Equivalence checks must compare runs on the same class.
- **Never benchmark on `--no-traffic` tagged revisions of `bowling-service`.** It pins traffic to a named revision and breaks another session's `services update --image`. Clone the service instead (`gcloud beta run deploy` from the exported spec).
- A parallel pose chunk is only safe to adopt after it matches the sequential stream bit-for-bit on 5 consecutive frames; tracked pose is stateful.
- `npx tsc --noEmit` checks nothing in `frontend/` (root tsconfig has `files: []`). Use `npx tsc -p tsconfig.app.json --noEmit` (43 pre-existing errors).
- Peer coordination that worked: message up front, own worktrees, hold the engine deploy until the peer reported its outcome, ff-merge only after it finished.

## Still broken / next steps
1. **Decision needed: instance-type scoring variance.** Pin the service to one CPU platform, or accept that a rep can differ by host. No ticket filed.
2. **Engine branches `feat/auto-lift-type` (`a52612e`) and `fix/squat-rep-count` (`73852de`) must rebase onto `perf/engine-2026-11-13` before deploying**, or they silently revert the speedup. Dry merge conflicts in `src/lifting/pose/estimator.py` and `tests/test_service_app.py`.
3. **No real phone upload has gone through backend → new engine yet.** Read the next `ANALYSIS_TIMING` line; expect `engine_clips_s` and `engine_reencode_s` = 0 for pushup/situp.
4. **No real `upload-timing` event seen yet**, only a synthetic one. Read the first real one to see where upload time goes on phones.
5. Annotated video from the ffmpeg encoder was played in desktop Chrome only, not on a phone or in the APK.
6. No 1080p, portrait or multi-person clip was run on Cloud Run with the flags on.
7. `perf/engine-2026-11-13` and `feat/situp-config` are unmerged; `toms_gym` has no upstream, so every commit here is laptop-only.
8. Fixtures in `~/code/bowling-app/perf-fixtures-2026-11-13` are real users' videos: never commit; delete when no longer needed. Experiment worktrees `~/code/bowling-app/perf-exp-*` and `~/code/toms_gym-perf` can be removed.

## Verification
- **Live state re-read 2026-11-14 at save time (gcloud):** engine `00054-zj5`, frontend `00208-pgq`, backend `00198-8kd`, each 100% on latest; the three engine env flags present; no `perf` service left.
- **Engine equivalence:** 8 real 100 Club clips on a cloned Cloud Run service, gated by `harness/compare.py` (rep count, clean/sloppy split, score drift < 2, plank hold ± 0.5 s), plus an adversarial verify pass (`docs/sessions/2026-11-13-perf-loop/verify-engine.md`).
- **Live revision:** direct engine calls on `00054-zj5` — squat 24.7 s, pushup 18.6 s, situp 52.4 s, plank 35.5 s, outputs matching the verified candidate; annotated video (h264 yuv420p 480x360) played in Chrome. Proof in `docs/sessions/2026-11-13-perf-loop/deploy-proof/`.
- **Frontend:** jest 950/950 on the rebased tree; prod pages loaded in Chrome with no console errors; synthetic `upload-timing` event found in prod logs.
- **Not run:** backend CI suite and Android emulator smoke test on the merged tree; anything in items 3–6 above.
