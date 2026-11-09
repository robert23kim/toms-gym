# Judge round 3 (16 stems on their rerun-2 tracks, 2026-11-09 15:20): track_v3 61b47162d2283afb, 12:50 amendments applied

**Video-only (2 of 2 reruns spent, still failing): 104714, 110622, 112413, 113716, 114059, 114438, 114631, 114810.** Still failing with one rerun left: 105322 (J2), 113911 (J2), 115105 (0 points) and 110224 (truth entry only). 114236 still needs the rule-owner call (not re-run by design).

**3 of 16 pass J1-J5 under the amendments: 105652, 110713, 113113. Latest verdicts over all 31 throws: 18 pass** (15 from round 2 plus these 3). As first written, 1 of the 16 passes (105652). Reseeding SAM at the deck (deck_reseed_sam) fired on 11 stems but produced a detected pin row on only 2 (105652, 113113). 114810 went from failing J4 to failing J2.

## Batch state and landing
- `rerun_r2_smoke.done` 14:34:12 (5/5, rc 0) and `rerun_r2_rest.done` 15:10:06 (10/10, rc 0). The rest batch was not started after smoke. I told main at 14:41, and it started at 14:42. No batch was dead: a stem finished every 1-4 min.
- All 15 re-run tracks differ from `work/round2_backup/tracks`. The 16 tracks that were not re-run (the 15 round-2 passers and 114236) are byte-identical to round 2 (`work/judge_r3/tracks_sha_*.txt`).
- **Two round-3 judges ran at once** on the same folder (`work/judge_r3/`). The other one wrote the results files at 15:13:27 and mine overwrote them at 15:13:44. Our verdicts are identical. Its notes are kept as `work/judge_r3/judge_all_round3_notes.twin.md`. Its pre-merge copy of judged_final was lost, so `changed_round3` is computed against `results/judged_round2.json`.

## Results (verdict = J1-J5, dead band read as "each leg exceeds 1 board", plus T-entry (entry_err_pr) and T-pinrow on truth stems)
| stem | round 2 | round 3 | reruns | J6 |
|---|---|---|---|---|
| 104714 T | J2 T-pinrow | J2 T-pinrow | 2, video-only | 3/3 |
| 105322 | J2 J3 | J2 | 1 | 3/3 plausible (55 ft small) |
| 105652 | J2 | **pass** | 1 | 2/3 (55 ft coast at the deck) |
| 110224 T | T-entry | T-entry | 1 | 3/3 |
| 110622 | J1 J3 J4 | J1 (47.3) | 2, video-only | 1/3 (camera up) |
| 110713 | J3 | **pass** (raw J4 count 5) | 1 | 2/3 |
| 112413 | J2 J3 | J2 | 2, video-only | 2/3 |
| 113113 | J2 | **pass** (raw J4 count 6) | 1 | 3/3 |
| 113716 T | J2 T-entry T-pinrow | same | 2, video-only | 3/3 |
| 113911 | J2 | J2 | 1 | 3/3 |
| 114059 | J2 | J2 | 2, video-only | 2/3 (20 ft coast off) |
| 114236 | J1 (79.7) | J1 (same track) | 0 | 3/3 on the frames that exist |
| 114438 | J2 | J2 | 2, video-only | 3/3 |
| 114631 | J2 | J2 | 2, video-only | 3/3 |
| 114810 | J4 | J2 (worse) | 2, video-only | 3/3 (kickback points gone) |
| 115105 | J1 J3 J4 J5 | same (0 points) | 1 | 0/3 (ball visible f570, f582) |

J1-J5 come from the shared `work/judge_r1/judge_rules.judge`, and an independent J1/J4 implementation is in `work/judge_r3/rules.py`. They agree on all 16 except the dead-band count on 114631: the >1 reading gives 1 sign change and the shared >=1 code gives 3. 114631 fails J2 either way, so its verdict does not change. J5 under the carried-quad reading is 100 % on 15 stems. Under the strict reading it is below 90 % on 105652 (87.7, a passer), 110622, 112413, 113911 and 114236. J6 grids: `work/judge_r3/j6_grid_1..4.jpg`, all 4 read.

## Truth clips (score_v2 on all 6 current tracks)
recall_pct is 100 on all 6. entry_err_pr is 2.47 / 3.25 / 2.35 / 0.28 / 1.95 / 8.66 (104714 110224 111238 111420 112638 113716), mean 3.16. The final_board entry_err mean is 5.64. pin_row_err is 34 / 1 / 1 / 2 / 1 / 14, mean 8.83. All the score fields are byte-identical to round 2, including those of the three re-run truth stems. Their entry and pin row did not move: the canary checks confirmed that the scorer read the new track files.

## The J2 class (from the track JSON only: `base_rows` vs ball y, `work/judge_r3/pinrow_gap.json`)
The ball stage reaches the deck. On every fallback stem the ball centre ends a few px short of the measured headpin base row, and the gap is still closing when the track ends. The cut runs 24-34 frames past every track end.

| stem | gap at track end | closing rate | track end | gap = 0 at |
|---|---|---|---|---|
| 104714 | 2.0 px | 2.2 px/frame | f382 | f383 |
| 114059 | 1.7 px | 1.1 px/frame | f619 | f621 |
| 113911 | 11.3 px | 1.8 px/frame | f522 | f528 |
| 105322 | 9.5 px | 1.3 px/frame | f443 | f450 |
| 114631 | 6.6 px | 0.9 px/frame | f584 | f592 |
| 114810 | 7.0 px | 0.9 px/frame | f662 | f670 |

- 114438 crosses on its last 2 frames, and the rule needs 3 real frames after the crossing.
- 113716's SAM tail does not move in the image after f557 (a static deck object).
- 112413's tail jumps 53 px back down at f361.
- A crossing that pass 3 found was discarded by the deck gate in pass 4 on 112413 and 114631. The loop keeps the last pass, not the best one.

The hint for 105322 and 113911, the two J2 stems that still have a rerun: take the pin row from the zero of a linear fit of (ball y - base row) over the last 6 real points, when it falls within 8 frames of the track end. That is the round-2 gutter rule applied in the lane. The other judge's hint caps the extrapolation at 3 frames, which would rescue neither stem. Whether an extrapolated crossing counts as a "detection" under J2 is a rule-owner call.

## For the rule owner
- 114236 and 110622 fail J1 on frames where the ball is not in the picture: on 114236 the camera is on the feet, on 110622 on the ceiling.
- 110224 passes J1-J5 and fails only the truth entry (pin row detected, pin_row_err 1). Its crossing-entry alternative moves it by 0.68 boards only.
- 110622 passes J3 with entry 20.26 although `events.gutter` says right.
- 105652 passes, but its strict J5 reading is 87.7 and its 55 ft J6 point is a coast circle.

## Quarantine
I opened `/Users/toka/pov-holdout/2026-11-09-glasses-pov-session/<stem>.json` only through `L2/score_v2.py`, on the 6 truth stems (`work/judge_r3/score.sh`). Only numbers went into the repo. A regex check found no truth number in any rerun_hint.

## Files
- `results/judged_round3.json` (16 rows with a `render` field: line / video-only / pending)
- `results/judged_final.json` (31 rows: latest_round 3, `round_of_verdict`, `video_only`, `changed_round3` vs round 2)
- `work/judge_r3/`: rules.py, rules_auto.json, pinrow_gap.json, write_judged.py, j6_grid.py and grids, score.sh, score_*.txt, sha/mtime snapshots
