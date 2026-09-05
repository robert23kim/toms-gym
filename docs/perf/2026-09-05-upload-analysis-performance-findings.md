# Upload + analysis performance findings — 2026-09-05

Follow-up to the 2026-08-28/29 perf pass (`docs/sessions/2026-08-29-upload-analysis-perf-loop.md`).
Method: two read-only code reviews (engine repo `~/code/bowling-app/analysis-engine`, deployed branch
`feat/pushup-config`; this repo's upload → Cloud Tasks → `/jobs/*` → engine → result path) cross-checked
against production logs, Cloud Run service configs and the Cloud Tasks queue. Claims marked **verified**
were re-read in code or logs by the lead; the rest are the reviewers' estimates.

## Data caveats (read first)

- **No real user analysis has run since 2026-08-29.** The only `ANALYSIS_TIMING` / `ANALYSIS_STAGES`
  samples in the 30-day log window are two re-analyses of the same pushup attempt (`53bd97fa`). Every
  number below is from those two runs or from code. Log retention is 30 days; older history is gone.
- Every engine request in that window started a fresh instance (`bowling-service` has no min-instances),
  so the numbers include a cold start. Measured from logs, that cold start is small (see F5).
- The `queue_wait_s` field is wrong for re-queued jobs (F9), so queue pressure cannot be read from it yet.

## Measured baseline (production, pushup, 10 reps)

| stage | run A (s) | run B (s) |
|---|---|---|
| engine download | 0.54 | 0.78 |
| engine analyze (pose on every frame + scoring) | 182.22 | 203.48 |
| engine annotated re-encode | 9.64 | 9.67 |
| engine metric clips (40 clips, 4-wide) | 42.68 | 55.70 |
| engine annotated upload | 0.41 | 0.38 |
| engine total | 235.49 | 270.02 |
| backend `requests.post` to engine | 237.5 | 272.3 |
| backend token + store + notify | 0.09 | 0.13 |
| backend total | 237.60 | 272.44 |

The backend's own work is ~0.1 s of a ~240 s job. The gap between the backend's engine call and the
engine's self-reported total is **~2 s** and covers cold start + network. All optimisation value is in the
engine's `analyze` and `clips` stages.

Same-clip variance across runs (182 vs 203 s, 43 vs 56 s) is instance variance, not code. Read
`ANALYSIS_STAGES` before crediting any change.

## Infrastructure as deployed

| | backend `my-python-backend` | engine `bowling-service` |
|---|---|---|
| revision | 00183 (2026-09-05) | 00049-knc (2026-08-29) |
| cpu / mem | 1 / 2Gi | 8 / 8Gi |
| concurrency | 80 (gunicorn gthread 2×8) | 1 |
| min / max instances | 1 / 10 | 0 / 3 |
| timeout | 900 s | 880 s |
| startup cpu boost | on | on |

Cloud Tasks `analysis-jobs`: 3 concurrent dispatches, 3 attempts, 5/s. The engine's concurrency 1 ×
max 3 is the real ceiling: a 4th simultaneous upload waits a full analysis.

## Findings, ranked by gain ÷ effort

### F1. Pushup metric clips are rendered, re-encoded and uploaded, then never displayed — S, 43–56 s (18–20 %) per pushup job. **Verified.**
Engine `src/lifting/pipeline.py:170-172` renders up to four clips per rep, `service/app.py:292-313,391-394`
re-encodes and uploads them. The result page renders pushups as one set-summary card
(`frontend/src/pages/VideoPlayer.tsx:737-745` via `lib/setSummary.ts`, which has no clip field) and hides the
rep-by-rep table. Gate `_render_metric_clips` on the exercise config (keep for curl/squat/deadlift). No accuracy
risk; also removes storage + egress. Biggest safe win available today.

### F2. Rep-lift pose runs single-process on an 8-vCPU instance — M, est. 100–170 s.
`src/lifting/pose/estimator.py:208-235` is a plain `cap.read()` → `detect_for_video` loop, called once from
`pipeline.py:142`. The plank path already has the pattern (`plank_analyzer.py:190-262`: time-chunked workers,
own `VideoCapture` seek + own landmarker per worker, merge by frame index). Port it to `estimate_video`.
**Needs a fixture eval**: OneEuro smoothing and prev-skeleton state reset at chunk edges can shift rep
boundaries/grades. Ship behind an env flag (`LIFT_POSE_WORKERS`, default 1) and compare rep counts + grades
on the pushup/curl fixture clips before enabling.

### F3. `num_poses=5` on rep lifts — S code / M validation, est. 20–40 % of remaining pose time.
`estimator.py:143`. Multi-pose forces the detector to search for five people every frame instead of
tracking one ROI. The candidate scorer (`estimator.py:70-150`) exists to pick the lifter out of a crowded
gym, so this is a behaviour change; try `num_poses=2` first. Plank already uses 1.

### F4. Frame stride 2 for rep lifts — M-L, ~50 % of remaining pose time.
Plank samples at 15 fps (`ANALYSIS_FPS`); rep lifts still run every frame. Rep detection is a peak search
over elbow/hip angles at ~30 fps; half rate is very likely neutral but must be proven on fixtures
(rep count, ROM min/max, tempo). Combine with F2 for the largest total.

### F5. Engine cold start is ~2 s, not tens of seconds — no action. **Verified from logs.**
Instance start 01:59:43.05 → gunicorn listening 01:59:43.92 → video downloaded 01:59:46.7 →
TFLite delegate created 01:59:52.8. Container boot is ~1 s; the ~6 s model init happens *inside*
`analyze_s` because `PoseEstimator()` is constructed per request (`pipeline.py:142`). A pre-warm ping from
the upload signing routes would save ≤2 s; caching the landmarker per worker process would save ~6 s but
needs a state reset between videos. Both are small; noted for completeness.

### F6. `NORMALIZE_BEFORE_ANALYZE=true` is inert on the deployed engine. **Verified.**
The env var is set on `bowling-service` but no code on `feat/pushup-config` reads it; it lives only on the
unmerged `feat/normalize-before-analyze` / `feat/analysis-pipeline-hardening` branches. Consequences: no
1080p rescue downscale for >1080p sources, and no `MAX_ANALYSIS_DURATION_S` fail-fast — a long raw phone
video can still hit the 880 s cap. The deploy warning in CLAUDE.md guards a var the running image ignores.
Fix = merge the hardening branch (or drop the var). The 9.6 s `reencode_s` is the annotated-video H.264
re-encode, *not* normalisation.

### F7. Lifting upload page uses `auto` compression — S. **Verified.**
`pages/UploadVideo.tsx:141` calls `uploadVideo` with no options → `auto`; a browser without WebCodecs falls
into the realtime MediaRecorder encode (plays the whole clip before sending a byte). `ChallengeDetail.tsx:211`
already passes `fast-only`. Pass `fast-only` here too. No effect on Chrome/Edge/Safari 16+.

### F8. Bowling video upload still uses the legacy multipart `/bowling/upload` — M. **Verified.**
`pages/BowlingUpload.tsx:54` posts FormData; `routes/bowling_routes.py:127` does `upload_from_string(file.read())`.
Hard 32 MiB Cloud Run cap (typical phone clips 413 with no server trace — the same bug fixed for lifting in
June), bytes cross the network twice, whole file in RAM twice, a gunicorn thread held for the transfer, no
compression/resume/progress. Route through `uploadVideo()` + a `/bowling/finalize` mirroring
`upload_routes.py:536`.

### F9. `queue_wait_s` is unusable for re-queued jobs — S, no speedup. **Verified.**
`services/analysis_timing.py:36` measures from `LiftingResult.created_at`; re-queue at
`routes/lifting_routes.py:50-56` resets status/`updated_at` but not `created_at`. Both prod samples report
4059 s / 4722 s for jobs that started within seconds. Add `queued_at` (set on insert and on re-queue).

### F10. Fold the analysis trigger into `/upload/finalize` — S.
`UploadVideo.tsx:171` awaits a second round trip (`triggerLiftingAnalysis`) after finalize. Creating the
`LiftingResult` row + enqueue inside `finalize_upload` (`upload_routes.py:536`) saves one mobile RTT and
closes the "uploaded but analysis never started" hole. Keep the standalone route for re-analyze.

### F11. Render clips asynchronously — L, 18–20 % of every rep-lift job (curl/squat/deadlift; F1 covers pushups).
Nothing on the result headline depends on clips. Return the report when `analyze` finishes; render clips in
a follow-up job. Frontend must tolerate missing clip URLs; engine needs the clean-checkout build.

### F12. Render/encode at ≤720p and pipe to ffmpeg — M, 5–12 s on rep lifts, 40–60 % of the plank tail.
`pipeline.py:186-197` sizes the annotated writer from the source and writes with cv2 (avc1 → mp4v fallback),
then `service/app.py:380-382` re-encodes with ffmpeg: every output frame is encoded twice. Piping raw frames
into `ffmpeg -f rawvideo … -c:v libx264 -preset veryfast` at 720p drops the intermediate file and the second
pass (skeleton coordinates are in source pixels — scale them by the same factor). Plank is worse:
`plank_analyzer.py:300-307` opens an mp4v writer, `:620-670` re-decodes the source to draw overlays, then the
service re-encodes again.

### F13. The rep-clip renderer buffers every decoded frame from first rep to last rep — OOM risk. **Verified.**
`pipeline.py:272-278` reads frames `min_frame..max_frame` into a dict before cutting clips. At 1080p that is
~6 MB per frame, so a 60 s set at 30 fps is ~11 GB on an 8 Gi instance — the exact pattern that OOM'd the
plank analyzer in June (fixed there by re-decoding per render). It has not fired in prod only because sets
have been short. F1 removes the exposure for pushups; for curl/squat/deadlift either seek per clip or stream
the range once and write clips as you go. S–M, safe.

### F14. Bowling analysis still shells out — M, 2–8 s per bowling job.
`service/app.py:184-198` runs `python -m scripts.debug_ball_motion` as a subprocess per request (fresh
interpreter + full imports each time) and recovers metrics by regex over stdout (`:217-233`). Lifting moved
in-process in engine commit `afd9266`; bowling never did. Moving it in-process also gives real tracebacks.

### F15. Annotated-video upload blocks before clips start — S, 2–5 s.
`service/app.py:384-394` uploads the annotated video synchronously, then starts the clip stage. Run the
upload on a thread alongside clip work. Clip uploads are already 4-wide (`:311`).

### F16. Engine config drift — S, hygiene.
`deploy.sh` says `--timeout=600` and no `--cpu-boost`; `Dockerfile:41` says gunicorn 870; the live revision
runs 880 with cpu-boost on (set by hand on 2026-08-29). The next `deploy.sh` run would silently regress
both, on top of dropping env vars (already documented in CLAUDE.md). Reconcile the script with the live
revision. `from src.lifting import pipeline` is a function-level import inside the request handler
(`service/app.py:365`), so the first request after a cold start also pays the MediaPipe/OpenCV import.
Cost note: concurrency 1 × 8 vCPU bills ~1840 vCPU-s per 230 s pushup job; F1 + F2 would cut that to
roughly 500–640.

### Minor / no action
- Two spare GCS round trips in composite complete/finalize (`upload_routes.py:725`, `:561`) — ~0.1–0.3 s.
- `AnalysisStatus.tsx:70` polls every 4 s without backoff (~60 requests/analysis); cheap, `report` is NULL
  until completion. Optional backoff.
- Backend concurrency 80 vs 16 gunicorn threads hides thread saturation from the autoscaler; harmless while
  the queue caps in-flight `/jobs/*` at 3. Lower `--concurrency` only together with queue/engine limits.
- Indexes on every upload/poll query are present (`User(email)`, `UserCompetition(user_id,competition_id)`,
  `LiftingResult.attempt_id`, `BowlingResult.attempt_id`); notification runs after commit (0.04 s).
- Compression cannot overlap upload without a fragmenting muxer (`resumableUpload.ts:233-281`) — L, skip.

## Recommended order

1. **Safe, no eval:** F1 (gate pushup clips) + F13 (stop buffering clip frames) + F15 (overlap annotated
   upload) + F16 (reconcile deploy.sh) in one engine deploy; F7 (`fast-only`) + F9 (`queued_at`) in one
   backend/frontend deploy. Expected: pushup job 240 s → ~190 s, and the OOM exposure gone.
2. **Needs a fixture eval:** F2 + F3 + F4 behind env flags — the 4–8× lever on the pose stage. Expected:
   pushup job ~190 s → 60–90 s. See "Fixture eval" below.
3. F6 merge the hardening branch (duration gate + rescue normalisation), F8 bowling upload path, F14
   bowling in-process.
4. F11 / F12 once the above land and real traffic exists to measure against.

## Fixture eval for the pose changes (F2–F4)

Real clips live at `~/code/bowling-app/analysis-engine/videos/input/` (`sagar_curl.mp4`,
`20260131_184427_toka_curl.mp4`, `production_deadlift.mp4`); engine commit `f70f646` moved fixtures out of
git to GCS, so treat those local copies as the source. `scripts/analyze_lift.py --output-summary` emits the
JSON to diff (rep count, per-metric scores, overall grade). Run each clip with the flag off and on, and
accept a change only when rep count is identical and every metric score moves < 2 points. There is no
lifting timing harness (`tests/test_benchmarks/` covers lane edges only) and **no real pushup clip exists
anywhere** — the live pushup challenge is graded on config that was never validated on real footage.

## Engine deploy reminders (unchanged)
Build from a clean worktree of `feat/pushup-config`; do not run `deploy.sh` as-is (it drops env vars);
pass `GCS_BUCKET_NAME, PLANK_POSE_WORKERS=8, NORMALIZE_BEFORE_ANALYZE=true, CLIP_UPLOAD_WORKERS=4`,
`--timeout=880 --cpu-boost`. Rollback: `bowling-service-00047-tdf`.

## Status
None of F1–F16 has been implemented; this is a findings document. The `queue_wait_s` bug (F9) and the
inert env var (F6) are the two things that would mislead the next measurement pass, so fix those first.
