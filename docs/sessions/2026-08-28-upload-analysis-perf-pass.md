# 2026-08-28 — upload + analysis perf pass (loop iteration 1)

## Shipped
- **Backend** (`my-python-backend-00180`): `/upload/composite/sign` caches signing credentials and signs parts 8-wide; part URLs live 60 min; `/composite/complete` verifies with one `list_blobs` and deletes leftovers in a background thread. `ANALYSIS_TIMING` log line per lifting/bowling job (`services/analysis_timing.py`). Lifting engine client timeout 620→890 s.
- **Frontend** (`my-frontend-00174`): composite parts retry 3× with backoff before falling back to the serial resumable path (`withRetry` in `lib/parallelUpload.ts`).
- **Engine** (`bowling-service-00049-knc`, built from clean worktree `/tmp/pushup-engine` on `feat/pushup-config` @ thread-cap commit): `ANALYSIS_STAGES` log + `stages` in the response; rep-metric clips re-encoded/uploaded 4-wide with `-threads 2`; plank workers `grab()` skipped frames; gunicorn 870 s / Cloud Run 880 s (`--cpu-boost` kept, all env vars preserved). Rollback: `bowling-service-00047-tdf`.

## Measured
| | before | after |
|---|---|---|
| `/upload/composite/sign`, 13 parts | 0.90–1.02 s | 0.26–0.40 s |
| 10-rep pushup, clip re-encode+upload tail | ~65 s (serial) | 55.7 s (4× ffmpeg, 8 threads each) → **42.7 s** (`-threads 2`) |
| same clip, pose/analyze stage (untouched code) | ~131 s | 182–203 s |

The analyze-stage variance (131 → 203 s on identical input, code unchanged) dwarfs the clip win; the new `ANALYSIS_STAGES` lines are what will show whether that's cold instances, node CPU variance, or contention. Query: `textPayload:"ANALYSIS_TIMING"` / `"ANALYSIS_STAGES"`.

## Gotchas hit
- Another session switched branches in this shared checkout mid-commit; three commits landed on `feat/bowling-scoresheet` and a redeploy from `main` silently reverted the backend perf (measured 0.9 s again). Cherry-picked to main (5b9f2c7, 08a44af, fd05041) and redeployed. Use worktrees for parallel sessions.
- `queue_wait_s` on a re-queued attempt measures from the row's original `created_at`, so re-analyses show hours of "queue wait".
- Prod runs `ANALYSIS_DISPATCH_MODE=tasks`; the Cloud Run Jobs cutover from 2026-07-06 is only on unmerged `feat/analysis-pipeline-hardening` (no conflicts with main as of today).

## Deferred (next iterations)
1. Rep-lift pose: every frame, single process, full model (`PoseEstimator.estimate_video`) — ~65 % of a rep-lift job. Chunk-parallel like plank, behind an env flag, validated against fixtures first (OneEuro/prev-skeleton state resets at chunk edges).
2. Plank render: pipe frames to ffmpeg stdin instead of mp4v + re-encode (15–30 % of plank jobs).
3. Lower `PARALLEL_THRESHOLD` 48→32 MiB now that per-part retry exists.
4. Merge `feat/analysis-pipeline-hardening` (jobs mode, duration gate, iOS streaming compression).
