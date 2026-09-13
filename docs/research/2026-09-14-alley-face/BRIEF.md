# Brief: does the alley have a face? Constellation detection of the lane's landmarks (next loop)

Start with: `/loop read docs/research/2026-09-14-alley-face/BRIEF.md fully, then run it — every
experiment, validated on the data, a one-minute review video at the end, commit when done`. Work
autonomously; Tom is not watching. Write everything into THIS folder (`README.md`, scripts,
`results/*.json` (gzip anything over ~5 MB), `overlays/`, `review.mp4` gitignored). Do not edit the
earlier loops' folders. **Commit the folder, the session doc and the CLAUDE.md section at the end.**

## The question

Loop 4 (`../2026-09-13-lane-landmarks/README.md`, read "What the results say" first) used the
landmarks one at a time: the ten pin bases fix the far end of any lane hypothesis (sample_input
1.19 → 0.37 boards, tom_old 1.61 → 0.41 against the pins truth), the arrows on their own cannot
extrapolate 45 ft, and the near end - the mask student's foul-line corners, 2-3 boards off on two
videos - is now the floor. Every step still started from a lane *hypothesis* (a trained mask or a
SAM prompt from a ball path), and the learned arrow detector memorised positions instead of
appearance.

Tom's hypothesis: the alley has a **face**. Nobody finds a face from one eye; the detector finds the
*arrangement* of eyes, nose and mouth, and the alignment step then refines every point jointly
under a shape model. The lane's features - two foul-line corners, a row of guide dots at ~7 ft, the
seven arrows in a V at ~15 ft, the ten pin bases at 60-62.6 ft, the two gutter edges joining them -
have an arrangement fixed by the rules, and unlike a face the shape model is exact and planar: its
only freedom is one homography. So the arrows should add value the way facial features do - not as
a far-end ruler, but as part of a constellation that (1) **finds** the lane in a frame with no ball
path, no trained mask and no prompt, (2) **aligns** all its points jointly so the near end comes out
right, (3) **persists** through the bowler, the rolling ball and the falling pins, and (4) can be
learned in the form face-alignment models use (heatmaps, not regressed coordinates - loop 3's pose
head and loop 4's arrow class both memorised geometry).

## The constellation (lane coordinates: x inches from the left edge, y inches from the foul line)

| feature | position | visibility (loop 4) | role |
|---|---|---|---|
| foul-line corners | (0, 0), (41.5, 0) | all videos (annotated bottom corners) | near end; currently the floor |
| guide dots | one row at ~7 ft, roughly 3 boards apart; **measure, do not assume** | plainly on tom_old (12-13 dots in `../2026-09-13-lane-landmarks/overlays/inspect_arrows_tom_old.jpg`), check the other two | near end, many points, one depth |
| seven arrows | boards 5 · 10 · 15 · 20 · 25 · 30 · 35, V with the centre at 15.4-15.8 ft and 0.4-0.5 ft per 5 boards (`results/landmarks_<stem>.json` → `all_fit.V`) | 7/7 on sample_input and tom_old, 5-6/7 on Chardie (720p) | mid-lane, the most distinctive arrangement in the frame |
| range-finder dots | 34-44 ft | none of the three videos | skip unless found |
| ten pin bases | rule-book rack, `landmarks.pin_bases_in()` | all videos while standing (until the pin-hit marker) | far end; the only width ruler that worked |
| gutter edges | the lines x = 0 and x = 41.5 | all videos, but confused with flat gutters at the deck and neighbouring lanes | lines, not points; use as constraints, not anchors |

Neighbouring lanes carry the same constellation one lane pitch (~1.55 lane widths) to each side,
and bowling_video shows six of them: "which face" is part of the question, as it was for the
student (loop 3, finding 2).

## Numbers to beat (loop 4, board MAE median through the throw, against the pins truth / the hand annotation)

| video | loop-3 student alone | student + ten detected pins (per frame) | SAM + pins, pre-hit frame | best lane of any loop |
|---|---|---|---|---|
| sample_input | 1.19 / 1.83 | 0.37 / 0.77 | 0.07-0.10 | 0.31 (student+arrows+pins10) |
| Chardie | 0.64 / 0.88 | 0.78 / 0.53 (near end 2 boards off) | 0.67 | 0.46 (arrows+pins10, all-landmark truth) |
| tom_old | 1.61 / 3.15 | 0.41 / 1.51 | 0.11 | 0.26 (two-class 1024 px student alone) |

Also: the per-frame pin refit floors at ~0.4 boards on tom_old whatever lane goes in (rack-fit noise;
pool the rack over frames); the student's foul-line corners are 19 / 12 px off on sample_input and
9 / 5 px on Chardie; landmarks as the camera model beat ORB (4.0 vs 5.3 px, 2.4 vs 5.2 at the pin
end) while the pins stand and are ill-conditioned from the arrows alone afterwards.

## What exists (reuse, do not rewrite)

- Truths, per frame: `../2026-09-13-lane-landmarks/common.py` → `truth_corners(stem, f,
  "annotated"|"pins"|"all")`, `score_corners`, `score_both`; `landmarks.py` → `truth_landmarks(stem,
  f)` (arrows + pin bases projected into any frame), `pin_bases_in`, `arrow_x_in`, `board_x_in`,
  `h_from_quad`, `to_lane` / `to_image`, `fit_homography` (weighted DLT with 2D points and
  point-on-line constraints), `fit_rack` (+ `alias_margin`), `detect_arrows`, `v_filter`,
  `rectify`, `white_map`. Copy the `common.py` pattern (loop 1 on `sys.path` for `gt`/`lane_sam`,
  loop 3's `camera_all_*.json`, `LM_SCRATCH`).
- Per-frame lanes to compare against: `../2026-09-13-lane-landmarks/results/e3_fit_*.json.gz`
  (`common.load` reads gzip), the rebuilt loop-3 corners in `baselines_rescored.json`, the
  two-class 1024 px student's lanes in `seg2_seg2_1024_lovo_tom_old__tom_old.json`.
- Detections already made: `$LM_SCRATCH/pred/lm_*.json` are gone with the scratchpad; rerun
  `e2_detect.py` (~1 s per standing-pin frame) if you need them.
- Video/report scaffolding: `review_video.py` (cards, panels, tracked clips, insets),
  `video_script.py`, `tables.py`, `fill_readme.py`, `click_landmarks.py`.
- Frames are NOT on disk (session scratchpad). Regenerate: loop 1's `gt.extract_frames` for the
  three annotated videos with `SAM_FRAMES` set, and the unlabeled two via `common.UNLABELED`
  (`~/Downloads/bowling_video.mp4`, `~/Downloads/IMG_0242.mov`). Weights download on first use.
- Python: `V=~/code/bowling-app/analysis-engine/.venv/bin/python` (torch 2.10 MPS, ultralytics
  8.4.14, opencv). No ffmpeg: OpenCV `avc1`.

## Experiments, in order

**E1 — Complete the constellation truth.** On the pre-hit frame of each annotated video, measure
the guide dots (and anything else repeatable and on the lane plane) through the all-landmark truth
homography: lane coordinates per dot, spacing, count, depth; check they agree across videos (same
alley) and write them into a `constellation.json` (lane coordinates + per-video visibility) and a
per-video `landmarks_<stem>.json` in loop 4's schema (`{x, y, frame, source, confidence}`). Project
into every frame with the truth homography. Report per-feature visibility per video, and which
features the bowler / ball / falling pins occlude on which frames (a visibility timeline).

**E2 — Feature candidates with no lane prior.** Cheap detectors over the whole frame: dark blobs
(arrows, dots), white columns (pin bodies), line segments (foul line, gutter edges). Report
candidates per frame and how many are true constellation points (precision of the raw pool) -
that is the clutter the constellation match has to beat.

**E3 — Finding the face.** From the candidate pool alone: use local structure to propose
correspondences (a V of seven dark blobs with near-equal spacing → the arrows; a row of ≥ 8 dark
dots at ~equal spacing → the guide dots; a white cluster with seven columns → the rack; the two
brightest long lines converging above → the gutters), hypothesise homographies from them (RANSAC
over the constellation, the rule-book coordinates as the model), and accept the hypothesis that
explains the most constellation points. Score: on what fraction of frames is the *right* lane
found (vs a neighbour), with no ball path, no student, no prompt; board MAE against both truths;
on bowling_video, how many of the six lanes are found and whether the ball's lane is separable
without the ball; on IMG_0242 (handheld, panning) per frame. Ablate the feature sets: arrows
only, arrows + dots, arrows + dots + rack, + gutters.

**E4 — Aligning the face.** From E3's homography, refine every landmark locally (sub-pixel
centroids for arrows and dots, `fit_rack` for the pin bases, gutter-line × foul-line intersection
for the near corners), then one weighted robust fit over all of them (weights = expected precision
in lane inches, pins tight, lines loose). Targets: the near end within 0.5 boards (the student's
2-3), the far end at the pins' floor or better with the rack pooled over the standing-pin frames
(loop 4 finding 9), and the whole path under loop 4's 0.37 / 0.78 / 0.41. Report against both
truths, per frame, pre-hit and last frames, the pin-end tail.

**E5 — Persistence.** Per frame through the throw: which features survive the bowler on the lane,
the rolling ball, the pins falling; the camera model from the surviving ones (loop 4's E4, a
similarity from static points - now with the dots as a second near depth so the arrows are not
collinear alone); the lane on every frame with the missing features carried through that camera.
Compare with loop 4's `+carry` / `+carryLM` rows (fragile) and with the ORB camera.

**E6 — Learning the face the way face alignment does.** A heatmap landmark model (one heatmap per
landmark class: 7 arrows, N dots, 10 pin bases, 2 foul corners; stride 4; a small U-Net or the
YOLO-pose *heatmap* variant if ultralytics offers one - not regressed coordinates), trained on the
three annotated videos with heavy homography augmentation of image and heatmaps together (the
constellation's only degree of freedom is the homography, so warping is exact supervision),
leave-one-video-out, `best.pt` chosen on the training videos' frames. Score recall and px error
per landmark class on the held-out video against the classical E2 detectors, and its constellation
fit against E4. Lessons that decide the recipe: loop 3's pose regressor memorised geometry (6-11
boards); loop 4's arrow class had AP 0 in-distribution under mosaic (half-scale tiles put a 6 px
arrow under the stride) and AP50 0.7 in-distribution / 0 held-out without mosaic; ultralytics'
MPS assigner crashes with eight tiny instances per image at batch 8-16. Two trainings share MPS.
If the model does not fire on the held-out video, say so with the in-distribution number beside it.

**E7 — Report.** `README.md` in loop 4's shape (question, constellation table with measured
positions, method, results against the loop-4 baselines in both truths, "what the results say",
recommendation for the engine, blocked / negative results, reproduce). `review.mp4` **about one
minute, one message**: the question and the answer on one card, the one clip that shows the face
being found and aligned (a few seconds), one table card, one recommendation card - ablations and
method live in the README. `docs/sessions/2026-09-14-alley-face-loop.md`, a memory note, a
CLAUDE.md bullet under "Lane Landmarks" if the answer changes what to ship. Send the video with
SendUserFile. **Commit** the folder, the session doc and CLAUDE.md (conventional commit,
`docs(bowling): ...`, git through a script per RTK.md, no `.pt` / `.mp4`).

## Rules and gotchas (each cost an earlier loop time)

- Every number in the README comes from a `results/*.json` row you produced; look at the overlay
  before believing a number (a good MAE on the wrong lane has happened three times now).
- Report against both truths (`annotated`, `pins`), never one; a method that improves against the
  hand corners but not the pins is fitting the annotation's error. The hand corners are 10 % too
  wide at the deck on sample_input, 7 % too narrow and 4 px left on tom_old.
- Train leave-one-video-out; pick `best.pt` on the training videos' frames only. All five videos
  are the same alley: generalisation means a new camera placement, not a new venue - say so.
- Pick the lane by an anchor that is not the top-confidence box; here the anchor is the
  constellation itself.
- The rack fit's one-column alias (6 in) wins on 2-4 % of frames from a poor hypothesis: keep the
  `alias_margin` test. Pool the rack over frames; per frame it floors at ~0.4 boards.
- `ultralytics` reads a flat point list as N one-point prompts (nest per object); its MPS assigner
  crashes with many tiny instances (batch 4 or mosaic off ran); mosaic + 0.5× scale erases 6 px
  features.
- Loop 1 is on `sys.path`: do not name a script `make_review_video.py` (it imports loop 1's).
- Loop 3's per-frame rows carry corner *distances*, not corners; loop 4's `baselines_rescored.json`
  has the rebuilt corners. `camera_all_*.json`'s `static_frame` is not the frame sample_input's
  static corners belong to (~frame 0).
- Background Bash waiters die at 10 min; use `nohup` scripts + Monitor, or the loop's wakeup.
  `rtk` rewrites bare `ls` and `grep` output; run git through a script; bare ISO dates parse as UTC.
- Under ~0.3 boards on the handheld videos and ~1 board on tom_old is within the annotation floor
  unless measured against the pins truth; under ~0.4 against the pins is within the rack-fit floor
  unless the rack is pooled.
- If a step is blocked (a feature invisible everywhere, a detector that never fires), say so in the
  README with the evidence and move on; a documented negative is a result.
