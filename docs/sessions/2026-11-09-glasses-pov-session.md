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
