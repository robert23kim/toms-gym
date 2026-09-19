<!-- Moved verbatim from CLAUDE.md on 2026-09-19; CLAUDE.md keeps a pointer. -->
# Lane Landmarks (research, 2026-09-13)

`docs/research/2026-09-13-lane-landmarks/` (README, scripts, `results/*.json`, overlays; `review.mp4`
gitignored). Physical landmarks as the lane ruler; what changes what to ship:

- **The hand-clicked corners are 1-2 boards off at the pins and every earlier far-end number was
  measured against them.** The ten-pin rack (bases at rule-book coordinates, 7-10 spacing 36 in of
  41.5) gives the far end: the annotation is 10 % too wide on sample_input (flat gutters at the deck
  look like lane), 4 % too wide on Chardie, 7 % too narrow and 4 px left on tom_old. The arrows, an
  independent ruler at 15 ft, agree with the pins to ~1 px. Use `common.truth_corners(stem, f,
  "pins")` (stored per video in `results/landmarks_<stem>.json`) and report the `annotated` and
  `pins` columns side by side; re-scored, loop 3's tom_old student is 1.6 boards, not 3.2, and loop
  2's far-end crop is the best SAM method on sample_input (0.15), not the worst.
- **Refit the homography from the detected pin bases on every frame the pins stand.** Rack template
  fit initialised from the student's (or SAM's) lane, ±0.12 lane widths, coarse grid + hill-climb,
  0.8 s CPU as written: loop-3 student sample_input 1.19 → 0.37, tom_old 1.61 → 0.41 boards
  median vs pins (1.83 → 0.77 vs the hand corners, which never saw a pin); far-end width error
  12 / 6 / 3 px → about 1 px. Ten pins beat two. **The per-frame refit floors at ~0.4 boards on
  tom_old whatever lane goes in** (0.26-1.62 → 0.35-0.41): the rack fit's own noise; pool the rack
  over the standing-pin frames through the camera model rather than fitting each frame. **Guard the one-column alias**: the rack shifted by
  one pin (6 in) still covers six of seven columns and won on 2-4 % of frames at 720p; require the
  score to beat both ±1-column shifts by a margin, and it poisons every frame that carries those pins.
- **Arrows cannot fix the far end** (seven x-only constraints at one depth, extrapolated 45 ft):
  `corners+arrows` is worse than the corners alone. With the pins they define the lane with no
  foul-line input (pre-hit 0.05 boards) and make a per-frame camera model that beats ORB on
  sample_input's hand corners (4.0 vs 5.3 px, 2.4 vs 5.2 at the pin end) — only while the pins
  stand; the arrows alone are near-collinear.
- **The mask student's near end is as wrong as its far end**: foul-line corners 19 / 12 px (3 / 2
  boards) off on sample_input, 9 / 5 px on Chardie. Fixing the far end alone leaves Chardie's board
  error where it was; gradient snapping made it worse. A foul-line / gutter-edge landmark is the
  next detector to build. **Learned arrows fail two ways, measured per class on the training videos'
  val split:** with mosaic the arrow class has AP 0 even in-distribution (half-scale tiles put a 6 px
  arrow under the 8 px stride, it never trains); without mosaic it reaches AP50 0.7 in-distribution and
  0 detections on a new video even at conf 0.001 - it memorises positions, like loop 3's pose head.
  1024 px training crashes in ultralytics' MPS assigner (`tal.py`) with eight instances per image at
  batch 8-16 (batch 4 ran; its lane is 0.26 boards vs pins on every tom_old frame - a lead, recipe not
  isolated).
- Harness notes: loop 3's per-frame rows carry corner *distances* and widths, not corners (rebuilt by
  sign enumeration against the stored widths + MAE); loop 1 is on `sys.path`, so a script named
  `make_review_video.py` imports loop 1's — name new scripts distinctly; `camera_all`'s
  `static_frame` (122) is not the frame sample_input's static corners belong to (~frame 0).
