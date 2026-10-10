# lane-first: lane edges first, then the ball in lane coordinates (glasses POV, 2026-10-10)

Run: `/Users/toka/code/bowling-app/analysis-engine/.venv/bin/python run.py <stem>` -> `tracks/<stem>.json` (SOURCE frame
numbers, tracks format + per-frame `u` (fraction across from the left edge), `z_ft`, `board`, `src` det|fill) and
`overlays/<stem>.jpg` (pin_hit-4 frame from cuts.json, polyline + circles, lane quad, final board).
`score_all.py` -> `results.json` + the dev table. `score_dev.sh` runs + scores the 5 dev throws in one go.
No torch, no YOLO, no SAM: cv2 + numpy only, ~1.2 s per video (1.1-1.7 s on all 10 cuts, single process).

## What was built
- `lane.py`: half-res HSV mask of lane wood (H 5-45, S >= 8, V >= 120; the far lane goes whitish, S ~20, so S is
  loose and the hue + V carry it; gutters are dark, V < 60). Connected components; OUR lane = the component holding
  the predicted ball (hint), else the one overlapping the previous frame's lane (> 30 %), else the biggest touching
  the frame bottom. Left/right edges = RANSAC lines (x = a*y + b, 3 px) on the component's row extremes, excluding
  rows where the extreme is at the image border (edge out of frame). Pin-deck row = topmost row where the component
  keeps >= 50 % of the fitted width for 3 rows. Sanity: both slopes converge upward, >= 30 inlier rows per side,
  vanishing point above the pin row. Quad: fl = lowest row with both edges in frame (`fl_is_foul_line: false`
  everywhere, the foul line is never in frame), pd = pin-deck row.
- `tracker.py`: per frame, phase-correlation camera shift (quarter-res grey, |shift| < 150 px or discarded), lane
  fit, consistency check against the previous lane moved by the shift (> 200 px jump at a mid row or > 400 px VP
  jump = rejected; the previous lane is coasted for at most 3 frames, then the next fit is accepted). Purple candidates
  (`ball.py`: H 120-172, S >= 40, V 55-200, components >= 12 px) only inside the lane ROI (quad widened by 15 % of
  the width, clipped at the pin row: this is what removes the purple masking panels and the mural structurally).
  Lane-plausibility per candidate: u in [-0.03, 1.03], radius within 2.4x of the lane prior r = 0.102 * w(y)
  (8.5 in ball / 41.5 in lane; 5x when the prior is <= 14 px near the pins), lane wood in the annulus 1.3-2.2 r
  (>= 25 %) unless at the pin row. Kalman CV on [u, Z, du, dZ]; Z = K / (y - y_vp), K = 60 ft * (y_pd - y_vp) as a
  running median over frames with a stable pin row (per-frame pin-row jitter otherwise moves the depth by 50 px).
  Prediction: y from the camera-stabilised image velocity of the last consecutive detections (+ the shift),
  x from the Kalman u at that row when it agrees with the image prediction within 2.5 r + 40 px (else the image x,
  and u is reset: a lane jump had moved the frame). Gate max(2.5 r, 40) * (1 + misses/2), capped 300 px.
  Re-acquisition when nothing is in the gate: the best lane-plausible candidate with ratio <= 1.8x (1.5x when the pin
  row is not in frame), fill >= 0.4, wood ring >= 50 % (or at the pins; 0.3 / 25 % for the big near-end ball,
  r >= 40 px: that took 185121 from 88.9 to 94.4 %, nothing else moved), Z not more than 5 ft behind.
  Fills: up to 6 consecutive predicted points inside the lane; track ends after 12 misses.
  Start: first lane-plausible blob >= 300 px (or, with no lane, a round purple blob >= 2500 px in the bottom 40 %).
- `run.py`: every frame record carries `on_lane` (lane edges + pin row valid for that frame and u in [-0.03, 1.03])
  so a renderer can drop the pre-release in-hand points and the frame-top junk on 185121 (frames 296-311) without
  changing what the scorer sees (13 of 57 points there are off-lane). Final board = median of the Kalman-smoothed board over the last 5 detections whose radius is within
  1.5x of the lane prior (the tiny r 3-5 px blobs among the pins read u ~ 1.0 and pulled 185331 to board 1.0).
  release/pin_hit in the JSON are the tracker's own (first detection; last tracked frame), diagnostic only.

## Dev table (score_tracks.py, truth in L/truth; recall tolerance max(2 r, 20 px), gaps <= 6 interpolated)
| stem | recall % | matched | median px | board (truth) | board_err | lane_err boards | window_err | pass | det/fill | wall s |
|---|---|---|---|---|---|---|---|---|---|---|
| 185121 | 94.4 | 17/18 | 10.0 | 10.7 (12.0) | 1.3 | 1.42 | [1, 6] | pass strong | 47/11 | 1.1 |
| 185331 | 70.0 | 42/60 | 1.4 | 4.4 (4.5) | 0.1 | 2.47 | [1, 8] | pass | 53/9 | 1.6 |
| 185645 | 90.3 | 56/62 | 1.8 | 8.4 (5.5) | 2.9 | 2.03 | [0, 1] | pass | 51/6 | 1.2 |
| 185454 | 100.0 | 52/52 | 1.2 | 11.2 (10.5) | 0.7 | 2.75 | [0, 15] | pass strong | 54/6 | 1.3 |
| 190115 | 100.0 | 55/55 | 1.6 | 8.8 (8.5) | 0.3 | 2.51 | [0, 12] | pass strong | 54/6 | 1.3 |

Mean recall 90.9 % over the 5 throws (baseline yolo_chain_sam 72.0 %), mean board_err 1.06 (baseline 0.5-3.5 on 4 stems, none on
185121), pass 5/5 (baseline 1/5), strong 3/5. 191900 (no throw): no cut in cuts.json -> empty frames,
release_frame null, correct. Holdout cuts run without reading truth: 191253 board 6.8 (54 det), 191820 gutter ball
board 1.1 (35 det, track ends in the right gutter), 191913 7.7 (57), 192142 6.6 (58), 192636 7.3 (53); overlays
read for 192636 and 191820 only (both plausible: ball into the left-of-centre pins / into the right gutter).

Scorer mutation check (work/mutation_shift100.json): 185454 track + lane shifted +100 px, board +5 ->
recall 98.1 -> 13.5 %, median 1.2 -> 100.7 px, board_err 0.7 -> 5.7, lane_err 2.75 -> 44.8.

## What worked
- The lane ROI + lane-width radius prior: the ball is the only purple thing on the wood, so once the lane is right
  the detector has nothing to confuse it with; recall on the three "head up" stems is 90-100 % with median 1.2-1.8 px.
- The pin-row quad matches truth where truth has quads: 185454 f373 ours pd 329-420 @ y 906 vs truth 331-420 @ 906.
- Boards 0.1-1.3 off on 4 of 5 without any pin-ruler: board_from_lines convention (1 at the right edge) confirmed
  unflipped against truth.
- Across-lane coordinate u is camera-invariant and the Kalman on it survives head whips (191820, 185121 swing).

## What failed, with the number that killed it
- Depth Z from the per-frame pin row (Z = 60 * w_pd / w(y)): per-frame pd jitter of ~10 px moved the Kalman fill
  by 65-86 px (185331 f336 fill 65 px off, 185645 f272 86 px off); replaced by the VP form with a median K. Even so,
  Z is noisy at the far end (+-2 ft) and on 185121 (left edge out of frame, VP jumps 130 -> 416) so Z is NOT used for
  prediction any more, only reported: the lens's "Kalman in lane coordinates" survives only for u.
- Lane coasting with a stale lane: 8-frame coasting after a wrong pre-release lane locked every later fit out as
  "inconsistent" (185121 0 % and 185645 5 detections in one iteration); fixed by dropping the lane after the coast
  and by 3 frames max.
- Velocity from pre-release (ball-in-hand) detections extrapolated the prediction to y = 0 for 10 frames
  (185331 299-308, 185121 300-310): only pairs of consecutive detections within 3 frames of the last one count now,
  and v is dropped after 3 misses.
- Still open, by missed truth frame (work/ probe): 185331 loses 18 points: 4 in the release window whose truth
  radius is 1.4-2.6 px (tolerance 20 px; our blob is 32-83 px from those centres while the ball is 50-110 px wide,
  so those truth reads are not matchable by a blob centroid) and 14 at the tail 345-358 (ball r 2-7 px among the
  pins: the purple mask finds nothing and the fills drift 21-59 px right while the ball moves left). 185645 loses
  its last 6 (294-299, r 4-7 px, same tail problem). 185121 loses 355 (31 px). Next lever: a dark-round-blob
  detector against the white pin bases for the last 10 frames, gated to the lane ROI at the pin row.
  185645 board 8.4 vs 5.5 +- 2 (err 2.9, just under the 3.0 gate): its truth board reads spread 4.2-8.2 themselves;
  the overlay (f295) shows the quad on the right lane with the right edge on the gutter, so this is not a lane pick
  error, it is the usual ~2-board far-end width error (lane_err 2.03).
- Pin hit: the track runs 12-15 frames past the pins on 185454/190115 (purple fragments among the pins keep matching);
  pin_hit_frame in the JSON is not a usable pin-hit estimate.

## Tuned on dev truth (name it)
- Ball HSV range read from truth ball centres on dev frames (work/probe_hsv.py); lane HSV from hand-picked lane,
  gutter, mural, pin pixels on 185454 f373 (work/probe2.py).
- Every threshold above (pd validity > 60 px from the top, K sample range 40-600 px, ratio 2.4x / 5x, ring 25 % / 50 %,
  gate cap 300, coast 3, jump 200 px, misses 12, fills 6, final-board quality filter 1.5x) was set by reading per-frame
  dumps of dev tracks against dev truth (work/dump.py); nothing from holdout (never read).
- cuts.json's release/pin_hit were used only for the cut window itself (given) and the overlay frame, not for tracking.

## Files
run.py, lane.py, ball.py, tracker.py, common.py, score_all.py, score_dev.sh, results.json, tracks/, overlays/,
work/ (probes, per-frame logs <stem>_log.json, dump.py, mutation file, snapshots tracker_v3..v7; v7 = final).
