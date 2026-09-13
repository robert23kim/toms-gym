# Brief: do more lane landmarks make the board number more accurate? (next loop)

Start with: `/loop read docs/research/2026-09-13-lane-landmarks/BRIEF.md fully, then run it — every
experiment, validated on the data, a review video at the end`. Work autonomously; Tom is not
watching. Write everything into THIS folder (`README.md`, scripts, `results/*.json`, `overlays/`,
`review.mp4` gitignored). Do not edit the earlier loops' folders. Commit only if Tom asks.

## The question

Loop 3 (`../2026-09-12-cheap-lane-model/README.md`, read its Results and "What the results say"
first) fits the lane from **four corners** — two edge lines evaluated at the foul line and the pin
deck — whether the corners come from SAM 2 or from the YOLO11n student. Every remaining error is
at the far end, where a board is 1-2 px: the student's mask swallows a gutter's width (+8 px at the
pin end on tom_old), SAM's mask is 5-12 % narrow at the deck (loop 2), and a corner error there
bends the whole board grid.

A lane has landmarks whose real-world position is fixed by the rules:

| landmark | position | what it constrains |
|---|---|---|
| foul line, both ends | 0 ft, boards 1 and 39 | near end (already have it) |
| seven arrows | ~15 ft, boards 5 · 10 · 15 · 20 · 25 · 30 · 35 | absolute board positions mid-lane, seven correspondences |
| range-finder dots | 34-44 ft | mid-far lane (optional, often invisible in phone video) |
| pin deck: 7-pin and 10-pin bases | 60 ft, pins 12 in apart centre to centre, 7 and 10 are 36 in apart; lane 41.5 in wide | far-end width and centre, from a physical ruler instead of a mask edge |

Hypothesis: a homography fitted to **all** visible landmarks (over-determined, weighted, robust)
beats the four-corner fit, most of all at the far end, and the pins fix the far-end width that
neither SAM nor the student gets right. The loop-3 answer on *regressed* keypoints stands: do NOT
add landmarks as extra pose-head keypoints (that head memorises geometry, 6-11 boards). Landmarks
here are detected features with known physical positions, fed to the fit.

## Numbers to beat (loop 3, held-out, board MAE, lower is better)

| video | student seg 640 gated: throw median / pre-hit / last | student +teacher frames | student 1024 (tom_old only) | hybrid student→SAM tiny pre-hit / last | SAM 2 ball-path prompts pre-hit / last (loops 1-2) |
|---|---|---|---|---|---|
| sample_input | 1.83 / 1.59 / 2.11 | 1.22 / 0.99 / 1.08 | – | 1.07 / 0.64 | 0.31 / 0.24 |
| Chardie | 0.88 / 0.96 / 1.28 | 0.97 / 0.82 / 0.59 | – | 0.51 / 0.59 | 0.69 / 0.39 |
| tom_old | 3.15 / 3.29 / 1.87 | 3.16 / 3.14 / 1.78 | 0.94 / 1.04 / 0.32 | 2.08 / 0.76 | 2.27 / 1.35 |

Caveat that decides the plan: loop 2 showed the hand-clicked corners are themselves off at the far
end (tom_old ~5 px = 3 boards lateral, Chardie ~2 boards) and every number above is measured against
them. **Below one board at the pins nothing is measurable until the truth is rebuilt from the pins.**
So the truth comes first (E1), and every result is reported against both truths, side by side.

## What exists (reuse, do not rewrite)

- Metric + per-frame truth + ball path helpers: `../2026-09-12-sam2-lane-experiments/{gt.py,lane_sam.py}`
  (`L.score`, `L.truth_corners`, `L.ball_points_on`, `L.fit_edges`, `L.lines_to_corners`, `L.gt_y`,
  `L.transform` camera motion, `L.draw_overlay`, `L.model("sam2.1_t.pt")`, `L.predict_mask`).
  Loop 3's `common.py` wires them up (`C.use_full_camera()` for the full-video camera model in
  `../2026-09-12-cheap-lane-model/results/camera_all_<stem>.json`); copy that pattern.
- Pins as a ruler, already half built: `../2026-09-12-sam2-lane-experiments-2/{centre_check2.py,rescore_pins.py}`
  (same-row pin-centre shift of the annotated top corners; centre only, width unchanged). Extend to
  width with the 7-pin / 10-pin spacing. The engine's pin detector:
  `~/code/bowling-app/analysis-engine/src/bowling/lane_tracking/pin_detector.py` (`detect_in_frame`,
  `find_white_cluster_center`, `PinFormation`).
- Student: `../2026-09-12-cheap-lane-model/{eval.py,postproc.py,hybrid.py,train.py,build_dataset.py}`;
  the all3+teacher weight is `../2026-09-12-cheap-lane-model/lane_seg640_all3_plus.pt` (gitignored,
  on disk). Leave-one-video-out weights are gone with the scratchpad: retrain with `train.py`
  (seg, 30 epochs, ~15-25 min per fold on MPS; `_plus` folds need the teacher frames from
  `teacher_sam.py` + `build_plus.py` on bowling_video first).
- Frames are NOT on disk any more (session scratchpad). Regenerate:
  `$V -c "import gt; [gt.extract_frames(s) for s in gt.VIDEOS]"` from the loop-1 folder with
  `SAM_FRAMES` pointing at your scratchpad, then `C.extract_unlabeled(...)` for bowling_video /
  IMG_0242 (`~/Downloads/bowling_video.mp4`, `~/Downloads/IMG_0242.mov`).
- Videos + annotations: `~/code/bowling-app/analysis-engine/{sample_input.mp4, videos/input/*.mp4,
  annotations/<stem>/annotation.json}` — corners only (`lane_edges`, sample_input also
  `frame_lane_edges`), ball per frame, `pin_hit_frame` / `frame_markers.pin_hit`. tom_old's
  `left_edge_points` / `right_edge_points` are three points per edge, not landmarks.
- Python: `V=~/code/bowling-app/analysis-engine/.venv/bin/python` (torch 2.10 MPS, ultralytics
  8.4.14, opencv). `yolo11n-seg.pt` and `sam2.1_t.pt` download on first use (`SAM_WEIGHTS`,
  `YOLO_CONFIG_DIR`). No ffmpeg: write video with OpenCV `avc1`.
- Annotation: `scripts/label_video.py` in the engine labels the ball, not landmarks. Nobody will
  click for you. Derive landmark truth semi-automatically (E1), check it in overlays yourself, and
  ship a 40-line cv2 click tool (`click_landmarks.py <stem> <frame>`) so Tom can correct a point
  later; write the truth as `results/landmarks_<stem>.json` = per named landmark
  `{x, y, frame, source: detected|clicked, confidence}`.

## Experiments, in order

**E1 — Truth from physical landmarks (do this before any model work).**
On one standing-pins frame per annotated video (pre-hit − 2 to − 6; loop 2's `common.frame_for`):
detect the ten pin bases (engine detector, then the cluster's row of bases — the 7-pin and 10-pin
are the outer ones of the back row), the seven arrows (dark/light triangles on the rectified lane
~15 ft down: rectify with the four-corner homography, template/contour match in lane coordinates,
map back), and the foul-line ends (from the mask / gutter edges). Build a pins-based far end:
centre from the cluster centre (loop 2), width = pin spacing × 41.5 / 36 at the base row. Report,
per video, how far each hand corner is from the landmark-derived one (px and boards). Re-score
loop 3's stored corners (`../2026-09-12-cheap-lane-model/results/*_anc_gated__*.json`, `corners`
per frame) against the new truth so the baselines above exist in both truths. Warp the landmark
truth through the camera model to every frame (`L.transform`), as loop 1 did for the corners.

**E2 — Detect the landmarks at inference time.**
(a) pins: engine detector on every frame with pins standing; (b) arrows: a second class on the
YOLO11n student (labels from E1 on the three videos + the SAM teacher video, tiny boxes, train at
1024 px because arrows are ~10 px), or a classical detector on the student-rectified lane if the
learned one does not fire; (c) foul-line ends from the student mask's bottom rows. Score each
landmark detector alone: recall and px error vs E1 on the held-out video (leave-one-video-out for
anything learned). Note which landmarks are visible in which video (range-finders probably in none).

**E3 — Multi-landmark homography.**
Fit the image→lane homography from all available correspondences (4 corners + up to 7 arrows + 2
pin bases + foul-line ends) with robust weighted least squares (weights from detector confidence
and expected px precision: pins tight, corners loose at the top), RANSAC against a wrong arrow.
Score with the loop-1 metric on the pre-hit and last frames and per frame through the throw, against
both truths. Ablations, each a row: corners only (baseline, must reproduce loop 3's numbers) ·
+arrows · +pins · +arrows+pins · each landmark dropped in turn (robustness) · the same with the
student at 1024 px and with the far-end crop. The number that matters most: far-end width error in
px and the board error on the last 20 % of the ball path.

**E4 — Landmarks as the camera model.**
Arrows and pins are static in the scene, so tracking them through the throw gives per-frame camera
motion directly (a similarity from 9 static points) instead of ORB on the whole frame. Compare with
`camera_all_<stem>.json` on sample_input, where per-frame hand corners exist (loop 3 measured ORB at
4.5 px mean). If it is better, per-frame truth and per-frame lanes both improve for free.

**E5 — Report.**
`README.md` in loop 3's shape (question, data, method, results tables against the loop-3 baselines
in both truths, "what the results say", recommendation for the engine, reproduce commands),
`review.mp4` (cards, per-video overlays with landmarks drawn, far-end insets, before/after board
grids), `docs/sessions/2026-09-13-lane-landmarks-loop.md`, a memory note, one CLAUDE.md bullet under
"Cheap Lane Model" if the answer changes what to ship. Send the video with SendUserFile.

## Rules and gotchas (each cost an earlier loop time)

- Every number in the README comes from a `results/*.json` row you produced; look at the overlay
  before believing a number (a good MAE on the wrong lane has happened twice).
- Keep the loop-1 metric unchanged; add the pins-based truth as a second column, never replace.
- Train leave-one-video-out; pick `best.pt` on the training videos' frames only.
- Choose the lane by an anchor (ball-path points inside the candidate), never the top-confidence box.
- `ultralytics` reads a flat point list as N one-point prompts: nest per object.
- Background waiters in the Bash tool die at 10 min without a notification; re-arm `until` loops
  or rely on the loop's fallback wakeup. Two trainings share MPS fine; CPU evals alongside slow them.
- Bare ISO dates parse as UTC; `rtk` rewrites bare `ls`; run git through a script if you need it.
- Report anything under ~0.3 boards on the handheld videos and ~1 board on tom_old as "within the
  annotation floor" unless it is measured against the pins-based truth.
- If a step is blocked (a landmark is invisible in all videos, the arrow detector never fires), say
  so in the README with the evidence and move on; a documented negative is a result.
