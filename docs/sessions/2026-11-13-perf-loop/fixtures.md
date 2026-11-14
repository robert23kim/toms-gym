# Perf loop 2026-11-13: fixtures and harness

## Headline

- 8 real attempts (3 Situp, 3 Pushup, 1 Squat, 1 Plank) are fixtures, all analysed by prod engine rev `bowling-service-00053-fxm` (the only revision serving since 2026-09-13).
- **I ran the prod image (digest `sha256:e3acfcbd…`) on the laptop as linux/amd64. On 6 of 8 fixtures it reproduces the prod result exactly, under the strict gates.** It is byte-deterministic run to run, and the result is the same with 4 or 8 CPUs.
- The other 2 (`pushup_97b4aaf2`, `situp_c9dec98b`) differ from prod by **one rep at a borderline**. The image gives 26 vs 25 and 14 vs 13 with a different rep set. Their GCS objects were not rewritten after upload (GCS generation time = upload time). These two **flip on tiny numeric perturbation** (Rosetta x86 vs Cloud Run's real CPU), so treat them as tripwires, not as proof.
- **Do not use laptop-native runs (analysis-engine venv) to check prod parity.** They are deterministic (byte-identical run1 vs run2 on all 8), but they match prod on **0 of 8**: rep counts are off by 1 to 20 (`situp_c9dec98b` gives 33 vs 13), and the plank `longest_run_s` is 0.87 s off. The cause is the deps: the venv is Python 3.13 / cv2 4.13 / arm64, and the image is Python 3.10.21 / cv2 **5.0.0** / mediapipe 0.10.30 / numpy 2.2.6. Native runs are fine for native-vs-native A/B speed and diffs only.
- The image's `/app/src` and `/app/service` are **identical** to the perf-engine worktree at `93378b0` (`diff -rq` is empty). Its model `.task` sha256 values match the copies seeded into the worktree. Mounting the worktree over `/app` (`WORKTREE=`) gives a byte-identical squat result.
- Laptop seconds, for reference only (the claim must be Cloud Run seconds): native analyze takes about 0.3-0.5x prod's analyze time on rep lifts (1.4x on the plank, heavy model). The emulated image takes about 0.6-1.1x.

## What is NOT covered

- None of this ran on Cloud Run. `bowling-service-perf` did not exist at 2026-11-13 ~21:30 (`gcloud run services list`). Until a variant runs there on the 8 fixtures and passes `compare.py` against `*.prod.json`, no claim about prod parity or prod speed is proven. The 2 tripwire fixtures need that run most.
- The pairing of attempt to video is by **log adjacency**: each `Finalize upload: object=…` line is paired with the next `Finalize succeeded: attempt=…` line (the trace field was empty). `GET /attempts/<id>` returned an error for all 8, so it could not confirm the pairing. The pairing is confirmed by the lift type in the Finalize line, and by the prod-image exact match on 6 of 8. The 2 tripwires share most rep boundaries with prod (same video).
- Engine stdout (`[ANALYZE] rep … ACCEPTED/SKIPPED`) is not in Cloud Run logs, so prod's per-rep gate decisions cannot be read back.

## Manifest

Prod timings come from the backend `ANALYSIS_TIMING` line (`engine_s` = backend-measured engine call, `total_s` = whole job). "prod result" is what the board reads: `total_reps`, reps with `form_score >= 70`, and plank `total_in_plank_s`. Native runs use the analysis-engine venv on the perf-engine worktree. Prod-image runs use the rev-00053 image as linux/amd64 under Rosetta, `--cpus 4`, `PLANK_POSE_WORKERS=8 NORMALIZE_BEFORE_ANALYZE=true` (prod env).

| fixture | lift | frames | fps | res | rot | dur s | prod result | prod analyze / clips / reencode / engine / total s | laptop-native wall (analyze) s, run1/run2 | prod-image wall s | native vs prod | prod-image vs prod |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| plank_9600f455.mp4 | Plank | 2586 | 30 | 1280x720 | 0 | 86.5 | hold 82.8s | 52.28 / 0.0 / 6.04 / 64.02 / 66.09 | 74.43 (72.64) / 75.31 (73.74) | 64.14 | DIFF(plank_hold) | MATCH |
| pushup_3c66c85e.mov | Pushup | 1232 | 24 | 480x360 | -180 | 51.3 | 18 reps / 18 clean | 93.19 / 6.4 / 2.9 / 107.57 / 108.5 | 32.41 (29.72) / 31.89 (29.74) | 76.78 | DIFF(grade,metric_status,rep_timing,reps,score_drift) | MATCH |
| pushup_97b4aaf2.mp4 | Pushup | 847 | 30 | 1280x720 | 0 | 28.4 | 25 reps / 20 clean | 79.66 / 21.92 / 4.1 / 106.16 / 107.13 | 53.79 (45.87) / 49.37 (41.75) | 108.11 | DIFF(clean_split,grade,metric_status,rep_timing,reps,score_drift) | DIFF(grade,metric_status,rep_timing,reps,score_drift) |
| pushup_e18a31d1.mp4 | Pushup | 1022 | 30 | 1280x720 | 0 | 34.1 | 24 reps / 19 clean | 134.59 / 20.63 / 6.3 / 166.92 / 167.96 | 57.07 (48.71) / 59.49 (51.38) | 123.72 | DIFF(clean_split,grade,metric_status,score_drift) | MATCH |
| situp_16b6ca35.mov | Situp | 2618 | 24 | 480x360 | -180 | 109.1 | 32 reps / 32 clean | 170.93 / 6.54 / 2.9 / 180.98 / 181.77 | 61.46 (58.93) / 62.99 (60.42) | 145.82 | DIFF(metric_status,rep_timing,reps,score_drift) | MATCH |
| situp_667a8480.mp4 | Situp | 1976 | 30 | 1280x720 | 0 | 66.2 | 30 reps / 28 clean | 230.81 / 15.4 / 8.85 / 260.81 / 262.08 | 81.67 (74.89) / 82.1 (74.77) | 179.77 | DIFF(clean_split,grade,metric_status,rep_timing,reps,score_drift) | MATCH |
| situp_c9dec98b.mp4 | Situp | 1719 | 30 | 1280x720 | 0 | 57.5 | 13 reps / 13 clean | 120.09 / 7.13 / 6.79 / 135.7 / 136.58 | 64.28 (58.66) / 65.22 (59.19) | 122.82 | DIFF(grade,metric_status,rep_timing,reps,score_drift) | DIFF(reps,score_drift) |
| squat_f47a8848.mov | Squat | 767 | 24 | 480x360 | -180 | 32.0 | 12 reps / 4 clean | 43.22 / 4.43 / 1.97 / 60.36 / 61.23 | 18.2 (16.94) / 18.85 (17.59) | 45.17 | DIFF(grade,metric_status,rep_timing,reps,score_drift) | MATCH |

Prod-image repeat on the 2 tripwires (`base-image-run2/`, `base-image-cpu8/`): identical to `base-image/`, still DIFF vs prod (reps).

## Files

- Fixtures (never commit): `/Users/toka/code/bowling-app/perf-fixtures-2026-11-13/`
  - `<lift>_<attempt8>.mp4|mov`: the source upload, from `gs://jtr-lift-u-4ever-cool-bucket/videos/…`.
  - `<name>.prod.json`: `GET /lifting/result/<attempt_id>` body (report under `.report`, NaN scrubbed to null).
  - `prod_timings.json`: the parsed `ANALYSIS_TIMING` line, the attempt id and the GCS object per fixture.
- Baselines (committed): `base-image/` (prod parity reference), `base-local/run1` and `base-local/run2` (native reference). `*.summary.json` is the engine report and `*.timing.json` holds the stages plus the analyze breakdown (`pose`, `render_video`, `render_clips`, `plank_analyze`).
- Harness: `harness/`.
  - `run_local.py` mirrors `service/app.py` `analyze_lift()` with no GCS. It copies the fixture to `input.mp4`, runs `analyze_lift(output_video=…, camera_view_override=None, no_overlay=False, lift_type=<lowercase>)` and `build_lift_summary`, re-encodes the annotated video, then re-encodes the clips in a `CLIP_UPLOAD_WORKERS` pool with `threads=2`. A canary exits if any engine module loads from outside the given worktree.

## Commands

```bash
H=/Users/toka/code/toms_gym-perf/docs/sessions/2026-11-13-perf-loop/harness
FX=/Users/toka/code/bowling-app/perf-fixtures-2026-11-13
WT=/Users/toka/code/bowling-app/perf-engine   # or your variant worktree

# One-time per new engine worktree: seed the pose models (gitignored .model_cache)
mkdir -p $WT/src/lifting/pose/.model_cache && cp /Users/toka/code/bowling-app/analysis-engine/src/lifting/pose/.model_cache/pose_landmarker_{full,heavy}.task $WT/src/lifting/pose/.model_cache/

# Prod-parity check of a variant: prod image deps + your worktree's src/service mounted over /app
WORKTREE=$WT $H/run_prod_image.sh $FX/situp_16b6ca35.mov /tmp/out PLANK_POSE_WORKERS=8 NORMALIZE_BEFORE_ANALYZE=true
python3 $H/compare.py $FX/situp_16b6ca35.prod.json /tmp/out/situp_16b6ca35.summary.json     # vs prod (6 fixtures expected MATCH)
python3 $H/compare.py $H/../base-image/situp_16b6ca35.summary.json /tmp/out/situp_16b6ca35.summary.json  # vs base image (all 8 expected MATCH)

# All fixtures, sequentially (image, or a worktree path for native)
WORKTREE=$WT $H/run_all.sh image /tmp/out-image PLANK_POSE_WORKERS=8 NORMALIZE_BEFORE_ANALYZE=true
$H/run_all.sh $WT /tmp/out-native [ENV=VAL ...]     # native A/B speed; compare against base-local/run1, not prod

# One fixture natively with flags
$H/run_local.sh $WT $FX/pushup_3c66c85e.mov /tmp/out SOME_FLAG=1

# Regenerate the manifest table
python3 $H/manifest.py
```

Do not edit `run_all.sh` while it is running. Bash reads scripts incrementally, and that edit cost run2 its ALLDONE line.

## compare.py gates

Every gate is strict by default. Reps are paired by time overlap, so one extra or missing rep is reported once.

| gate | rule |
|---|---|
| reps | `total_reps` and `len(rep_metrics)` identical, and every rep pairs by time overlap |
| clean_split | per-rep `form_score >= 70` identical (the Situp clean/sloppy board rule, `CLEAN_REP_MIN_FORM`) |
| grade | per-rep `form_grade` and `overall_grade` identical |
| view | `camera_view` and `active_arm` identical |
| score_drift | per-rep `form_score`, `overall_score` and per-metric `value` within 2 points |
| metric_status | per-metric pass/warn/fail identical |
| rep_timing | rep `start_s`/`end_s` within 0.25 s |
| plank_hold | `total_in_plank_s` and `longest_run_s` within 0.5 s |
| plank_type / plank_score | `plank_type` identical; `overall_form_score` within 0.02, `body_line_*` within 2 deg |

`--tolerate a,b` downgrades the named gates to warnings. It refuses `reps`, `clean_split` and `plank_hold` unless `--i-know` is also given.

I did not loosen any tolerance. The prod-image instrument needs none on 6 of 8, and the 2 tripwires differ in rep count, which no tolerance may hide.

**Mutation check** (edited copies of prod JSONs):

| mutation | expected | result |
|---|---|---|
| drop rep 6 of situp_16b6ca35 | exit 1 | exit 1, [reps] |
| rep 31 form 72.6 -> 69.9 | exit 1 | exit 1, [clean_split] |
| rep 31 70.5 vs 69.5 (crosses 70, drift 1.0) | exit 1 | exit 1, [clean_split] only |
| rep 31 72.6 -> 70.9 (drift 1.7, no cross) | exit 0 | exit 0 |
| plank hold +1.0 s | exit 1 | exit 1, [plank_hold] |
| plank hold +0.3 s | exit 0 | exit 0 |
| `--tolerate clean_split` without `--i-know` | refused | refused, exit 1 |

## Side observations for the perf agents

- On Cloud Run, `analyze` is 85-93% of engine time. On the slow fixtures the prod analyze time is about 2-3x the native laptop time and about 1.3-1.6x the emulated-image laptop time at 4 CPUs, so the 8-vCPU Cloud Run instance is slower per job than a laptop under Rosetta. CPU allocation and throttling, and the pose stage, are the places to look.
- `clips` is 4-26 s in prod for pushups and situps. It is `_reencode_h264` x (reps x metrics) plus the uploads.
- Laptop-native breakdown (situp_667a8480): analyze is 74.9 s, split into pose 51.3 s, render_video 7.7 s and render_clips 15.4 s. Pose is about 70% of it (see `analyze_breakdown` in `base-local/run1/*.timing.json`).
