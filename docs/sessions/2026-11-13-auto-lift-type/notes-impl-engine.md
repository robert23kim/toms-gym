Per type, all 51 labelled clips: situp 10/11, pushup 16/17, squat 1/1 (thinly tested: one clip, none in the development half), plank 21/22; overall 48/51 = 94.1 %; held-out half 29/32 = 90.6 % (situp 5/6, pushup 9/10, squat 1/1, plank 14/15).

# Engine notes: automatic lift type (2026-11-13)

Verdict: built, committed, **not pushed, not built, not deployed**. deploy_ok = true by the contract's rule, with two caveats
Tom should read before the deploy: (1) 2 of the 3 misses are **silent** (confidence 0.91 and 1.00), and one of them would
credit **162 pushups for a 141 s plank**; (2) pose for the eval came from macOS, only 7 clips were re-run in the production
Linux image (same detected types, one confidence dropped from 0.86 to 0.56).

- Worktree `/Users/toka/code/bowling-app/auto-engine`, branch `feat/auto-lift-type` off `feat/situp-config` (93378b0). Tree clean.
- Commits: `b4464b3` classifier + unit tests; `d3f9f57` auto in pipeline/service/CLI + tests; `920db45` eval script + result
  table + README; `a52612e` thin out the early-decision checks.
- **Never commit from this session folder:** `clips/` (videos and `manifest.json` with attempt and user ids),
  `sheets/` (faces), `pose-cache/`, `pose-cache-linux/` (body pose of real athletes) and `engine/` (summaries of real
  uploads). Stage session docs by explicit file, never the whole directory.
- Artifacts (not committed): this folder: `clips/` (65 downloads, `manifest.json` with ids, split and exclusions),
  `pose-cache/` (macOS), `pose-cache-linux/` (prod image), `sheets/` (contact sheets), `engine/` (before/after summaries,
  test logs, eval outputs, mutation-check.txt).

## 1. What was built

- `src/lifting/analysis/lift_type_classifier.py`: rules on joint angles only (elbow, knee, hip = shoulder-hip-knee), so a
  phone on its side changes nothing. Per joint: cycles (troughs with prominence 35/25/12 deg, at least 0.3 s wide), median
  and 90th percentile; plus the fraction of time nothing moves (1 s rolling spread under 8 deg).
  situp = folded at the hips at rest and never standing straight, with elbow or hip cycles; pushup = straight body, elbow
  cycles, knees not cycling with them; squat = knees and hips cycle together and open out straight; plank = straight body
  that holds still or shows no rep cycles. Confidence = winner's score x its share of all scores. No usable pose (under
  2 s, or no joint seen 30 % of the time) or no known candidate = no detection.
- `src/lifting/pipeline.py`: `analyze_lift(..., lift_type="auto", candidates=[...])` -> `_analyze_auto`: one
  `estimate_video_candidates` pass, classify, then the normal pipeline on the same candidates. Situp: the existing
  tracker. Pushup/squat: `select_standing_track` (new, `pose/estimator.py`) replays the per-frame selection + OneEuro
  smoothing of `estimate_frame` on the stored candidates. `estimate_frame`/`estimate_video` are untouched; the rest of
  `analyze_lift` moved verbatim into `_analyze_skeletons`.
- Plank cannot reuse the pass (heavy model, 15 fps, 8 workers), so the pass stops early: `early_decision` is asked every
  2 s (every 10 s after 30 s) and stops when the prefix reads as a plank with a still run of 8 s, or at 60 s when the
  prefix is a plank or has nobody in it. Then the unchanged `_analyze_static_hold` runs.
- `src/lifting/summary.py`: only in auto mode adds `detected_lift_type`, `lift_type_confidence`, `lift_type_scores`;
  `lift_type` = detected type. No detection = `{"lift_type": "auto", "detected_lift_type": null,
  "lift_type_confidence": 0.0, "lift_type_scores": {...}}`.
- `service/app.py`: reads `candidates`; auto without a non-empty list = 400; no detection = 200 with
  `annotated_video_url: null` and the summary uploaded. `scripts/analyze_lift.py`: `--lift-type auto --candidates a,b`.
- Clarifications for the other sides are in `contract-deviations.md` (engine section, items 1-7). No field name or type
  in the wire contract changed.

## 2. Labelled set

Source: Cloud SQL read-only (`SET default_transaction_read_only = on`), every `Attempt` joined through `UserCompetition`:
77 attempts, 77 distinct videos. Downloaded with `gsutil cp` (read-only): all 28 club attempts, 27 legacy attempts of
the same four types (Summer plank challenge 15, Pushup challenge 6, Situp challenge 3, New Powerlifting planks 3) and the
10 legacy "Squat" uploads in the "Bowling" competition = 65 files.

- Excluded: c56-c65 (the 10 legacy "Squat" uploads are one 31 KB colour-bar test pattern, ten times), c40 (black frames,
  5 fps), c38/c39 (byte-identical to c29, the 10 s plank fixture `backend/tests/fixtures/test_video_plank_10s.mp4`),
  c44 (identical to c43). c40 and c56 were kept as "nobody in the video" cases: both give no detection.
- **51 clips with a person**: plank 22, pushup 17, situp 11, squat 1. 11 uploaders.
- Labels: every distinct clip read on contact sheets (`sheets/sheet_01..08.jpg`, 4 frames each, picked for difference).
  **No label was wrong.** Worth knowing: c33, c35 (plank) and c47 (pushup) are filmed with the phone on its side; c48 is
  knee pushups; c32 is a plank filmed from the feet with the head hidden. Limit of the check: 4 frames cannot show a
  clip that mixes two lifts.
- Engine fixtures: `tests/fixtures/lifting/situp_crunch_real_candidates.npz` (already in the repo) is classified in a
  unit test (situp, confidence >= 0.6), not counted in the 51. The backend plank fixture is c29.
- Split, frozen in `manifest.json` before any feature was computed: development = alternating clips of the two athletes
  with the most uploads, capped at half of each type: plank 7, pushup 7, situp 5, squat 0 (19). Held-out = the other 32,
  of which 14 are from 9 athletes with no development clip.
- Pose cache = exactly what production classifies on (raw candidates per frame through `open_video`), macOS, full model.
  Clips over 150 s are cached for their first 75 s (label-agnostic); every such clip stopped inside the cache.

## 3. Result (script `scripts/eval_auto_lift_type.py eval`, table `docs/auto_lift_type/labelled_set_result.md`)

| Set | Result |
|---|---|
| All 51 | 48/51 = 94.1 %: plank 21/22, pushup 16/17, situp 10/11, squat 1/1 |
| Held-out 32 | 29/32 = 90.6 %: plank 14/15, pushup 9/10, situp 5/6, squat 1/1 |
| Held-out, athletes with no development clip (14) | 12/14 = 85.7 %: plank 9/10, pushup 3/4 |
| Development 19 | 19/19 |
| Correct but under 0.6 (the app asks) | 1 (c36 plank 0.57) |
| Nobody in the video | 2/2 no detection |

The held-out half was scored once with the rules frozen; the rows of that first run are identical to the committed table
(`engine/eval-first-holdout-run.md` vs the committed file, `diff` empty). Nothing in the classifier changed after it.
The only later change (`a52612e`, check schedule) leaves the table byte-identical (`cmp`).

Honest caveats on blindness: (a) before the held-out run, the end-to-end before/after check had already run auto on
c28, c24, c08 (held-out) and printed their detected type; no rule was changed because of them. (b) Between the first
development result and the held-out run, three rule changes came from **synthetic** unit tests, not from clips: a squat
is not "folded" because it stands up every rep; a jittery hold with no cycles is still a hold; hip cycles count as reps
only for a folded body.

### Misses

| Clip | Label | Guess | Confidence | Reason |
|---|---|---|---|---|
| c22 (held-out, club athlete) | situp | none | 0.00 | Crunch-depth reps: 3 hip and 5 elbow cycles in 57 s, still 74 % of the time, so it reads as a folded body holding still. Production counted 13 situps on it with the trunk-lift (ear-hip-knee) signal, which the classifier does not use. **The app asks.** |
| c32 (held-out, legacy, other athlete) | plank | pushup | 1.00 | Camera at the feet looking along the body, head hidden. The full-model arm keypoints jump: 38 false elbow cycles in 141 s, still 20 %. **Silent.** Run as a pushup on the same candidates the engine counts **162 reps** (grade D). Production's plank analyzer (heavy model) measured 110.7 s in plank on it. |
| c48 (held-out, legacy, other athlete) | pushup | plank | 0.91 | 8.8 s of knee pushups from the front quarter: elbows bend towards the camera, 2D elbow angle stays 158-165 deg, 0 cycles. **Silent.** Told it is a pushup, production counted 2 reps (about 5 done). Same miss in the Linux image (0.89). |

Follow-ups that would address them (not done: they would be tuning on the held-out half): use the trunk-lift angle for
situp cycles (c22); ask instead of deciding when the pipeline's rep count and the classifier's cycle count disagree,
162 vs 38 on c32.

## 4. Explicit lift types unchanged

`engine/before/` (93378b0, before any edit) vs `engine/after/` (a52612e): `analyze_lift` + `build_lift_summary`, JSON
written as the service writes it. sha256 of the files:

| Fixture | Type | Count | before = after |
|---|---|---|---|
| c28 | squat | 13 reps | d83dade21997856f = same |
| c15 | pushup | 25 reps | bb1063c58ee41617 = same |
| c24 | situp | 23 reps | 26f1788c477c9d37 = same |
| c29 (10 s fixture) | plank | 5.87 s | b41aeb9f06684126 = same |
| c08 | plank | 56.58 s | d103bf754f0c0ee9 = same |

Not covered by a before/after clip: bicep_curl and deadlift, which run through the same moved code
(`_analyze_skeletons`); they are covered by the existing unit suite only.

Auto on the same five clips (real MediaPipe, both paths): detected squat/pushup/situp/plank/plank and the summary equals
the explicit one exactly once the three new keys are removed. Not covered: the annotated video and metric clips (no
output video was requested in these runs), the HTTP route with real GCS, and the H.264 re-encode. The service route is
covered by unit tests with a fake bucket only.

## 5. Tests

- New: 41 tests. `tests/test_lifting/test_lift_type_classifier.py` (each type at 0/90/180 deg rotation, knee pushups, squat
  with swinging arms, keypoint glitches, hip sag, long set with rests, candidates, no pose, legs out of frame, early
  decision, stream, check schedule, the real situp fixture), `tests/test_lifting/test_auto_lift_type_pipeline.py` (auto =
  explicit apart from the keys for situp/pushup/squat, plank stops the pass, no candidates, nobody, replay = estimate_frame,
  stop hook), `tests/test_lift_summary.py` (+3), `tests/test_service_app.py` (+3).
- Whole suite, `pytest tests -p no:cacheprovider`: before (93378b0) 10 failed, 1258 passed, 34 skipped; after (final
  commit a52612e) **10 failed, 1299 passed, 34 skipped** (`engine/after/pytest-all-final.log`). The 10 failures are the
  same names before and after (`cmp` of the sorted FAILED lists, rc 0): 4 bowling pipeline integration, 4 YOLO tracker,
  1 lane-edge benchmark, 1 `test_service_app::test_metric_clips_are_reencoded_uploaded_and_rewritten`. Pre-existing, not
  caused by this work, not investigated.
- Mutation check (`engine/mutation-check.txt`): 26 mutations, 26 killed, each file re-read after the write and restored
  from an in-memory copy (sha printed). First pass had 4 survivors (hip cycles for a straight body, early decision for
  any type, two replay guards); those tests were strengthened and the run repeated.

## 6. Runtime (macOS M3, analysis only, no output video; noisy, another session was using the machine)

| Clip | Explicit | Auto | Extra |
|---|---|---|---|
| c08 plank, 68 s | 41.7 s, 41.4 s | 52.1 s, 56.6 s | **+31 %** (mean of two rounds; the pass read 16 s of video before stopping) |
| c29 plank, 10 s | 9.3 s | 15.7 s | +69 % (short clip: the whole clip is read) |
| c15 pushup, 28 s | 19.3 s, 25.8 s | 22.9 s, 25.1 s | +6 % mean (+19 %, -3 %) |
| c24 situp, 48 s | 32.5 s | 36.1 s | +11 % |
| c28 squat, 32 s | 15.1 s | 18.3 s | +21 % |

The plank percentages understate production: here the plank analyzer ran on one worker, production runs it on 8
while the classification prefix stays single-threaded.

Rep lifts add no pose pass; the extra is the stop checks and classification (about 1 s of CPU on a 28 s clip, measured
on the cache). Planks pay for the classification prefix: 10-22 s of video on the 21 planks it recognised.
Production estimate, not measured: the full model costs about 56-80 ms per frame there (squat 43 s for 767 frames,
situp 171 s for a 67 s clip), so a plank pays roughly 15-55 s on top of about 52 s today. Worst case: a hold that never
reads as a plank is read to the 60 s limit (about 145 s extra), and a plank misread as reps (c32) is read in full.

## 7. Production image check (Linux pose)

`docker run --platform linux/amd64 --network none` on `gcr.io/toms-gym/bowling-service:situp-13b49b5` with the worktree's
`src` and `scripts` mounted read-only: pose re-extracted for c28, c15, c24, c29, c08, c36, c48 (planks over 50 s cut to
30 s), then classified. Same detected type on all seven (6 right, c48 the same miss). Confidences: c29 0.86 -> **0.56**
(the 10 s fixture now asks), c36 0.57 -> 0.57, c48 0.91 -> 0.89, the rest 1.00. Not covered: the other 44 clips on
Linux pose, and the service running in Cloud Run.

## 8. Limits and risks

- Squat: one clip. The rule is from first principles and synthetic bodies; front-on only.
- Silent wrong guesses are possible on unusual camera placements (2 of 51, both legacy, neither from the two club
  athletes, whose 37 clips are 36 right and 1 asked). A plank misread as pushups can over-credit heavily (162).
- A rep set that opens with a hold of 8 s or more before the first rep is decided as a plank at that point.
- Auto holds up to 5 pose candidates per frame in memory for pushup and squat too (situp already did).
- The live engine has no "auto": it would fall back to bicep-curl analysis, so the backend switch must stay off until
  this branch is deployed (`gcloud builds submit --tag ...` from this clean worktree, then
  `gcloud run services update --image ...`; never `deploy.sh`).
