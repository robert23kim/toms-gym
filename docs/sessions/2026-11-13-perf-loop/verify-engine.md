# Adversarial verify: engine candidate f198bac (2026-11-14)

**Verdict: pass, with objections.** Same-class outputs are bit-identical, and the timing holds up.
- Every candidate Cloud Run response is bit-identical to an old-code-path response from a host of the same class. The only difference is that per-metric `clip_url` is missing for pushup and situp. I checked this leaf by leaf with NaN == NaN, on 24 saved pairs plus 4 runs of my own.
- The 3.07x claim is reproduced exactly from the `ANALYSIS_STAGES` log lines.

**What the claim gets wrong:** "the same results as the base on every fixture" is **false as a direct A/B statement**.
- In the sitting, 5 of 8 fixtures DIFF cand-vs-base. That includes a `clean_split` (pushup_e18a31d1 rep 24: 70.10 vs 67.73) and a rep count (pushup_97b4aaf2: 25 vs 26).
- Every one of those DIFFs is reproduced **base-vs-base** across Cloud Run instances, with the same gates failing.
- So the move between clean and sloppy comes from the host, not from the candidate.
- **The unchanged prod engine already scores the same video differently depending on which instance it lands on.** That is live on the 100 Club today, and it is independent of this change. In my own run, the base plank landed on a class-B host and DIFFs from prod (82.19 vs 82.79 s hold).

Not covered:
- No browser or phone playback (ffprobe only).
- An old APK reading a pushup or situp result without `clip_url`.
- Any 1080p, 90°-rotated (portrait) or multi-person video on Cloud Run.
- Cloud Run memory for a 3-minute 1080p clip. I measured that on the laptop, natively.

## Checks I ran myself
| check | result |
|---|---|
| compare.py on every saved base x cand pair in the A/B (`candidate/cloudrun/ab`) | MATCH squat, situp_667a8480, situp_c9dec98b (4/4 each). Cross-instance DIFFs on pushup x3, situp_16b6ca35, plank |
| Exact leaf diff (`verify-engine/rawdiff.py`, only `.clip_url` may be missing, NaN==NaN) on the same-class pairs | 0 differing leaves and 0 non-`clip_url` missing keys on all 22 rep and plank pairs (`verify-engine/pairs.txt`) |
| Same pairs, base vs base across instances | DIFF on all 5 cross-class fixtures with the same gates: pushup_3c66c85e (metric_status, score_drift), pushup_97b4aaf2 (reps, grade...), pushup_e18a31d1 (**clean_split**, grade...), situp_16b6ca35 (reps), plank (plank_hold) |
| Squat on class A | cand A vs flags-off `np-off-key/squat.r2` (instance 773106, A): 0 non-`clip_url` leaves differ. No class-A **base-image** squat exists on Cloud Run |
| Could the comparison fail? | Files differ (cmp at byte 124; `processing_time_s` and `stages` differ, e.g. 74.4 vs 26.64, `reencode` 1.09 vs 0.0). No duplicate md5 among the 41 response files |
| compare.py mutation check (my own) | Unmutated exit 0. Exit 1 for each of: one rep 75.0 -> 69.9, a rep dropped (with and without `total_reps`), a metric status flipped, a rep start moved +0.3 s, plank hold +0.6 s. Within tolerance (score -1, hold +0.4) exit 0. The tolerance hides nothing here: same-class pairs are exact |
| Image provenance | Revisions `perf-cand` and `perf-cand2` both run digest `42f105dd...`. The Cloud Build source tarball's `src/` and `service/` are identical to `git archive f198bac` (156 py files). The canary hash for parallel.py matches f198bac and differs from 9fe6d63. Pinned deps match the base build (mediapipe 0.10.30, numpy 2.2.6, cv2 5.0.0.93, scipy 1.15.3) |
| Flags live | Revision env: `LIFT_POSE_WORKERS=4`, `SKIP_METRIC_CLIPS_FOR=pushup,situp`, `LIFT_VIDEO_ENCODER=ffmpeg` on top of the prod env, which equals 00053's 4 vars. Logs 05:00-06:05Z: perf-cand has 15 parallel lines, 12 clip skips, 0 re-encodes and 0 Tracebacks; perf-base has 0, 0, 959 re-encodes and 0. My run (06:06Z on): perf-cand has 4 parallel lines, 2 skips, 0 re-encodes and 101 `H264_DIRECT`; perf-base has 0, 0, 208 and 0 |
| Timing from `ANALYSIS_STAGES` (`verify-engine/stages-logs.tsv`) | Sum of per-fixture means: base 953.0 s, cand 310.7 s, 3.07x, identical to the claim. Timestamps show strict alternation, base-then-cand in round 1 and cand-then-base in round 2 |
| My own run, fresh `perf-bench-<fx>-{cand,base}-verify-r1`, cand then base per fixture | See below |
| Flag-off on the merged code (native laptop, 93378b0 tree vs f198bac, flags unset) | squat and pushup_97b4aaf2: summary JSON **byte-identical**, same clip count (52, 100), annotated.mp4 byte-identical. **Plank not run to completion.** The base-tree plank (heavy model, `PLANK_POSE_WORKERS=4`) was still churning workers after 20 min at laptop load ~9.7, so I stopped it. The plank flag-off change is verified by reading only: `open_h264_writer` returns None, so the code falls back to `cv2.VideoWriter`, and `release() is False` is never true for cv2 |
| Engine tests (touched suites) | 47 passed, 2 skipped (real-MediaPipe opt-in); worktree porcelain 0 |

### My own Cloud Run run (n=1 per fixture, `verify-engine/own-run-compare.txt`)
| fixture | cand inst/class, s | base inst/class, s | cand vs prod JSON | note |
|---|---|---|---|---|
| squat_f47a8848 | 8eeb43 A, 19.78 (after a 29.0 warm) | fa6bb5 B, 52.27 | MATCH (compare.py) | bit-identical to the class-A flags-off response; base bit-identical to the sitting's base B |
| pushup_e18a31d1 | 8eeb43 A, 29.17 | df31ca A, 153.31 | **bit-identical** except clip_url | 5.3x same class |
| situp_667a8480 | 8eeb43 A, 74.65 (includes a 9.87 s upload stall) | df31ca A, 227.45 | **bit-identical** except clip_url | 3.0x same class. Sync offset 21 with a 48-frame extension: the non-trivial splice ran and still matched |
| plank_9600f455 | 8eeb43 A, 39.75 | fa6bb5 B, 52.54 (includes a 9.86 s upload stall) | **bit-identical** (prod stores NaN as null) | base DIFFs from prod (B host). The stall also hits base, so it is not the candidate |

### Artifacts (ffprobe on the GCS outputs from my run)
- All candidate annotated outputs are h264 High, yuv420p, with **moov before mdat**.
- Base outputs were moov-after-mdat. The candidate is better there.
- Frame counts are identical to base (767, 1022, 1976, 1293), and durations are within 2 ms.
- The plank (sampled-fps writer, no size hint) is 1293 frames at 86.47 s on both.
- The squat rep1 clip is h264, yuv420p, faststart, 46 frames on both.
- The candidate files are 8-20% smaller.

## Diff review (`git diff 93378b0..f198bac`)
- **Flag-off path.**
  - `open_h264_writer` returns None unless `LIFT_VIDEO_ENCODER=ffmpeg`.
  - `release() is False` is never true for cv2, which returns None.
  - `SKIP_METRIC_CLIPS_FOR` unset gives the empty set.
  - `LIFT_POSE_WORKERS` unset gives 1, which is sequential.
  - The `estimate_frame` refactor (`_select_and_smooth`) has the same logic, and the empty-pose case returns the same empty Skeleton.
  - Proven byte-identical natively on squat and pushup.
- **The bowling path is touched, but inert.** `/analyze` (bowling) goes through the edited `_reencode_h264`, which now consults `is_browser_ready`.
  - That set is filled only by `FfmpegH264Writer.release()`, which the bowling pipeline never uses, so bowling always re-encodes as before.
  - The `clip_file` and `final_video` callers handle a returned input path.
- **Chunk edges.**
  - Splice records come from MediaPipe outputs that are bit-equal on 5 consecutive frames (digest = frame crc + every float of every pose).
  - Before a sync the left chunk extends, and a chunk that never syncs is dropped. Worst case is sequential output.
  - The remaining risk is MediaPipe hidden state that does not show in the outputs. It is empirical, as the report says.
  - Evidence: 7 rep fixtures x 3 boundaries on both host classes, all bit-identical, including the 21-frame late sync. A rep near a boundary cannot shift unless that hidden-state assumption fails.
  - No 90° portrait, 1080p or multi-person fixture ran on Cloud Run.
  - `CAP_PROP_FRAME_COUNT` over- or under-count is handled: the last chunk reads to EOF, and an empty chunk is dropped (unit-tested).
- **Memory.** Native arm64 on a 180 s 1080p30 clip (5400 frames, the pushup_e18a31d1 fixture looped and upscaled), whole `analyze_lift`, all three flags, RSS of the process tree:
  - pushup: **1.83 GiB peak** (4 workers).
  - squat: **1.83 GiB peak** with **12 concurrent ffmpeg** (current + prestarted + flushing reps) and 508 clips.
  - Pose stage alone: 1.49 GiB.
  - Records grow about 5 KB per pose per frame, so 5 poses x 5400 frames adds about 140 MB.
  - Cloud Run fixtures max out at 27% of 8 Gi. Large headroom, but Cloud Run bytes at 1080p were not measured.
- **Temp files.**
  - Everything lives in the request's `mkdtemp`, which the `finally` removes.
  - ffmpeg stderr goes to a `TemporaryFile`, closed in `release()`.
  - **Leak path (non-blocking):** an exception mid-`_render_metric_clips` leaves the current, prestarted and flushing ffmpeg writers unreleased. Only GC of the Popen stdin ends them, inside a long-lived gunicorn worker. The old cv2 writers had the same exposure but no child processes.
  - `_browser_ready` grows by one path per encoded file for the process lifetime (small).
- **Response keys.**
  - Top-level keys are unchanged (`annotated_video_url`, `summary_url`, `report`, `stages`, `processing_time_s`), and `lifting_processor.py` reads only those.
  - Within the report, only `rep_metrics[].metrics[].clip_url` goes missing, and only for pushup and situp.
  - On `feat/100-club` 9ebbd3d (read-only `git show`), `VideoPlayer.tsx` `usesSetSummary` is pushup or situp, so their rep table and clips are hidden.
  - The leaderboard `clip_url` is the annotated video (`challenge_leaderboard._clip_url`, `consistency.py`).
  - The backend maps `Pushup` to `pushup` and `Situp` to `situp`, so the skip matches prod lift types.
- `clip_keys` is now a hard-coded copy of the renderer keys. If someone adds a renderer without adding its key, that clip is silently dropped (non-blocking).

## Objections (none blocks; carry them into the deploy decision)
1. Restate the equivalence claim as "bit-identical per host class". The direct A/B DIFFs, including the clean/sloppy flip, are pre-existing instance nondeterminism in prod. That deserves its own ticket for the live challenge.
2. Squat class-A equivalence rests on a flags-off response of the non-pose image, not the base image.
3. Plank has no shown speedup:
   - 0.95x in the A/B.
   - 1.18x same-class at n=1.
   - My run's 39.75 vs 52.54 is inflated by a base upload stall.
4. The ~9.8 s `upload` stall hit 2 of my 9 responses (cand situp, base plank). It is not caused by the candidate, but it is unexplained.
5. The `perf-cand` and `perf-cand2` specs carry an explicit `execution-environment: gen1` annotation that `perf-base` and 00053 lack. baseline.md says prod runs gen1, so this is probably equivalent, but I did not verify it.
6. The rollback (unset the flags in the same image) is verified natively only, not on Cloud Run: byte-identical on squat and pushup, and plank by reading only.

## State
- Prod `bowling-service` at 2026-11-14T06:33:40Z: `bowling-service-00053-fxm` at 100%. I made no change to prod.
- I made no revision or traffic change on `bowling-service-perf`.
- Left behind:
  - GCS: `lifting/perf-bench-*-{cand,base}-verify-r1/` (8 attempt prefixes, 35 objects).
  - `/Users/toka/code/bowling-app/perf-out-verify/`: real-user renders, the 180 s test clip and flag-off outputs. It is outside every repo, so never commit it.
- Files: `verify-engine/` holds `rawdiff.py`, `pairs.txt`, `stages-logs.tsv`, `flaglines.tsv`, `verify-logs.tsv`, `run.sh`, `run.log`, `run/*.json`, `own-run-compare.txt`, `mem_long.py`, `mem_full.py` and `flagoff.py`.
