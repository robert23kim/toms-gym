# Judge: wildcard (NCC template relay + SAM lane), holdout, 2026-10-10

**Verdict: partial.** The tracking holds up on the holdout: mean recall 76.5, and 4 of 5 stems score 89-100 %
at 3-10 px median error. Board reads within 3 boards on only 2 of 5 stems, so it misses `works`.

## How it was run
- `run.py <stem>` run fresh and one at a time on each holdout stem, from `experiments/wildcard/`, with the
  engine venv python. No code changes or path fixes. Exit code 0 on all 5. run.py reads only `cut_start`,
  `cut_end` and `cut_path` from `cuts.json`, never its `release_frame`/`pin_hit_frame`.
- Scored with `score_tracks.py` against `/Users/toka/.cache/bowling-pov-holdout-2026-10-10/<stem>.json`.
  The truth was not copied into L. Logs are in `/Users/toka/.cache/bowling-pov-holdout-2026-10-10/judge_wildcard/`.
- The machine was loaded the whole time: 4 other agents' `run.py` jobs at ~100 % CPU each, load average 7-13 on
  12 cores. Wall times below were measured under that load.

## Holdout
| stem | recall % | median px | board_err | lane_err | window_err [rel, pin] | pass | wall s |
|---|---|---|---|---|---|---|---|
| 191253 | 98.1 (52/53) | 3.4 | 0.5 | 2.63 | [10, 3] | strong | 62.2 |
| 191820 | 0.0 (0/24) | - | null | null | [25, 4] | no | 34.4 |
| 191913 | 95.7 (22/23) | 3.2 | 1.0 | 5.49 | [0, 14] | strong | 61.0 |
| 192142 | 100 (17/17) | 6.5 | 4.0 | 2.64 | [1, 3] | no | 63.3 |
| 192636 | 88.9 (16/18) | 9.6 | 5.5 | 4.55 | [2, 2] | no | 157.4 (SAM 144 s) |
| **mean** | **76.5** | | 2.75 over 4 stems; within 3 boards on 2/5 | | | 2/5 | 75.7 |

Dev mean recall was 96.1. The holdout drop comes from one total miss, not from drift: excluding 191820, the
holdout mean is 95.7. The board read is weaker than on dev (dev 1.0 over its 4 right-lane stems, holdout 2.75
over 4). The truth-fitted pin bias (+8 frames) and the SAM quad width are the likely knobs to look at.

## Dev reproduction
I re-ran 185331 (after backing up the original track). It came out identical to the claim: recall 91.7, median
6.4 px, board_err 0.5, lane_err 0.74, wall 58.9 s. **Reproduced.**

## Overlays I read
- **191820 (fails)**: the seed is the wrong ball. In frame 430 the bowler's purple ball is mid-lane on the
  centre lane, and the track does not start until 437. From 437 to 467 the track follows a small ball (r ~10,
  constant) at the far end of a lane to the LEFT: a neighbour's ball, which YOLO picked up with box confidence
  0.74. The NCC relay followed that ball faithfully. SAM found no lane (all 5 candidates had a residual of
  25-32 px), so final_board is null. This is a seeding failure in the single-seed design, which takes the most
  confident box among the chain's first 6. Neither the tracker nor the scorer caused it, and dev never
  exercised it.
- **192636 (board off by 5.5)**: in frames 405, 420, 440 and 452 the red circle sits on the ball, and the
  ball is inside the cyan SAM quad, which is the lane the bowler threw on. Near the pins the ball sits on the
  right side of the quad. That fits a single-digit board from the right, but the scorer says the read is 5.5
  off, and the quad width is off by 5-9 boards (lane_err 4.55). The per-frame board at 452 (3.18) does not
  match final_board 7.0. The overlay polyline is drawn in raw image coordinates from frames taken while the
  head moves, so on the pin_hit-4 frame it does not lie on the lane. The notes already say this; it makes the
  overlay hard to read, not wrong.

## Caveats
- The holdout cuts were made by the shared cut step ("visual, single-frame edges"). They are not part of this
  experiment, but they bound where the relay can start.
- The verdict rests on 5 videos, one of which is a total miss. Moving one board read (192142, 4.0) under 3
  would flip the verdict to `works`.
