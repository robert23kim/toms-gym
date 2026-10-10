# Lane geometry: tracks JSON -> top-down lane

Applies to `results/tracks/<stem>.json` written by `track.py` (method `sam2-video`). Everything a top-down
renderer needs is in the JSON; `lane_geom.py` (cv-free, numpy only for the fit) implements the formulas below.

## Frames
Every frame number is a SOURCE frame of `/Users/toka/Downloads/<stem>.mp4`. Cut frame k = source `cut_start + k`
(`work/cuts/cuts.json`). `release_frame` / `pin_hit_frame` in the JSON are the cuts.json values (inputs).

## Per-frame lane quad: `lane["<f>"]`
Image pixels of source frame f (portrait, ~1376 x 1824). Left/right are IMAGE left/right, which is the bowler's
left/right (the camera looks down the lane).

| key | meaning |
|---|---|
| `pd_l`, `pd_r` | far-end corners: left / right lane edge at the top row of the engine's SAM lane mask, warped into frame f. Both share one y. |
| `fl_l`, `fl_r` | near-end corners: left / right lane edge at the mask's LOWEST row, warped into frame f. **Not the foul line** (`fl_is_foul_line: false` on every frame: the foul line is under the bowler, out of view). |
| `pin_y` | row (frame f) of the pin deck = 60 ft: the head-pin base when the engine accepted a pin-rack fit (`meta.pins_rack_accepted`), else the mask top. Can sit a few px above the `pd_*` row (185454: pd row 961.5, pin_y 951.0). Missing on fallback tracks: use the mean `pd_*` y. |

Lane edges are the straight lines `fl_l -> pd_l` (left gutter edge) and `fl_r -> pd_r` (right gutter edge); extend
them past both ends. Their intersection is the vanishing point `vp` (`lane_geom.vanishing_point(quad)`). The quad
comes from ONE SAM lane fit on a reference frame (`meta.lane_method`, `meta.pin_row_ref` is the pin row there),
carried to every frame by the engine's per-frame 2x3 affine camera model, so the quad moves with the head.

## Board (across the lane)
At the ball's row y: `xl = x on the left edge line at y`, `xr = x on the right edge line at y`,
`board = 1 + 38 * (x - xr) / (xl - xr)`. Board 1.0 is ON the RIGHT edge line, 39.0 ON the LEFT edge line, 20.0 is the
centre (right-hander convention, same as the truth and the engine's `board_from_lines` / `pin_rack.boards_from_lane_x`).
Unrounded. So the 41.5 in lane spans 38 board UNITS: one unit = 41.5 / 38 = 1.092 in, and inches from the right edge are
`x_in = (board - 1) / 38 * 41.5`. (A physical board is 41.5/39 = 1.064 in wide; physical board n's centre is at engine
board `1 + (n - 0.5) * 38/39`.) Check: a point exactly on the `fl_r -> pd_r` line gives `lane_point` board 1.0.

## Distance from the foul line (down the lane)
`s = (pin_y - vp_y) / (y - vp_y)`: 1 at the pin row, falling as 1/(y - vp_y) toward the camera (flat lane, pinhole
camera). `ft = a * s + b`, `a + b = 60`. The per-track `(a, b)` is in `lane_top_down_model`:
- `kind: "cv_fit"`: fitted per throw by least squares on the on-lane points between release and pin hit, assuming the
  ball is at the foul line at `release_frame` and rolls at constant speed: `a*(s-1) + 60 = v*(f - release_frame)`.
  Also gives `v_ft_per_frame`, `rmse_ft` (residual of the constant-speed fit) and `implied_pin_frame` (release + 60/v,
  an independent check against `pin_hit_frame`).
- `kind: "pin_only"`: a=60, b=0 (camera foot at the foul line), used when the fit has < 8 points or a falls outside
  30-120. This reads the near end several feet long (185454: 12 ft at release+3 vs 4 ft with the fit).
Function: `lane_geom.lane_point(quad, x, y, a, b) -> (board, ft)`.

## Precomputed: `lane_top_down`
List, one entry per track frame that has a quad: `{"f", "board", "ft", "on_lane", "zone", "board_engine"}`. `board`/`ft` are
exactly `lane_point(lane[str(f)], x, y, a, b)` with the track's model, so a renderer can use them as-is.
`on_lane` = 0.5 <= board <= 39.5 and 0 <= ft <= 60.5 (the half-unit / half-foot margins are deliberate slack for quad
jitter, not the edge positions); points past pin hit (deflection into the pins, ft > 60) are
kept with `on_lane: false`. `zone` is `lane`, `gutter_r` (board < 0.5), `gutter_l` (board > 39.5), `past_pins`
(ft > 60.5) or `behind_foul` (ft < 0). Draw `lane` and both gutter zones (clamp the board to the gutter, e.g. -1 / 40):
the holdout gutter ball 191820 has 21 `gutter_r` points after 31 `lane` points. `board_engine` is the engine's own board for that frame (computed in the reference frame,
pin-rack homography when accepted): within ~0.7 board of `board` on 185454.
`final_board` is the engine's read (median board of the last 5 rolling-segment positions at or below the pin row) and is
the number to print as the result; it is the one scored.

## Drawing a top-down lane (suggested)
Canvas W x H, foul line at the bottom, pins at the top, as the bowler sees it:
`X = W * (39 - board) / 38` (left edge line at X=0, right edge line at X=W; gutter points fall outside, clamp them into
a gutter band), `Y = H * (1 - ft / 60)`.
Landmarks in engine board units: arrows at ~15 ft (a shallow V, 12-16 ft in reality) on physical boards 5..35 =
engine 5.4, 10.3, 15.1, 20.0, 24.9, 29.7, 34.6; head pin at 60 ft, board 20.0; pins 12 in apart = 10.99 units, rows
0.866 ft apart (row 2 at 14.5/25.5, row 3 at 9.0/20.0/31.0, row 4 at 3.5/14.5/25.5/36.5).
Aspect: 60 ft x 41.5 in is 17.3 : 1; compress Y.

## Caveats
- The glasses lens is wide-angle and the lane edges are fitted as straight lines; distortion bends the near end.
- The camera model is affine per frame; head roll makes image rows tilt against the lane, so far-end `ft` jitters.
- `ft` depends on the release-at-foul-line and constant-speed assumptions (real balls slow ~10 % and hook);
  no truth exists for distance, only `implied_pin_frame` vs `pin_hit_frame` as a check.
- Stems with no quad (lane refused, 185121; no throw, 191900) have `lane: {}` and an empty `lane_top_down`.
