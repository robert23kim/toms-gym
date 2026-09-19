<!-- Moved verbatim from CLAUDE.md on 2026-09-19; CLAUDE.md keeps a pointer. -->
# Engine Lane Integration (2026-09-13)

`docs/research/2026-09-13-engine-lane-integration/` (README, `evaluate.py`, `run_engine.py`,
`make_review_video.py`, `results/`, `review.mp4` gitignored). The five lane loops above became one
pass of the analysis engine: branch `feat/sam-lane-calibration` in the worktree
`~/code/bowling-app/lane-engine` (off `feat/situp-config` 05267b1), `--sam-lane` on
`scripts/debug_ball_motion.py`, `SAM_LANE=1` in the service. Not deployed (the image needs torch +
ultralytics + `models/sam2.1_t.pt`).

- **Numbers** (board MAE of the annotated ball path through the engine's lane, per frame, loop 4's
  pins truth, median over the throw): sample_input 6.4 -> 0.6, Chardie 166 (the classical detector
  picked the neighbouring lane; 0 % ball detection followed) -> 1.1, tom_old 13.2 -> 0.4; 96-100 %
  of frames within two boards. The engine's own final board (median over the ball's last five
  frames on the lane surface): 2.4 / 13.4 / 7.8 boards off -> 2.4 / 3.6 / 2.2 (Chardie's tracker
  loses the ball at frame 108 of a 134-frame roll; sample_input's last on-lane frames are ~10
  before contact and the ball hooks 1.5 boards in them: tracker limits, not lane ones). `--yolo` is needed for any Chardie track; the deployed config has none.
- **The pass** (`src/bowling/lane_tracking/lane_calibration.py` + `lane_geometry.py`,
  `frame_alignment.py`, `sam_prompter.py`, `pin_rack.py`; glue and re-render in
  `scripts/sam_lane_pass.py`): rolling segment of the track -> ORB similarity per frame -> candidate
  frames (pin-hit −4…−10, −2, then +6…+30 past the track's end) -> SAM 2 tiny from three ball-path
  prompts -> gates -> far-end crop pass -> per-frame lane, per-position board, final board = median
  over the last five positions still on the lane surface (positions above the mask top + one
  far-end radius are the ball deflected into the pins) -> JSON + summary fields + re-rendered debug
  video. Every stage degrades to the last. Ablations: no crop 0.76 / 0.92 / 0.55; calibration
  frame −8 instead of −4: 0.57 / 1.09 / 0.15 (as good or better everywhere; default kept at −4).
- **What real tracker output needed that the research did not**: the longest forward-rolling run,
  not the whole track (approach junk + spikes); candidates past the track's end (the bowler still
  stands on the lane when the tracker loses the ball); two non-geometric gates because a bowler's
  legs pass residual/shape/prompt tests (the mask must reach the path's far end, and the same
  prompts on a frame six away, warped through the camera model, must give the same lane).
- **Pin-rack refit is opt-in (`--pin-refit`)**: initialised from the SAM lane it converged on the
  one-column alias on 8 of 9 standing-pin frames (margins 0.025-0.032); gated (margin >= 0.03, two
  agreeing frames, far-end centre shift <= 6 % of width) it never fires. The crop-only lane is within
  a board anyway; the rack is a research result, not a shipped stage.
- **Evaluator gotcha**: `evaluate.py` never mixes a config's calibrated frames with its static lane
  (an early version did and made the tom_old pre-hit number identical to the baseline's).
