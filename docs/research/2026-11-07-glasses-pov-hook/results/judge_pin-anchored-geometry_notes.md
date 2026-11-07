# Judge: pin-anchored-geometry (stage lane) on the holdout, 2026-11-07

Ran `run.py <stem> --device mps` fresh from `experiments/pin-anchored-geometry/`, sequentially, one process, no code
edit. 4 of 5 holdout stems completed (3.3-3.9 s each). **191913 crashed** in 0.6 s:

    run.py line 239, in pin_ruler
    IndexError: index 118 is out of bounds for axis 0 with size 118

The crash is in the pin-ruler diagnostic (not used for the board): columns are filtered with `c < len(prof)` and
then `int(round(c))` rounds up to `len(prof)`. Not a path fix, so it is scored as a failure (no track). An
informative work-dir copy with the filter changed to `< len(prof) - 0.5` (`work/judge_pin-anchored-geometry/patched/`,
NOT used for the verdict) runs and still scores badly there: far recall 0, path_err_far 12.79, entry_err 16.92, no raw
board in the last 12 frames. That is loop 1's sam2 ball point drifting onto a gutter object from f493, which this
lane-only stage inherits unchanged.

Scores with truth-derived fields live outside the repo in
`/Users/toka/pov-holdout/2026-11-07-glasses-pov-hook/work/judge_pin-anchored-geometry_scores/`;
`judge_pin-anchored-geometry.json` keeps the per-stem rows with every `truth_*` field stripped.

## Holdout (score_v2, same truth for both; e = experiment, b = loop-1 sam2-video track)

| stem | far px e / b | path_err_far e / b | path_err_rms e / b | entry_err e / b | hook_err e / b | dir e / b |
|---|---|---|---|---|---|---|
| 191253 | 3.6 / 3.6 | **0.99** / 1.51 | **0.81** / 2.66 | **1.59** / 3.47 | 2.01 / 2.95 | T / T |
| 191820 (gutter ball) | 5.4 / 5.4 | **2.29** / 2.49 | 1.96 / 2.24 | **1.27** / 3.41 | 3.18 / 10.06 | F / F |
| 191913 | crash / 30.8 | crash / 16.07 | crash / 13.15 | crash / 3.10 | crash / 13.49 | - / F |
| 192142 | 4.0 / 4.0 | **1.62** / 2.15 | 1.22 / 5.24 | 12.42 / 16.65 | 11.80 / 13.38 | T / T |
| 192636 | 10.5 / 10.5 | 4.25 / 4.66 | 3.12 / 3.68 | 12.36 / 13.55 | 10.66 / 10.50 | T / T |
| mean (4 run) | 5.88 / 5.88 | **2.29 / 2.70** | 1.78 / 3.46 | 6.91 / 9.27 | 6.91 / 9.22 | 75 / 75 % |
| baseline over all 5 | - / 10.86 | - / 5.38 | - / 5.39 | - / 8.04 | - / 10.08 | - / 60 % |

Ball points are loop 1's, so recall / px errors are identical to the baseline on the 4 stems (by construction).
path_err_far improves on 4 of 4 stems that ran (mean 2.70 -> 2.29 on the same 4). entry_err <= 3 on 2 of 5
(191253, 191820); 192142 / 192636 are scored against the truth entry at the OBSERVED pin contact, several frames
after cuts.json pin_hit (same convention penalty as the sibling judges); against the truth's own
`entry_at_cut_pin_hit` (unscored, informative) the errors are 1.60 / 5.40 vs baseline 5.83 / 6.59. 192636's
remaining error is the far-end ball point (far px 10.5, path_bias_far -3.9), not the lane.

## Verdict (stage lane): partial
Rule: works iff holdout path_err_far mean improves AND entry_err <= 3 on >= 3 of 5. path_err_far improves (every stem
that ran), but entry_err <= 3 on only 2 of 5, and the run crashed outright on 1 of 5 where the baseline at least
produced a track. No mean regresses on the 4 stems; the regression is coverage (191913: no output). The dev claim
of a big hook_err gain (2.35 -> 0.20) does not carry over: holdout hook_err 9.22 -> 6.91 on the same 4, still large,
driven by the entry convention on 192142 / 192636.

## hook_in_raw_track (raw boards{}, LS slope x12 over pin_hit-12..pin_hit vs the truth path's direction; |d| < 1 = flat)
- 191253: raw +1.5 rise, truth rise -> same.
- 191820: raw -2.7 fall, truth rise -> DIFFERENT (gutter ball; the far boards are read off the right edge).
- 191913: crashed (patched copy: 1 raw board in the window, no direction) -> not measurable.
- 192142: raw +3.0 rise, truth rise -> same (hook back is in the raw series).
- 192636: raw +1.1 rise, truth rise -> same (weak; the far ball point is biased low).

## dev reproduction
185454 re-run (stored track and dev.json backed up first to `work/judge_pin-anchored-geometry/dev_before/`): every
score_v2 field except wall_s equals its row in `results/dev.json`; boards{} and path_fit identical, only meta differs.

## Overlays
- dev final__185454: cyan edges sit on the lane edges, green path on the wood with a smooth drift right, ends on the
  orange ball circle at the magenta pin row. Panel path is a clean, nearly straight line to ~11.
- dev final__185331: edges on the lane, path ends on the ball at the pin row near the right edge, but the image path
  has a sideways jog at mid-lane and the panel shows a horizontal jump at ~35 ft (monotone-ft drawing of a camera
  tilt) and starts at ~12 ft; entry 2.3 is the ball-point bias the NOTES already own.
- holdout final__192142: edges on the lane, green path on the wood, ends on the ball at the pin row. The panel does
  NOT show the hook: the curve runs at ~board 5-6 through 45-60 ft and continues past 60 ft onto the deck, and the
  entry marker (9.23 at 60 ft) sits ~3 boards left of the curve. The ft model overshoots (loop-1 known issue).
- holdout final__191820 (gutter ball): path on the lane hugging the right edge, ends at the right edge at the pin
  row where the ball is; panel ends off the lane to the right (entry -3.68). No invented hook.

## Addenda
- Why `partial` and not `fails`: path_err_far improves on 4/4 stems that ran; the regressions are coverage (191913
  crashed where the loop-1 track produced a scored row) and, marginally, hook_err on 192636 (10.50 -> 10.66). `works`
  is out of reach even without the crash: entry_err <= 3 on 2/5, and the patched 191913 reads 16.92 (baseline 3.10).
  The 5-stem baseline means are inflated by 191913's drifted loop-1 track (path_err_far 16.07); compare like-for-like
  on the same 4 stems (2.70 -> 2.29).
- 192142 panel, measured: the ft model's implied pin frame is 468.5 vs pin_hit 480 (192636: 444.5 vs 457; 191253:
  427.0 vs 437), so the model puts 60 ft ~12 frames early and the last-12-frame move (where the raw boards hook from
  5.96 at f467 to 9.23 at f480) is drawn at or past 60 ft. The data has the hook; the drawing hides it.
- Files this judge wrote inside the experiment folder: `tracks/<holdout stem>.json` and `overlays/final__<holdout
  stem>.jpg` for the 4 holdout stems that ran (run.py's fixed output dir), and a regenerated 185454 track/overlay
  (identical except `meta`; originals in `work/judge_pin-anchored-geometry/dev_before/`). None of them contain truth.
