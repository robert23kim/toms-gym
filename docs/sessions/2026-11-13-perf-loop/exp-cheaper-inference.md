# Perf loop 2026-11-13: experiment cheaper-inference

## Headline

**Nothing is accepted. No setting that makes pose inference cheaper passes the equivalence gate, so none should be enabled.** Not run: Cloud Run (no revision was created on `bowling-service-perf`, because no candidate survived the laptop gates). Nothing was blocked.

| setting (flag) | pose-pass time vs flag-off (laptop, interleaved) | prod-image gate vs `base-image/` | native gate vs native base |
|---|---|---|---|
| all flags unset | CPU 0.97-1.00x of base 93378b0 | **8/8 MATCH** (incl. plank) | 7/7 MATCH, skeletons bitwise identical |
| `POSE_NUM_POSES=1` | 0.54-0.66x (-34 to -46%; most on the fixture with 1.3 poses/frame) | **0/7 pass**, rep count changes on 6 of 7 | 0/7 pass |
| `POSE_NUM_POSES=3` / `=2` | 3: 1.00x on 3/3 fixtures; 2: 0.96-1.00x (both inside the noise floor) | not run (nothing to gain) | 3: skeletons bitwise identical on 3/4, different on `situp_667a8480`, where compare.py fails on metric_status, rep_timing, score_drift; 2: differs on 1/3 |
| `POSE_FRAME_STRIDE=2` | 0.49-0.51x (-50%) | **0/3 pass** (3 of 7 rep fixtures run) | 0/7 pass |
| `POSE_MAX_SIDE=640` | 0.98x on 720p (inside the 0.97-1.01 noise floor) | **0/2 pass** (2 of 4 720p fixtures run) | 0/4 pass |
| `POSE_NUM_POSES=1` + `POSE_FRAME_STRIDE=2` | 0.31-0.32x (-68%) | not run (both parts fail alone) | not run |

The flag code is on branch `perf/exp-cheaper-inference` (commit `d0ba36d`), default off. With every flag unset it reproduces `base-image/` on all 8 fixtures under prod deps, so merging it changes nothing; there is also no reason to merge it today.

**Decision needed:** equivalence to the current engine cannot be the gate for this family of changes. The engine's own count for `situp_c9dec98b` is 13 on Cloud Run host class B (prod), 14 on class A and in the emulated image, 15 with stride 2, 28 with `num_poses=1`, and 33 on the laptop's native deps. A hand-counted rep total per fixture is the only gate that could tell "different" from "worse".

## What is NOT covered

- **Cloud Run.** No candidate ran there. Speeds below are laptop arm64 ratios, measured while the load average was 24-50. The only Cloud Run number for this family is the baseline's `num_poses` micro-benchmark (-34 to -36%), which agrees with the laptop ratio. Host class B was never exercised; the prod-image gate is class A only.
- **Subset runs in the prod image:** stride 2 ran on squat, `pushup_3c66c85e`, `situp_c9dec98b`; max-side 640 ran on `pushup_e18a31d1`, `situp_667a8480`. Both failed on every fixture run, and failed on every fixture in the native screen, so the rest were not run.
- **Prod-image pose seconds are not a timing source.** Those runs overlapped other agents' jobs (flag-off pose 147 s vs 124 s in `base-image/` for the same code path).
- **No ground truth.** "Fails the gate" means "differs from the current engine", not "less accurate".
- The combination was timed only. `num_poses` 2/3 were timed and screened natively, not run in the prod image, because they save nothing.
- Decode at reduced resolution was not built: decode is 1-2 ms/frame here (0.5-2.7 s per job in the Cloud Run profile), the render passes need full-size frames anyway, and a smaller landmarker input already fails the gate.

## Gate results

Prod image = rev-00053 image as emulated amd64 with this worktree's `src/` and `service/` mounted (`code_hash f152716adfc9ad5f`, checked by the harness), env `PLANK_POSE_WORKERS=8 NORMALIZE_BEFORE_ANALYZE=true`, compared with `compare.py` against `base-image/`. reps/clean = `total_reps` / reps with `form_score >= 70`.

| variant | fixture | base reps/clean | variant reps/clean | failing gates |
|---|---|---|---|---|
| flag-off | all 8 | - | identical | none (MATCH x8, plank hold 82.79 s both) |
| np1 | squat_f47a8848 | 12/4 | 13/4 | grade, metric_status, rep_timing, reps, score_drift |
| np1 | pushup_3c66c85e | 18/18 | 19/19 | grade, metric_status, rep_timing, reps, score_drift |
| np1 | pushup_97b4aaf2 | 26/20 | 26/19 | clean_split, grade, metric_status, rep_timing, reps, score_drift |
| np1 | pushup_e18a31d1 | 24/19 | 23/20 | clean_split, grade, metric_status, rep_timing, reps, score_drift |
| np1 | situp_16b6ca35 | 32/32 | 41/41 | grade, metric_status, rep_timing, reps, score_drift |
| np1 | situp_667a8480 | 30/28 | 32/32 | clean_split, grade, metric_status, rep_timing, reps, score_drift |
| np1 | situp_c9dec98b | 14/14 | 28/28 | grade, metric_status, rep_timing, reps, score_drift |
| stride2 | squat_f47a8848 | 12/4 | 12/4 | grade, metric_status, rep_timing, score_drift |
| stride2 | pushup_3c66c85e | 18/18 | 17/17 | grade, metric_status, rep_timing, reps, score_drift |
| stride2 | situp_c9dec98b | 14/14 | 15/15 | grade, metric_status, rep_timing, reps, score_drift |
| side640 | pushup_e18a31d1 | 24/19 | 23/19 | clean_split, grade, metric_status, reps, score_drift |
| side640 | situp_667a8480 | 30/28 | 32/31 | clean_split, grade, metric_status, rep_timing, reps, score_drift |

**The flag was on in each run:** every image log carries the estimator's own lines, e.g. np1 `POSE_CONFIG num_poses=1 ...`, stride2 `POSE_STATS ... frames=767 inferred=384`, side640 `POSE_STATS ... inferred=1022 resized=1022`. The flag-off logs show `num_poses=5 max_side=0 frame_stride=1`, `inferred == frames`, `resized=0` and no `POSE_CONFIG` line.

Native screen (`screen.py`: pose pass + analysis, no render; arm64 venv). Its flag-off output matches `base-local/run1` on 7/7, so the instrument is valid. Rep totals, base -> variant:

| fixture | np1 | stride2 | side640 |
|---|---|---|---|
| squat_f47a8848 | 13 -> 13 (grade, timing, score fail) | 13 -> 12 | no-op (480x360) |
| pushup_3c66c85e | 18 -> 19 | 18 -> 18 (clean split fails) | no-op |
| pushup_97b4aaf2 | 25 -> 25 (clean split fails) | 25 -> 24 | 25 -> 24 |
| pushup_e18a31d1 | 24 -> 23 | 24 -> 24 (clean split fails) | 24 -> 24 (score_drift only) |
| situp_16b6ca35 | 32 -> 41 | 32 -> 31 | no-op |
| situp_667a8480 | 34 -> 34 (grades, timing fail) | 34 -> 21 | 34 -> 34 (clean split fails) |
| situp_c9dec98b | 33 -> 31 | 33 -> 33 (grades, timing fail) | 33 -> 33 (grades, timing fail) |

Every variant moved keypoints on 83-100% of frames, with a 99th-percentile shift of 15-1270 px. Nothing here is a small perturbation.

## Speed

Instrument: `ibench.py`. One process, every arm's `PoseEstimator` is fed the same decoded frames in 48-frame chunks in rotating order, so load hits all arms alike. It times resize + BGR->RGB + `mp.Image` + inference, per source frame. Ratio = chunk median vs flag-off; `off2` is a second flag-off arm (the noise floor). n = 16 / 22 / 36 / 55 chunks. The CPU-time ratio is in brackets.

| arm | squat_f47a8848 (360p) | pushup_e18a31d1 (720p) | situp_c9dec98b (720p) | situp_16b6ca35 (360p) |
|---|---|---|---|---|
| flag-off, ms/frame wall (CPU) | 27.0 (24.3) | 32.5 (27.0) | 27.2 (25.8) | 26.7 (24.2) |
| off2 (noise floor) | 0.97 (1.00) | 1.01 (1.00) | 0.99 (1.00) | 0.99 (1.00) |
| np1 | 0.66 (0.67) | 0.64 (0.64) | 0.63 (0.63) | 0.64 (0.64) |
| stride2 | 0.51 (0.50) | 0.50 (0.50) | 0.50 (0.50) | 0.49 (0.50) |
| side640 | 1.00 (no-op) | 0.98 (0.99) | 0.98 (0.96) | 1.00 (no-op) |
| np1 + stride2 | 0.32 (0.32) | 0.31 (0.32) | 0.32 (0.32) | 0.32 (0.33) |

**Flag-off equals base:** whole-process ABAB of the pose pass, base worktree `perf-engine` (93378b0) vs this branch with no flags, n=4 each on squat / pushup_e18a31d1 / situp_c9dec98b. CPU-time median ratio 0.99 / 0.97 / 1.00; skeleton hash identical on every run. Wall median ratio was 0.95 / 1.11 / 0.90, which is machine load, not code (`timing-base-vs-off.jsonl`).

If the gate were waived, and pose is 52-84% of analyze on Cloud Run (baseline.md), np1 would be roughly -19 to -30% of analyze and stride 2 roughly -26 to -42%. That is arithmetic, not a measurement.

## Why each one fails or does not pay

- **`num_poses` 5 -> 1.** Reading of the evidence (MediaPipe source not opened here): with one person in frame the landmarker holds fewer poses than `num_poses`, so it runs the person detector on every frame. `num_poses=1` stops that while a pose is tracked. That is the whole saving and the whole behaviour change: keypoints differ on every frame that has a pose. `num_poses=3` still runs the detector every frame, so it saves nothing: 1.00 / 1.00 / 1.00x of flag-off on squat, pushup_e18a31d1 and situp_667a8480 in a second interleaved run on a quieter machine (load average 6-10; `ibench-np/`, noise floor 0.99-1.01), and `num_poses=2` gives 1.00 / 1.00 / 0.96x. Their skeletons are bitwise identical to base only while a video never holds more than the allowed number of candidates: `num_poses=3` differs on `situp_667a8480` (1.29 poses/frame). So there is no middle setting. The same run put `num_poses=1` at 0.62-0.63x on squat and pushup and 0.54x on `situp_667a8480`.
- **Frame stride 2.** Situps leave skipped frames empty for `clean_pose_track` to interpolate; pushup/squat interpolate between neighbours after the per-frame selector. The landmarker sees half the frames and the smoothing sees a doubled step, and rep boundaries move.
- **Max side 640.** The model input size is fixed, so a smaller source only saves the colour conversion and copy (about 1.5 ms of 33 ms at 720p) and adds a resize. No gain, and results still change.
- **BGR->RGB / copy.** Measured at 720p: `cvtColor` 0.55 ms + `mp.Image` 1.0 ms of 33.3 ms per frame (4.6%); at 360p 0.19 ms of 26.8 ms. Both are required inputs. Nothing to skip.
- **Threads.** Inference is single-threaded: in `ibench.py` the CPU time of the timed calls is 0.83-0.95x of their wall time (flag-off row above), so at most one core is busy. mediapipe 0.10.30's Python `BaseOptions` maps to a C struct with model path and delegate only, so the thread count is not reachable from this code. On an 8-vCPU instance the remaining lever is more processes (the plank path already does this), which is outside this experiment.

## Code and tests

- Engine branch `perf/exp-cheaper-inference`, worktree `/Users/toka/code/bowling-app/perf-exp-cheaper-inference`, one commit `d0ba36d` on 93378b0. Touches `src/lifting/pose/estimator.py`, `src/lifting/pipeline.py`, new `tests/test_lifting/test_pose_options.py`.
- Flags, each also per lift as `<NAME>_<LIFT>` (e.g. `POSE_NUM_POSES_PUSHUP=1`): `POSE_NUM_POSES` (default 5), `POSE_MAX_SIDE` (default 0 = source size), `POSE_FRAME_STRIDE` (default 1). Unset or invalid = old behaviour. Plank and the hybrid backend are untouched.
- Tests: 26 new, all pass. Mutation check (`mutation_check.py`, output in `mutation_check.txt`): 9 mutations, 9 killed, each by the test meant for it; file restored and re-read after each. My first pass was partly invalid: a same-size restore inside one second left a stale `.pyc`, so the next mutation looked killed by the wrong test. The rerun disables bytecode caching.
- `tests/test_lifting` + service and summary tests (`-m "not slow"`): 264 pass, 1 fails. The failure (`test_service_app.py::test_metric_clips_are_reencoded_uploaded_and_rewritten`, the fake lacks a `threads` kwarg) fails the same way on base 93378b0.
- One near miss: I ran that first mutation pass while two screens were using the worktree. No screen process started inside the window (file times checked), and the one closest to it was rerun with a bitwise-identical result. I also once wrote to a `mutate.py` in the shared session scratchpad that belonged to another agent; none of my edits matched its text, its content is unchanged, and it wrote nothing in my worktree.

## Files (all under `exp-cheaper-inference/`)

- `screen.py`, `sweep.sh`, `skdiff.py`: native screen. Outputs in `screen/<tag>/` (`*.summary.json`, `*.screen.json` with the skeleton hash and pose stats; the 30 MB of skeleton dumps were deleted).
- `image_gate.sh`, `image_all.sh`, `image.log`, `image/<tag>/`: prod-image gate outputs and logs.
- `ibench.py`, `ibench_all.sh`, `ibench/*.json`, `ibench.log`: interleaved speed bench.
- `timing_base.sh`, `timing-base-vs-off.jsonl`: base vs flag-off. `timing.sh`, `timing.jsonl`: an earlier process-level A/B, too noisy to use. `ibench_np.sh`, `ibench-np/*.json`, `screen/np3/`: the `num_poses` 3/2 check.
- `mutation_check.py`, `mutation_check.txt`.
