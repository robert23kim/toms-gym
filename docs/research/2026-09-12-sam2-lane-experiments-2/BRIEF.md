# Brief for loop-2 agents (read fully before touching anything)

## Goal

Beat the 2026-09-12 SAM 2 lane numbers in `../2026-09-12-sam2-lane-experiments/README.md`
(read its Results and "What the results say" sections first — everything there is measured
with exactly the metric you will use). Board MAE, lower is better, on the three videos
sample_input / Chardie (`20260112_121117`) / tom_old:

| method (loop 1) | frame | sample_input | Chardie | tom_old |
|---|---|---|---|---|
| `even3_last` (headline) | last | 0.24 | 0.39 | 1.35 |
| best single-frame per video | last | 0.08 | 0.32 | 0.61 |
| `video_rev` per-frame mean / median | every frame | 1.85 / 0.98 | 16.39 / 4.02 | 3.73 / 2.35 |
| `video_span` per-frame mean / median | every frame | 2.00 / 1.06 | 19.45 / 3.86 | 3.55 / 2.23 |

Loop 2 so far (this folder, `results/*.json`): `even3_prehit` 0.55 / 0.72 / 2.34 — the pre-hit
frame (pin_hit − 2, pins standing, bowler off the lane) scores WORSE with the loop-1 prompt
because `track_points_even` drops any point within 3 ball radii of the ball, and at pre-hit
the ball is at the top of the lane, so only 2 of 3 prompts survive and the mask stops short of
the pin deck. Use `common.even_points_keep` (keeps n points by sliding them along the path)
for any frame where the ball is on the lane.

## Metric (do not change it)

`L.score(stem, corners, f)`: the four predicted corners (two fitted edge lines evaluated at the
annotated top / bottom y from `L.gt_y(stem, f)`) define a 4-corner board homography; every
annotated ball position (warped into frame f) is mapped to a board number and compared with
the homography from the annotated corners for that frame. `board_mae` is the mean abs diff.
Truth is per frame (`L.truth_corners`): sample_input has hand-annotated per-frame corners
(piecewise constant, 6 sets, top width 58–61 px ⇒ ~±1 board of annotation noise at the pins);
Chardie's static corners are pinned to f170 and warped through the ORB camera model; tom_old
is a tripod. One board is 1.0–1.7 px at the pin end.

## Files

- `common.py` — sets `SAM_FRAMES` / `SAM_WEIGHTS` to this session's scratchpad and imports the
  loop-1 modules `gt` and `lane_sam as L`. `C.frame_for(stem, kind)` for kinds `pre`, `mid`,
  `last`, `prehit` (pin_hit − 2), `prehit-N`. `C.read_frame(stem, f)`. `C.path_points_between`.
  `C.even_points_keep(stem, f, n, lo, hi)`.
- `sam2x.py` — `S.SamImage(img, weights, imgsz)` encodes once; `.logit(points, labels)` →
  (float logits HxW at source res, score); `.logits([obj1_pts, obj2_pts, ...], labels)` → one
  logit map per object (multi-object in one decode, ragged lists padded). `S.crop_logit(img,
  (x1,y1,x2,y2), points_full_coords, weights)` runs SAM on a crop (upscaled to 1024 by the
  letterbox) and returns crop-sized logits.
- `edges.py` — `E.component(logit, anchors)`, `E.soft_rows(logit, y_top, y_bot, anchors, comp)`
  → per-row sub-pixel (ys, xl, xr); `E.fit_pair(ys, xl, xr)` → (left, right, info) with lines as
  (a, b) meaning x = a*y + b; `E.merge_rows`, `E.polarity`, `E.snap_pair`, `E.crop_box`.
- `run2.py` — method registry. Register your methods from YOUR OWN file:

  ```python
  import run2, common as C, edges as E, sam2x as S
  L = C.L
  @run2.method("pins_anchor", "one-line description", kinds=("prehit", "last"))
  def pins_anchor(stem, weights, kind):
      f = C.frame_for(stem, kind); t0 = time.time(); img = C.read_frame(stem, f)
      ...  # lines = (left, right) as (a, b) tuples, mask = uint8 HxW or None
      prompts = {"points": [[x, y], ...], "labels": [1, ...], "bboxes": [[x1, y1, x2, y2]]}  # drawn on overlays
      return [run2.finish(stem, f, mask, lines, prompts, t0, {"any": "extra fields"}, kind)]
  if __name__ == "__main__":
      run2.run(["pins_anchor"], ["prehit", "last"], "sam2.1_b.pt", "", C.STEMS)
  ```

  `run2.run` writes `results/<method>_<kind><tag>.json` (one row per video, loop-1 schema:
  stem, frame, kind, ok, board_mae, board_max, within_1, within_2, corner_err_px,
  corner_err_mean_px, corners, prompts, latency_s, method, weights, desc, + your extras) and
  `overlays/<method>_<kind><tag>_<stem>.jpg` (mask tint, green = truth, red = prediction,
  yellow = positive prompts, magenta X = negatives, cyan = boxes, 3x pin-end inset).
- Loop-1 helpers in `../2026-09-12-sam2-lane-experiments/lane_sam.py` (imported as `L`):
  `L.trajectory(stem)` (on-lane ball frames + positions, cut at pin hit), `L.trajectory_all`,
  `L.pin_hit_frame`, `L.ball_points_on(stem, f)` / `L.ball_points_on_ordered` (ball path warped
  into frame f), `L.truth_corners(stem, f)`, `L.gt_y`, `L.lines_to_corners`, `L.score`,
  `L.transform(stem, f_from, f_to)` (2x3 affine camera motion), `L.warp_pt/warp_line/warp_mask`,
  `L.person_boxes(img)` (YOLO11n), `L.fit_edges` (loop-1 binary row-extreme fit),
  `L.robust_line`, `L.draw_overlay`, `L.predict_mask` (loop-1 binary path), `L.model(weights)`.
  `gt.load_annotation(stem)`, `gt.ball_gt`, `gt.board_from_corners`.

## Paths

- Python: `V=~/code/bowling-app/analysis-engine/.venv/bin/python` (torch, ultralytics 8.4.14,
  opencv, mediapipe 0.10.30). Run from this folder: `cd docs/research/2026-09-12-sam2-lane-experiments-2`.
- Frames (JPEG per frame): `$SCRATCH/frames/<stem>/<idx:05d>.jpg`; weights `$SCRATCH/weights/`
  (sam2.1_t.pt, sam2.1_b.pt, yolo11n.pt); loop-1 per-frame masks for `video_rev` / `video_span`:
  `$SCRATCH/masks/masks_<method>_<stem>.npz` (packbits, key = frame idx) + `lines_<method>_<stem>.json`,
  where `SCRATCH=/private/tmp/claude-502/-Users-toka-code-toms-gym/aec659a7-dd91-473a-be23-bf34027e9b97/scratchpad`.
- Videos + annotations: `~/code/bowling-app/analysis-engine/{sample_input.mp4, videos/input/*.mp4, annotations/<stem>/annotation.json}`.
- Write your own artefacts under `$SCRATCH/<your-agent-name>/` when they are not results/overlays.

## Rules

- Do NOT edit `common.py`, `edges.py`, `sam2x.py`, `run2.py` or anything in the loop-1 folder.
  Put your code in your own file(s) in this folder. If you need a helper that belongs in a
  shared file, copy it into yours.
- Every method must produce the loop-1 row schema through `run2.finish` so the review video can
  render it. Per-frame (tracking) methods must ALSO add `per_frame: [{frame, board_mae,
  fit_resid_px}]`, `perframe_mae_mean`, `perframe_mae_median`, `perframe_mae_max`,
  `perframe_within_2` to the row (see `_perframe_rows` in loop-1 `run_methods.py`) and save
  masks + lines the same way (`$SCRATCH/masks/masks_<method>_<stem>.npz`, `lines_<method>_<stem>.json`).
- Gotchas that cost loop 1 hours: ultralytics reads a flat point list as N single-point prompts
  (nest per object — `SamImage` does this for you); pick the mask component holding the prompts,
  not the largest (`E.component`); cut the ball path at pin hit (`L.trajectory` does); truth
  moves with the camera on two videos — always score frame f against `L.truth_corners(stem, f)`;
  CPU is shared with other runs, so latency numbers are indicative only; run only your own
  methods, never the whole registry.
- Use `sam2.1_b.pt` (comparable with the loop-1 table); if a method is promising, also run it
  with `--weights sam2.1_t.pt --tag _tiny` by passing tag `_tiny` to `run2.run`.
- Every number you report must come from a `results/*.json` row you produced. Look at your
  overlays before believing a number; a good MAE with a mask on the wrong lane has happened.
- Report: write `results/report_<agent>.md` (what you tried, table of numbers vs the baselines
  above, what worked, what did not and why, open questions, exact commands to reproduce) and
  reply with ONLY that path and the word DONE. Reports over 16 KB are truncated in transit, so
  the file is the deliverable. If blocked, write what you have and reply `BLOCKED: <why>`.
