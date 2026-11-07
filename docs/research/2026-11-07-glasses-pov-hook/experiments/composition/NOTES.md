# composition: appearance-prior ball over a per-frame lane stage (loop 2, stage both, 2026-11-07)

Run: `PY run.py <stem> [--device mps] [--lane auto|sam|edge] [--smooth 3] [--refine] [--ball file|rerun] [--out-dir DIR]`
-> `tracks/<stem>.json` (tracks format, SOURCE frames, `boards{}` per frame, `path_fit`, `stage: "both"`) and
`overlays/final__<stem>.jpg`. `run_dev.sh <tag> <args>` runs + scores the 5 dev stems into `work/<tag>/`.
Primary config (what `tracks/`, `overlays/`, `results/dev.json` hold): `--lane edge --smooth 3`. Alternate
`--lane auto --smooth 3` (engine SAM quads, edge fallback) in `tracks_auto/` + `results/dev_auto.json`.
All variants side by side: `results/variants.json`. No torch, no SAM: 0.5-0.7 s per stem (see wall_s caveat).

## Headline (dev means, score_v2; baseline = loop-1 sam2-video tracks, `L2/results/baseline_v2.json`)

| config | far recall | path_err_far | entry_err (n) | hook_err | path_err_rms | path_missing | direction_ok | wall s |
|---|---|---|---|---|---|---|---|---|
| baseline (loop 1) | 100 | 2.08 (4) | 1.00 (4) | 2.35 | 3.65 (4) | 2.8 | 50 % (2/4) | 106.7 |
| **primary: edge lane + smooth 3** | **100** | **0.67 (5)** | **0.79 (5)** | **0.94** | **0.61 (5)** | 0.2 | 100 % (5/5) | 0.6* |
| auto: SAM quads, edge fallback, smooth 3 | 100 | 0.79 (5) | 0.35 (5) | 1.10 | 3.13 (5) | 0.2 | 100 % | 0.3* |
| sam only (no fallback) | 100 | 0.73 (4) | 0.22 (4) | 1.39 | 4.23 (4) | 2.8 | 100 % (4/4) | 0.1* |
| edge raw (no smoothing) | 100 | 0.72 | 0.82 | 0.94 | 0.64 | 0.2 | 100 % | 0.6 |
| edge + row refinement (`--refine`) | 100 | 1.54 | 0.56 | 1.26 | 1.22 | 0.2 | 100 % | 0.6 |
| edge + smooth 5 | 100 | 0.65 | 0.76 | 0.97 | 0.60 | 0.2 | 100 % | 0.6 |

Per stem, primary (path_err_far / entry_err / hook_err / fit): 185121 1.34 / 0.90 / 0.72 / line; 185331 1.04 / 2.08 / 2.15 /
line+hook; 185454 0.24 / 0.03 / 0.45 / line; 185645 0.52 / 0.88 / 0.93 / line; 190115 0.21 / 0.06 / 0.47 / line.
Baseline per stem path_err_far: - / 5.05 / 0.82 / 1.42 / 1.05.
*wall_s covers reading the cut, the stored ball track and the per-frame lane stage only. The loop-1 appearance-prior
tracker (1 s + 8-10 s ORB/YOLO scan, cached) is read from `L1/experiments/appearance-prior/tracks/` (`--ball rerun`
re-runs it in-process: identical output on 185454, 2.0 s), and the sam/auto variants read the loop-1 engine SAM lane pass
(43-195 s per video) from `L1/results/tracks/`. The primary variant needs neither SAM nor torch.

## What was built
- **Ball stage** = loop-1 appearance-prior `fixed` track (purple hue window for the big ball, camera-compensated
  blackhat x motion x hue peak at the far end). Scored alone with score_v2 it has 100 % far recall on all 5 dev stems
  and far median px 1.6-3.4 (sam2-video: 1.1-8.3; 185331 8.3 -> 2.5). Far-end centre bias vs truth (median over the
  far window): dx -1.2..+0.7 px, dy -1.5..-3 px (reads 2 px high), no x bias to correct. A dark-disc re-centring
  (blackhat centroid within 1.5 r) was tried and made it worse on 4/5 stems (|d| 2.4 -> 3.3 on 185645): not used.
- **Lane stage `sam`**: the engine SAM per-frame quads loop 1 stored with the sam2-video track (one SAM fit on a
  reference frame, carried by the engine's per-frame 2x3 affine; the quad was prompted by the sam2 ball, not this one).
- **Lane stage `edge`**: `L1/experiments/lane-first/lane.py` `fit_lane` on EVERY frame (half-res wood HSV mask,
  component chosen by the ball position, RANSAC line per gutter edge on the component's row extremes, pd row = mask
  top), no temporal carry at all. Frame rejected when the ball reads outside u [-0.15, 1.15] (185121 f304/f306, the
  ball is out of frame there anyway). 0 failures on the other 4 stems.
- **Fallback** (`--lane auto`): sam quad when loop 1 has one for the frame, else edge. Used on 185121 (SAM refused in
  loop 1: 72/72 frames edge) and on the 3 pre-lane frames f298-300 of every other stem; sam elsewhere. 191820 (holdout,
  SAM refused) would take the same path; not run (holdout).
- **Board**: `1 + 38 (x - xr)/(xl - xr)` at the ball CENTRE row from that frame's quad (dev truth convention);
  `boards_contact` (y + r) is written beside it, not scored. `--smooth 3` = rolling median over 3 consecutive track
  frames (`boards_raw` keeps the raw series).
- **path_fit**: over the roll tail (last 60 % of release..pin_hit) least-squares line vs line + upward quadratic beyond
  a breakpoint (grid over fb); the hook is kept only if it removes >= 0.5 boards RMS AND the fitted path rises >= 1.0
  board after its minimum (`params.hook_rejected` records the rejected gain otherwise). Entry (`board_at_60ft`) =
  Theil-Sen line over the last 10 frames <= pin_hit evaluated AT pin_hit (fixes the engine's median-of-last-5 lag).
  `min_board` = minimum of the fitted path (a line's minimum is at an end: no hook invented from jitter).
  Result: line+hook on 185331 only (rise 4.2, rms 1.42 -> 0.45); line on the other four (hook gains 0.21-0.26 boards
  RMS, rises 0.6-0.95, rejected).
- **ft**: loop-1 `lane_geom` model (release at the foul line, constant speed) with s rescaled so the ball at pin_hit
  reads 60 ft: the edge quad's pd row is the wood-mask top, 0-15 px below the pin bases (185331: 562 vs truth 549), so
  without it ft overshot (implied_pin 342 vs 358). After: implied_pin 351.8 / 353.0 / 379.6 / 294.4 / 446.4 vs pin_hit
  356 / 358 / 377 / 299 / 444 (4-5 frames early on 3 stems, 2.5 late on 2), rmse 2.4-9.8 ft. Quads whose pd row is at
  the frame top (< 60 px: the release frames, the camera looks down and the far end is out of frame) carry a board but
  no ft (185121 f298 read 42 ft before the gate). ft is not scored; it drives the top-down panel only.
- **Overlay**: pin_hit-4 frame; orange = raw track (camera swirl, trimmed to lane/gutter zones and <= pin_hit), green =
  every point -> (board, ft) in its own quad -> image point in the shown frame's quad, cyan = the quad used on that
  frame, magenta = pin row + entry marker, panel = board vs ft with the raw boards (dots) and the fitted path (red).

## What the lens taught
- **The far-end miss on the dev hooker was the ball, not the lane.** Loop-1 185331: sam2-video ball 8.3 px off at the
  deck -> boards fell into the right gutter (-0.5) while truth rose 5.3 -> 7.95. Same SAM quad, appearance-prior ball:
  f354 reads 5.64 vs truth 5.91. path_err_far 5.05 -> 0.84 (sam quads) / 1.04 (edge), direction_ok false -> true.
- **The SAM quad carried by the affine is wrong mid-lane, right at the pins.** sam variant path_err_rms 4.2-6.6 on
  185454/190115 (reads 7-9 at f332-350 where truth is 14-18) but path_err_far 0.4-1.2. A per-frame edge fit fixes the
  middle (rms 0.22-0.92) at a small cost at the pins on 185331/185645 (far 0.84 -> 1.04, 0.52 -> 0.52) and a gain on
  190115 (1.17 -> 0.21).
- **Entry is the one metric where the carried SAM quad wins** (0.35 vs 0.79), on 185331 (0.23 vs 2.08) and 185645
  (0.08 vs 0.88). 185331's truth entry is 6.88 +- 4.39 (edge/ball-ruler reads 6.7-8.7, pin ruler 0-3.8); the edge
  variant reads 8.96 and its last raw boards 8.7-9.4 at f357-358 against truth 7.95, i.e. 1-1.4 high at the deck,
  consistent with the ball being 3.5 px left of truth at f354 (538 vs 541.5 = 1.4 boards at 2.4 px/board).
- **The hook is real only on 185331 and the fit says so**: line+hook accepted there alone (truth hooks_back true,
  trend +2.14 over the last 12 frames). hook_err 2.15 there is the far-end +1.4 bias plus the quadratic rise 4.2 vs
  truth 1.6-2.7 (truth: "without f358 the rise is 0.9"). On the four monotone throws the line fit gives hook_err
  0.45-0.93 vs baseline 1.8-1.9 (raw-min hooks invented by jitter).
- **Row refinement hurts.** Snapping each fitted edge to the strongest grey step within +-12 px at the ball row moved
  the right edge 8-9 px inward on 185331 (615 -> 607 at f342 where truth reads 614.5): the strongest step is the
  gutter-capping highlight, not the wood/gutter lip. path_err_far 0.72 -> 1.54. The RANSAC line over the whole edge is
  the better local estimate; left as `--refine`, off.
- **Smoothing 3 vs 5**: 0.67/0.79 vs 0.65/0.76 (far/entry); 3 kept as the smaller assumption at a far end that moves
  1.5-2 boards per frame on a hooker.

## Tuned on dev truth (declared)
- Everything loop 1 tuned: appearance-prior hue windows / motion thresholds and lane-first HSV + RANSAC thresholds
  were set on dev truth in loop 1 (their NOTES.md).
- This loop: the choice of primary variant (edge+smooth3 over auto) was made after reading the dev table; smooth
  window 3 vs 5, the hook gates (0.5 boards RMS, 1.0 board rise), ENTRY_N 10 and the refine window were each set
  after one look at dev scores; `--refine` was dropped after it scored worse on dev. The u gate [-0.15, 1.15] and
  the s_pin rescale range were set from the 185121/185331 dumps. Holdout truth was not opened; holdout stems were not run.
- cuts.json release/pin_hit are inputs (window_err 0 by construction): the ft rescale, the tail window and the entry
  frame all read them.

## Canaries (score_v2 on the 185454 primary track, in memory)
as-is path_missing 0 / far 0.38 / entry 0.21; boards + lane_top_down + boards_by_frame emptied -> path_missing 13 (=
truth points), path_err_far None; frames emptied -> recall 0 / far 0; +25 px on frames >= pin_hit-12 -> far recall 0,
far median 25.0 px. The ft rescale changed no scored number (means identical except wall_s).

## Open / not done
- 185331 entry/hook: the +1.4-board deck bias comes from the ball stage (3.5 px); a far-end ball refinement that does
  not use the blackhat centroid is the next lever (e.g. purple-weighted centroid gated by the lane row width).
- 185121 reads 11-12.4 where truth reads 9.5-11.3 at f348-356: the fitted left edge sits 9-10 px right of truth's
  left_x on those frames (blurred diagonal left gutter), ~1 board. A left-edge-specific fit (two-sided step) untried.
- The per-frame quad jitters +-8 px at the far end (185121 f347 xl 92 between 96 and 108), which is why the warped
  green track wiggles in the overlays; the smoothing only acts on the board series. A lane-relative temporal filter
  (smooth the width and centre at the ball row) was not tried.
- Only dev was run. Holdout (incl. the SAM-refused 191820 gutter ball, where the ball reads u > 1) is for the judge.
