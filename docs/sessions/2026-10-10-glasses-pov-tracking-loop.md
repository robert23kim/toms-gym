# Glasses-POV bowling tracking loop (2026-10-10)

Loop folder `docs/research/2026-10-10-glasses-pov-tracking/`. Request: analyse 11 first-person Meta-glasses bowling videos, run experiments, cut away the walk-up, finish with a showcase (video one side, rendered ball trace the other). Engine worktree `~/code/bowling-app/pov-engine`, branch `exp/r2-glasses-pov` (off `exp/r1-yolo-first-chain`).

## What was done, in order
1. Cuts. 10 of 11 videos cut to release-10 .. pin_hit+20 (82-99 frames, H.264, same resolution). 191900 has no throw. Releases for 185121/185331/185645 copied from the 09-19 truth; the other 7 are visual reads. All 10 checked by frame-0 difference (0.7-0.8 at offset 0, 17-32 at +-1,2).
2. Truth for the dev split. 185454, 190115 labelled this loop (HSV chain, Lab b* radius, 18 frames per video eye-checked, board 10.5 and 8.5, +-1.0). Others reused.
3. Baseline. 4 engine configs x 10 cuts = 40 runs. Best yolo_chain_sam: recall 72.0 dev / 43.9 holdout, pass 1/5 and 1/5.
4. Six experiments, one process at a time, holdout truth withheld.
5. Judges re-ran each experiment on dev and scored the holdout. Holdout truth released after scoring.
6. Integration: fixed rule picked sam2-video for all 11 videos. Fallback applied on 0 stems.
7. Showcase rendered (28.9 s, 10 throws), critic pass, re-render with four fixes.

## Numbers

| | dev recall | holdout recall | board_err | verdict |
|---|---|---|---|---|
| baseline yolo_chain_sam | 72.0 | 43.9 | 0.5-5.5 where present | - |
| cam-diff | 95.3 | 73.0 | 2.7 | works |
| lane-first | 90.9 | 77.3 | 2.2 | works |
| appearance-prior | 97.5 | 98.8 | 3.25 | partial |
| sam2-video (chosen) | 97.5 | 90.46 | 2.5 | works |
| detector-tiling | 91.9 | 78.56 | 2.25 | works |
| wildcard | 96.1 | 76.5 | 2.75 | partial |

Chosen method on the 10 throws: dev 4/5 pass (board_err 1.0 over 4 boards), holdout 2/5 pass (board_err 2.5, board <= 3 on 3/5). Per-stem table in `README.md`.
Cost: sam2-video wall time 62-223 s per video (mean over dev 111.7 s); lane-first 1.3 s per video.

## Critic fixes applied to the showcase
Circle stops at the last lane frame (191913 gutter circle). Leading outlier trimmed (192636). Pin rack flipped. 185121 moved last and labelled "no lane fit". Interpolated circles orange. Dev/HOLDOUT tag added.

## Still broken
- 192142 board 5 vs truth 10 and 192636 board 7 vs truth 12.5; every method reads 4-5.5 boards low. Truth rests on 3 reads each. Unknown whether the fault is the lane quad or the truth.
- 191913 recall 56.5 %: far-end crop pass drifts to a gutter object from f493. Its board_err 0.0 is luck and decides the method choice.
- 185121: no lane fit, no board, no top-down trace (handheld video, wrong lane for the engine).
- 192636 median px error 7.7, wall time 222.9 s.
- Release and pin hit are inputs, not outputs. window_err is not an end-to-end number.
- Scorer has no small far-end shift mutation.
- appearance-prior's final regeneration (tag final_fixed_sam) was incomplete at budget end; shipped tracks are from the identical-config run `results/fixed_noyolo_sam.json`.
- Not verified here: the numbers above were copied from the loop's result files (`results/final.json`, judge JSONs, critic notes), not re-run.

## Next steps
1. Re-read 192142 and 192636 boards; score the lane stage alone.
2. Gate the 191913 far-end drift and re-score; report the choice with and without it.
3. Automatic release/pin detection, scored as window_err.
4. 15/25 px far-end mutations in `score_tracks.py`.
5. Image-space fallback trace for refused lanes.
6. Try lane-first as a fast board prior.
7. Merge or archive branch `exp/r2-glasses-pov`; the engine worktree is clean.

## Files to commit (nothing committed yet)
Under `docs/research/2026-10-10-glasses-pov-tracking/`: `README.md`, `RULES.md`, `.gitignore`, `track.py`, `lane_geom.py`, `make_showcase.py`, `score.py`, `score_tracks.py`, `results/` (JSON, notes, tracks, tracks_baseline), `truth/`, `overlays/`, `experiments/*/` (code, NOTES.md, results, tracks, overlays; not caches or `.venv`). Plus this file. Gitignored, not committed: `showcase.mp4`, `work/`, `__pycache__/`, `*.pt`, `.venv/`.

## Retro (lead, after the run)
Run: workflow `wf_87256d40-4b6`, 24 agents, 0 errors, 945 tool calls, 3.7 h wall. Model split held and was verified from the transcripts: 6 experiments on Fable (137-182 turns each), cut/truth/baseline/judges/integrate/critic on Opus, gate/showcase/showcase-fix/docs on Sonnet. Measured usage from the agent transcripts: 237 M cache-read, 19.9 M cache-write, 0.42 M input, 0.35 M output tokens; the harness reported 3.84 M.

- **Went well.** The dev/holdout split did its job: every experiment dropped from dev to holdout (cam-diff 95 to 73, wildcard 96 to 77) and the judges scored the holdout before anyone saw its truth. The critic found four real showcase defects (gutter circle, empty opening panel, upside-down pin rack, outlier diagonal) and the fix pass cleared them in one go. Resume was never needed.
- **Went badly.** The Cut brief let dev release/pin frames be copied from the 09-19 truth, so `window_err` is 0 by construction and the dev numbers are not end-to-end. The Truth brief asked for a board but not a minimum number of board reads; 192142 and 192636 got 3 each and are the two boards every method misses by 4-5.5, so the loop cannot say whether the lane stage or the truth is wrong. The experiment brief did not require camera-compensated overlays, so the per-experiment overlays are not evidence. The method choice flips on one lucky board (191913).
- **Change next time.** Make release/pin detection a scored stage, never an input. Require at least 5 independent board reads per truth board and a stated uncertainty. Require the `final__` overlay format (camera-compensated path on one frame) from every experiment. Have each judge score the lane stage separately from the ball track. Report method-choice sensitivity (leave-one-stem-out) in `final.json`.
