# Integrate: one method for all 11 glasses-POV videos (2026-10-10)

## Choice
**sam2-video**, alone. Rule (fixed in advance): highest holdout mean recall among 'works' verdicts, board_err the
tiebreak. Works: cam-diff 73.0, lane-first 77.3, detector-tiling 78.6, **sam2-video 90.5**. appearance-prior
(98.8) is 'partial' (board <= 3 on 2/5, no board on 192636), so it is out. No composition: no judge measured a lane
stage on its own, and lane-first's holdout board misses (192142 3.4, 192636 5.2) are on the same two stems
sam2-video misses (5.0, 5.5), so there is no holdout number to justify a swap.

## What was built
- `track.py <stem> [--device mps|cpu] [--top-down-only]`: glue over `experiments/sam2-video/{run,prompt,sam_track}.py`
  (prompt, forward SAM 2 propagation, crop re-prompts, backward pass, near-release blobs, engine SAM lane pass),
  ~200 lines, no copied tracker code. Writes `results/tracks/<stem>.json` (tracks format, source frames) +
  `lane_top_down`, `lane_top_down_model`, `meta.fallback`, and `overlays/final__<stem>.jpg`.
- `lane_geom.py`: quad -> (board, ft) and back (`lane_point`, `image_point`, `fit_ft_model`). Spec:
  `results/lane_geometry.md`.
- `work/final/run_all.sh` (sequential driver), `work/final/score_final.py` (scoring, the only step that reads labels),
  `work/final/why.txt`, logs in `work/final/logs/`.
- Overlay: cyan quad and orange raw per-frame track (from run.overlay; the raw path swirls because the head moves),
  plus a **green** path = every lane/gutter point mapped through `lane_top_down` back into the shown frame (camera
  motion removed: it lies on the lane), and a top-down strip on the right (board 39 left, foul line bottom, arrows at
  15 ft, `b<final_board>`). Read: 185645, 191913, 191820 (gutter ball: 31 lane + 21 gutter_r points).

## Results (score_tracks.py; identical to the experiment's dev table and the judge's holdout table)
| stem | split | n | final board | recall % | median px | board_err | lane_err | wall s |
|---|---|---|---|---|---|---|---|---|
| 185121 | dev | 55 | - | 94.4 | 8.4 | - (lane refused) | - | 129.5 |
| 185331 | dev | 65 | 5.0 | 93.3 | 5.0 | 0.5 | 0.89 | 89.7 |
| 185645 | dev | 67 | 7.0 | 100 | 3.5 | 1.5 | 0.44 | 78.2 |
| 185454 | dev | 56 | 11.0 | 100 | 2.1 | 0.5 | 1.88 | 69.8 |
| 190115 | dev | 59 | 10.0 | 100 | 2.0 | 1.5 | 1.25 | 166.5 |
| 191900 | dev | 0 | - | (no throw) | | | | 0 |
| 191253 | holdout | 64 | 6.0 | 100 | 1.9 | 0.5 | 2.44 | 78.6 |
| 191820 | holdout | 56 | 1.0 | 95.8 | 4.2 | 1.5 | 6.25 | 62.0 |
| 191913 | holdout | 73 | 7.0 | 56.5 | 2.8 | 0.0 | 4.88 | 96.3 |
| 192142 | holdout | 70 | 5.0 | 100 | 2.7 | 5.0 | 2.74 | 88.1 |
| 192636 | holdout | 71 | 7.0 | 100 | 7.7 | 5.5 | 2.67 | 222.9 |
Dev: mean recall 97.5, board_err 1.0 over 4 boards, 4/5 strong. Holdout: mean recall 90.5, board_err 2.5, board <= 3
on 3/5, scorer pass 2/5 (191913 fails on recall: far-end crop pass drifts onto a gutter object from f493; its 0.0
board is luck, per the judge). 192142/192636 board misses come from the engine SAM lane quad, not the ball.
Determinism: a second full run of 191820 gave byte-identical frames, lane and board.

## Fallback
Rule: < 15 points or no final_board -> baseline yolo_chain_sam track. Triggered on 185121 (no board) and 191900
(no throw). Not applied on either: the 185121 baseline track also has no final_board and fewer points (44 vs 55),
and 191900 has no cut and no baseline run. `fallback_stems` is empty; `meta.fallback` in each track says why.

## Distance model (new here)
`ft = a*s + b`, `s = (pin_y - vp_y)/(y - vp_y)`, a+b=60, fitted per throw from release-at-foul-line + constant speed.
a = 66-73 on all 9 throws with a board (consistent across stems), rmse 0.3-0.9 ft on 7, 2.1-2.4 on 185331/190115.
Independent check: implied pin frame (release + 60/v) vs cuts.json pin hit: -2 (185454, 190115), -6 to -9 (185645,
191253, 192142), -11 to -16 (185331, 191913, 192636), +9 (191820, gutter ball). Early = the ball slows; the model has
no deceleration. The pin-only model (a=60, b=0) would put release+3 at 12 ft on 185454 (4 ft with the fit).
`lane_top_down.board` matches the engine's per-frame board within 0.05 near the pins (185645, 192142, 191253).

## Label-isolation checks
- Static: every module loaded by track.py (57 local files: track.py, lane_geom.py, the 3 sam2-video modules, the
  engine `scripts/sam_lane_pass.py` + `src/...`) scanned for the word: 1 hit, a comment in the engine's
  `lane_edge_detector.py:550` ("left of ground truth ..."), no file access. Canary: the same scan finds 26 in score_tracks.py.
- Runtime: full run of 191820 under `sys.addaudithook`: 2459 opens, 0 under a label path or the holdout cache; data files
  opened = cuts.json, the SAM weights, the output JSON (cv2 opens the cut in C, not audited).
- **Declared dependency**: release_frame / pin_hit_frame come from cuts.json and set the prompt window, the lane-pass
  segment and the reported window. For the dev stems cuts.json copied them from the 09-19 labels (its `method`
  field says so); for the holdout they are independent visual reads. So dev numbers are not end-to-end and window_err
  is 0 by construction everywhere.

## Release
After scoring: holdout label JSONs copied to `truth/`, holdout overlays to `overlays/`, and the holdout labelling notes
that existed only in the cache (`work/NOTES_3.md`, `work/a4/NOTES_4_holdout.md`, `work/20260915_191253_6cf2480f/NOTES.md`)
to `truth/holdout_label_notes/`. Judge notes were already in `results/judge_*_notes.md`.

## Open
- 191913 far end (crop re-prompt drifts at r 7-10 px; a jump gate in boards, not px, would catch it).
- Engine SAM lane quad right edge inside the real edge on 192142/192636 (boards 5.0/5.5 off); 185121 lane refused.
- Runtime: 62-223 s per video on MPS; the engine lane pass dominates when its first candidates fail.

## End-state checks
- Engine worktree `pov-engine`: `git status --short --untracked-files=all` prints 0 lines after all runs.
- Board scale: the engine puts board 1.0 / 39.0 ON the right / left edge lines (38 units = 41.5 in, 1.092 in per unit);
  `lane_point` returns exactly 1.0 / 39.0 for points on the two edge lines (185454 f350). lane_geometry.md and the
  overlay strip use `X = W*(39 - board)/38`.
- 191900 has no `final__` overlay (no cut).
