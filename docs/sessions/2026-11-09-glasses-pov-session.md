# Glasses-POV session 2026-11-08 (run 2026-11-09)

Folder: `docs/research/2026-11-09-glasses-pov-session/` (README.md has the clip and experiment tables; RULES.md has the numbered lessons).

## What was done, in order
1. Rules fixed before any tracker run (RULES.md): quarantined truth, J1-J6 judge, pick rule, render rule.
2. Cuts: `auto_cuts.py` run honestly on 25 untouched throw clips: 4 right, 6 wrong, 15 null. Added `--release` and the v3.1 clip-end gate (post-hoc, no holdout); releases read by eye. Spot check fired on 2 of 3 auto reads.
3. Ball colour per clip and game/bowler map (Tom: games 1 and 3; Chardie/"Chris": game 2; 111218 no throw). Split: 6 truth, 8 dev, rest.
4. Truth on 6 clips, quarantined.
5. Three experiments judged on truth: motion-only partial (recall 100, entry 5.64, pin row 8.83), sam2-from-hand partial (92.4 / 8.12 / 10.17), ball-colour-model fails (74.2 / 6.51 / 16.5). Pick: motion-only, flagged.
6. `track_v3.py` integrated and run on all throws; judge rounds 1-3 with two reruns; amendments of 12:50 disclosed.
7. Render `session.mp4` (117.5 s), critic pass, must-fix items applied.

## Numbers
- 18 of 31 throws pass J1-J5 (4 as first written after round 2; 11 of 15 round-2 passes depend on amendments).
- Truth clips: entry_err at detected pin row mean 3.16 (4 of 6 within 2.5), pin_row_err mean 8.83 (4 of 6 within 4 frames), recall 100 (non-discriminating).
- 8 stems video-only after both reruns; 5 more still failing with reruns left or a rule-owner call open (105322, 113911, 115105, 110224, 114236).

## Still broken
- J2: ball track ends a few px short of the headpin base row on most failures; 13 throws render without a line. Game 3 has only 3 of 11 lines.
- Chardie breakpoints read 8-13 ft on flat stretches; 115157 line wanders into the gutter band.
- Auto cuts unreliable; truth covers no green/red ball; recall metric loose.
- Naming: overhead monitors say "Chris", map says "Chardie". Game-1 frames by order only.
- Render guards not mutation-checked; two concurrent round-3 judges overwrote files (verdicts identical).

## Next steps
Gap-closing pin-row fit and a fresh rerun budget for the 13 failing throws; dense truth or truth-pin-row scorer window; holdout for auto_cuts; truth on a non-black upright-POV clip.

## Files to commit
README.md, RULES.md, .gitignore, auto_cuts.py, auto_cuts_notes.md, score_auto_cuts.py, track_v3.py, make_session_video.py, the run/rerun shell scripts, results/ (md, json, tracks/), experiments/*/ sources and NOTES.md, and this session doc. Not work/, *.mp4, overlays, tracks caches, __pycache__.

## Round 4 (17:40-18:20): the judge's pin-row hint applied, on Tom's ask
- Change: `track_v3.py` gained a last-resort pin-row fallback, `pin_row_extrapolated_crossing`: least-squares zero of the same-frame gap (ball centre y minus the headpin base row of that frame) over the last 6 real points, accepted when the gap is closing and the zero is within -3..+8 frames of the track end. It runs only after the SAM pass to the cut end, the deck re-seed, the relaxed hold and the gutter channel have all left the pin row on the cut fallback (gated on pass >= 3), so passers cannot change. RULES.md amendment 17:40 (third rerun, over budget, rule-owner call; J2 reading).
- Simulation first (scratchpad `sim_r4`): the judge's round-3 gap table ("7 of 9 within 8 frames") used the 3-frame median of the base row, which at the track end is a 2-sample mean and reads a false drop under camera pan (113911: median gaps 21 -> 11, same-frame 20.6 -> 20.3). Same-frame gaps fire on 3 of 9: 104714, 114059, 114438. The run matched the simulation exactly.
- Re-run: `rerun_r2.sh work/rerun_r2/stems_r4.txt r4`, 10 stems (9 fallback + canary 104946), 1837 s, 0 failures. Canary: frames, boards, lane, base rows, pin row identical to the round-3 track (its events only gained the round-2 fields it never had, because it was last tracked in round 1).
- Judge: run by the main loop with the round-1/3 rule code and score_v2 (`work/judge_r4/`), J6 grids read by eye. 114059 and 114438 pass (J1 92.3 and 100, J6 3/3). 104714 (truth clip): pin_row_err 34 -> 3 frames, but entry_err_pr 2.47 -> 6.88 because the two SAM tail points sit on the deck, not the ball (J6 2/3), so it stays video-only for T-entry instead of J2. The other six keep their round-3 verdicts.
- Result: 20 of 31 lines (was 18); Game 3 5 of 11 (was 3). Truth means over 6 clips: pin_row_err 8.83 -> 3.67 frames, entry_err_pr 3.16 -> 3.90 boards. `results/judged_round4.json`, `results/judged_final.json` (latest_round 4, changed_round4).
- Render bug found and fixed: `make_session_video.py` had the video-only stems hard-coded from round 3, so the first re-render ignored the new passes; it now reads `judged_final.json`. The pin-row label reads "extrapolated crossing" on those throws.
- Drive: the same file was updated in place (PATCH to id 1Dx_AuSQvHf5D21UDJM0j6K0UiKVQJZB0, md5 verified), so Tom's link did not change.
- Still broken: 105322, 113911, 114631, 114810 (gap closes too slowly or not at all over the last 6 points: zero 12-40 frames past the end), 112413 (tail jumps to the wrong object), 113716 (static tail), 110622/114236 (camera aim), 115105 (black ball, no chain), 110224 (entry 3.25 off truth). The entry at an extrapolated pin row inherits the tail's error (104714), so the next change is to the tail itself: reject SAM tail points that do not advance toward the row, then re-fit.
