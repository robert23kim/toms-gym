# Glasses-POV hook loop (loop 2), 2026-11-07

Folder `docs/research/2026-11-07-glasses-pov-hook/` (README, RULES). Asked: better downlane detection, a drawn line that goes right then hooks left where the data does, a final video with the best of both.

## Done, in order
1. Gate: far-end cause is both stages (lens curvature ruled out at <= 2.8 px; centre-row read 1-2 boards low; SAM centroid bloated at the pins). Holdout truth quarantined to `/Users/toka/pov-holdout/2026-11-07-glasses-pov-hook`.
2. Truth v2: dev then holdout, per-throw entry +- uncertainty and hooks_back; holdout shows hooks on 191253, 191913, 192142, 192636.
3. Scorer `score_v2.py` with mutations; loop 1 re-scored (dev entry 1.00, path_err_far 2.08; holdout entry 8.04, path_err_far 5.38).
4. Five experiments: composition and lane-gated-ball work; pin-anchored-geometry, far-end-stacking, physics-smoother partial.
5. Integration `track_v2.py`: ball lane-gated-ball, lane composition edge lane, path none, plus clean_series fix after the provenance and hook-in-data skeptics.
6. Critic, showcase re-render (31.9 s), then docs and restore of the loop-1 holdout truth into L1/truth/ (holdout v2 truth copied into L2/truth/).

## Numbers (v1 -> v2)
- All 10: far recall 90 -> 100, entry 4.91 -> 2.22 (like for like on 9: 2.46), path_err_far 3.91 -> 0.82.
- Holdout n=5: entry 8.04 -> 3.98, path_err_far 5.38 -> 1.11, path_err_rms 5.39 -> 0.92, hook_err 10.08 -> 4.53, direction 60 -> 80 %.
- Caveats: shared instrument with the truth, post-selection holdout, mixed entry convention (contact vs cut pin_hit), rule written after seeing 191820.

## Still broken
- No contact detection; cut pin_hit is 10 and 6 frames early on 192142 and 192636, so the video line stops short of the full hook (amber diamond marks the labelled contact).
- clean_series would reject real hook ends if the window extended past pin_hit+4.
- 191913 track turns about 7 frames early; 191820 direction_ok false (trend inside the gutter).
- track_v2 reads the loop-1 SAM track from disk (108-131 s per throw); nothing in `pov-engine`.
- Showcase audio sync and player playback unchecked; only some frames viewed.

## Next steps
Detect contact from pin-deck motion and re-anchor 60 ft; jump-based tail rejection; re-read all entries at contact and re-score; rebuild the showcase from the fix-pass drawing; new session with frozen truth and a second instrument; port to `exp/r2-glasses-pov`.

## Files to commit
`docs/research/2026-11-07-glasses-pov-hook/`: README.md, RULES.md, .gitignore, track_v2.py, score_v2.py, score_all.py, score_final_v2.py, mutate_v2.py, audit_run.py, make_showcase.py, results/, truth/, overlays/, experiments/*/ (run.py, NOTES.md, results, tracks, overlays, helper scripts); this session doc. The restored `2026-10-10-glasses-pov-tracking/truth/` files should show as unmodified. Not: work/, *.mp4, __pycache__, .venv.
