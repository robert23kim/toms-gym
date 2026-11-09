# Judge round 1 (re-issued 2026-11-09 ~14:00): 22 stems, 12:50 amendments applied

**This step was re-issued after round 1 (12:28) and round 2 (13:33) were already on disk.** I judged `results/tracks` as I found them. 12 of the 22 tracks already carry rerun 1 (track_v3 `86a42d3466b8f4c3`), so one of the two reruns the iteration rule allows is already spent, and the workflow's counter does not know it. The 12:28 files are kept in `work/judge_r1b/*.before_rejudge.*`.

**13 of 22 pass J1-J5 (amended): 10 of the 16 listed stems and 3 of the 6 truth stems.** Under the rules as first written, 3 of 22 pass. Every verdict matches round 2 and the merged `judged_final.json`. The one difference is the J4 reading on 114631, explained below. Its verdict does not change, because it still fails J2.

Batch state: `work/run_all.done` (12:17, 22/22), `rerun_r1.done` (13:26, 12/12) and `run_missing.done` (13:40, 9/9) are all present, so no batch was dead. The 9 left-out stems (105322, 105652, 110713, 112146, 112800, 113113, 113911, 114236, 115105) are not part of this round. 115105 has 0 ball points. 111218 has no throw.

## How each rule was computed (`work/judge_r1b/rules.py`)
- J1-J5 come from `work/judge_r1/judge_rules.judge`, the same code the earlier rounds used.
- I also wrote a separate re-implementation of J1 and J4 (`indep` in `rules_auto.json`). It agrees with the shared code on J1, the jump size and the raw J4 sign-change count on all 22 stems. It disagrees on the dead-band J4 count only on 114631.
- **J4 dead band:** RULES.md says the move on each side must *exceed* 1 board. The shared code counts a move of >= 1. On 114631 the median series goes 16.59 -> 14.21 -> 15.52 -> **14.52** -> 15.86. That 1.00-board leg does not exceed 1, so it is not a direction change. The count is 1 sign change and J4 passes. Round 2 counted 3. Both counts are in `metrics`.
- J5 uses the carried-quad reading: 100 % on all 22 stems, longest missing run 0.
- J3: 110622 is the only stem with a gutter flag (right side). I could not confirm the gutter from the frames: the camera is tilted up at the end of the track (`look_gutter.jpg`). 112413 ends at the right lane edge (entry -0.74) but has no gutter flag, so the gutter clause cannot apply. Neither verdict depends on this read.
- The truth scores were re-run through `score_v2.py` on the current tracks. They are byte-identical to `work/judge_r2/score_*.txt`.

## Results
Pass: 104946, 105857, 110442, 110948, 111631, 111941, 112936, 113541, 114919, 115157, 111238 T, 111420 T, 112638 T.
| stem | fails | as first written | J6 |
|---|---|---|---|
| 104714 T | J2 T-pinrow | J2 J4 T-entry T-pinrow | 3/3, 55 ft short of the deck |
| 110224 T | T-entry (_pr 3.25) | T-entry | 3/3 |
| 110622 | J1 (53.2) J3 J4 | same | 1/3, camera tilted up |
| 112413 | J2 J3 | J2 J3 J4 | 3/3, right edge by 55 ft |
| 113716 T | J2 T-entry T-pinrow | same | 3/3 |
| 114059 | J2 | J2 J4 | 2/3 (20 ft coast circle off) |
| 114438 | J2 | J2 J4 | 3/3 |
| 114631 | J2 | J2 J4 | 3/3 |
| 114810 | J4 (2 sign changes) | J4 | 2/3 (55 ft SAM circle right of the ball) |

Amendments: 8 of the 13 passes depend on them. 110948, 111631, 112936, 113541, 114919 and 115157 pass only with the J4 dead band. 111238, 111420 and 112638 pass only on `entry_err_pr` (112638 also needs the dead band).

Truth clips (numbers only): recall_pct 100 on all 6. entry_err_pr 2.47 / 3.25 / 2.35 / 0.28 / 1.95 / 8.66, mean 3.16. entry_err (final_board) mean 5.64. pin_row_err 34 / 1 / 1 / 2 / 1 / 14, mean 8.83. score_v2 recall stops at the cut pin_hit, so recall 100 says nothing about the far end on the two fallback stems (104714, 113716).

## Rerun hints (one change each, written to `rerun_hint`)
- **J2 pin-row fallback** on 104714, 113716, 114059, 114438 and 114631: when SAM dies at the deck, re-seed it from the last real residual detection with one more crop pass, and keep tracking until the headpin-row crossing holds on 3 real frames.
- 110622: take the pin row from the ball reaching the base row inside the right gutter channel. The current pin row is the pin-motion frame f483, 46 frames after the track ends at f437.
- 112413: run the lane-first gutter-channel check over the last 15 track frames, so the throw is flagged gutter and the pin row comes from the channel crossing.
- 114810: gate the SAM deck points to within 2 boards of the residual chain. Points f661-674 lock onto the right-edge kickback gap.
- 110224: read the entry as the board interpolated at the sub-frame crossing. No truth numbers are in any hint.

## For the rule owner
- 115157 passes J2 only through the "relaxed hold" detection that rerun 1 added. J6 cannot confirm its deck points are the ball. If that detection does not count, the totals are 12 of 22 and 9 of 16.
- The J2 detection on 114810 rests on the same doubtful deck points.

## Quarantine
I opened the quarantine only through `score_v2.py` with `/Users/toka/pov-holdout/2026-11-09-glasses-pov-session/<stem>.json`, on the 6 truth stems. Only numbers went into the repo.

## Files
`results/judged_round1.json`, `results/judged_final.json` (merged with `stems.update`; the only row change is 114631, whose rules_failed went from J2+J4 to J2), `work/judge_r1b/` (rules.py, rules_auto.json, write_judged.py, j6_grid_1..6.jpg, look_gutter.jpg, score_*.txt, backups).
