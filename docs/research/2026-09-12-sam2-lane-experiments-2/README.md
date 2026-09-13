# SAM 2 lane detection, loop 2: resolution, anchors, tracking (2026-09-12)

Status: complete. Review video: `review.mp4`. Scripts, result JSON (`results/`), overlays and
diagnostics (`overlays/`) are in this folder; frames, weights and per-frame masks live in the
session scratchpad (regenerate with the commands at the end). Loop 1 is
`../2026-09-12-sam2-lane-experiments/` and everything here is measured with its metric, its
per-frame truth and its ball-path prompts (`common.py` imports its `gt.py` / `lane_sam.py`).

## The questions

Loop 1 ended at 0.24 / 0.39 / 1.35 boards (`even3_last`, sample_input / Chardie / tom_old) with the
verdict "the floor is the pixel, not the model". This loop asked two things:

1. Can SAM 2 be pushed below that with the same weights: sub-pixel edges, zoomed crops, tiles,
   a 2048 px encoder, prompt ensembles, extrapolation from the wide end, a vanishing point shared
   with the neighbouring lanes?
2. Is there a better **anchor** than the ball path, the way the lifting analysis in the same engine
   anchors on named pose landmarks (wrist, ankle, hip) rather than on pixels: the gutters as
   objects, the pins as a physical ruler, the bowler's release point?

Plus the loop-1 recommendation that was never measured: occlusion-gated tracking through the throw.

## Setup

Same three videos and metric as loop 1 (board MAE of every annotated ball position through the
4-corner homography from the fitted edge lines vs the homography from the annotated corners; truth
per frame). Two additions:

- **Frame kinds.** `last` is loop 1's last annotated ball frame, which is *after* pin contact on
  sample_input and Chardie (pins flying, ball in the pit) and motion-blurred on tom_old. `prehit` =
  pin-hit marker − 2 and `prehit-6` = marker − 6: pins standing, bowler off the lane, sharp, ball on
  the lane near the far end.
- **Encode once, decode many** (`sam2x.py`). The image encoder is ~95 % of a SAM call on CPU; the
  prompt encoder and mask decoder are milliseconds. `SamImage` caches the encoding and returns
  float logits at source resolution for any number of prompt sets or objects. That makes prompt
  ensembles, multi-object prompts and candidate masks essentially free, and it exposes the decoder's
  grid: 256 cells over the 1024 px letterbox = **7.5 source px per cell on a 1080x1920 frame**, where
  a board is 1-2 px. Crops of the pin end letterboxed to 1024 px get 2.5-4.4x more cells per board.

### The prompt bug

`track_points_even` (loop 1) drops any prompt within three ball radii of the ball on the scored
frame. At `prehit` the ball sits at the far end, so the top prompt vanished and only two of three
prompts survived; the mask then stopped short of the pin deck and the line fit extrapolated through
the narrowest part of the lane. tom_old's `last` frame (= the pin-hit frame) had the same bug in
loop 1. `common.even_points_keep` slides the point down the path until it clears the ball instead:

| even3, sam2.1_b | last (s / C / t) | prehit (s / C / t) |
|---|---|---|
| loop-1 rule (dropped) | 0.24 / 0.39 / 1.35 | 0.55 / 0.72 / 2.34 |
| kept prompts (`_k`) | 0.24 / 0.39 / **1.17** | **0.31** / 0.69 / 2.27 |

Every method below uses kept prompts (`_k`).

## Results

Board MAE, lower is better, sam2.1_b unless stated. Loop-1 numbers to beat: `even3_last`
0.24 / 0.39 / 1.35; best per video by any loop-1 method 0.08 / 0.32 / 0.61.

**Resolution and extrapolation (this loop's own methods)**

| method | last (s / C / t) | prehit (s / C / t) | prehit-6 (s / C / t) |
|---|---|---|---|
| `even3` binary mask, first/last pixel per row (loop-1 fit) | 0.24 / 0.39 / 1.17 | 0.31 / 0.69 / 2.27 | 0.14 / 0.49 / 2.19 |
| `soft` sub-pixel edges from the logit zero crossings | 0.22 / 0.47 / 1.23 | 0.24 / 0.88 / 2.29 | 0.11 / 0.55 / 2.21 |
| `ens` 10 prompt variants on one encoding, mean logit | 0.20 / 0.52 / 1.31 | 0.21 / 0.89 / 2.30 | **0.10** / 0.57 / 2.22 |
| `zoom` second pass on a crop of the top 55 % of the lane | 0.68 / 0.33 / 0.66 | 0.87 / 0.39 / 1.88 | 0.67 / 0.39 / 1.76 |
| `zoom_lo` crop prompts kept away from the pin deck | 0.70 / **0.32** / **0.49** | 0.89 / 0.37 / 1.86 | 0.65 / 0.49 / 1.85 |
| `zoom_trim` zoom_lo, top 15 % of rows left out of the fit | 0.65 / 0.34 / 0.49 | 0.91 / 0.38 / 1.86 | 1.03 / 0.45 / 1.77 |
| `tiles` three overlapping crops | 0.84 / 0.42 / 0.98 | 1.13 / 0.45 / 1.92 | · |
| `ens_zoom` ensemble on the full frame and on the crop | 0.67 / 0.34 / 0.68 | 1.03 / 0.43 / 1.89 | · |
| `hires` encoder at imgsz 2048 | 0.36 / 0.45 / 2.72 | 0.51 / 0.96 / 1.50 | 0.45 / 0.90 / 1.36 |
| `snap2` polarity-aware sub-pixel gradient snap, ±6 px | 0.40 / 0.76 / 1.51 | 0.55 / 0.83 / 1.78 | · |
| `trim` fit on the lower 70 % of rows, extrapolated | 0.43 / 0.87 / 1.44 | 0.41 / 1.14 / 2.49 | · |
| `vp` edges through a vanishing point shared with the neighbour lane | 0.17 / 0.61 / 1.23 | 0.26 / 0.99 / 2.30 | · |

**sam2.1_t (tiny, 0.7 s per encode)**

| method | last (s / C / t) | prehit (s / C / t) | prehit-6 (s / C / t) |
|---|---|---|---|
| `even3` | 0.72 / 0.50 / 0.74 | 1.01 / 0.52 / 2.03 | 0.76 / 0.79 / 1.92 |
| `soft` | 0.70 / 0.45 / 0.80 | 0.94 / 0.45 / 2.04 | 0.72 / 0.71 / 1.95 |
| `ens` | 0.63 / 0.47 / 0.76 | 0.89 / 0.55 / 2.05 | 0.68 / 0.76 / 1.97 |
| `zoom` | 0.46 / 0.72 / **0.45** | 0.70 / 0.72 / 1.84 | 0.38 / 0.54 / 1.62 |
| `zoom_lo` | 0.46 / 0.48 / 0.57 | 0.75 / 0.60 / 1.84 | 0.43 / 0.49 / 1.60 |

**Best per video, any method, either loop**

| | sample_input | Chardie | tom_old |
|---|---|---|---|
| loop 1 | 0.08 (`perframe_track`, last) | 0.32 (`even_last_large`) | 0.61 (`track_last_tiny`) |
| loop 2 | 0.10 (`ens`, prehit-6) | 0.32 (`zoom_lo`, last) | 0.45 (`zoom` tiny, last) / 0.49 (`zoom_lo`, last) |

**Anchors (agent `anchors-1`, `run_anchors.py`; sam2.1_b, kept prompts)**

| method | prehit (s / C / t) | last (s / C / t) |
|---|---|---|
| `softk` soft edges + kept prompts (the agent's baseline) | 0.24 / 0.88 / 2.29 | 0.22 / 0.47 / 1.23 |
| `gutters` lane + both gutters as three objects in one decode; edge = lane-vs-gutter logit crossing | 0.20 / 0.76 / 2.30 | 0.18 / 0.53 / 1.35 |
| `pins` pin cluster sets both top corners, SAM's lower rows set the slopes | 0.76 / 0.58 / 0.86 | 2.82 / 0.48 / 0.89 |
| `pins_m` pin cluster sets the far-end **centre**, SAM keeps its width | 0.21 / 0.88 / 0.60 | 2.43* / 0.82 / 0.85 |
| `pins_c` pin centre, SAM width, pair pivoted about the foul line | 0.40 / 0.88 / 1.92 | 2.70 / 1.06 / 1.82 |
| `pins_zoom` pins + a SAM pass on the top-55 % crop | 0.76 / 0.58 / 0.85 | 2.79 / 0.49 / 0.89 |
| `landmarks` prompts from the release point to the pin centre, **no ball path** | 0.38 / 0.87 / 2.37 | 0.37 / 0.41 / 1.44 |
| `landmarks_pin` landmarks + the pin anchor on the far end | 0.48 / 0.51 / 1.05 | 2.28* / 0.48 / 1.08 |
| `pins_m` tiny / `landmarks_pin` tiny / `gutters` tiny | 0.45 / 0.90 / 0.54 · 0.79 / 0.62 / 0.76 · 0.90 / 0.42 / 2.22 | 1.94 / 0.68 / 0.93 · 1.82 / 0.60 / 0.88 · 0.75 / 0.44 / 1.14 |

\* every pin method collapses on sample_input's `last` frame: the pins are measured on the
pre-hit frame and warped 11 frames through the camera model, which moves the pin centre 8 px
(five boards) on that handheld video. Pins must be measured on the frame they are used on.

**The pins as a ruler (pre-hit frame, `centre_check2.py`).** The standing cluster's centre is the
lane centre at the pin deck, independent of any hand-clicked corner. It is measured at the row where
the pin bases sit (annotated top row + dy), so every centre line below is evaluated *at that row*. On
tom_old the two edges have very different slopes (−1.13 and −0.30 px per row) and the lane centre
slides 4 px over the 5.7 rows between the pin bases and the annotated top corners, so the agent's
JSON field `pin_centre_err_px` (+6.4 on tom_old, two different rows) must not be used; an earlier
draft of this README did, and read the tom_old annotation as four boards off. Offsets in px:

| at the pin-base row | sample_input | Chardie | tom_old |
|---|---|---|---|
| pin cluster centre − annotated centre | −0.9 | +2.3 | +1.7 |
| pin-derived width / annotated width at that row | 0.85 | 0.92 | 1.07 |
| `even3` / `soft` / `ens` / `gutters` vs pins | +1.1 | +0.6 … +0.9 | **+5.2** |
| `zoom_lo` / `tiles` vs pins | −1.0 / −1.4 | −0.6 / −0.4 | +3.9 / +4.2 |
| `hires` vs pins | −0.6 | +0.1 | +2.8 |
| `landmarks` vs pins | +0.4 | +0.9 | +5.5 |
| `pins_m` / `pins` vs pins (circular: they use the pin centre) | 0.0 | +0.1 / 0.0 | +0.1 / 0.0 |

**Re-scored against a pin-centred truth** (`rescore_pins.py`: the annotated top corners shifted by
the same-row pin-centre offset above, −0.9 / +2.2 / +1.7 px, width unchanged; pre-hit frames;
annotated → pin-centred; the `pins*` rows are circular because they use the pin centre themselves):

| method | sample_input | Chardie | tom_old |
|---|---|---|---|
| `even3` | 0.31 → 0.16 | 0.68 → 0.82 | 2.26 → 1.69 |
| `soft` | 0.23 → 0.15 | 0.88 → 0.56 | 2.29 → 1.72 |
| `ens` | 0.21 → 0.16 | 0.91 → 0.54 | 2.31 → 1.74 |
| `gutters` | 0.19 → 0.18 | 0.75 → 0.71 | 2.30 → 1.73 |
| `zoom_lo` | 0.89 → 0.60 | 0.37 → 1.26 | 1.87 → 1.29 |
| `hires` | 0.51 → 0.22 | 0.95 → 0.51 | 1.49 → 0.92 |
| `landmarks` (no ball path) | 0.39 → 0.14 | 0.88 → 0.61 | 2.39 → 1.81 |
| `landmarks_pin` | 0.47 → 0.26 | 0.52 → 0.99 | 1.05 → 0.47 |
| `pins_m` (circular) | 0.20 → 0.13 | 0.90 → 0.54 | 0.62 → 0.09 |
| `even3`, prehit-6 | 0.13 → 0.28 | 0.48 → 1.22 | 2.21 → 1.64 |

**Far-end width, predicted / annotated** (foul-line width in brackets):

| method, prehit | sample_input | Chardie | tom_old |
|---|---|---|---|
| `even3` | 0.905 (1.023) | 0.879 (0.993) | 0.945 (0.984) |
| `soft` | 0.920 (1.027) | 0.907 (0.999) | 0.960 (0.986) |
| `zoom_lo` | 0.933 (1.025) | 0.928 (0.995) | 0.948 (0.987) |
| `gutters` | 0.928 (1.032) | 0.894 (0.992) | 0.990 (0.994) |


**Tracking and frame choice (agent `track-1`, `run_track.py`)**

`video_carry` re-scores loop 1's SAM 2 video-mode masks (`video_rev`: prompted on the clean last
frame and propagated backwards; `video_carry_span`: `video_span`, forwards from release) with a
truth-free gate, replacing a gated frame's lane with the nearest passing frame's lines warped through
the camera model. Per frame, each scored against its own lane (mean / median / max / % of frames
within 2 boards):

| | sample_input | Chardie | tom_old |
|---|---|---|---|
| loop 1 `video_rev` | 1.85 / 0.98 / 5.71 / 66 % | 16.39 / 4.02 / 75.4 / 38 % | 3.73 / 2.35 / 7.71 / 13 % |
| `video_carry` (gated + carried) | **0.98** / 0.84 / 4.65 / 91 % | **0.41** / 0.31 / 0.86 / 100 % | **1.94** / 1.85 / 2.48 / 53 % |
| loop 1 `video_span` | 2.00 / 1.06 / 6.13 / 66 % | 19.45 / 3.86 / 67.6 / 38 % | 3.55 / 2.23 / 7.58 / 14 % |
| `video_carry_span` | 1.33 / 1.03 / 4.97 / 80 % | **0.34** / 0.27 / 0.71 / 100 % | 2.00 / 2.05 / 2.40 / 28 % |
| oracle gate (flag exactly the bad frames) on `video_rev` | 0.80 / 0.81 / 3.25 / 97 % | 0.41 / 0.31 / 0.86 / 100 % | 1.92 / 1.85 / 2.48 / 53 % |
| `video_keep` (tiny; video mode re-prompted with kept prompts on the pre-hit frame, propagated back, gated) | 1.04 / 0.93 / 4.62 / 93 % | 2.29 / 2.48 / 2.48 / 29 % | 1.75 / 1.82 / 2.30 / 93 % |

Gate statistics for `video_carry`: frames replaced 44 of 91 / 53 of 111 / 72 of 154; precision
0.80 / 1.00 / 0.90 against "frame error > 2 boards", recall 1.0 on all three (no occluded frame slipped
through). On the replaced frames the error went 3.13 → 1.31 / 24.8 → 0.31 / 5.54 → 1.65; the kept
frames sit at 0.68 / 0.60 / 2.19 (tom_old's 2.19 is the annotation offset of finding 8, present on
every frame of that video). Of the five gate features the agent built (fit residual, row coverage,
bottom width vs the throw's median, bottom **centre** vs the median, overlap with YOLO person boxes),
the shipped configuration uses only the centre rule at 3 % of the lane width: when the bowler stands
in the lane the mask's centre jumps, everything else is noisier than the failure it is meant to catch.

`best_late` runs SAM on the six frames before contact and picks one by a truth-free score:

| candidate (frames before contact → MAE) | sample_input | Chardie | tom_old |
|---|---|---|---|
| 1 / 2 / 3 / 4 / 5 / 6 | 0.22 / 0.24 / 0.24 / 0.16 / 0.20 / **0.11** | 0.86 / 0.88 / 0.75 / 0.59 / 0.72 / **0.55** | 2.21 / 2.29 / 2.29 / 2.21 / **2.18** / 2.21 |
| picked (residual + coverage + gradient + sharpness) | 0.22 (−1) | 0.88 (−2) | 2.18 (−5) |

The picker found the oracle only on tom_old, where all six are equal; on the handheld videos its
features rank the frames almost opposite to their error. The candidates themselves show the useful
pattern: the error falls steadily the further the frame is from contact (0.22 → 0.11, 0.86 → 0.55),
because the ball, the only moving thing near the far end, is further from the pin deck.
`late_median` (median of the six frames' lines warped into the pre-hit frame) is 0.44 / 0.79 / 2.14
(0.23 / 1.05 / 2.21 without warping), worse than the best single frame every time, as in loop 1.
Re-running video mode from the pre-hit frame with the tiny model and kept prompts (`video_keep`) is
no better than gating loop 1's masks and is worse on Chardie (2.29: the tiny model's propagation
drifts on the 720p video), so the gate on existing masks is the cheaper and better path.


## What the results say

1. **Fixing the prompt rule is the only change that helps everywhere it applies.** Three kept
   prompts instead of two: tom_old last 1.35 → 1.17, sample_input pre-hit 0.55 → 0.31 with no other
   change. It matters for the engine because a ball detector will always place the last path points
   next to the ball.

2. **Sub-pixel edges and prompt ensembles change nothing; the residual is systematic.** Reading the
   logit zero crossing instead of the first mask pixel moves results by ≤0.1 board. Ten prompt
   variants (3-5 points, four spacings, ±6 px lateral jitter) decoded on one encoding span only
   0.14-0.22 on sample_input, 0.41-0.63 on Chardie, 1.31-1.55 on tom_old, and their mean logit
   scores like any single member. Whatever error is left is not prompt noise and not the mask's
   quantisation; it is the same on every variant.

3. **Resolution at the pin end helps two videos and hurts the third, for a reason that is not the
   model.** A second SAM pass on a crop of the top 55 % of the lane (2.5x on sample_input, 4.4x on
   Chardie, 1.8x on tom_old) takes Chardie 0.47 → 0.32 and tom_old 1.23 → 0.49 (0.45 with the tiny
   model), but sample_input 0.22 → 0.65-0.70. `overlays/diagzoom_sample_input_113.jpg` shows why: at
   high resolution SAM includes the lit gutter lip in the lane, 1-2 px per side at the far end, and
   the sample_input annotator stopped at the wood edge. On Chardie and tom_old the wider far end
   happens to match their annotations better. 1-2 px is one board at the pins, so the sign of the
   "improvement" depends on the annotator's convention, not on SAM. The 2048 px encoder (`hires`)
   is the same story with worse stability (tom_old 0.83 with two prompts, 2.72 with three).

4. **Extrapolating from the wide end is worse on every video.** Fitting only the lower 70 % of rows
   (`trim`; the sweep from 0 to 50 % is in the JSON) and constraining both edges through a vanishing
   point estimated with the neighbouring lane's edges (`vp`, 4 lines; the neighbour was found on
   sample_input and Chardie, not behind tom_old's ball return) both lose. The mask's far-end rows
   agree with the annotation better than any line extrapolated from where a board is 10 px, so the
   lower-lane edges carry their own small offsets (the gutter lip on the right, the annotation
   inside the gutter on the left of tom_old, `overlays/diag_tom_old_169.jpg`) that a long lever arm
   amplifies. The polarity-aware gradient snap fails for the same reason: the strongest edge of the
   right sign within 6 px is usually the lip, not the annotated boundary.

5. **Which frame: sharper is not better against this truth.** `prehit-6` gives the best sample_input
   numbers of either loop (0.10-0.14) and `prehit` / `prehit-6` are fine on Chardie with a crop
   (0.37-0.49), but every method scores ~1.8-2.3 on tom_old's sharp pre-hit frames against 0.5-1.2
   on its blurred last frame. See point 6.

6. **The annotation, not the model, is now the floor.** Three checks on the truth itself:
   - sample_input's "per-frame" corners are six hand-clicked sets over 180 frames; the top width
     varies 58-61 px, about ±1 board at the pins. Numbers near 0.1-0.2 are at that floor.
   - On tom_old's sharp pre-hit frames both of SAM's far-end edges sit 5-7 px to the right of the
     annotated ones, tapering to 0 at the foul line (`diag_offsets.py`: left +6.4/+5.3/+3.8/+1.9/0.0
     px from top to bottom band, right +5.0/+4.0/+2.1/+1.1/−1.0): a lateral shift of the far end,
     not a width error. The pins (point 8) put the annotation within 1.7 px of the lane centre and
     SAM 5.2 px right of it, so this one is SAM's. It is unique to tom_old's standing-pin frames and
     shrinks on the pin-hit frame (f171, blurred, pins falling: 1.17-1.35), which is why the blurred
     frame scores better than the sharp ones there. The likely cause is the deck: standing pins and
     their reflections brighten the right half of the lane's end on this lane, and the mask follows
     the light. An earlier draft of this README read the same 5 px as an annotation error from a 5x
     crop by eye; the pin measurement says otherwise.
   - Chardie: SAM agrees with the pins to within 1 px at the far end; the annotation is 2.3 px
     (about two boards) off it.

   Consequence: on the two handheld videos, differences below ~0.3 (sample_input) and ~0.5-0.9
   (Chardie, where a board is 1 px and the annotation is two of them off) are not measurable with
   these corners; on tom_old the ~1.7 boards that remain after the crop are SAM's and the pin centre
   removes them. Either way the next lever is a physical ruler at the far end (the pins, below), not
   another prompt.

7. **Tiny vs base.** With a crop, sam2.1_t matches or beats base on tom_old (0.45) and Chardie (0.48)
   and is within 0.25 on sample_input; without a crop it is 0.2-0.5 worse on sample_input. The loop-1
   recommendation to ship tiny stands, with the crop.

8. **The pins arbitrate the far-end centre, video by video.** Measured at the pin-base row, SAM's
   far-end centre is within about 1 px of the standing pin cluster's centre on sample_input and
   Chardie, and 5.2 px (three boards) to the right of it on tom_old for every full-frame prompt
   (3.9-4.2 px with a crop, 2.8 px at 2048 px). The annotations are 0.9 px (sample_input), 2.3 px
   (Chardie, two boards) and 1.7 px (tom_old) from the pins. So the metric's floor is annotation
   noise on the handheld videos, and on tom_old the residual is a genuine SAM shift of the far end
   that only the pin anchor fixes: re-scored against a pin-centred truth the full-frame methods stay
   at 1.7 boards on tom_old while `pins_m` is at 0.09 (circular, but its width and slopes come from
   SAM, so it says the rest of the lane is right once the centre is). On Chardie the full-frame
   methods improve to 0.5-0.6 against that truth and the crop methods get worse, a ±0.7 swing from a
   2 px shift where a board is 1 px; the pin measurement's own ±1 px uncertainty is the floor there.
   The crop's real defect on sample_input is in the same table: its far end sits 1 px left of the
   pins where the full-frame mask is 1 px right, and the annotation happens to sit on the pins' side.

9. **The one SAM error that survives the pins is the far-end width.** At the foul line SAM's width
   is within 2-3 % of the annotation on every video, so there is no edge-convention offset. At the
   pin deck the full-frame mask is 5-12 % narrower than the annotation (2-3 px per side, 1.5-3
   boards); the crop brings that to 5-7 %, the gutter objects to 1 % on tom_old only. The pins'
   extent cannot arbitrate: at the pin-base row it reads 0.85, 0.92 and 1.07 of the annotated width
   (outer pins merge with their reflections, 720p splits the cluster, and on sample_input at 8x the
   outermost pin is plainly 4-6 px inside the visible lane edge), and four different extent rules
   move it by at most 0.03. The width ruler needs the pin *spacing* (12 in between neighbours, seven
   columns 6 in apart from behind), which nobody has built yet. The annotated ball radius is a
   fixed-size marker (25 px on every frame), so the ball is not a ruler either.

10. **Anchors.** Gutters as separate objects work mechanically (the lane-vs-gutter crossing exists
    on ~99 % of rows, decoded for ~5 ms on the cached encoding) and buy almost nothing: 0.24 → 0.20,
    0.88 → 0.76, 2.29 → 2.30. The lane's lateral boundary was never the uncertain thing; the line
    fitted through a 39-67 px far end is. The pin rack is a centre ruler, not a width ruler (above),
    and used for the centre only it removes tom_old's 5 px shift: `pins_m` 0.60 against the
    annotation (0.54 with tiny weights), 0.09 against the pin-centred truth. Pivoting the pair about
    the foul line instead of refitting through the far-end segment (`pins_c`) is worse everywhere;
    adding a crop on top of the pins (`pins_zoom`) changes nothing (±0.01), because once the pins fix
    the top corners the crop has nothing left to add; and pins measured on one frame and warped 11
    frames through the camera model on handheld video move 8 px, which is why every pin method
    collapses on sample_input's `last` frame. Prompting from the bowler and the pins with no ball
    path (`landmarks`) scores 0.37 / 0.41 / 1.44 on the last frame against 0.24 / 0.39 / 1.17 for the
    ball path: the lane can be found before there is a ball track. Details that matter for the
    engine: MediaPipe found no pose on sample_input's release frame (the bowler is clipped at the
    frame edge; the YOLO box bottom stood in and still put all three prompts on the lane), the
    wrists were invisible on every video at release (visibility 0.02-0.23; the hand is under the
    body from behind) while the sliding foot was 0.67-0.84, so the foot is the near landmark and the
    wrist only a cross-check; the near anchor is very forgiving (all three were off the lane
    laterally, one 87 px below its bottom row) because the far anchor is precise and the segment
    converges onto the lane; and the path is ball-free for prompting but not yet for timing (the
    release frame and the choice of bowler still came from the ball annotation; a swing-peak
    detector would close that).

11. **Tracking through the throw is solved by one rule, and the camera model now binds.** The loop-1
    video-mode masks are wrong only while the bowler stands in the lane, and when that happens the
    mask's centre at the foul line jumps (on Chardie's worst frames the mask sits on the neighbouring
    lane with normal width, residual and coverage and no bowler overlap: every geometric health check
    passes, only the centre notices it is 250 px away). Flagging frames whose centre is more than 3 %
    of the lane width from the throw's median (after warping into one frame; the median re-estimated
    over the passing frames in three passes, because more than half of Chardie's throw is occluded)
    catches every such frame on all three videos with 0-8 false alarms, and carrying the nearest
    clean frame's lane through the camera model brings the per-frame mean from 1.85 / 16.4 / 3.7 to
    0.98 / 0.41 / 1.94, within 0.2 of an oracle gate. Gating on the four features the brief named
    (residual, coverage, width, person overlap) without the centre makes Chardie *worse* than loop 1
    (34.1). Carrying the median of k nearest frames instead of the single nearest loses (k=5: +0.23
    on Chardie, +0.25 on tom_old): being close beats being averaged once cumulative drift enters.
    Two threshold traps recorded by the agent: an absolute residual cut (3 px) failed every
    sample_input frame and silently returned the loop-1 numbers, and re-estimating the residual median
    over passing frames is a ratchet. A held-out check exists: fresh masks from SAM 2 tiny video
    mode re-prompted with kept prompts on the pre-hit frame (`video_keep`) gate from 2.05 / 19.6 / 3.51
    to 1.04 / 2.29 / 1.75 with recall 1.0 again (tom_old's 1.75 is the best per-frame mean in either
    loop; Chardie's backwards propagation collapsed and the gate carried four frames). The binding
    constraint is now the ORB camera model's per-frame jitter, 3.0 px mean and 8.9 px max at the pin
    end on sample_input against 10 px of cumulative motion over 19 frames: a two-frame carry costs
    2.4 boards there (the last frame regresses 0.21 → 2.40), so never gate the frame you are about
    to quote, and note that Chardie's and tom_old's truth is a static annotation warped through the
    same model the carry uses, which makes their gains partly circular; sample_input's 1.85 → 0.98
    against an independent hand annotation is the honest one. Choosing among late frames by residual,
    coverage, gradient or sharpness does not work (the two consistently signed features, residual and
    SAM's own score, are anti-correlated with error); the candidates differ by ≤0.33 boards anyway,
    and distance from contact is the only pattern.

## Anchoring like the fitness model

The lifting pipeline anchors every measurement on named landmarks with physical meaning (33
MediaPipe keypoints → joint angles), not on pixels, and that is what makes it robust to camera
placement. The lane has landmarks of exactly that kind, each at a known physical position:

| landmark | physical position | what it pins down |
|---|---|---|
| foul line corners | 0 ft, boards 1 and 39 | the near end (wide, easy: 10 px per board) |
| release point (bowler's wrist / slide foot) | on the lane, just past the foul line | a prompt that exists before any ball track |
| arrows | 15 ft, boards 5-35 in steps of 5 | absolute board positions mid-lane (not tried here) |
| pin deck corners, 7-pin and 10-pin | 60 ft, pins 36 in apart, cluster ≈ 40.8 of 41.5 in | the far end, where a board is 1-2 px and the annotation is weakest |

Measured here: (a) prompts built from the release point and the pin centre find the lane without a
ball track, within 0.1-0.3 board of the ball-path prompts on two videos; (b) the pin cluster's centre
is a far-end truth good to ~1 px: it exposed a three-board SAM shift on tom_old that no prompt or crop
removes and a two-board annotation error on Chardie, and anchoring the far end on it fixes the former
(`pins_m` 0.60 / 0.54 tiny on tom_old, 0.09 against the pin-centred truth); (c) the pins' *extent* is
not a width ruler, the pin *spacing* would be. So yes, there is a better anchor than the ball path, and
it is the same idea as the fitness model: named landmarks with known physical positions, found by a
detector, with the segmentation model filling in the geometry between them. The proper long-term
version is a small lane-keypoint model (foul-line corners, 7 arrows, deck corners, 7-pin, 10-pin,
headpin), trained the way the pose model was, which gives a metric homography from a single frame
and makes every board number absolute instead of relative to a mask edge. Until there is labelled
data for it, SAM prompted from the pose and the pins, with the far end calibrated on the pin
cluster, is the practical version, and it also removes the "ball first, lane second" dependency.


## Recommendation for the engine

Updates the loop-1 list; unchanged items are not repeated.

1. **Prompt rule: keep n points.** Slide a prompt down the path when it lands on the ball; never drop
   it. Three points, 15-85 % of the on-lane path by image length.
2. **Frame: a pre-hit frame with the pins standing** (pin-hit − 2 to − 6), then a second SAM pass on
   a crop of the far half with its prompts in the lower half of the crop (`zoom_lo`). Use the crop's
   rows for the far end and the full frame's for the rest, one robust line per edge. Tiny weights.
3. **Anchors before the ball track**: prompt from the release point and the pin cluster centre
   (`landmarks`) to get a lane on the first pass; refine with the ball path once it exists.
4. **Calibrate the far-end centre with the pins**, not with the mask edge: the standing cluster's
   centre is the lane centre at the deck, and re-centring SAM's far end on it (`pins_m`) removed the
   one SAM failure in this set (tom_old, 5 px = 3 boards, invisible to every prompt and crop). Measure
   the pins on the frame they are used on (warping them across a handheld throw costs 8 px) and use
   the width from SAM, not from the pin extent. A pin count (seven columns from behind) should gate a
   partial rack, which nothing here handles.
5. **Tracking: gate, then carry.** Per-frame masks fail only when the bowler stands in the lane; a
   truth-free gate plus carrying the nearest clean lane through the camera model is what makes
   video mode usable through the whole throw.
6. **Do not** snap to gradients, extrapolate from the wide end, run the encoder at 2048 px, or
   ensemble prompts. None of them buys anything against this truth.
7. **Ground truth next.** Before another model loop, annotate the far end with the pins as the ruler
   (7-pin and 10-pin bases on a standing-pin frame) on at least these three videos, and re-score.
   Everything below one board at the pins is currently unmeasurable.

## Retro (two agents in parallel, ~90 min each)

Harness first, then fan-out, worked: `run2.py`'s method registry and `run2.finish` gave the agents
a fixed row schema, so every number they produced could be read back from `results/*.json` and
re-analysed here (`centre_check.py`, `rescore_pins.py`) without their prose. That mattered because
the harness refused both agents' report files (`results/report_*.md` is not writable from a
subagent); one report came back inline and was cut at 16 KB, the other never arrived and was
requested in chunks afterwards. The pins centre check, the single most useful number of the loop,
came out of the anchors agent's extras, not its report. And the agent's report corrected the lead:
the first draft of this README compared the pin centre at the pin-base row with the annotated centre
at the annotated top row (the JSON field does exactly that), five rows apart on a lane whose edges
have different slopes, and concluded that tom_old's annotation was four boards off; measured at one
row it is 1.7 px and the shift is SAM's. A number that agrees with what you already believed from a
5x crop is the one to re-derive. The tracking agent's report was written with a shell heredoc after
the Write tool refused the file; do not brief report files at all, and never suggest that route.
`run2.finish` applies `extra` after the score, so passing an earlier row through as `extra` silently
overwrites `board_mae` and the corners (this produced one wrong row before it was caught). What went
badly otherwise: latency figures are
meaningless (three SAM processes on one CPU), the anchors agent re-implemented `soft` as `softk`
(same numbers), and its `pins_m` "win" on tom_old needed a diagnosis of the metric's insensitivity to
the left edge before it could be quoted. Next time: brief agents to put the narrative in the JSON
extras or a `.txt`, keep messages under 8 KB and numbers-first, and stagger CPU-heavy runs.


## Reproducing

```
V=~/code/bowling-app/analysis-engine/.venv/bin/python   # torch, ultralytics 8.4.14, opencv, mediapipe
cd docs/research/2026-09-12-sam2-lane-experiments-2
# frames + weights: loop 1's commands (gt.extract_frames, first SAM call downloads weights) into
# $SAM2X_SCRATCH/frames and /weights; loop-1 video-mode masks into $SAM2X_SCRATCH/masks
$V run2.py --list
$V run2.py --prompts keep --methods even3,soft,ens,zoom,zoom_lo,zoom_trim,tiles,ens_zoom,hires,snap2,trim,vp --kinds last,prehit,prehit-6
$V run2.py --prompts keep --weights sam2.1_t.pt --tag _tiny --methods even3,soft,ens,zoom,zoom_lo --kinds last,prehit,prehit-6
$V run2.py --methods even3,soft,zoom,hires,ens --kinds last,prehit          # loop-1 prompt rule, for the comparison
$V run_anchors.py; $V run_track.py                                          # the agents' methods
$V diag_offsets.py tom_old 169 keep; $V diag_top.py tom_old 169 171 zoom; $V diag_zoom.py sample_input 113
$V centre_check2.py; $V rescore_pins.py                                       # pins vs annotation vs SAM, same row
$V tables.py wide                                                            # README tables
$V make_review_video2.py                                                     # review.mp4 + results/summary.md
```
