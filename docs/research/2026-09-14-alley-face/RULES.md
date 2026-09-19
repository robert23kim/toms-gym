<!-- Moved verbatim from CLAUDE.md on 2026-09-19; CLAUDE.md keeps a pointer. -->
# Alley Face (research, 2026-09-14)

`docs/research/2026-09-14-alley-face/` (README, scripts, `results/*.json`, overlays; `review.mp4`
gitignored). The lane's markings as one constellation (foul corners, seven foul-line dots 1.8 in
behind the line, eleven guide dots at 7.04 ft on a 3-board pitch, seven approach dots at -11.7 ft,
seven arrows, ten pin bases, gutter lines) with one degree of freedom, a homography. What to keep:

- **Measure the marks, do not assume symmetry**: every dot row sits 0.4-0.7 in LEFT of the lane
  centre under the truths (1.8 in for the approach dots); `results/constellation.json` carries the
  measured positions, `x_rule_in` the symmetric ones. The visible lane edges confirm the annotated
  foul ends on tom_old only.
- **The face can be found with no ball path, mask or prompt** - chains of regularly spaced dark
  marks read as arrow rows, paired with rack-shaped white blobs (the ten pins merge into one white
  mass; px/in = width / 40.8 in, base row = top + 15 in), chance-corrected constellation score:
  right lane on 50 % of tom_old's throw frames (0.31 pre-hit, 0.62 median vs pins), 26 % of
  sample_input, 0 % of Chardie (720p). Arrows alone 13 % at 3 boards; the rack is what makes it
  findable. **The top-scoring face is the neighbouring lane on most frames**: pick the lane by the
  bowler or the ball, never by the score.
- **Aligning does not beat finding**: rack refit + arrows fix the far end (2-4 px) and the pre-hit
  frame, but the near-end rows (foul-line / guide dots) are not in a whole-frame black-hat pool on
  handheld video, so the joint fit is 0.81 vs E3's 0.62; gutter segments around a coarse lane pick
  the lip or the next lane. The mask student's near end (loop 4) remains the engine's floor.
- **Heatmap landmark models (U-Net, exact homography augmentation, LOVO)**: the per-landmark
  variant memorises positions (held-out tom_old arrows 0.20, dots 0, pins 0.96); the per-CLASS
  variant transfers appearance (arrows 0.92 recall at 3.7 px, precision 0.85 - the black-hat pool is
  5 % precise). Five videos of one alley cannot teach placement; collect other phones and angles.
- Harness: loop 4's modules `import common`, so this loop's shared module is `af.py`; a chain
  waiting on result files fired on probe runs' stale files (wait on the process); rank chains by
  spacing regularity, not length (1080p six-lane frames flood the budget with ceiling chains).
