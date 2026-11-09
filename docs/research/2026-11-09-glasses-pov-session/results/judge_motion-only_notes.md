# Judge: motion-only on the 6 truth clips (2026-11-09)

Verdict: **partial**. Mean recall 100 % (>= 85 holds), entry_err <= 3 boards on 3 of 6 (needs 4). Pick-rule inputs are score_v2's `recall_pct` and `entry_err` on the frozen truth files.

## Runs
`experiments/motion-only/run.py <stem> --device mps --any-stem`, sequential, from `work/judge_motion-only/batch.py` (600 s subprocess timeout per stem, logs in `work/judge_motion-only/`). `--any-stem` lifts the dev guard; it is a flag, not a code change. No code edited. All 6 ran with rc 0, 38-60 s each (mean 50 s; SAM 26 s on 104714). All 6 truth files present, so nothing was skipped.
Serialisation: the batch waited until no other `run.py <stem>` or `run_dev.sh` was running, and launched run.py by full path so the ball-colour-model judge's guard would see it. Every stem waited exactly the 8 s stability check and no other tracker appeared in any poll, so this batch did not overlap another run. Runs: 11:26:00-11:31:45. A first attempt was killed after a few seconds on 104714 and run again.

## Per stem (score_v2, truth as frozen)
| stem | recall | far recall | entry_err | entry_err_pr | pin_row_err | pin row source | path_err_rms | far px err |
|---|---|---|---|---|---|---|---|---|
| 104714 | 100 | 100 | 2.6 | 2.47 | 34 | fallback | 0.99 | 5.8 |
| 110224 | 100 | 100 | 10.3 | 3.25 | 1 | geometric | 1.25 | 2.2 |
| 111238 | 100 | 100 | 5.7 | 2.35 | 1 | geometric | 0.74 | 2.9 |
| 111420 | 100 | 100 | 2.6 | 0.28 | 2 | geometric | 0.36 | 1.2 |
| 112638 | 100 | 100 | 2.7 | 1.95 | 1 | pin motion | 0.85 | 1.9 |
| 113716 | 100 | 100 | 9.95 | 8.66 | 14 | fallback | 1.17 | 3.2 |
| mean | 100 | 100 | 5.64 | 3.16 | 8.83 | 4/6 detected | | |

RULES truth-clip extras: entry_err <= 2.5 on 0/6; pin_row_err <= 4 on 4/6. J2 (pin row detected, not fallback) holds on 4/6.

## Two caveats that bear on the verdict
1. **The scorer's window stops at the cut pin_hit, and the truth notes say that is 8-34 frames early.** Re-scored with `pin_hit_frame` set to the truth's own pin row (temporary copy in the scratchpad, deleted afterwards): recall 53.8 / 100 / 100 / 96.4 / 100 / 61.3 (mean 85.25), far recall 7.7 / 100 / 100 / 92.3 / 100 / 7.7 (mean 67.95). On 104714 the track ends 12 frames before the pins. On 113716 the last frames are off the ball (far px err 19.2, path_err_far 4.86). Mean recall still clears 85, by 0.25.
2. **`entry_err` reads the track's `final_board`, which run.py evaluates at the cut pin_hit** (`final_board_rule`: Theil-Sen at pin_hit). On a late hook that is the wrong depth. `events.entry_board` is the same quantity at the experiment's own pin-row estimate, and the overlay draws it. Scored against the truth pin-row board (`entry_err_pr`) it is <= 3 on 4/6, which would make the verdict `works`. The verdict above keeps score_v2's `entry_err` as the rule states; whoever owns the pick rule needs to decide which one counts. On 110224 the gap is 10.3 vs 3.25, and on 111238 it is 5.7 vs 2.35.

## Overlay check (110224, 113716; `overlays/final__*` and `picture__*`)
- 110224: the circle is on the ball in the 20, 40 and 55 ft crops (f397/f420/f438). The white chained path runs down the lane into the deck. Its pin row is 1 frame off truth, and the magenta entry sits on the ball at the pins. That entry is 3.25 boards short on a hook moving about 2 boards per frame.
- 113716: the circle is on the ball in all three crops (f503/f523/f539), but the "55 ft" crop is 19 frames before the true pin row because the pin row fell back to the early cut value. The white chained path zig-zags near the foul line, and the magenta entry is drawn at that early frame, about 9 boards off. The path does not end where the ball is at the pin row.

## Off limits kept
Only numbers from the quarantine are written here. No truth coordinates or boards are copied into the repo. The quarantine copy used for caveat 1 lived in the scratchpad and was deleted.
