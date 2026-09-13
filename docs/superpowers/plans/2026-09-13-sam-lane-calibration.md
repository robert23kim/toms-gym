# Plan: SAM lane calibration in the engine (2026-09-13)

Worktree `~/code/bowling-app/lane-engine`, branch `feat/sam-lane-calibration` off
`feat/situp-config` 05267b1 (the deployed lineage). Research folder
`docs/research/2026-09-13-engine-lane-integration/`. Python: the engine's `.venv`.

Iteration 0 - baseline: run the old engine (`--simple-detect`) on the three videos,
dump its static lane, score it (annotated + pins truths), keep its debug videos.

Iteration 1 - calibration core: `lane_geometry`, `frame_alignment`, `sam_prompter`,
`lane_calibration` (full-frame SAM only), `--sam-lane` in the script, JSON output,
service summary fields, re-render. Tests for each pure module (mutation-checked).
Run on the three videos, score per frame.

Iteration 2 - far-end crop pass. Score. Keep if it helps against the pins truth.

Iteration 3 - pin rack refit + metric homography. Score. Keep if it helps.

Iteration 4 - sweep the calibration frame (pin_hit - 2 / -4 / -6), pick the default.

Wrap - review.mp4 (side by side), README with the tables, CLAUDE.md sections in both
repos, memory, commits in both repos.
