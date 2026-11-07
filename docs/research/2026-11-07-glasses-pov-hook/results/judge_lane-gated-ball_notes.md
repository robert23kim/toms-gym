# Judge: lane-gated-ball (stage ball) on the holdout, 2026-11-07

Rows: `results/judge_lane-gated-ball.json` (truth_* fields stripped; scorer outputs and the dev-repro track kept in
`HO/work/judge_lane-gated-ball/`, outside the repo). Scorer `score_v2.py`, holdout truth v2 at HO. Baseline = loop-1
sam2-video track `L1/results/tracks/<stem>.json` scored against the SAME holdout truth.

## Ran fresh
`run.py <stem> --device mps` on all 5 holdout stems, sequentially, exit 0, no path fixes, no dev-only files needed.
Stage wall 1.8-2.3 s per stem. It does NOT re-run SAM: it consumes the loop-1 sam2-video track, so `wall_s` (mean 111.8)
= loop-1 wall (consumed) + stage. SAM re-prompt never fired on the holdout (reprompts 0 on all 5).
Gate events: 191253 radius 3; 191820 radius 2, coast 2; 191913 lateral 4 + radius 17 (21 pred+refine); 192142 lateral 1
+ radius 4; 192636 lateral 13 (13 pred+refine).

## Holdout table (experiment / loop-1 baseline)
| stem | recall | far recall | med px | far med px | path_err_rms | path_err_far | entry_err | hook_err | dir ok |
|---|---|---|---|---|---|---|---|---|---|
| 191253 | 100 / 100 | 100 / 100 | 1.7 / 2.5 | 1.8 / 3.6 | 2.37 / 2.66 | 0.99 / 1.51 | 1.16 / 3.47 | 0.56 / 2.95 | T / T |
| 191820 (gutter) | 100 / 100 | 100 / 100 | 3.5 / 3.9 | 4.4 / 5.4 | 2.00 / 2.24 | 2.11 / 2.49 | 1.64 / 3.41 | 3.37 / 10.06 | F / F |
| 191913 | 100 / 33.3 | 100 / 0 | 1.5 / 28.6 | 1.4 / 30.8 | 1.53 / 13.15 | 1.47 / 16.07 | 0.60 / 3.10 | 0.95 / 13.49 | T / F |
| 192142 | 100 / 100 | 100 / 100 | 1.0 / 2.9 | 1.0 / 4.0 | 4.99 / 5.24 | 0.85 / 2.15 | 11.95 / 16.65 | 8.68 / 13.38 | T / T |
| 192636 | 100 / 100 | 100 / 100 | 0.9 / 6.5 | 0.9 / 10.5 | 1.32 / 3.68 | 0.42 / 4.66 | 8.22 / 13.55 | 6.14 / 10.50 | T / T |
| **mean** | **100 / 86.7** | **100 / 80** | **1.72 / 8.88** | **1.90 / 10.86** | **2.44 / 5.39** | **1.17 / 5.38** | **4.71 / 8.04** | **3.94 / 10.08** | 80 % / 60 % |
Per stem vs baseline: better on 5/5 for med px, far med px, path_err_rms, path_err_far, entry_err, hook_err; recall and
far recall better 1/5, tied 4/5 (baseline at 100); worse on 0 stems for every metric.

## Verdict: works (stage ball), with a rubric gap stated
The literal ball criterion (far_recall beats loop-1 on >= 3 of 5 AND mean improves) is unreachable here: loop-1 is
already at 100 far recall on 4 of the 5 holdout stems, so the experiment can only tie them. It beats on 1/5 (191913,
0 -> 100) and the mean improves 80 -> 100. 'partial' needs a regression and there is none on any metric or stem; 'fails'
contradicts 5/5 improvement on every px and path metric. Judged on what the ball stage owns: far median px 10.86 -> 1.90
(5/5), median px 8.88 -> 1.72 (5/5), recall/far recall better-or-tied 5/5. The orchestrator may override with this gap
in view.

Calibration: holdout far px 1.90 vs in-sample dev 1.12 (refine thresholds were tuned on the dev far frames); it degrades
out of sample but does not collapse. Excluding the 191913 rescue, the gain is still large on 192636 (10.5 -> 0.9) and
192142 (4.0 -> 1.0).

Mechanism differs from the NOTES' prediction: 191913's gutter-object drift was rescued mostly by the RADIUS gate
(17 events) with lateral only 4; 192636 fired the lateral gate 13 times and those overrides were correct (far px 0.9).

## entry_err / hook_err on 192142 and 192636 are not a ball-stage failure
The holdout truth `entry` is read at the observed pin contact, 10 frames (192142) and 6 frames (192636) after the cut's
pin_hit_frame, where the ball moves ~1.5-2 boards per frame; `final_board` is the median of the last 5 boards <= cut
pin_hit, so it stops short by construction (loop-1 has the same problem: 16.65 / 13.55). Against the truth's
`entry_at_cut_pin_hit` the experiment's final_board is within 1.13 (192142) and 1.26 (192636) boards; loop-1 is 5.83 and
6.59 off. Hand-forward for the lane/path stage: extend the read past the cut pin_hit to the observed contact, or read the
last frame instead of a 5-frame median.

## Dev reproduction
Re-ran 185331 (`--tag _judgerepro`): track frames and boards byte-identical to the experiment's track, every score_v2
metric identical to its dev.json row (far px 2.1, path_err_far 1.28, entry_err 0.87, hook_err 1.91). The repro files
were moved out of L2 so `score_all.py` does not pick them up.

## Overlays
- final__185331 (dev): green inside the quad, smooth to the deck, ends at the ball marker; the near-end zigzag in the
  board-vs-ft panel is the garbage carried quad (known, loop-1 too).
- final__190115 (dev): green on the lane, ends at the deck. The quad's right edge runs into the right gutter at the near
  end (lane-stage issue, not this stage).
- final__191913 (holdout): green on the lane to the pins; the grey loop-1 line peels right onto the ball-return object at
  the deck. A raw-frame check (pin_hit-6 and pin_hit on 191913, 192636, 191820; scratchpad pinhit_check.jpg) puts the
  green circle on the purple ball in all 6 frames, while the grey loop-1 circle sits on the dark ball-return object on
  191913 and is bloated beside the ball on 192636; on 191820 (gutter) green is on the ball in the gutter.

## hook_in_raw_track (raw boards{}, last 12 frames to pin_hit, first -> min -> last; no fit)
- 191253: 5.5 -> 8.9 rising; agrees with the truth direction. (The brief calls 191253 monotonic from loop-1 truth; the
  loop-2 holdout truth rises over the last 12 frames, so the two truths differ in description.)
- 191820: -1.1 -> -4.5 -> -4.0 falling; DISAGREES. Gutter ball, boards < 0 are an extrapolation beyond the lane edge;
  loop-1 disagrees the same way.
- 191913: 6.1 -> 10.7 rising; agrees (loop-1 disagrees: it is on the gutter object at boards -8..-9).
- 192142: 6.2 -> 5.5 -> 10.2, min then rise; agrees (hook back left is in the raw track).
- 192636: 9.0 -> 7.5 -> 14.2, min then rise; agrees (loop-1 rises only 4.4 -> 7.7 with slope +0.6).
4 of 5 agree; the one disagreement is the gutter ball.
