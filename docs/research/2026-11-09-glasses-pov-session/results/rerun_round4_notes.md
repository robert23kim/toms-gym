# Rerun round 4 (2026-11-09 17:40-18:20): extrapolated headpin-row crossing

Trigger: Tom asked for the judge's round-3 pin-row hint to be applied and the video re-rendered. Rule owner's call, disclosed in RULES.md (17:40 amendment): a third rerun over the budget of 2, and a J2 reading that counts a last-resort extrapolated crossing as a detection.

## Change (track_v3.py, `pin_row_extrapolated_crossing`)
Runs only when the pin row is still the cut fallback after the SAM pass to the cut end, the deck re-seed, the relaxed hold and the gutter channel (pass >= 3). Same-frame gap g(f) = ball centre y - headpin base row at f, over the last 6 real points; least-squares line; pin row = its zero when the slope is negative and the zero is within -3..+8 frames of the track end. The condition is false for every passing stem (their pin row is detected before pass 3), so their tracks cannot change; the canary 104946 reproduced frames, boards, lane and pin row exactly.

## Why same-frame gaps, not the judge's 3-frame row median
At the track end the median over (f-1, f, f+1) has two samples and is a mean; under camera pan the base row moves 15-20 px per frame, so the last gap reads a false drop. The round-3 table in `work/judge_r3/pinrow_gap.json` was built that way and said 7 of 9 would fall within 8 frames. The same-frame simulation on the stored tracks (`sim_r4`) said 3 of 9. The run gave 3 of 9.

| stem | same-frame gaps (px, last 6) | zero past end | fired | round 3 -> round 4 |
|---|---|---|---|---|
| 104714 | 23.8 22.8 17.0 18.3 13.7 7.2 | +5.2 (f387) | yes | J2 T-pinrow -> T-entry (pin_row_err 34 -> 3, entry_err_pr 2.47 -> 6.88) |
| 114059 | 8.5 6.0 6.5 7.0 2.6 4.2 | +4.0 (f623) | yes | J2 -> pass (J1 92.3, J6 3/3) |
| 114438 | 6.1 4.3 3.3 2.7 0.3 -1.4 | -0.7 (f590) | yes | J2 -> pass (J1 100, J6 3/3) |
| 114631 | 15.3 19.8 14.8 14.9 15.3 7.9 | +15.0 | no | J2 |
| 105322 | 17.1 15.8 15.0 14.0 13.9 11.7 | +12.6 | no | J2 |
| 114810 | 11.0 12.0 12.0 10.7 9.1 8.7 | +14.7 | no | J2 |
| 113911 | 23.7 21.2 19.0 20.3 20.6 20.3 | +39.2 | no | J2 (gap flat: the SAM tail moves with the camera, not toward the pins) |
| 112413 | slope +12.7 | - | no | J2 (tail jumps to another object) |
| 113716 | slope -0.2 | +50 | no | J2, T-entry, T-pinrow (static tail) |

## Verdicts (work/judge_r4/, same rule code as rounds 1-3, J6 read by eye)
20 of 31 lines (18 before). Video-only: 104714 105322 110224 110622 112413 113716 113911 114236 114631 114810 115105. Truth means (6 clips): recall 100, entry_err_pr 3.90 (3.16), pin_row_err 3.67 (8.83).

## Lessons
18. Anchor a "gap closing" statistic on same-frame measurements; a cross-frame median at a series end is a biased mean.
19. A right pin-row frame does not make the entry right: the entry at an extrapolated crossing inherits the tail points' error (104714: +4.4 boards). Fix the tail, then extrapolate.
20. The renderer must read the verdict file, never a pasted list (the first round-4 render showed the two new passes as video-only).
