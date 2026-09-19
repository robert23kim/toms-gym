<!-- Moved verbatim from CLAUDE.md on 2026-09-19; CLAUDE.md keeps a pointer. -->
# Cheap Lane Model (research, 2026-09-12)

`docs/research/2026-09-12-cheap-lane-model/` (README, scripts, `results/*.json`, overlays; `review.mp4`
gitignored, regenerate with the README commands; frames / datasets / runs were in the session
scratchpad). Asks whether a YOLO11n student (6 MB, 30 ms per frame on CPU, no prompt) can replace
SAM 2 for the lane, scored with the SAM loops' metric, leave-one-video-out on the three annotated
videos plus two unlabeled Downloads videos (`bowling_video.mp4`, `IMG_0242.mov` — all five are the
same alley). What to keep:

- **Seg head yes, pose head no.** `yolo11n-seg` trained on two videos gives a lane on every frame of
  the third, including frames where the bowler stands on it (Chardie 0.9 boards median / 0.65
  occluded, sample_input 1.2 with teacher frames, tom_old 3.1). The 4-keypoint `yolo11n-pose` head
  regresses the training lanes' geometry (6-11 boards) — do not ship it.
- **Its failure is *which* lane, not precision.** With several lanes in view the top-confidence
  detection flips to the neighbour. Select the candidate holding the most ball-path points
  (`eval.py --select anchor`) and gate with loop 2's centre-jump rule (`postproc.py gated`: RANSAC
  inliers ≥ 0.7, top width > 0 and < bottom width, foul-line centre within 0.3 lane widths of the
  video median, carry the nearest accepted lane). Never the top-confidence box.
- **Pseudo-labels help only where the geometry matches.** SAM 2 tiny prompted from the engine's ball
  detector labels a new video (`teacher_sam.py`); 162 such frames of bowling_video took held-out
  sample_input from 1.85 → 1.22 boards median (66 → 98 % within 2) and did nothing for tom_old.
- **Resolution fixes width, data fixes confidence.** At 640 px the mask swallows a gutter's width on
  tom_old (3.1 boards); the same student at 1024 px is 0.9 boards / 100 % within 2 (58 ms) but
  confident on only 60 of 409 frames of that unseen placement — gate + carry bridges it on a tripod,
  not on a handheld video.
- **Hybrid removes the ball-track dependency**: 3 points on the student's centre line as SAM 2 tiny
  prompts score 0.5-1.1 boards on pre-hit frames (`hybrid.py`); use it on 2-3 clean frames, not per
  frame. Recommended engine shape: student = tracker + lane picker + prompt source, SAM = far-end
  calibration. Labels for the two static-corner videos come from a full-video ORB camera model
  (`camera_all.py`, 4.5 px vs sample_input's hand per-frame corners).
