# physics-smoother (loop 2, stage: path) — 2026-11-07

Folder: `docs/research/2026-11-07-glasses-pov-hook/experiments/physics-smoother/`. Entry `run.py <stem> [--device]`
(numpy/scipy on the saved loop-1 sam2-video track, no torch, 0.2 s per stem), dev table `run_dev.py` ->
`results/dev.json`, selector mutation check `selector_check.py` -> `results/selector_check.txt`, sensitivity
`sweep.py` -> `results/sensitivity.json`. Outputs `tracks/<stem>.json` (tracks format, SOURCE frames, `boards{}` =
fitted boards, `boards_raw{}` = loop-1 boards, `path_fit{}`, `ft_model{}`, `stage: "path"`) and
`overlays/final__<stem>.jpg` (pin_hit-4 frame, lane edge lines of that frame's quad in cyan, pin row in yellow,
raw track re-projected as orange dots, fitted path as the green polyline, white cross = board at 60 ft, top-down
panel with raw dots + fitted curve + the breakpoint line).

## What it does
1. **Down-lane coordinate (ft) from a decelerating kinematic model anchored on the contact row.** The loop-1
   `ft = a*s + b` reads the ball CENTRE row; the ball touches the lane one physical radius lower
   (`r_phys = 4.25 in * lane_width_px(row) / 41.5`), which at the far end is 8-9 px = 5-7 ft. So the depth ratio `s`
   is taken at `y + r_phys` and `ft(t) = d0 + v0*t - k*t^2/2` (d0 in [0, 3], k >= 0, end speed >= 60 % of v0) is fitted
   by Huber least squares against `a*(s-1) + 60` on frames release+3..pin_hit with `s <= 1.03`. The pin row is 60 ft by
   geometry; the frame where the model reaches 60 ft is reported as `implied_pin_frame` and compared with the hand
   `pin_hit_frame` instead of forcing `ft(pin_hit) = 60` (see "ft anchor" below). Per-frame ft is the time model, not
   `a*s+b`, so camera-tilt jitter in `s` does not reach the path.
2. **Across-lane model** on (ft, raw board) for frames with `24 <= ft <= 60` (the last 60 % of the roll, the scorer's
   tail window), weights `s^2`: `board = b0 + b1*ft` (straight) or `+ c*max(0, ft - bp)^2` with `c >= 0` (hook: boards
   rising only, bp on a 35..55 ft grid, >= 8 points past bp), Huber delta 1 board, IRLS. The hook form is kept only if
   it beats the straight fit on BOTH an interleaved 2-fold held-out Huber loss (by >= 5 %) and clipped-residual BIC; it
   is labelled `hook` (`chose_hook: true`) only when the fitted rise from its minimum to 60 ft is >= 1 board, else
   `curve` (a decelerating drift that has not turned back). Frames with ft < 24 get the extrapolated skid line.
3. `path_fit = {kind, chose_hook, params, board_at_60ft, min_board, min_board_ft, residual_rms_boards, n_points,
   selection{cv, bic, reasons}, boards_by_frame}`; `final_board = board_at_60ft`; the engine's final board is kept in
   `meta.final_board_engine`. 185121 (no lane quads) passes through with `path_fit: null`.

## Dev table (score_v2 vs L2/truth; baseline = loop-1 sam2-video track as scored in results/baseline_v2.json)

| stem | fit | 60 ft at f (hand pin) | path_err_rms base -> new | path_err_far | entry_err | hook_err | direction_ok |
|---|---|---|---|---|---|---|---|
| 185121 | none (no lane) | - | - | - | - | - | - |
| 185331 (hooks) | straight | 352.1 (358) | 5.60 -> **3.26** | 5.05 -> 4.03 | 1.88 -> **5.22** | 3.87 -> 1.61 | false -> false |
| 185454 | straight | 379.1 (377) | 4.64 -> 3.56 | 0.82 -> 1.02 | 0.61 -> 0.32 | 1.82 -> 1.02 | true -> true |
| 185645 | curve (bp 53 ft, rise 0.56) | 297.2 (299) | 2.11 -> **3.52** | 1.42 -> 0.97 | 0.52 -> 0.35 | 1.90 -> 0.46 | false -> false |
| 190115 | straight | 447.3 (444) | 2.26 -> **0.73** | 1.05 -> 0.65 | 1.01 -> 0.66 | 1.80 -> 0.25 | true -> true |
| mean (4) | | | 3.65 -> **2.77** | 2.08 -> **1.67** | 1.00 -> 1.64 | 2.35 -> **0.84** | 50 -> 50 % |

recall / far recall / px errors are unchanged by construction (frames are the loop-1 frames). wall_s 0.19 s is on
top of the loop-1 track (106.7 s), not a speedup.

Beats the baseline on path_err_rms, path_err_far and hook_err; loses on entry_err (one stem) and ties direction_ok.

## What the decomposition said before building (why the numbers look like this)
`board(truth xy, quad)` vs `board(track xy, quad)` vs `board(track x, truth edges)` per truth frame on the 4 lane stems:
- **185331 far end is a BALL error, not lane and not path.** f348-358: track x is 5-8 px right of truth and 5-9 px
  above it (r 14 vs truth 8: the SAM mask is bloated by the deck reflection), while the quad edges at the truth row are
  within 1-5 px of the truth edges and read the truth xy at 5.1-6.0 (truth 5.3-7.95). Raw boards go 4.5 -> 0.4 -> -0.5,
  i.e. the track rolls into the right gutter. The fit follows the data, as it must: entry 1.66 vs truth 6.88. The
  engine's 5.0 was the median of f343-347 (10 ft before the pins) and only looks right because the track had not fallen
  off yet. No hook candidate is admissible (c <= 0 at every breakpoint: the data accelerates RIGHT at the end, which no
  convex model can draw), so no hook is drawn and hook_err 1.61 is the truth's own rise (which the truth notes say may be
  pin contact at f356-358).
- **Near/mid-lane boards are quad-carry error on every stem**: 185454 f332 reads 7.8 vs 18.2 (quad right edge 185 px off
  at the near end, error decaying 10 -> 6 -> 2.5 -> 0.5 boards at 8 / 24 / 36 / 58 ft); 185645 +3 / -3 / +2 / +3.3 at
  5 / 17 / 26 / 35 ft; 190115 -3.4 / -2.8 at 18 / 22 ft. That is why the board model is fitted on the last 60 % only and
  the near end is the extrapolated skid line: it wins on 190115 (0.73) and 185331, loses on 185645 (the s^2-weighted
  mid-lane points at 24-37 ft are +3 boards high there, the line through them is steep, and extrapolating it to the foul
  line reads 27 vs truth 19). path_err_rms is quad-limited, not path-limited.
- **Far-end jitter of +-1-2.5 boards on alternate frames** (185645 f291-299: 6.7, 7.6, 5.6, 7.6, 5.0; track x 4 px right
  of truth on the low frames) is what the fit removes: hook_err 1.8-2.05 -> 0.25-1.0 on the three flat throws, because
  `path_fit.min_board` is the curve's minimum, not the raw series' noise floor.

## ft anchor: geometric crossing vs hand pin hit
Implied 60-ft frame minus hand pin_hit: 185331 -5.9, 185454 +2.1, 185645 -1.8, 190115 +3.3 (loop-1 centre-row fits:
-11.5, -1.7, -6.1, -1.9). The contact-row correction moves every crossing later by 4-5 frames: the residual is now centred on the hand read (-5.9..+3.3) instead of always early. On 185331 the truth says the ball
centre is at the pin-base row at f350 and "partly behind a pin" from f352, so the hand 358 is late: forcing ft(358)=60
would stretch 6 deck frames over 0 ft. The task's `ft(pin_hit)=60` is therefore reported as a check, not imposed.
d0 sits on its 3 ft bound on all four stems: at release+3 the contact-row depth already reads > 3 ft (the ball is 3-4 ft
down the lane one frame after it lands), so the bound is active, not a fit failure. k is 0 on three stems and 0.0067
ft/frame^2 on 185331 (end speed 0.83 ft/frame = 0.67 of v0): the constant-speed read of loop 1 was fine; its 73 ft at pin hit came from
the centre row and the pin-row carry, not from deceleration.

## Selector mutation check (`results/selector_check.txt`, 40 seeds, 30 points on 24-60 ft, +-1.2 alternate-frame jitter)
straight 15 -> 6: straight 40/40 (entry 5.86 +- 0.15, true 6.0). hook 5.3@45 -> 7.95@60: hook 28/40, straight 12/40
(entry 7.18 +- 1.06, true 7.96). shallow 0.8-board rise: straight 40/40 (entry 5.25 +- 0.17 vs true 6.81: the refused
rise costs 1.6 boards). The selector never invents a hook on a straight series; it misses a real 2.7-board hook 30 % of
the time at this noise level, and a sub-1-board rise is refused by design (truth uncertainty floor 1.0).

## Sensitivity (`results/sensitivity.json`; read AFTER the default table, dev truth seen)
(fit_from_ft, s-exponent) -> path_err_rms / path_err_far / entry_err / hook_err / direction %:
(24, 2) default 2.77 / 1.67 / 1.64 / 0.84 / 50; (24, 4) 2.84 / 1.74 / 1.82 / 0.65 / 75; (30, 2) 2.86 / 1.69 / 1.77 /
0.65 / 75; (36, 2) 3.06 / 1.75 / 1.92 / 0.74 / 75 (185645 becomes `hook`); (0, 2) 2.60 / 1.76 / 1.77 / 1.33 / 50;
(0, 4) 2.79 / 1.72 / 1.76 / 0.77 / 75; (24, 0) 2.73 / 1.80 / 1.89 / 0.96 / 50. All within the 1-board truth floor of
each other; the default (fixed before scoring) was kept. The direction_ok flips are on 185645, where the truth trend is
+0.02 (flat) and the verdict follows which side of +-1 the fitted slope lands.

## What was tuned on truth
Every dev truth file was read in full before the design (the decomposition table above). Fixed before any score:
Huber deltas (1.5 ft, 1 board), the 35-55 ft breakpoint grid, >= 8 hook points, the 5 % CV margin, the 1-board rise
floor, release+3 start, s^2 weights, the last-60 % fit window (chosen from the quad-carry decomposition and the scorer's
tail window). Changed after a score: `min_board` was first taken over 0-60 ft and read a 3.3-board "hook" on 185454 from
the near-end extrapolation; it is now the minimum over the fit window (24-60 ft), the same tail the scorer uses for the
raw series. Nothing else was changed after scoring; the sweep is reported, not adopted.

## What failed / is out of scope
- 185331 entry (5.22) and far path (4.03): ball stage. The SAM mask drifts up-right onto the deck reflection in the last
  10 frames; fix in the ball stage (re-measure the centre on the dark disc, cap r at r_phys) and this path stage will
  follow it. A convexity prior cannot rescue it: the fit sees 30 frames of decelerating drift and then 6 of acceleration
  to the right, and the Huber line splits the difference.
- Near-end extrapolation on 185645 (+1.4 path_err_rms). The alternative (fit the whole roll) trades it for 185454's
  rising artifact; both are quad carry.
- direction_ok 50 %: unchanged. It is informative only on 185331 (truth +2.14), where the track points the wrong way.
- 185121: no lane, nothing to fit.
- No holdout stem was run or read.

## Variant: fit up to the hand pin_hit_frame (`--fit-to-hand-pin-hit` / `PS_FIT_TO_HAND_PIN=1`, `results/dev_fit_to_hand_pin.json`)
The default fit domain ends where the kinematic ft reaches 60, so frames between that crossing and the hand
`pin_hit_frame` are dropped (185331: 6 frames, 185645: 2). The loop-2 gate evidence names exactly those frames as the
far-end cause on the holdout hookers (192142 f478-482), so the integrator needs the switch. On dev it changes the
means to path_err_rms 2.69 / path_err_far 1.85 / entry_err 2.10 / hook_err 0.75 / direction 50 % (default 2.77 / 1.67 /
1.64 / 0.84 / 50): 185645 flips from `curve` to `straight` (entry 7.17 -> 5.91 against truth 7.52, far 0.97 -> 1.61)
because its two extra frames (f298-299, raw 5.6 and 5.0, track x 4 px right of truth) pull the tail down; 185331 is
unchanged in kind (straight, entry 1.66 -> 1.57); 185454 and 190115 are identical (their crossing is after the hand read).
Dev cannot settle which domain is right, because the only dev frames it adds are the drifted ones; it is left off by
default and reported. `lane_top_down[*].in_fit_window` marks the frames the board model was fitted on; frames outside it
(near end, past the crossing) are the extrapolated skid line and a renderer should draw them differently.
