# Glasses-POV bowling tracking, loop 2 (research, 2026-11-07)

`docs/research/2026-11-07-glasses-pov-hook/` (README, scripts, `results/*.json`, `experiments/*/NOTES.md`, overlays, `truth/`; `showcase.mp4` and `work/` gitignored). Goal: better downlane detection and a line that goes out right then hooks left where the data does. Rules learned:

## What to keep
1. **Measure the lane per frame in that frame.** Wood-mask gutter-edge lines with no temporal carry beat one SAM quad carried by a 2x3 affine: path_err_rms 0.61 vs 3.13 (dev), path_err_far 2.53 vs 5.38 (holdout).
2. **Find the far ball with a compact purple disc at the geometric radius.** r_geo = 0.5 x 7.78 boards x lane_width_px(row)/38; far recall 100, far px 1.1-1.9 vs 8-11 for the SAM centroid.
3. **Read the board at the ball's contact row (y + r), not its centre**, when comparing with the truth's `board_contact`: a right-of-centre far ball reads 1-2 boards low at the centre row.
4. **Evaluate entry with a Theil-Sen line over pin_hit-10..pin_hit at pin_hit.** The loop-1 median of the last 5 lags the last-15-ft move by 4-5 boards.
5. **Draw the raw boards (3-frame median) against constant-speed depth** anchored release = 0 ft, pin_hit = 60 ft. Per-frame ft zig-zags by 5+ ft on 4 stems.
6. **Hook presence comes from the raw rise, never from a fit.** Draw nothing the measured track does not contain.
7. **Reject the tail one-sided against a line fitted before the tail** (clean_series, 6 boards): it dropped exactly 191820 f463-467 and changed nothing on 9 stems.
8. **Two scorer views always: the whole line and the far window.** path_err_rms for the line, path_err_far (pin_hit-12..pin_hit) for the pocket.
9. **Report the truth uncertainty with every entry** (+-1.0 to +-6.2) and do not tune below it.
10. **Put holdout and dev side by side on every table; show holdout first in the video.**
11. **Keep the leave-one-out table with the picks.** The lane pick flips on 3 of 5 holdout leave-outs.
12. **Mutation-check the scorer on a real track**: empty frames recall 0, +25 px far shift far recall 0, mirrored boards path_err_far 5 -> 33.

## What does nothing or hurts
13. **Lens curvature as an explanation:** clean edges fit a straight line to 0.7-2.8 px over 700-1200 px.
14. **A fitted hook (physics-smoother):** entry 8.04 -> 9.14 and a 7.4-board hook drawn on the 191820 gutter ball.
15. **Raw per-frame boards for min or hook:** jitter 1-2.5 boards invents a 1.8-2 board hook on straight throws.
16. **Pin-anchored Hough lanes alone:** crashed on 191913, entry <= 3 on 2/5. The pin ruler implies a lane 0.755x the edge width.
17. **--refine snapping edges to the strongest grey step (+-12 px):** far 0.72 -> 1.54, it locks onto the gutter-cap highlight.
18. **Blackhat re-centring of the far ball:** |d| worse on 4/5 stems.
19. **Far-end stacking over the disc filter:** same far px (1.9), one per-stem regression.
20. **Trusting cut pin_hit as the contact frame:** it is 10 and 6 frames early on 192142 and 192636, and clean_series would reject their true hook ends if the window grew.

## Harness gotchas
21. Every frame index is SOURCE numbering; cut frame k = cut_start + k; the rate is 30 fps though ffprobe says 120.
22. Boards 1-39 from the right gutter; ball moving right = board falling, hook left = board rising.
23. Quarantine does not hide holdout numbers that sit in prior READMEs, judge JSONs and the task text; say so in the gate notes.
24. Holdout truth is built and stored outside the repo (`HO`), then copied into `truth/` after judging.
25. Run a canary before every scorer use: 185454 must reproduce `final.json`; the empty-frames copy must score recall 0.
26. direction_ok is only informative where the truth trend is >= 1 board over 12 frames (185331 on dev); flat truth is a coin flip.
27. The truth uses the same instrument as the tracker; claim agreement, not absolute accuracy below ~1.5 boards.
28. Stages picked from holdout rows make the holdout a post-selection number; state it.
29. Read every saved video frame before describing it; the showcase notes said "line = measured boards vs constant-speed depth" while the first render used per-frame ft.
30. One torch process at a time on MPS; the engine SAM lane pass costs 43-195 s per video, composition costs about 1 s.
31. `ffmpeg` 9 has no drawtext; burn text with `cv2.putText`. Trim at pin_hit and stop circles at the last lane frame.
32. Pin ruler is biased low by 1.5-2 boards when the ball is in front of the pins: only reads at the contact frame count for entry.
