# Do more lane landmarks make the board number more accurate? (2026-09-13)

Status: complete. Review video: `review.mp4` (gitignored; regenerate with the commands at the
end). Scripts, result JSON (`results/`) and overlays (`overlays/`) are in this folder; frames,
datasets, training runs and per-frame detections live in the session scratchpad (`LM_SCRATCH`).
Nothing in the earlier loops' folders was edited. The per-frame E3 files are committed gzipped
(`results/e3_fit_*.json.gz`; `common.load` and `common.has_result` read either form).

## The question

Loops 1-3 fit the lane from **four corners**: two edge lines evaluated at the foul line and the
pin deck. Every remaining error was at the far end, where a board is 1-2 px, and loop 2 showed the
hand-clicked corners themselves are off there (tom_old ~5 px, Chardie ~2 px), so every number was
measured against a truth that is wrong by 1-3 boards at the pins. A lane has landmarks whose
position is fixed by the rules: the foul line (0 ft, boards 1 and 39), seven arrows (~15 ft, boards
5 · 10 · 15 · 20 · 25 · 30 · 35), and ten pin bases (60-62.6 ft, 12 in apart, 7-pin to 10-pin 36 in
on a 41.5 in lane). This loop asks (E1) whether those landmarks give a better truth than the hand
corners, (E2) whether they can be detected at inference time from a rough lane, (E3) whether a
homography fitted to all of them beats the four-corner fit, most of all at the far end, and (E4)
whether the static landmarks make a better per-frame camera model than ORB on the whole frame.

Metric, unchanged from loops 1-3 (`../2026-09-12-sam2-lane-experiments/lane_sam.py::score`): the
annotated ball path (warped into the frame) is mapped to boards through the predicted homography
and through the truth's, board MAE is the mean absolute difference. New here: **every number is
reported against three truths** - `annotated` (the hand corners, loops 1-3), `pins` (E1's
pins-based far end on the annotated foul-line ends) and `all` (E1's fit through foul ends, all ten
pin bases and the arrows) - plus the error over the last 20 % of the path (the pin end).

## Data

The three annotated videos of loops 1-3 (`sample_input` 1080p handheld with hand corners on every
frame; `Chardie` 720p handheld; `tom_old` 688p tripod, closest camera), the same frames, ball
annotations and camera models (`../2026-09-12-cheap-lane-model/results/camera_all_*.json`). No new
video and no new clicks: the landmark truth is detected (E1), checked in overlays, and correctable
later with `click_landmarks.py <stem> <frame>` (writes `source: clicked` into
`results/landmarks_<stem>.json`).

What is visible (`overlays/inspect_*.jpg`, `e1_*`): all ten pins stand cleanly on every video's
pre-hit frames; the seven arrows are plain dark inlays on the rectified lane on all three (a V
with the centre arrow ~15.4-15.8 ft down and 0.4-0.5 ft per 5 boards); the 7-ft guide dots show on
tom_old only; range-finder dots (34-44 ft) are visible on none.

## Method

- **E1 truth** (`landmarks.py`, `e1_truth.py`). Pins: the ten bases at their rule-book lane
  coordinates are projected through the annotated quad (top edge assumed at the head-pin row) and
  a similarity (shift + scale about the rack centre) is searched so that a matched filter - white
  along each body axis, dark in the 6-in gaps and above the pin tops - peaks; then each column is
  refined to its intensity centroid. Two independent widths agree to ~1 px on every video (7-10
  base spacing × 41.5/36, and the outer edges of pins 7 and 10 at belly height × 41.5/40.77).
  Arrows: the annotated quad rectifies the lane to 10 px per board, dark blobs in the 9-19 ft band
  are assigned to the seven nominal boards (±2.5 boards) and filtered by the V (mirror arrows at
  the same depth). Foul-line ends: the annotated bottom corners. Repeated on pre-hit −2/−4/−6.
- **Pins truth**: centre = rack centre, width = 7-10 spacing × 41.5/36 at the back-row base;
  edge lines through the annotated foul-line ends; corners at the annotated rows. Stored as
  fractions along the annotated top edge so it applies to every frame's quad without a camera
  warp (`common.truth_corners(stem, f, "pins"|"all")`). **All-landmark truth**: weighted DLT
  through the foul ends (2D), all ten pin bases (2D) and the arrows (x-only, point-on-board-line).
- **Re-scoring** (`rescore_baselines.py`): loop 2's SAM rows carry corners; loop 3's per-frame
  rows carry only corner distances and widths, so the corners are rebuilt (corners sit on the
  annotated rows, so each error is ±dx; the sign pattern is the one that reproduces the stored
  widths and MAE; ambiguous frames skipped).
- **E2 detectors** (`e2_detect.py`): from a lane hypothesis on every frame (loop 3's gated student
  corners; also its +teacher and 1024 px variants and loop 2's SAM single frames): pins = the same
  rack fit initialised from the hypothesis (coarse grid, ±0.12 lane widths, alias check against a
  one-column shift), arrows = the same blob detector on the hypothesis-rectified lane, foul ends =
  the hypothesis' bottom corners. Scored against the E1 landmarks projected into each frame.
- **E3 fit** (`e3_fit.py`): weighted DLT per frame, weights = 1 / expected precision in lane
  inches (foul ends 1.0 in, far corners 3 in, arrows 0.7 in, pins 0.45 in), constraints with
  residual > 2.5 in dropped (never the last depth anchor). Two passes: after a corners+pins fit the
  arrows are re-detected from the corrected lane. Pins are used while they stand; after the hit
  they are carried through the ORB camera model (`+carry`) or a similarity on the arrows seen on
  both frames (`+carryLM`). Variants are named by their constraint sets; `drop-<landmark>` leaves
  one out.
- **E4** (`e4_camera.py`): E2's arrows (+ pin bases while standing) matched to the same landmarks
  on the first frame, RANSAC similarity per frame; on sample_input both models carry the hand
  corners of frame 0 onto every frame and are judged against that frame's hand corners.
- **Learned arrows** (`build_dataset_lm.py`, `train_lm.py`, `eval_seg2.py`): yolo11n-seg with two
  classes (lane polygon + arrow boxes from the E1 landmarks projected into every frame), LOVO, 640
  and 1024 px, MPS.

## Results

### E1 - the truth from the physical landmarks (pre-hit frame; hand vs pins vs all)

<!-- TABLE:e1 -->
| video | px/board at pins | far width px: hand / pins / all | far centre px: hand / pins / all | hand TL, TR vs pins (px = boards) | annotated quad MAE vs pins (tail) | vs all (tail) | arrows found, abs err boards hand / pins | pins vs arrows agreement (all-fit resid, in) | repeatability over 3 frames (centre px std, width ratio std) |
|---|---|---|---|---|---|---|---|---|---|
| sample_input f117 | 1.56 | 59.4 / 54.0 / 54.5 | 548.7 / 547.3 / 547.3 | -1.4 = -0.9, +4.1 = +2.6 | 0.68 (1.07) | 0.65 (1.05) | 7/7, 0.33 / 0.18 | arrows 0.14, pins 0.37 | 0.1, 0.0039 |
| Chardie f132 | 1.01 | 38.5 / 36.8 / 37.4 | 424.7 / 426.4 / 425.8 | -2.6 = -2.6, -1.2 = -1.2 | 0.58 (1.09) | 0.34 (0.64) | 5/7, 0.29 / 0.5 | arrows 0.57, pins 0.45 | 0.29, 0.0008 |
| tom_old f169 | 1.68 | 63.9 / 68.2 / 67.8 | 528.9 / 532.8 / 532.9 | -2.8 = -1.7, -6.0 = -3.6 | 1.46 (2.36) | 1.5 (2.44) | 7/7, 0.31 / 0.26 | arrows 0.26, pins 0.38 | 0.49, 0.0085 |
<!-- /TABLE:e1 -->

Reading it: the hand-clicked far end is **10 % too wide on sample_input and 4 % too wide on
Chardie** (the flat gutters at the pin deck look like lane), **7 % too narrow and 4 px left on
tom_old**; the centre is 1.4 px right / 1.7 px left / 3.9 px left of the pin rack. The arrows,
detected without any use of the pins, agree with the pins-based truth better than with the hand
corners on sample_input (0.18 vs 0.33 boards mean abs error at 15 ft) and tom_old (0.26 vs 0.31)
and slightly worse on Chardie (0.50 vs 0.29 with 5 of 7 arrows at 720p); under one homography
through foul ends, pins and arrows the residuals are 0.14-0.57 in for the arrows and 0.37-0.45 in
for the pins, i.e. the two rulers agree to about one pixel at the far end. The detector repeats to
0.1-0.5 px in centre and 0.1-0.9 % in width over three standing-pin frames. The hand annotation
scores 0.68 / 0.58 / 1.46 boards against the pins truth (1.07 / 1.09 / 2.36 on the pin-end tail):
that is the size of the error every earlier loop was measured against.

### Baselines of loops 2-3 re-scored in all three truths

<!-- TABLE:baselines -->
| method | video | frame(s) | MAE vs annotated | vs pins | vs all landmarks | tail (last 20 % of path) vs pins | far width err px vs pins | far centre err px vs pins |
|---|---|---|---|---|---|---|---|---|
| SAM 2 base, even3 ball-path prompts (loop 2) pre-hit | sample_input | f117 | 0.31 | 0.48 | 0.46 | 0.99 | -0.4 | +1.6 |
| SAM 2 base, even3 ball-path prompts (loop 2) pre-hit | Chardie | f132 | 0.68 | 0.49 | 0.39 | 0.16 | -3.2 | +1.1 |
| SAM 2 base, even3 ball-path prompts (loop 2) pre-hit | tom_old | f169 | 2.26 | 0.73 | 0.69 | 1.42 | -6.9 | +2.9 |
| SAM 2 base, even3 ball-path prompts (loop 2) last | sample_input | f128 | 0.25 | 0.42 | 0.41 | 0.91 | -2.2 | +1.5 |
| SAM 2 base, even3 ball-path prompts (loop 2) last | Chardie | f170 | 0.39 | 0.81 | 0.54 | 0.63 | -3.2 | +0.7 |
| SAM 2 base, even3 ball-path prompts (loop 2) last | tom_old | f171 | 1.19 | 0.42 | 0.46 | 0.25 | -5.6 | +0.1 |
| SAM 2 base, far-end crop zoom_lo (loop 2) pre-hit | sample_input | f117 | 0.89 | 0.15 | 0.17 | 0.15 | +1.3 | -0.5 |
| SAM 2 base, far-end crop zoom_lo (loop 2) pre-hit | Chardie | f132 | 0.37 | 0.89 | 0.62 | 0.82 | -1.3 | -0.1 |
| SAM 2 base, far-end crop zoom_lo (loop 2) pre-hit | tom_old | f169 | 1.87 | 0.33 | 0.29 | 0.7 | -6.7 | +1.7 |
| SAM 2 base, far-end crop zoom_lo (loop 2) last | sample_input | f128 | 0.7 | 0.14 | 0.14 | 0.1 | -1.0 | -0.2 |
| SAM 2 base, far-end crop zoom_lo (loop 2) last | Chardie | f170 | 0.31 | 0.97 | 0.7 | 1.01 | -1.2 | -0.1 |
| SAM 2 base, far-end crop zoom_lo (loop 2) last | tom_old | f171 | 0.51 | 1.16 | 1.2 | 1.66 | -1.4 | -2.6 |
| SAM 2 + pin centre pins_m (loop 2) pre-hit | sample_input | f117 | 0.2 | 0.55 | 0.53 | 0.86 | +8.1 | +0.5 |
| SAM 2 + pin centre pins_m (loop 2) pre-hit | Chardie | f132 | 0.9 | 0.33 | 0.45 | 0.28 | +1.3 | +0.6 |
| SAM 2 + pin centre pins_m (loop 2) pre-hit | tom_old | f169 | 0.62 | 0.93 | 0.96 | 1.57 | -6.9 | -2.1 |
| SAM 2 pose+pin landmark prompts (loop 2) pre-hit | sample_input | f117 | 0.39 | 0.37 | 0.35 | 0.71 | +1.5 | +0.9 |
| SAM 2 pose+pin landmark prompts (loop 2) pre-hit | Chardie | f132 | 0.88 | 0.4 | 0.46 | 0.42 | -2.8 | +1.4 |
| SAM 2 pose+pin landmark prompts (loop 2) pre-hit | tom_old | f169 | 2.39 | 0.85 | 0.81 | 1.58 | -4.9 | +3.2 |
| student seg640 gated (loop 3) throw median | sample_input | 180 frames | 1.83 | 1.19 | 1.21 | 2.68 | +10.6 | -6.1 |
| student seg640 gated (loop 3) pre-hit / last | sample_input | pre-hit / last | 1.59 / 2.11 | 0.91 / 1.58 | 0.93 / 1.59 | | | |
| student seg640 gated (loop 3) throw median | Chardie | 162 frames | 0.88 | 0.64 | 0.52 | 0.62 | +5.7 | -0.5 |
| student seg640 gated (loop 3) pre-hit / last | Chardie | pre-hit / last | 0.96 / 1.29 | 0.35 / 0.57 | 0.5 / 0.79 | | | |
| student seg640 gated (loop 3) throw median | tom_old | 406 frames | 3.15 | 1.61 | 1.57 | 1.96 | +4.2 | +4.8 |
| student seg640 gated (loop 3) pre-hit / last | tom_old | pre-hit / last | 3.29 / 1.89 | 1.76 / 0.35 | 1.72 / 0.31 | | | |
| student seg640 +teacher gated (loop 3) throw median | sample_input | 153 frames | 1.18 | 0.51 | 0.52 | 0.79 | +8.7 | -1.8 |
| student seg640 +teacher gated (loop 3) pre-hit / last | sample_input | pre-hit / last | 0.99 / 1.08 | 0.28 / 0.53 | 0.29 / 0.53 | | | |
| student seg640 +teacher gated (loop 3) throw median | Chardie | 139 frames | 0.95 | 0.65 | 0.57 | 0.41 | +2.5 | +0.1 |
| student seg640 +teacher gated (loop 3) pre-hit / last | Chardie | pre-hit / last | 0.82 / 0.61 | 0.4 / 0.58 | 0.42 / 0.34 | | | |
| student seg640 +teacher gated (loop 3) throw median | tom_old | 405 frames | 3.16 | 1.62 | 1.58 | 2.25 | +1.7 | +4.8 |
| student seg640 +teacher gated (loop 3) pre-hit / last | tom_old | pre-hit / last | 3.13 / 1.79 | 1.6 / 0.26 | 1.56 / 0.22 | | | |
| student seg1024 gated (loop 3, tom_old only) throw median | tom_old | 291 frames | 0.91 | 0.64 | 0.68 | 1.27 | +2.7 | -1.9 |
| student seg1024 gated (loop 3, tom_old only) pre-hit / last | tom_old | pre-hit / last | None / 0.33 | None / 1.87 | None / 1.9 | | | |
<!-- /TABLE:baselines -->

### E2 - detecting the landmarks from a rough lane

<!-- TABLE:e2 -->
| lane hypothesis | video | frames | pins: fired / standing | pins px err (median) | pin centre err (boards, med) | pin span err (boards, med) | alias frames (>3 boards) | arrows correct / frame | false / frame | arrow recall | arrow dx (boards, med) | ms pins / arrows |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| student seg640 gated (loop 3) | sample_input | 180 | 119 / 119 | 1.44 | 0.56 | 1.47 | 0 | 4.73 | 1.03 | 0.68 | 0.64 | 709 / 57 |
| student seg640 gated (loop 3) | Chardie | 162 | 120 / 126 | 0.81 | 0.69 | 0.14 | 6 | 5.04 | 0.48 | 0.72 | 0.77 | 617 / 51 |
| student seg640 gated (loop 3) | tom_old | 406 | 167 / 168 | 1.41 | 0.36 | 0.63 | 6 | 6.54 | 0.01 | 0.93 | 0.61 | 700 / 43 |
| student +teacher (loop 3) | sample_input | 153 | 92 / 92 | 1.37 | 0.68 | 0.50 | 0 | 5.48 | 1.31 | 0.78 | 0.63 | 706 / 64 |
| student +teacher (loop 3) | Chardie | 139 | 99 / 105 | 0.59 | 0.38 | 0.17 | 5 | 5.12 | 0.47 | 0.73 | 0.67 | 578 / 45 |
| student +teacher (loop 3) | tom_old | 405 | 168 / 169 | 1.42 | 0.36 | 0.63 | 6 | 6.60 | 0.01 | 0.94 | 0.61 | 701 / 44 |
| student 1024 (loop 3) | tom_old | 291 | 110 / 111 | 1.44 | 0.36 | 0.62 | 4 | 6.53 | 0.01 | 0.93 | 0.61 | 704 / 39 |
| two-class student 1024 (this loop) | tom_old | 409 | 169 / 171 | 1.43 | 0.36 | 0.63 | 7 | 6.36 | 0.08 | 0.91 | 0.61 | 699 / 36 |
| SAM 2 even3 (loop 2, 2 frames) | sample_input | 2 | 1 / 1 | 0.56 | 0.02 | 0.40 | 0 | 7.00 | 0.00 | 1.00 | 0.28 | 716 / 51 |
| SAM 2 even3 (loop 2, 2 frames) | Chardie | 2 | 1 / 1 | 0.46 | 0.26 | 0.15 | 0 | 6.50 | 0.00 | 0.93 | 0.46 | 455 / 50 |
| SAM 2 even3 (loop 2, 2 frames) | tom_old | 2 | 1 / 1 | 0.74 | 0.28 | 0.55 | 0 | 3.50 | 0.00 | 0.50 | 0.61 | 740 / 33 |
| SAM 2 crop (loop 2, 2 frames) | sample_input | 2 | 1 / 1 | 0.55 | 0.02 | 0.40 | 0 | 7.00 | 0.00 | 1.00 | 0.28 | 720 / 48 |
| SAM 2 crop (loop 2, 2 frames) | Chardie | 2 | 0 / 1 | - | - | - | 1 | 6.50 | 0.00 | 0.93 | 0.45 | 440 / 47 |
| SAM 2 crop (loop 2, 2 frames) | tom_old | 2 | 1 / 1 | 0.76 | 0.28 | 0.53 | 0 | 3.50 | 0.00 | 0.50 | 0.61 | 757 / 36 |
<!-- /TABLE:e2 -->

Learned arrows: the two-class student (`seg2_*`, lane polygon + seven arrow boxes) detects
**zero** arrows on any frame of held-out tom_old at 640 px (an arrow is ~6 px there) **and at
1024 px** (~10 px; `seg2_1024_lovo_tom_old`, batch 4, `results/seg2_seg2_1024_lovo_tom_old__tom_old.json`).
Its lane class is unaffected: 3.15 / 1.75 boards median (annotated / pins) at 640 px, loop 3's
number - and at 1024 px **1.34 / 0.26 boards on every one of the 409 frames** (conf median 0.78,
71 ms), where loop 3's one-class 1024 model fired on 60 frames and scored 0.91 / 0.64. Not the same
recipe (batch 4 = four times the steps, no horizontal flip, a second class), so the cause is not
isolated; it is the best per-frame lane on tom_old in the four loops and is used below as a lane
source (`seg2_1024`). The other 1024 folds and two 640 folds crashed in ultralytics' task-aligned
assigner on MPS (`tal.py::get_box_metrics`: `index N is out of bounds`, `shape mismatch`) with the
eight-instance labels at batch 8 and 16, on every retry; mosaic off trained (see Blocked).

### E3 - one homography from all the landmarks (loop 3's student lane as the only input)

Throw median over the same frames as loop 3 (5 before release to the last on-lane ball frame);
`corners` is the source lane itself and reproduces the re-scored loop 3 row.

<!-- TABLE:e3_loop3 -->
| variant (loop3) | video | frames ok | throw median: annotated / pins / all | tail (last 20 %) pins | pre-hit pins | last pins | far width err px (pins, med) | far centre err px (pins, med abs) |
|---|---|---|---|---|---|---|---|---|
| corners | sample_input | 82 | 1.83 / 1.19 / 1.21 | 2.68 | 0.91 | 1.58 | 12.2 | 6.1 |
| snapcorners | sample_input | 82 | 2.72 / 1.97 / 1.99 | 2.86 | 1.72 | 2.33 | 12.2 | 6.1 |
| corners+arrows | sample_input | 82 | 2.15 / 1.50 / 1.52 | 3.04 | 1.27 | 1.12 | -4.5 | 3.9 |
| corners+pins | sample_input | 82 | 0.71 / 0.41 / 0.41 | 0.46 | 0.50 | 1.58 | 1.6 | 0.8 |
| corners+pins10 | sample_input | 82 | 0.77 / 0.37 / 0.37 | 0.46 | 0.48 | 1.58 | 0.7 | 0.7 |
| corners+arrows+pins10 | sample_input | 82 | 0.89 / 0.31 / 0.32 | 0.61 | 0.22 | 1.12 | 0.1 | 0.8 |
| foul+arrows+pins10 | sample_input | 81 | 0.88 / 0.31 / 0.32 | 0.61 | 0.22 | - | 0.1 | 0.8 |
| arrows+pins10 | sample_input | 81 | 1.10 / 0.40 / 0.42 | 0.62 | 0.05 | - | 0.7 | 0.7 |
| arrows+pins10+weakfoul | sample_input | 81 | 1.02 / 0.33 / 0.35 | 0.62 | 0.07 | - | -0.4 | 0.7 |
| arrows+pins10+top | sample_input | 81 | 1.10 / 0.40 / 0.41 | 0.62 | 0.05 | - | 0.7 | 0.7 |
| snapfoul+pins10 | sample_input | 81 | 1.66 / 0.98 / 1.00 | 0.85 | 0.66 | - | -1.6 | 0.7 |
| snapfoul+arrows+pins10 | sample_input | 81 | 1.34 / 0.63 / 0.65 | 0.63 | 0.31 | - | -1.0 | 0.7 |
| corners+arrows+pins10+carry | sample_input | 82 | 0.89 / 0.31 / 0.32 | 0.61 | 0.22 | - | 0.1 | 0.8 |
| corners+arrows+pins10+carryLM | sample_input | 82 | 0.89 / 0.31 / 0.32 | 0.61 | 0.22 | - | 0.1 | 0.8 |
| corners+arrows(1pass) | sample_input | 82 | 1.84 / 1.22 / 1.24 | 2.51 | 1.00 | 1.12 | -1.6 | 3.5 |
| foul+arrows+pins(1pass) | sample_input | 81 | 0.94 / 0.36 / 0.37 | 0.76 | 0.28 | - | 0.3 | 1.0 |
| corners | Chardie | 70 | 0.88 / 0.64 / 0.51 | 0.62 | 0.35 | 0.57 | 6.2 | 1.0 |
| snapcorners | Chardie | 70 | 0.95 / 0.49 / 0.49 | 0.56 | 0.33 | 0.60 | 6.2 | 1.0 |
| corners+arrows | Chardie | 70 | 0.75 / 0.71 / 0.56 | 0.68 | 0.50 | 0.38 | 2.8 | 1.1 |
| corners+pins | Chardie | 70 | 0.52 / 0.77 / 0.56 | 0.60 | 0.69 | 0.57 | -0.2 | 0.2 |
| corners+pins10 | Chardie | 70 | 0.53 / 0.78 / 0.52 | 0.63 | 0.67 | 0.57 | 0.1 | 0.2 |
| corners+arrows+pins10 | Chardie | 70 | 0.51 / 0.77 / 0.53 | 0.62 | 0.66 | 0.38 | 0.1 | 0.2 |
| foul+arrows+pins10 | Chardie | 62 | 0.50 / 0.75 / 0.49 | 0.56 | 0.66 | - | 0.1 | 0.2 |
| arrows+pins10 | Chardie | 60 | 0.50 / 0.72 / 0.46 | 0.57 | 0.55 | - | 0.0 | 0.1 |
| arrows+pins10+weakfoul | Chardie | 62 | 0.49 / 0.79 / 0.53 | 0.64 | 0.66 | - | 0.1 | 0.2 |
| arrows+pins10+top | Chardie | 60 | 0.50 / 0.72 / 0.46 | 0.57 | 0.55 | - | 0.0 | 0.1 |
| snapfoul+pins10 | Chardie | 62 | 0.55 / 0.51 / 0.42 | 0.54 | 0.65 | - | 0.5 | 0.2 |
| snapfoul+arrows+pins10 | Chardie | 62 | 0.52 / 0.60 / 0.41 | 0.55 | 0.66 | - | 0.3 | 0.2 |
| corners+arrows+pins10+carry | Chardie | 70 | 0.51 / 0.76 / 0.53 | 0.54 | 0.66 | 0.83 | 0.1 | 0.2 |
| corners+arrows+pins10+carryLM | Chardie | 70 | 0.51 / 0.77 / 0.53 | 0.65 | 0.66 | 0.86 | 0.1 | 0.2 |
| corners+arrows(1pass) | Chardie | 70 | 0.78 / 0.73 / 0.56 | 0.69 | 0.49 | 0.38 | 2.9 | 1.1 |
| foul+arrows+pins(1pass) | Chardie | 62 | 0.55 / 0.72 / 0.47 | 0.53 | 0.64 | - | -0.1 | 0.2 |
| corners | tom_old | 151 | 3.15 / 1.61 / 1.57 | 1.96 | 1.76 | 0.35 | 3.4 | 4.1 |
| snapcorners | tom_old | 151 | 2.69 / 1.18 / 1.14 | 1.96 | 1.26 | 0.33 | 3.4 | 4.1 |
| corners+arrows | tom_old | 151 | 0.45 / 1.77 / 1.80 | 3.45 | 1.75 | 0.35 | -1.1 | 6.0 |
| corners+pins | tom_old | 151 | 1.63 / 0.37 / 0.38 | 0.53 | 0.38 | 0.35 | 2.2 | 0.7 |
| corners+pins10 | tom_old | 151 | 1.51 / 0.41 / 0.43 | 0.71 | 0.51 | 0.35 | 1.1 | 1.0 |
| corners+arrows+pins10 | tom_old | 151 | 1.23 / 0.41 / 0.44 | 0.90 | 0.15 | 0.35 | 1.0 | 1.4 |
| foul+arrows+pins10 | tom_old | 143 | 1.23 / 0.41 / 0.44 | 0.90 | 0.15 | - | 1.0 | 1.4 |
| arrows+pins10 | tom_old | 143 | 1.24 / 0.30 / 0.34 | 0.58 | 0.19 | - | 1.1 | 0.7 |
| arrows+pins10+weakfoul | tom_old | 143 | 1.09 / 0.44 / 0.48 | 0.78 | 0.12 | - | 0.6 | 1.1 |
| arrows+pins10+top | tom_old | 143 | 1.24 / 0.30 / 0.33 | 0.57 | 0.19 | - | 1.1 | 0.7 |
| snapfoul+pins10 | tom_old | 143 | 1.01 / 0.58 / 0.62 | 0.77 | 0.14 | - | 0.7 | 1.1 |
| snapfoul+arrows+pins10 | tom_old | 143 | 1.05 / 0.51 / 0.55 | 0.73 | 0.14 | - | 0.6 | 1.0 |
| corners+arrows+pins10+carry | tom_old | 151 | 1.23 / 0.41 / 0.44 | 0.90 | 0.15 | 0.31 | 0.9 | 1.3 |
| corners+arrows+pins10+carryLM | tom_old | 151 | 1.23 / 0.41 / 0.44 | 0.90 | 0.15 | 0.35 | 1.0 | 1.4 |
| corners+arrows(1pass) | tom_old | 151 | 0.44 / 1.77 / 1.80 | 3.46 | 1.75 | 0.35 | -1.0 | 6.0 |
| foul+arrows+pins(1pass) | tom_old | 143 | 0.98 / 0.65 / 0.68 | 1.38 | 0.51 | - | 1.1 | 2.3 |
| dropped landmark (loop3, foul+arrows+pins base) | sample_input throw median (pins) / tail | Chardie throw median (pins) / tail | tom_old throw median (pins) / tail |
|---|---|---|---|
| foul+arrows+pins | 0.39 / 0.84 | 0.74 / 0.56 | 0.65 / 1.38 |
| foul+arrows+pins10 | 0.31 / 0.61 | 0.75 / 0.56 | 0.41 / 0.90 |
| drop-arrow_5 | 0.35 / 0.72 | 0.74 / 0.56 | 0.60 / 1.30 |
| drop-arrow_10 | 0.36 / 0.77 | 0.72 / 0.56 | 0.60 / 1.30 |
| drop-arrow_15 | 0.38 / 0.80 | 0.74 / 0.56 | 0.61 / 1.30 |
| drop-arrow_20 | 0.38 / 0.83 | 0.72 / 0.54 | 0.62 / 1.32 |
| drop-arrow_25 | 0.39 / 0.85 | 0.72 / 0.56 | 0.63 / 1.33 |
| drop-arrow_30 | 0.39 / 0.86 | 0.72 / 0.56 | 0.64 / 1.35 |
| drop-arrow_35 | 0.39 / 0.86 | 0.74 / 0.57 | 0.65 / 1.37 |
| drop-pin_7 | 0.31 / 0.60 | 0.75 / 0.56 | 0.42 / 0.93 |
| drop-pin_10 | 0.33 / 0.65 | 0.75 / 0.55 | 0.43 / 0.94 |
<!-- /TABLE:e3_loop3 -->

Same fits on loop 3's other lanes and on loop 2's SAM single frames:

<!-- TABLE:e3_loop3_plus -->
| variant (loop3_plus) | video | frames ok | throw median: annotated / pins / all | tail (last 20 %) pins | pre-hit pins | last pins | far width err px (pins, med) | far centre err px (pins, med abs) |
|---|---|---|---|---|---|---|---|---|
| corners | sample_input | 75 | 1.18 / 0.51 / 0.52 | 0.79 | 0.28 | 0.53 | 9.8 | 2.0 |
| snapcorners | sample_input | 75 | 1.49 / 0.80 / 0.82 | 0.84 | 0.53 | 0.79 | 9.8 | 2.0 |
| corners+arrows | sample_input | 75 | 0.62 / 0.40 / 0.40 | 0.48 | 0.55 | 0.47 | 3.3 | 0.9 |
| corners+pins | sample_input | 75 | 1.18 / 0.47 / 0.49 | 0.55 | 0.17 | 0.53 | 1.4 | 0.7 |
| corners+pins10 | sample_input | 75 | 1.20 / 0.51 / 0.52 | 0.58 | 0.17 | 0.53 | 0.5 | 0.7 |
| corners+arrows+pins10 | sample_input | 75 | 1.08 / 0.40 / 0.42 | 0.53 | 0.08 | 0.47 | 0.6 | 0.7 |
| foul+arrows+pins10 | sample_input | 74 | 1.08 / 0.40 / 0.42 | 0.53 | 0.08 | - | 0.6 | 0.7 |
| arrows+pins10 | sample_input | 74 | 1.10 / 0.41 / 0.43 | 0.64 | 0.04 | - | 0.7 | 0.7 |
| arrows+pins10+weakfoul | sample_input | 74 | 1.04 / 0.34 / 0.36 | 0.55 | 0.04 | - | 0.6 | 0.7 |
| arrows+pins10+top | sample_input | 74 | 1.10 / 0.41 / 0.42 | 0.64 | 0.03 | - | 0.7 | 0.8 |
| snapfoul+pins10 | sample_input | 74 | 1.55 / 0.84 / 0.86 | 0.72 | 0.49 | - | -0.5 | 0.8 |
| snapfoul+arrows+pins10 | sample_input | 74 | 1.23 / 0.55 / 0.56 | 0.55 | 0.21 | - | 0.1 | 0.7 |
| corners+arrows+pins10+carry | sample_input | 75 | 1.08 / 0.40 / 0.42 | 0.52 | 0.08 | 1.72 | 0.5 | 0.7 |
| corners+arrows+pins10+carryLM | sample_input | 75 | 1.08 / 0.40 / 0.42 | 0.53 | 0.08 | 0.38 | 0.5 | 0.7 |
| corners+arrows(1pass) | sample_input | 75 | 0.61 / 0.41 / 0.40 | 0.48 | 0.54 | 0.47 | 3.4 | 1.0 |
| foul+arrows+pins(1pass) | sample_input | 74 | 1.03 / 0.34 / 0.35 | 0.42 | 0.13 | - | 0.7 | 0.5 |
| corners | Chardie | 72 | 0.95 / 0.65 / 0.57 | 0.41 | 0.39 | 0.58 | 3.2 | 0.5 |
| snapcorners | Chardie | 72 | 0.95 / 0.64 / 0.55 | 0.47 | 0.36 | 0.41 | 3.2 | 0.5 |
| corners+arrows | Chardie | 72 | 0.86 / 0.66 / 0.59 | 0.61 | 0.46 | 0.42 | 2.3 | 1.1 |
| corners+pins | Chardie | 72 | 0.54 / 0.85 / 0.61 | 0.67 | 0.74 | 0.58 | -0.3 | 0.2 |
| corners+pins10 | Chardie | 72 | 0.55 / 0.82 / 0.58 | 0.64 | 0.71 | 0.58 | 0.1 | 0.2 |
| corners+arrows+pins10 | Chardie | 72 | 0.55 / 0.81 / 0.56 | 0.62 | 0.66 | 0.42 | 0.2 | 0.2 |
| foul+arrows+pins10 | Chardie | 64 | 0.52 / 0.78 / 0.52 | 0.59 | 0.66 | - | 0.2 | 0.2 |
| arrows+pins10 | Chardie | 62 | 0.49 / 0.71 / 0.44 | 0.56 | 0.56 | - | 0.0 | 0.2 |
| arrows+pins10+weakfoul | Chardie | 64 | 0.50 / 0.77 / 0.52 | 0.61 | 0.66 | - | 0.2 | 0.2 |
| arrows+pins10+top | Chardie | 62 | 0.49 / 0.71 / 0.44 | 0.56 | 0.56 | - | 0.0 | 0.2 |
| snapfoul+pins10 | Chardie | 64 | 0.56 / 0.64 / 0.48 | 0.53 | 0.70 | - | 0.7 | 0.2 |
| snapfoul+arrows+pins10 | Chardie | 64 | 0.53 / 0.69 / 0.45 | 0.53 | 0.68 | - | 0.6 | 0.2 |
| corners+arrows+pins10+carry | Chardie | 72 | 0.54 / 0.79 / 0.56 | 0.55 | 0.66 | 0.89 | 0.2 | 0.2 |
| corners+arrows+pins10+carryLM | Chardie | 72 | 0.54 / 0.81 / 0.56 | 0.63 | 0.66 | 0.88 | 0.2 | 0.2 |
| corners+arrows(1pass) | Chardie | 72 | 0.89 / 0.67 / 0.58 | 0.52 | 0.48 | 0.42 | 2.5 | 1.0 |
| foul+arrows+pins(1pass) | Chardie | 64 | 0.57 / 0.77 / 0.52 | 0.51 | 0.64 | - | 0.1 | 0.3 |
| corners | tom_old | 152 | 3.16 / 1.62 / 1.58 | 2.25 | 1.60 | 0.26 | 1.3 | 4.6 |
| snapcorners | tom_old | 152 | 2.79 / 1.27 / 1.23 | 2.25 | 1.19 | 0.34 | 1.3 | 4.6 |
| corners+arrows | tom_old | 152 | 0.26 / 1.39 / 1.42 | 2.68 | 1.46 | 0.26 | -1.4 | 4.5 |
| corners+pins | tom_old | 152 | 1.52 / 0.28 / 0.30 | 0.54 | 0.28 | 0.26 | 2.0 | 0.7 |
| corners+pins10 | tom_old | 152 | 1.40 / 0.35 / 0.37 | 0.72 | 0.42 | 0.26 | 1.1 | 1.0 |
| corners+arrows+pins10 | tom_old | 152 | 1.19 / 0.40 / 0.43 | 0.87 | 0.10 | 0.26 | 0.9 | 1.3 |
| foul+arrows+pins10 | tom_old | 146 | 1.19 / 0.40 / 0.43 | 0.86 | 0.10 | - | 0.9 | 1.3 |
| arrows+pins10 | tom_old | 146 | 1.25 / 0.29 / 0.34 | 0.58 | 0.19 | - | 1.1 | 0.8 |
| arrows+pins10+weakfoul | tom_old | 146 | 1.09 / 0.45 / 0.49 | 0.77 | 0.13 | - | 0.6 | 1.1 |
| arrows+pins10+top | tom_old | 145 | 1.25 / 0.29 / 0.33 | 0.58 | 0.19 | - | 1.1 | 0.7 |
| snapfoul+pins10 | tom_old | 146 | 1.01 / 0.58 / 0.62 | 0.77 | 0.14 | - | 0.7 | 1.1 |
| snapfoul+arrows+pins10 | tom_old | 146 | 1.06 / 0.51 / 0.55 | 0.74 | 0.15 | - | 0.6 | 1.0 |
| corners+arrows+pins10+carry | tom_old | 152 | 1.19 / 0.40 / 0.43 | 0.86 | 0.10 | 0.20 | 0.9 | 1.3 |
| corners+arrows+pins10+carryLM | tom_old | 152 | 1.19 / 0.40 / 0.43 | 0.86 | 0.10 | 0.26 | 0.9 | 1.3 |
| corners+arrows(1pass) | tom_old | 152 | 0.26 / 1.38 / 1.42 | 2.67 | 1.46 | 0.26 | -1.4 | 4.5 |
| foul+arrows+pins(1pass) | tom_old | 146 | 1.02 / 0.56 / 0.60 | 1.19 | 0.42 | - | 0.8 | 1.9 |
| dropped landmark (loop3_plus, foul+arrows+pins base) | sample_input throw median (pins) / tail | Chardie throw median (pins) / tail | tom_old throw median (pins) / tail |
|---|---|---|---|
| foul+arrows+pins | 0.34 / 0.42 | 0.74 / 0.51 | 0.56 / 1.19 |
| foul+arrows+pins10 | 0.40 / 0.53 | 0.78 / 0.59 | 0.40 / 0.86 |
| drop-arrow_5 | 0.35 / 0.43 | 0.75 / 0.52 | 0.52 / 1.12 |
| drop-arrow_10 | 0.35 / 0.43 | 0.75 / 0.52 | 0.52 / 1.12 |
| drop-arrow_15 | 0.35 / 0.43 | 0.74 / 0.51 | 0.53 / 1.13 |
| drop-arrow_20 | 0.35 / 0.43 | 0.73 / 0.52 | 0.54 / 1.15 |
| drop-arrow_25 | 0.34 / 0.42 | 0.72 / 0.49 | 0.54 / 1.15 |
| drop-arrow_30 | 0.34 / 0.43 | 0.76 / 0.52 | 0.56 / 1.17 |
| drop-arrow_35 | 0.34 / 0.42 | 0.74 / 0.52 | 0.56 / 1.19 |
| drop-pin_7 | 0.40 / 0.53 | 0.78 / 0.59 | 0.41 / 0.87 |
| drop-pin_10 | 0.39 / 0.51 | 0.78 / 0.57 | 0.42 / 0.90 |
<!-- /TABLE:e3_loop3_plus -->

<!-- TABLE:e3_loop3_1024 -->
| variant (loop3_1024) | video | frames ok | throw median: annotated / pins / all | tail (last 20 %) pins | pre-hit pins | last pins | far width err px (pins, med) | far centre err px (pins, med abs) |
|---|---|---|---|---|---|---|---|---|
| corners | tom_old | 98 | 0.91 / 0.64 / 0.68 | 1.27 | - | 1.86 | 2.4 | 2.1 |
| snapcorners | tom_old | 98 | 0.79 / 0.82 / 0.85 | 1.27 | - | 2.03 | 2.4 | 2.1 |
| corners+arrows | tom_old | 98 | 0.60 / 0.94 / 0.98 | 1.75 | - | 1.86 | -0.2 | 2.9 |
| corners+pins | tom_old | 98 | 1.28 / 0.29 / 0.32 | 0.66 | - | 1.86 | 2.1 | 0.9 |
| corners+pins10 | tom_old | 98 | 1.21 / 0.35 / 0.38 | 0.74 | - | 1.86 | 1.1 | 1.1 |
| corners+arrows+pins10 | tom_old | 98 | 1.11 / 0.43 / 0.46 | 0.81 | - | 1.86 | 0.9 | 1.2 |
| foul+arrows+pins10 | tom_old | 93 | 1.12 / 0.42 / 0.46 | 0.81 | - | - | 0.9 | 1.2 |
| arrows+pins10 | tom_old | 93 | 1.24 / 0.30 / 0.34 | 0.59 | - | - | 1.1 | 0.8 |
| arrows+pins10+weakfoul | tom_old | 93 | 1.07 / 0.46 / 0.50 | 0.76 | - | - | 0.9 | 1.1 |
| arrows+pins10+top | tom_old | 93 | 1.24 / 0.30 / 0.34 | 0.58 | - | - | 1.1 | 0.8 |
| snapfoul+pins10 | tom_old | 93 | 1.02 / 0.57 / 0.61 | 0.77 | - | - | 1.0 | 1.1 |
| snapfoul+arrows+pins10 | tom_old | 93 | 1.06 / 0.50 / 0.54 | 0.74 | - | - | 0.9 | 1.0 |
| corners+arrows+pins10+carry | tom_old | 98 | 1.12 / 0.42 / 0.46 | 0.80 | - | 0.43 | 0.9 | 1.2 |
| corners+arrows+pins10+carryLM | tom_old | 98 | 1.12 / 0.43 / 0.46 | 0.81 | - | 1.86 | 0.9 | 1.2 |
| corners+arrows(1pass) | tom_old | 98 | 0.60 / 0.94 / 0.98 | 1.75 | - | 1.86 | -0.2 | 2.9 |
| foul+arrows+pins(1pass) | tom_old | 93 | 1.06 / 0.48 / 0.52 | 0.93 | - | - | 0.9 | 1.4 |
| dropped landmark (loop3_1024, foul+arrows+pins base) | sample_input throw median (pins) / tail | Chardie throw median (pins) / tail | tom_old throw median (pins) / tail |
|---|---|---|---|
| foul+arrows+pins | - | - | 0.48 / 0.93 |
| foul+arrows+pins10 | - | - | 0.42 / 0.81 |
| drop-arrow_5 | - | - | 0.47 / 0.91 |
| drop-arrow_10 | - | - | 0.46 / 0.90 |
| drop-arrow_15 | - | - | 0.46 / 0.90 |
| drop-arrow_20 | - | - | 0.47 / 0.90 |
| drop-arrow_25 | - | - | 0.47 / 0.91 |
| drop-arrow_30 | - | - | 0.48 / 0.93 |
| drop-arrow_35 | - | - | 0.49 / 0.94 |
| drop-pin_7 | - | - | 0.43 / 0.82 |
| drop-pin_10 | - | - | 0.44 / 0.83 |
<!-- /TABLE:e3_loop3_1024 -->

<!-- TABLE:e3_seg2_1024 -->
| variant (seg2_1024) | video | frames ok | throw median: annotated / pins / all | tail (last 20 %) pins | pre-hit pins | last pins | far width err px (pins, med) | far centre err px (pins, med abs) |
|---|---|---|---|---|---|---|---|---|
| corners | tom_old | 154 | 1.34 / 0.26 / 0.29 | 0.59 | 0.07 | 2.16 | 2.1 | 0.8 |
| snapcorners | tom_old | 154 | 1.19 / 0.43 / 0.47 | 0.59 | 0.24 | 2.33 | 2.1 | 0.8 |
| corners+arrows | tom_old | 154 | 0.76 / 0.90 / 0.94 | 1.64 | 0.72 | 2.16 | -0.2 | 2.7 |
| corners+pins | tom_old | 154 | 1.29 / 0.31 / 0.34 | 0.65 | 0.06 | 2.16 | 2.0 | 0.9 |
| corners+pins10 | tom_old | 154 | 1.23 / 0.39 / 0.42 | 0.73 | 0.20 | 2.16 | 1.1 | 1.0 |
| corners+arrows+pins10 | tom_old | 154 | 1.13 / 0.44 / 0.48 | 0.83 | 0.09 | 2.16 | 1.0 | 1.2 |
| foul+arrows+pins10 | tom_old | 145 | 1.13 / 0.44 / 0.47 | 0.81 | 0.09 | - | 1.0 | 1.2 |
| arrows+pins10 | tom_old | 141 | 1.24 / 0.31 / 0.35 | 0.60 | 0.19 | - | 1.1 | 0.8 |
| arrows+pins10+weakfoul | tom_old | 145 | 1.08 / 0.47 / 0.51 | 0.76 | 0.16 | - | 0.9 | 1.1 |
| arrows+pins10+top | tom_old | 141 | 1.24 / 0.31 / 0.35 | 0.60 | 0.19 | - | 1.1 | 0.8 |
| snapfoul+pins10 | tom_old | 145 | 1.03 / 0.57 / 0.61 | 0.75 | 0.16 | - | 1.0 | 1.0 |
| snapfoul+arrows+pins10 | tom_old | 145 | 1.07 / 0.51 / 0.54 | 0.75 | 0.17 | - | 0.9 | 1.1 |
| corners+arrows+pins10+carry | tom_old | 154 | 1.14 / 0.43 / 0.47 | 0.81 | 0.09 | 0.23 | 1.0 | 1.2 |
| corners+arrows+pins10+carryLM | tom_old | 154 | 1.13 / 0.44 / 0.47 | 0.81 | 0.09 | 2.16 | 1.0 | 1.2 |
| corners+arrows(1pass) | tom_old | 154 | 0.76 / 0.90 / 0.94 | 1.67 | 0.72 | 2.16 | -0.1 | 2.8 |
| foul+arrows+pins(1pass) | tom_old | 145 | 1.06 / 0.50 / 0.53 | 0.92 | 0.25 | - | 1.0 | 1.4 |
| dropped landmark (seg2_1024, foul+arrows+pins base) | sample_input throw median (pins) / tail | Chardie throw median (pins) / tail | tom_old throw median (pins) / tail |
|---|---|---|---|
| foul+arrows+pins | - | - | 0.50 / 0.92 |
| foul+arrows+pins10 | - | - | 0.44 / 0.81 |
| drop-arrow_5 | - | - | 0.48 / 0.90 |
| drop-arrow_10 | - | - | 0.47 / 0.90 |
| drop-arrow_15 | - | - | 0.48 / 0.89 |
| drop-arrow_20 | - | - | 0.48 / 0.89 |
| drop-arrow_25 | - | - | 0.48 / 0.90 |
| drop-arrow_30 | - | - | 0.49 / 0.90 |
| drop-arrow_35 | - | - | 0.50 / 0.92 |
| drop-pin_7 | - | - | 0.44 / 0.83 |
| drop-pin_10 | - | - | 0.45 / 0.83 |
<!-- /TABLE:e3_seg2_1024 -->

<!-- TABLE:e3_sam_even3_k -->
| variant (sam_even3_k) | video | frames ok | throw median: annotated / pins / all | tail (last 20 %) pins | pre-hit pins | last pins | far width err px (pins, med) | far centre err px (pins, med abs) |
|---|---|---|---|---|---|---|---|---|
| corners | sample_input | 1 | 0.31 / 0.48 / 0.46 | 0.99 | 0.48 | 0.42 | -0.4 | 1.6 |
| snapcorners | sample_input | 1 | 0.60 / 0.49 / 0.48 | 0.93 | 0.49 | 0.40 | -0.4 | 1.6 |
| corners+arrows | sample_input | 1 | 0.46 / 0.32 / 0.30 | 0.49 | 0.32 | 0.21 | 7.2 | 0.0 |
| corners+pins | sample_input | 1 | 0.82 / 0.10 / 0.12 | 0.05 | 0.10 | 0.42 | -0.2 | 0.0 |
| corners+pins10 | sample_input | 1 | 0.79 / 0.10 / 0.10 | 0.08 | 0.10 | 0.42 | 0.1 | 0.1 |
| corners+arrows+pins10 | sample_input | 1 | 0.75 / 0.09 / 0.09 | 0.12 | 0.09 | 0.21 | 0.8 | 0.0 |
| foul+arrows+pins10 | sample_input | 1 | 0.75 / 0.09 / 0.09 | 0.12 | 0.09 | - | 0.8 | 0.0 |
| arrows+pins10 | sample_input | 1 | 0.77 / 0.05 / 0.06 | 0.02 | 0.05 | - | 0.1 | 0.1 |
| arrows+pins10+weakfoul | sample_input | 1 | 0.70 / 0.10 / 0.08 | 0.16 | 0.10 | - | 1.1 | 0.1 |
| arrows+pins10+top | sample_input | 1 | 0.76 / 0.04 / 0.05 | 0.04 | 0.04 | - | 0.1 | 0.0 |
| snapfoul+pins10 | sample_input | 1 | 1.09 / 0.37 / 0.38 | 0.05 | 0.37 | - | 0.3 | 0.0 |
| snapfoul+arrows+pins10 | sample_input | 1 | 0.83 / 0.20 / 0.19 | 0.18 | 0.20 | - | 0.9 | 0.2 |
| corners+arrows+pins10+carry | sample_input | 1 | 0.75 / 0.09 / 0.09 | 0.12 | 0.09 | 1.78 | 0.8 | 0.0 |
| corners+arrows+pins10+carryLM | sample_input | 1 | 0.75 / 0.09 / 0.09 | 0.12 | 0.09 | 0.11 | 0.8 | 0.0 |
| corners+arrows(1pass) | sample_input | 1 | 0.46 / 0.32 / 0.30 | 0.49 | 0.32 | 0.21 | 7.2 | 0.0 |
| foul+arrows+pins(1pass) | sample_input | 1 | 0.76 / 0.08 / 0.08 | 0.09 | 0.08 | - | 1.0 | 0.0 |
| corners | Chardie | 1 | 0.68 / 0.49 / 0.39 | 0.16 | 0.49 | 0.81 | -3.3 | 1.2 |
| snapcorners | Chardie | 1 | 0.70 / 0.53 / 0.43 | 0.16 | 0.53 | 0.69 | -3.3 | 1.2 |
| corners+arrows | Chardie | 1 | 0.60 / 0.58 / 0.36 | 0.36 | 0.58 | 0.61 | 1.3 | 0.1 |
| corners+pins | Chardie | 1 | 0.49 / 0.72 / 0.45 | 0.52 | 0.72 | 0.81 | -0.5 | 0.1 |
| corners+pins10 | Chardie | 1 | 0.54 / 0.67 / 0.41 | 0.46 | 0.67 | 0.81 | 0.2 | 0.0 |
| corners+arrows+pins10 | Chardie | 1 | 0.55 / 0.66 / 0.41 | 0.44 | 0.66 | 0.61 | 0.4 | 0.0 |
| foul+arrows+pins10 | Chardie | 1 | 0.55 / 0.66 / 0.41 | 0.44 | 0.66 | - | 0.4 | 0.0 |
| arrows+pins10 | Chardie | 1 | 0.55 / 0.56 / 0.33 | 0.39 | 0.56 | - | 0.1 | 0.1 |
| arrows+pins10+weakfoul | Chardie | 1 | 0.56 / 0.65 / 0.40 | 0.42 | 0.65 | - | 0.4 | 0.0 |
| arrows+pins10+top | Chardie | 1 | 0.56 / 0.56 / 0.32 | 0.39 | 0.56 | - | 0.1 | 0.1 |
| snapfoul+pins10 | Chardie | 1 | 0.59 / 0.67 / 0.43 | 0.41 | 0.67 | - | 0.6 | 0.0 |
| snapfoul+arrows+pins10 | Chardie | 1 | 0.59 / 0.63 / 0.39 | 0.38 | 0.63 | - | 0.6 | 0.0 |
| corners+arrows+pins10+carry | Chardie | 1 | 0.55 / 0.66 / 0.41 | 0.44 | 0.66 | 0.69 | 0.4 | 0.0 |
| corners+arrows+pins10+carryLM | Chardie | 1 | 0.55 / 0.66 / 0.41 | 0.44 | 0.66 | 0.51 | 0.4 | 0.0 |
| corners+arrows(1pass) | Chardie | 1 | 0.60 / 0.58 / 0.35 | 0.36 | 0.58 | 0.61 | 1.3 | 0.1 |
| foul+arrows+pins(1pass) | Chardie | 1 | 0.53 / 0.67 / 0.41 | 0.46 | 0.67 | - | 0.2 | 0.0 |
| corners | tom_old | 2 | 1.72 / 0.57 / 0.57 | 0.83 | 0.73 | 0.42 | -6.2 | 1.6 |
| snapcorners | tom_old | 2 | 1.65 / 0.58 / 0.59 | 0.83 | 0.62 | 0.55 | -6.2 | 1.6 |
| corners+arrows | tom_old | 2 | 1.12 / 0.45 / 0.49 | 0.53 | 0.48 | 0.42 | -2.5 | 0.7 |
| corners+pins | tom_old | 2 | 1.32 / 0.26 / 0.30 | 0.20 | 0.09 | 0.42 | -3.2 | 0.1 |
| corners+pins10 | tom_old | 2 | 1.42 / 0.27 / 0.27 | 0.22 | 0.11 | 0.42 | -3.1 | 0.5 |
| corners+arrows+pins10 | tom_old | 2 | 1.36 / 0.26 / 0.27 | 0.18 | 0.09 | 0.42 | -3.0 | 0.4 |
| foul+arrows+pins10 | tom_old | 1 | 1.54 / 0.09 / 0.07 | 0.11 | 0.09 | - | -0.4 | 0.6 |
| arrows+pins10 | tom_old | 1 | 1.43 / 0.19 / 0.20 | 0.07 | 0.19 | - | -0.6 | 0.5 |
| arrows+pins10+weakfoul | tom_old | 1 | 1.52 / 0.15 / 0.14 | 0.17 | 0.15 | - | -0.4 | 0.7 |
| arrows+pins10+top | tom_old | 1 | 1.43 / 0.19 / 0.20 | 0.07 | 0.19 | - | -0.6 | 0.5 |
| snapfoul+pins10 | tom_old | 1 | 1.54 / 0.15 / 0.14 | 0.19 | 0.15 | - | -0.3 | 0.7 |
| snapfoul+arrows+pins10 | tom_old | 1 | 1.52 / 0.15 / 0.14 | 0.17 | 0.15 | - | -0.3 | 0.7 |
| corners+arrows+pins10+carry | tom_old | 2 | 1.54 / 0.15 / 0.14 | 0.17 | 0.09 | 0.22 | -0.2 | 0.8 |
| corners+arrows+pins10+carryLM | tom_old | 2 | 1.36 / 0.26 / 0.27 | 0.18 | 0.09 | 0.42 | -3.0 | 0.4 |
| corners+arrows(1pass) | tom_old | 2 | 1.12 / 0.45 / 0.49 | 0.53 | 0.48 | 0.42 | -2.5 | 0.7 |
| foul+arrows+pins(1pass) | tom_old | 1 | 1.29 / 0.25 / 0.29 | 0.37 | 0.25 | - | 0.3 | 0.3 |
| dropped landmark (sam_even3_k, foul+arrows+pins base) | sample_input throw median (pins) / tail | Chardie throw median (pins) / tail | tom_old throw median (pins) / tail |
|---|---|---|---|
| foul+arrows+pins | 0.08 / 0.09 | 0.67 / 0.46 | 0.25 / 0.37 |
| foul+arrows+pins10 | 0.09 / 0.12 | 0.66 / 0.44 | 0.09 / 0.11 |
| drop-arrow_5 | 0.10 / 0.04 | 0.70 / 0.50 | 0.26 / 0.38 |
| drop-arrow_10 | 0.09 / 0.06 | 0.68 / 0.48 | 0.24 / 0.37 |
| drop-arrow_15 | 0.09 / 0.07 | 0.68 / 0.47 | 0.24 / 0.35 |
| drop-arrow_20 | 0.08 / 0.08 | 0.66 / 0.45 | 0.23 / 0.35 |
| drop-arrow_25 | 0.08 / 0.10 | 0.66 / 0.45 | 0.23 / 0.34 |
| drop-arrow_30 | 0.08 / 0.11 | 0.66 / 0.45 | 0.24 / 0.35 |
| drop-arrow_35 | 0.08 / 0.12 | 0.67 / 0.46 | 0.25 / 0.37 |
| drop-pin_7 | 0.09 / 0.11 | 0.66 / 0.45 | 0.10 / 0.16 |
| drop-pin_10 | 0.11 / 0.17 | 0.64 / 0.42 | 0.10 / 0.14 |
<!-- /TABLE:e3_sam_even3_k -->

<!-- TABLE:e3_sam_zoom_lo_k -->
| variant (sam_zoom_lo_k) | video | frames ok | throw median: annotated / pins / all | tail (last 20 %) pins | pre-hit pins | last pins | far width err px (pins, med) | far centre err px (pins, med abs) |
|---|---|---|---|---|---|---|---|---|
| corners | sample_input | 1 | 0.89 / 0.15 / 0.17 | 0.15 | 0.15 | 0.14 | 1.3 | 0.5 |
| snapcorners | sample_input | 1 | 1.21 / 0.47 / 0.49 | 0.21 | 0.47 | 0.35 | 1.3 | 0.5 |
| corners+arrows | sample_input | 1 | 0.57 / 0.22 / 0.20 | 0.31 | 0.22 | 0.12 | 7.1 | 0.5 |
| corners+pins | sample_input | 1 | 0.82 / 0.09 / 0.11 | 0.02 | 0.09 | 0.14 | 0.0 | 0.1 |
| corners+pins10 | sample_input | 1 | 0.79 / 0.07 / 0.09 | 0.04 | 0.07 | 0.14 | 0.2 | 0.0 |
| corners+arrows+pins10 | sample_input | 1 | 0.76 / 0.07 / 0.07 | 0.07 | 0.07 | 0.12 | 0.8 | 0.1 |
| foul+arrows+pins10 | sample_input | 1 | 0.76 / 0.07 / 0.07 | 0.07 | 0.07 | - | 0.8 | 0.0 |
| arrows+pins10 | sample_input | 1 | 0.79 / 0.06 / 0.08 | 0.03 | 0.06 | - | 0.2 | 0.2 |
| arrows+pins10+weakfoul | sample_input | 1 | 0.72 / 0.07 / 0.06 | 0.10 | 0.07 | - | 1.0 | 0.0 |
| arrows+pins10+top | sample_input | 1 | 0.79 / 0.06 / 0.08 | 0.03 | 0.06 | - | 0.2 | 0.2 |
| snapfoul+pins10 | sample_input | 1 | 1.12 / 0.39 / 0.41 | 0.05 | 0.39 | - | 0.3 | 0.1 |
| snapfoul+arrows+pins10 | sample_input | 1 | 0.86 / 0.19 / 0.19 | 0.13 | 0.19 | - | 0.9 | 0.1 |
| corners+arrows+pins10+carry | sample_input | 1 | 0.76 / 0.07 / 0.07 | 0.07 | 0.07 | 1.80 | 0.8 | 0.1 |
| corners+arrows+pins10+carryLM | sample_input | 1 | 0.76 / 0.07 / 0.07 | 0.07 | 0.07 | 0.08 | 0.8 | 0.1 |
| corners+arrows(1pass) | sample_input | 1 | 0.57 / 0.22 / 0.20 | 0.31 | 0.22 | 0.12 | 7.1 | 0.5 |
| foul+arrows+pins(1pass) | sample_input | 1 | 0.78 / 0.06 / 0.07 | 0.03 | 0.06 | - | 1.0 | 0.2 |
| corners | Chardie | 1 | 0.37 / 0.89 / 0.62 | 0.82 | 0.89 | 0.97 | -1.4 | 0.1 |
| snapcorners | Chardie | 1 | 0.42 / 0.97 / 0.70 | 0.84 | 0.97 | 0.87 | -1.4 | 0.1 |
| corners+arrows | Chardie | 1 | 0.47 / 0.71 / 0.44 | 0.63 | 0.71 | 0.67 | 1.5 | 0.5 |
| corners+pins | Chardie | 1 | 0.37 / 0.89 / 0.62 | 0.82 | 0.89 | 0.97 | -1.4 | 0.1 |
| corners+pins10 | Chardie | 1 | 0.37 / 0.89 / 0.62 | 0.82 | 0.89 | 0.97 | -1.4 | 0.1 |
| corners+arrows+pins10 | Chardie | 1 | 0.47 / 0.71 / 0.44 | 0.63 | 0.71 | 0.67 | 1.5 | 0.5 |
| foul+arrows+pins10 | Chardie | 0 | - / - / - | - | - | - | - | - |
| arrows+pins10 | Chardie | 0 | - / - / - | - | - | - | - | - |
| arrows+pins10+weakfoul | Chardie | 0 | - / - / - | - | - | - | - | - |
| arrows+pins10+top | Chardie | 0 | - / - / - | - | - | - | - | - |
| snapfoul+pins10 | Chardie | 0 | - / - / - | - | - | - | - | - |
| snapfoul+arrows+pins10 | Chardie | 0 | - / - / - | - | - | - | - | - |
| corners+arrows+pins10+carry | Chardie | 1 | 0.47 / 0.71 / 0.44 | 0.63 | 0.71 | 0.67 | 1.5 | 0.5 |
| corners+arrows+pins10+carryLM | Chardie | 1 | 0.47 / 0.71 / 0.44 | 0.63 | 0.71 | 0.67 | 1.5 | 0.5 |
| corners+arrows(1pass) | Chardie | 1 | 0.47 / 0.71 / 0.44 | 0.63 | 0.71 | 0.67 | 1.5 | 0.5 |
| foul+arrows+pins(1pass) | Chardie | 0 | - / - / - | - | - | - | - | - |
| corners | tom_old | 2 | 1.19 / 0.74 / 0.74 | 1.18 | 0.33 | 1.16 | -4.0 | 2.1 |
| snapcorners | tom_old | 2 | 1.14 / 0.79 / 0.79 | 1.18 | 0.26 | 1.31 | -4.0 | 2.1 |
| corners+arrows | tom_old | 2 | 0.75 / 0.85 / 0.90 | 1.31 | 0.55 | 1.16 | -0.6 | 1.9 |
| corners+pins | tom_old | 2 | 0.99 / 0.61 / 0.65 | 0.89 | 0.06 | 1.16 | -1.2 | 1.4 |
| corners+pins10 | tom_old | 2 | 1.10 / 0.65 / 0.66 | 0.95 | 0.15 | 1.16 | -1.0 | 1.6 |
| corners+arrows+pins10 | tom_old | 2 | 1.04 / 0.63 / 0.64 | 0.90 | 0.10 | 1.16 | -0.9 | 1.6 |
| foul+arrows+pins10 | tom_old | 1 | 1.56 / 0.10 / 0.08 | 0.15 | 0.10 | - | -0.4 | 0.6 |
| arrows+pins10 | tom_old | 1 | 1.45 / 0.20 / 0.20 | 0.11 | 0.20 | - | -0.7 | 0.6 |
| arrows+pins10+weakfoul | tom_old | 1 | 1.54 / 0.17 / 0.15 | 0.21 | 0.17 | - | -0.4 | 0.8 |
| arrows+pins10+top | tom_old | 1 | 1.45 / 0.20 / 0.20 | 0.11 | 0.20 | - | -0.7 | 0.6 |
| snapfoul+pins10 | tom_old | 1 | 1.56 / 0.16 / 0.15 | 0.23 | 0.16 | - | -0.3 | 0.8 |
| snapfoul+arrows+pins10 | tom_old | 1 | 1.54 / 0.17 / 0.15 | 0.21 | 0.17 | - | -0.3 | 0.8 |
| corners+arrows+pins10+carry | tom_old | 2 | 1.56 / 0.16 / 0.14 | 0.22 | 0.10 | 0.22 | -0.3 | 0.8 |
| corners+arrows+pins10+carryLM | tom_old | 2 | 1.04 / 0.63 / 0.64 | 0.90 | 0.10 | 1.16 | -0.9 | 1.6 |
| corners+arrows(1pass) | tom_old | 2 | 0.75 / 0.85 / 0.90 | 1.30 | 0.55 | 1.16 | -0.6 | 1.9 |
| foul+arrows+pins(1pass) | tom_old | 1 | 1.30 / 0.24 / 0.28 | 0.36 | 0.24 | - | 0.1 | 0.3 |
| dropped landmark (sam_zoom_lo_k, foul+arrows+pins base) | sample_input throw median (pins) / tail | Chardie throw median (pins) / tail | tom_old throw median (pins) / tail |
|---|---|---|---|
| foul+arrows+pins | 0.06 / 0.03 | - / - | 0.24 / 0.36 |
| foul+arrows+pins10 | 0.07 / 0.07 | - / - | 0.10 / 0.15 |
| drop-arrow_5 | 0.09 / 0.03 | - / - | 0.25 / 0.37 |
| drop-arrow_10 | 0.07 / 0.02 | - / - | 0.23 / 0.35 |
| drop-arrow_15 | 0.07 / 0.03 | - / - | 0.22 / 0.34 |
| drop-arrow_20 | 0.06 / 0.03 | - / - | 0.22 / 0.34 |
| drop-arrow_25 | 0.06 / 0.04 | - / - | 0.22 / 0.33 |
| drop-arrow_30 | 0.06 / 0.04 | - / - | 0.23 / 0.34 |
| drop-arrow_35 | 0.05 / 0.05 | - / - | 0.24 / 0.36 |
| drop-pin_7 | 0.06 / 0.06 | - / - | 0.11 / 0.19 |
| drop-pin_10 | 0.08 / 0.11 | - / - | 0.11 / 0.18 |
<!-- /TABLE:e3_sam_zoom_lo_k -->

### E4 - the landmarks as the camera model

<!-- TABLE:e4 -->
| video | landmarks per frame (median) | frames with a landmark fit | corner error vs hand per-frame corners: landmarks / ORB (px mean, throw) | top corners: landmarks / ORB | max: landmarks / ORB | vs ORB (px mean, no hand truth) |
|---|---|---|---|---|---|---|
| sample_input | 17.0 | 180/180 | 3.45 / 4.24 | 1.59 / 3.46 | 9.27 / 15.14 | - |
| Chardie | 16.0 | 158/162 | - | - | - | 4.57 |
| tom_old | 7.0 | 401/406 | - | - | - | 7.9 |
<!-- /TABLE:e4 -->

## What the results say

1. **The hand corners were the floor, and it was 1-2 boards at the pins.** Measured on the pins,
   the hand annotation is 5 px too wide on sample_input and 4 px too narrow and 4 px left on
   tom_old; the arrows, an independent ruler at 15 ft, side with the pins. Re-scored against the
   pins, loop 3's student is not 3.15 boards off on tom_old but 1.6, and loop 2's far-end crop is
   not the worst SAM method on sample_input (0.89) but the best (0.15). Every earlier conclusion
   drawn below one board at the far end should be re-read in the `pins` column.

2. **The pins are the far-end ruler; they fix it on every frame from a lane that was 12 px off.**
   With the ten detected pin bases added to the student's own four corners, held-out sample_input
   goes from 1.19 to 0.37 boards median against the pins truth and from 1.83 to 0.77 against the
   hand annotation (independent of the pins); tom_old from 1.61 to 0.41; the far-end width error
   drops from 12 / 6 / 3 px to about 1 px. Dropping pin 7 or pin 10 changes the fit by a few
   hundredths of a board; ten pins are better than two. On loop 2's SAM lanes (single pre-hit
   frames) the same refit reaches 0.07-0.11 boards on sample_input and tom_old.

3. **The arrows cannot fix the far end and are not needed when the pins are there.** Seven
   x-only constraints at one depth pin the board scale at 15 ft, but the far end is then an
   extrapolation over 45 ft of lane from a 30-board baseline: `corners+arrows` is worse than the
   corners alone on sample_input and `corners+arrows+pins10` is within 0.06 boards of
   `corners+pins10` on every video. Their value is elsewhere: without any foul-line input, `arrows+pins10`
   recovers the pre-hit lane to 0.05 boards on sample_input, so arrows + pins define the lane
   along the whole ball path with no near-end detector at all; and they are the only landmark
   left after the pins fall (E4).

4. **The student's near end is as wrong as its far end.** Loop 3's foul-line corners are 19 / 12 px
   (3 / 2 boards) off on sample_input and 9 / 5 px on Chardie; the brief's premise that the far end
   was the only remaining error holds for SAM, not for the mask student. That is why Chardie's
   far end lands within 0.1 px of the pins truth yet the board error does not move (0.64 → 0.78
   against pins, 0.88 → 0.53 against the annotation): the two truths disagree at the near end by
   a few px and the metric integrates along the path. Gradient snapping of the near end made it
   worse (`snapcorners`); a foul-line landmark detector is the missing piece.

5. **A one-column alias is the rack fit's failure mode.** Shifted by one pin column (6 in) the
   template still covers six of seven columns; from a poor hypothesis at 720p it locked there on
   2-4 % of frames (1-7 per video), which then poisoned the frames that carried those pins after
   the hit. The guard is cheap: the score at ±1 column must lose by a margin, and the search stays
   within ±0.12 lane widths of the hypothesis.

6. **Static landmarks are a better camera model than ORB while the pins stand.** On sample_input
   the arrows + pin bases carry the first frame's hand corners onto every frame with 4.0 px mean
   error (2.4 px at the pin end) against ORB's 5.3 (5.2 at the pin end), max 9.3 vs 15.1; on
   Chardie the two models agree to 4.6 px. After
   the pin hit only the seven arrows remain, nearly collinear at one depth, and the similarity is
   ill-conditioned (tom_old, 7 landmarks median after the hit: 7.9 px from ORB on a tripod). Two depths are needed.

7. **Carrying pins after the hit is fragile on handheld video, both ways.** Through ORB or through
   the arrows' own similarity, the carried far end on sample_input's last frame scores 0.55-2.9
   boards depending on the variant, against 1.1 for corners+arrows on that frame. The 10 frames
   after pin contact are the ball in the pit; the board number that matters is fixed before it.

8. **An aside that is not about landmarks.** The two-class student trained at 1024 px, batch 4,
   no horizontal flip gives a lane on every frame of held-out tom_old at 0.26 boards median against
   the pins truth (0.29 against all landmarks, 92.9 % within two boards), where loop 3's 1024 model
   was confident on 60 of 409 frames. Since the recipe differs in three ways at once it is a lead,
   not a result; fed to the pin refit it is the `seg2_1024` table above.

9. **The per-frame pin refit has its own floor, about 0.4 boards on tom_old.** Whatever lane goes
   in - loop 3's 640 px student (1.61), its +teacher variant (1.62), its 1024 px model (0.64) or
   this loop's 1024 px student (0.26) - `corners+pins10` comes out at 0.35-0.41 boards median
   against the pins truth, and the far-end width within about 1 px. That is the rack fit's own
   per-frame noise (1.4 px per base, 0.36 boards of centre, median); it helps every lane worse than
   that and hurts the one lane that was better (0.26 → 0.39). The pins are static in the scene, so
   the fix is to fit the rack once per throw (median over the standing-pin frames, moved through
   the camera model) rather than per frame; not done here.

## Recommendation for the engine

1. **Detect the pin rack and refit the homography from it while the pins stand** - the student
   (or SAM) lane is the initial guess, the ten pin bases at their rule-book coordinates are the
   constraint. ~0.8 s per frame for the grid search as written; a two-parameter refine from the
   previous frame would be milliseconds. Use all ten bases, with the alias margin as the
   acceptance test, and pool the rack over the standing-pin frames (through the camera model)
   instead of trusting one frame: the per-frame refit floors at ~0.4 boards (point 9).
2. **Treat the four corners as a hypothesis, not a measurement**: the mask student's foul-line
   corners are 2-3 boards off on two of three videos. Weight them as such, and add a foul-line /
   gutter-edge landmark at the near end before trusting any near-end board number to a board.
3. **Use the arrows for the camera, not for the far end**: with the pins they give a per-frame
   similarity better than ORB (E4) and a lane along the whole path with no foul-line input; alone
   they cannot extrapolate 45 ft.
4. **Rebuild the truth before the next accuracy claim**: `results/landmarks_<stem>.json` +
   `common.truth_corners(stem, f, "pins")`. Report both columns; a method that improves against
   the hand corners but not against the pins is fitting the annotation's error.

## Blocked / negative results

- **Learned arrow detector**: 0 detections on every held-out video at 640 px and at 1024 px (the
  lane class is unaffected, see E2). Two distinct failures (measured below): with mosaic the class
  never trains at all; without mosaic it fits the training videos (AP50 0.7) and transfers nothing.
  A dedicated small-object detector on lane-rectified crops, trained on many placements, would be
  the next attempt if one is wanted at all - the classical detector (recall 0.68-0.93 from the
  student lane, 7/7 from a truth-quality lane, 50 ms) carries E2. Training itself was fragile: 1024 px on
  MPS crashed in ultralytics' assigner with these labels at batch 8 and 16 and ran at batch 4; the
  two 640 folds whose training set includes tom_old crashed at epoch 1 on every retry and only
  trained with mosaic off (`results/seg2_seg2_640_*_nomosaic__*.json`): again zero arrows on
  held-out Chardie and sample_input, and their lanes are worse than loop 3's mosaic-trained ones
  (Chardie 1.01 / 0.73 vs 0.88 / 0.64, sample_input 2.65 / 1.98 vs 1.83 / 1.19 against annotated /
  pins), so mosaic matters for the lane class.
- **Why the arrow class failed, measured on the training videos' own val split** (`model.val`,
  per class): with mosaic on (the loop-3 recipe, 640 and 1024 px) the arrow class has **AP 0 and
  recall 0 in-distribution** - mosaic tiles four frames at half scale, a 6 px arrow becomes 3 px,
  under the 8 px stride, and is never assigned a positive; the class never trains. With mosaic
  off it does learn in-distribution (AP50 0.68-0.71, recall 0.62-0.64, precision 0.92-0.93 on the
  training videos' held-back frames) and still fires on **nothing** on the held-out video: at
  conf 0.001 it emits 17-115 arrow boxes per 12 frames, none within 1.5 boards of a true arrow,
  best confidence on a true arrow 0.000. It learned where the arrows sit in the two training
  videos' frames, not what an arrow looks like - loop 3's pose-head failure in a new guise, at
  five videos of the same alley. The classical detector on the rectified lane needs no training
  and transfers by construction.
- **Gradient snap of the near end** (`snap*` rows): worse than the raw student corners.
- **Range-finder dots**: not visible on any video; the 7-ft dots only on tom_old (unused).
- `foul+arrows` (no far-end 2D anchor) is degenerate by construction and reported as such.

## Reproducing

```
V=~/code/bowling-app/analysis-engine/.venv/bin/python
export LM_SCRATCH=<scratch>          # frames/, weights/, ds/, runs/, pred/ go here
cd docs/research/2026-09-13-lane-landmarks
# frames: loop 1's gt.extract_frames into $LM_SCRATCH/frames (SAM_FRAMES), unlabeled via common.UNLABELED
$V inspect_landmarks.py               # what is visible
$V e1_truth.py                        # results/landmarks_<stem>.json, e1_truth.json, e1_summary.md, overlays/e1_*
$V diag_pins.py; $V diag_consistency.py   # two pin widths, which landmark sets agree
$V rescore_baselines.py               # loops 2-3 in all three truths
$V sam_lanes.py even3_k; $V sam_lanes.py zoom_lo_k
$V e2_detect.py --src loop3; $V e2_detect.py --src "loop3:student seg1024 gated (loop 3, tom_old only)" --tag loop3_1024 tom_old
$V e2_detect.py --src "loop3:student seg640 +teacher gated (loop 3)" --tag loop3_plus
for st in sample_input 20260112_121117 tom_old; do for m in even3_k zoom_lo_k; do $V e2_detect.py --src results/lanes_sam_${m}__${st}.json --tag sam_${m} $st; done; done
for t in loop3 loop3_plus sam_even3_k sam_zoom_lo_k; do $V e3_fit.py --tag $t; done; $V e3_fit.py --tag loop3_1024 tom_old
$V e4_camera.py
$V build_dataset_lm.py; $V train_lm.py lovo_tom_old 640 30; LM_BATCH=4 $V train_lm.py lovo_tom_old 1024 30
$V eval_seg2.py seg2_640_lovo_tom_old tom_old
$V tables.py; $V fill_readme.py; $V review_video.py
```
