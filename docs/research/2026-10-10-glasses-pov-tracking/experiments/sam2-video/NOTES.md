# sam2-video: SAM 2.1 video propagation as the glasses-POV ball tracker (2026-10-10)

Loop: `docs/research/2026-10-10-glasses-pov-tracking`, experiment folder `experiments/sam2-video/`.
Baseline to beat: `results/baseline.json` config `yolo_chain_sam`, dev mean recall 72.0 %, 1/5 dev pass.

## What was built
`run.py <stem> [--device mps|cpu]` reads `work/cuts/cuts.json` + the cut, writes `tracks/<stem>.json`
(tracks format, SOURCE frames) and `overlays/<stem>.jpg` (pin_hit-4 frame, track polyline, lane quad, final board).
Modules: `prompt.py` (purple-blob prompter), `sam_track.py` (SAM 2 propagation + gate + crop re-prompt).
Driver: `run_dev.sh <stem>...` (run + score sequentially, one torch process at a time; appends `dev_scores.jsonl`).
Checks: `mutation_check.py`, `lane_debug.py` (verbose engine lane pass on a saved track), `smoke1.py` (first smoke).

Pipeline per cut (k = cut-local frame, source = cut_start + k):
1. **Prompt**: first frame in release+3 .. release+23 with a *chained* compact purple blob (HSV 118-165, S>=50,
   V>=35; aspect 0.55-1.8, bbox fill >= 0.45, area >= 300, lower 75 % of the frame) that has motion-consistent
   successors at k+1 and k+2 (distance <= 3 r + 60 px, area ratio 0.4-2.5). YOLO (`yolo11n_bowling.pt`) is the
   fallback and was never needed. All 10 cuts prompt at release+3 except 185121 (release+16: the ball leaves the
   top of the frame at release and re-enters at r 22 px).
2. **Forward propagation**: `SAM2VideoPredictor` (ultralytics 8.4.14, `models/sam2.1_t.pt`, imgsz 1024, one box
   prompt) over a temp sub-clip k0 .. pin_hit+4. Per frame: mask centroid, equivalent radius sqrt(area/pi).
3. **Gate**: death at the first missing mask, area > 2.5x the median of the last 3, or centroid jump > 4 r + 40 px.
4. **Far-end crop re-prompt** (up to 3): a 480 px window centred 2 frames ahead of the last good point, upscaled
   2x, prompted with the last good box, propagated to pin_hit+4; points touching the window edge end the pass.
5. **Backward propagation**: the same prompt on the reversed frames k0 .. release, so the blurred near-release
   ball (r 55-130 px) is tracked too; a compact-blob chain backwards from k0 fills anything SAM misses.
6. **Lane + board**: the engine's `scripts.sam_lane_pass.run_sam_lane_pass` (SAM lane calibration, `pov-engine`
   ad2c96e) with `segment=` the track restricted to release+8 .. pin_hit and positions <= pin_hit, pin hit from
   cuts.json. Per-frame quads -> `lane`, calibrated boards -> `boards`, `final_board` from the engine.
`release_frame`/`pin_hit_frame` in the output are the cuts.json values (inputs), so `window_err` is 0 by
construction and is not a tracker claim. The engine's `last_lane_frame` is in `meta` (9-11 frames before pin hit).

## Dev table (MPS, scored by `L/score_tracks.py`; baseline = yolo_chain_sam)
| stem | recall % | median px | board_err | lane_err | wall s | verdict | baseline recall / board_err |
|---|---|---|---|---|---|---|---|
| 185121 | 94.4 (17/18) | 8.4 | - (lane refused) | - | 131.4 | no board | 88.9 / - |
| 185331 | 93.3 (56/60) | 5.0 | 0.5 | 0.89 | 96.2 | strong | 56.7 / 0.5 |
| 185645 | 100.0 (62/62) | 3.5 | 1.5 | 0.44 | 80.1 | strong | 85.5 / 3.5 |
| 185454 | 100.0 (52/52) | 2.1 | 0.5 | 1.88 | 77.6 | strong | 59.6 / 2.5 |
| 190115 | 100.0 (55/55) | 2.0 | 1.5 | 1.25 | 173.1 | strong | 69.1 / 0.5 |
| **mean** | **97.5** | | 1.0 (4 boards) | | 111.7 | **4/5 pass, 4/5 strong** | 72.0, 1/5 pass |

Overlays `overlays/<stem>.jpg` were read for all five: the polyline ends at the pins of the lane the cyan quad marks
on every stem; the swirl near the pins is raw camera motion (the glasses tilt), not tracker wobble. Scorer mutation
check (`mutation_check.py 185454`): original 98.1 % / board_err 0.5 -> shifted +100 px, board +5: 13.5 % / 5.5 /
lane_err 43.7 (the survivors are the near-release points whose tolerance is 2 r = 110-260 px).

Holdout cuts (191253, 191820, 191913, 192142, 192636) were run with the same code for the showcase; their truth
was not read and they are not scored here. 191900 (no throw) gets an empty track.

## Runtime per video
Wall (MPS, M3 Pro, other agents on the box): 77.6 / 96.2 / 80.1 / 173.1 / 131.4 s, mean 111.7 s. Breakdown: SAM
forward 26-39 s (0.51 s/frame at 1376x1840), backward 2-8 s, crop pass 3-16 s, engine lane pass 43-55 s when
its first candidate frames fit, 138-147 s on 190115 (five candidates at residual 12-13 px before frame pin+6 fits),
108-180 s when it refuses (185121). CPU: SAM forward pass on 185454 1.12 s/frame (77 s for 69 frames) vs 0.51 s/frame
MPS (35 s); no unsupported-op fallback was seen in the unfiltered smoke run (later runs filtered stderr). The 120 s target holds on 3 of 5 dev stems; the lane pass
is what breaks it, not SAM.

## What worked
- SAM 2.1-tiny propagation from ONE box at release+3 follows the ball through pin contact on the glasses videos
  without any crop: 185454 full pass 53/53 masks, 0.2-10 px from truth down to r 9 px (truth) at the pins.
- The chained compact blob is a prompt that never missed on 10 cuts; on the near half it is itself a tracker
  (<= 5 px from truth at release+1..+7 on 4 of 5 dev stems).
- Backward propagation adds the big blurred ball at release (3 frames on 4 stems, 7 frames k 19-25 on 185121),
  which is exactly what the baseline chain never linked (it started 8-11 frames after release).
- The crop re-prompt is load-bearing where the full-frame mask dies early: 185331 (death k=64, 11 frames added),
  185645 (5), holdout 191913 (18), 192636 (12), 192142 (6).
- The engine lane pass gives a board within 1.5 on the 4 stems it calibrates when fed release+8..pin_hit.

## What failed (with the number that killed it)
- Largest purple blob as the prompt: the right gutter's blue glint (area 9095) beat the ball; SAM tracked the glint
  coherently for 12 frames, 740-1340 px from truth, 0 % recall (first smoke on 185454).
- Lane pass fed the whole track: refused on 185331 and 185645 ("mask top 574 is 874 px short of the path's far end",
  "167835 px short", residuals 35-96 px) because the post-pin-hit points (camera whipping away) and the release
  frames (aligner warp broken through the head swing) land nowhere. Trimming to release+8..pin_hit fixed both.
- Gate that ended at the last mask instead of pin_hit+4: a mask missing at the tail never counted as a death, so
  holdout 191913 stopped at f495, 14 frames before pin hit, with no crop pass. Fixed (gate walks to k_end).
- 185121 lane calibration refuses with this track as with the baseline's (it is the handheld 1184x1584 video,
  not glasses); recall 94.4 % but no board, so no pass. Not fought.
- Reading the board from the five crop frames past pin hit moved 190115 from 9.0 to 10.0 (truth 8.5); restricting
  the board read to <= pin hit did NOT move it back (10.07 raw, lane_err 1.25 vs 1.61 before: the calibration picked
  a different reference frame once k=pin_hit was in the segment). Left at 1.5, within the gate.
- Pin-hit estimate "first frame the ball centre is above the quad's deck row" gave 302 for a 358 pin hit on
  185331: the per-frame quad at release frames is not a deck row. Removed; `last_lane_frame` is kept in meta.
- Wall time: the engine lane pass alone is 138-195 s on 190115 and holdout 192636.

## What was tuned on truth
- HSV range widened to H 118-165 after reading the ball's HSV at dev-truth positions (median H 123-136, S 70-164).
- PROMPT_OFFSET = 3 and the compact-blob filters were chosen by comparing blob centres with dev truth at
  release+1..+9 on all five dev stems (<= 5 px on 4 stems); PROMPT_SCAN = 20 because the 185121 truth/visual scan
  showed the ball re-entering at release+16.
- Board read restricted to <= pin hit after the 190115 board moved vs truth (no effect in the end).
- NOT tuned on truth: LANE_SEG_START = 8 (from the engine's own lane log), PIN_TAIL = 4, gate thresholds
  (set once, not tuned; the backward pass uses 3.5x / 80 px), crop side 480 / scale 2 / 3 passes.
- cuts.json release/pin_hit frames are inputs (truth-derived on 185121/185331/185645) and bound the passes.

## Next
- Replace the engine lane pass's candidate loop (the wall-time sink) or cache its aligner; cap the pass at ~60 s.
- Holdout truth scoring by the orchestrator; 191820 (right gutter ball per cuts.json notes) reads board 1.0
  (raw -4.17), which is the gutter.
