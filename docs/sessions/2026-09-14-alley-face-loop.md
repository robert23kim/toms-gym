# 2026-09-14 — Alley-face loop (constellation detection of the lane's landmarks)

Autonomous `/loop` run of `docs/research/2026-09-14-alley-face/BRIEF.md`. Everything is in that
folder (README, scripts, `results/*.json`, `overlays/`, `review.mp4` gitignored). Loop 4's
`common.py` / `landmarks.py` are imported through `af.py` (this loop's shared module is not called
`common.py` because loop 4's modules import a `common`). Frames were not regenerated: loop 4's
scratchpad survived with all five videos' frames and was copied.

## What was done

- **E1.** Three dot rows measured on the lane plane through loop 4's all-landmark truth: guide dots
  at 7.04 ft (3-board pitch, 11), foul-line dots 1.8 in behind the foul line (5-board pitch, 7),
  approach dots at -11.7 ft (7). Every row 0.1-0.2 in rms on its grid and 0.4-0.7 in LEFT of the
  lane centre under the truth (1.8 in for the approach dots); the visible lane edges confirm the
  annotation's foul ends on tom_old, so the constellation carries the measured, off-centre
  positions. Per-frame visibility timeline (bowler / ball / pins in motion) for every point.
- **E2.** Whole-frame detectors, no lane prior: black-hat dark marks (two tiers), rack-shaped white
  blobs (the ten pins merge into one white mass; px/in = width / 40.8 in, base row = top + 15 in;
  centre and base within 1-2 px of the truth), LSD segments. Pool precision 0.6-5 %; arrows in
  the pool on 96 / 69 / 44 % of frames (tom_old / sample_input / Chardie), foul-line dots 96 / 28 /
  9 %, guide dots 43 / 16 / 0 %.
- **E3.** Chains of regularly spaced marks read as arrow / dot rows, paired with rack blobs (px/in
  consistent with the row's pitch), one DLT per pairing, chance-corrected constellation score,
  camera-placement priors, "a face needs its eyes" (>= 3 arrows explained). Right lane found on
  50 % of tom_old's throw frames (0.31 pre-hit, 0.62 median vs pins; far width 2 px), 26 % of
  sample_input's, 0 % of Chardie's; four lanes per frame on bowling_video, the ball's lane among
  them on 55 %. Ablation: arrows alone 13 % at 3 boards, + rack 45-55 %. Top score = the right lane
  on 40 % / 1 % / 10 %: the neighbour with the squarer arrows wins.
- **E4.** Rack refit + arrows as a rigid pattern from the pool + one weighted DLT: far end fixed,
  pre-hit frame improved (tom_old 0.31 -> 0.25), throw median not (0.62 -> 0.81; sample_input 1.73
  -> 1.92); near corners 14 / 24 px. The near-end rows are not in the pool on handheld video.
- **E5.** Landmark camera on 185/187 tom_old frames (7 landmarks after the pins fall), lane on every
  frame at 0.81; on sample_input worse than ORB (10.4 vs 4.2 px) - one wrong pattern-matched row.
- **E6.** 44-channel heatmap U-Net, exact homography augmentation, LOVO. Fold tom_old: in-distribution
  recall 0.6-1.0 per class at 2-4 px; held-out: pins 0.96, arrows 0.20, dots 0.00. Memorises the
  training videos' geometry, as loop 4's pose head and arrow class did. Other folds train after.

## Gotchas learned

- A chain waiting on `results/e3_face_*.json` fired on the probe runs' stale files; wait on the
  process, not the file.
- `import common` inside loop 4's modules shadows any `common.py` in the new folder: name the new
  shared module something else (`af.py`).
- The E2 recall of arrows against the model V (mean of three videos) is 0.5 lower than against the
  per-video V: score detectors against `truth_points_v`, not the constellation model.
- Chains: the arrows' V turns at the apex (dy sign flips) and their image spacing on an oblique
  view varies 0.6-1.6x; extrapolate x only and hold y in a band.
- Ranking chains by length floods the budget with ceiling chains on a 1080p six-lane frame; rank by
  spacing regularity.
- The rack fill cut (`sorted by fill[:12]`) dropped the true rack; rack pairing must be by
  px/in consistency with the arrow row, not by fill.
- Gutter segments taken around a coarse lane pick the gutter lip or the neighbour; rectified-band
  dot refinement under a coarse lane mis-assigns by a whole pitch.
- `zsh` treats `echo ==` / `===` as a command lookup error inside the Bash tool; `rtk` rewrites
  `grep -v` output into a "0 matches" summary - tail logs with `tail`, filter in Python.

## Open

- A near-end detector for handheld video (foul-line dots / gutter corner) is the missing piece for
  both alignment and persistence; the classical pool does not contain it and the heatmap model does
  not transfer it.
- The lane-selection anchor (bowler feet / ball) for multi-lane frames.
- The two remaining E6 folds; the class variant.
- Truth near end on sample_input / Chardie unverified (bowler / ball return over the foul line).
