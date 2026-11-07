# lane-gated-ball (stage: ball) — loop 2, 2026-11-07

Folder: `experiments/lane-gated-ball/` (`run.py`, `run_dev.sh`, `tracks/`, `overlays/final__<stem>.jpg`, `results/dev.json`,
`results/ablations/`). Diagnostics that led here: `L2/work/lane-gated-ball/diag_far.py`, `diag_refine.py`, `crop_185331_*.jpg`.
Baseline: loop-1 sam2-video tracks scored with `score_v2.py` (`results/baseline_v2.json`).

## What was built
`run.py <stem> [--device mps|cpu] [--reprompt-every N] [--no-sam] [--no-refine] [--no-gates] [--tag T]`
reads `L1/work/cuts/cuts.json`, the cut, and the loop-1 chosen track `L1/results/tracks/<stem>.json` (its SAM points are the
coarse candidate source, its per-frame quads give boards). Per frame, release .. pin_hit+4:
1. **Camera model**: loop-1 cam-diff `Motion` (ORB + RANSAC homography chain, 1.6-1.8 s per cut). Used for the prediction
   when the quad is not trusted and for the overlay (every track point warped into the pin_hit-4 frame).
2. **Trusted quad**: at/after release+8, the ball row inside the quad span, `r_geo <= 20 px` and the quad smooth vs the
   previous frame (pin-deck row moves <= 10 % of the span, width ratio 0.85-1.18). The carried quad is garbage through the
   head swing: 185331 f304-310 has its pin-deck row at 20, 208, 392, 37, -75 px.
3. **Prediction**: with >= 3 real (non-coast) points on trusted quads, a line fit in lane coordinates (board, depth ratio s)
   over the last 4, mapped back through the current quad; else constant velocity through the homography chain.
4. **Gates** (only against a lane prediction): lateral <= 3 boards x frame gap; outside 0.5..39.5 rejected unless the
   previous point was already at/over the edge; radius 0.4-2.2 x r_geo; image jump <= (4 r + 40) x gap.
5. **Radius prior**: ball 8.5 in = 7.78 board units -> `r_geo = 0.5 * 7.78 * lane_width_px(row) / 38` from the quad.
   Within ~1 px of the truth r on every far dev frame (truth 7.0-13.2, r_geo 7.7-12.6); the SAM r is 1.2-1.9x bloated there.
6. **Far-end refinement** (r_geo <= 16): purple (H 112-170, S >= 30) disc-minus-annulus matched filter at r_geo, argmax
   inside +-max(2 r, 12) px of the gated candidate (or the prediction), penalised 0.015 per px of shift; accepted when
   response >= 0.40 and annulus <= 0.35; sub-pixel = purple-weighted centroid in the disc; the refined point is re-checked
   against the 3-board lateral gate (the window is up to +-16 px = ~6 boards at the deck; fired 3x on dev, 185645 x2 and
   190115 x1, metrics unchanged except 185645 path_err_rms 1.77 -> 2.44). Else the candidate stands.
7. **SAM 2 re-prompt** (2x crop, 320 px, 6 frames) from the prediction when the far window has no candidate, or every N
   frames with `--reprompt-every N`. Never needed on dev (the loop-1 track has a point on every frame).
8. No candidate: coast on the prediction (conf 0.2) up to 3 frames, then stop.
Output: tracks format, SOURCE frames, `boards{}` = `lane_point` of the loop-1 quad at the ball CENTRE row (same convention
as loop 1 so path metrics compare like for like), `final_board` = median of the last 5 boards <= pin_hit, `lane_top_down`,
`stage: ball`, `meta` with gate counts, sources and the first 60 gate events. `wall_s` = loop-1 wall (the SAM track it
consumes) + this stage (1.7-2.0 s); `stage_wall_s` is the stage alone.

## Dev table (`results/dev.json`; baseline_v2 in brackets)
| stem | recall | far recall | med px | far med px | path_err_rms | path_err_far | entry_err | hook_err | dir ok | gates fired | refined |
|---|---|---|---|---|---|---|---|---|---|---|---|
| 185121 (no lane) | 100 | 100 | 1.0 (1.4) | 0.9 (2.0) | - | - | - | - | - | 0 | 34 |
| 185331 (hooks) | 100 | 100 | 2.5 (6.0) | 2.1 (8.3) | 4.39 (5.60) | 1.28 (5.05) | 0.87 (1.88) | 1.91 (3.87) | true (false) | 12 lateral, 1 radius | 38 |
| 185454 | 100 | 100 | 1.1 (1.6) | 0.9 (1.1) | 4.35 (4.64) | 0.55 (0.82) | 0.59 (0.61) | 1.64 (1.82) | true | 1 lateral | 27 |
| 185645 | 100 | 100 | 1.4 (2.0) | 1.1 (1.9) | 2.44 (2.11) | 1.02 (1.42) | 0.86 (0.52) | 0.26 (1.90) | true (false) | 3 lateral, 2 lateral-on-refined | 36 |
| 190115 | 100 | 100 | 0.6 (2.1) | 0.6 (2.1) | 1.61 (2.26) | 1.24 (1.05) | 0.18 (1.01) | 0.18 (1.80) | true | 1 lateral-on-refined | 29 |
| **mean** | 100 (100) | 100 (100) | **1.32 (2.62)** | **1.12 (3.08)** | 3.20 (3.65) | 1.02 (2.08) | 0.62 (1.00) | 1.00 (2.35) | 100 % (50 %) | | |
Recall ties the baseline (already 100 on dev); direction_ok is informative only on 185331 (the other three truths are flat).
wall_s mean 108.6 (106.7): the stage adds 1.7-2.0 s on top of the loop-1 SAM track it consumes.

## Ablations on 185331 (`results/ablations/`)
| run | med px | far med px | path_err_far | entry_err | hook_err | dir ok | note |
|---|---|---|---|---|---|---|---|
| `--no-refine --no-gates` | 6.0 | 8.3 | 5.05 | 6.62 | 0.86 | false | reproduces baseline_v2 exactly: the pass-through is clean (canary) |
| `--no-refine` (gates only) | 3.7 | **7.1, far recall 57** | 3.69 | 5.88 | 0.34 | false | gates reject the bloated SAM points, nothing replaces them, 4 coasts, track lost |
| `--no-gates` (refine only) | 2.1 | 1.9 | 1.32 | 1.26 | 1.52 | true | the refinement carries the gain |
| gates + refine (default) | 2.5 | 2.1 | 1.28 | 0.87 | 1.91 | true | gates change 13 frames at the deck (pred+refine instead of base+refine), entry a little better, px a little worse |
| `--reprompt-every 4` | 2.1 | 1.9 | 1.32 | 1.18 | 1.60 | true | 10 SAM crop passes (3 s each, stage 45.5 s), 12 SAM candidates used: no gain over refine only |

## What worked
- **The geometric radius prior.** One number from the quad (lane width at the ball's row) predicts the far-end ball radius
  within ~1 px on all 4 quad stems; it is what lets the matched filter be the right size. SAM's own r is useless there.
- **Compact purple disc refinement at the deck.** The SAM mask centroid at the pins sits on a blob that includes the dark
  ball-return/pit area beside the ball (crop_185331_352.jpg: the ball is at the lower-left of a mask twice its size).
  A disc-minus-annulus response finds the ball itself: far median px 8.3 -> 2.1 on 185331, 2.1 -> 0.6 on 190115, every
  stem improves. This is the whole dev gain.
- **A camera-compensated overlay with the loop-1 track in grey.** The green line of this run is smooth to the pins on
  all four quad stems; the grey loop-1 line swerves 5 boards right at the deck on 185331.
- **The `--no-refine --no-gates` run reproducing the baseline numbers** is the pipeline canary.

## What failed / did nothing (with the number)
- **Gates without a replacement candidate lose the track** (185331 no-refine: far recall 57 %, 4 coasts). A gate is only
  safe when something else supplies the point; on 185331 the loop-1 SAM point is 3-6 boards off the prediction at the
  deck on 12 consecutive frames, so a gate-only tracker coasts off.
- **Gates on dev are a no-op or slightly negative on px** (far med 2.1 with vs 1.9 without on 185331; 0-1 events on the
  others). Their purpose (the 191913 gutter-object drift at f493) is a holdout failure and cannot be measured here.
- **SAM 2 re-prompting every few frames** adds 3 s per pass and nothing on dev (identical px to refine-only). On-demand
  re-prompting never triggered on dev because the loop-1 track has every frame.
- **Lane-coordinate gates before the quad is trustworthy kill the track**: the first version gated from release+8 and lost
  185645 and 190115 at release+13 (lateral x4, 3 coasts, recall 7 %). The carried quad is only usable once the head has
  settled (r_geo <= 20, smooth pin-deck row).
- **Radius gate from a garbage quad**: 185331 f306 r_geo 1.3 px (quad span 105 px) rejected a correct r 49 point.
- **Dark-disc (grey min) refinement**: picks gutters/ball-return, 21-56 px off on every far frame (diag_far.py).
- **A loose +-30 px refinement window around the SAM point** picks the pin-deck purple on 2 of 42 far frames (22 and 33 px);
  tying the window to the prediction and penalising distance removed both.
- **entry_err / hook_err on 185331 are now dominated by the truth's own spread**: truth entry 6.88 with uncertainty 4.39
  (reads -0.05 .. 8.73), and `final_board` at the centre row still reads ~0.9 low (lane-stage effect 1 from the gate result).
- The near-end zigzag in the top-down panel (185331 f304-310) is the garbage carried quad, same as loop 1; boards there
  are emitted for comparability and dominate path_err_rms (4.39) on both methods.

## What was tuned on dev truth
- REFINE_MIN_RESP 0.40, REFINE_MAX_ANN 0.35, DIST_PEN 0.015, window +-max(2 r, 12): chosen from `diag_refine.py`, which
  compared the filter's argmax with the dev truth ball centres on the far frames of all 5 dev stems (the 33/22 px outliers
  set the window and the distance penalty). Those are the SAME far frames the scorer uses, so the dev far-px numbers are
  in-sample for these thresholds; the only out-of-sample evidence is the smooth green line on the non-truth frames of the
  overlays.
- R_LO 0.4 / R_HI 2.2: from the observed SAM r / truth r ratios at the deck (1.2-1.9) on dev truth.
- NOT tuned on truth: LAT_BOARDS 3 (the brief), R_FAR 16 and R_GATE 20 (from the r_geo listing of the tracks), QUAD_SMOOTH
  0.10 / width 0.85-1.18 (from the 185331 quad listing, no truth), LANE_SEG_START 8 (loop-1 rule), COAST_MAX 3, SAM crop
  320 px / 2x / 6 frames (set once).
- Scorer mutation on this run's tracks: +25 px x on frames >= pin_hit-12 -> far recall 100 -> 0, recall 100 -> 46.2 / 40.0
  (185331, 190115); empty frames -> recall 0.

## Holdout expectations and risks (not measured)
- The lateral/lane gates should stop the 191913 drift onto a gutter object (45 px right at the deck = ~18 boards, far above
  the 3-board gate); the refinement then needs a purple disc inside +-16 px of the prediction, else the track coasts 3
  frames and stops before pin hit (recall loss, no false point).
- The gutter ball 191820 enters the gutter continuously; the lane gate keeps candidates when the previous point was already
  at/over the edge (board < 1 or > 39), untested.
- 185121-style stems (no quad) get the refinement with r = 0.8 x SAM r and no lane gates (0.9 px far on dev).
- 192142/192636 read 4-5.5 boards low in loop 1 for lane-stage reasons (centre row, quad carry); this stage changes the
  pixels, not the readout, so the board bias is expected to remain.

## Next
- Feed the refined far-end points and r_geo to the lane stage (y + r contact row, last-frame read) instead of the SAM r.
- Run the gates on the holdout cuts without truth and count events per stem (191913 should fire, the others not).
- Replace the carried quad at the near end with a per-frame fit so the top-down near end stops zigzagging.
