# Baseline: engine on the glasses-POV cuts (2026-10-10)

Engine ad2c96e (exp/r2-glasses-pov), input = work/cuts/<stem>.mp4, 4 configs x 10 cuts = 40 runs, all rc 0,
--jobs 2 (wall times under 2-way contention). Scored by score_tracks.py; rows in results/baseline.json,
tracks in results/tracks_baseline/. 191900 has no cut (no throw), so it is not run. No truth file missing.
Cells are recall % / board_err ("-" = no final_board). (H) = holdout.

| config | 185121 | 185331 | 185645 | 185454 | 190115 | 191253 (H) | 191820 (H) | 191913 (H) | 192142 (H) | 192636 (H) | dev mean recall | holdout mean recall | pass dev / holdout |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| service | 0 / - | 0 / - | 3 / - | 38 / - | 0 / - | 0 / - | 8 / 6.5 | 9 / - | 0 / - | 0 / - | 8.3 | 3.4 | 0/5 / 0/5 |
| yolo | 0 / - | 0 / - | 0 / - | 48 / - | 0 / - | 0 / - | 0 / 32.5 | 30 / - | 0 / - | 0 / - | 9.6 | 6.1 | 0/5 / 0/5 |
| yolo_chain | 89 / - | 57 / - | 86 / - | 60 / - | 69 / - | 92 / - | 0 / 6.5 | 30 / - | 41 / - | 56 / - | 72.0 | 43.9 | 0/5 / 0/5 |
| yolo_chain_sam | 89 / - | 57 / 0.5 | 86 / 3.5 | 60 / 2.5 | 69 / 0.5 | 92 / 0.5 | 0 / 6.5 | 30 / 2.0 | 41 / 4.0 | 56 / 5.5 | 72.0 | 43.9 | 1/5 / 1/5 |

**Best config by dev mean recall: yolo_chain_sam** (72.0 %, tied with yolo_chain, whose track is identical; the SAM
pass only adds the lane and the board). It passes 1 of 5 dev (190115) and 1 of 5 holdout (191253). Holdout mean
recall drops to 43.9 %.

## Systematic failures (dev overlays overlays/baseline__*; holdout overlays were not opened)
- service and yolo (no chain): the track sits on the near lane / the frame bottom (pre-release ball in hand, lane
  markings), never on the rolling ball: dev recall <= 3 % on 4 of 5 stems; only 185454 gets 38-48 %.
- yolo_chain starts 8-11 frames after release on all 5 dev stems and 4 of 5 holdout (191820: 25): the big blurred ball at the
  frame bottom (truth r 55-130 px) is never linked, which caps recall at 57-60 % on 185331 and 185454.
- The chain's end is unreliable (pin window_err 5-26 dev, up to 46 holdout): it stops early or runs past pin hit.
- The static lane is meaningless on a moving head camera: lane_err 76-300 boards on every static-only row, and the
  static path gives no final_board on any dev stem. Only the SAM per-frame lane gives a board (lane_err 0.7-2.1 dev).
- SAM lane calibration refuses 185121 (residual 9 px; mask top 519 px short of the path's far end), so no board;
  on the holdout gutter ball 191820 it refuses too (residual 33 px) and the chain tracks 0 % of that throw.
- Board convention is right: |(40 - final_board) - truth| is 16.5-30.5 on every row where SAM produced a board, against 0.5-6.5 unflipped (the one
  exception is a static-lane board, yolo 191820: 35.0, flipped 2.5, a gutter ball on a non-calibrated lane).
- Board errors where SAM ran on dev: 0.5, 3.5, 2.5, 0.5 (185645 at 3.5 is just over the gate, truth unc. 2.0);
  so recall, not the board, is what fails 185331 and 185454.
