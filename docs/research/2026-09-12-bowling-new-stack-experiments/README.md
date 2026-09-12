# Bowling board tracking: can a new stack replace the engine? (2026-09-12)

Status: experiments complete (E4 stopped early by request, one fold missing at 640 px).
Scripts, result JSON and two debug overlays are in this folder; frames, model weights
and the venv were left in the session scratchpad. Companion doc:
`ai-bowling-app-research.md` (what the shipping phone apps do).

## Why this was run

The lifting features (plank, pushup, curl) are reliable because MediaPipe BlazePose does
the hard perception step and the engine only does geometry on 33 landmarks. The bowling
board number is computed by ~24k lines of hand-tuned OpenCV in
`~/code/bowling-app/analysis-engine/src/bowling/` (HSV thresholds, gutter-darkness scans,
a function the docs call "untouchable"), tuned on one video, with no ground-truth board
annotations anywhere. The question was whether current foundation models can replace
that pathway outright rather than patch it.

Proposed stack: foundation-model lane calibration + learned ball detector + the existing
4-corner homography. Each piece was tested separately against the engine's own three
annotated videos with the engine's own metric (predicted ball center within 50 px of the
annotated center = hit), so numbers are comparable with
`analysis-engine/docs/detection-scoreboard.md`.

| Video | Res | Ball | Annotated ball frames | Lane width at pin end |
|---|---|---|---|---|
| sample_input | 1080×1920 | bright | 86 | 58 px (≈1.5 px per board) |
| 20260112_121117 ("Chardie") | 720×1280 | dark | 66 | 39 px (≈1.0 px per board) |
| tom_old | 688×1264 | dark | 148 | 67 px (≈1.7 px per board) |

The last column is the physical constraint every method hits: at the far end of the lane
one board is 1 to 2 pixels wide in phone video, so pixel-level edge error becomes
multi-board error there. The old engine's own white paper reports 4 px top-edge jitter
and a 10 px systematic offset, i.e. 1.5 and ~4 boards at the pins.

## Verdict

| Piece | Candidate | Result | Use it? |
|---|---|---|---|
| Lane corners | Gemini 3.5 Flash / 3.1 Pro pointing at 4 corners | 5 to 54 boards mean error; outlines the neighbouring lane; repeats disagree | No |
| Lane corners | SAM 2.1 (Meta, CPU, ~1.5 s/frame) prompted with points on the ball's path | 0.2 / 0.5 / 2.3 boards mean error on clean frames; fails when the bowler stands in the lane | **Yes**, multi-frame median + tap-to-correct |
| Lane corners | YOLOE-11l text prompt "bowling lane" | 44 to 66 boards; no mask on Chardie | No |
| Ball, no training | YOLOE-11s text prompt "bowling ball" (CPU, 0.2 s/frame) | 85 / 50 / 42 % recall at conf 0.01 (Feb 2026 COCO zero-shot: 26 / 0 / 0 %) | Not alone; good fine-tune start |
| Ball, no training | YOLOE-11l, YOLO-World-v2-l | no better / much worse | No |
| Ball labelling | Gemini 3.5 Flash, one frame per call | 83 / 68 / 94 % recall, 71 to 92 % precision, 4 to 12 px | **Yes**, offline auto-labeller |
| Ball, fine-tuned | RF-DETR nano, leave-one-video-out, 384 px | 62 / 61 / 97 % recall @0.05, 0.05 s/frame CPU | Comparable to Feb YOLOv8n, better precision and px error |
| Ball, fine-tuned | RF-DETR nano, 640 px (1 of 3 folds finished) | sample_input 72 % recall / 65 % precision / 8 px @0.05 | Better than YOLOv8n on the same held-out video (73 % / 41 % / 20 px) |

Bottom line: the lane half of the stack works today on CPU with no training. The ball
half needs a fine-tune, and the labelling bottleneck that stalled the February attempt is
now solvable with a VLM. Nothing here requires a GPU.

## E1: lane corners from a vision-language model (`e1_lane_corners.py`)

The model receives one frame and returns the four lane-surface corners as normalized
[y, x]. Metric: corners → the engine's board homography → applied to every annotated
ball position → absolute board difference vs. the homography from the annotated corners.

Gemini 3.5 Flash, frames 0 and 60, 3 repeats (18 calls, 13 to 53 s each):

| Video | Corner error px | Board MAE | Board max | ≤1 board |
|---|---|---|---|---|
| sample_input | 71 to 490 | 2.4 to 54.4 | 61.8 | 0 to 50 % |
| Chardie | 25 to 229 | 4.6 to 41.7 | 236 | 0 % |
| tom_old | 3 to 195 | 7.0 to 32.6 | 61 | 0 % |

Gemini 3.1 Pro (12 calls, 9 to 50 s each): board MAE 11 to 33. No better.

Failure modes (see `results/dbg_e1_sample_input.jpg`, green = truth, red = Gemini):
on sample_input the model outlined the adjacent lane, since nothing in one frame says
which lane is in play; on tom_old it put the left edge a third of the way into the lane.
Circling the ball and asking for "the lane this ball is on" (`--mark-ball`) fixed the
lane choice and brought the best repeats to 1.8 to 2.5 boards, but one repeat in three
still returned a >100-board outlier. VLM pointing is not pixel-precise enough for a
target that is 40 to 60 px wide.

## E1b: lane corners from a promptable segmenter (`e1b_lane_mask.py`)

SAM 2.1-base (ultralytics wrapper) on CPU, ~1.5 s per frame. The mask's per-row
left/right extremes are line-fitted; corners are the lines at the annotated top/bottom y;
same board metric as E1. Chardie's ground-truth lane is 39 px wide at the pins, so 1 px
of edge error there is 1 board.

| Prompt | sample_input MAE | Chardie MAE | tom_old MAE |
|---|---|---|---|
| Centroid of the Gemini quad, frame 0 / 60 | 68.0 / 0.9 | 9.6 / 150 | 2.3 / 2.1 |
| One point on the ball itself | segments the ball, not the lane | | |
| 5 points along the ball's path, pre-release frame | 0.35 | 17.3 (bowler in lane) | 0.92 |
| Same, frames 0 / pre-release / last | 0.52 / 0.35 / 5.3 | 9.7 / 17.3 / **0.48** | 2.3 / 0.9 / 2.3 |
| Median of those 3 frames | **0.22** (100 % ≤1) | 9.7 | 2.30 (43 % ≤2) |

YOLOE-11l with the text prompt "bowling lane" instead of SAM: 66 / no mask / 44 boards.

Reading: with a few points that are on the correct lane (which the ball trajectory gives
for free), SAM 2 finds the boundary to within ~7 px on 1080p and ~5 px on 720p, i.e.
sub-board at the arrows and 1 to 2 boards at the pins. Every failure was a frame with
the bowler standing in the lane (Chardie frames 0 and 60), so production must use frames
after release and a consensus over several. The 5 px under-coverage at the pin end on
tom_old (62 vs 67 px) is systematic and did not change when the top 20 % of rows were
excluded from the fit; it is at the resolution floor. See `results/dbg_e1b_sam2_tom_old_0.jpg`.

## E2: zero-shot ball detection with a text prompt (`e2_zero_shot_ball.py`)

Every annotated frame plus every explicit no-ball frame, imgsz 1280, top-1 box per
frame, no lane mask, no tracking. Feb 2026 baseline (COCO "sports ball"): 0 / 0 / 25.7 %.

| Model | conf | sample_input R / P | Chardie R / P | tom_old R / P | s/frame CPU |
|---|---|---|---|---|---|
| YOLOE-11s "bowling ball" | 0.01 | 50.0 / 71.7 | 42.4 / 37.3 | 85.1 / 96.2 | 0.20 |
| YOLOE-11s | 0.05 | 47.7 / 87.2 | 30.3 / 39.2 | 73.0 / 98.2 | |
| YOLOE-11s | 0.25 | 30.2 / 100 | 16.7 / 50.0 | 58.1 / 97.7 | |
| YOLOE-11l | 0.01 | 46.5 / 72.7 | 47.0 / 46.3 | 85.8 / 93.4 | 0.63 |
| YOLO-World-v2-l | 0.01 | 25.6 / 91.7 | 10.6 / 17.9 | 11.5 / 89.5 | 0.63 |

Position error when it hits: 3 px on tom_old, 9 to 14 px elsewhere. Misses are far-end
frames where the ball is under 10 px, and the dark ball on the 720p clip. Model size
does not help; the prompt is doing the work. Not a production detector on its own, but
a far better fine-tune starting point than COCO YOLO.

## E3: VLM as an offline auto-labeller (`e3_vlm_ball_label.py`)

Gemini 3.5 Flash, one frame per call, every third annotated frame (101 frames) plus
8 explicit no-ball frames per video.

| Video | Recall | Precision | Mean err px | Near ball (r≥10 px) | Far ball (r<10 px) | Pre-release frames wrongly labelled |
|---|---|---|---|---|---|---|
| sample_input | 82.8 % | 92.3 % | 12.0 | 14/14 | 10/15 | 0/8 |
| Chardie | 68.2 % | 71.4 % | 8.0 | 15/22 | – | 5/8 |
| tom_old | 94.0 % | 90.4 % | 3.8 | 47/49 | – | 5/8 |

Latency 4.5 to 12.5 s per frame. It finds every near-to-mid-lane ball on two of three
videos, loses the far-end ball once it is under 10 px, and ignores the "not in the
bowler's hand" instruction on pre-release frames (a trajectory filter removes those).
Good enough to label hundreds of frames per hour for a human to accept or nudge, which
is the step the February effort stalled on. Not a per-frame production path.

## E4: RF-DETR nano fine-tune, leave-one-video-out (`e4_build_dataset.py`, `e4_train_eval.py`)

Train on two videos (positives + ≤40 negatives each), test on the third. MPS training,
15 epochs, batch 4. Baseline: Feb 2026 YOLOv8n leave-one-out on two videos at 640 px.

384 px (all three folds, ~11 to 13 min each), conf 0.05 / 0.25:

| Held out | Recall | Precision | Mean err px | Recall @0.25 | CPU s/frame |
|---|---|---|---|---|---|
| sample_input | 61.6 % | 46.9 % | 9.1 | 44.2 % | 0.053 |
| Chardie | 60.6 % | 65.6 % | 6.2 | 28.8 % | 0.049 |
| tom_old | 96.6 % | 98.6 % | 13.5 | 88.5 % | 0.046 |

640 px (stopped after one fold, ~25 min per fold), conf 0.05 / 0.10 / 0.25:

| Held out | Recall | Precision | Mean err px | CPU s/frame |
|---|---|---|---|---|
| sample_input | 72.1 / 61.6 / 54.7 % | 65.3 / 93.0 / 100 % | 8.3 / 7.5 / 7.4 | 0.127 |

Against the YOLOv8n baseline on the same held-out video (sample_input, conf 0.05):
72.7 % recall, 41.2 % precision, 19.8 px. RF-DETR nano at 640 px matches recall with
much better precision and less than half the position error, trained on the same
few hundred frames. The tom_old fold (held out, trained on only 130 boxes) reaching
96.6 % / 98.6 % is the strongest cross-venue result in either repo. Resolution matters:
384 → 640 px added 10 points of recall on the 1080×1920 video. The Chardie and tom_old
640 px folds were not finished.

## Market check (`ai-bowling-app-research.md`)

AI Bowling, Track My Roll and LaneTrax all calibrate with exactly four lane corners:
automatic detection plus draggable handles that snap to the edges, remembered per
session. Camera behind the approach, offset to the bowling-hand side, high, tripod,
whole lane in frame, portrait. None supports arbitrary angles; rev rate is user-entered
or from a sensor. AI Bowling's release notes admit board accuracy was fixed only after
manual handles landed. Same conclusion as E1/E1b: automate the corners, keep the tap.

## Recommended stack

1. **Ball first, lane second.** Run the ball detector on every frame, keep the track, use
   5 points along it as SAM 2 prompts on frames after release, take the median of the
   fitted edges over several frames, show the four corners for a tap-to-correct.
   CPU only; ~1.5 s per prompted frame.
2. **Ball detector = fine-tuned small model, labels bootstrapped by Gemini.** Label the
   existing uploads with the E3 prompt, filter by trajectory continuity, hand-check, then
   fine-tune RF-DETR nano at 640 px (or YOLOE from its "bowling ball" checkpoint).
3. **Keep the homography, drop the engine.** The 4-corner board mapping in
   `lane_tracking/board_calculator.py` survives; the lane-edge heuristics do not.
4. **Report confidence at the pin end.** With 1 to 2 px per board there, quote board at
   the arrows as the primary number and pin-end board as a ±2 range. Tighter pin-end
   numbers need filming guidance (phone high, pin deck near the top of frame), not models.

Not tested: SAM 3 (CUDA-only; the CPU-only Cloud Run service could not run it anyway);
per-frame VLM tracking (ruled out on latency and far-end error); YOLOE fine-tuning.

## Reproducing

```
python3 -m venv venv && venv/bin/pip install torch torchvision ultralytics rfdetr google-genai opencv-python numpy
# frames: python -c "import gt; [gt.extract_frames(s) for s in gt.VIDEOS]"
venv/bin/python e1_lane_corners.py gemini-3.5-flash --frames 0,60 --repeats 3
venv/bin/python e1b_lane_mask.py sam2 --point track --frames 0,pre,last
venv/bin/python e2_zero_shot_ball.py yoloe --imgsz 1280
venv/bin/python e3_vlm_ball_label.py gemini-3.5-flash --every 3 --neg 8
venv/bin/python e4_build_dataset.py && venv/bin/python e4_train_eval.py
```

Gemini runs through Vertex with `backend/credentials.json` (google-genai SDK,
`vertexai=True, location="global"`; the REST endpoint 404s for 3.x models).
