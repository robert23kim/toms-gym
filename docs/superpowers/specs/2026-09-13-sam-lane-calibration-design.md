# SAM lane calibration in the bowling engine (design, 2026-09-13)

Ports the shippable findings of the five 2026-09-12/13 lane research loops into
`analysis-engine` as one new pass, and measures old vs new engine on the three
annotated videos with the loops' own metric.

## What the engine does today

`scripts/debug_ball_motion.py` (what the Cloud Run service runs, `--simple-detect`)
finds ONE lane per video before the ball is tracked: classical anchor detection
(foul line, gutters, pins) on early frames, refined by `detect_pin_action`. Board
numbers come from `BirdsEyeRenderer`, which interpolates the ball's x between the
static lane's left/right edges at the ball's y. On a handheld phone the lane drifts
24-36 px over a throw (loop 1), which is 10+ boards at the pin end where a board is
1-2 px; the classical edges themselves are several boards off at the pins.

## What the research established (in order of effect)

1. SAM 2 prompted with 3 points spaced evenly by image length along the on-lane
   ball path (15-85 %), slid off the ball, on a frame after the bowler has cleared
   the lane and before pin contact, gives 0.2-1.2 boards; the mask component is the
   one holding the prompts (loops 1-2).
2. A second SAM pass on a crop of the far 55 % of the lane, prompts in the lower
   half of the crop, fixes the far-end width (Chardie 0.47 -> 0.32, tom_old
   1.23 -> 0.49; against the pins-based truth it also wins on sample_input) (loop 2).
3. The standing pin rack is a far-end ruler: refitting a metric homography from the
   detected pin bases takes the far-end centre and width to ~1 px (loop 4).
4. Per-frame lanes are needed on handheld video; carrying one calibrated lane
   through a per-frame ORB similarity camera model is within 0.2 boards of an
   oracle gate (loop 2).
5. Tiny weights (`sam2.1_t`) match base with the crop (loop 2). Sub-pixel edges,
   prompt ensembles, gradient snapping, 2048 px encoding, vanishing-point fits: no
   gain (loop 2). The YOLO seg student is a tracker / lane picker, not a
   calibrator, and it was trained on these three videos (loop 3): not used here.

## Design

A new pass 5, `--sam-lane`, after ball detection and trajectory cleanup:

```
positions (frame, x, y, r) + pin-hit frame + video
  -> FrameAligner: ORB + RANSAC similarity of every throw frame to the calibration frame
  -> calibration frame = pin_hit - 4 (>= 6 positions before it)
  -> prompts: path warped into that frame, 3 even points, off the ball
  -> SAM 2 tiny full frame -> component holding the prompts -> row extremes -> robust line per edge
  -> far-end crop pass (top 55 % of the lane, 2 prompts at 10-55 % of the crop path) -> rows merged, crop wins -> refit
  -> pin rack fit initialised from the SAM quad; if it passes (contrast >= 2.5, score > 0.2, alias margin > 0.02),
     metric homography from the foul-line corners + 10 pin bases (weighted DLT, robust) replaces the edge lines
  -> LaneCalibration: lines in the calibration frame + per-frame transforms
  -> per-frame LaneEdges (lines warped), per-position raw board, summary (final_board = median of the last 5 on-lane)
  -> <out>_lane_calibration.json, summary.json fields, and the debug video re-rendered with the per-frame lane
```

Every step degrades: no ultralytics / no weights / no mask -> the pass is skipped and
the old lane and boards stand; crop or pin fit that fails its gate -> the previous
stage's lines stand. The classical lane is kept in the JSON as `baseline_lane`.

Modules (all under `src/bowling/lane_tracking/`, pure numpy/cv2 except the SAM wrapper):

- `lane_geometry.py`: `even_path_points`, `component_with_prompts`, `robust_line`,
  `fit_edge_lines`, `lines_to_corners`, `merge_rows`, `crop_box`, `board_from_lines`.
- `frame_alignment.py`: `FrameAligner` (per-frame 2x3 similarity to a reference,
  `transform(f_from, f_to)`, `warp_point`, `warp_line`).
- `sam_prompter.py`: `SamLaneSegmenter(weights, weights_dir)` -> binary mask for
  point prompts on a frame or a crop; `None` when unavailable.
- `pin_rack.py`: rack template, matched-filter score, coarse-to-fine fit, column
  refinement, alias margin, `fit_homography` (points + point-on-line), `corners_from_h`.
- `lane_calibration.py`: `calibrate_lane(...)` orchestration, `LaneCalibration`
  (`lane_edges_at`, `board_at`, `to_dict`).

`scripts/calibrated_render.py` re-renders the debug video from the per-frame lane
(reuses `BirdsEyeRenderer.update_lane_edges` and `DebugVisualizer`).
`service/app.py` passes `--sam-lane` when `SAM_LANE=1` (deploy follow-up: weights in
the image, torch + ultralytics in `requirements-service.txt`).

## Evaluation (research folder `docs/research/2026-09-13-engine-lane-integration/`)

Same metric as loops 1-4: per frame, the annotated ball path (warped into the frame
through loop 1's camera model) mapped to boards through the engine's lane on that
frame vs through the truth lane on that frame; board MAE; two truths, the annotated
corners and loop 4's pins-based corners. The old engine is one static lane on every
frame; the new engine is the calibrated lane carried per frame. Also reported: the
engine's own final board (product number) old vs new vs truth. Deliverable:
`review.mp4`, about a minute, one side-by-side clip per video, old engine left /
new engine right, then the table.

## Out of scope

Deploying to Cloud Run; the seg student; SAM video mode; the alley-face constellation.
