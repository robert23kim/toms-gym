# Judge: composition (stage both) on the holdout, 2026-11-07

Config run fresh: `run.py <stem> --lane edge --smooth 3 --ball rerun --device mps` (the primary; run.py's own
defaults are `--lane auto --smooth 0`, so the flags were passed explicitly). Sequential, one process, no crash, no
dev-only file needed, no code edit. 1.7-2.6 s per video. The re-run ball (apptrack in-process, cached ORB scan)
is identical to the stored loop-1 appearance-prior track on all 5 holdout stems (max px diff 0.0).
Tracks/overlays: `work/judge_composition/{tracks,overlays}/`. Scores with truth-derived fields live outside the
repo in `/Users/toka/pov-holdout/2026-11-07-glasses-pov-hook/work/judge_composition_scores/`; `judge_composition.json`
keeps the per-stem rows with every `truth_*` field stripped.

## Holdout (score_v2, same truth for both)

| stem | far recall c / b | far px c / b | path_err_far c / b | path_err_rms c / b | entry_err c / b | hook_err c / b | dir c / b | fit |
|---|---|---|---|---|---|---|---|---|
| 191253 | 100 / 100 | 4.7 / 3.6 | 0.87 / 1.51 | 0.74 / 2.66 | 0.22 / 3.47 | 0.29 / 2.95 | T / T | line+hook |
| 191820 (gutter ball) | 87.5 / 100 | 4.7 / 5.4 | **8.23 / 2.49** | 5.95 / 2.24 | 1.32 / 3.41 | 5.11 / 10.06 | T / F | line+hook |
| 191913 | 100 / 0 | 3.9 / 30.8 | 1.93 / 16.07 | 1.53 / 13.15 | 0.21 / 3.10 | 3.08 / 13.49 | T / F | line |
| 192142 | 100 / 100 | 4.2 / 4.0 | 0.92 / 2.15 | 0.71 / 5.24 | 9.80 / 16.65 | 9.30 / 13.38 | T / T | line+hook |
| 192636 | 100 / 100 | 3.0 / 10.5 | 0.71 / 4.66 | 0.57 / 3.68 | 6.33 / 13.55 | 6.30 / 10.50 | T / T | line+hook |
| **mean** | 97.5 / 80.0 | 4.10 / 10.86 | **2.53 / 5.38** | 1.90 / 5.39 | 3.58 / 8.04 | 4.82 / 10.08 | 100 / 60 % | |

c = composition, b = loop-1 sam2-video track. path_missing 0 everywhere. entry_err <= 3 on 3/5 (191253, 191820, 191913).

## Rule verdict (stage both): works, with caveats
path_err_far mean 2.53 vs 5.38 and entry_err <= 3 on 3 of 5 -> works by the rule. No scored mean regresses.
- **The mean gain leans on 191913**, where the loop-1 track drifts onto a gutter object (far recall 0). Without it
  path_err_far is 2.68 vs 2.70, a tie; per stem the composition wins 4/5 and loses 191820 badly.
- **191820 (gutter ball) regresses 2.49 -> 8.23**: one frame. At f463 (pin_hit, camera whip) the per-frame edge fit
  takes a different component and the ball reads ~22 boards too high (the 3-frame median cannot act at the series end);
  the other far frames are +2-3 boards high (ball in the gutter, edge read on the gutter side). That outlier also
  makes the path fit accept a hook on a gutter ball the truth marks hooks_back=false, and the overlay panel draws the
  red path swinging from the gutter back to the headpin. This is the "drawn hook the throw does not have" failure.
- **Entry on 192142 / 192636 (9.8 / 6.3)** is scored against the truth entry at the OBSERVED pin contact, several
  frames after the cuts.json pin_hit the method evaluates at; the ball rises ~1.5-2 boards per frame there. Against
  the truth's own `entry_at_cut_pin_hit` the same entries are off 1.02 / 0.63 (unscored, informative). The baseline
  pays the same penalty (16.6 / 13.6). Any method reading entry at cut pin_hit will miss these two by construction.
- 191913 hooks back in the truth but the fit drew a line and the raw series falls over the last 12 frames (missed hook).
- As a ball stage alone it would fail its rule: far recall beats the loop-1 track on 1 of 5 stems only (191913);
  far median px is worse on 191253 / 192142 (4.7 / 4.2 vs 3.6 / 4.0), better on 191820 / 191913 / 192636.

## hook_in_raw_track (raw boards_raw, LS slope x12 over pin_hit-12..pin_hit vs truth path points; |d| < 1 = flat; truth magnitudes kept out of the repo)
- 191253: raw +4.0 rise, truth rise -> same (hook back).
- 191820: raw +8.9 rise, truth rise -> same sign, but the raw rise is the f463 22-board outlier; truth is a gutter ball (hooks_back false).
- 191913: raw -1.9 fall, truth rise -> DIFFERENT (hook missed).
- 192142: raw +5.3 rise, truth rise -> same (hook back).
- 192636: raw +6.0 rise, truth rise -> same (hook back).

## dev reproduction
185331 re-run with the same flags into `work/judge_composition_dev/`: every score_v2 field equals its row in
`experiments/composition/results/dev.json` (far 1.04, entry 2.08, hook 2.15, rms 0.92, recall 100). The track file
differs only in meta (wall time).

## Overlays
- dev final__185331: cyan quad on the lane edges, green path on the wood, ends on the magenta pin-row marker right of
  the headpin where the ball is; panel path rises at the deck (the accepted hook).
- dev final__185454: green path on the lane, straight drift right, ends at the pin-row marker; orange raw swirl off-lane
  is camera motion, trimmed as described.
- holdout final__192142: green path on the lane, ends at the pin-row marker; panel reads out right to ~6 at 46 ft and
  back left to ~12 at 60 ft, a sensible hook shape.
- holdout final__191820: green path on the lane and ends at the lane's right edge at the pin row, but the ball is in
  the gutter; panel's red path swings back to the headpin at the top (the f463 outlier). Wrong.
