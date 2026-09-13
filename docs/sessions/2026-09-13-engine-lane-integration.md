# Engine lane integration: the SAM lane research becomes pass 5 — 2026-09-13

## What this was
Asked to read the five bowling-lane research loops (2026-09-12 to 09-14), implement the most
promising parts in the analysis engine in a loop, and finish with a side-by-side clip of the old
and new engine on the existing videos.

## What changed
- **Engine** worktree `~/code/bowling-app/lane-engine`, branch `feat/sam-lane-calibration`
  off `feat/situp-config` 05267b1 (the deployed lineage), two commits:
  - 453c6cc `feat(bowling): SAM lane calibration pass (--sam-lane) from the tracked ball path`:
    `src/bowling/lane_tracking/{lane_geometry,frame_alignment,sam_prompter,pin_rack,lane_calibration}.py`,
    `scripts/sam_lane_pass.py` (boards, summary fields, re-render), flags on
    `scripts/debug_ball_motion.py` (`--sam-lane`, `--sam-back`, `--no-far-crop`, `--pin-refit`,
    `--no-rerender`, `--sam-weights[-dir]`), `service/app.py` passes the flag on `SAM_LANE=1` and
    reads `final_board` / `entry_board` / `lane_edges` from the summary, `fetch_dev_assets.sh`
    pulls `models/sam2.1_t.pt`, CLAUDE.md section, 4 test files / 39 tests.
  - 668ff27 `fix(bowling): extend calibrated edge polylines to the pin row for the bird's-eye render`
    (the renderer clamps outside the polyline; a rolling ball above the mask top read board 13
    instead of 18 on tom_old).
- **toms_gym** commits ef1dec4 and ed4cccf: `docs/research/2026-09-13-engine-lane-integration/`
  (`common.py`, `evaluate.py`, `run_engine.py`, `tables.py`, `make_review_video.py`,
  `fill_readme.py`, `video_script.json`, README with table / findings / recommendation / retro,
  `results/`, `overlays/`; `review.mp4` 55 s gitignored), spec
  `docs/superpowers/specs/2026-09-13-sam-lane-calibration-design.md`, plan under `plans/`,
  CLAUDE.md section "Engine Lane Integration", memory `engine_lane_integration.md`.
- **Numbers** (board MAE of the annotated ball path through the engine's lane, per frame,
  pins-based truth, median over the throw): sample_input 6.4 → 0.6, Chardie 166 (classical
  detector chose the neighbouring lane; 0 % ball detection) → 1.1, tom_old 13.2 → 0.4; frames
  within two boards 0 % → 96 / 97 / 100 %. Engine's final board (median over the last five
  positions on the lane surface): 2.4 / 13.4 / 7.8 boards off → 2.4 / 3.6 / 2.2.
- Ablations (`results/summary.md`): no far-end crop 0.76 / 0.92 / 0.55; calibration frame −8
  instead of −4: 0.57 / 1.09 / 0.15 (as good or better everywhere, default left at −4); pin refit
  on: identical to off (it never fires).

## What we learned
- Real tracker output needs four things the research (which prompted from the annotation) never
  did: use the longest forward-rolling run of the track, not the whole track (approach junk +
  spikes at the pins); try candidate frames up to 30 frames past the track's end (the tracker
  loses the ball while the bowler still stands on the lane); a bowler's legs pass every geometric
  gate, so require the mask to reach the path's far end and to be static across two frames six
  apart under the camera model; neither the mask top nor the track's end is "the pins" — the SAM
  mask stops 10-20 px short of the pin bases and the tracker's last positions are the ball
  deflected into the pins (a pin-row crossing rule was tried and was worse, board 29 vs truth 17).
- The pin-rack refit from the landmarks loop, initialised from the SAM lane, converges on the
  one-column alias on 8 of 9 standing-pin frames (margins 0.025-0.032); loop 4's 0.03 margin is
  not sufficient. Gated by margin, cross-frame agreement and far-end centre shift it never fires.
- The tracker's ball radius is a fixed 22-33 px; at the pins the ball is 5-8 px. A far-end radius
  from the local lane width (a tenth of it) is what the on-lane test needs.
- Ten engine runs in this loop; eight failed on one of the above. Editing modules while a batch
  imports them produced two runs with mixed code (v5, v8's sample_input).
- `feat/situp-config` moved to 13b49b5 in another session while this worktree sat at 05267b1.

## Still broken / next steps
- **Not deployed.** Needs torch + ultralytics and the 78 MB `sam2.1_t.pt` in the service image;
  rebase `feat/sam-lane-calibration` onto `feat/situp-config` 13b49b5 first; ship with `--yolo`
  (the deployed config has no Chardie track at all).
- **Ball tracker is now the largest product error**: Chardie loses the ball at frame 108 of a
  134-frame roll while it hooks 3 boards; sample_input's last on-lane frames are ~10 before
  contact. A tracker loop on the last 20 frames is the next win.
- Pin-rack refit stays opt-in until a pin detector that does not start from the lane exists.
- Calibration frame default (−4) is worth a sweep on more videos (−8 was better on all three).
- `scripts/lane_ab_report.py` in the engine repo has a hardcoded Anthropic API key in source
  (pre-existing, untouched): rotate it.
- Ablation timings were measured with other runs sharing the CPU.

## Verification
- Engine fast suite on the branch: 1067 passed, 11 skipped, 5 failed — the same 5 fail on the
  base commit 05267b1 (`test_tracker.py` YOLO cases, `test_service_app.py` metric clips).
  `tests/test_lane_tracking/`: 602 passed. New guards mutation-checked (component-by-prompts,
  outlier pin drop, static-object check).
- All numbers above come from `evaluate.py` on the final `after` run (config
  `--simple-detect --yolo --sam-lane`) and the `before` / `before_yolo` runs of the deployed
  engine; `review.mp4` was regenerated from that run and frames inspected.
- Not verified: anything on Cloud Run; behaviour on videos other than the three annotated ones.
