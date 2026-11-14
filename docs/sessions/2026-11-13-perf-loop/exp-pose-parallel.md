# Experiment pose-parallel: chunked parallel pose for rep lifts (LIFT_POSE_WORKERS)

## Headline

- Nothing was blocked or skipped. Prod `bowling-service` did not change: `bowling-service-00053-fxm` at 100%, generation 55, read before and after (`exp-pose-parallel/prod-{before,after}.txt`). Everything on Cloud Run ran on the throwaway `bowling-service-perf` as 0%-traffic tagged revisions.
- **`LIFT_POSE_WORKERS=4` gives the same output as the sequential engine, by construction, and cuts Cloud Run analyze 1.3-2.2x** (final commit, `pp-f4`, n=3 per fixture, vs the class-B base at n=1-2). A second pair of instances with the same setting (`pp-w4`, n=2) gave 1.5-2.6x. The pose stage alone drops 2.4-3.1x on `pp-f4` and 2.7-3.7x on `pp-w4`, against a 1-worker figure from the profiler (n=1). Default (unset or 1) is the old sequential path.
- **Equivalence, final code `47cb245`:**
  - Emulated prod image (rev-00053 deps, worktree mounted, 4 workers): 8/8 fixtures `compare.py` MATCH and **byte-identical** `summary.json` vs `base-image/`.
  - Cloud Run `pp-f4` (4 workers), 8 fixtures x 3 runs: 24/24 MATCH the base run of the same host class (all landed on class B).
  - Laptop native, on the earlier commits (not re-run on `47cb245`): end-to-end at `00d0d4c`, 7/7 rep fixtures byte-identical to flag-off and to `base-local/run1` at 4 workers (3 fixtures also at 2 workers, n=3); raw pose output at `9fe6d63` (`==` on every Skeleton, before any scoring) identical on 7 fixtures x {2,3,4} workers, 39 chunk boundaries.
  - Laptop native on `47cb245`: raw pose output identical at 4 workers on `situp_667a8480` (the fixture that needs the extension) and on the 1080p clip; the opt-in real-video test passes on the squat at 3 workers.
- **8 workers do not beat 4 on the 8-vCPU instance.** Pose stage, Cloud Run seconds: squat 33 -> 17 (2) -> 10-12 (4) -> 9-11 (6) -> 10-11 (8). Use 4.
- The seam hazard is real and the code handles it rather than tolerating it: see "The seam".

## What is NOT covered

- **Default-off = old behaviour rests on this, and no more:** laptop native at `00d0d4c`, flag unset, 8/8 fixtures byte-identical to `base-local/run1` (`estimator.py` is unchanged from `00d0d4c` to `47cb245`; the last commit touches only `parallel.py`, which the flag-off path never imports); Cloud Run `pp-off` 6/6 MATCH on three fixtures (squat, pushup_e18a31d1, situp_667a8480). Flag-off was not run in the emulated prod image.
- **Cloud Run class A with the final commit at 4 workers.** Both `pp-f4` instances were class B. Class A evidence is (a) the emulated image, which behaves like class A, on the final commit, and (b) Cloud Run `pp-w8` (8 workers, both instances class A, 8 fixtures x 3) on the previous commit `00d0d4c`, 24/24 MATCH the class-A reference (for `pushup_97b4aaf2`, which has no class-A Cloud Run base, the emulated-image reference). `00d0d4c` -> `47cb245` changes one search start index that cannot alter results with the shipped constants (see "What I tried").
- **Flag-off speed on Cloud Run is only shown equal to base within host variance** (`pp-off`, 3 fixtures x 2: squat 38.8 warm vs base 38.9; pushup_e18a31d1 111-114 vs 102.5; situp_667a8480 162-189 vs 163). Two instances of the same class differed by 17% on the same fixture, so Cloud Run cannot resolve a small flag-off cost. Laptop: flag-off vs the base worktree back-to-back n=3, median off <= median base on all three fixtures, noise +-20% (sibling agents were loading the laptop).
- **Base Cloud Run numbers are n=1-2 per host class** (from baseline.md) and instances of one class vary +-15-20%. Read the speedups as ranges, not points. The 1-worker pose-stage column is the perf-prof profile (n=1, class unknown, profiler overhead included).
- **Why 8 does not scale is a hypothesis** (vCPUs are hyperthreads / memory bandwidth). I did not measure per-process CPU on Cloud Run. Laptop workers=1 uses 1.05 CPU per wall second, so the landmarker is single-threaded there.
- **No real 1080p fixture.** Memory at 1080p was measured natively on a 12 s clip upscaled from a 720p fixture (deleted after the run).
- **Unit tests use fake chunk streams.** They cover chunking, splice, digest, replay and fallback, not MediaPipe. The real-MediaPipe test is opt-in (`LIFT_POSE_TEST_VIDEO=<video>`, passes on the squat fixture, 3 workers, both entry points) because the repo has no lifting video.
- A hung worker (600 s poll timeout, then sequential) was not exercised for real; a raised worker error is unit-tested and falls back.
- gen2 execution environment, `containerConcurrency > 1`, the hybrid backend (untouched, it calls `estimate_frame`) and `num_poses != 5` were not run. See risks for `num_poses=1`.
- The notes folder is not committed (shared worktree with sibling agents); the engine branch is.

## How to enable

- Branch `perf/exp-pose-parallel` in `/Users/toka/code/bowling-app/perf-exp-pose-parallel`, base `93378b0`, commits `9fe6d63` (feature + tests), `00d0d4c` (stats through the logger), `47cb245` (sync search starts at the owner's own sync frame).
- Env: `LIFT_POSE_WORKERS=4`. Unset, `1`, or non-numeric = sequential path, same calls as before.
- Proof it is on: one log line per rep-lift job, `INFO:src.lifting.pose.parallel:LIFT_POSE_PARALLEL workers=4 frames=... sync_offsets=[...] extended_frames=... parallel_s=... splice_s=...`. Absent on plank and when the flag is off (checked: 0 lines for plank, 1 per rep fixture; 0 "Parallel pose failed" in 167 Cloud Run log lines).
- Files: `src/lifting/pose/parallel.py` (new), `src/lifting/pose/estimator.py`, `tests/test_lifting/test_pose_parallel.py`.

## Design

- Workers (spawn, like the plank) each open the video with `open_video`, `grab()` from frame 0 to their chunk bound (no seek, so frame indices cannot drift), start a cold landmarker with the same options, and return raw `(x, y, visibility)` per pose per frame plus a digest.
- The parent replays the existing selection, `_prev_skeleton` scoring and OneEuro smoothing sequentially over the merged frames (`estimate_video`), or builds the candidate lists for whole-video person tracking (`estimate_video_candidates`, situp). `estimate_frame` was split into detect and `_select_and_smooth` so both paths share that code. The only cross-chunk state left is inside MediaPipe.
- **Splice:** each chunk overruns its bound by 8 frames. A chunk is adopted only from the first frame where its digest equals the already-true stream on 5 consecutive frames. The digest is a crc of the decoded frame plus every float MediaPipe returned (landmarks and world landmarks, all poses). Until then the left worker is asked for 48 more frames at a time; a chunk that never matches is dropped and the left worker covers it. Worst case is sequential time plus worker start-up, never a different result.
- Any worker error, a video shorter than 120 frames, or fps 0 runs the sequential path.

## The seam (what the probe found)

Scratch probe, laptop, real MediaPipe, cold landmarker started at an offset vs the sequential stream (`scripts/probe.py`, `probe2.py`):

- Sequential vs sequential: 0 differing frames (the check can pass).
- `num_poses=1` canary: a cold start **never** becomes bit-identical (max diff 0.64 at the first frame, still 0.001-0.008 after 60 frames). So the check can fail, and a fixed warm-up would not have worked in that mode.
- `num_poses=5` (the rep-lift setting): bit-identical **from the first frame** at 12 of 14 offsets. My reading, not verified in MediaPipe's source: the detector runs every frame while fewer than 5 poses are tracked, so there is normally no carried state. That fits the baseline's finding that `num_poses=1` is 35% cheaper.
- The 2 failures: the sequential stream is still tracking a pose the detector no longer finds (a person lying down in the situp video); the cold chunk has one pose fewer. It re-synced after 27 and 113 frames, at the first frame the detector found that pose again, and stayed identical after.
- Removing the verification (adopt each chunk at its bound) on `situp_667a8480`: raw output differs from sequential starting exactly at the first chunk bound (frame 658 with 3 workers, 494 with 4) (`eq-mutant-unverified-splice.jsonl`). So an unverified port would have changed situp candidates in a live challenge.

## Equivalence per fixture

| fixture | emulated prod image, 4 workers, `47cb245` vs base-image | Cloud Run `pp-f4` (4 workers, `47cb245`) r1-r3 vs same-class base | Cloud Run `pp-w8` (`00d0d4c`) r1-r3 vs same-class base | native 4 workers (`00d0d4c`) vs flag-off |
|---|---|---|---|---|
| squat_f47a8848 | MATCH, byte-identical | 3/3 MATCH (B) | 3/3 MATCH | byte-identical (n=3, also 2 workers) |
| pushup_3c66c85e | MATCH, byte-identical | 3/3 MATCH (B) | 3/3 MATCH (A) | byte-identical |
| pushup_97b4aaf2 | MATCH, byte-identical | 3/3 MATCH (B, = prod 25 reps) | 3/3 MATCH emulated image (26 reps, class A) | byte-identical |
| pushup_e18a31d1 | MATCH, byte-identical | 3/3 MATCH (B) | 3/3 MATCH (A) | byte-identical (n=3, also 2 workers) |
| situp_16b6ca35 | MATCH, byte-identical | 3/3 MATCH (B) | 3/3 MATCH (A) | byte-identical |
| situp_667a8480 | MATCH, byte-identical | 3/3 MATCH (B, 31 reps) | 3/3 MATCH (A, 30 reps) | byte-identical (n=3, also 2 workers) |
| situp_c9dec98b | MATCH, byte-identical | 3/3 MATCH (B, = prod 13 reps) | 3/3 MATCH (A, 14 reps) | byte-identical |
| plank_9600f455 | MATCH, byte-identical (flag does not touch plank) | 3/3 MATCH (B) | 3/3 MATCH (A) | byte-identical |

- All 84 Cloud Run results across `pp-off/w2/w4/w6/w8/f4` match a same-class reference; none matched no class (`cloudrun/joined.txt`). Each instance was consistent with one class on every fixture where A and B differ.
- The first commit `9fe6d63` was also 8/8 byte-identical in the emulated image (`image-w4-9fe6d63/`).
- Comparator: `harness/compare.py`, strict, no `--tolerate`.

## Speed

### Cloud Run, pose stage only (engine log `parallel_s + splice_s`), seconds

| fixture (frames, res) | 1 worker (profile, n=1) | 2 | 4 (`pp-w4`, n=2) | 4 (`pp-f4` final, n=3) | 6 | 8 (class A) |
|---|---|---|---|---|---|---|
| squat_f47a8848 (767, 360p) | 33.2 | 16.4-17.1 | 10.2-10.8 | 12.2-12.7 | 9.2-11.1 | 10.4-11.0 |
| pushup_e18a31d1 (1022, 720p) | 49.0 | 28.2-30.9 | 15.9-16.5 | 18.2-19.7 | 17.3-19.0 | 19.5-20.0 |
| situp_16b6ca35 (2618, 360p) | 121.4 | 58.4-58.6 | 33.1-33.6 | 38.7-40.3 | 25.8-31.0 | 26.2-30.7 |
| situp_667a8480 (1976, 720p, 2 people) | 106.7 | 58.0-72.6 | 36.8-39.1 | 44.7-45.2 | 41.5-45.9 | 55.4-58.7 |

2, 4, 6 ran on class-B instances; 8 on class A (15-23% slower per baseline). `pp-w4` and `pp-f4` are the same setting on different instances; the 15-20% gap between them is instance variance, not the one-line code difference.

### Cloud Run, analyze stage (`ANALYSIS_STAGES analyze_s`), class-B base vs 4 workers

| fixture | base, class B | `pp-f4` final, n=3 | speedup | `pp-w4`, n=2 | speedup |
|---|---|---|---|---|---|
| squat_f47a8848 | 38.9 | 20.2, 20.6 (26.4 first call on a cold instance) | 1.9x | 16.9, 17.4 | 2.3x |
| pushup_3c66c85e | 64.7 | 33.0-33.7 | 1.9-2.0x | 27.0, 31.9 | 2.0-2.4x |
| pushup_97b4aaf2 | 84.5, 85.4 | 66.0-67.8 | 1.25-1.3x | 54.9, 55.4 | 1.5x |
| pushup_e18a31d1 | 102.5 | 76.1-79.6 | 1.3x | 62.7, 64.2 | 1.6x |
| situp_16b6ca35 | 130.4 | 59.3-61.0 | 2.1-2.2x | 49.9, 50.8 | 2.6x |
| situp_667a8480 | 163.1 | 103.8-107.1 | 1.5-1.6x | 86.3, 88.5 | 1.9x |
| situp_c9dec98b | 112.9 | 66.1-67.6 | 1.7x | 54.1, 57.3 | 2.0-2.1x |

Whole job (`processing_time_s`), class-B base -> `pp-f4`: squat 44 -> 26, pushup_3c66c85e 73 -> 42, pushup_97b4aaf2 110-113 -> 94-98, pushup_e18a31d1 130 -> 104-110, situp_16b6ca35 140 -> 70-72, situp_667a8480 185 -> 128-133, situp_c9dec98b 125 -> 81-82. What is left on the 720p pushups is clip and video rendering, which this experiment does not touch.

### Laptop native, back-to-back in one shell, n=3 (pose stage s; secondary, laptop was shared)

| fixture | base worktree | flag off | 2 workers | 4 workers | speedup vs off, per rep |
|---|---|---|---|---|---|
| situp_667a8480 | 71.1, 66.9, 64.5 | 56.0, 73.3, 61.4 | 30.8, 33.2, 35.8 | 20.5, 20.0, 27.5 | 2: 1.8, 2.2, 1.7; 4: 2.7, 3.7, 2.2 |
| pushup_e18a31d1 | 24.6, 36.8, 30.3 | 24.3, 32.7, 23.4 | 15.0, 18.2, 13.5 | 9.2, 9.2, 7.6 | 2: 1.6, 1.8, 1.7; 4: 2.6, 3.5, 3.1 |
| squat_f47a8848 | 16.2, 21.2, 15.2 | 16.0, 20.1, 15.1 | 10.3, 9.2, 8.4 | 7.9, 6.7, 5.3 | 2: 1.6, 2.2, 1.8; 4: 2.0, 3.0, 2.8 |

Other four rep fixtures, n=1, off -> 4 workers: situp_16b6ca35 54.3 -> 16.1, situp_c9dec98b 37.5 -> 12.0, pushup_3c66c85e 25.1 -> 8.1, pushup_97b4aaf2 19.4 -> 7.7.

### Why 4 and not 8

- 2 workers give 1.9-2.0x on the pose stage, 4 give 2.6-3.6x, 6 and 8 give nothing more on clean videos.
- On the two-person situp 8 is worse than 4: 7 boundaries, 4 of them needed the left worker extended (192 frames, 16 s done one worker at a time) against 1 of 3 at 4 workers (48 frames, 3-4 s).
- Start-up per worker on Cloud Run: 0.4-0.6 s (import + model). The `grab()` to the chunk start adds up to 2.3 s for the last of 4 workers on a 720p situp, 5.7 s for the last of 8.

### Memory

- Cloud Run, p99 per minute, max over the run (`cloudrun/memory-utilization.json`, 60 s samples so short peaks can be missed): perf-base 28% of 8 Gi, `pp-off` 17%, `pp-w4` 16%, `pp-f4` 15%, `pp-w6` 19%, `pp-w8` 26%. No revision came near the limit.
- Laptop, whole process tree, 4 workers: 1.32 GB at 720p, 1.62 GB on the 1080p clip; one worker is 256 MB at 720p and 321 MB at 1080p. Workers keep one frame at a time, so 8 workers at 1080p extrapolate to about 3 GB.

## Tests and mutation check

- `tests/test_lifting/test_pose_parallel.py`: 22 unit tests + 2 opt-in real-video tests; `tests/test_lifting` 250 passed.
- Whole engine suite on `47cb245`: 1280 passed, 10 failed. The same 10 fail on the base worktree at `93378b0` (1258 passed, 10 failed): bowling tracker/YOLO, lane benchmark, pipeline integration and `test_service_app.py::test_metric_clips_are_reencoded_uploaded_and_rewritten`. No failure is new (`tests-exp.txt`, `tests-base.txt`).
- 12 mutations on a scratch copy, each verified by re-reading the file, all killed (`mutation-final.txt`): sync on 1 or 4 frames, search before the owner's own sync frame, splice off by one, adopt unverified, never extend, digest without the frame, digest without presence, replay timestamp drift (both entry points), flag ignored, worker failure swallowed.
- Two mutants survived the first pass and led to changes: a partial "sync on one frame" mutation (the test had no coincidence inside the initial overlap; added) and a redundant read-to-EOF call (removed).

## What I tried, including what did not work

- **Fixed warm-up frames at chunk starts (the brief's suggestion): not built.** The probe showed the mismatch lasts until the detector re-finds a tracked pose, 27-113 frames here and unbounded in principle, so no fixed overlap is safe. Verified splice replaces it.
- **Seek to the chunk start: not used.** `grab()` from frame 0 keeps indices exact and costs at most about 2 s at 4 workers. A seek guarded by the same digest could recover that; left as a follow-up.
- **`print` for the stats line: replaced by the logger** so Cloud Run shows it.
- **Two cold chunks can agree with each other before the left one is itself verified.** With overrun 8 and sync 5 at most 3 such frames exist, so results could not change, but the search now starts at the owner's own sync frame so no choice of constants can splice at an unverified frame (`47cb245`, with a test that fails without it).
- **8 and 6 workers on Cloud Run: no gain over 4**, and worse on the two-person video.
- **Parallel extension of several boundaries at once and a larger overrun: not built.** At 4 workers the sequential extension cost 3-4 s on the worst fixture.

## Risks

- **Sibling flags must go through the shared code, or they are bypassed at workers > 1.** The parallel branch returns before the sequential loop, and the landmarker options now live only in `create_landmarker()` (used by `PoseEstimator.__init__` and by every worker). A flag that changes `num_poses`, strides frames, or edits the sequential loop in `estimate_video` / `estimate_video_candidates` has to be made in `create_landmarker()` and in the worker loop in `parallel.py` too, then re-run through the raw-equality check.
- **The `bowling-service-perf` template now carries my image and `LIFT_POSE_WORKERS=4`** (the last deploy was `pp-f4`). A later deploy there with `--update-env-vars` inherits both. Use `--set-env-vars` with the full list and an explicit `--image`, as these deploys did.
- **The final commit at 4 workers never landed on a class-A Cloud Run instance.** The emulated image (class-A-like) covers it, 8/8 byte-identical.
- **Do not combine with `num_poses=1` without re-testing.** In the probe a cold chunk never matched the sequential stream in that mode. With this code every chunk would then be dropped and the job would cost sequential time plus start-up: output stays correct, the speedup disappears. I did not run the engine that way; this follows from the probe and the splice rule. The same applies to any change that makes the landmarker carry state.
- **Videos with several people, or where the detector loses the lifter for long stretches, get less.** Each unsynced boundary is finished by one worker. Worst case is about sequential time plus 1-2 s.
- The sync rule assumes that 5 consecutive frames with identical frame crc and identical MediaPipe floats mean identical tracker state. It held on 39 native boundaries, 8/8 emulated-image fixtures and 84 Cloud Run results, and the unverified mutant shows the check bites, but it is an argument about MediaPipe's graph, not a proof.
- 4 extra processes of about 250-320 MB each for the pose stage. Fine at `containerConcurrency: 1` and 8 Gi; not sized for concurrency above 1.
- Host class still decides the board result on borderline videos. This change does not add to that and does not fix it.

## Resources created (all on the throwaway service, none serving users)

- Revisions on `bowling-service-perf`, 0% traffic, tagged: `pp-off`, `pp-w2`, `pp-w4`, `pp-w6`, `pp-w8` (image `exp-pose-parallel-00d0d4c`) and `pp-f4` (image `exp-pose-parallel-47cb245`, `LIFT_POSE_WORKERS=4`). Their specs differ from `perf-base` only in the image digest and that env var (`cloudrun/rev-*.export.yaml`). Traffic stayed 100% on `perf-base`.
- Images `gcr.io/toms-gym/bowling-service:exp-pose-parallel-{00d0d4c,47cb245}` = `perf-base-93378b0` plus the two changed files.
- Engine outputs under `lifting/perf-bench-*-pp-*` in the bucket.

## Files

- Engine branch: `/Users/toka/code/bowling-app/perf-exp-pose-parallel` (`perf/exp-pose-parallel`, head `47cb245`).
- Evidence: `/Users/toka/code/toms_gym-perf/docs/sessions/2026-11-13-perf-loop/exp-pose-parallel/`
  - `eq-raw.jsonl` (raw equality sweep), `eq-mutant-unverified-splice.jsonl`, `mutation-final.txt`
  - `image-final-w4/` (final commit, timing + compare per fixture), `image-w4-9fe6d63/`
  - `cloudrun/joined.txt` and `joined.json` (every result: instance, matched class, analyze, pose stats), `pose-log-lines.txt`, `<tag>/bench.tsv`, `<tag>/instances.tsv`, `f4/*.json`
  - `native-ab/ab-summary.txt`, `ab.progress`
  - `scripts/` (probe, eq, A/B, Cloud Run join, memory sampler, mutation runner)
- Scratch outputs not copied (annotated summaries, logs): `/Users/toka/code/bowling-app/perf-exp-pose-parallel-out/`.
