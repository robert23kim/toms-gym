# Judge: sam2-from-hand on the 6 truth clips (2026-11-09)

Verdict: **partial**. Mean recall 92.4 % passes the pick rule's recall bar (>= 85); entry_err <= 3 holds on 1 of 6 (needs >= 4).

## How it was run
- `experiments/sam2-from-hand/run.py <full stem> --device mps`, fresh on all 6 truth stems, sequentially, through
  `work/judge_sam2-from-hand/batch.py` (600 s timeout per stem; waits for any other judge's `run.py` to finish so only one torch
  process runs). All 6 exited rc=0, wall 78-97 s (mean 88 s). No code changes, no path fixes. No stem was skipped: all 6 truth files exist.
- Scored with `L2/score_v2.py experiments/sam2-from-hand/tracks/<full stem>.json Q/<short>.json`. Every truth file carries `pin_row`.
  Raw scorer fields per stem: `work/judge_sam2-from-hand/scores_raw.json`; rows and means: `results/judge_sam2-from-hand.json`.
- Truth-clip colours (from `results/split.json`): blue-purple 104714, 110224, 113716; black 111238, 111420, 112638. No green or red ball is in the truth set,
  so the colour-free claim is still untested on those colours.

## Per stem
| stem | recall % | far recall % | entry_err | entry_err_pr | pin_row_err (frames) | pin row source | path_err_rms | direction_ok |
|---|---|---|---|---|---|---|---|---|
| 104714 | 100.0 | 100.0 | 2.6 | 0.58 | 7 | geometric | 0.92 | yes |
| 110224 | 94.4 | 85.7 | 10.9 | 3.64 | 1 | geometric | 1.87 | yes |
| 111238 | 100.0 | 100.0 | 5.5 | 9.7 | 16 | pin motion | 0.75 | yes |
| 111420 | 60.0 | 11.1 | 13.2 | 12.72 | 11 | geometric | 6.01 | no |
| 112638 | 100.0 | 100.0 | 4.0 | 4.05 | 12 | fallback | 0.62 | yes |
| 113716 | 100.0 | 100.0 | 12.55 | 12.55 | 14 | fallback | 1.44 | no |
| mean | 92.4 | 82.8 | 8.12 | 7.21 | 10.17 | 4/6 detected | | |

- `entry_err` is score_v2's field (path_fit.board_at_60ft where the track has a path fit, else the final board); `entry_err_pr` is
  `events.entry_board`. The pick-rule count is the same under either: 1 of 6 within 3 boards.
- Truth-clip extras from RULES.md: entry_err <= 2.5 on 0/6; pin_row_err <= 4 on 1/6 (110224).

## What the numbers say
- The ball is followed: recall 100 % on 4/6 and path_err_rms <= 1.9 boards on 5/6. The ball stage is not the weak part on 5 of 6.
- The entry is the weak part, and it follows the pin row: pin_row_err is 7-16 frames on 5/6. Two stems took the cut pin_hit fallback
  (112638, 113716), one took pin motion (111238, 16 frames off). On 113716 the path is on the ball at every check frame (path_err_rms 1.44)
  but the entry is read at a pin-row frame 14 frames off and lands 12.55 boards off.
- 111420 (black ball) is the one ball-stage failure: far recall 11.1 %, 16 frames with no lane quad (J5 fails), entry read as -3.0
  with entry_err_pr 12.72. The proposed gutter flag (entry < 0.5) would fire on this track. This is the dark-ball far-end weakness the
  experiment's own notes named on 110442.
- The cut pin_hit is not a safe fallback: on the two fallback stems it scored 12 and 14 frames off, and on 104714 the cut pin_hit (f350)
  is 41 frames before the geometric crossing the tracker found (f391, scored 7 off).
- The dev proxies had no entry measure, and entry is where the truth fails this experiment (recall 0.977 dev vs 92.4 % truth; entry_err mean 8.12).

## Overlay read (J6-style, own images): path on the ball mid-lane 2/2, ends where the ball is at the pin row 0/2
- 113716 (purple): `check__` circles are on the ball at 20, 40 and 55 ft, tight radius. In `final__` the green lane path runs down the
  lane and ends at the magenta pin-row mark. The raw orange image track does not line up with the final frame because the head turned
  (expected for the stacked overlay). The path is on the ball, but the pin row it ends on is the cut fallback, 14 frames off, so the end point is not
  where the ball is at the pin row.
- 111420 (black): circle on the ball at 20 ft. At 40 and 55 ft the circle sits on dark blobs by the gutter divider and
  in front of the deck, and I cannot confirm either is the ball. In `final__` the raw track loops above the pin deck into the
  masking area at the far end, and the lane path ends in the right gutter at board -3. The path does not end where the ball is at the pin row.

## For the pick and the reruns
- Fix the pin row before anything else: the ball is on the lane, and the entry is read at the wrong frame. 112638/113716 never got a held geometric crossing.
- 111420 needs a far-end check on the dark ball: SAM leaves the ball after ~40 ft, the lane gate does not catch it, and the edge lane fails on 16 frames.
- This judge opened the quarantine only to score and to list key names. No truth coordinates are written here.
