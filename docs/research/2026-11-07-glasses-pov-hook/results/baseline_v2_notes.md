# Baseline v2: loop-1 sam2-video tracks scored with score_v2.py (dev only, 2026-11-07)

Scorer `score_v2.py` (definitions in its docstring), table `score_all.py` -> `results/baseline_v2.json`,
mutations `mutate_v2.py` -> `results/mutations_v2.json`. Tracks: `L1/results/tracks/<stem>.json`, unchanged.
Holdout truth was not opened. Windows (far = pin_hit-12..pin_hit, roll tail = last 60 %) use the TRUTH frames.

## Table (boards from the right gutter)

| stem | recall | far recall | med px / far | path_err_rms | path_err_far | far bias | entry_err | hook_err (track vs truth hook) | trend track / truth (12 f) | direction_ok |
|---|---|---|---|---|---|---|---|---|---|---|
| 185121 | 100 | 100 | 1.4 / 2.0 | - (14/14 missing) | - | - | - (no final_board) | - | - / -0.36 | - |
| 185331 (hooks) | 100 | 100 | 6.0 / 8.3 | 5.60 | **5.05** | -4.62 | 1.88 | **3.87** (5.48 vs 1.61) | **-3.49 / +2.14** | **false** |
| 185454 | 100 | 100 | 1.6 / 1.1 | 4.64 | 0.82 | -0.78 | 0.61 | 1.82 (1.81 vs -0.01) | -1.51 / -0.76 | true |
| 185645 | 100 | 100 | 2.0 / 1.9 | 2.11 | 1.42 | -1.04 | 0.52 | 1.90 (2.01 vs 0.11) | -1.94 / +0.02 | **false** |
| 190115 | 100 | 100 | 2.1 / 2.1 | 2.26 | 1.05 | +0.51 | 1.01 | 1.80 (2.05 vs 0.25) | -1.97 / -0.74 | true |
| mean | 100 (5) | 100 (5) | 2.6 / 3.1 | 3.65 (4) | 2.08 (4) | -1.48 (4) | 1.00 (4) | 2.35 (4) | | 50 % (2/4) |

wall_s (loop-1 meta): 129.5, 89.7, 69.8, 78.2, 166.5 (mean 106.7).

## What the loop-1 method already fails
- **Ball detection is not the problem on dev**: recall and far recall are 100 % on all 5 (v2 truth is 13-15 points
  per stem, tolerance max(2r, 15) px). The far-end pixel error is 1-2 px except 185331 (8.3 px median at the deck).
- **The far end of the board path fails on the one hooking dev throw.** 185331 truth goes 5.27 (f346) -> 7.95 (f358);
  the track's boards fall 4.5 -> 0.4 -> -0.5 -> 0.9, i.e. into the right gutter, 4.6 boards low on average over the last
  12 frames, trend -3.5 vs +2.1, direction_ok false. On the three non-hooking stems with a lane, path_err_far is 0.8-1.4.
  So the expected far-end failure is real but concentrated on 185331; it is the loop-1 "every method reads the hookers
  4-5.5 boards low" pattern (192142/192636 on holdout) showing up on dev.
- **entry_err is mostly fine on dev** (0.5-1.0 on 185454/185645/190115) and 1.88 on 185331. The engine final_board 5.0
  on 185331 is not what the per-frame boards say at the end (0.3-0.9), so final_board is right-ish by smoothing, not by
  reading the hook: its last-5 boards are all below 1.6.
- **hook_err 1.8-3.9 on every stem: the raw board series invents a hook.** Track entry minus the raw min over the last
  60 % of the roll is 1.8-2.05 on three throws whose truth hook is -0.01 to 0.25. The per-frame boards jitter by 1-2.5
  boards frame to frame at the far end (185645: 7.6, 5.6, 7.7, 5.0 over f293-299; 190115: 7.95 at f442), so min is a
  noise floor and entry (median of last 5) sits above it. Any loop-2 path drawing taken from raw per-frame boards would
  draw a hook that is not there; this is why hook_err must be read with direction_ok and the truth hook together.
- **direction_ok 2/4**: 185331 fails on the missed hook; 185645 fails because the truth is flat (+0.02) and the track
  jitters down -1.94 over the last 12 frames.
- **direction_ok is only informative where |truth trend| >= 1 board over the last 12 frames**, which on dev is 185331
  alone. On the flat-truth throws the verdict follows the sign of truth noise: 185454 (truth -0.76, track -1.51) passes
  and 185645 (truth +0.02, track -1.94) fails on the same jitter. Read the 2/4 as 0/1 on the hooker plus three coin flips.
- **Near-end board error dominates path_err_rms on two stems**: 185454 reads 7.0-9.2 at f332-350 where truth is
  18.2-14.2 (near-end lane quad wrong; bias -3.1 overall, -0.8 far), 185331 f304 reads 2.5 vs 16.97 (release frame).
  Use path_err_far for the pocket and path_err_rms for the whole line.
- **185121 has no lane** (SAM lane refused): no boards, no final_board, path_missing 14/14. Its means are left out
  (entry/path/hook n=4).

## Mutations (results/mutations_v2.json; in memory, real loop-1 tracks)
- (a) empty frames: recall 100 -> 0, far recall 100 -> 0 (185454, 190115).
- (b) +25 px x on track frames >= pin_hit-12: far_recall 100 -> 0 on both; recall 100 -> 46.2 (185454) and 40.0 (190115).
  Recall drops by exactly the far share (7/13, 9/15 truth points are in the far window), which is the truth's density at
  the deck, not a scorer leak; far_median_px_err 1.1 -> 25.7 and 2.1 -> 26.1.
- (c) mirrored boards (40 - board, boards + lane_top_down + final_board): 185331 (the dev hooker) path_err_rms 5.60 -> 28.25,
  path_err_far 5.05 -> 32.65, direction_ok false -> true (trend -3.49 -> +3.49 against truth +2.14). The flip goes the
  "wrong" way because the baseline already gets the direction wrong. 190115: 2.26 -> 19.13, direction true -> false.
- (d) final_board = boards[pin_hit-2]: 185331 entry_err 1.88 -> 6.61, 185454 0.61 -> 1.28, 190115 1.01 -> 1.04 (7.95 and
  10.0 sit almost symmetrically about truth 8.99). Precondition not met: no dev track has a last-12 trend >= 1
  board/frame; the steepest is 185331 at 0.29 board/frame (-3.49 over 12 frames).
- extra (e) truth as track: recall 100, path_err_rms 0, entry_err 0, hook_err 0, direction_ok true on 190115 and 185331.
- extra (f) path_fit branch: boards/lane_top_down removed, path_fit.boards_by_frame = old boards + 3, board_at_60ft =
  final + 3 -> path_sources {path_fit: 13}, path_bias -3.11 -> -0.11, entry_err 0.61 -> 2.39 (185454).
No mutation failed to move its metric; no scorer fix was needed.

## For loop-2 experiments
- Emit `path_fit.board_at_60ft` and `path_fit.min_board` to be scored on the fit; emit `path_fit.boards_by_frame`
  ({"<f>": board}) to be scored per frame when `boards`/`lane_top_down` are absent. `boards` wins over the others.
- A smooth fit through the raw boards would cut hook_err on the three flat throws (track hook 1.8-2.05 is noise), but on
  185331 it must rise in the last 12 frames to pass direction_ok; one dev hooker is thin evidence (holdout has two).
