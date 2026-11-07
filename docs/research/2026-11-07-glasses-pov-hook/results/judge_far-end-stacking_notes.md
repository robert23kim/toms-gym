# Judge: far-end-stacking (stage ball) on the holdout, 2026-11-07

Rows: `results/judge_far-end-stacking.json` (truth_hook / truth_trend_boards stripped; raw scorer outputs, holdout tracks
and the dev-repro backup in `HO/work/judge_far-end-stacking/`, outside the repo). Scorer `score_v2.py`, holdout truth v2
at HO. Baseline = loop-1 sam2-video track `L1/results/tracks/<stem>.json` scored against the SAME holdout truth.

## Ran fresh
`run.py <stem> --device mps` on all 5 holdout stems, sequentially, exit 0, no path fixes, no dev-only or truth files
needed. 27 frames replaced per stem, rule purple_disc on all 27 every stem (the energy fallback never fired). Stage wall
7.0 / 8.6 / 5.8 / 6.4 / 5.8 s (mean 6.7). It does not re-run SAM: it consumes the loop-1 track, so end to end is
loop-1 wall (78.6 / 62.2 / 96.3 / 88.1 / 222.9) + stage, mean 116.3 s. Median shift vs loop-1 1.6 / 3.5 / 28.7 / 2.9 /
4.0 px (191913's 28.7 is the rescue off the gutter object).

## Holdout table (experiment / loop-1 baseline)
| stem | recall | far recall | med px | far med px | path_err_rms | path_err_far | entry_err | hook_err | dir ok |
|---|---|---|---|---|---|---|---|---|---|
| 191253 | 100 / 100 | 100 / 100 | 1.6 / 2.5 | 1.6 / 3.6 | 2.43 / 2.66 | 0.66 / 1.51 | 3.47 / 3.47 | 2.88 / 2.95 | T / T |
| 191820 (gutter) | 100 / 100 | 100 / 100 | 3.7 / 3.9 | 3.5 / 5.4 | 1.77 / 2.24 | 1.81 / 2.49 | 3.41 / 3.41 | 7.96 / 10.06 | F / F |
| 191913 | 100 / 33.3 | 100 / 0 | 1.7 / 28.6 | 1.5 / 30.8 | 1.48 / 13.15 | 1.27 / 16.07 | 3.10 / 3.10 | 1.68 / 13.49 | T / F |
| 192142 | 100 / 100 | 100 / 100 | 0.8 / 2.9 | 0.6 / 4.0 | 5.00 / 5.24 | 0.69 / 2.15 | 16.65 / 16.65 | 13.38 / 13.38 | T / T |
| 192636 | 100 / 100 | 100 / 100 | 2.0 / 6.5 | 2.1 / 10.5 | 1.47 / 3.68 | 0.55 / 4.66 | 13.55 / 13.55 | 11.48 / 10.50 | T / T |
| **mean** | **100 / 86.7** | **100 / 80** | **1.96 / 8.88** | **1.86 / 10.86** | **2.43 / 5.39** | **1.00 / 5.38** | **8.04 / 8.04** | **7.48 / 10.08** | 80 % / 60 % |

Per stem: better 5/5 on med px, far med px, path_err_rms, path_err_far; recall / far recall better 1/5 (191913), tied 4/5
at the 100 ceiling; entry_err tied 5/5 by construction (final_board is loop-1's); hook_err better 3/5, tied 1/5,
WORSE on 192636 (10.50 -> 11.48): the far-end min moved (4.44 -> 5.42) while the entry stayed loop-1's stale median, so
the hook arithmetic got worse even though the ball is now on the ball.

Calibration: holdout far px 1.86 vs dev 1.20 (parameters tuned on dev 185331); degrades out of sample, does not
collapse. Near-identical to lane-gated-ball's holdout far px (1.90); that experiment also improved entry_err, this one
cannot.

## Verdict: partial (stage ball)
Literal ball criterion: far_recall beats loop-1 on >= 3 of 5 AND the mean improves. It beats on 1/5 (191913 0 -> 100),
ties 4/5 at 100, mean 80 -> 100. The >= 3 of 5 half is unreachable (loop-1 already at 100 on 4 of 5), so 'works' is not
met as written. Not 'fails': every px and path_err metric improves on 5/5. 'partial' because hook_err regresses on
192636 while the px/path metrics improve, and entry_err does not move at all (the far-end boards are better but nothing
reads the entry from them). Also the experiment's own lens is unproven: its dev NOTES show N=1 (no stacking) = N=5
within 0.3 px; the gain is the purple-disc re-centring, not the temporal stacking. The orchestrator may read this as
'works on what the ball stage owns' with these caveats in view.

## Dev reproduction
Re-ran 185331 (outputs backed up first, restored after): frames, boards, lane_top_down and final_board identical to the
experiment's track (only meta.wall_s 5.4 vs 5.3); score_v2 output byte-identical to `experiments/far-end-stacking/results/
score_<stem>.json` (far px 1.9, path_err_far 0.56, entry_err 1.88, hook_err 1.38, direction_ok true). dev_reproduced = true.

## Overlays (each overlay shows frame pin_hit-4)
- final__185331 (dev): path inside the cyan quad, cyan replaced segment runs up to the pin deck, ends among the pins;
  board panel monotonic to the right with the far tail drifting further right (no hook drawn).
- final__185645 (dev): on the lane, ends at the deck; the near-end zigzag in the board panel is the loop-1 quad (not this
  stage).
- final__191913 (holdout): on the lane to the pins, cyan tail curls left at the deck (raw boards rise 6.4 -> 10.4); the
  orange loop-1 circles peel off right at the end.
- Raw-frame check at pin_hit-6 and pin_hit on 191913, 192636, 192142 (HO/work/judge_far-end-stacking/fes_pinhit_check.jpg): green
  experiment circle on the purple ball, sized to it, in all 6 frames; loop-1's grey circle sits on the ball-return
  object on 191913 and is bloated (r 12-20 vs 7-8) and offset on 192636 / 192142.
Verdict: the drawn path sits on the lane and ends on the ball at pin hit.

## hook_in_raw_track (raw boards{}, last 12 frames to the cut pin_hit, first -> min -> last; no fit; truth direction only)
- 191253: 5.4 -> 9.0 rising; agrees with the truth's last-12 direction (rising). Loop-1 rises less (5.3 -> 7.6).
- 191820: -1.5 -> -4.0 -> -3.9 falling; DISAGREES (gutter ball, boards < 0 extrapolated past the edge; loop-1 same).
- 191913: 6.5 -> 6.4 -> 10.4 rising; agrees (loop-1 -8.0 .. -8.2 on the gutter object, disagrees).
- 192142: 6.1 -> 5.7 -> 10.5 min then rise; agrees (hook back left is in the raw track).
- 192636: 9.1 -> 7.5 -> 14.3 min then rise; agrees (loop-1 rises only 4.4 -> 7.7).
4 of 5 agree; the one disagreement is the gutter ball.
