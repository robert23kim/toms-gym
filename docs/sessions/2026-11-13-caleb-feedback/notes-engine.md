# C3 engine notes: squat counted 12, athlete did 10 (2026-11-13)

Verdict: reproduced (12 in the production image), cause found (the walk to and from the spot is counted),
fix committed and gives 10, **not deployable under the contract: no second squat clip with a known count exists**.
Nothing was pushed, built or deployed. The live attempt and the challenge rows were only read.

- Worktree: `/Users/toka/code/bowling-app/squat-engine`, branch `fix/squat-rep-count` off `feat/situp-config` (93378b0).
- Commit: `73852de fix(squat): do not count the walk to and from the spot as reps` (5 files, +195 -2).
- Artifacts (not committed): `docs/sessions/2026-11-13-caleb-feedback/c3/` (clip/, kp/, sheets/, prod/, prod-image/, before/, after/, tools/).

## 1. Reproduction

Clip: `c3/clip/squat12.MOV` (copy of `reporter-clip/squat12.MOV`): h264 480x360, 24 fps, 767 frames, 31.96 s, rotation -180.
Live result: `gsutil cp gs://jtr-lift-u-4ever-cool-bucket/lifting/f47a8848-.../summary.json c3/prod/summary.json` (read-only): total_reps 12, grade D.

| Where | Pose | Segmented | Counted | Note |
|---|---|---|---|---|
| Live prod summary.json | Linux | n/a | **12** | windows 2.88-4.75 ... 26.96-29.12 |
| Prod image `gcr.io/toms-gym/bowling-service:situp-13b49b5`, offline (`--network none`), shipped code | Linux (amd64 under emulation) | 13 | **12** | same 12 rep windows as live to 0.01 s; form scores within 0.01 |
| macOS native, `.venv`, branch code | macOS | 13 | 13 | one more walk-in stride survives |

Why macOS says 13 and prod 12 (observed, not inferred): both segment 13 cycles. On Linux the first one (frames 49-69) is
dropped by the existing valid-frame guard, log line `[ANALYZE] rep 0 SKIPPED: valid_ratio=0.48 < 0.5 (frames=21, valid=10)`.
On macOS the pose model sees the legs on a few more of those frames, so that stride is kept. Same cause, one more symptom.

Commands (PY = `/Users/toka/code/bowling-app/analysis-engine/.venv/bin/python`, E = the worktree, C3 = the c3 dir):

    $PY $C3/tools/extract_kp.py $E $C3/clip/squat12.MOV $C3/kp/caleb_squat12.npz          # macOS pose
    $PY $C3/tools/trace.py $E $C3/kp/caleb_squat12.npz squat --signal
    docker pull --platform linux/amd64 gcr.io/toms-gym/bowling-service:situp-13b49b5
    docker run --rm --platform linux/amd64 --network none -v $C3/clip:/c3/clip:ro -v $C3/tools:/c3/tools:ro -v $C3/kp:/c3/kp \
      --entrypoint sh gcr.io/toms-gym/bowling-service:situp-13b49b5 -c \
      'python /c3/tools/extract_kp.py /app /c3/clip/squat12.MOV /c3/kp/caleb_squat12_linux.npz; python /c3/tools/trace.py /app /c3/kp/caleb_squat12_linux.npz squat'

The counter: `EXERCISE_CONFIGS["squat"]` segments on `compute_knee_angle` (hip-knee-ankle) of one side (here `right`,
view auto-detected as `side` although the athlete faces the camera). `segment_reps` smooths (Savitzky-Golay, 11 frames),
finds extension peaks with `distance >= 0.5 s` and `prominence >= 20 deg` (`MIN_PROMINENCE`), adds boundary peaks, and
every peak-to-peak span up to 5 s is a rep. Nothing asks whether the span is a squat.

## 2. Which reps are real (eye count)

Sheets: `c3/sheets/caleb_0..5.jpg`, 4 fps, timestamp only on each tile (`tools/sheet.py`). Honest caveat: the engine
trace was on screen before I read the sheets, so the eye count was not blind.

What the video shows: 0-1.5 s empty room; 1.75-4.5 s he walks from the phone (on the floor) to his spot, back to the
camera; 4.75 s he turns and faces the camera; ten squats with bottoms at about 6.5, 8.9, 11.25, 13.6, 15.9, 18.0, 20.0,
22.0, 24.0, 26.0 s; 27.0-29.75 s he walks back to the phone; 31 s the phone is picked up.
**My eye count is 10. It agrees with the athlete.**

Per-rep verdict (prod image, shipped code; right knee angle in degrees):

| Prod rep | Window (s) | Bottom (s) | Knee min | Other knee at bottom | Feet travel (leg lengths) | Eye verdict |
|---|---|---|---|---|---|---|
| (skipped) | 2.04-2.88 | 2.54 | 143 | 174 | 0.45 | walk-in stride (already dropped on Linux by the valid-frame guard) |
| 1 | 2.88-4.75 | 3.79 | 116 | 177 | 1.82 | **walk-in stride, not a squat** |
| 2 | 4.75-7.38 | 6.54 | 76 | 81 | 0.10 | squat 1 |
| 3 | 7.38-9.83 | 8.92 | 76 | 84 | 0.02 | squat 2 |
| 4 | 9.83-12.42 | 11.25 | 92 | 95 | 0.03 | squat 3 |
| 5 | 12.42-14.67 | 13.62 | 85 | 97 | 0.03 | squat 4 |
| 6 | 14.67-16.92 | 15.83 | 98 | 103 | 0.02 | squat 5 |
| 7 | 16.92-19.08 | 18.04 | 102 | 105 | 0.02 | squat 6 |
| 8 | 19.08-21.04 | 20.04 | 95 | 100 | 0.02 | squat 7 |
| 9 | 21.04-22.96 | 22.00 | 92 | 94 | 0.02 | squat 8 |
| 10 | 22.96-25.12 | 24.08 | 85 | 91 | 0.02 | squat 9 |
| 11 | 25.12-26.96 | 26.08 | 99 | 99 | 0.02 | squat 10 |
| 12 | 26.96-29.12 | 27.71 | 130 | 173 | 1.82 | **walk-out stride, not a squat** |

Cause: not the camera angle. A self-filmed set starts and ends with a walk; each stride bends one knee by 50-64 deg,
well past the 20 deg rep prominence, so the walk-in and the walk-out are each a "rep". Every self-filmed squat upload
is exposed to this (0 to 2 extra reps, more on a longer walk). `trim_edge_outlier_reps` (the situp guard) cannot catch
it: the two strides last 1.88 s and 2.17 s, inside 0.5-2.5x the 2.2 s median rep.

## 3. Fix (commit 73852de)

`drop_walking_strides(reps, skeletons, side)` in `src/lifting/analysis/rep_segmenter.py`, enabled by
`EXERCISE_CONFIGS["squat"]["drop_walking_strides"]`, applied in `analyze_from_skeletons` after the view choice (next to
`trim_edge_reps`). A segmented rep is dropped only when **both** stride signs hold:

1. one knee bends alone: at the bottom (median over the bottom frame +/- 2) the other knee bends less than half as far
   as the counted knee (`WALK_OTHER_KNEE_SHARE = 0.5`);
2. the feet travel: the ankle midpoint moves more than a quarter of a hip-to-ankle length over the rep
   (5th-95th percentile range, `WALK_FEET_TRAVEL_LEGS = 0.25`).

Why both, measured on this clip (`tools/features.py`): the other-knee test alone is untested on a side-on far leg that
the pose model may leave straight; feet travel alone would drop a real squat whose window runs into the walk-off (left
side, 25.17-27.96 s: both knees at 98-102 deg, travel 0.86). Using the straighter leg as the signal does not work either:
it still dips to 154 deg on the walk-in, a 26 deg swing. Margins here (Linux and macOS keypoints): squats share >= 0.88 and
travel <= 0.10; strides share 0.05-0.18 and travel 0.41-1.82. An unseen other leg or unseen feet keep the rep.

Tests (written first, watched red at `assert 12 == 10`): `tests/test_lifting/test_squat_real_footage.py`, 8 tests.
Fixture `tests/fixtures/lifting/squat_walk_in_out_real_keypoints.npz` = the prod-image keypoints of this upload (pose
only, no imagery, neutral name; it is a friend's body pose in the engine repo: drop it if that is unwanted and the two
real-footage tests go with it). Real footage: 10 reps, each bottom within 0.35 s of the hand-marked time, nothing before
4.65 s or after 27.1 s. Synthetic: a stride is dropped; a squat in place, a shallow squat, one knee reading straight over
planted feet, a squat whose window runs into the walk-off, and an unseen other leg are kept.

Mutation check (file re-read after each write and after each restore; restored run: 8 passed):

| Mutation | Tests that failed |
|---|---|
| config key False | both real-footage tests |
| `and` -> `or` | planted-feet, runs-into-walk-off |
| knee test removed | runs-into-walk-off |
| travel test removed | planted-feet |
| never drop | both real-footage tests, stride-is-dropped |

Not killed by any of these: the unseen-other-leg test (it guards NaN handling only).

## 4. Before / after, every clip

| Clip | Truth | Before | After | Note |
|---|---|---|---|---|
| Reporter squat, prod image, pose + `analyze_lift` (no output video) + `build_lift_summary`, worktree `src` mounted over `/app/src` | 10 | 12 | **10** | grade D 64.7 -> D 61.6; the 10 kept windows are prod reps 2-11 unchanged (`c3/prod-image/before_e2e.json`, `after_e2e.json`) |
| Same, with an output video as the service calls it (`tools/e2e_render.py`: annotated render, alerts, metric clips), fixed code only | 10 | not run | **10** | `total_reps 10`, annotated.mp4 4.9 MB, 40 metric clips for reps 1-10 only (`c3/prod-image/render/`). Not exercised: the HTTP route, the H.264 re-encode and the GCS uploads. |
| Reporter squat, Linux keypoints, analysis only | 10 | 12 | **10** | `c3/before|after/squat_linux.json` |
| Reporter squat, macOS keypoints, analysis only | 10 | 13 | **10** | `squat_mac.json` |
| Situp fixture `situp_crunch_real_keypoints.npz` | n/a | 67 | 67 | output file byte-identical (sha 3f10a988...) |
| Pushup, prod clip 3c66c85e (macOS pose, analysis). It is the reporter's own upload, read from `/Users/toka/code/bowling-app/perf-fixtures-2026-11-13/`, a sibling directory another step of this run created; read only | prod says 18 | 18 | 18 | byte-identical (sha 5c037df9...) |
| Plank `backend/tests/fixtures/test_video_plank_10s.mp4`, full `analyze_lift` | n/a | 5.87 s in plank | 5.87 s | byte-identical (sha 9280fc87...) |

The comparison could have failed: both squat files differ before/after.

Engine tests (`$PY -m pytest ... -p no:cacheprovider`):

| Scope | Before (93378b0) | After (73852de) |
|---|---|---|
| `tests/test_lifting tests/test_lift_summary.py tests/test_service_summary.py` | 232 passed, 2 skipped | 240 passed, 2 skipped |
| whole `tests/` | 10 failed, 1258 passed, 34 skipped (run in the clean sibling worktree `situp-engine`, same commit) | 10 failed, 1266 passed, 34 skipped |

The 10 failures are the same 10 names before and after (`diff` of the sorted FAILED lists is empty): 4 bowling
`test_pipeline_integration`, 4 `test_detectors/test_tracker` YOLO, 1 lane-edge benchmark, 1
`test_service_app::test_metric_clips_are_reencoded_uploaded_and_rewritten`. Not caused by this change; not investigated.

Tree state after the runs (`git status --porcelain --ignored`): no tracked or untracked changes in either worktree.
The whole-suite baseline ran inside `situp-engine` (not my tree) with `PYTHONDONTWRITEBYTECODE=1`; no file there is newer
than 13 Sep. In `squat-engine` the runs left only gitignored files: `data/lifting/golden/*.png` (written by the lifting
tests), `yolov8s-worldv2.pt` (26 MB, downloaded by a bowling test) and `src/lifting/pose/.model_cache/` (the pose model,
copied from `situp-engine`, same sha as the one in the prod image). `situp-engine` carries the same three.

## 5. Labelled regression set: none exists

labelled_set_size = **0**, labelled_regressions = 0 (vacuous).

Where I looked, and why each check could have returned something:
- Engine repo: no squat video, annotation or fixture (`find -iname '*squat*'`: plan docs only; `annotations/` is bowling;
  `videos/input` holds curl, deadlift and bowling clips).
- `backend/tests/fixtures`: one plank clip.
- Session and reference docs: `docs/reference/100-club.md` says squat counting "has never been validated on real footage".
- Production bucket: `gsutil ls gs://.../lifting/*/summary.json` = 73 summaries; by `lift_type`: plank 31, pushup 19,
  situp 11, bicep_curl 5, deadlift 1, **squat 1 (the reporter's)**, 5 with no `lift_type` (old format, curl metrics,
  0-2 reps, opened one by one). The sweep found the other lift types, so it was able to find squats.
- Boards: The 100 Club has 2 athletes, the other has Squat 0; "New Powerlifting Challenge" lists Squat but holds only a
  deadlift and a snatch; the owner's 31 lifts contain no squat.
Not covered: squat uploads that were never analysed (no summary in the bucket) would only show in the database, which
I did not query.

## 6. Deploy decision

deploy_ok = **false**. reproduced yes, count_after 10 yes, lifting tests pass yes, labelled_set_size 0 < 3.

Decision needed (Tom): the fix is ready on `fix/squat-rep-count` but the contract's regression gate cannot be met,
because the reporter's clip is the only squat ever analysed. Options: (a) film or collect at least 3 squat clips with
known counts (ideally one side-on, one with a walk in and out, one with a pause) and re-run section 4 on them before
deploying; (b) deploy on this one clip plus the unit tests, accepting that a side-on squat is unverified. If deployed:
`gcloud builds submit --tag gcr.io/toms-gym/bowling-service:squat-73852de` from the clean worktree, then
`gcloud run services update --image ...` (never `deploy.sh`). The live attempt would still read 12 until re-analysed,
which is also Tom's call.

## 7. Points impact (from `live-before.json` and `services/consistency.py`, nothing written)

None. Week 2 (9-15 Nov), quota 125: his week is 147 lifts with 12 squats, 145 with 10. Both are over the quota, so week
points stay `min(lifts, 125) + 50 = 175` and his total stays 375 (200 + 175), rank 1 (Toka 350). Squat counts raw reps
(only Situp is quality-scored). Squat lead this week: he has 12 or 10, the only other athlete has 0; a leader needs
only the top amount above zero, so he leads either way and the +25 type bonus (added when the week ends Sunday) is
unchanged. Only difference: a rival would need 11 squats instead of 13 to take the lead before Sunday.

## 8. Limits

- One clip, one camera position (front-on, phone on the floor). Side-on squats, barbell squats and a walk straight down
  the camera axis are unverified.
- A crouch to start or stop the phone (both knees, feet planted) would still count; it is out of frame here.
- The valid-frame guard, the 20 deg prominence and the view auto-detection (front-facing athlete read as `side`) were
  left as they are.
- Prod-image runs were amd64 under emulation on an arm64 Mac: count and rep windows match live exactly, form scores
  differ in the third decimal. The pulled image `gcr.io/toms-gym/bowling-service:situp-13b49b5` is still in the local
  Docker store.
