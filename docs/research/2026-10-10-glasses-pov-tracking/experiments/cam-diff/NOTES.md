# cam-diff: camera-compensated frame differencing for the glasses-POV cuts (2026-10-10)

Run: `/Users/toka/code/bowling-app/analysis-engine/.venv/bin/python run.py <stem> [--no-far-upscale] [--thr N] [--no-sam]`
(reads `L/work/cuts/cuts.json`, writes `tracks/<stem>.json` in SOURCE frame numbers and `overlays/<stem>.jpg`).
`run_dev.sh` scores the five dev stems with `L/score_tracks.py` (logs + score JSON in `work/scores_<TAG>/`),
`run_holdout.sh` makes tracks for the five holdout stems (no truth read, no scoring). `results.json` holds the dev table.

## What was built
- `camdiff.py`: ORB (3000 features, half-size grey) + RANSAC homography per consecutive pair (no ball mask: the
  ball is < 1 % of the frame except at release, where RANSAC drops it as outliers). Residual at t =
  min(|I_t - warp(I_t-1)|, |I_t - warp(I_t+1)|) on 3x3-blurred grey, so the ghost at the previous ball position
  cancels. 2.5 s per cut for all ~90 homographies; inliers 600-2100 mid-roll, 0-90 for the 5-10 frames around
  release where the head swings.
- `tracker.py`: blobs of residual > 22 (open 3, close 5, area 12-40000, aspect < 3), the far third of the frame
  upscaled 2x before thresholding (the brief's lever; coordinates mapped back). Each blob gets a purple fraction
  (HSV hue 112-170, S >= 30 inside its disc) and is **re-measured on the purple component** around it (the residual
  of a uniformly dark ball is only its rim and highlights, so the residual radius under-reads 3-20x; window grows
  while the component touches its border). Blobs resolving to the same purple component are merged.
  Link: greedy tracklets with a constant-velocity prediction carried through the homography (position and
  velocity both warped), gate max(2.5 r, 25 px), radius may shrink but not grow (1.15 r + 3, yolo_chain's gate).
  Throw = the tracklet maximising span x purple x residual x shrink with a non-growing fitted radius. Then an
  extension both ways from the seed: nearest candidate at the compensated prediction, else a **guided colour
  search** (purple pixels, AND residual > 10 where the motion is known) within the gate; backward the radius may
  grow (1.4 r + 6); 6 misses end it (2 where there is no motion model); where the residual is absent a guided blob
  must be a filled disc (aspect <= 1.6, fill >= 0.45: the purple masking panels are not). Gaps <= 6 interpolated.
- `run.py`: the engine's SAM lane pass (`scripts.sam_lane_pass.run_sam_lane_pass`, `lane_calibration.calibrate_lane`)
  prompted by this track as the segment. Changes for the POV: the segment starts where ORB has >= 400 inliers for
  3 frames (+2) and ends at a pin-hit guess + 2 (guess = last tracked frame - 12: the track runs 0-16 frames past
  contact on dev because the ball stays visible among the pins); candidate reference frames back 4/8/12/16 and
  ahead 3 of the guess; `MAX_RESID_PX` 8 -> 15 (the wide-angle lens leaves 9-14 px straight-line residuals; 190115
  was refused at 8 on every candidate), `GOOD_RESID_PX` left at 5 (7 stopped at a neighbour lane on 185645,
  lane_err 66). Pin hit = first frame of the whole track above the calibration's pin row (+0.5 r); final board =
  engine `board_summary` over the frames up to it. Lane quad per cut frame from `calib.to_dict`; `fl_*` is the
  lowest calibrated lane row, never the foul line (`fl_is_foul_line: false`).
- Overlay: pin_hit-4 frame; orange = track in each frame's own coordinates (loops with the head motion, as the
  baseline overlays), **white = the same track chained through the homographies into the displayed frame** (the
  path on the lane; only the frames whose chain has no ORB failure), cyan = lane quad, text = final board.

## Dev table (final config: thr 22, far third 2x, SAM as above; baseline = results/baseline.json yolo_chain_sam)
| stem | recall % | median px | board_err | lane_err boards | window_err [rel, pin] | pass | wall s | baseline recall / board_err |
|---|---|---|---|---|---|---|---|---|
| 185121 (handheld, not glasses) | 83.3 | 7.3 | 7.0 | 59.2 | [14, 1] | no | 167.9 | 88.9 / - |
| 185331 | 93.3 | 1.6 | 0.5 | 0.40 | [1, 3] | strong | 35.0 | 56.7 / 0.5 |
| 185645 | 100.0 | 1.3 | 2.5 | 0.78 | [9, 0] | pass | 34.9 | 85.5 / 3.5 |
| 185454 | 100.0 | 1.1 | 0.5 | 2.15 | [1, 6] | strong | 66.7 | 59.6 / 2.5 |
| 190115 | 100.0 | 1.2 | 0.5 | 1.27 | [1, 4] | strong | 130.3 | 69.1 / 0.5 |
| **mean** | **95.3** | | 2.2 (1.0 without 185121) | | | **4/5** (3 strong) | 87 | 72.0, pass 1/5 |

Scorer mutation check on my 185454 track (`work/mutation_check.py`): as-is 100.0 / px 1.1 / board 0.5 / lane 2.15;
+100 px x (lane too, board +5): 15.4 / 99.6 / 5.5 / 43.0; empty: 0.0 / null / null / null. The 15 % that survive
the shift are the release frames whose truth r is 44-115 px (tolerance 2 r).

Overlays read: all five dev (track on the right lane, white path inside the quad and ending at the pins on
185331/185454/190115/185645; on 185121 the quad's deck sits left of the pins and the near edge leaves the frame)
and holdout 191820 (gutter ball: white path down the right gutter, board 1.0).

## What worked (numbers from `work/probe_raw.py`, `work/probe_track.py`, mean over truth points, no SAM)
- Raw residual blobs with purple >= 0.25 within tolerance of truth: 14/18, 49/60, 50/62, 43/52, 41/55 (78-85 %).
  The ball's residual is 50-190 (max in its window) against a frame 99.5th percentile of 13-50 mid/far roll;
  at the pins (r 4-10) it is 33-80, still above the pin-edge stripes, which the aspect test removes.
- Greedy tracklets alone: 13/18, 35/60, 38/62, 25/52, 31/55 (60 %): fragments. Seed + two-way extension +
  guided colour + interpolation: 91.9 %. + purple radius re-measurement and candidate merge: 95.5 % (185454 and
  190115 to 100 %: the big blurred ball in the first 5-10 frames after release, which the YOLO chain never links,
  is found backwards by the guided colour search with the grow gate). Far third 2x: 97.2 % of points
  (185645 95.2 -> 100, 185121 77.8 -> 83.3; the others unchanged).
- Threshold: 15 gives 96.0 % (185121 83.3, rest equal), 22 is the default, 30 collapses to 61.1 % (190115: the seed
  tracklet is a 9-point non-ball fragment, recall 0).
- Release = first tracked frame: within 1 frame of the visual release on 4 of 5 dev and all 5 holdout
  (cuts.json visual reads); 185645 starts 9 frames early (the ball in the hand is tracked backwards) and 185121 14
  late (below).

## What failed
- **185121** (the 09-19 handheld video, camera zoomed and swinging; `ball_invisible` 299-306, then the ball sits at
  the top of the frame against the purple masking panel at 307-313 with 0-36 ORB inliers): no motion model, the
  guided search either walks into the panel (first version: recall 77.8 with 10 guided points in the panel) or,
  with the disc test, stops (recall 83.3, frames 298-313 missed). The SAM lane it accepts is the right lane but
  its deck is left of the pins: lane_err 31-59 boards, board_err 5-7 on every run; the baseline refused this
  video altogether (residual 9 px).
- **Pin hit as a signal of its own**: a white-strip-above-the-ball rule (S < 70, V > 160 in the strip 1-3 r above
  the ball, 2 consecutive frames, r <= 18) fired ~25 frames early on every glasses stem (351 vs 377 on 185454) on
  the pins' reflections in the oiled lane; the residual burst of flying pins (residual > 30 around the ball) came
  8-15 frames after the truth pin hit (384 vs 377, 373 vs 358). Both dropped; the SAM pin row is used instead,
  which lands -8..+13 frames of the truth on dev (0-6 in the final run) and, by the visual reads in cuts.json,
  10-21 frames EARLY on four holdout stems (427 vs 437, 488 vs 509, 460 vs 480, 443 vs 457): the mask top is short
  of the pin bases where the far end is compressed, so the board is read 10-20 frames before contact there.
- **SAM candidate frames**: with the engine defaults the glasses stems lost the lane on 3 of 5 (edge-fit residual
  10-14 px, "mask top N px short of the path's far end" when the segment included release frames whose alignment
  blows up (-16000 px), falling pins when the guess was late). Fixed by the segment start/end rules above, not by
  a better lane model; 185645 still calibrates on frame 303 (4 frames after contact) and gets 2.5 boards (truth
  uncertainty 2.0; the no-upscale run calibrated earlier and got 1.5).
- **Wall time**: 35-168 s per video, target 120. The tracker is 5-9 s; the SAM pass is the rest and scales with
  the number of candidate frames tried (each = one SAM full pass + a static-check partner pass): 185121 168 s,
  190115 130 s when the first candidates fail the static check.
- The track continues 0-16 frames past the pins (the ball among the pins and into the pit): harmless for recall,
  it is why the pin-hit guess is `end - 12`.

## What was tuned on the dev truth
thr 22 (from the residual-at-truth probe), the purple hue/saturation window (HSV medians at truth centres: H
121-153, S 37-163), min purple 0.25, gates (2.5 r / 25 px, 6 misses, grow 1.4 r + 6), the disc test, the
`end - 12` pin guess (dev overshoot 0-16), the ORB >= 400 segment start (from the 185331 SAM failure), MAX_RESID 15
(190115 refused at 8), GOOD_RESID 5 (7 broke 185645), far-third 2x kept as default on dev recall (95.3 vs 93.3)
although it moved 185645's board from 1.5 to 2.5. The holdout was never scored and its truth never read.

## Runtime
Final dev run: 167.9 / 35.0 / 34.9 / 66.7 / 130.3 s (mean 87 s; tracker 5-9 s of it). Holdout: see `work/holdout_run.log`.
Files: `camdiff.py`, `tracker.py`, `run.py`, `run_dev.sh`, `run_holdout.sh`, `results.json`, `tracks/`, `overlays/`,
`work/` (probes, score JSONs per run, `tracks_main`/`overlays_main` = the no-upscale run, mutation check).

## Holdout (tracks + overlays only, final config; truth never read)
| stem | release (cuts.json visual) | pin_hit (visual) | final board | points | wall s |
|---|---|---|---|---|---|
| 191253 | 377 (377) | 421 (437) | 8.0 | 56 | 29.8 |
| 191820 gutter ball | 412 (411) | 463 (463) | 1.0 | 53 | 25.2 |
| 191913 | 441 (441) | 488 (509) | 8.0 | 54 | 29.1 |
| 192142 | 415 (415) | 466 (480) | 6.0 | 57 | 33.1 |
| 192636 | 391 (391) | 443 (457) | 7.0 | 62 | 29.4 |
Every holdout stem got a lane on its first SAM candidate (25-33 s). The no-upscale run (`work/holdout_logs_main/`)
gave boards 7 / 1 / 8 / 7 / 7: the far-third upscale moved 191253 by one board and 192142 by one.

## Caveat on "far third 2x"
What is upscaled is the **residual image** (top third, 2x cubic) before thresholding and blob extraction, so the
gain is in blob connectivity and the morphology at small scale. The brief's variant, upscaling the frames before
the warp and the differencing (finer alignment at the far end), was not tried; `camdiff.residual` differences at
native resolution.
