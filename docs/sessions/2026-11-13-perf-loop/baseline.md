# Perf loop 2026-11-13: baseline (profile + Cloud Run)

## Headline

- **Cloud Run gives different results on different instances of the same image.** The prod reference itself depends on which instance did the work. The bench ran 16 requests against one revision, and they landed on two instances. On those two instances, 5 of 8 fixtures gave different results (rep count +-1 on two situps, the clean split on pushup_e18a31d1, plank hold 82.19 vs 82.79 s). Within one instance the result was stable. **Each prod fixture matches one of the two instances:**
  - Instance A (`…eed6b1222b98`) matches prod on pushup_3c66c85e, pushup_e18a31d1, situp_16b6ca35, situp_667a8480 and the plank.
  - Instance B (`…bb285fb747c2`) matches prod on situp_c9dec98b (13) and pushup_97b4aaf2 (25).
  - Squat matches on both.
  - So the two fixtures.md calls "tripwires" are not emulation drift. Prod analysed them on a B-class host, and the emulated image behaves like A.
- **Host class also accounts for most of the speed spread.** Analyze was 15-23% faster on instance B than on instance A for the same fixture. On one instance it repeats within about 1% (pushup_97b4aaf2 ran on B twice: 84.49 / 85.39 s). The bench's "run-to-run spread" of 13-26% is the gap between instances, not noise.
- **Where the seconds go on Cloud Run (rep lifts):**
  - Pose inference is 52-84% of analyze, at 38-50 ms/frame, about 2x the laptop.
  - Metric-clip rendering is 8-40%, the worst case being 720p pushups (42 s of 106 s).
  - Rendering the annotated video is 5-14%.
  - Decode, model init, tracking and scoring are each under 3%.
  - After analyze, the service's `clips` stage (ffmpeg re-encode + upload of 26-100 clips) adds 4-23 s, and the annotated re-encode adds 1-6 s.
- **Situp costs about 2x a pushup mainly because situp videos have about 2x the frames** (1719-2618 vs 847-1232). Per-frame pose cost is only about 15% higher for situps: 45-50 vs 38-44 ms/frame on Cloud Run, from more candidate poses per frame (1.26 vs 0.99 at 720p). Resolution is the second factor. Per frame, rendering is cheaper for situps, because they cut 2 clips per rep where pushups cut 4.
- **`num_poses=5 → 1` cut pose inference by 34-36% on Cloud Run** (45.3→29.1 and 49.7→32.8 ms/frame, situp_667a8480, first 600 frames, timed only). It changes the candidates that situp tracking and the per-frame selector see, so it is a lead and must pass compare.py.
- The engine runs on Cloud Run **gen1 (gVisor, kernel `4.19.0-gvisor`)** with 8 vCPUs, avx2/avx512f visible. The gen2 execution environment is a config-only candidate that nobody has tested yet.

## What is NOT covered / caveats

- **Host-class mapping is n=2 instances.** A third CPU class may exist. The CPU model reads `unknown` under gVisor, so A and B are labelled by instance id and by their outputs, not by hardware. Prod's own per-attempt instance ids were not read.
- **Gating consequence for the integrator:** a strict compare of a candidate against `*.prod.json` on Cloud Run will FAIL on some fixtures even for an unchanged engine. Compare a candidate per fixture against the base run **from the same host class**, using `instances.tsv` and the A/B reference set below. Or use the emulated prod image (deterministic, class A) for correctness, with Cloud Run for speed only. Until a candidate request lands on a known class, its compare result cannot be attributed to the code change.
- **Cloud Run profile split** comes from the throwaway tag `perf-prof` (image `perf-prof-93378b0` = perf-base plus `harness/profiling/` behind a `/profile` route that runs the profiler in a subprocess), n=1 per rep-lift fixture. Wrapping adds per-call overhead (proxy objects on every `read`/`write`/`detect_for_video`), so read the split as proportions. Its situp_667a8480 run gave 31 reps (B-like). Instances were not recorded for the profile runs.
- **Plank:** the wrappers cannot see inside the 8 spawned pose workers (prod `PLANK_POSE_WORKERS=8`). Model init, decode and inference are all inside "parallel pose total". The laptop plank row used 4 workers.
- **Laptop native rows** (arm64, Python 3.13, cv2 4.13) are secondary. Their codec paths and counts differ (squat 13 reps vs 12), and Cloud Run encode is 3-6x slower relative to them.
- `NORMALIZE_BEFORE_ANALYZE` appears nowhere in the engine (`grep -rn --include='*.py'` over perf-engine is empty), so that env var is inert.
- **Deviation from the brief:**
  - `gcloud run services replace` failed: it needs the Cloud Resource Manager API, which is disabled on toms-gym. I declined the enable prompt.
  - Instead, `bowling-service-perf` was created with `gcloud beta run deploy` and explicit flags.
  - Evidence of parity: the exported revision spec of `bowling-service-perf-perf-base` differs from `bowling-service-00053-fxm` **only in the image digest** (`diff` of the `spec:` sections; files `cloudrun-base/rev-*.export.yaml`).
  - The new service has an empty IAM policy (no allUsers). It also has no `run.invoker` binding for the backend SA, which nothing needs.
- **Rebuilt image vs prod image:** pip resolved the same key versions (`opencv-python-headless 5.0.0.93`, `numpy 2.2.6`, `mediapipe 0.10.30`, `scipy 1.15.3`). Each fixture matched prod on at least one instance, so dependency drift is not visible. I did not deploy the prod digest itself to the perf service. Every candidate built today inherits these same unpinned resolutions.
- **Prod read-back:** `bowling-service` stayed on latest `bowling-service-00053-fxm`, `latestRevision: true` 100%, image `situp-13b49b5`, generation 55, before the bench, after the service was created, and after the bench (`cloudrun-base/bowling-service-{before,after-create,after-bench}.txt`).

## Cloud Run baseline (perf-base tag, n=2 per fixture, sequential)

Seconds come from the engine's own `stages` (= `ANALYSIS_STAGES`). "prod" is the backend `ANALYSIS_TIMING` for the original attempt. squat r1 was the first request on instance B and carries about 5 s of lazy import, so the bench now does a discarded warm-up first.

Instance per request (`cloudrun-base/instances.tsv`): **A** = `…eed6b1222b98`, **B** = `…bb285fb747c2`.

| fixture | r1 host | r2 host | r1 vs r2 analyze (same host?) | result by host |
|---|---|---|---|---|
| squat_f47a8848 | B (cold) | B | 44.36 / 38.91 (B/B, r1 cold) | 12 reps both |
| pushup_3c66c85e | A | B | 83.96 / 64.73 | A = prod; B: score_drift + metric_status |
| pushup_97b4aaf2 | B | B | 84.49 / 85.39 (1.1%) | B = prod (25); emulated image gives 26 |
| pushup_e18a31d1 | A | B | 121.82 / 102.53 | A = prod; B: clean_split differs |
| situp_16b6ca35 | A | B | 157.25 / 130.40 | A = prod; B: rep boundaries differ |
| situp_667a8480 | A | B | 193.94 / 163.08 | A = prod (30); B gives 31 |
| situp_c9dec98b | A | B | 132.70 / 112.85 | B = prod (13); A gives 14, as does the emulated image |
| plank_9600f455 | B | A | 35.78 / 44.52 | A = prod (82.79 s); B gives 82.19 s |

Every result in the table below:

| fixture | prod analyze / clips / total s | r1 analyze / clips / reencode / total s | r2 analyze / clips / reencode / total s | spread analyze | r1 vs prod | r2 vs prod | r1 vs base-image | r2 vs base-image |
|---|---|---|---|---|---|---|---|---|
| squat_f47a8848 | 43.22 / 4.43 / 59.4 | 44.36 / 4.45 / 2.47 / 51.77 | 38.91 / 4.42 / 0.8 / 44.39 | 13.1% | MATCH | MATCH | MATCH | MATCH |
| pushup_3c66c85e | 93.19 / 6.4 / 103.04 | 83.96 / 6.23 / 2.62 / 93.32 | 64.73 / 7.13 / 1.04 / 73.24 | 25.9% | MATCH | DIFF(metric_status,score_drift) | MATCH | DIFF(metric_status,score_drift) |
| pushup_97b4aaf2 | 79.66 / 21.92 / 106.1 | 84.49 / 21.7 / 3.58 / 110.23 | 85.39 / 23.19 / 3.65 / 112.73 | 1.1% | MATCH | MATCH | DIFF(grade,metric_status,rep_timing,reps,score_drift) | DIFF(grade,metric_status,rep_timing,reps,score_drift) |
| pushup_e18a31d1 | 134.59 / 20.63 / 162.24 | 121.82 / 20.35 / 4.31 / 147.15 | 102.53 / 22.76 / 4.13 / 129.99 | 17.2% | MATCH | DIFF(clean_split,grade,metric_status,score_drift) | MATCH | DIFF(clean_split,grade,metric_status,score_drift) |
| situp_16b6ca35 | 170.93 / 6.54 / 180.9 | 157.25 / 6.46 / 2.32 / 166.49 | 130.4 / 6.6 / 2.3 / 139.82 | 18.7% | MATCH | DIFF(reps) | MATCH | DIFF(reps) |
| situp_667a8480 | 230.81 / 15.4 / 256.12 | 193.94 / 12.75 / 6.24 / 213.64 | 163.08 / 15.32 / 6.22 / 185.31 | 17.3% | MATCH | DIFF(clean_split,grade,metric_status,rep_timing,reps,score_drift) | MATCH | DIFF(clean_split,grade,metric_status,rep_timing,reps,score_drift) |
| situp_c9dec98b | 120.09 / 7.13 / 134.75 | 132.7 / 9.95 / 4.97 / 148.32 | 112.85 / 6.34 / 4.93 / 124.93 | 16.2% | DIFF(reps,score_drift) | MATCH | MATCH | DIFF(reps,score_drift) |
| plank_9600f455 | 52.28 / 0.0 / 59.5 | 35.78 / 0.0 / 4.87 / 41.36 | 44.52 / 0.0 / 3.88 / 49.26 | 21.8% | DIFF(plank_hold,plank_score) | MATCH | DIFF(plank_hold,plank_score) | MATCH |

(`vs base-image` = vs the emulated prod image's laptop output. It matches instance A's results.)

Reference outputs per class for gating candidates: class A = `cloudrun-base/{pushup_3c66c85e,pushup_e18a31d1,situp_16b6ca35,situp_667a8480,situp_c9dec98b}.r1.json` + `plank_9600f455.r2.json`. Class B = `cloudrun-base/{squat_f47a8848,pushup_3c66c85e,pushup_97b4aaf2,pushup_e18a31d1,situp_16b6ca35,situp_667a8480,situp_c9dec98b}.r2.json` + `pushup_97b4aaf2.r1.json` + `plank_9600f455.r1.json`.

## Profile: where analyze time goes

#### Cloud Run (perf-prof tag, 8 vCPU gVisor, prod deps)

| fixture | frames | res | analyze s | model init | decode | pose inference | ms/frame inf | poses/frame | rgb+build | track+smooth | rep+score | render video (dec/enc) | render clips (dec/enc) | clips written |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| plank_9600f455 (plank_9600f455.r1.profile.response.json) | 2586 | 1280x720 | 42.3 | in workers | in workers | parallel pose total 30.73 | - | - | - | - | rest 0.15 | 11.41 (enc 9.85) | - | 0 |
| plank_9600f455 (plank_9600f455.r2.profile.response.json) | 2586 | 1280x720 | 42.18 | in workers | in workers | parallel pose total 29.53 | - | - | - | - | rest 0.19 | 12.44 (enc 10.66) | - | 0 |
| pushup_3c66c85e | 1232 | 480x360 | 60.86 | 0.24 | 0.66 | 47.33 | 38 | 0.92 | 1.03 | 0.0 | 0.11 | 3.15 (0.47/1.44) | 8.33 (0.53/5.09) | 72 |
| pushup_e18a31d1 | 1022 | 1280x720 | 105.52 | 0.26 | 1.51 | 44.92 | 44 | 0.99 | 2.29 | 0.0 | 0.12 | 14.13 (1.44/7.89) | 42.29 (1.45/29.66) | 96 |
| situp_16b6ca35 | 2618 | 480x360 | 139.79 | 0.28 | 1.78 | 117.48 | 45 | 0.95 | 1.89 | 0.95 | 0.27 | 6.57 (1.3/3.19) | 10.54 (1.46/6.22) | 64 |
| situp_667a8480 | 1976 | 1280x720 | 160.76 | 0.78 | 2.65 | 98.13 | 50 | 1.26 | 5.1 | 0.67 | 0.23 | 22.43 (2.29/12.29) | 30.77 (2.24/22.66) | 62 |
| squat_f47a8848 | 767 | 480x360 | 40.02 | 0.29 | 0.55 | 31.46 | 41 | 0.84 | 0.91 | 0.0 | 0.07 | 1.99 (0.35/0.93) | 4.75 (0.33/3.03) | 48 |

#### laptop native arm64 (secondary)

| fixture | frames | res | analyze s | model init | decode | pose inference | ms/frame inf | poses/frame | rgb+build | track+smooth | rep+score | render video (dec/enc) | render clips (dec/enc) | clips written |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| plank_9600f455 (plank_9600f455.profile.json) | 2586 | 1280x720 | 22.59 | in workers | in workers | parallel pose total 19.08 | - | - | - | - | rest 0.05 | 3.46 (enc 3.0) | - | 0 |
| pushup_3c66c85e | 1232 | 480x360 | 28.36 | 0.13 | 0.23 | 23.5 | 19 | 0.91 | 0.16 | 0.0 | 0.04 | 0.9 (0.31/0.23) | 3.39 (0.33/2.29) | 72 |
| pushup_e18a31d1 | 1022 | 1280x720 | 46.92 | 0.14 | 0.28 | 20.98 | 21 | 0.99 | 0.29 | 0.0 | 0.04 | 4.37 (1.17/1.56) | 20.81 (0.41/17.55) | 96 |
| situp_16b6ca35 | 2618 | 480x360 | 58.31 | 0.15 | 0.5 | 50.95 | 19 | 0.94 | 0.19 | 0.27 | 0.09 | 1.9 (0.71/0.55) | 4.25 (0.64/2.74) | 64 |
| situp_667a8480 | 1976 | 1280x720 | 73.21 | 0.12 | 0.63 | 49.9 | 25 | 1.29 | 0.48 | 0.21 | 0.08 | 6.47 (1.91/2.25) | 15.31 (1.22/12.25) | 68 |
| squat_f47a8848 | 767 | 480x360 | 16.07 | 0.18 | 0.14 | 13.16 | 17 | 0.84 | 0.09 | 0.0 | 0.02 | 0.52 (0.17/0.14) | 1.95 (0.14/1.39) | 52 |

Columns:
- decode = `cap.read` in the pose pass.
- rgb+build = the pose pass minus inference and decode (BGR→RGB, `mp.Image`, Skeleton build).
- render (dec/enc) = the total, with the decode part and the `VideoWriter.write` (mp4v encode) part.
- clips written = metric clips the engine wrote; the service then re-encodes and uploads each one.
- Cloud Run model init is under 0.8 s, and track+smooth+rep+score is under 1.5 s on every fixture.

### num_poses micro-benchmark (Cloud Run, perf-prof tag, `profile-cloudrun/numposes.situp_667a8480.json`)

Same 600 decoded frames of situp_667a8480 in one process, timing only. The order was 5, 1, 5, 1.

| num_poses | rep1 ms/frame | rep2 ms/frame | poses/frame |
|---|---|---|---|
| 5 (prod) | 45.3 | 49.7 | 1.23 |
| 1 | 29.1 | 32.8 | 1.00 |

## Ranked: where the seconds are (Cloud Run, per job)

1. **Pose inference: 31-117 s per rep-lift job, 52-84% of analyze.** It is serial per frame on 8 vCPUs, at 38-50 ms/frame. The levers, cheapest first:
   - `num_poses` 5→1: -35% of inference, measured. It is an accuracy risk for situp tracking.
   - Parallel chunked pose for rep lifts, as the plank already does. This needs a VIDEO-mode tracking/smoothing seam at the chunk boundaries.
   - Frame stride.
   - The gen2 execution environment, config only.
2. **Metric clips: 5-42 s in the engine's render plus 4-23 s in the service's re-encode and upload.** Pushups write 4 clips per rep at full resolution through cv2 mp4v and then re-encode every clip with ffmpeg. pushup_e18a31d1 spends 42 s rendering and 20-23 s in the clips stage, against 102-122 s of analyze. The 2026-09-05 findings (F1) say the pushup clips are never displayed, so gating them off for pushups is the cheapest large win. Re-verify on the current frontend first. Otherwise: encode once (pipe to ffmpeg H.264, drop the re-encode) or downscale.
3. **Annotated video render: 2-22 s** (mp4v encode 1-12 s), **plus the H.264 re-encode at 1-6 s.** Encoding H.264 once at render time would remove one full encode pass.
4. **Plank: 36-45 s analyze.** The 8-worker parallel pose pass is about 30 s, and the overlay render is 11-12 s, with the encode at 10-11 s. The render is the cheap target.
5. **Host class: +-15-23% on everything,** depending on which instance a job lands on. Engine code cannot change this. It also decides the board result on borderline videos.
6. Decode (1-3 s), model init (under 1 s), tracking/smoothing/scoring (under 1.5 s), download (under 0.6 s), and summary upload (under 0.4 s) are not worth working on.

## Files

- `cloudrun-base/`:
  - `<fixture>.r<k>.json`: full engine responses.
  - `bench.tsv`, `compare.txt`, `instances.tsv`, `bench.log`.
  - Service and revision exports, and the prod read-backs.
- `profile-cloudrun/`: Cloud Run profile responses (plank r1/r2 from the `perf-prof2` tag, which carries a fixed `__main__` guard for the spawn workers) and the num_poses result. `profile/`: the laptop native profiles.
- `harness/bench_cloudrun.sh <tag-url> <outdir> [runs=2] [fixture ...]`:
  - Refuses any URL that is not a `bowling-service-perf` URL.
  - Checks `/health`, makes one discarded warm-up call, then runs sequential runs with attempt ids `perf-bench-<fixture>-<tag>-r<k>`.
  - Writes `bench.tsv` and `compare.txt` (vs prod and vs the base image), then joins each attempt to its instance id from the logs (`instances.tsv`).
  - The run that produced this baseline did not have the warm-up or the instance join. The join was then tested by hand on this run's logs (16/16 rows).
- `harness/summarize_baseline.py` regenerates the tables above. `harness/profiling/` holds the profiler, the num_poses bench, the `/profile` Flask wrapper and its Dockerfile (`FROM perf-base`), none of it committed to the engine.

Resources created, all on the throwaway service `bowling-service-perf`, none serving users:
- Revisions `bowling-service-perf-perf-base` (100%, tag `perf-base`), `-perf-prof` (0%, tag `perf-prof`) and `-perf-prof2` (0%, tag `perf-prof2`).
- Images `gcr.io/toms-gym/bowling-service:perf-base-93378b0`, `perf-prof-93378b0` and `perf-prof2-93378b0`.
- The `gs://jtr-lift-u-4ever-cool-bucket/perf-bench/` fixtures, plus the engine's outputs under `lifting/perf-bench-*`.
