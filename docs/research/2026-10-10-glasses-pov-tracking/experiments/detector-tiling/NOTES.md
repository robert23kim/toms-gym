# detector-tiling: far-end tiling vs a multi-scale box pool (glasses POV, 2026-10-10)

Lens as briefed: yolo11n_bowling.pt and YOLO-World ("bowling ball") on 2x / 3x upscaled crops of the far third of
the lane plus the full frame, conf 0.05-0.3, boxes linked by the engine's `yolo_chain`. Verdict: **the upscaled far
crops are dead** (far-band any-box recall 16-20 % at 2x/3x against 91 % at native scale); what beats the baseline is
the finding underneath it, that the fine-tuned YOLO11n is **scale-specific**, so the tracker pools the boxes of four
inference scales (imgsz 320 / 640 / 1280 on the full frame + the far crop at native resolution) and links the union
with the engine chain. Dev mean recall **91.9 %** (baseline yolo_chain_sam 72.0 %), pass 2/5 (baseline 1/5).

## What was built (all in this folder; nothing in the engine worktree was edited, its modules are imported)
- `dump_dets.py <stem>`: every box per frame of the cut for 11 configs (bowl_full320/640/1280/native, bowl_far1x/
  1.5x/2x/3x, world_full1280, world_far2x) at conf >= 0.05, plus ORB camera shifts -> `work/dets_<stem>.json`
  (SOURCE frames, full-frame px). The far crop is a fixed frame fraction (rows 0.22-0.62 H, cols 0-0.80 W: where the
  pins sit on a head camera looking down the lane; every dev far-third truth point lies inside it), resized by the
  scale factor and run at imgsz = its long side.
- `raw_recall.py`: any-box recall by distance band before linking (truth frames in [release, pin_hit] split in
  thirds; hit = a box within max(2r, 20 px) with 0.4 r <= r_box <= 3 r + 6). Table: `work/raw_recall_table.md`.
- `tracker.py`: `pool_frame` (union of the configs' boxes above a per-config floor, boxes of one object merged
  into the most confident one with the MEDIAN radius over the merged boxes) + engine `chain_detections`.
- `run.py <stem> [--cache]`: cut -> 4 detector passes + ORB -> pool -> engine yolo_chain (r_grow 1.5) -> engine
  SAM lane (`calibrate_lane` with prompts from the r <= 30 px part of the chain, candidates pin-4/pin-8/pin+2,
  residual gate 14 px) -> `tracks/<stem>.json` (source frames; `fl_*` = bottom of the SAM mask, `fl_is_foul_line`
  false), `overlays/<stem>.jpg` (pin_hit-4 frame, polyline, lane quad, board), `work/run_<stem>.json` (timings).
  `--cache` reuses the dump (tuning only; the dev table below is from full runs).
- `eval_chain.py`, `score_all.py`, `cmp_overlay.py` (dev-only: track + truth on one frame -> `work/cmp_<stem>.jpg`).

## Raw any-box recall by band, before linking (mean over the 5 dev stems; full table in work/raw_recall_table.md)
| config | floor | near | mid | far | per-stem far (185121/185331/185645/185454/190115) |
|---|---|---|---|---|---|
| bowl_full320 | 0.05 | 79.6 | 36.6 | 0.0 | 0 / 0 / 0 / 0 / 0 |
| bowl_full640 (= baseline scale) | 0.05 | 58.0 | 93.1 | 35.5 | 66.7 / 0 / 19.0 / 44.4 / 47.4 |
| bowl_full1280 | 0.05 | 5.4 | 93.9 | 79.3 | 100 / 25 / 71.4 / 100 / 100 |
| bowl_fullnative (imgsz = long side) | 0.05 | 6.4 | 54.9 | 91.1 | 100 / 65 / 90.5 / 100 / 100 |
| bowl_far1x (far crop, native) | 0.05 | 2.1 | 51.4 | **91.1** | 100 / 65 / 90.5 / 100 / 100 |
| bowl_far1.5x | 0.05 | 1.2 | 3.3 | 51.7 | 50 / 70 / 52.4 / 33.3 / 52.6 |
| bowl_far2x | 0.05 | 0.0 | 0.0 | 15.9 | 33.3 / 10 / 9.5 / 11.1 / 15.8 |
| bowl_far3x | 0.05 | 0.0 | 0.0 | 19.9 | 50 / 35 / 14.3 / 0 / 0 |
| world_full1280 | 0.05 | 59.2 | 21.1 | 0.0 | 0 / 0 / 0 / 0 / 0 |
| world_far2x (185331 only) | 0.05 | 5.0 | 5.0 | 5.0 | - / 5 / - / - / - |
At floor 0.1: far1x far 88.1, full1280 far 76.3, far2x 3.0, far3x 9.3, world 0. At 0.3 everything far is <= 25.
- The far-end floor of detection at native scale is 91 % (88 % at 0.1); the weak stem is 185331, whose truth
  radius at the deck is 2-5 px (65 %). **Upscaling lowers it**: at 2x the detector returns r ~9 px boxes on the lane
  dots and pin heads and none on the ball (frame 330: nearest 2x box 265 px away, native box 0.9 px away, conf 0.27).
- The near band (release ball, r 60-130 px) is only found at imgsz 320 (80 %) / 640 (58 %); at 1280+ it is 2-6 %.
- YOLO-World (yolov8s-worldv2, "bowling ball"): 59 % near at 0.05, 0 % far on every stem, 29-40 s per video. Dead.

## Dev table (full runs, `run.py <stem>`, scored by L/score_tracks.py; baseline yolo_chain_sam in brackets)
| stem | recall % | median px | board_err | lane_err (boards) | window_err | pass | wall s |
|---|---|---|---|---|---|---|---|
| 185121 | 94.4 (89) | 11.7 | 7.0 (-) | 59.37 | [10, 0] | no | 136.6 |
| 185331 | 85.0 (57) | 7.2 | 4.5 (0.5) | 0.63 | [4, 3] | no | 90.3 |
| 185645 | 95.2 (86) | 6.4 | 3.5 (3.5) | 0.36 | [4, 4] | no | 60.5 |
| 185454 | 92.3 (60) | 5.7 | 0.5 (2.5) | 1.60 | [4, 1] | yes | 64.3 |
| 190115 | 92.7 (69) | 5.0 | 0.5 (0.5) | 1.74 | [4, 4] | yes | 123.1 |
| mean | **91.9** (72.0) | | 3.2 (1.75 over 4) | | | 2/5 (1/5) | 95 |
Runtime per video: detect 24-36 s (full320 1 s, full640 3 s, full1280 8-15 s, far1x 5-11 s, ORB 4-5 s), chain
< 0.1 s, SAM lane 34-100 s. Two stems exceed the 120 s target because the engine keeps trying candidates while the
fit residual stays above its 5 px "good" threshold (the glasses lens bends the edges: 8-13 px on 185121/190115).
Holdout tracks were produced with the same script (`tracks/<holdout stem>.json`, not scored here; see run_holdout.log).

## What worked
- Multi-scale pool + engine chain: every dev stem >= 85 % recall, the track starts 4 frames after release on 4 of
  5 (baseline: 8-11) and ends within 0-4 frames of the pin hit (baseline: 5-26). Offline ablations (cached boxes,
  r_grow 1.5): drop far1x -> 81.6 mean, drop full320 -> 77.4, drop full1280 -> 80.4, native full frame instead of
  the far crop -> 86.5 (same boxes at the far end, 3x slower, more clutter mid-frame).
- Median-radius merge. The same ball gets r 38 (640) and r 20 (1280) on 185121 frame 317; keeping the tightest box
  made r jump 20 -> 38 at 318 and the engine's radius gate (1.15 r + 3) cut the chain (185121 50 %, 185645 19 %
  with min-r merge; 94.4 / 95.2 with the median).
- SAM prompts from the small-ball part of the chain only (r <= 30 px): with the whole chain the release ball
  (head still down) warps badly into the pin-hit frame and the lane was refused on 3 of 5 dev; 185331 then got a lane
  (lane_err 0.63).
- Scorer mutation check (work/mutation_185645_shift100.json): 185645 track +100 px x, board +5 -> recall 95.2 -> 4.8,
  board_err 3.5 -> 8.5. Read from the scorer's own output.

## What failed, with the number
- Far-end tiling at 2x/3x: far-band recall 16-20 % (vs 91 % native); the fine-tuned detector does not fire on a
  3x-upscaled 5 px ball. Also 17-50 s per video at those sizes. Dead.
- YOLO-World: 0 % far on all 5 dev stems. Dead.
- The board on 3 of 5 dev: 185121 7.0 (the SAM lane is the left neighbour lane: lane_err 59 boards; the baseline
  refused that stem outright), 185331 4.5 and 185645 3.5 with a correct lane (lane_err 0.4-0.6). At the deck one
  board is ~2.5 px on these frames (lane top width 95-105 px) and the track's median error is 6-7 px, so the
  last-5-frames board is 2-4 boards noisy. The engine's pin-rack refit (--pin-refit) moved 185331 to 8.0 (err 3.5)
  and was rejected on 185645 (alias margin 0.016). Not fixed; a board from the pin the ball hits, or reading the
  board a few frames earlier where the ball is bigger and projecting it, is the next lever.
- The engine's residual gate (8 px) refuses lanes on the glasses frames (8-13 px residuals): raised to 14 px here
  (185121's wrong lane came in at 8.1 px under the raised gate; 190115's right lane at 12.0).
- The chain still starts 4 frames after release on 4 of 5 dev (the truth's first 3-4 frames are the ball half out
  of the frame bottom with r 90-130 px; the 320 pass finds it on 80 % of the near third but the chain's first box
  is the first one it can link, 10 frames late on 185121 where the ball is invisible 299-306).

## Tuned on dev truth (the holdout has seen none of this)
r_grow 1.5 (1.15 engine default; 1.3 gave 87.7, 1.5 91.9), per-config conf floor 0.1 (0.05 -> 89.4, 0.15 -> 89.8),
the config set (320/640/1280/far1x), the median merge rule, LANE_MAX_R 30, the SAM candidate list and the 14 px
residual gate. The far-crop fraction (0.22-0.62 H, 0-0.80 W) was chosen from the dev truth's far-third y range.

## Rules learned
- The fine-tuned YOLO11n is scale-specific: it finds the ball only when its apparent size is near the training size.
  Resize the frame to the ball, not the ball to the detector.
- Pooling scales needs a radius rule: per-scale boxes of one ball differ by up to 2x in r.
- On a head camera, prompt the lane from where the head is up (the small-ball part of the path).

## Holdout runs (no truth read; cuts.json release/pin_hit in brackets are the cutter's visual labels, used only here for the window)
| stem | chain frames | lane | board | wall s |
|---|---|---|---|---|
| 191253 | 381-439 [377, 437] | sam_full+crop | 7.0 | 60.8 |
| 191820 (gutter ball) | 415-450 [411, 463] | refused | - | 80.1 |
| 191913 | 444-498 [441, 509] | sam_full+crop | 9.0 | 65.1 |
| 192142 | 419-488 [415, 480] | sam_full+crop | 9.0 | 70.6 |
| 192636 | 396-455 [391, 457] | sam_full+crop | 7.0 | 101.1 |
Every holdout chain starts 3-5 frames after the cutter's release frame (the baseline tracked 0 % of 191820 and
started 25 frames late there). The overlays were read for 191820 only.

## Notes on the artefacts
- 191900 (dev split) has no cut: the clip holds no throw (work/cuts/NOTES.md), so it was not run and has no track.
- `overlays/<stem>.jpg` draws the polyline in each frame's own pixel coordinates on the pin_hit-4 frame, as briefed
  (same as the baseline overlays). On a head camera with large motion (191820: the camera is on the ceiling at
  pin_hit-4) the line sweeps across the frame; that is the camera, not the track. `work/cmp_<stem>.jpg` (dev) shows
  the same against the truth, which has the same sweep.
