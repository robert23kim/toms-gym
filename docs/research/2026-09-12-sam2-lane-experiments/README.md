# Can SAM 2 find the bowling lane? Prompting experiments (2026-09-12)

Status: complete. Review video: `review.mp4` (1920x1080, 4.7 min, 23 MB). Scripts, result JSON
and overlays are in this folder; frames, model weights and per-frame masks were left in
the session scratchpad (regenerate with the commands at the end).

## Why

The Feb-2026 engine attempt (`src/bowling/lane_tracking/sam2_segmentor.py`, branch
`_annotations`, never shipped) wired SAM 2 behind `--sam2-lane` and got 0 % ball
detection: its prompts were a fixed box over the middle of the frame and three points down
the frame's centre line, which land on the pin deck, the bowler or the neighbouring lane.
The 2026-09-12 new-stack report showed that prompting with points along the ball's path
instead gives 0.2 to 2.3 boards of error. This loop asks the follow-up questions: which
prompt, which frame, how many frames, and whether SAM 2's video mode can track the lane
through a throw. The ball is not tracked here; annotated ball positions stand in for a
detector, exactly as in the earlier report.

## Setup

- Model: SAM 2.1 base (`sam2.1_b.pt`) through ultralytics 8.4.14, CPU, ~1.5 s per frame
  at 1024 px. Person boxes for the negative-prompt methods come from YOLO11n.
- Videos: the engine's three annotated throws.

  | video | res | camera | ball frames | lane width at pins |
  |---|---|---|---|---|
  | sample_input | 1080x1920 | handheld, drifts 24 px | 86 | 58 px (1.5 px/board) |
  | Chardie (20260112_121117) | 720x1280 | handheld, drifts 36 px | 66 | 39 px (1.0 px/board) |
  | tom_old | 688x1264 | tripod, 3 px | 148 | 67 px (1.7 px/board) |

- Metric: the mask's per-row left/right extremes are line-fitted (robust polyfit), the
  lines are evaluated at the annotated top/bottom y to give four corners, and the 4-corner
  board homography is applied to every annotated ball position up to the pin-hit marker.
  Board MAE is the mean absolute difference against the homography from the annotated
  corners. This isolates "is the edge line right", which is all the board number depends on.
  Two details that the earlier report did not have and that changed results here:
  - **Only on-lane ball frames count.** Chardie's ball is annotated 36 frames past pin
    contact, into the pit, 190 px above the lane. Those points are not boards, and prompts
    spaced along a path that includes them collapse onto the pit. `pin_hit_frame` (or
    `frame_markers.pin_hit`) cuts the path: 77 / 65 / 148 on-lane positions.
  - **The mask component is chosen by the prompts, not by area.** A leaked mask often
    spans the neighbouring lane as a second connected component, and on Chardie that one is
    larger. Fitting the largest component put the "lane" one lane to the right (66 boards,
    for every frame of a video-mode run). The component that contains the most positive
    prompt points is the one the ball rolled on.

### Truth follows the camera

The first pass scored every frame against the single static `lane_edges` in the
annotation and produced nonsense: a clean mask on the last frame of sample_input scored
2.3 boards while the same prompt on the pre-release frame scored 0.3. The reason is that
sample_input and Chardie are handheld. sample_input carries hand-annotated per-frame
corners (`frame_lane_edges`) and they drift 21 px from the static set by the end of the
throw; ORB + RANSAC similarity fits confirm 24 px on sample_input, 36 px on Chardie and
3 px on tom_old. At the pin end a board is 1 to 2 px, so a static lane is off by 10+
boards on a handheld phone by the time the ball reaches the pins.

`camera_motion.py` therefore fits a per-frame similarity transform from the pre-release
frame and the truth is made per frame: sample_input uses its own per-frame annotation;
Chardie's static corners are pinned to the last frame (SAM on that frame agrees to <1
board and the pre-release frame is 30 px away, so the annotator clicked near the end) and
warped to other frames; tom_old barely moves. Validation on sample_input, where both
exist: warping the annotated corners from the reference frame to every other frame lands
within 3.5 px of the hand annotation on average (max 11 px, at the block boundaries of a
per-frame annotation that is itself piecewise constant). Ball positions from other frames
are moved through the same transforms before scoring, so every number below is "the lane
on this frame vs the annotated lane on this frame".

Two consequences for the design, both visible in the results: any method that combines
frames on a handheld video is capped by the stabilisation error (~3 px = ~2 boards at the
pins), and production needs a lane per frame, not one lane per video.

## Results

Board MAE per method (lower is better; "fail" = no usable mask). Single-frame and
multi-frame methods report the lane on the last ball frame. Tracking methods also report
the mean over every scored frame of the throw, each against its own lane.

| method | description | sample_input | Chardie | tom_old | per-frame mean (s / C / t) |
|---|---|---|---|---|---|
| `generic_box` | Feb-2026 engine prompt: fixed box over the middle of the frame, no scene knowledge | 6.27 | fail | fail |  |
| `center3` | Feb-2026 fallback prompt: three points down the frame centre line | 13.00 | 6.89 | 7.77 |  |
| `track_pre` | 5 positive points along the ball path, pre frame | 1.42 | 1.13 | 1.12 |  |
| `track_mid` | 5 positive points along the ball path, mid frame | 6.06 | 31.11 | 7.20 |  |
| `track_last` | 5 positive points along the ball path, last frame | 0.09 | 1.07 | 0.93 |  |
| `track1_last` | A single positive point on the ball path (the 2026-09-12 report's prompt), last frame | 0.12 | 0.39 | 16.54 |  |
| `track9_last` | 9 positive points along the ball path, last frame | 4.85 | 3.90 | 1.31 |  |
| `even_last` | 5 points spaced evenly along the path's image length (15-85%), last frame | 0.17 | 0.50 | 1.54 |  |
| `even3_last` | 3 evenly spaced path points, last frame | 0.24 | 0.39 | 1.35 |  |
| `even_neg_last` | Evenly spaced path points plus negatives half a lane-width outside the first mask, last frame | 0.15 | 1.67 | 0.80 |  |
| `even_person_last` | Evenly spaced path points plus negatives on detected people, last frame | 0.29 | 0.38 | 1.54 |  |
| `track_box_last` | Path points plus a loose box around the path (x +-25% of frame width), last frame | 4.02 | 3.84 | 1.25 |  |
| `lane_neg_last` | Two passes: path points, then negatives half a lane-width outside the first mask, last frame | 2.93 | 3.78 | 1.20 |  |
| `person_neg_mid` | Path points plus negative points on every YOLO-detected person, mid frame | 6.15 | fail | 7.08 |  |
| `person_neg_last` | Path points plus negative points on every YOLO-detected person, last frame | 0.90 | 2.47 | 0.93 |  |
| `multimask_sam_last` | 3 candidate masks from the path points; keep the one SAM scores highest | 0.38 | 1.07 | 1.07 |  |
| `multimask_geo_last` | 3 candidate masks; keep the straightest full-height one containing the path | 0.38 | 1.07 | 1.07 |  |
| `median3_span` | Path points on 3 frames spread pre..last, median of the (camera-warped) edge lines | 2.10 | 1.51 | 0.93 |  |
| `median5_span` | Path points on 5 frames spread pre..last, median of the edge lines | 3.33 | 0.72 | 0.89 |  |
| `median9_span` | Path points on 9 frames spread pre..last, median of the edge lines | 3.28 | 0.77 | 0.92 |  |
| `median5_late` | Path points on 5 frames in the last 30% of the throw, median of edge lines | 1.79 | 0.43 | 2.00 |  |
| `outer5_span` | 5 frames pre..last, outermost left/right edge across frames (occlusion only narrows) | 1.08 | 0.40 | 1.49 |  |
| `outer9_span` | 9 frames pre..last, outermost edges | 1.10 | 32.60 | 1.86 |  |
| `vote5_span` | 5 frames pre..last, pixel-wise majority vote of warped masks, then one edge fit | 2.50 | 0.41 | 0.85 |  |
| `vote9_span` | 9 frames pre..last, pixel-wise majority vote of warped masks, then one edge fit | 3.06 | 0.43 | 1.68 |  |
| `vote9_person_span` | vote9_span with negative points on detected people in every frame | 2.89 | 0.68 | 1.40 |  |
| `vote5_even_span` | vote5_span with evenly spaced path points | 2.48 | 0.40 | 0.91 |  |
| `median5_span_snap` | median5_span, then snap each edge line to the strongest gradient within +-6 px | 1.97 | 0.76 | 1.36 |  |
| `vote9_span_snap` | vote9_span, then gradient snap | 1.60 | 0.75 | 1.83 |  |
| `perframe_track` | SAM on every 2nd ball frame with path points; each frame scored against its own lane | 0.08 | 0.48 | 2.08 | 2.08 / 12.42 / 5.91 |
| `perframe_person` | perframe_track with negative points on detected people | 2.84 | 0.51 | 2.08 | 3.11 / 95.99 / 5.29 |
| `video_span` | SAM 2 video mode: prompt once on the pre-release frame, propagate forward to the last frame; per-frame scoring | 0.29 | 0.37 | 1.21 | 2.00 / 19.45 / 3.55 |
| `video_rev` | SAM 2 video mode run backwards: evenly spaced prompts on the clean last frame, propagate back to release | 0.21 | 0.38 | 1.53 | 1.85 / 16.39 / 3.73 |

Weights (last frame, path points):

| weights | s/frame CPU | sample_input | Chardie | tom_old |
|---|---|---|---|---|
| sam2.1_t (tiny) | 0.7 | 0.68 / 0.52 | 1.12 / 0.52 | 0.61 / 0.79 |
| sam2.1_b (base) | 1.6 | 0.09 / 0.17 | 1.07 / 0.50 | 0.93 / 1.54 |
| sam2.1_l (large) | 3.8 | 0.32 / 0.50 | 9.20 / 0.32 | 1.21 / 1.17 |

(pairs are `track_last` / `even_last`)

## What the results say

1. **The Feb-2026 prompts are the whole reason that attempt failed.** The fixed box
   segments the ceiling or nothing (`generic_box`: 6.3 boards, then two fails); the three
   centre-line points give 7 to 13 boards. The identical model with points on the ball's
   path gives about a board or less. Nothing about SAM 2 needed changing.

2. **Which frame matters more than which prompt.** The same 5 path points score
   0.09 / 1.07 / 0.93 on the last ball frame, 1.42 / 1.13 / 1.12 on the pre-release frame,
   and 6.1 / 31 / 7.2 mid-throw. Mid-throw the bowler is standing in or in front of the lane
   on all three videos and the mask edge runs along their leg. The per-frame runs make this
   explicit: the first half of every throw averages 1.8 / 25 / 8.4 boards, the second half
   2.3 / 0.7 / 3.5. Frames after the bowler has cleared the lane are the ones to use, and no
   prompt trick recovers a frame where the lane is physically hidden.

3. **Spread prompt points by image distance, not time, and keep them off both ends.**
   Time-even picks bunch at the far end because the ball moves slowly in image space far
   from the camera; a cluster of points by the pins makes the mask leak into the
   neighbouring lane (Chardie: 1 point 0.39, 5 points 1.07, 9 points 3.9; sample_input with
   9 points 4.85). Points spaced evenly along the path's on-lane image length between 15 %
   and 85 % give 0.17 / 0.50 / 1.54 with five points and 0.24 / 0.39 / 1.35 with three.
   Three is enough.

4. **Boxes, negatives and candidate selection do not help.** A loose box around the path
   pulls the mask sideways (4.0 / 3.8 / 1.25). Negatives on YOLO-detected people change
   nothing on a clean frame and cannot rescue an occluded one (`person_neg_mid` 6.2 / fail /
   7.1). Negatives half a lane-width outside the first mask help on the tripod video (0.80)
   and hurt on the handheld ones (2.9 / 3.8 with time-even points). SAM's own three
   candidates: the top-scored one is what `predict()` already returns, and a geometric
   picker chose the same mask every time.

5. **Merging frames is capped by camera stabilisation on handheld video.** Medians and
   pixel votes over 5 to 9 frames warped into the last frame score 2.1 to 3.3 boards on
   sample_input, worse than any single clean frame, because the similarity fit is good to
   about 3 px and a board is 1.5 px at the pins. On the tripod (tom_old) and on Chardie,
   where the late frames dominate, they are fine (0.85 to 0.93 and 0.40 to 0.77). Taking the
   outermost edge across 9 frames is unstable (Chardie 32.6): one leaked mask wins the max.
   Gradient snapping within 6 px recovers some of it (median-of-5 on sample_input 3.33 to
   1.97, vote-of-9 3.06 to 1.60) at a cost on the motion-blurred tom_old last frame.

6. **SAM 2 video mode follows a handheld camera with no explicit stabilisation.** One
   prompt, propagated over the throw, scores 2.0 / 19 / 3.6 boards mean per frame forward
   and 1.85 / 16 / 3.7 backwards from the last frame. The Chardie mean is the occluded first
   half (31 to 38 boards while the bowler stands in the lane); its second half is 1.4, and
   sample_input's median is about 1 board over 77 frames. Direction barely matters once the
   lane component is chosen by the prompts; before that fix, video mode on Chardie read the
   neighbouring lane for the whole throw.

7. **Independent per-frame SAM is no better than propagation and costs 2x.** Every-2nd-
   frame prompting scores 2.1 / 12 / 5.9 (path points) and 2.0 / 6.1 / 3.6 (even points);
   per-frame person negatives are actively harmful (96 boards mean on Chardie from a few
   catastrophic frames).

8. **Model size does not matter; tiny is enough.** sam2.1_t scores 0.68 / 1.12 / 0.61
   (path points) and 0.52 / 0.52 / 0.79 (even points) at 0.7 s per frame on CPU; large is no
   better and worse on Chardie with path points (9.2).

9. **The floor is the pixel, not the model.** Every good result still shows 1 to 2 boards at
   the pin end where a board is 1 to 1.7 px, and the mask bleeds a few px into the bright
   pin deck at the very top. The earlier report's advice stands: quote the board at the
   arrows, report the pin-end board as a range, and ask for a higher camera.

## Recommendation

For the engine, in order:

1. **Prompt = the ball path, evenly spaced by image length, 15 % to 85 %.** Three to five
   positive points. No box, no negatives.
2. **Frame = after the bowler has cleared the lane.** Use the ball track to pick the last
   frames before pin contact, run SAM on two or three of them, keep the one with the lowest
   line-fit residual, or median them without warping when the camera is still (check with a
   cheap phase-correlate on the top of the frame).
3. **Per-frame lanes on handheld video via SAM 2 video mode**, prompted once on a clean
   frame and propagated (direction does not matter), with the lane component chosen by the
   prompts. For frames where the bowler hides the lane, carry the nearest clean frame's lane
   through the camera-motion model instead of trusting the mask.
4. **Snap the final lines to the gradient within 6 px**, only when a gradient is present.
5. **Ship sam2.1_t.** Same accuracy, 0.7 s per frame on CPU; the base model's extra
   second buys nothing here.
6. Keep the Feb-2026 skeleton (`sam2_segmentor.py`: pipeline hook, `LaneEdges` output,
   confidence gating, mask margin, tests) and replace only `_sam2_mask_for_frame`'s prompt
   block and the row-extreme edge fit with the versions in `lane_sam.py`. ultralytics and the
   weights still need adding to `requirements-service.txt` and the image.

Not done here: a ball detector (annotations stood in), ground-truth board numbers (the
metric is relative to hand-clicked corners, as before), and any video where the lane is not
the one nearest the camera's own approach.

## Reproducing

```
V=~/code/bowling-app/analysis-engine/.venv/bin/python   # has torch, ultralytics, opencv
cd docs/research/2026-09-12-sam2-lane-experiments
$V -c "import gt; [gt.extract_frames(s) for s in gt.VIDEOS]"   # frames -> scratchpad (SAM_FRAMES)
$V camera_motion.py                                             # results/camera_<stem>.json
$V run_methods.py --list
$V run_methods.py                                               # all methods, ~25 min CPU
$V run_methods.py --methods track_last --weights sam2.1_t.pt --tag _tiny
$V make_review_video.py                                         # review.mp4 + results/summary.md
```

Weights download into `SAM_WEIGHTS` (scratchpad by default) on first use.
