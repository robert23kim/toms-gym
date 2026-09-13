# 2026-09-13 — Engine lane integration: the SAM lane research becomes pass 5

Ask: take the lane experiments (five research loops, 2026-09-12 to 09-14), implement the most
promising ones in the engine in a loop, and end with a side-by-side clip of the old and new engine
on the existing videos.

## Done

- `~/code/bowling-app/lane-engine`, branch `feat/sam-lane-calibration` (off `feat/situp-config`
  05267b1): new modules `lane_geometry.py`, `frame_alignment.py`, `sam_prompter.py`, `pin_rack.py`,
  `lane_calibration.py` under `src/bowling/lane_tracking/`, glue + re-render in
  `scripts/sam_lane_pass.py`, `--sam-lane` (+ `--sam-back`, `--no-far-crop`, `--pin-refit`,
  `--no-rerender`, `--sam-weights[-dir]`) on `scripts/debug_ball_motion.py`, summary fields, service
  reads them and passes the flag on `SAM_LANE=1`. 4 new test files (39 tests, mutation-checked
  guards). Fast suite: 602 passed in `tests/test_lane_tracking`, the 5 pre-existing failures on the
  base commit unchanged.
- Research folder `docs/research/2026-09-13-engine-lane-integration/`: `evaluate.py` (loops' metric,
  both truths), `run_engine.py`, `tables.py`, `make_review_video.py`, README with the table, the
  gates learned, recommendation and retro; `review.mp4` (~1 min, before/after per video).
- Numbers: lane MAE 6.4 / 166 / 13.2 -> 0.6 / 1.1 / 0.4 boards (pins truth, median); final board
  error 2.4 / 13.4 / 7.8 -> 2.4 / 3.6 / 2.2 (median over the last five frames on the lane surface).
- CLAUDE.md sections in both repos, memory `engine_lane_integration.md`, spec
  `docs/superpowers/specs/2026-09-13-sam-lane-calibration-design.md`, plan under plans/.

## Still broken / open

- Not deployed. The service image needs torch + ultralytics and `models/sam2.1_t.pt`;
  `feat/situp-config` has moved to 13b49b5 since the worktree was cut — rebase before merging.
- The pin-rack refit finds the one-column alias from the SAM lane (8 of 9 frames); it is opt-in
  and never fires under the gates. Needs a lane-independent pin detector.
- Chardie's product number is capped by the ball tracker losing the ball at frame 108/134; the
  deployed config has no Chardie track at all without `--yolo`.
- `scripts/lane_ab_report.py` in the engine repo carries a hardcoded Anthropic API key in source
  (pre-existing, not touched here) — rotate it and move it to an env var.
- Timings in the ablation logs were measured while other runs shared the CPU.

## Next

Merge (rebased), deploy with `SAM_LANE=1` and `--yolo`, then a tracker loop on the early ball loss
near the pins.
