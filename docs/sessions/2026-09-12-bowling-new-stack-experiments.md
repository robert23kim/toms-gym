# Bowling new-stack experiments — 2026-09-12

## What this was
Tom asked why the bowling board-tracking engine is so much less reliable than the
lifting features, whether a pretrained model could find the ball or lane, and then to
survey the 2026 model market and run experiments on a replacement stack rather than
patch the existing pathway. A self-paced loop ran the experiments; Tom stopped it once
the picture was clear and asked for the findings to be documented.

## What changed
- New research folder `docs/research/2026-09-12-bowling-new-stack-experiments/`:
  `README.md` (full findings + recommended stack), `ai-bowling-app-research.md`
  (how the shipping phone apps calibrate), the eight experiment scripts
  (`gt.py`, `gemini.py`, `e1_lane_corners.py`, `e1b_lane_mask.py`,
  `e2_zero_shot_ball.py`, `e3_vlm_ball_label.py`, `e4_build_dataset.py`,
  `e4_train_eval.py`), raw result JSON for every run, and two debug overlays.
- Memory note `bowling_new_stack_experiments.md` pointing at the report.
- No product code, engine code, or deployment was touched.

## What we learned
- **Why lifting is better:** MediaPipe BlazePose does the perception; the engine only
  does angle math on 33 landmarks (~4.7k lines). Bowling does its own perception with
  ~24k lines of hand-tuned OpenCV, needs a metric homography lifting never needs, and
  has zero ground-truth board annotations. The deployed service runs `--simple-detect`
  only; the fine-tuned YOLO in the repo never shipped (no ultralytics in the image).
- **Lane by VLM pointing fails:** Gemini 3.5 Flash / 3.1 Pro put the corners 5 to 54
  boards off and outlined the neighbouring lane on `sample_input`. Circling the ball
  fixed lane choice but one repeat in three still returned a >100-board outlier.
- **Lane by SAM 2.1 works on CPU:** prompted with 5 points along the ball's path on
  post-release frames, board MAE 0.22 / 0.48 / 2.30 on sample_input / Chardie /
  tom_old, ~1.5 s per frame. Only failures were frames with the bowler standing in the
  lane, so production needs a median over several post-release frames plus a
  tap-to-correct. A single point ON the ball segments the ball, not the lane.
- **Pin-end resolution floor:** one board is 1.0 to 1.7 px wide at the far end of these
  videos, so ±2 boards there is the limit for any method (the old engine's own 4 px
  jitter / 10 px offset was already 1.5 to 4 boards). Fix is filming height, not models.
- **Zero-shot ball:** YOLOE-11s with the text prompt "bowling ball" = 85 / 50 / 42 %
  recall at conf 0.01 (Feb COCO "sports ball" test: 26 / 0 / 0 %). YOLOE-11l no better,
  YOLO-World-v2-l much worse. Prompt, not capacity, is doing the work.
- **Gemini as labeller:** 83 / 68 / 94 % recall, 71 to 92 % precision, 4 to 12 s per
  frame; loses the ball under ~10 px and ignores "not in the bowler's hand". Viable for
  offline auto-labelling, not runtime.
- **RF-DETR nano fine-tune, leave-one-video-out:** 384 px recall 62 / 61 / 97 % at
  conf 0.05 (tom_old held out: 96.6 % / 98.6 % precision, trained on 130 boxes). 640 px
  on sample_input: 72 % R / 65 % P / 8 px vs YOLOv8n's 73 % / 41 % / 20 px on the same
  held-out video. 384 → 640 px added 10 points of recall on 1080×1920.
- **Market:** AI Bowling, Track My Roll and LaneTrax all calibrate with four draggable
  lane corners (auto-detect + snap), prescribe camera behind the approach offset to the
  bowling-hand side, high, tripod, portrait. Rev rate is user-entered or from a sensor.
  AI Bowling has <1k downloads and no public accuracy evidence.
- **Vertex gotcha:** Gemini 3.x on Vertex 404s via the REST `generateContent` endpoint
  (both `global` and `us-central1`, v1 and v1beta1) but works through the google-genai
  SDK with `vertexai=True, location="global"` and `backend/credentials.json`.
  `gemini-2.5-flash` works via REST on the regional host.
- **SAM 3** hard-requires CUDA (8 to 20 GB VRAM), so it could not be tested here and
  cannot run on the CPU-only Cloud Run service. Its point-prompt tracking is within a
  point of SAM 2.1 on easy footage anyway; the gains are on text prompts and long video.

## Still broken / next steps
- E4 at 640 px has only the `sample_input` fold; the Chardie and tom_old 640 px folds
  were killed mid-training when Tom stopped the loop. Rerun
  `venv/bin/python e4_train_eval.py` at 640 px if the RF-DETR vs YOLOE decision needs
  all three.
- Nothing is built. Recommended order in the README: ball detector → trajectory →
  SAM 2 prompts → median edges → existing homography → tap-to-correct; bootstrap ball
  labels from existing uploads with the E3 Gemini prompt; keep
  `lane_tracking/board_calculator.py`, retire the lane-edge heuristics.
- Ground-truth **board** annotations still do not exist anywhere; the board metric in
  these experiments is relative to the hand-clicked lane corners, not to a measured
  board. Adding board numbers to `annotation.json` is a prerequisite for a real accuracy
  claim.
- The experiment venv, extracted frames (236 MB) and model weights lived in the session
  scratchpad, which is gone. Reproduction steps are in the README.

## Verification
- Every number in the README is copied from the JSON in `results/` (E1/E1b/E2/E3
  complete; E4 384 px complete, 640 px one fold). Nothing was deployed or tested in
  production; no unit tests were run because no product code changed.
- The E4 agent's own `e4_results.md` was never written (stopped before its report), so
  the E4 section was assembled from `e4_runs/res384_ep15/summary.json` and the 640 px
  `eval.json`, both copied into `results/`.
- Experiment processes confirmed dead (`pgrep` returned 0) before writing this.
