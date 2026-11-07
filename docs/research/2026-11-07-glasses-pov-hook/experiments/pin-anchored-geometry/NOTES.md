# pin-anchored-geometry (loop 2, stage: lane, 2026-11-07)

`run.py <stem> [--device mps|cpu]` (cv2/numpy only, ~3 s per video; `--device` is accepted and ignored). Input: the
loop-1 sam2-video track (`L1/results/tracks/<stem>.json`): ball points unchanged, its carried quads used only as
PRIORS. Output: `tracks/<stem>.json` (tracks format, SOURCE frames, raw per-frame boards in `boards{}`, per-frame
measured quads in `lane{}`, `stage: "lane"`, `path_fit` with `board_at_60ft` / `min_board`), `overlays/final__<stem>.jpg`
(pin_hit-4 frame, measured edges cyan, measured pin row magenta, whole track warped in as a green polyline through
(board, ft), far-end inset, top-down panel), `results/dev.json` (`L2/score_all.py tracks results/dev.json`).

## What the baseline overlays actually fail (looked before building)
- `L1/overlays/final__*.jpg`: the ONE SAM quad carried by a 2x3 affine is 15-47 px off at the near end (185454 f344:
  quad 305/520 vs true edges 320/567) and, on 185331, its right edge passes THROUGH the ball at the far end (f354:
  quad right 545 vs true 553, ball x 541). The quad is not curved, it is in the wrong place: the gate found no lens
  curvature (max resid < 3 px over 700-1200 px), so a straight line per edge per frame is enough IF it is measured in
  that frame.
- The engine pin_y sits 7-14 px below the visible pin bases at the far end (185454 f373: 919 vs 905 measured).

## Method
1. Decode the cut, keep release..pin_hit+4. Process frames in REVERSE (far end first: the carried quad is good there).
2. Per frame, per edge: prior = the next frame's measured line translated by `cv2.phaseCorrelate` (quarter-size grey,
   Hanning), else the carried quad. Pass 0 = a 1-D Hough: line anchored near the pin row (x scanned +-12 % of the lane
   width at the pin row), slope scanned prior +-0.6 in 0.004 steps, score = sum of the clipped signed gradient along
   the line (grey Sobel-x / p97 + 1.5 x Lab-b* Sobel-x / p97, 7-row box; gutter->wood is + for the left edge, - for the
   right). Rows within the ball (|dy| < 1.4 r + 6 and |dx| < 2.4 r + 12) and rows where the line has left the frame
   are skipped. Pass 1/2: per-row argmax in a band (8 %, then 6 % of the lane width, min 8/6 px) + 3-sigma line fit;
   ok when n >= 12 rows and rms <= 3.5 px. Pass 3: local refit +-max(40, 1.2 w) rows around the ball row in a 5 px band.
3. Board at the ball CENTRE row from the measured edges (the truth convention): `1 + 38 (x - xr) / (xl - xr)`.
   Emitted only when both edges are measured and 4.5 r <= lane width at the ball row <= 14 r (the sam2 r is inflated
   1.5-2x at the far end, so the gate is loose); otherwise no board for that frame (190115 f393 only).
4. Pin-base row per frame (last 24 frames): the lowest row of the headpin's white run (V - S map) in a +-2.5 % lane
   width column at the lane centre; the offset to the engine pin_y (median of the last 5) carries into frames without a
   read. Pin ruler per frame (last 8): 7 white pin columns at 6-in spacing -> px/in, headpin x -> ball board.
5. Entry = board at pin_hit_frame (cuts.json, the ball at the rack front), as a linear fit over pin_hit-4..pin_hit+1
   evaluated AT pin_hit (no trailing median). `min_board` = min of a 5-frame median over the last 60 % of the roll.
   ft model: loop-1 `fit_ft_model` on the non-degenerate frames.

## Dev results (`results/dev.json`, score_v2.py; baseline = loop-1 sam2-video, `L2/results/baseline_v2.json`)

| stem | path_err_rms base -> ours | path_err_far | entry_err | hook_err | direction_ok | boards | wall s |
|---|---|---|---|---|---|---|---|
| 185121 | - (no quad) | - | - | - | - | 0 | 0.1 |
| 185331 (hooks) | 5.60 -> 3.18 | 5.05 -> 4.30 | 1.88 -> 4.55 | 3.87 -> 0.14 | false -> false | 62 | 3.3 |
| 185454 | 4.64 -> 0.34 | 0.82 -> 0.42 | 0.61 -> 0.74 | 1.82 -> 0.02 | true | 53 | 3.0 |
| 185645 | 2.11 -> 0.72 | 1.42 -> 0.97 | 0.52 -> 0.80 | 1.90 -> 0.63 | false -> false | 64 | 2.9 |
| 190115 | 2.26 -> 0.36 | 1.05 -> 0.40 | 1.01 -> 0.44 | 1.80 -> 0.01 | true | 55 | 2.8 |
| mean (4) | 3.65 -> **1.15** | 2.08 -> **1.52** | 1.00 -> 1.63 | 2.35 -> **0.20** | 50 % -> 50 % | | 106.7 -> 2.5 |

recall / far recall 100 / 100 and the px errors are the loop-1 ball points (unchanged). path_missing stays 2.8 (185121).
Edges vs the truth's same-frame edge reads: within 0-2 px on every truth frame of 185454 / 185645 / 190115 incl.
the near end (190115 f396: 196.8/754.7 vs 196.2/757; 185454 f332: 299.9/881.1 vs 300/880 where the quad was 279/695).

## What worked
- Measuring the edges in the frame instead of carrying one quad: near-end boards go from 7-9 to 15-18 (truth 15-18)
  on 185454; path_err_rms 4.64 -> 0.34. The anchored slope scan is what made the near end work (a +-22 % band around a
  47-185 px wrong prior found nothing; the scan finds the dominant line, the band then refines it).
- Reverse order + phase-correlation carry: the first frames after release (ball r 60-90, camera looking down, carried
  quad 25 px wide) measure from the next frame's lines; `degenerate` frames use the prior lines' vanishing point for
  the top of the search instead of the bogus pin_y.
- hook_err 2.35 -> 0.20: with a clean board series the 5-median min no longer invents a 1.8-2 board hook on the flat
  throws (185454 track hook -0.03 vs truth -0.01; 190115 0.23 vs 0.25).
- Pin-base row per frame: 185454 f377 measured 893 vs truth pin_row_y 895 (engine 902); 190115 f443 640 vs 640.

## What failed / what this stage cannot fix
- **185331 far end is the BALL point, not the lane.** With the truth ball x and OUR edges the last-12-frame boards read
  5.1 / 4.4 / 4.2 / 4.8 / 3.8 / 5.2 / 6.6 vs truth 5.3 / 5.5 / 5.4 / 5.8 / 5.9 / 6.2 / 8.0 (0.4-1.4 low, rising = direction
  ok); with the sam2 x they read 4.5 / 2.6 / 1.6 / 1.0 / 0.4 / 1.6 / 2.3. The sam2 centre is 4-8.6 px RIGHT and 2.5-8.7 px
  UP of the truth's with r 14 vs 8: the mask takes the ball plus its blur/reflection; 185331 is the fastest across the
  image at the deck (7 px/frame vs 2-3 on the others) and its far_median_px_err is 8.3 vs 1.1-2.1. That is 3-4 of the
  4.3 boards of path_err_far and all of entry_err 4.55 (truth entry 6.88 +-4.39). A ball-stage fix: re-centre the far-end
  point on the purple component against the motion direction (loop-1 rule "re-measure on the purple component").
- The remaining 0.4-1.4 on 185331 is an edge convention: our gradient-max edges sit 2.7 px inside the truth's eye-read
  edges on that blurry deck (per-row residuals around the ball row are +-1 px, so the detector is consistent; the
  truth's own two crops of one frame differed by 4 px there). On the other three stems the convention agrees to 0-2 px.
- entry_err mean 1.63 vs 1.00: 185331 (ball point); on the other three 0.44-0.80 vs 0.52-1.01 (190115 better, 185454 /
  185645 0.1-0.3 worse: their truth entry is a mean of 6 reads 0.6-1.3 apart, inside the 1.0 uncertainty).
- direction_ok unchanged 2/4: 185331 misses because the ball-point bias grows along the last 12 frames (trend -2.3 vs
  +2.1); 185645 truth is flat (+0.02) and our raw series has two ball-point outliers (f295, f299: sam2 x 3.8-4.2 px off
  -> 2 boards) giving -1.27. Smoothing boards{} would flip it but that is a path-stage decision, boards{} stays raw.
- **Pin ruler disagrees with the edges by a constant factor and is NOT used for the board.** On every stem the 7 pin
  columns at 6-in spacing imply a 41.5 in lane that is 0.743-0.774 (mean 0.755) of the measured edge-to-edge width at the
  pin row (loop 1 saw px/in 1.67 vs 2.1 = 0.80). The ruler board is 1-7 below the edge board for a ball on boards 7-12
  (185454 10.1 vs 10.9 edge / 11.6 truth; 190115 3.5 vs 8.6 / 9.0; 185645 4.3 vs 6.7 / 7.5) and jitters 1-7 boards frame
  to frame on 185331 / 190115 (6 of 7 columns found, the comb snaps to a neighbour). The truth is edge-based, so the
  ruler would score worse by construction; whether the 25 % is the pin spacing, the gutter lip being read as the edge
  at the deck, or something else is open. The task text's "7-pin 33, 10-pin 7" is not the rule book (36.5 / 3.5 engine
  boards, 12 in apart); the code uses the rule book.
- 185121 (SAM lane refused in loop 1) still has no boards: this stage needs a quad prior to anchor the scan. Seeding
  the scan from the frame bottom (two dominant lines) was not tried (budget).
- The "ball bottom reaches the measured pin row" frame is 353 on 185331 and 294 on 185645 (pin_hit 358 / 299): on a
  tilting camera a pixel-row comparison is not a lane-depth test (the ball centre sits on the base row for 8 frames on
  185331), so entry stays at pin_hit_frame. The ft model's implied pin frame is 347.8 on 185331 (vs 358), 377.5 /
  289.2 / 443.1 on the others (vs 377 / 299 / 444).
- Overlay: the drawn path uses a monotone ft (cumulative max) so camera tilt does not zigzag it; the JSON keeps raw ft.

## Tuned on truth (dev)
The edge detector's band widths, the 0.35 strength floor, the rms 3.5 / n 12 acceptance, the ball mask radius, the
lane-width gate 4.5-14 r, and the choice to read the board at the ball CENTRE row from the EDGES (not the pin ruler,
not y+r) were all checked against the dev truth's per-frame left_x/right_x and board, iterating on 185454 then
185331 / 185645 / 190115. Holdout truth was never opened; `run.py` reads no truth file (the `--debug` flag prints the
dev truth beside the measurement and is off by default).

## Next
1. Ball stage: de-bias the far-end sam2 centre (purple component, motion direction); re-score 185331 with this lane.
2. Path stage: fit the board series (this stage's raw boards are clean enough that a smooth fit would pass
   direction_ok on 185645); keep hook presence a result of the fit, not an assumption.
3. Seed the slope scan without a quad (185121; and 191820 on holdout where SAM refused).
4. Settle the pin-ruler / edge 0.755 ratio with a tape measure or one frame of a known lane.

## Honesty lines (added after review)
- 185331 hook_err 0.14 is two ~4-board-low numbers cancelling (entry 2.33, min 0.86), not a measured hook.
- The entry is a linear fit over pin_hit-4..pin_hit+1 evaluated at pin_hit: no lag, but built from trailing positions.
  The raw board at pin_hit is in `boards{}`: raw vs fit = 185331 2.32 / 2.33, 185454 10.99 / 10.87, 185645 5.98 / 6.72,
  190115 8.55 / 8.55; it differs materially only on 185645 (the f299 ball-point outlier).
- Pin-ruler corroboration from the dev truth itself: 185454 truth `pin_columns_x` at f377 = 361..422 (61 px over the
  7 columns = 36 in) against truth edges 341/434 (93 px): 61 / 36 x 41.5 / 93 = 0.756, the same ratio our comb finds
  (0.743-0.774). The 0.755 is a fact of the image, not of the peak matcher.
