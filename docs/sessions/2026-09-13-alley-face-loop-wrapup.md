# Alley-face loop wrap-up — 2026-09-13

## What this was
Autonomous `/loop` run of `docs/research/2026-09-14-alley-face/BRIEF.md` (folder dated by the
brief, run on 2026-09-13): does the lane have a "face" - a constellation of arrows, dot rows, pin
rack and gutters that can be found, aligned, tracked and learned with no ball path, mask or
prompt? Mid-loop session doc: `docs/sessions/2026-09-14-alley-face-loop.md` (E1-E6 narrative,
gotchas). This file is the hand-over state at the end of the session.

## What changed
- Commit `f2a55b6` — `docs(bowling): alley-face loop (2026-09-14)`: the loop folder (README with
  all tables, `af.py`, `e1_*`/`e2_*`/`e3_face.py`/`e4_align.py`/`e5_persist.py`/`e6_*`,
  `results/*.json`, 42 overlays, `review_face.py` + `video_script.py`), the mid-loop session doc
  and a new **Alley Face** section in `CLAUDE.md`. `review.mp4` (65 s, 7 MB) is gitignored and
  was sent to Tom in the conversation; regenerate with `review_face.py`.
- Memory note `alley_face_loop.md` (+ MEMORY.md pointer).
- Headline numbers (all vs loop 4's pins truth, throw medians): constellation found from the raw
  pool on 50 % of tom_old throw frames at 0.62 boards (0.31 pre-hit), 26 % sample_input, 0 %
  Chardie (720p); top score is the neighbouring lane on most frames; joint alignment 0.81 (near
  end has no classical detector); per-class heatmap U-Net transfers arrows to held-out tom_old
  (0.92 recall, 0.85 precision) and, fed to the constellation match, gives **0.43 boards at
  14 ms/frame** with no lane input (loop 4's student + pin refit: 0.41); per-landmark heatmaps
  memorise placement (0.20).

## What we learned
- The dot rows (guide 7.04 ft, foul-line -1.8 in, approach -11.7 ft) sit 0.4-0.7 in LEFT of the
  lane centre under every truth; a symmetric-by-rule model misplaces them by half a board.
- Two E4 designs were replaced during the run: nearest-point row assignment on a rectified band
  mis-assigns by a whole pitch under a coarse lane, and gutter segments around a coarse lane pick
  the lip or the next lane. The committed E4 is a rigid-pattern search in the mark pool with the
  gutters dropped; an intermediate variant scored 0.70 on tom_old but 2.24 on sample_input and is
  not reported anywhere.
- Class-level heatmaps (no identity) transfer; identity is the constellation's job. That reverses
  the "learned landmarks don't transfer" reading of loop 4.
- Harness: a chain waiting on `results/e3_face_*.json` fired on probe runs' stale files - wait on
  the process. Loop 4's modules `import common`, so the new shared module had to be `af.py`.

## Still broken / next steps
- **E6 folds `lovo_sample_input` and `lovo_20260112_121117` were still training at session end**
  (sample_input at 1100/2500 iterations after 59 min; Chardie queued). The chain
  `chain_e6.sh` in the session scratchpad
  (`/private/tmp/claude-502/-Users-toka-code-toms-gym/06d30d1b-ddda-464a-9f08-c75e215855ea/scratchpad`,
  `runs/heat_*`, `pred/heat_*`, `logs/e6_*.log`) keeps running unattended and ends with
  `e6_eval.py` into `logs/e6_eval.log`, but nothing folds the result into the repo. To finish:
  `cd docs/research/2026-09-14-alley-face && V=~/code/bowling-app/analysis-engine/.venv/bin/python;
  AF_SCRATCH=<that path> $V e6_eval.py; $V e6_face.py lovo_sample_input class; $V e6_face.py
  lovo_20260112_121117 class; $V tables.py; $V fill_readme.py`, then commit. If the scratchpad was
  cleaned, retrain per the README's Reproducing block (~50 min per fold pair on MPS). The README
  status line says this.
- The 0.43-board heatmap-pool result is one fold, one held-out placement; it needs the other two
  folds before it is more than a lead.
- Lane selection on multi-lane frames (bowler feet / ball anchor) and a near-end detector for
  handheld video are the open engine questions; the truths' near end is unverified on
  sample_input and Chardie.
- Repo hygiene unrelated to this loop: `.gitignore` and `frontend/.env.production` were already
  modified before the session and were left untouched.

## Verification
- Every README number comes from `results/*.json` produced in this session; overlays were viewed
  for tom_old f169 / f97, sample_input f117, bowling_video f207, the E4 near corners and the E6
  detections before the numbers were believed.
- The review video was rendered (1959 frames, 30 fps, 65.3 s) and four frames inspected.
- Not verified: the two pending E6 folds (see above); the class-heatmap 0.43 result on any video
  other than tom_old.
