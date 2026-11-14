# Perf loop 2026-11-13: experiment non-pose (clips, encode, re-encode)

Engine branch `perf/exp-non-pose` (worktree `/Users/toka/code/bowling-app/perf-exp-non-pose`), 4 commits on `93378b0`, head `ad232be`.

## Headline

- **Nothing was blocked. One thing was cut short and one mistake was left behind.** The emulated prod-image A/B stopped at n=2 on the pushup and situp key fixtures (squat n=3 counting the smoke pair); the Cloud Run A/B is n>=3 on squat, pushup_e18a31d1, situp_667a8480 and the plank. A first deploy with a wrong env delimiter left a broken revision `bowling-service-perf-np-on` on the throwaway service (0% traffic, no tag, never called).
- **Two flags, both default off = old behaviour:**
  - `SKIP_METRIC_CLIPS_FOR=pushup,situp` skips the per-rep metric clips for those lift types. The result page never shows them (proof below).
  - `LIFT_VIDEO_ENCODER=ffmpeg` pipes rendered frames straight into one libx264 encode. The cv2 mp4v write and the service's ffmpeg re-encode both go away, for the annotated video (rep lifts and plank) and for the clips that are still made (squat).
- **Cloud Run, both flags on, same result class (B), total job seconds:**

| fixture | base (perf-base) | flags off (same image) | flags on | on vs base | on vs off |
|---|---|---|---|---|---|
| pushup_e18a31d1 (720p) | 130.0 (n=1) | 120.8 (n=1) | 58.4 (n=3, 55.5-62.5) | 2.23x | 2.07x |
| pushup_97b4aaf2 (720p) | 111.5 (n=2) | - | 59.4 (n=1, incl. a 9 s upload stall) | 1.88x | - |
| pushup_3c66c85e (360p) | 73.2 (n=1) | 67.0 (n=1) | 64.0 (n=1, incl. a 9.5 s upload stall) | 1.14x | 1.05x |
| situp_667a8480 (720p) | 185.3 (n=1) | 209.9 (n=2) | 127.5 (n=3, 118.0-132.4) | 1.45x | 1.65x |
| situp_c9dec98b (720p) | 124.9 (n=1) | - | 90.4 (n=1) | 1.38x | - |
| situp_16b6ca35 (360p) | 139.8 (n=1) | - | 130.5 (n=1) | 1.07x | - |
| squat_f47a8848 (360p) | 48.1 (n=2, one cold) | 46.3 (n=2) | 40.1 (n=3, 36.9-43.2) | 1.20x | 1.15x |
| plank_9600f455 (720p) | 41.4 (n=1) | 55.1 (n=3) | 33.7 (n=4, 31.1-36.8) | 1.23x | 1.64x |

- **What those ratios do and do not prove.** Off and on ran on different instances (a revision's env is fixed), and instances that give the same result still differ in speed: flags-off against base on the same class ranges from -8% to +33%. So the totals carry that much instance noise. The part that does not depend on the instance is the stage split, which held on all 27 flags-on requests: `reencode_s` 0.7-7.3 -> 0.0, `clips_s` 6-23 -> 0.0 for pushup and situp (4.1 -> 0.8 for squat), and `analyze_s` for the 720p pushup pushup_e18a31d1 on class B 94.5-102.5 -> 55.0-61.9.
- **Results did not change.** Flags off: all 8 summaries are byte-identical to the base image's. Flags on: `compare.py` passes on all 8 in the prod image, and all 27 Cloud Run responses match the base run of their host class under the strict gates (50 of 50 responses across base/off/on classified, 0 matched neither class).
- **Output videos pass a new artifact gate on all 8 fixtures**: H.264, yuv420p, moov before mdat, same frame count / size / fps as the old upload, every plane SSIM >= 0.9715 against the old upload, 4-19% smaller. Against a lossless render of the same frames the new 720p pushup video is marginally closer than the old one (SSIM 0.9795 vs 0.9784, PSNR 39.78 vs 39.64 dB).

## What is NOT covered

- **No on-run landed on a class-A host.** Both flags-on instances gave class-B results. Nothing in the change is host dependent, but it was not observed there.
- **Old APK web assets.** The proof that pushup/situp clips are never shown is from the current frontend source (`perf/upload-analysis-2026-11-13` and `feat/100-club` are identical in the three files). An older build that still showed per-rep cards for those lifts would fall back to seeking in the annotated video, because `hasClips` is also true when `best_time_s` and `worst_time_s` exist. I did not run an old build.
- **Rendered in a browser: not done.** The gate is ffprobe + SSIM + three side-by-side crops I looked at (old | new | lossless: same frame, same overlay, same colours). No file was played in Chrome or on a phone.
- **Squat on the laptop shows no gain** (wall 0.91x-0.96x, pose noise of +-15% under a load average of 50 swamps a 5 s effect). The squat claim rests on Cloud Run only (n=3 vs n=2).
- **Plank fallback branches** (ffmpeg dies mid-render, zero sampled frames) are code-read only; the plank happy path has a unit test and 4 Cloud Run runs.
- **Unit tests ran on the laptop venv** (Python 3.13, ffmpeg 9), not inside the image (Python 3.10, Debian ffmpeg). The image path is covered by the 8-fixture runs, not by pytest.
- **The ~9 s upload stall** (4 of 50 perf requests: 2 off, 2 on; 1 of the last 30 prod lifting requests, 2026-11-12) is not caused by the flags and not explained. It is inside `upload_from_filename`.
- `run_local.py` does not run the Flask route. The route branch is covered by two new tests in `tests/test_service_app.py` and by the Cloud Run runs.

## Env flags

```
SKIP_METRIC_CLIPS_FOR=pushup,situp
LIFT_VIDEO_ENCODER=ffmpeg
```

Both are read at call time. Unset, empty, or `LIFT_VIDEO_ENCODER=cv2` is the old code path. They are independent; either can be on alone.

## Why skipping pushup and situp clips is safe

- `VideoPlayer.tsx:763-773`: for `usesSetSummary` lifts (pushup, situp) the cards are one card built from `summarizeSet(report.rep_metrics)`.
- `lib/setSummary.ts:124-138`: a `SetMetric` has no `clip_url`, `best_time_s` or `worst_time_s`, so `hasClips` (`VideoPlayer.tsx:809`) is false and the `<video>` at 856-873 never renders.
- `VideoPlayer.tsx:933`: the rep-by-rep table is hidden for the same lifts, and it shows no clips anyway.
- No other reader: `grep clip_url` over `frontend/src` finds only the leaderboard row field (the annotated video) and `types.ts`; the backend never reads a metric `clip_url` and only logs `stages` generically.
- `git diff HEAD feat/100-club` is empty for `VideoPlayer.tsx`, `lib/setSummary.ts`, `SetStats.tsx`, `lib/types.ts` (read at 668529b, 2026-11-13 22:07).
- Squat, deadlift, bicep curl and bench keep per-rep cards with clips, so they are not in the flag.

## What changed in the engine

- `src/lifting/pipeline.py`: `_metric_clips_skipped(lift_type)` gates Pass 3 and logs `METRIC_CLIPS skipped lift_type=...`.
- `src/lifting/video_writer.py` (new): `FfmpegH264Writer`, a `write/release/isOpened` writer that pipes bgr24 into `ffmpeg -c:v libx264 -preset veryfast -crf 25 -pix_fmt yuv420p -an -movflags +faststart` (the same settings as `_reencode_h264`, plus faststart). It pads odd sizes to even, keeps stderr in a temp file, and `release()` returns True only for rc 0 with at least one frame. Successful files are remembered in-process.
- `service/app.py`: `_reencode_h264` returns the input untouched when the writer already produced it (`H264_DIRECT already H.264`). The route and `_publish_metric_clips` are unchanged; clips upload from the path they were written to.
- `_render_output_video`, `_render_metric_clips`, `plank_analyzer.analyze_plank`: use the writer when the flag is on. If ffmpeg is missing they use cv2 from the start. If ffmpeg fails mid-stream the annotated video is re-rendered through cv2, and a failed clip gets no `clip_url` (the page then seeks in the annotated video).
- Clips only: ffmpeg starts from the capture size before the first frame, the next rep's encoders start while the current rep renders, and a rep's encoders flush while the next rep renders. Each is capped at `-threads 2`.
- Response shape: top-level keys and `stages` keys are identical on and off (`reencode` and `clips` stay, at 0.0). The key-path diff of every report passes: nothing added, nothing missing except `rep_metrics[i].metrics[j].clip_url` on pushup and situp (96, 104, 72, 64, 60, 28 paths), and squat keeps all 48.

## Gates and proof

All run on outputs of the prod image with the worktree mounted (`run_prod_image.sh`, code-hash guard), flags off = A, flags on = B. Raw lines: `exp-non-pose/image-gates.txt`.

| gate | result |
|---|---|
| A summary vs `base-image/*.summary.json` | byte-identical, 8 of 8 |
| B `compare.py` vs base image (strict) | pass, 8 of 8 |
| B key-path diff | pass, 8 of 8 |
| B annotated video artifact gate vs A | pass, 8 of 8; min plane SSIM 0.9786-0.9848; bytes -3.8% to -19.2% |
| Cloud Run responses vs same-class base reference | off 23 of 23, on 27 of 27 |
| Cloud Run artifact gate (downloaded uploads) | pass: annotated squat, pushup_e18a31d1, situp_667a8480 and the 4 rep-1 squat clips |
| flag really on, laptop | A logs: 0 `H264_DIRECT`/`METRIC_CLIPS skipped` lines and 29-105 ffmpeg re-encodes per rep-lift fixture; B logs: 0 re-encodes, no `clips/` dir for pushup and situp, squat uploads 48 clips with 0 re-encodes |
| flag really on, Cloud Run logs | `np-on2`: 0 `Re-encoding to H.264`, 255 `H264_DIRECT wrote`, 9 `METRIC_CLIPS skipped` at count time, no WARNING lines; `np-off`: 539 re-encodes, 0 of the others |
| GCS | `lifting/perf-bench-pushup_e18a31d1-np-on-r1/` and the situp one hold only `annotated.mp4` + `summary.json`; the squat one has 48 clips, same as off |

The two gates I wrote were mutation-checked, and both first versions had a hole:
- `artifact_check.py`: dropped frames, mp4v codec, no faststart, yuv444p, 30 fps and a horizontal flip all FAIL. A 40 degree hue shift first PASSED (ffmpeg's `All` SSIM is luma weighted); the gate now takes the worst plane and it fails at 0.9227 < 0.95. Pairing frames by timestamp also under-reported old vs new as 0.90, because the two muxers' timestamps differ by microseconds; frames are now paired by index.
- `keydiff.py`: a report missing `form_score`, or missing `clip_url` without `--expect-no-clips`, FAILS. One metric losing `status` first PASSED (list indexes were collapsed); paths are now indexed and it fails.

Flags off equals base timing: on the laptop round 2 the non-pose seconds are 105.2 (image code) vs 101.2 (worktree, off) on pushup_e18a31d1 and 100.8 vs 95.9 on situp_667a8480. On Cloud Run class A, flags off vs base is 135.6 vs 147.2, 159.5 vs 166.5, 213.7 vs 213.6, 140.1 vs 148.3 (pushup_e18a31d1, situp_16b6ca35, situp_667a8480, situp_c9dec98b).

## Timing detail

Cloud Run, per fixture and class, base / off / on with stage means: `exp-non-pose/cloudrun/summary.md` (from `classify.tsv`, 50 rows). Instances: base 222b98 (A) and b747c2 (B); off 773106 (A) and 2f0ea0 (B); on c138d5 and fd9e08 (both B).

Emulated prod image on the laptop, 4 CPUs, sequential base, A, B. wall / pose / non-pose seconds; sibling agents ran containers at the same time, so pose moves by up to 45% between runs and only the non-pose column is worth reading:

| fixture | round | image code | off (A) | on (B) | non-pose on vs off |
|---|---|---|---|---|---|
| pushup_e18a31d1 | 1 | - | 142.8 / 56.5 / 86.3 | 95.8 / 82.0 / 13.8 | -84% |
| pushup_e18a31d1 | 2 | 195.1 / 89.9 / 105.2 | 182.4 / 81.1 / 101.2 | 81.2 / 67.4 / 13.8 | -86% |
| situp_667a8480 | 1 | - | 312.2 / 194.1 / 118.1 | 228.6 / 200.8 / 27.7 | -77% |
| situp_667a8480 | 2 | 256.9 / 156.0 / 100.8 | 274.8 / 178.8 / 95.9 | 168.9 / 145.0 / 24.0 | -75% |
| squat_f47a8848 | 1 | - | 54.3 / 40.5 / 13.7 | 56.2 / 47.5 / 8.7 | -37% |
| squat_f47a8848 | 2 | 67.0 / 51.8 / 15.3 | 62.2 / 44.3 / 18.0 | 68.6 / 50.9 / 17.7 | -1% |
| pushup_3c66c85e | 1 | - | 141.2 / 97.1 / 44.1 | 106.3 / 100.2 / 6.0 | -86% |
| pushup_97b4aaf2 | 1 | - | 150.4 / 64.7 / 85.7 | 78.8 / 61.9 / 16.9 | -80% |
| situp_16b6ca35 | 1 | - | 194.2 / 157.5 / 36.7 | 173.8 / 167.5 / 6.3 | -83% |
| situp_c9dec98b | 1 | - | 178.1 / 122.7 / 55.4 | 131.2 / 115.6 / 15.6 | -72% |
| plank_9600f455 | 1 | - | 85.9 wall | 80.7 wall | - |

All rounds: `exp-non-pose/image/summary.md`.

## What I tried, including what failed

1. **Clip gate.** Worked first time. It is the larger half of the pushup win: the engine render (8-42 s in the profile) and the `clips` stage (6-23 s) both go.
2. **ffmpeg writer, started on the first frame.** Correct but slow for clips: the first write of each clip blocked until that ffmpeg had started, four in series per rep. In the emulated image the squat clip render went 2.4 s -> 10.3 s.
3. **Start from a size hint, pre-start the next rep, flush in the background.** Squat clip render in the emulated image came down to 6.8-7.9 s, still above the old 3.3-4.5 s there, because 48 process starts are very expensive under emulation. On Cloud Run the squat `analyze_s` is level (39.1 on vs 40.0 off, class B) and the saving is the service stages: `clips_s` 4.1 -> 0.8 and `reencode_s` 0.7-2.9 -> 0. So for clips the writer saves the re-encode, not the render.
4. **Not built: annotated upload on a thread while clips publish.** `upload_s` is 0.14-0.34 s, and with the flags on there is no `reencode` or clip work left to overlap with.
5. **Not built: model or landmarker init per request, tracking/smoothing for situp.** The profile has init under 0.8 s and tracking + smoothing + scoring under 1.5 s on every fixture.
6. **Not built: lower annotated render resolution.** It would change what the athlete sees, which the brief rules out. It is a product decision; the 720p annotated render is now the largest non-pose cost left.
7. **Native laptop A/B is useless for encode timing.** The venv's cv2 opens `avc1` (VideoToolbox) where the image falls back to `mp4v`, so the old path is a different codec there. I used native runs only as smoke tests.

## Tests

`tests/test_lifting/test_metric_clip_gate.py` (4), `tests/test_lifting/test_video_writer.py` (14), `tests/test_service_app.py` (+2 for the route and the clip publisher). `tests/test_lifting` + the three service/summary files: 257 passed, 2 skipped (missing fixture videos, as at base).

Mutation check, each restored from an in-memory copy and re-read:

| mutation | killed by |
|---|---|
| clip gate always False / always True | `test_a_listed_lift_type_gets_no_clips...` / the three "keeps its clips" tests |
| service never skips the re-encode | `test_annotated_video_is_h264_directly_and_the_service_skips_the_reencode` |
| failed encode still marked ready | `test_a_failed_encode_is_reported_and_never_marked_browser_ready` |
| flag ignored (always ffmpeg) | `test_the_flag_is_off_by_default` |
| no cv2 fallback | `test_annotated_render_falls_back_to_cv2_when_ffmpeg_dies` |
| no even-size pad | `test_odd_frame_sizes_are_padded_to_even` |
| clip_url set although the encode failed | first SURVIVED; added `test_a_clip_whose_encode_failed_gets_no_clip_url`, now killed |
| zero-frame pre-started writer reports ok | `test_a_prestarted_writer_that_got_no_frames_is_not_browser_ready` |
| wrong size hint not corrected | `test_a_wrong_size_hint_is_corrected_by_the_first_frame` |
| pre-start opens the wrong rep / every other clip frame dropped | `test_metric_clips_are_h264_directly_and_keep_their_rep_frames` |
| plank ignores the writer / writes at source fps | `test_plank_overlay_is_h264_directly_at_the_sampled_rate` |

`tests/test_service_app.py::test_metric_clips_are_reencoded_uploaded_and_rewritten` failed at `93378b0` (its fake lacked the `threads` argument the service passes); fixed in the same commit.

## Risks for the integrator

- **One ffmpeg process per clip and per annotated video now lives during `analyze`**, up to 12 at once for a squat (current, next and flushing rep, 4 each). Memory was not measured on Cloud Run; the instance has 8 GiB and no request failed.
- **A hung ffmpeg blocks a write with no timeout** (only `release()` has a 120 s limit); gunicorn's 870 s timeout is the backstop, as it is for the pose pass today.
- **The frame rate is now the source's exact rate** (for example 10220/341 instead of cv2's rounded 2997/100). Duration differs by under 1 ms; frame count is identical.
- **The "already H.264" memory is per process.** It works because gunicorn runs one worker and the pipeline runs in-process. A move to a subprocess pipeline would silently bring the re-encode back (slower, not wrong).
- **If the clip gate is merged without the frontend ever changing, nothing breaks; if someone later shows per-rep cards for pushup or situp**, the clips will be missing and the page falls back to seeking in the annotated video.

## Resources created (all on the throwaway service, none serving users)

- Image `gcr.io/toms-gym/bowling-service:perf-nonpose-ad232be` (digest `sha256:e4c479ac...fa33c`).
- Revisions on `bowling-service-perf`, all 0% traffic: `bowling-service-perf-np-off` (tag `np-off`, prod env), `bowling-service-perf-np-on2` (tag `np-on`, prod env + the two flags), and the broken `bowling-service-perf-np-on` (no tag; `GCS_BUCKET_NAME` holds a comma-joined string). The exported specs of the first two differ from `perf-base` only in the image digest and, for `np-on2`, the two env vars (`exp-non-pose/cloudrun/revisions/`). I deployed `np-off` last so the service's latest template carried no experiment flags.
- GCS: engine outputs under `lifting/perf-bench-*-np-off-r*` and `lifting/perf-bench-*-np-on-r*`.
- Prod `bowling-service` read back after the runs: `bowling-service-00053-fxm`, generation 55, 100%, unchanged.
- Local, outside any repo: `/Users/toka/code/bowling-app/perf-out-non-pose/` holds the rendered videos of real users (not committed anywhere).

## Files

- `exp-non-pose/harness/`: private copies of `run_local.py` (adds the uploaded-file record, re-encode counter, kept annotated video and rep-1/2 clips), `run_local.sh`, `run_prod_image.sh`, `compare.py`; new `artifact_check.py`, `keydiff.py`, `classify_cloudrun.py`, `summarize_cloudrun.py`, `summarize_image.py`, `sweep_image.sh`, `ffmpeg_lossless.py`.
- `exp-non-pose/cloudrun/`: bench outputs per tag (`np-off-all`, `np-off-key`, `np-off-plank`, `np-on-all`, `np-on-key`, `np-on-plank`), `classify.tsv`, `summary.md`, `revisions/`.
- `exp-non-pose/image/`: summaries and timings per config and round, `sweep.progress`, `summary.md`. `exp-non-pose/image-gates.txt`.
