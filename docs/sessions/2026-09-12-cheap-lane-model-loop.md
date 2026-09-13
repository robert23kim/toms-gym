# Cheap lane model loop — 2026-09-12

## What this was
Asked: "can we build a cheap bowling-lane-specific model, like the fitness pose model, run experiments
to validate it on data, and make a video at the end?" Self-paced `/loop` (19:00–22:40) that distilled
the lane into a YOLO11n student and scored it with the two SAM 2 loops' metric. Report + video in
`docs/research/2026-09-12-cheap-lane-model/`.

## What changed
- New research folder `docs/research/2026-09-12-cheap-lane-model/`: `README.md` (question, data,
  method, leave-one-video-out tables, plus / resolution / unlabeled sections, nine findings,
  engine recommendation, reproduce commands), 15 scripts (`common.py`, `camera_all.py`,
  `build_dataset.py`, `train.py`, `eval.py`, `postproc.py`, `hybrid.py`, `teacher_sam.py`,
  `ball_detect.py`, `build_plus.py`, `eval_unlabeled.py`, `bench.py`, `tables.py`, `fill_readme.py`,
  `make_review_video.py`), `results/` (106 JSON + `summary.md` + `bench.json`), `overlays/` (80 jpg),
  `video_script.json`, `review.mp4` (2:38, 21.5 MB, gitignored). Sent to the user twice via
  SendUserFile; the final cut includes the 1024 px finding.
- `CLAUDE.md`: new "Cheap Lane Model (research, 2026-09-12)" section with the keep-list.
- Memory: `cheap_lane_model.md` (+ MEMORY.md pointer).
- Nothing committed. The folder (27 MB, 9.4 MB results + 18 MB overlays) and the CLAUDE.md edit are
  uncommitted; see next steps.
- Trained weights, datasets, frames and per-frame predictions are in the session scratchpad
  (`/private/tmp/claude-502/-Users-toka-code-toms-gym/d71975f3-…/scratchpad/{runs,ds,frames,pred}`)
  and are lost on reboot; every number in the README comes from `results/*.json`.

## What we learned
- Only three annotated bowling videos exist anywhere; the production bucket's other "bowling"
  uploads are 31 KB synthetic clips. Two more real videos sat in `~/Downloads` (`bowling_video.mp4`,
  `IMG_0242.mov`). All five are the same alley.
- A 6 MB `yolo11n-seg` trained on two videos gives a lane on every frame of the third, including the
  frames where the bowler stands on it: Chardie 0.88 boards median (0.65 occluded), sample_input
  1.83 → 1.22 with 162 SAM-teacher frames, tom_old 3.15 at 640 px / 0.94 at 1024 px. 30 ms/frame CPU
  (58 at 1024) vs SAM 2 tiny 836 ms + a ball track.
- The student's real failure is *which* lane: the top-confidence box flips to the neighbour once the
  bowler leaves. One anchor per video (ball-path points, or loop 2's centre-jump rule in the gate)
  fixes it. Raw row-extreme line fits on a learned mask blow up on ~10 % of frames; a sanity gate
  (RANSAC inliers ≥ 0.7, positive and tapering width, centre near the video median) + carry costs
  nothing and holds.
- The 4-keypoint pose head fails everywhere (6-11 boards): it regresses the training lanes' geometry.
- Pseudo-labels help only where the geometry matches (sample_input yes, tom_old no). Resolution fixes
  tom_old's width (the 640 px mask swallows a gutter), not its confidence (60/409 frames fire at 1024).
- Student centre line → SAM 2 tiny prompts: 0.5-1.1 boards on pre-hit frames with no ball track.
- Tooling: ultralytics trains fine on MPS (two runs in parallel ≈ 25 s/epoch each, dataloader is
  single-threaded on macOS); `avc1` through OpenCV writes a playable H.264 mp4 without ffmpeg; the
  Bash tool's background waiters cap at 10 min, so long trainings need re-armed `until` loops or the
  loop's fallback wakeup.

## Still broken / next steps
- **Commit the folder** (`git add docs/research/2026-09-12-cheap-lane-model CLAUDE.md docs/sessions/2026-09-12-cheap-lane-model-loop.md`),
  as the SAM loops were — not done because nothing asked for a commit.
- **The student is not in the engine.** Wiring per the README's recommendation: student as tracker +
  lane picker + prompt source (gate + carry from `postproc.py`), SAM 2 tiny on 2-3 clean frames for
  the far-end calibration. The candidate weight is saved as
  `docs/research/2026-09-12-cheap-lane-model/lane_seg640_all3_plus.pt` (5.7 MB, gitignored).
- **Confidence on unseen placements** is the open problem (tom_old 60/409 frames at 1024 px). Only more
  camera placements pseudo-labelled by the SAM 2 teacher will move it; IMG_0242 needs a manual prompt
  because the ball detector fires on the rack.
- The 1024 px result exists for the tom_old fold only; the other two folds and a 640 px + far-end-crop
  variant were not run.
- Every number is against the hand corners that loop 2 showed are 1-3 boards off at the pin end on
  tom_old / Chardie; sub-board differences are not measurable until the pins-based truth exists.
- Next loop is briefed: `docs/research/2026-09-13-lane-landmarks/BRIEF.md` (landmarks as homography
  constraints + pins-based truth). Start it with `/loop read … BRIEF.md fully, then run it`.
- IMG_0242's polygon stops at the monitor stand: the model has never seen a non-person occluder.

## Verification
- Every table number is read from `results/*.json` by `tables.py` / `fill_readme.py`; the label
  pipeline was checked visually on nine frames (occluded / clean / post-throw per video) and the
  camera-warped labels against sample_input's hand per-frame corners (4.5 px mean).
- `eval.py` was mutation-checked on the one-epoch smoke model (409/409 frames, ~3 boards) before any
  real fold; the anchor selector was verified by Chardie's clean-frame median dropping from 59 to 0.9.
- Overlays were viewed for every held-out video and both unlabeled videos; the review video was
  frame-sampled after each of three renders (the second fixed an out-of-range frame crash and a
  training-set number in a header).
- Not verified: the student in the engine (never wired), any video from a different alley, and
  latency on Cloud Run (numbers are this Mac's CPU at 4 threads).
