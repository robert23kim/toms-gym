# Glasses-POV bowling tracking (research, 2026-10-10)

`docs/research/2026-10-10-glasses-pov-tracking/` (README, scripts, `results/*.json`, `experiments/*/NOTES.md`, overlays; `showcase.mp4` and `work/` gitignored). Meta-glasses first-person clips, 11 videos, 10 with a throw. Rules learned in this loop:

## What to keep
- **Cut to release..pin hit and give the tracker both frames.** The ball is out of frame from rel-40 to rel-2 (backswing) and only a sliver is in hand at rel-60..-50. Cuts: `work/cuts/cuts.json`. Cost: nothing detects release or pin hit; window_err is 0 by construction on dev.
- **Track from the release frames, not from the YOLO chain.** The big blurred ball (r 105-135 px) in release..release+10 is never linked by the YOLO chain (starts 8-11 frames late, baseline recall 72.0 dev / 43.9 holdout). sam2-video backward propagation, cam-diff backward extension and NCC backward relay recover it (95-98 % dev).
- **Fixed purple hue window beats learned appearance.** Hue 112-170, S >= 30: 97.5 % dev recall vs 17-24 % for H-S back-projection (`experiments/appearance-prior/results/`). The ball washes out along the roll (S 157 -> 50, V 90 -> 150) and the pin deck reflects the purple backdrop.
- **Compensate the camera before measuring motion.** ORB + RANSAC homography per pair (half-size grey, 2.5 s per cut) is the base of cam-diff, appearance-prior and wildcard. Far end: argmax of blackhat x |frame - warp(prev)| x purple within the gate was within 12 px on 22/23 and 23/23 frames vs hue 2/23 and 0/23.
- **Re-measure the radius on the purple component.** The residual of a dark ball is only its rim; raw residual r under-reads 3-20x (`experiments/cam-diff/NOTES.md`).
- **Pool detector scales.** The fine-tuned YOLO11n finds the release ball (r 60-130) only at imgsz 320/640 and the far ball (r 4-13) only at native. Four pooled scales: dev recall 91.9 vs 72.0 chain baseline (`experiments/detector-tiling`).
- **Prompt SAM with a track, then take the lane from SAM.** Only the SAM per-frame lane gives a board (lane_err 0.7-2.1 dev); the static lane gives lane_err 76-300 boards. Feed the lane pass the segment where ORB has reliable shifts (release+8..pin_hit for sam2-video).
- **Predict the image row from camera-stabilised image velocity; take only u from the lane filter.** Z = K/(y - y_vp) jittered fills 65-86 px per frame (`experiments/lane-first`).
- **One scorer, one track format, mutation-checked.** `score_tracks.py` on a real track: as-is 100, +100 px 15.4, empty 0.
- **Show interpolated points differently.** Gaps <= 6 are interpolated; `make_showcase.py` draws them orange, tracked cyan.
- **Sensitivity of the method choice goes in the write-up.** Choice flips from sam2-video to detector-tiling if 191913's board_err 0.0 is excluded.

## What does nothing or hurts
- **Far-end tiling with 2x/3x crops**: 16-20 % far-band recall vs 91 % at native. **YOLO-World "bowling ball"**: 0 % far on every dev stem.
- **Learned H-S histogram appearance prior**: 17-24 % dev recall (thresholds 10/20/40/80).
- **YOLO boxes as extra candidates in appearance-prior**: 0.7 % alone, +0 on top. YOLO radii stay 20-25 px at every distance.
- **Farneback flow residual after a global affine**: one-step oracle 3/35 and 2/27 mid-lane.
- **Static lane on a moving head camera**: no final_board on any dev stem.
- **Letting the engine SAM lane pass handle the handheld 09-19 video 185121 and the gutter ball 191820**: refused (residual 9-58 px); back=10, r x3 and a -8 frame retry change nothing. appearance-prior also refuses 190115.
- **appearance-prior as the chosen method**: 98.8 holdout recall, but board <= 3 on 2/5 and none on 192636.
- **Per-experiment overlays as board evidence**: raw per-frame tracks over one lane quad swirl and cross gutters. Use the camera-compensated `overlays/final__*.jpg`.

## Harness gotchas
- Every frame index is in source numbering; cut frame k = cut_start + k. `r_frame_rate` says 120; the rate is 30.
- ffmpeg 9 has no drawtext; burn text with `cv2.putText`.
- Boards count from the right gutter (right-hander). Wrong-way convention reads 16.5-30.5 boards off.
- Track frames run to the cut end (ball into the pit); trim at pin_hit_frame before rendering. A 3-blob false hold appeared in 185121 at 299-306 (ball out of frame).
- A circle drawn after the last lane frame lands on gutter objects (191913, ~45 px right of the ball, f500-506). Stop it at `last_lane_frame`.
- An outlier first point near the foul line draws a long diagonal in the top-down panel (192636 f443). Trim jumps > 6 boards or > 10 ft.
- The pin rack in the top-down diagram: headpin nearest the bowler.
- Do not read holdout truth in experiments. `track.py` was checked by a static scan of 57 modules and an audit hook (0 opens).
- Run one torch process at a time on MPS (SAM 0.51 s/frame MPS vs 1.12 s CPU); the engine lane pass takes 43-195 s per video.
- Truth board uncertainty is 1-1.05 boards; do not tune below it. Gate: board_err <= 3, recall pass per `score_tracks.py`.
- Holdout truth was released only after scoring; label it from the cache, not from the experiment outputs.
