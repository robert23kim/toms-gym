# Perf candidate: pose-parallel + non-pose combined (2026-11-14)

**Verdict: ship.** On Cloud Run the combined candidate cut the summed per-fixture job time from 953 s to 311 s (3.07x, -67%). That comes from an alternating A/B in one sitting, n=2 per tag. Every fixture matches base under strict `compare.py` on the same host class: class A in the A/B, class B on a second revision of the same image.

Not covered: no output was played in a browser or on a phone; nothing was deployed to `bowling-service`; the engine branch is local and not pushed.

## What was built
- Engine worktree `/Users/toka/code/bowling-app/perf-engine`, branch `perf/engine-2026-11-13`:
  - `66b47de`: merge of `perf/exp-pose-parallel` (47cb245).
  - `f198bac`: merge of `perf/exp-non-pose` (ad232be).
  - The merges had no conflicts and no shared files. Pose workers use the `spawn` context, and the ffmpeg encoders open only in pass 2, after pose. Every flag is still default OFF in code.
- Tests: the touched suites gave 47 passed, 2 skipped; `tests/test_lifting` gave 268 passed, 4 skipped. The skipped tests need video fixtures.
- Image: `gcr.io/toms-gym/bowling-service:perf-cand-f198bac`, digest `sha256:42f105ddd88c070a6a92e52ac2eb290a1a0b9f8783987e7615c86bf8af596e11`. Built by Cloud Build from the clean worktree (porcelain 0).

## Env to deploy (on top of the live prod env)
```
LIFT_POSE_WORKERS=4
SKIP_METRIC_CLIPS_FOR=pushup,situp
LIFT_VIDEO_ENCODER=ffmpeg
```
- The comma in `SKIP_METRIC_CLIPS_FOR` breaks gcloud's default parser, so use a custom delimiter.
- Prod recipe: `gcloud run services update bowling-service --region us-east1 --project toms-gym --image gcr.io/toms-gym/bowling-service:perf-cand-f198bac --update-env-vars '^@^LIFT_POSE_WORKERS=4@SKIP_METRIC_CLIPS_FOR=pushup,situp@LIFT_VIDEO_ENCODER=ffmpeg'`. Never use `deploy.sh`.
- **Before deploying, re-check the prod revision.** At 2026-11-14T06:01:19Z, after the whole bench, prod was still `bowling-service-00053-fxm` (100%), which runs base 93378b0. If another session has since deployed an engine change, rebase `perf/engine-2026-11-13` onto that change and rebuild.
- **Rollback:** unset the three flags (the old code path in the same image), or roll back to the 00053 digest.

## Equivalence
| check | result |
|---|---|
| Emulated prod image (amd64, worktree mounted, code hash checked), prod env + 3 flags, vs `base-image` | 8/8 strict PASS |
| Flags live in the image runs | `LIFT_POSE_PARALLEL` line on 7/7 rep fixtures and absent on plank; `METRIC_CLIPS skipped` on 6/6 pushup and situp; reencode 0.0 |
| Artifact gate, image annotated videos vs the flags-off image outputs | 8/8 PASS: H.264 yuv420p faststart, same frames, fps and size, min plane SSIM 0.9786-0.9848, 4-19% smaller |
| Artifact gate, squat clips | 4/4 PASS |
| Comparator mutation check | flipping one situp rep across the 70 clean line gives exit 1; unmutated gives exit 0 |
| Cloud Run A/B sitting (`perf-cand`, 1 instance, class A on all 16 responses) | Every cand response matches the class-A reference. Every same-class cand-vs-base pair in the sitting matches: pushup x3, situp_667a8480, situp_c9dec98b |
| Cloud Run `perf-cand2` (same image and spec, 2 instances, class B on 8/8) | Matches the class-B base instance from the A/B sitting on 9/9 pairs (squat x2, pushup x3, situp_16b6ca35 x2, plank x2), and the class-B reference `cloudrun-base/*.r2` for situp_667a8480 and situp_c9dec98b |
| Responses matching neither class | 0 of 24 |

The direct cand-vs-base DIFFs in `cloudrun/summary.md` are all cross-class pairs (cand on A against base instance `56f1be` on B). That includes the plank DIFF, 82.79 vs 82.19 s hold. The same split shows up between two unchanged base instances.
- Base instance `56f1be` is B on every fixture, and base `eb01ce` is A on every fixture. One class explains every response of each instance.
- So the plank 0.6 s is the host, not the code. Each output is identical to its own class's reference.

Flags live on Cloud Run (revision logs):
- `perf-cand`: 15 parallel lines (7 rep fixtures x 2, plus the warm-up), 12 clip skips, 0 `Re-encoding to H.264`, 161 `H264_DIRECT wrote`, 0 Tracebacks.
- `perf-base` in the same window: 0, 0, 1005 and 0.
- `perf-cand2`: 8 parallel lines, 6 clip skips, 0 re-encodes.

## Speed (Cloud Run `processing_time_s`, seconds)
| fixture | base, class A (A/B sitting) | cand, class A (A/B sitting) | base, class B (A/B sitting) | cand2, class B (after, n=1) | same-class speedup |
|---|---|---|---|---|---|
| squat_f47a8848 | - | 23.2, 20.9 | 44.1, 44.8 | 16.7 | B 2.7x |
| pushup_3c66c85e | 89.9 | 26.6, 27.6 | 74.4 | 18.6 | A 3.3x, B 4.0x |
| pushup_97b4aaf2 | 132.8 | 24.6, 25.4 | 112.9 | 28.9 | A 5.3x, B 3.9x |
| pushup_e18a31d1 | 145.8 | 30.4, 32.4 | 132.5 | 26.1 | A 4.6x, B 5.1x |
| situp_16b6ca35 | - | 52.5, 52.2 | 143.6, 142.2 | 37.7 | B 3.8x |
| situp_667a8480 | 223.7, 226.5 | 62.9, 61.4 | - | 51.6 | A 3.6x |
| situp_c9dec98b | 153.1, 155.5 | 45.4, 46.9 | - | 37.9 | A 3.3x |
| plank_9600f455 | - | 39.5, 49.1* | 42.8, 41.5 | 35.8 | B 1.18x |

- Sum of per-fixture means in the A/B: base 953.0 s, cand 310.7 s. That is 3.07x, against a 15-23% (worst +33%) instance spread.
- \*Plank cand r2 includes a 9.75 s `upload` stall. That is the unexplained ~9 s stall the non-pose report saw on both flag states and on prod; 1 of 24 candidate responses hit it here.
- Plank in the A/B is 0.95x on the mean, but it pits a class-A candidate against a class-B base, and class B is the faster class here. Without the stall, cand analyze is 38.8 s against base analyze + reencode of 42.0 s. On the same class (cand2 vs base B) plank is 1.18x.
- No fixture got slower beyond the spread.
- Cand stages: `reencode` 0.0 everywhere, `clips` 0.0 on pushup and situp, 0.7-0.85 s on squat.

**The two changes add up on 720p pushups.** The per-rep clip render that `SKIP_METRIC_CLIPS_FOR` removes lived inside `analyze`. For pushup_e18a31d1:
- base analyze: 102.5 s (class B, baseline) and 122.7 s (class A, today)
- minus the clip render (about 42 s)
- minus the pose saving (about 26 s at 4 workers)
- = about 30-50 s left, against 26-32 s observed.

**Memory:** Cloud Monitoring `container/memory/utilizations`, p99 per minute, max over the window.

| revision | max | points |
|---|---|---|
| `perf-cand` | 27% of 8 Gi (2.16 GiB) | 44 |
| `perf-base` | 16% | 44 |
| `perf-cand2` | 14% | 4 (metric lag) |

The 60 s sampling can miss short peaks. No OOM, kill or worker-timeout lines appeared in any revision log.

## Risks carried into prod
- Pushup and situp results lose `clip_url`. I re-checked this against the frontend source at `feat/100-club` 9ebbd3d, which is newer than the non-pose check, with a read-only `git show`:
  - `VideoPlayer.tsx` shows these lifts as one "Whole set" card built by `summarizeSet`. Its `SetMetric` has no `clip_url` and no best/worst times, so `hasClips` (line 840) is false.
  - The rep-by-rep table is hidden for them (`!usesSetSummary`).
  - Every other `clip_url` reader in `frontend/src` is the leaderboard row's annotated-video field.
  - An old APK build was not checked. It would fall back to seeking in the annotated video.
- The rest are unchanged from the part reports:
  - Multi-person videos gain less from pose-parallel.
  - The chunk sync rule is empirical.
  - A hung ffmpeg has no per-frame timeout; gunicorn's 870 s is the backstop.
  - The frame rate is now the exact source rate.
  - The encoder flag alone is thinly tested, so enable all three together.
  - Sized for `containerConcurrency` 1.
- Do not combine with `num_poses=1` without re-testing.

## Left behind (throwaway service `bowling-service-perf` only)
- Revisions `bowling-service-perf-perf-cand` (tag `perf-cand`) and `-perf-cand2` (tag `perf-cand2`), both 0% traffic. `perf-base` still has 100%. The service template now carries the candidate image and flags, so later deploys need an explicit `--image` and `--set-env-vars`.
- Image tag `perf-cand-f198bac`.
- GCS outputs under `lifting/perf-bench-*-perf-{base,cand}-ab-r*` and `lifting/perf-bench-*-perf-cand2-r1`.
- Rendered videos of real users are in `/Users/toka/code/bowling-app/perf-out-candidate/image-on/`, outside any repo and not committed.

## Files
- `candidate/image-on/`: summaries, timings, compare results, progress and the artifact gate.
- `candidate/cloudrun/`:
  - `ab/` (per-tag responses, `bench.tsv`, `instances.tsv`), `summary.md` (direct cand-vs-base compare with classes) and `ab.log`.
  - `cand2/` plus `cand2-classify.tsv` and `cand2-vs-baseB.txt`.
  - `logs-*.txt`, `memory*.txt` and `rev-perf-cand.export.yaml`.
- `harness/bench_ab.sh` (alternating A/B; keeps the URL guard, health canary, warm-up, fresh token and `perf-bench-` ids), `harness/summarize_ab.py` and `harness/memq.py`.
