# Engine perf deploy, 2026-11-14

Outcome of the 2026-11-13 perf loop (notes, harness and every measurement: `docs/sessions/2026-11-13-perf-loop/`;
start with `candidate.md` and `verify-engine.md`).

## What is live

**Superseded the same day:** live is `bowling-service-00061-ram` (engine `main` at `f4d0059`): this build plus automatic lift type (`00057-qag`, the rollback target) and auto on the parallel pose workers; explicit lift types return the same reports. See `docs/reference/auto-lift-type.md`. The rest of this section describes `00054-zj5`.

- `bowling-service-00054-zj5`, image digest `sha256:42f105dd…6e11`, built from engine branch
  `perf/engine-2026-11-13` at `f198bac` (worktree `~/code/bowling-app/perf-engine`, off `feat/situp-config` `93378b0`).
- Three env flags, each default off in code (unset = the old path):
  - `LIFT_POSE_WORKERS=4`: chunked parallel pose for rep lifts. A chunk is adopted only after it matches the
    sequential stream bit for bit on 5 consecutive frames. 8 workers are no faster than 4.
  - `SKIP_METRIC_CLIPS_FOR=pushup,situp`: no per-rep metric clips for lifts whose result page never shows them.
  - `LIFT_VIDEO_ENCODER=ffmpeg`: one libx264 encode instead of cv2 mp4v plus a re-encode.
- Rollback: `gcloud run services update bowling-service --region us-east1 --remove-env-vars LIFT_POSE_WORKERS,SKIP_METRIC_CLIPS_FOR,LIFT_VIDEO_ENCODER`
  (same image, old path; checked on the laptop image only), or route traffic to `bowling-service-00053-fxm`.
- Frontend `my-frontend-00208-pgq`: `upload-timing` telemetry event per successful upload (logged as
  `FRONTEND_ERROR action=upload-timing`, filter it out when counting errors) and no realtime MediaRecorder fallback.

## Measured

Cloud Run, 8 real 100 Club clips, alternating A/B on a cloned bench service: 953 s -> 311 s summed (3.07x).
Pushup 90-146 s -> 25-32 s, situp 153-227 s -> 45-63 s, squat 44 s -> 17-23 s, plank unchanged.
On the live revision after the deploy (direct engine calls, one instance): squat 24.7 s, pushup 18.6 s, situp 52.4 s,
plank 35.5 s, each identical to the verified candidate output for that host class.

## Not covered

- No phone upload through the backend was run after the deploy; read the next real `ANALYSIS_TIMING` lines.
- No 1080p, portrait or multi-person clip ran on Cloud Run. Memory peaked at 27 % of 8 Gi on the fixtures.
- Annotated video playback was checked with ffprobe on laptop outputs, not in a browser or the APK.

## Open

- **Host-class nondeterminism (pre-existing, not caused by this change):** the same image scores the same video
  differently on two kinds of Cloud Run instance: 5 of 8 clips differ, e.g. a pushup clip at 25 vs 26 reps and a rep
  moving between clean and sloppy. Evidence: `baseline.md`, `cloudrun-base/instances.tsv`.
- Cheaper inference (`num_poses`, frame stride, smaller input) changes rep counts on nearly every clip; it can only
  be judged against hand-counted reps, not against the current engine.
- `feat/auto-lift-type` and `fix/squat-rep-count` are both off `93378b0` and must be rebased onto
  `perf/engine-2026-11-13` before they deploy; the dry merge conflicts in `src/lifting/pose/estimator.py` and
  `tests/test_service_app.py`.
- Upload: no speedup shipped. 28 uploads in 14 days, median 6.7 s, the PUT is nearly all of it; iOS is link-bound.
