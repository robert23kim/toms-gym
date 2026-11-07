# Judge: physics-smoother (stage path) on the holdout, 2026-11-07

Run fresh: `run.py <stem> --device mps` (defaults), one process at a time, no crash, no dev-only file needed, no code
edit. 0.23-0.25 s per stem (meta.wall_s; ~0.5 s process wall), on top of the stored loop-1 sam2-video track.
Outputs written by run.py to `experiments/physics-smoother/{tracks,overlays}/<holdout stem>`. A second pass with
`--fit-to-hand-pin-hit` was scored for information (rows in the JSON), then the default was re-run and re-scored
byte-identical. Scores with truth-derived fields live outside the repo in
`/Users/toka/pov-holdout/2026-11-07-glasses-pov-hook/work/judge_physics-smoother_scores/`;
`judge_physics-smoother.json` keeps the per-stem rows with every `truth_*` field stripped.

## Holdout (score_v2, same truth for both; p = physics-smoother, b = loop-1 sam2-video track it is fitted on)

| stem | fit (kind, chose_hook) | 60 ft at f - hand pin | path_err_far p / b | path_err_rms p / b | entry_err p / b | hook_err p / b | dir p / b |
|---|---|---|---|---|---|---|---|
| 191253 | hook (rise 1.09), yes | -3.7 | 1.49 / 1.51 | 2.95 / 2.66 | 3.06 / 3.47 | 2.63 / 2.95 | T / T |
| 191820 (gutter ball) | **hook (rise 7.42), yes** | +9.7 | 2.74 / 2.49 | 2.45 / 2.24 | **8.24 / 3.41** | 10.38 / 10.06 | T / F |
| 191913 | straight | -11.9 | 3.29 / 16.07 | 3.31 / 13.15 | 5.11 / 3.10 | 4.13 / 13.49 | F / F |
| 192142 | straight (no admissible hook) | -5.2 | 2.97 / 2.15 | 5.70 / 5.24 | 15.54 / 16.65 | 12.14 / 13.38 | T / T |
| 192636 | straight (no admissible hook) | -9.3 | 4.39 / 4.66 | 3.39 / 3.68 | 13.73 / 13.55 | 13.06 / 10.50 | F / T |
| **mean** | | | **2.98 / 5.38** | 3.56 / 5.39 | **9.14 / 8.04** | 8.47 / 10.08 | 60 / 60 % |

recall / far recall / px errors are identical to the baseline by construction (frames are the loop-1 frames):
far_recall 80.0, far_median_px 10.86. path_missing 0. entry_err <= 3 on 0 of 5 (baseline 0 of 5).

## Rule verdict (stage path): partial, leaning fails
- path_err_far mean improves 5.38 -> 2.98, **but all of it is 191913**, where the loop-1 track sits on a gutter object
  (raw boards ~ -8) and the fit, extrapolating the pre-drift line, lands back on the lane. Without 191913 the far error
  is 2.90 vs 2.70: worse. Per stem it wins 191253 (tie), 191913, 192636 and loses 191820 and 192142.
- entry_err mean regresses 8.04 -> 9.14 (191820 3.41 -> 8.24, 191913 3.10 -> 5.11).
- **It drew a hook on the one throw that does not hook back**: 191820 is a gutter ball (truth hooks_back false). The raw
  series goes monotonically right into the gutter; the board-range filter (-2..42) drops every frame from f456 on, the
  last kept points flatten at -1.6, and the convex term (exactly 8 points past bp 37 ft, the minimum) extrapolates that
  flattening 16 ft beyond the data into a 7.4-board rise to 5.8 at 60 ft. This is the "hook the measured track does not
  contain" failure, so the 'path works' condition fails on two counts.
- Hook selection is inverted on the holdout: the two clear hookers 192142 and 192636 get straight lines because the
  kinematic 60-ft crossing comes 5.2 / 9.3 frames before the hand pin hit and the default fit window ends there, which
  removes exactly the frames where the raw series rises (192142 f478-480, 192636 f453-457; 7 / 13 and 3 / 13 far
  frames inside the window). `--fit-to-hand-pin-hit` does not rescue them: both become `curve` (rise 0.94 / 0.00) and
  the means barely move (far 3.02, entry 9.16).
- 191253 is drawn as a 1.09-board hook. The task text calls 191253 monotonic (loop-1 truth); the loop-2 holdout truth
  marks it as hooking back, so on this truth the hook is right in kind but 2.6 boards short in size.
- Entry on 192142 / 192636 is scored at the observed pin contact several frames after cuts.json pin_hit (the composition
  judge's note); every method reading entry at pin_hit pays ~13-16 boards there, the baseline included.
- The ft model is the weak link on the holdout: implied 60-ft frame minus hand pin hit is -11.9 .. +9.7 (dev claimed
  -5.9 .. +3.3), and k = 0 on every holdout stem (constant speed). 191820 reaches only 51 ft at its hand pin hit.

## hook_in_raw_track (raw quad board series = run.py board_raw = loop-1 boards; LS slope x12 over pin_hit-12..pin_hit; |d| < 1 = flat; truth magnitudes kept out of the repo)
- 191253: raw +1.2 rise, truth rises -> SAME.
- 191820: raw -4.3 fall (rolls into the right gutter), truth points rise over the window but the truth flags a gutter ball with no hook back -> DIFFERENT by the slope test.
- 191913: raw -1.2 fall (track on a gutter object from f493), truth rises -> DIFFERENT (hook missed by the track itself).
- 192142: raw +3.3 rise (jump at f478-480), truth rises -> SAME; the fit window cuts those frames, so the fit misses it.
- 192636: raw +0.6 (flat by the 1-board rule, though the last 5 frames climb ~3 boards), truth rises -> DIFFERENT (weakly).

## dev reproduction
185645 re-run with defaults: all 30 score_v2 fields equal the row in `experiments/physics-smoother/results/dev.json`
(curve, bp 53, entry 7.17), and the track JSON is identical apart from meta.wall_s.

## Overlays
- dev final__185645: cyan edges on the lane, green path on the wood ending at the white cross on the pin row where the
  orange raw dots end; the near-end extrapolated line runs visibly left of the raw dots (the known 27-vs-19 near-end
  read), so the bottom half of the drawn path is not where the ball rolled.
- dev final__190115: green straight path on the lane through the raw dots, ends at the pin-row cross where the ball is. Good.
- holdout final__192142: green path on the lane hugging the right edge, ends at the pin-row cross at the end of the raw
  dots; but it is a straight line drifting LEFT from board ~1 at the foul line (extrapolated b0 1.2), with no out-then-back
  shape, on the clearest hooker in the holdout. Not a sensible bowling line.
- holdout final__191820: green path on the lane's right side, ends at a white cross on the wood (board 5.8) while the ball
  is in the gutter; the top-down panel's green line exits the right edge of the lane (gutter) and the hook back is the
  extrapolated part. Wrong end point.
