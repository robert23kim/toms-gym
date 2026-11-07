# far-end-stacking (loop 2, stage: ball) — 2026-11-07

Lens: motion-compensated temporal stacking for the tiny far-end ball (r 4-13 px), seeded from the loop-1 sam2-video
track. `run.py <stem> [--device mps|cpu]` (cv2/numpy only; `--device` is accepted and unused, no torch), ~6 s per stem
on top of the loop-1 track it builds on (loop-1 wall 70-167 s). Outputs `tracks/<stem>.json` (tracks format, SOURCE
frames, `stage: "ball"`), `overlays/final__<stem>.jpg`, `work/<stem>_cands.json` (per-frame candidates and the linked
positions for every N), `results/dev.json` (`make_dev.py`), `results/score_<stem>.json`, `results/cands_<stem>.json`
(`score_cands.py`, truth-side, dev only).

## What actually fails in the loop-1 far end (read before building)
Baseline v2 far recall is already 100 % on all 5 dev stems at tolerance max(2 r_truth, 15 px), so there was no
detection miss for stacking to recover. The one far-end failure is **185331**: the sam2 mask swallows the dark
object touching the ball from f348 on, so the track sits 6-9 px up-right of the ball with r 14-16 against truth 7.5-8.5
(far median 8.3 px; the per-frame boards fall into the right gutter, direction_ok false). The other four stems are
at 1-2 px, the hand-read floor.

## Method as built
1. ORB homographies per frame pair (`L1/experiments/cam-diff/camdiff.py: Motion`, half-size grey), chained for
   frame-to-frame carries (`Chain`).
2. Window = pin_hit-24 .. pin_hit+2 (27 frames). Seed = the loop-1 track's last 10 frames before the window: position,
   camera-compensated velocity (mean of 3 carried differences), radius from the purple connected component (median).
3. Energy per frame, full-res: blur(purple hue 112-170, S >= 30) x blackhat(grey, ellipse 2.2 r) x |three-frame
   camera-compensated residual| (each blurred by r/3). Candidates = top-6 local maxima inside a gate of
   max(45, 6 r) px around the carried constant-velocity prediction, plus the prediction itself (penalised 0.7/frame,
   for occluded frames).
4. Stacking: a candidate's unary = sum over the N-1 neighbouring frames of log(E_{t+d}(path point) / Emax_{t+d}),
   where the path is the candidate's own constant velocity (candidate minus the carried best previous state)
   carried by the chained homographies. N=1 is the no-stacking control.
5. Linking: first-order DP over the candidates, transition = ||c - (carried prev + carried prev velocity)||^2 /
   (2 sigma^2), sigma 8 px, velocity per state from its back-pointer (0.7 observed + 0.3 carried).
6. Two passes: pass 1 with the seed radius everywhere; pass 2 recomputes the energy with the per-frame radius
   measured in pass 1 (non-increasing toward the pins, floor 0.5 r_seed). With the pass-1 kernel (2.5 r_seed = 35 px)
   the energy peak merged with the dark object on 185331 f343-352 (4-5 px up-right).
7. Final centre: purple pixels inside a disc of 1.3 r around the pick, two mean-shift steps capped at r/2 in total
   (`purple_disc`); energy-weighted centroid inside 0.8 r when fewer than 0.35 pi r^2 purple pixels (never fired on
   dev). r = sqrt(count / pi), clamped non-increasing.
8. Output: loop-1 points outside the window, these inside; boards for the replaced frames from the loop-1 lane quad
   of that frame (`lane_geom.lane_point`); `final_board` is loop-1's engine value, unchanged (stage ball; entry_err is
   therefore the baseline's); `lane_top_down` recomputed with `track.add_top_down` logic.

## Dev results (`results/dev.json`, scorer `L2/score_v2.py`, truth `L2/truth`)

| stem | recall | far recall | median px | far median px | path_err_rms | path_err_far | entry_err | hook_err | direction_ok | +wall s |
|---|---|---|---|---|---|---|---|---|---|---|
| 185121 | 100 | 100 | 1.4 (1.4) | 1.7 (2.0) | - | - | - | - | - | 5.6 |
| 185331 | 100 | 100 | 1.9 (6.0) | 1.9 (8.3) | 4.29 (5.60) | 0.56 (5.05) | 1.88 (1.88) | 1.38 (3.87) | true (false) | 5.4 |
| 185454 | 100 | 100 | 1.5 (1.6) | 1.0 (1.1) | 4.59 (4.64) | 0.42 (0.82) | 0.61 (0.61) | 1.82 (1.82) | true (true) | 8.2 |
| 185645 | 100 | 100 | 1.6 (2.0) | 1.0 (1.9) | 1.97 (2.11) | 0.90 (1.42) | 0.52 (0.52) | 0.36 (1.90) | true (false) | 5.5 |
| 190115 | 100 | 100 | 0.5 (2.1) | 0.4 (2.1) | 2.31 (2.26) | 1.18 (1.05) | 1.01 (1.01) | 0.87 (1.80) | true (true) | 7.1 |
| mean | 100 | 100 | 1.38 (2.62) | 1.20 (3.08) | 3.29 (3.65) | 0.77 (2.08) | 1.00 (1.00) | 1.11 (2.35) | 100 % (50 %) | 6.4 (+106.7 loop-1) |

Baseline (loop-1 sam2-video, `L2/results/baseline_v2.json`) in brackets. Beats the baseline on far_median_px_err
(3.08 -> 1.20), median_px_err (2.62 -> 1.38), path_err_far (2.08 -> 0.77), hook_err (2.35 -> 1.11), direction_ok
(2/4 -> 4/4), path_err_rms (3.65 -> 3.29, small). Ties recall / far recall (100) and entry_err (loop-1 final_board
kept). Wall is additive (+6.4 s), not a beat. Deterministic: two reruns gave identical scores on all 5.

Not a passthrough: 27 frames replaced per stem, median shift vs loop 1 of 1.4 / 4.7 / 1.8 / 1.6 / 1.4 px, max 12.3 px
(185331). Outside the window frames[] and boards{} are loop-1's; lane_top_down is refit over the whole track (ft model includes the replaced samples). Bias check on the frames before the 185331 failure
(f334-346): new-vs-loop-1 shifts 0.8-3 px except f343-345 (4.8-6.4 px, see residual below).

## Stacking does nothing on dev (the honest finding)
`results/dev.json: by_n`. Far-band recall before linking (any candidate within tolerance) is 100 % on every stem,
and after linking 100 % for N = 1, 3, 5, 7. The linked positions differ by at most 0.3 px between N=1 and N=7
(185331 3.05 vs 3.34, 185645 4.39 vs 4.30; the other three identical). The no-colour ablation
(`--no-purple-energy`, energy = blackhat x residual only, `work/ablation_no_purple/`) also keeps 100 % pre-link recall
with N=1 = N=5 everywhere except 185331 (4.10 vs 3.86 px). The single-frame energy peak already lands within 3-4 px
of the ball on every far frame; the gain is the re-centring, not the stacking. At the stricter tolerance of one
truth radius (7-13 px, `results/recall_at_r_truth.json`) far recall is still 100 % before linking and for every N, so
the candidate gate (45+ px around a seeded prediction) is not what makes the metric saturate. The lens's premise (far-end candidates
are missing) does not hold once the roll is cut to release..pin hit and the window is seeded from a track.

## Ablations (all on dev truth)
- Final-centre rule: `purple` 1.20 mean far median vs `energy` (energy-weighted centroid) 2.46 — the residual-based
  centroid is leading-edge biased on 185454/185645/185121 (1.8 / 3.3 / 3.2 px). Purple disc chosen.
- Purple disc radius: 1.0 r -> 2.9, 1.1 r -> 1.6, 1.3 r -> 1.2 (chosen). Smaller discs clip the ball itself.
- Saturation-weighted purple centroid (`--sat-weight`, clip((S-25)/40)): 1.2 mean, same as unweighted (185121 1.2,
  185331 2.3, 185454 0.9, 185645 1.2, 190115 0.4). Not adopted (no gain, one more rule).
- sigma 4 / 5 / 8 px: identical far medians on 185331 (2.6 linked / 2.89 final in the single-pass version).
- Single pass (seed-radius energy) + purple disc: 185331 2.9 vs 1.9 with the two-pass per-frame radius.

## Residual failure
185331 f343-345: the purple mask bleeds into the dark diagonal object beside the ball (its blurred edge reads hue
112-170 at S 30-45), the disc centroid moves 3-4 px up-right, board dips to 2.8 at f344 against truth 5.7
(`work/diag_185331_jog.jpg`, green truth / orange DP pick / cyan final). The DP pick itself is within 2 px there, so a
contamination guard (reject the refinement when the mask count exceeds the expected area) would fix it, but the
count ratio (1.15-1.26) overlaps clean frames on 185645 (1.24). Left as is: one frame, median unaffected, path jog of
~3 boards for 2 frames.

## Harness notes
- The loop-1 `camdiff.Motion` ORB homographies are reproducible run to run here (scores byte-identical on rerun).
- Cut frames are 1248x1664 (not the source 1376x1824); everything in SOURCE numbering via cuts.json cut_start.
- `echo ====` fails in zsh (`=` expansion); use `echo ----`.
- The hook that rewrites `ls`/`grep` makes the first Bash call of each such command fail the auto-mode check; the
  verbatim re-issue passes.

## tuned_on_truth
Every choice below was made by scoring against L2 dev truth (target stem 185331, regression check on the other four):
window 24 / seed 10, blackhat kernel 2.2 r and blur r/3 (from 2.5 r and r/2), two-pass per-frame radius, the
pred-candidate penalty 0.7, log-sum stacking (from mean energy, which let the prediction candidate win at 185331
f344-346 for N >= 5), sigma 8, final-centre rule purple over energy, disc 1.3 r, mean-shift cap r/2, min purple area
0.35 pi r^2. Holdout truth was not opened; `run.py` reads no truth file.

## Missing / next
- The loop-1 lane quads are reused unchanged, so far-end boards still carry the loop-1 lane error; this experiment
  only moves the ball. 185121 has no lane (no boards).
- `final_board` is loop-1's; a path-stage experiment should read the entry from these re-centred far-end boards
  (185331 last-frame board 7.3 vs truth entry 6.9 vs loop-1 final_board 5.0).
- Contamination guard for the purple disc (185331 f343-345).
- Not run on holdout (by design of the loop).
