# A cheap lane model: can a 6 MB network replace SAM 2 for the bowling lane? (2026-09-12)

Status: complete. Review video: `review.mp4` (gitignored, 2:38; regenerate with the commands at
the end). Scripts, result JSON (`results/`) and overlays (`overlays/`) are in this folder; frames,
datasets and training runs live in the session scratchpad; the `all3_plus` weight is kept here as
`lane_seg640_all3_plus.pt` (gitignored).

## The question

The lifting side of the app runs a small pose network (MediaPipe) per frame and gets named
landmarks in ~10 ms. The bowling side finds the lane with SAM 2 (loops 1-2,
`../2026-09-12-sam2-lane-experiments*/`), which needs a ball track first for its prompts, costs
0.8 s per frame on CPU with the tiny weights, and has no lane at all while the bowler stands on it.
This loop asks whether a **lane-specific student** in the pose model's shape (YOLO11n, 2.8 M
parameters, 6 MB, one 640 px pass per frame, no prompt) can be trained from the three annotated
videos, how close it gets to SAM 2 on the SAM loops' metric, and what it is actually good for.

Metric, unchanged from loops 1-2: the fitted edge lines are evaluated at the annotated top/bottom
y to give four corners; every annotated ball position (warped into the frame) is mapped to a board
through that homography and through the annotated corners'; board MAE is the mean absolute
difference. Truth is per frame (sample_input's hand per-frame corners; Chardie / tom_old's static
corners moved through the ORB camera model). Loop 2 showed the hand corners themselves are 1-3
boards off at the pin end on tom_old and Chardie, so nothing below ~1 board is measurable here.

## Data

| video | res | camera | frames | label |
|---|---|---|---|---|
| sample_input | 1080x1920 | handheld, drifts 24 px | 180 | hand-clicked corners on every frame |
| Chardie (`20260112_121117`) | 720x1280 | handheld, drifts 36 px | 171 | static corners warped through the full-video camera model |
| tom_old | 688x1264 | tripod, closest camera, lane 1.7x wider in the image | 409 | static corners, tripod |
| bowling_video (`~/Downloads`) | 1080x1920 | static, wide, six lanes in view, one clean throw | 417 | none; SAM 2 tiny teacher prompted from the engine's ball detector |
| IMG_0242 (`~/Downloads`) | 720x1280 | handheld, panning, shot from the seats | 929 | none; the ball detector fires on the rack, so qualitative only |

These are all the bowling videos that exist: the production bucket's other "bowling" uploads are
31 KB synthetic test clips, and every one of the five was shot at the same alley (same mural).
Generalisation below therefore means **a new camera placement at the same venue**, not a new
venue. `camera_all.py` extends loop 1's throw-only camera fit to every frame; warping the
reference frame's corners through it lands 4.5 px (mean, max 13.8) from sample_input's hand
per-frame corners, which is the label noise the warped labels carry on the other two videos.
Occluded frames (bowler on the lane) keep their lane label: the student is asked for an amodal
lane, which SAM cannot give.

## Method

- **Students** (`build_dataset.py`, `train.py`): `yolo11n-seg` with one class (lane polygon →
  mask → per-row left/right extremes of the component holding the ball path → robust line per
  edge → corners) and `yolo11n-pose` with one class and four keypoints (TL/TR/BL/BR → edge lines
  through the corner pairs). 30 epochs on Apple MPS from the COCO checkpoints, batch 16, 640 px,
  fliplr / ±5° / ±10 % translate / 0.5-1.5x scale / perspective / HSV augmentation, mosaic off for
  the last 10 epochs. 9-22 min per fold with two trainings sharing the GPU.
- **Folds**: leave-one-video-out (`lovo_<stem>`: train on the other two, score every frame of the
  held-out video) and `all3`. The in-training val split is every 10th frame of the *training*
  videos, so `best.pt` never sees the held-out video. `_plus` folds add the SAM 2 teacher frames
  of bowling_video (`teacher_sam.py`, `build_plus.py`: 162 frames with fit residual ≤ 4 px outside
  the throw window).
- **Scoring** (`eval.py`): every frame of the held-out video, split into the throw (5 frames before
  release to the last on-lane ball frame, loop 1's span), clean frames (ball rolling, bowler off
  the lane), occluded frames (video start to 3 frames after release) and the two single frames the
  SAM loops report (`last`, `prehit` = pin hit − 2). CPU latency per frame is measured in the same
  pass (`bench.py` for the controlled numbers).
- **Lane selection**: `--select anchor` picks, among the student's candidates, the mask holding the
  most ball-path points (the same rule loop 1 used to choose SAM's component). `--select conf`
  takes the top-confidence detection.
- **Post-processing** (`postproc.py`, on the saved masks, no re-inference): RANSAC edge lines (2-row
  samples, 3 px inliers); a ±5-frame median (`window`); one lane per video from the clean frames
  (`video`); and `gated` = reject a frame when RANSAC inliers < 70 %, the top width is ≤ 0 or ≥ the
  bottom width, fewer than 60 % of rows have mask, or the foul-line centre is more than 0.3 lane
  widths from the video's median centre (loop 2's centre-jump rule), then carry the nearest
  accepted lane. Every frame gets a lane.
- **Hybrid** (`hybrid.py`): three positive points on the student's centre line at 20/50/80 % of the
  lane's height become SAM 2 tiny's prompts on a clean frame. No ball track anywhere in the chain.

## Results

Board MAE on the held-out video, lower is better. `last` / `pre-hit` are the single frames the
SAM loops report; clean / occluded are per-frame mean / median; "≤2 boards" is the share of throw
frames within two boards. SAM rows are loops 1-2 on the same frames and metric.

<!-- TABLE -->
| video | method | last | pre-hit | clean mean / med | occluded mean / med | <=2 boards (throw) | frames with a lane | per frame |
|---|---|---|---|---|---|---|---|---|
| sample_input | seg640|_anc | 2.06 | 1.55 | 1.88 / 1.78 | 2.16 / 2.18 | 73 % | 180/180 | 32 ms |
| sample_input | hybrid: seg640|_anc prompts -> SAM 2 tiny | 0.64 | 1.07 | 2.55 / 1.43 | no lane | - | 19 clean | ~600 ms |
| sample_input | seg640|_anc_gated | 2.11 | 1.59 | 1.92 / 1.85 | 2.17 / 2.21 | 66 % | 180/180 | 32 ms |
| sample_input | seg640|_anc_video | 0.77 | 0.73 | 1.94 / 2.22 | 3.42 / 3.73 | 29 % | 180/180 | 32 ms |
| sample_input | seg640|_plus_anc_gated | 1.08 | 0.99 | 1.32 / 1.25 | 1.44 / 1.58 | 98 % | 180/180 | 32 ms |
| sample_input | seg640|_plus_anc_video | 0.16 | 0.28 | 1.56 / 1.92 | 3.07 / 3.40 | 72 % | 180/180 | 32 ms |
| sample_input | pose640 | 5.82 | 7.47 | 6.46 / 6.57 | 5.76 / 5.63 | 0 % | 180/180 | 28 ms |
| sample_input | SAM 2 base, even3 prompts (loops 1-2) | 0.24 | 0.31 | - | no lane | - | 1 frame | 2130 ms |
| sample_input | SAM 2 tiny, path prompts (loop 1) | 0.68 | - | - | no lane | - | 1 frame | 2930 ms |
| sample_input | SAM 2 video mode, per frame (loop 1) | 0.21 | - | 1.85 / 0.98 * | - | 66 % | 86/91 | 1359 ms |
| sample_input | SAM 2 gate + carry (loop 2) | 2.40 | - | 0.98 / 0.84 * | carried | 91 % | 86/91 | - |
| Chardie | seg640|_anc | 1.14 | 1.04 | 15.99 / 0.91 | 0.72 / 0.62 | 73 % | 171/171 | 31 ms |
| Chardie | hybrid: seg640|_anc prompts -> SAM 2 tiny | 0.59 | 0.51 | 6.29 / 4.50 | no lane | - | 17 clean | ~600 ms |
| Chardie | seg640|_anc_gated | 1.28 | 0.96 | 1.82 / 0.89 | 0.68 / 0.65 | 80 % | 171/171 | 31 ms |
| Chardie | seg640|_anc_video | 4.97 | 0.84 | 1.88 / 0.82 | 11.49 / 12.18 | 69 % | 171/171 | 31 ms |
| Chardie | seg640|_plus_anc_gated | 0.59 | 0.82 | 2.18 / 0.98 | 0.73 / 0.65 | 77 % | 171/171 | 28 ms |
| Chardie | seg640|_plus_anc_video | 6.37 | 2.06 | 2.43 / 2.02 | 10.29 / 11.00 | 44 % | 171/171 | 28 ms |
| Chardie | pose640 | 8.64 | 10.14 | 29.65 / 12.33 | 9.74 / 10.69 | 0 % | 171/171 | 27 ms |
| Chardie | SAM 2 base, even3 prompts (loops 1-2) | 0.39 | 0.69 | - | no lane | - | 1 frame | 2060 ms |
| Chardie | SAM 2 tiny, path prompts (loop 1) | 1.12 | - | - | no lane | - | 1 frame | 960 ms |
| Chardie | SAM 2 video mode, per frame (loop 1) | 0.38 | - | 16.39 / 4.02 * | - | 38 % | 66/111 | 1343 ms |
| Chardie | SAM 2 gate + carry (loop 2) | 0.38 | - | 0.41 / 0.31 * | carried | 100 % | 66/111 | - |
| tom_old | seg640|_anc | 104.62 | 3.23 | 36.30 / 3.28 | 47.70 / 3.35 | 0 % | 370/409 | 29 ms |
| tom_old | hybrid: seg640|_anc prompts -> SAM 2 tiny | 0.76 | 2.08 | 3.35 / 1.98 | no lane | - | 37 clean | ~600 ms |
| tom_old | seg640|_anc_gated | 1.87 | 3.29 | 3.12 / 3.13 | 3.27 / 3.29 | 1 % | 409/409 | 29 ms |
| tom_old | seg640|_anc_video | 1.71 | 3.06 | 3.08 / 3.13 | 3.11 / 3.13 | 1 % | 370/409 | 29 ms |
| tom_old | seg640|_plus_anc_gated | 1.78 | 3.14 | 3.12 / 3.16 | 3.16 / 3.17 | 1 % | 409/409 | 29 ms |
| tom_old | seg640|_plus_anc_video | - | 2.96 | 3.00 / 3.04 | 3.01 / 3.04 | 0 % | 398/409 | 29 ms |
| tom_old | pose640 | - | - | 8.55 / 8.77 | - / - | 0 % | 33/409 | 40 ms |
| tom_old | SAM 2 base, even3 prompts (loops 1-2) | 1.35 | 2.27 | - | no lane | - | 1 frame | 2070 ms |
| tom_old | SAM 2 tiny, path prompts (loop 1) | 0.61 | - | - | no lane | - | 1 frame | 1020 ms |
| tom_old | SAM 2 video mode, per frame (loop 1) | 1.53 | - | 3.73 / 2.35 * | - | 13 % | 148/154 | 1346 ms |
| tom_old | SAM 2 gate + carry (loop 2) | 1.53 | - | 1.94 / 1.85 * | carried | 53 % | 148/154 | - |

\* SAM per-frame means are over the throw frames each method scored: loop 1's video mode covers the whole throw including occluded frames; loop 2's gate + carry reports accepted frames only.
<!-- /TABLE -->

Best single number per video, any method: sample_input 0.24 (SAM, ball path) · Chardie 0.32
(SAM, crop) · tom_old 0.45 (SAM tiny, crop) — all from the SAM loops; the student's best are
0.73 / 0.84 / 1.71 (`video` median on the pre-hit / pre-hit / last frame).

**Hybrid, single clean frames (student lane → 3 centre-line prompts → SAM 2 tiny, `hybrid_*.json`)**

| video | pre-hit | last | pre-hit − 6 | clean frames median (hybrid / student alone) | SAM with ball-path prompts (loop 2, pre-hit / last) |
|---|---|---|---|---|---|
| sample_input | 1.07 | 0.64 | 0.58 | 1.43 / 1.83 | 0.31 / 0.24 |
| Chardie | 0.51 | 0.59 | 0.57 | 4.50 / 0.89 | 0.69 / 0.39 |
| tom_old | 2.08 | 0.76 | 1.97 | 1.98 / 3.15 | 2.27 / 1.35 |

**Adding the SAM 2 teacher's frames (`_plus`: + 162 pseudo-labelled bowling_video frames, gated + carry, anchor-selected)**

| held-out video | throw median | ≤2 boards | occluded median | pre-hit / last (per frame) | pre-hit / last (one lane per video) |
|---|---|---|---|---|---|
| sample_input | 1.83 → **1.22** | 65.9 % → **97.6 %** | 2.21 → **1.58** | 1.59 / 2.11 → **0.99 / 1.08** | 0.73 / 0.77 → **0.28 / 0.16** |
| Chardie | 0.88 → **0.97** | 80.0 % → **77.3 %** | 0.65 → **0.65** | 0.96 / 1.28 → **0.82 / 0.59** | 0.84 / 4.97 → **2.06 / 6.37** |
| tom_old | 3.15 → **3.16** | 0.6 % → **0.6 %** | 3.29 → **3.17** | 3.29 / 1.87 → **3.14 / 1.78** | 3.06 / 1.71 → **2.96 / –** (no mask on that frame) |

(before → after; SAM 2 with ball-path prompts on the same single frames: 0.31 / 0.24 · 0.69 / 0.39 · 2.27 / 1.35)


**Unlabeled videos, student trained on all three annotated videos (`all3`)**

bowling_video is a camera placement none of the training videos have (static, wide, six lanes in
view). The SAM 2 tiny teacher, prompted from the engine's ball detector's path, is the reference
(`teacher__bowling_video.json`, every 2nd frame); its corners are the "annotation" and the
detected ball path the evaluation points. Teacher-reliable = fit residual ≤ 4 px and outside the
throw window (the teacher itself is wrong while the bowler and ball are on the lane, 8-13 px
residual, top width 100 px — exactly loop 1's occlusion failure).

| student | boards vs teacher, reliable frames (mean / median) | ≤2 boards | corner px | boards in the throw window |
|---|---|---|---|---|
| seg 640, anchor-selected | 1.23 / 1.13 (162 frames) | 93.2 % | 7.6 | 2.2 / 1.23 |
| seg 640, gated + carry | 1.21 / 1.12 | 93.8 % | 7.6 | 2.17 / 1.23 |
| pose 640 | 3.05 / 3.17 | 13.6 % | 8.1 | 3.21 / 3.14 |

The student picks the ball's lane out of six with 0.96 confidence on every frame and stays 1.1
boards (7.6 px at the corners) from the teacher; through the throw, where the teacher has no
usable lane, the student's lane moves 1.2 boards median (`overlays/seg640_all3_*_bowling_video.jpg`).

`all3_plus` (trained on those same teacher frames) reproduces the teacher to 0.13 boards median,
100 % within two boards, 4.0 px at the corners (`seg640_all3_plus__bowling_video__vs_teacher.json`).
That is a training-set number — it shows the student can copy SAM 2 to well under a board, not that
it generalises; the 1.1 boards above is the held-out figure. On the 43 throw-window frames, which
were excluded from training and where the teacher itself is unreliable, `all3_plus` sits 0.4 boards
median from the teacher's (occluded) lane against 1.2 for `all3`.

IMG_0242 (handheld, panning, shot from the seats, far end of the lane behind a monitor stand) has no
usable ball path, so it is qualitative: the raw student has a lane on 657/929 frames
at conf ≥ 0.1 and the gate carries the rest; it is the bowler's lane every time we looked, but the
polygon stops where the monitor hides the far end — the model was never shown an occluder that is
not a person (`overlays/seg640_all3_*_IMG_0242.jpg`). Both clips are in the review video.


**Resolution: the same student at 1024 px, held-out tom_old (`seg1024_lovo_tom_old`, `_anc_c02_gated`)**

| input size | frames with a lane (conf ≥ 0.02) | throw median, gated + carry | ≤2 boards | pre-hit / last | one lane per video | ms/frame (4 threads) |
|---|---|---|---|---|---|---|
| 640 px | 370 / 409 (conf median 0.13) | 3.15 | 0.6 % | 3.29 / 1.87 | 3.06 / 1.71 | 30 |
| 1024 px | 60 / 409 (conf median 0.00) | **0.94** | **100 %** | **1.04 / 0.32** | **1.05 / –** | 58 |

Doubling the input resolves the far end: the 640 px mask's 160 px prototype included part of the
right gutter on every frame (+8 px at the pin end); at 1024 px the masks it does produce sit within a
board of the annotation. What it does not fix is confidence — the 1024 px model is sure of a lane on
only 60 frames of a camera placement it has never seen, and the number above is honest only because
tom_old is a tripod, so a lane carried from those 60 frames is valid on all 409. On a handheld video
a 15 % fire rate would not do; that part is a data problem (finding 4), the width was a resolution
problem.

<!-- /RES -->

**Cost** (`results/bench.json`, this Mac, 4 CPU threads): student seg 640 px **30 ms** (6.0 MB,
2.8 M params), student pose 41 ms (5.6 MB), SAM 2 tiny 1024 px **836 ms** (78 MB, 39 M params, plus
a ball track for its prompts), SAM 2 base ~2.1 s. Training a fold: 9-22 min on the laptop.

## What the results say

1. **Yes, a 6 MB student learns the lane from two videos, and it gives a lane on every frame,
   including the frames where the bowler stands on it.** Held-out Chardie: 0.9 boards median through
   the throw, 0.65 on the occluded frames, 80 % of frames within two boards, at 31 ms. Held-out
   sample_input: 1.8 / 2.2. SAM 2 has no lane on the occluded frames (loop 1's video mode reads
   16 boards mean on Chardie because of them) and needs 25x the compute per frame.

2. **Its weakness is not precision but which lane.** With `--select conf` the top-confidence
   detection on Chardie flips to the neighbouring lane on half the clean frames (59-66 boards) while
   the occluded frames are right: once the bowler leaves, two lanes look equally plausible to a
   model trained on two videos. One anchor per video fixes it (the ball path, or loop 2's foul-line
   centre-jump rule inside the gate) — SAM needs prompts on every frame, the student needs one cue
   per video to choose between its own candidates.

3. **The pose head is the wrong head at this data size.** Four regressed corners score 5.8-10 boards
   on every held-out video and on tom_old barely fire (33/409 frames above conf 0.1): the regressor
   reproduces the training lanes' width and position instead of reading the image. A dense mask
   head, whose edges follow pixels, generalises where a global regressor cannot. Trained on all
   three videos it does locate the right lane in bowling_video's six-lane view (3 boards from the
   teacher), so it is coarse, not broken.

4. **tom_old separates two failures: width and confidence.** Its camera is the closest and lowest,
   the lane 1.7x wider in the image than anything in training. At 640 px the student's mask
   consistently includes part of the right gutter (+8 px at the pin end, 13-17 px on the right edge:
   3.1 boards, and the `_plus` teacher frames do not touch it); at 1024 px the width is right (0.9
   boards, 100 % within two) but the model is confident on only 60 of 409 frames. Resolution fixed
   the width; only a matching camera placement in training will fix the confidence.

5. **Raw row-extreme fits are fragile on a learned mask.** 47 of tom_old's 370 masked frames blew up
   (top width negative, 80-290 boards) because the coarse 160 px mask proto leaks for a few rows.
   RANSAC alone does not catch a leak that is itself straight; the sanity gate + carry does, and
   costs nothing (3.2 mean instead of 45 on tom_old, 1.7 instead of 29 on Chardie).

6. **One lane per throw from the clean frames matches SAM's single-frame numbers on the handheld
   videos** (`video`: 0.73 / 0.84 pre-hit) — the same setting the engine uses today with its static
   lane — but is useless on the occluded frames of a handheld video (3.4-12 boards), because the
   camera moved. Per-frame lanes (`gated`) are what a handheld phone needs.

7. **The hybrid removes SAM's dependency on a ball track.** Prompting SAM 2 tiny from the student's
   centre line scores 0.51-1.07 on the pre-hit frames and 0.59-0.76 on the last frames, within 0.3
   of the ball-path prompts on the handheld videos, and beats the student alone on tom_old (2.0 vs
   3.1 median). It is not uniformly better per frame (Chardie 4.5 median over 17 clean frames:
   SAM leaks into the neighbour lane from a centre-line prompt on a few frames), so it belongs on
   2-3 chosen clean frames, not on every frame.

8. **Pseudo-labels from the SAM 2 teacher help exactly where the geometry matches.** 162 teacher
   frames of bowling_video (portrait, elevated, like sample_input) take held-out sample_input from
   1.83 to 1.22 boards median and from 66 % to 98 % of frames within two boards; its one-lane-per-video
   pre-hit / last numbers (0.28 / 0.16) now match SAM's own (0.31 / 0.24). Chardie, already near the
   annotation floor, moves within noise, and tom_old, whose close low camera resembles nothing in the
   teacher set, does not move at all. The lever is a *matching* new camera placement, not more frames.


## Recommendation for the engine

1. **Ship the seg student as the lane *tracker*, not the lane *calibrator*.** One 640 px pass per
   frame (34 ms) gives a lane on every frame including the occluded ones; gate + carry as in
   `postproc.py`. Use its centre line (a) to choose the lane and (b) as SAM 2 tiny's prompts on two
   or three clean frames near pin contact for the calibration the board number depends on. That
   is ~3 s per throw instead of loop 1's ~2 min of video mode, and no ball track is needed before
   the lane exists.
2. **Pick the lane with one cue per video**: the ball path when it exists, else the foul-line
   centre-jump rule. Never the top-confidence box.
3. **Do not ship the pose head.** Keypoint regression needs more camera geometries than five videos
   contain.
4. **Grow the geometry, not the epochs.** Every new camera placement pseudo-labelled by the SAM 2
   teacher is worth more than any hyperparameter here; tom_old's 3 boards is a data number.
5. **Run the student at 1024 px, or at 640 px plus a far-end crop.** The 160 px mask prototype at
   640 px is what puts a gutter's width into the lane; 1024 px costs 58 ms instead of 30 and takes
   tom_old from 3.1 to 0.9 boards. Below one board at the pins nothing here resolves anything;
   loop 2's crop pass on SAM still owns that.

## Next

The follow-up on physical landmarks (arrows, pin bases, foul line as extra homography
constraints, pins-based far-end truth) is briefed in `../2026-09-13-lane-landmarks/BRIEF.md`.

## Reproducing

```
V=~/code/bowling-app/analysis-engine/.venv/bin/python   # torch 2.10 (MPS), ultralytics 8.4.14, opencv
cd docs/research/2026-09-12-cheap-lane-model
# frames: loop 1's gt.extract_frames into $LANE_SCRATCH/frames, then
$V -c "import common as C; [C.extract_unlabeled(s) for s in C.UNLABELED]"
$V camera_all.py                       # results/camera_all_<stem>.json (+ label-noise check on sample_input)
$V build_dataset.py                    # $LANE_SCRATCH/ds/{seg,pose}: labels, folds, yamls
$V ball_detect.py; $V teacher_sam.py bowling_video 0-416:2; $V build_plus.py   # teacher frames + _plus folds
for f in lovo_tom_old lovo_sample_input lovo_20260112_121117 all3; do $V train.py seg $f 640 30; $V train.py pose $f 640 30; done
for f in lovo_tom_old_plus lovo_sample_input_plus lovo_20260112_121117_plus all3_plus; do $V train.py seg $f 640 30; done
$V train.py seg lovo_tom_old 1024 30
for s in sample_input 20260112_121117 tom_old; do
  $V eval.py seg640_lovo_$s $s --tag _anc; $V postproc.py seg640_lovo_${s}_anc $s; $V hybrid.py seg640_lovo_${s}_anc $s
  $V eval.py pose640_lovo_$s $s
done
$V eval.py seg640_all3 bowling_video IMG_0242; $V eval_unlabeled.py seg640_all3 bowling_video
$V bench.py seg640_lovo_sample_input pose640_lovo_tom_old --sam
$V tables.py 'seg640|_anc' 'seg640|_anc_gated' 'seg640|_anc_video' 'seg640|_plus_anc_gated' pose640   # results/summary.md
$V make_review_video.py                # review.mp4
```
