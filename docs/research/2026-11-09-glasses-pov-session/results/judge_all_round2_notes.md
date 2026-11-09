# Judge round 2 (all 31 throws, 2026-11-09 14:00): track_v3, 12:50 amendments applied

**15 of 31 pass J1-J5 (amended): 13 of the 22 batch stems, 2 of the 9 left-out stems (112146, 112800), 3 of the 6 truth stems.** Under the rules as first written 4 of 31 pass. 11 of the 15 passes depend on the amendments. This file replaces the 13:33 round-2 notes on 19 stems (copy: `work/judge_r2_all/judge_all_round2_notes.before_round2_all.md`).

Batch state: `run_all.done` (12:17, 22/22), `rerun_r1.done` (13:26, 12/12) and `run_missing.done` (13:40, 9/9) are all present. No batch was dead. `results/tracks` mtimes were identical at the start and the end of judging (`tracks_mtime_start/end.txt`). The 22 batch tracks are unchanged since the re-issued round 1, and their J1-J5 rows equal `work/judge_r1b/rules_auto.json` exactly (regression check in `rules.py`). 111218 has no throw and is excluded.

## How each rule was computed (`work/judge_r2_all/rules.py`)
- J1-J5 come from the shared `work/judge_r1/judge_rules.judge`. An independent re-implementation of J1 and J4 agrees on all 31, except the dead-band count on 114631.
- J4 verdict uses RULES.md's wording: each leg must *exceed* 1 board. The shared code uses `>= 1`, which counts 3 sign changes on 114631 instead of 1. Its verdict does not change (J2 fails). Both counts and the raw count are in `metrics`.
- J5 uses the carried-quad reading, which is 100 % on 30 stems (115105 has no track). The strict reading (edge lane on every frame from release to the pin row) is below 90 % on 105652 (lane missing f333-341), 110622, 113911 (f479-488) and 114236 (lane starts f367). All four already fail another rule, so no verdict changes (`metrics.J5_strict_fails`).
- J3 gutter clause: only 110622 has `events.gutter` (right). At 40 and 55 ft the camera points at the ceiling, so my frame read cannot confirm the gutter, and J3 stays failed.
- J6 frames are at round(release + ft/60 * (pin_row - release)). The 8 grids are `work/judge_r2_all/j6_grid_1..8.jpg`, 4 stems each, and I read all 8. `look_seed.jpg` shows the early frames of 114236 and 115105.

## Results
Pass: 104946, 105857, 110442, 110948, 111631, 111941, 112146, 112800, 112936, 113541, 114919, 115157, plus truth stems 111238, 111420 and 112638.

| stem | fails | as first written | reruns spent | J6 |
|---|---|---|---|---|
| 104714 T | J2 T-pinrow | J2 J4 T-entry T-pinrow | 1 | 3/3, short of the deck at 55 ft |
| 105322 (new) | J2 J3 | same | 0 | 2/3, 55 ft at the right lane edge unconfirmed |
| 105652 (new) | J2 | J2 | 0 | 3/3 |
| 110224 T | T-entry (_pr 3.25) | T-entry | 0 | 3/3 |
| 110622 | J1 (53.2) J3 J4 | same | 1 | 1/3, camera tilted up |
| 110713 (new) | J3 (entry None, entry_n 1) | J3 J4 | 0 | 2/3, 55 ft coast circle unclear |
| 112413 | J2 J3 | J2 J3 J4 | 1 | 3/3 |
| 113113 (new) | J2 | J2 J4 | 0 | 3/3 |
| 113716 T | J2 T-entry T-pinrow | same | 1 | 3/3 |
| 113911 (new) | J2 | J2 J4 | 0 | 3/3 |
| 114059 | J2 | J2 J4 | 1 | 2/3 (20 ft coast circle off) |
| 114236 (new) | J1 (79.7) | J1 | 0 | 3/3 on the frames that exist |
| 114438 | J2 | J2 J4 | 1 | 3/3 |
| 114631 | J2 | J2 J4 | 1 | 3/3 |
| 114810 | J4 (2 dead-band sign changes) | J4 | 1 | 2/3 (55 ft deck point doubtful) |
| 115105 (new) | J1 J3 J4 J5 (0 ball points) | same | 0 | 0/3, ball visible but no track |

Truth clips (score_v2, numbers only; byte-identical to the r1b scores). recall_pct is 100 on all 6. `entry_err_pr` is 2.47 / 3.25 / 2.35 / 0.28 / 1.95 / 8.66 (104714, 110224, 111238, 111420, 112638, 113716), mean 3.16. `entry_err` (final_board) mean is 5.64. pin_row_err is 34 / 1 / 1 / 2 / 1 / 14, mean 8.83. score_v2 recall stops at the cut pin_hit, so 100 says nothing about the far end on the fallback stems 104714 and 113716.

## Rerun hints (one change each, in `rerun_hint`)
- **J2 fallback, SAM dies at the deck** (104714, 113716, 114059, 114438, 114631, and new 105652, 113113, 113911). Re-seed SAM from the last real residual detection with one more crop pass. Keep tracking until the headpin-row crossing is held on 3 real frames.
- **Right gutter / edge, no flag** (112413, and new 105322 with the same shape: SAM dies at f440 with one channel point and entry -1.87). Run the lane-first gutter-channel check over the last 15 track frames, so the throw is flagged gutter and the pin row comes from the channel crossing.
- **110622**: take the pin row from the ball reaching the base row inside the right channel, not from pin motion at f483.
- **110224, 110713**: read the entry as the board interpolated at the sub-frame headpin-row crossing. On 110713 this applies whenever fewer than 2 deck points exist.
- **114810**: gate the SAM deck points to within 2 boards of the residual chain.
- **115105** (new, 0 points): no seed came from 49 candidates, and ORB failed on 23 frame pairs. The camera is rolled about 25 degrees and panning, yet a dark blue ball is plainly on the lane at f560-576. When the residual chain has no seed, seed from a dark-disc test inside the lane-first quad (no colour assumption).
- **114236** (new): no tracker change helps. From f354 to f366 the camera points at the foul line and the bowler's feet, so the ball is not in the picture (`look_seed.jpg`). The track is continuous from f367 to f416. This needs a rule-owner call: either start the J1 window where the lane is first in view, or render the throw video-only.
- Rerun budget: the 12 stems in `work/rerun_r1/stems.txt` have spent 1 of 2 reruns. For the 8 that still fail (104714, 110622, 112413, 113716, 114059, 114438, 114631, 114810), the next rerun is the last one; after it a failing throw is rendered video-only. The 7 new stems and 110224 have spent 0. Do not read the rerun count from `meta.round`: the 9 new stems carry `rerun_round1`, but that was their first and only run.

## For the rule owner
- 115157 passes J2 only through `detected (relaxed hold)`, which rests on deck points that J6 cannot confirm. If that does not count as a detection, the total is 14 of 31.
- 114810's J2 crossing rests on the same doubtful deck points. Its verdict does not change.
- 114236 fails J1 on frames where the ball is out of view, so J1 as written cannot be passed on this clip.
- Amendment dependence: 11 of the 15 passes need the amendments (only 104946, 105857, 110442 and 111941 pass as first written). The 9 new stems were tracked with track_v3 after round 1, so their first track already includes the rerun-1 fallbacks.

## Quarantine
I opened the quarantine only through `score_v2.py` with `/Users/toka/pov-holdout/2026-11-09-glasses-pov-session/<stem>.json`, on the 6 truth stems. Only numbers went into the repo, and no truth number is in any `rerun_hint`.

## Files
`results/judged_round2.json` (31 rows), `results/judged_final.json` (31 rows, latest_round 2; the pre-merge copy is `work/judge_r2_all/judged_final.before_round2_all.json`), and `work/judge_r2_all/` (rules.py, rules_auto.json, write_judged.py, j6_grid.py, j6_grid_1..8.jpg, look.py, look_seed.jpg, score_*.txt, tracks mtime snapshots).
