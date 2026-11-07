# Refute: provenance of results/tracks/*.json (skeptic, 2026-11-07)

Claim tested: L2/results/tracks/*.json are tracker output (track_v2), scored against an independent truth.
Verdict: **not refuted on leakage.** Two must-fix wording caveats on how independent the holdout number is (below).
Scratch: `work/refute_provenance/` (rerun.py, audit_*.json, rescore_*.json, mutate_one.py, mutation_192636.txt). No shipped file changed: the shasum of all 10 shipped tracks and of overlays/final__192636.jpg matched before and after.

## (a) Static scan of the import closure
- The closure was taken from a live run (`rerun.py`: sys.addaudithook, then a sys.modules listing). Project modules loaded: track_v2.py, experiments/lane-gated-ball/run.py, experiments/composition/run.py, L1 lane_geom.py, L1 cam-diff/camdiff.py, L1 lane-first/lane.py. Lazy imports that did not fire: L1 sam2-video/sam_track.py (the LGB re-prompt) and composition's appearance-prior + pov-engine apptrack (ball_stage is replaced by the injection).
- The coarse candidate source, the L1 sam2-video track, was not truth-prompted. L1 sam2-video/run.py opens only cuts.json, and prompt.py has no `open(` or truth hit (grep exit 1). The only truth readers in that folder are smoke1.py and mutation_check.py, which are test tooling.
- `grep -Ei 'truth|label|pov-holdout'` over those 7 files gives 4 hits, all docstrings or meta strings: track_v2.py:14, lane-gated-ball/run.py:13, composition/run.py:15 and :435. There is no file I/O on a truth or holdout path. A grep for hardcoded holdout stem ids (1912/1918/1919/1921/1926) finds only composition/run.py:12, a docstring about the stems SAM refused. No experiment .py/.sh/.md under experiments/ names pov-holdout.
- Dynamic: 164 opens, 0 matching truth/label/pov-holdout. Canary: cuts.json and the L1 sam2-video track were both opened, so the hook was recording. No writes outside scratch except the expected L2/__pycache__ pyc. The shipped audit logs agree: 155-165 opens per stem and 0 bad opens on all 10.

## (b) Re-run on holdout 20260915_192636_7c7fbfb0
- The same code was run with TV.L2/TV.WORK pointed at scratch (exit 0). boards (71), frames, lane, lane_top_down and final_board 13.8 are all identical to the shipped track. The only byte difference is meta.wall_s (225.6 vs 225.7, a timing field). So the shipped track is reproducible from the current track_v2.py and the inputs on disk. Only one stem was re-run. track_v2.py mtime is 16:40:12 and the tracks were written 16:40:15-16:40:40, so the code on disk is the code that wrote them.

## (c) Re-score against HO/20260915_192636_7c7fbfb0.json
- score_v2 on the rerun gives far_recall 100, far px 0.9, path_err_rms 0.36, path_err_far 0.44, entry_err 6.75, hook_err 6.38, direction_ok True. These match final_v2.json rows[9] exactly. v1 re-scored: far px 10.5, path_far 4.66, entry 13.55, matching the v1_* fields.
- The holdout truth files were written 15:40-15:50, before any loop-2 experiment ran (run.py files 16:14/16:17) and before the tracks (16:40). The truth tools (HO/work/tools) are seeded only from HO/loop1 truth (ball and lane_quads). They read no tracker output. HO/loop1 `lane_quads` are themselves loop-1 truth: per-row wood->gutter edge fits made by holdout truth agent 4 on 2026-10-10 (`truth_method`), not engine SAM quads. The seeds also only centre the search: `measure.py` re-fits the edges from pixel steps, and every point is confirmed by eye.

## (d) Far-end mutation on the shipped 192636 track (in memory)
- Shifting x by +25 px on frames >= pin_hit-12 (17 points) takes far_recall 100 -> 0, recall 100 -> 46.2 and far px 0.9 -> 25.0. +40 px gives the same. The far tolerance is max(2r, 15) = 16-20.4 px on this stem, so 25 px is outside it.
- The board metrics do not move under the x shift. score_v2 reads the track's own boards{}/final_board and does not recompute them from x. A separate mutation, boards +3 on the far frames, takes path_err_far 0.44 -> 2.93. So the board metrics are live too, but a track whose boards{} disagreed with its own ball points would not be caught.

## Caveats (must fix in the claim's wording)
1. **The truth is the same instrument as the tracker.** The holdout ball is a purple-hue/dark blob fit (H 105-175, S>=35 or V<60), confirmed by eye. lane-gated-ball's far refine is a purple disc filter (H 112-170, S>=30). The truth boards come from same-frame wood->gutter edge lines, and the composition lane is per-frame wood-mask gutter edges. There is no data leak. But "0.9 px / 0.44 boards" measures agreement with that shared instrument, and v1 (SAM masks) is scored on the instrument v2 copies. The truth's own pin ruler disagrees with the edge profile by 1-2 boards (192636 limits), so absolute board accuracy below ~1.5 boards is not established.
2. **The holdout is not untouched for the integrated pick.** The ball and lane stages were chosen from the judges' holdout rows (judge_*.json). That is why the leave-one-out flips exist. So the v2 holdout means are post-selection, not a fresh test. before_after (n=10) also mixes 5 in-sample dev stems, on which the refine thresholds and the smoothing were tuned.
- Not provenance, but worth noting: 192142 and 192636 entry is scored at the observed contact, 6 frames after cuts.json pin_hit, while every tracker evaluates at pin_hit. The truth release/pin_hit equal cuts.json (shared input).
