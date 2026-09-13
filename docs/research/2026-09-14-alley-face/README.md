# Does the alley have a face? Constellation detection of the lane's landmarks (2026-09-14)

Status: complete for E1-E5 and the tom_old fold of E6; the two remaining E6 folds train in the background and are folded into the E6 table when they land. Review video: `review.mp4` (gitignored; regenerate with the commands at the
end). Scripts, result JSON (`results/`) and overlays (`overlays/`) are in this folder; frames,
candidate pools, per-frame fits, datasets and training runs live in the session scratchpad
(`AF_SCRATCH`). Nothing in the earlier loops' folders was edited; loop 4's `common.py` /
`landmarks.py` are imported (this loop's shared module is `af.py` because loop 4's modules import a
`common`).

## The question

Loop 4 used the landmarks one at a time from a lane hypothesis. This loop asks whether the lane's
markings - two foul-line corners, a row of guide dots, the seven arrows, the ten pin bases, the gutter
edges - form a constellation that can be (E3) **found** in a frame with no ball path, no trained mask
and no prompt, (E4) **aligned** jointly so the near end comes out right, (E5) **persisted** through the
bowler, the ball and the falling pins, and (E6) **learned** the way face alignment learns faces
(heatmaps under exact homography augmentation), with (E1) the constellation itself measured first
and (E2) the raw feature pool it has to be found in.

Metric, unchanged from loops 1-4: board MAE of the annotated ball path through the predicted
homography vs through the truth's; every number against the hand annotation (`annotated`), the
pins-based truth (`pins`) and the all-landmark truth (`all`) of loop 4, plus the last-20 % tail.

## The constellation (E1)

Lane coordinates: x in inches from the left edge (board 39 side), y in inches from the foul line.

<!-- TABLE:e1 -->
| feature | lane position (in) | count | source | visible on sample_input (pre-hit) | visible on Chardie (pre-hit) | visible on tom_old (pre-hit) |
|---|---|---|---|---|---|---|
| foul-line corners | (0, 0), (41.5, 0) | 2 | rule | 2/2 | 2/2 | 2/2 |
| foul-line dots (approach side) | y = -0.15 ft (-1.8 in), x = 20.75 + k x 5.32 in (5 boards), k = -3..3 | 7 (7 observed) | measured on sample_input f117 (+ pooled frames), symmetric completion; measured centre -0.66 in from the lane centre | 6/7 | 0/7 | 7/7 |
| guide dots | y = 7.04 ft (84.5 in), x = 20.75 + k x 3.19 in (3 boards), k = -5..5 | 11 (8 observed) | measured on tom_old f165 (+ pooled frames), symmetric completion; measured centre -0.41 in from the lane centre | 0/11 | 0/11 | 8/11 |
| approach dots | y = -11.74 ft (-140.9 in), x = 20.75 + k x 5.32 in (5 boards), k = -3..3 | 7 (5 observed) | measured on Chardie f130 (+ pooled frames), symmetric completion; measured centre -1.78 in from the lane centre | 0/7 | 5/7 | 0/7 |
| seven arrows | boards 5..35, V centre 15.52 ft, 0.45 ft per 5 boards (per video: sample_input 15.36/0.48, Chardie 15.42/0.37, tom_old 15.78/0.50) | 7 | rule-book boards, depth from loop 4 | 7/7 | 5/7 | 7/7 |
| ten pin bases | rule-book rack, head pin at 60 ft | 10 | rule | 10/10 | 10/10 | 10/10 |
| gutter edges, foul line | x = 0, x = 41.5, y = 0 | lines | rule | all | all | all |
<!-- /TABLE:e1 -->

<!-- TABLE:timeline -->
| video | class | points | clear per frame (median, throw) | frames with >= half clear (of throw frames) | hidden by the bowler | by the ball | pins in motion |
|---|---|---|---|---|---|---|---|
| sample_input | foul | 2 | 2 | 82/82 | 31-125 (42 frames) | - | - |
| sample_input | fdot | 7 | 5 | 68/82 | 34-121 (83 frames) | 43-43 (1 frames) | - |
| sample_input | dot | 11 | 11 | 82/82 | 41-102 (31 frames) | 49-53 (5 frames) | - |
| sample_input | adot | 7 | 0 | 0/82 | - | - | - |
| sample_input | arrow | 7 | 7 | 82/82 | 89-101 (2 frames) | 59-63 (5 frames) | - |
| sample_input | pin | 10 | 10 | 81/82 | - | 114-128 (15 frames) | 119-179 (61 frames) |
| Chardie | foul | 2 | 1 | 75/75 | 45-128 (64 frames) | - | - |
| Chardie | fdot | 7 | 4 | 66/75 | 47-122 (76 frames) | - | - |
| Chardie | dot | 11 | 6 | 38/75 | 56-111 (56 frames) | 68-74 (7 frames) | - |
| Chardie | adot | 7 | 5 | 75/75 | - | - | - |
| Chardie | arrow | 7 | 6 | 51/75 | 58-106 (43 frames) | 74-83 (10 frames) | - |
| Chardie | pin | 10 | 6 | 40/75 | 75-93 (19 frames) | 101-134 (34 frames) | 135-170 (36 frames) |
| tom_old | foul | 2 | 2 | 154/154 | 8-154 (44 frames) | - | - |
| tom_old | fdot | 7 | 5 | 127/154 | 10-141 (132 frames) | - | - |
| tom_old | dot | 11 | 11 | 154/154 | 22-121 (55 frames) | 30-36 (7 frames) | - |
| tom_old | adot | 7 | 0 | 0/154 | - | - | - |
| tom_old | arrow | 7 | 7 | 154/154 | 61-91 (5 frames) | 43-58 (16 frames) | - |
| tom_old | pin | 10 | 10 | 104/154 | - | 115-171 (56 frames) | 171-408 (238 frames) |
<!-- /TABLE:timeline -->

## Method

- **E1 constellation** (`e1_constellation.py`, `e1_timeline.py`). The lane plane of each annotated
  video's pre-hit frame (and -2 / -4) is rectified through loop 4's all-landmark truth homography and
  every repeatable dark mark near the foul line is measured in lane inches: a row finder fits a
  regular grid (pitch 3 or 5 boards) to small dark blobs in three bands (4.5-9.5 ft, -1.5..0.6 ft,
  -14.5..-9.5 ft). The constellation is written symmetric about the lane centre by the rules (x =
  20.75 + k x pitch); the measured centre offset under the truth is recorded as the truth's own
  near-end error. The visibility timeline projects every point into every frame and marks it clear /
  behind the bowler (yolo11n-seg person mask, dilated 4 px) / under the annotated ball / pins in
  motion (after the pin-hit marker).
- **E2 candidates** (`e2_candidates.py`). Whole frame, no lane prior: dark marks = max over three
  black-hat scales (9 / 17 / 29 px), strong tier median + 6 MAD (>= 12 grey levels), weak tier >= 8;
  rack blobs = white-map (V - S) blobs with a rack's proportions (0.2 w <= h <= 1.3 w; the ten pins
  merge into one white mass at these resolutions, so px/in = w / 40.8 and the base row = top + 15 in);
  line segments = LSD, >= 5 % of the frame height. Precision / recall against the per-video truth
  (arrows at the V depth loop 4 measured on that video; 1.5 in, >= 4 px).
- **E3 finding the face** (`e3_face.py`). Chains of dark marks with near-constant spacing (gap ratio
  0.5-2, y held within 0.28 of the gap so the V can turn at its apex), ranked by spacing regularity;
  each chain of 5-11 is read as every row class (arrows / guide dots / foul-line dots / approach
  dots) at every contiguous board assignment; paired with each rack blob above it whose px/in is
  0.12-0.9 of the row's own (or with a second row: arrows + a dot row); one DLT per pairing with the
  rule-book constellation as the model. Camera-placement priors reject the impossible (near width
  2-20 x the far width, deck >= 0.6 near widths above the foul line, the arrows inside the frame).
  Score = constellation points explained (a mark within clip(0.6 in x local px/in, 3, 8) px, weak
  marks 0.5) minus the chance matches at that tolerance (mark density x pi tol^2), + 3 for a rack
  blob at the projected rack, + 0.5 per LSD segment along a projected gutter (<= 3 a side) or the
  foul line (<= 2); a hypothesis needs >= 3 arrows explained. Hypotheses are clustered into lanes by
  both ends. "Right lane" = far-end centre within one far width and foul-line centre within half a
  near width of the truth's (E3 is a coarse find; the board MAE columns carry the accuracy).
- **E4 aligning the face** (`e4_align.py`). From E3's homography of the right lane: arrows and the
  three dot rows re-detected as sub-pixel centroids on the H-rectified bands, the pin bases with loop
  4's rack fit (alias-margin guarded), gutter lines as robust fits to the LSD segments along x = 0 /
  x = W, the foul line likewise along y = 0, near corners = their intersections; one weighted robust
  DLT (pins 0.45 in, arrows / dots 0.7, approach dots 1.0, corners 1.0, gutter points 1.5 x-only;
  reject > 2.5 in). Variants drop the corners, drop the pins, or use the rack pooled over the
  standing-pin frames (E5).
- **E5 persistence** (`e5_persist.py`). E4's refined landmarks matched by name to the pre-hit frame,
  RANSAC similarity per frame = the static-landmark camera; missing landmarks carried through it;
  the rack pooled in the reference frame (median over standing-pin frames) and moved back per frame;
  lane refitted on every frame from detected + carried points. Camera judged on sample_input's hand
  per-frame corners against loop 3's ORB model.
- **E6 heatmaps** (`e6_heatmap.py`, `e6_eval.py`). A 3.8 M-parameter U-Net (stride-4 output) with
  one sigmoid heatmap per landmark (44) or per class (6), trained on 640 px native-resolution crops
  with a random homography applied to image and points together (rotation +-12 deg, scale 0.64-1.4,
  anisotropy, shear, perspective, translation) plus photometric noise; occluded landmarks (E1
  timeline) and fallen pins are ignored in the loss; positives weighted 20x. Leave-one-video-out,
  2500 iterations of batch 6 on MPS, best.pt by the training videos' held-back frames. Inference on
  the full frame, peaks above 0.25 with quadratic sub-cell refinement.

## Results

### E2 - the raw feature pool, no lane prior

<!-- TABLE:e2 -->
| video | frames | ms | dark marks / frame (strong) | precision of the pool (strong) | rack blobs / frame, precision | rack recall (standing) | arrow recall, px | guide dots | foul dots | approach dots | true gutter / foul-line segments per frame |
|---|---|---|---|---|---|---|---|---|---|---|---|
| sample_input | 180 | 206 | 1388 (826) | 0.006 (0.007) | 34.4, 0.019 | 0.958 | 0.69, 2.6 | 0.16 | 0.28 | - | L 1.24 R 0.48 foul 0.9 |
| Chardie | 171 | 89 | 663 (383) | 0.006 (0.004) | 20.3, 0.035 | 0.896 | 0.44, 2.0 | 0.00 | 0.09 | 0.03 | L 1.36 R 1.13 foul 0.01 |
| tom_old | 409 | 78 | 532 (274) | 0.033 (0.049) | 26.9, 0.011 | 0.655 | 0.96, 3.2 | 0.43 | 0.96 | - | L 2.2 R 2.57 foul 3.17 |
| bowling_video | 139 (every 3rd) | 225 | 1536 (924) | - | 26.2, - | - | - | - | - | - | - |
| IMG_0242 | 310 (every 3rd) | 74 | 458 (260) | - | 14.0, - | - | - | - | - | - | - |
<!-- /TABLE:e2 -->

### E3 - finding the face

<!-- TABLE:e3 -->
| video | feature set | frames | lanes found / frame (median) | right lane found (throw frames) | top score is the right lane | bowler's feet pick it | frame centre | widest | board MAE median: annotated / pins / all | tail (pins) | pre-hit (pins) | far width err px | far centre err px | ms |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| sample_input | arrows+dots+rack+gutters | 180 | 5 | 0.26 | 0.01 | 0.23 | 0.00 | 0.00 | 2.41 / 1.73 / 1.74 | 0.56 | 1.43 | 11.5 | 0.8 | 3469 |
| sample_input | arrows (every 5th frame) | 36 | 1 | 0.00 | 0.00 | 0.00 | 0.00 | 0.00 | - / - / - | - | - | - | - | 2870 |
| sample_input | arrows+dots (every 5th frame) | 36 | 2 | 0.00 | 0.00 | 0.00 | 0.00 | 0.00 | - / - / - | - | - | - | - | 3240 |
| sample_input | arrows+rack (every 5th frame) | 36 | 4 | 0.25 | 0.00 | 0.20 | 0.00 | 0.00 | 2.10 / 1.73 / 1.73 | 0.64 | - | 11.6 | 0.8 | 2894 |
| sample_input | arrows+dots+rack (every 5th frame) | 36 | 5 | 0.25 | 0.00 | 0.20 | 0.00 | 0.00 | 2.10 / 1.73 / 1.73 | 0.64 | - | 11.6 | 0.8 | 3446 |
| Chardie | arrows+dots+rack+gutters | 171 | 0 | 0.00 | 0.00 | 0.00 | 0.00 | 0.00 | - / - / - | - | - | - | - | 1323 |
| Chardie | arrows (every 5th frame) | 35 | 0 | 0.00 | 0.00 | 0.00 | 0.00 | 0.00 | - / - / - | - | - | - | - | 938 |
| Chardie | arrows+dots (every 5th frame) | 35 | 0 | 0.00 | 0.00 | 0.00 | 0.00 | 0.00 | - / - / - | - | - | - | - | 1300 |
| Chardie | arrows+rack (every 5th frame) | 35 | 0 | 0.00 | 0.00 | 0.00 | 0.00 | 0.00 | - / - / - | - | - | - | - | 944 |
| Chardie | arrows+dots+rack (every 5th frame) | 35 | 0 | 0.00 | 0.00 | 0.00 | 0.00 | 0.00 | - / - / - | - | - | - | - | 1339 |
| tom_old | arrows+dots+rack+gutters | 409 | 5 | 0.50 | 0.40 | 0.28 | 0.29 | 0.09 | 1.29 / 0.62 / 0.65 | 0.49 | 0.31 | 2.0 | 0.7 | 995 |
| tom_old | arrows (every 5th frame) | 82 | 0 | 0.13 | 0.13 | 0.50 | 0.50 | 0.50 | 4.32 / 2.83 / 2.79 | 3.38 | - | 51.2 | 10.0 | 294 |
| tom_old | arrows+dots (every 5th frame) | 82 | 1 | 0.13 | 0.07 | 0.09 | 0.17 | 0.12 | 6.46 / 5.43 / 5.39 | 9.14 | - | 39.0 | 13.6 | 616 |
| tom_old | arrows+rack (every 5th frame) | 82 | 4 | 0.45 | 0.35 | 0.23 | 0.41 | 0.14 | 1.29 / 0.58 / 0.59 | 0.43 | - | 3.0 | 0.7 | 353 |
| tom_old | arrows+dots+rack (every 5th frame) | 82 | 4 | 0.55 | 0.39 | 0.29 | 0.23 | 0.13 | 1.28 / 0.53 / 0.57 | 0.36 | - | 0.9 | 0.7 | 1003 |
| tom_old | arrows+dots+rack+gutters - pool = class heatmap model's arrows (held-out) | 409 | 3 | 0.56 | 0.56 | 0.46 | 0.65 | 0.14 | 1.77 / 0.43 / 0.43 | 0.40 | 0.41 | 1.5 | 0.5 | 14 |
| tom_old | arrows+dots+rack+gutters - pool = landmark heatmap model's arrows (held-out) | 409 | 0 | 0.00 | 0.00 | 0.00 | 0.00 | 0.00 | - / - / - | - | - | - | - | 0 |
| video | feature set | frames | lanes / frame (median, max) | frames with >= 1 lane | ball's lane found | ball's lane is the top score | ms |
|---|---|---|---|---|---|---|---|
| bowling_video | arrows+dots+rack+gutters | 139 | 4, 10 | 0.98 | 0.55 | 0.10 | 4499 |
| IMG_0242 | arrows+dots+rack+gutters | 310 | 1, 6 | 0.84 | - | - | 429 |
<!-- /TABLE:e3 -->

### E4 - aligning the face

<!-- TABLE:e4 -->
| video | variant | frames | throw median: annotated / pins / all | tail (pins) | pre-hit (pins) | last (pins) | far width err px | far centre err px | near corners err px (L / R) |
|---|---|---|---|---|---|---|---|---|---|
| sample_input | e3 | 40 | 2.41 / 1.73 / 1.74 | 0.56 | 1.43 | - | 11.5 | 0.8 | - |
| sample_input | rows+pins | 39 | 2.56 / 1.92 / 1.94 | 0.83 | 1.47 | - | 4.3 | 1.0 | 12.3 / 34.3 |
| sample_input | refit | 38 | 2.56 / 1.92 / 1.94 | 0.83 | 1.47 | - | 4.3 | 1.0 | 12.3 / 34.3 |
| sample_input | no-near | 38 | 2.56 / 1.92 / 1.94 | 0.83 | 1.47 | - | 4.3 | 1.0 | 12.3 / 34.3 |
| sample_input | rows-only | 19 | 27.07 / 26.37 / 26.39 | 22.03 | 136.68 | - | 49.2 | 753.1 | 674.1 / 938.8 |
| sample_input | pins-pooled | 38 | 2.48 / 1.87 / 1.89 | 0.81 | 1.45 | - | 4.0 | 1.0 | 13.0 / 33.2 |
| Chardie | e3 | 6 | - / - / - | - | - | - | - | - | - |
| Chardie | rows+pins | 6 | - / - / - | - | - | - | - | - | - |
| Chardie | refit | 6 | - / - / - | - | - | - | - | - | - |
| Chardie | no-near | 6 | - / - / - | - | - | - | - | - | - |
| Chardie | rows-only | 1 | - / - / - | - | - | - | - | - | - |
| Chardie | pins-pooled | 6 | - / - / - | - | - | - | - | - | - |
| tom_old | e3 | 187 | 1.29 / 0.62 / 0.65 | 0.49 | 0.31 | - | 2.0 | 0.7 | - |
| tom_old | rows+pins | 178 | 1.27 / 0.81 / 0.85 | 0.85 | 0.25 | - | 2.6 | 1.2 | 14.4 / 24.4 |
| tom_old | refit | 177 | 1.27 / 0.81 / 0.84 | 0.85 | 0.29 | - | 2.5 | 1.2 | 14.4 / 24.2 |
| tom_old | no-near | 177 | 1.27 / 0.81 / 0.84 | 0.85 | 0.29 | - | 2.5 | 1.2 | 14.4 / 24.2 |
| tom_old | rows-only | 172 | 2.56 / 2.21 / 2.20 | 2.33 | 3.82 | - | 21.4 | 9.8 | 38.8 / 35.0 |
| tom_old | pins-pooled | 178 | 1.10 / 0.81 / 0.85 | 0.85 | 0.33 | - | 2.0 | 1.3 | 11.5 / 22.6 |
<!-- /TABLE:e4 -->

### E5 - persistence

<!-- TABLE:e5 -->
| video | frames | camera fits | landmarks in common (median; after the hit) | pooled rack (pins, frames) | lane on every frame: throw median annotated / pins / all | tail (pins) | after the hit (pins) | last (pins) | camera vs hand corners px: landmarks / ORB (pin end) | max |
|---|---|---|---|---|---|---|---|---|---|---|
| sample_input | 40 | 39 | 16; 5 | 10, 36 | 2.51 / 1.91 / 1.93 | 0.81 | - (0 f) | - | 10.42 / 4.15 (7.88 / 3.7) | 138.0 / 15.05 |
| Chardie | 6 | 6 | 14; - | 10, 6 | - / - / - | - | - (0 f) | - | - | - |
| tom_old | 187 | 185 | 7; 7 | 10, 74 | 1.09 / 0.81 / 0.85 | 0.90 | - (0 f) | - | - | - |
<!-- /TABLE:e5 -->

### E6 - learning the face

<!-- TABLE:e6 -->
| model | held-out video | class | clear points | recall (6 px) | px err median | precision | classical E2 recall, same frames | in-distribution recall (training videos' held-back frames) |
|---|---|---|---|---|---|---|---|---|
| class | tom_old | foul | 774 | 0.04 | 5.6 | 0.400 | - | 0.95 |
| class | tom_old | fdot | 2528 | 0.00 | - | 0.000 | 0.92 | 0.73 |
| class | tom_old | dot | 4280 | 0.00 | - | 0.000 | 0.38 | 0.73 |
| class | tom_old | adot | 0 | - | - | 0.000 | - | 0.00 |
| class | tom_old | arrow | 2824 | 0.92 | 3.7 | 0.853 | 0.95 | 0.98 |
| class | tom_old | pin | 1306 | 0.37 | 2.7 | 0.442 | - | 0.17 |
| landmark | tom_old | foul | 774 | 0.06 | 3.8 | 0.880 | - | 1.00 |
| landmark | tom_old | fdot | 2528 | 0.00 | 4.7 | 0.250 | 0.92 | 0.77 |
| landmark | tom_old | dot | 4280 | 0.00 | - | 0.000 | 0.38 | 0.96 |
| landmark | tom_old | adot | 0 | - | - | - | - | 0.00 |
| landmark | tom_old | arrow | 2824 | 0.20 | 2.5 | 0.151 | 0.95 | 0.98 |
| landmark | tom_old | pin | 1306 | 0.96 | 3.6 | 0.152 | - | 1.00 |
| model | held-out video | frames fitted (throw) | named points / frame | constellation fit: throw median annotated / pins / all | tail (pins) | pre-hit (pins) | far width err px | ms / frame |
|---|---|---|---|---|---|---|---|---|
| landmark | tom_old | 84 | 8 | 11.96 / 12.57 / 12.61 | 14.03 | 10.32 | 137.1 | 74 |
<!-- /TABLE:e6 -->

## What the results say

1. **The constellation is real and measurable, and it is not quite centred.** Three dot rows were
   found on the lane plane besides the arrows and pins: the guide dots at 7.04 ft (eleven at a
   3-board pitch, boards 5..35, all eleven seen on tom_old with the middle three under glare), seven
   dots 1.8 in behind the foul line on the arrow boards (7/7 on tom_old, 6/7 on sample_input, none
   resolvable at 720p), and the approach dots 11.7 ft behind the foul line (five of seven on Chardie,
   out of frame or hidden by the ball return elsewhere). Each row fits its grid to 0.1-0.2 in rms, yet
   under the truth homography every row's centre sits 0.4-0.7 in LEFT of the lane centre (approach
   dots 1.8 in, twelve feet of extrapolation), and the visible lane edges at the foul line confirm
   the truth there on tom_old - so the marks are laid half an inch off the lane's centre line, and a
   symmetric-by-rule model would misplace every dot by half a board. The constellation carries the
   measured positions. The arrows' depth disagrees between videos by 0.4 ft (15.36 / 15.42 / 15.78
   ft), which is the truths' own near-end scale error, not the alley's.

2. **Occlusion is short and the pins are the only long gap.** Through the throw the bowler hides
   the foul-line dots for 44-132 frames but the arrows for 2-43 and the guide dots for 31-56; the
   ball covers any one row for 5-25 frames; the pins are gone from the pin-hit marker on (61 / 36 /
   238 frames). On every video at least half of every visible row is clear on most throw frames.

3. **The raw pool is 99 % clutter, and the far end is in it but the near end is not.** With no lane
   prior a frame holds 460-1540 dark marks (precision 0.6-5 %), 14-34 rack-shaped white blobs and
   80-150 line segments. The arrows are in the pool on 96 % of tom_old frames, 69 % of sample_input
   and 44 % of Chardie (at 720p an arrow has no contrast against the lane); the rack blob is present
   on 66-96 % of standing-pin frames and, where present, its centre and base row are within 1-2 px
   of the truth and its width gives px/in to 2-3 %; the guide dots are in the pool on 43 / 16 / 0 %
   of frames and the foul-line dots on 96 / 28 / 9 %. The near-end features are what the classical
   detectors cannot see on the handheld videos.

4. **The face can be found from the pool alone - where its eyes are visible.** Chains of regularly
   spaced marks read as arrow rows, paired with a rack blob and scored by the constellation points
   they explain, find the right lane on 50 % of tom_old's throw frames (pre-hit 0.31 boards vs the
   pins truth, 0.62 median on the found frames, far-end width 2 px), 26 % of sample_input's and 0 %
   of Chardie's; on the six-lane bowling_video four lanes are found per frame (up to ten hypotheses)
   and the ball's lane is among them on 55 % of frames. Ablations: arrows alone find a lane on 13 %
   of tom_old frames at 3 boards (one depth cannot fix the far end), arrows + dots 13 %, arrows +
   rack 45 %, arrows + dots + rack 55 %; the gutters change the ranking, not the set. Every miss
   traces to the pool: no 5-of-7 arrow chain (arrows under the ball or below the mark threshold) or
   no rack blob on that frame.

5. **"Which face" is the open half of the finding problem.** The top-scoring constellation is the
   right lane on 40 % of tom_old's found frames and 1 % of sample_input's - the neighbouring lane,
   whose arrows the camera sees more squarely, scores higher; on bowling_video the ball's lane is
   the top score on 10 % of frames. The bowler's feet pick the right lane on 28 / 23 %, the frame
   centre on 29 / 0 %, the widest lane on 9 / 0 %. The constellation finds faces; choosing the
   bowler's face needs the bowler (or the ball) as an anchor, as loop 3 found for the student.

6. **Aligning the face does not beat finding it, because the near end has no detector.** From E3's
   lane the pins are refitted (loop 4's rack fit, 0.3-1.9 px per base) and the seven arrows are taken
   from the mark pool as a rigid pattern (7/7 on every frame tried); one weighted fit of the two
   fixes the far end (width error 2.0 -> 2.6 px on tom_old, 11.5 -> 4.3 on sample_input) and the
   pre-hit frame (tom_old 0.31 -> 0.25 boards vs pins) but not the throw median (0.62 -> 0.81 on
   tom_old, 1.73 -> 1.92 on sample_input), and the near corners stay 14 / 24 px (tom_old) and 12 /
   34 px (sample_input) from the annotation. Arrows at one depth plus a rack 45 ft further leave the
   near end's tilt free; the rows that would pin it (foul-line dots, guide dots) are the ones the
   classical pool does not hold on the handheld videos (finding 3), and gutter segments taken around
   a coarse lane pick the gutter lip or the next lane (dropping them was the fix, not weighting).
   Pooling the rack over the standing-pin frames (74 frames on tom_old) moves the throw median by
   under 0.05 boards: the per-frame rack noise loop 4 saw (0.4 boards) is not the limit here, the
   near end is. Dropping the pins (`rows-only`) is catastrophic (2.2 / 26 boards): the far end
   still comes only from the rack.

7. **Persistence works as a camera, not as a lane.** Matching the refined landmarks by name to the
   pre-hit frame gives a similarity on 185 of 187 tom_old frames (7 landmarks in common after the
   pins fall: the arrows carry it) and a lane on every frame at 0.81 boards vs pins - the same as
   the per-frame E4, since the carried points inherit its near end. On sample_input the landmark
   camera is worse than ORB (10.4 vs 4.2 px, max 138 vs 15): with only the arrows and a few
   pattern-matched dots the RANSAC similarity is fooled by one wrong row. Loop 4's version (17
   landmarks from a lane hypothesis) beat ORB; this one, fed from the pool, does not.

8. **Per-landmark heatmaps memorise the training videos' faces; per-class heatmaps learn what an
   arrow looks like.** Trained on sample_input + Chardie with random homographies on image and
   points (leave-one-video-out, best checkpoint on the training videos' held-back frames), the
   44-channel landmark model finds, on those training videos' frames, arrows 0.95-1.0 / guide dots
   0.93-0.99 / foul-line dots 0.6-0.94 / foul corners 1.0 / pins 1.0 within 6 px (2-4 px median) -
   and on held-out tom_old: pins 0.96, arrows 0.20, foul corners 0.06, guide dots 0.00, foul-line
   dots 0.00, at 74 ms per frame; the constellation fitted from its named points is 12.6 boards (it
   names the wrong arrows). Only the pins - a large white shape that looks the same on every lane -
   transfer; the small dark marks are recognised by where they sit in the two training videos'
   frames, loop 4's pose-head and arrow-class failure again, and exact homography augmentation did
   not change it. The 6-channel CLASS model (one heatmap per class, no identity) is the other way
   round: held-out arrows 0.92 recall at 3.7 px with 0.85 precision (the black-hat pool: 0.95 at
   5 % precision), pins 0.37 (the merged rack is not ten peaks), dots still 0.00. Appearance
   transfers, identity does not; the arrows' identity is the constellation's job (E3).

10. **Appearance model + constellation is the best prompt-free lane finder of the loop.** With the
   class model's arrow peaks as the mark pool (about nine marks per frame instead of 530), the same
   E3 finds the right lane on 56 % of held-out tom_old's throw frames at **0.43 boards vs the pins
   truth** (0.41 pre-hit, far width 1.5 px), the top score IS the right lane on every one of them,
   the frame centre picks it on 65 %, and a frame takes 14 ms instead of 995 - within 0.02 boards
   of loop 4's student + ten-pin refit (0.41), with no lane hypothesis, ball path or prompt. The
   landmark model's arrows give nothing (0 %). One fold, one held-out placement: the transfer is
   real but measured once.
9. **Two of the three truths' near ends are themselves in question, the third is confirmed.** The
   dot rows sit 0.4-0.7 in left of the lane centre under every truth, the arrows' depth differs by
   0.4 ft between videos, and the annotated foul-line ends are where every truth's near end comes
   from. On tom_old the visible lane edges at the foul line confirm the annotation to 1-2 px on both
   sides (`overlays/e4_corner_*`), so tom_old's near-end numbers are real; on sample_input and Chardie
   the foul ends could not be checked (bowler, ball return) and a near-end error of a board is
   possible in the truth itself.

## Recommendation for the engine

1. **Use the constellation to find lanes, the rack to fix the far end, and keep a near-end
   detector on the list.** Regularly spaced dark-mark chains + a rack blob find a lane with no ball
   path, mask or prompt on half of tom_old's frames at 0.6 boards (0.3 pre-hit) in ~1 s of Python;
   it is a detector-free lane proposal for the engine's first frames. Do not expect it at 720p.
2. **Anchor the choice of lane on the bowler or the ball, never on the score.** The best-scoring
   face is a neighbour on most frames of every multi-lane video.
3. **Do not ship a joint alignment from the black-hat pool.** Arrows + pins already give the far end;
   the near end needs the foul-line dots or the foul-line / gutter corner, which the pool does not
   contain on handheld 720p-1080p video. The mask student's near end (loop 4, 2-3 boards) is still
   the engine's best near end, and it is still the floor.
4. **Learn appearance, let the constellation assign identity.** A per-class heatmap (one channel
   for "arrow") transfers to a new placement (0.92 recall, 0.85 precision) where a per-landmark
   one memorises geometry (0.20); its arrows + E2's rack blobs + E3 give 0.43 boards at 14 ms per
   frame on the held-out video. That is the shape of a lane-landmark model for the engine: class
   heatmaps for arrows / dots / pins, the rule-book constellation for which is which. Five videos
   of one alley cannot teach the dots (0.00 held-out); the next data is other phones and angles.
5. **Re-measure before trusting a near-end number**: `results/constellation.json` carries the
   measured dot rows (0.4-0.7 in off the lane centre), `overlays/e4_corner_*` the edge check that
   confirms tom_old's annotation; on the other two videos the truths' near end is unverified.

## Blocked / negative results

- **Chardie (720p) is invisible to the classical pool**: 2 of 5 arrows resolvable, no dots, no lane
  found on any frame by any feature set. Loop 4 found 5/7 arrows there only with the annotation's
  rectification; with no lane prior the marks are below the black-hat floor.
- **Arrows alone cannot find a lane** (13 % of tom_old frames, 3 boards): one depth. Arrows + dots
  without a rack is no better (13 %) because the dot rows are rarely in the pool; the rack is what
  makes the face findable (45-55 %).
- **Gutter segments and near corners from a coarse lane hurt** (sample_input near end 36-48 px until
  they were dropped); the gutter's two edges are 9 in apart and a coarse lane cannot tell them
  apart.
- **Rectified-band dot refinement mis-assigns by a whole pitch** under a coarse lane (foul-line dots
  74-124 px off on sample_input); the rigid pattern search in the image replaced it.
- **Heatmap landmark model**: transfers the pins only (finding 8); the class variant and the other
  two folds are reported in the E6 table as they land.
- **The rack blob detector misses 34 % of tom_old's standing-pin frames** (the ball or the bowler
  merges into or splits the white mass); E3's misses on tom_old are those frames plus frames with
  fewer than five arrow marks in the pool.
- **Range-finder dots**: still visible on no video. The approach dots at -11.7 ft are visible on
  Chardie only; the guide dots at 7 ft on tom_old only (sample_input's 7-ft band is glare).

## Reproducing

```
V=~/code/bowling-app/analysis-engine/.venv/bin/python
export AF_SCRATCH=<scratch>       # frames/ (copy loop 4's or extract with loop 1's gt.extract_frames + loop 3's common.extract_unlabeled), pred/, ds/, runs/
cd docs/research/2026-09-14-alley-face
$V e1_inspect.py; $V e1_constellation.py; $V e1_timeline.py          # constellation.json, landmarks_<stem>.json, e1_timeline_*, overlays/e1_*
$V e2_candidates.py                                                    # cand_<stem>.json.gz in $AF_SCRATCH/pred, results/e2_candidates_*
$V e3_face.py --sets arrows+dots+rack+gutters                          # all five videos; results/e3_face_<stem>.json, overlays/e3_face_*
$V e3_face.py --tag ablate --sets arrows,arrows+dots,arrows+rack,arrows+dots+rack --step 5 tom_old sample_input 20260112_121117
$V e4_align.py; $V e5_persist.py; $V e4_align.py; $V e5_persist.py     # second pass uses the rack pooled by E5
$V e6_heatmap.py build; $V e6_heatmap.py train lovo_tom_old landmark 2500; $V e6_heatmap.py train lovo_tom_old class 2500
for st in sample_input 20260112_121117 tom_old; do $V e6_heatmap.py predict lovo_tom_old landmark $st; done; $V e6_eval.py lovo_tom_old
$V tables.py; $V fill_readme.py; $V video_script.py; $V review_face.py
```
