# The research lane in the engine: SAM lane calibration, before vs after (2026-09-13)

Status: complete. Review video: `review.mp4` (gitignored, ~1 min; regenerate with the commands at
the end). Engine branch `feat/sam-lane-calibration` in the worktree `~/code/bowling-app/lane-engine`
(off `feat/situp-config` 05267b1, the deployed lineage). Scripts, result JSON (`results/`) and
overlays (`overlays/`) are in this folder; engine runs live in the session scratchpad.

## The question

Five loops (2026-09-12 to 09-14, the folders next to this one) established how to find the lane
to a board or better. None of it was in the engine: the deployed pipeline still finds ONE lane per
video with classical anchor detection (foul line, gutters, pin cluster) before the ball is tracked,
and reads every board off it. This loop ports the parts that survived the research, as one pass
behind a flag, and measures the deployed engine against the new one on the three annotated videos
with the loops' own metric.

What was ported, in order of effect (with the loop that measured it):

1. **SAM 2 prompted from the ball path** on a frame near pin contact: three positive points spaced
   evenly by image length along the on-lane path (15-85 %), slid back off the ball, the mask
   component holding the prompts, one robust line per edge (loops 1-2).
2. **A far-end crop pass**: SAM again on a crop of the far 55 % of the lane with two prompts in
   the crop's lower half; the crop's rows replace the full frame's for the far end (loop 2).
3. **The standing pin rack as the far-end ruler**: a rack template rendered through the lane
   hypothesis, matched-filter fit, sub-pixel column refinement, then a metric homography from the
   foul-line corners and the ten pin bases (loop 4).
4. **One lane carried per frame** through an ORB + RANSAC similarity camera model (loops 1-2): a
   handheld phone drifts 24-36 px over a throw, 10+ boards at the pins.
5. Tiny weights (`sam2.1_t`), no sub-pixel edges, no prompt ensembles, no gradient snapping, no
   vanishing-point fits (loop 2 measured each as no gain). The YOLO seg lane student (loop 3) was
   trained on these three videos and is not used; the alley-face constellation (loop 5) is research.

## The engine before and after

**Before** (`--simple-detect`, what `service/app.py` runs): passes 1-4 find a static lane, track
the ball, and `BirdsEyeRenderer` reads the board as the ball's x-fraction between that lane's
edges at the ball's row. Its lane on the three videos: 55 px above the pin bases and too wide on
sample_input; the neighbouring lane on Chardie (0 % ball detection follows); 80 px too high and
half the true width at the pins on tom_old.

**After** (`--simple-detect --yolo --sam-lane`): a pass 5 after tracking and trajectory cleanup,
`src/bowling/lane_tracking/lane_calibration.py`:

```
tracked positions -> rolling segment (longest run of frames moving toward the pins)
  -> ORB similarity of every throw frame to the calibration frame (features at half resolution)
  -> candidate frames: pin_hit-4, -6, -8, -10, -2, then +6 .. +30 past the end of the track
     per candidate: SAM 2 tiny full frame -> component holding the prompts -> rows (thin tails trimmed)
                    -> line per edge -> gates: residual <= 8 px, far/near width <= 0.75,
                    near width >= 12 % of the frame, mask reaches the path's far end, and the same
                    prompts on a frame 6 away give the same lane (a lane is static, a bowler is not)
     first candidate with residual <= 5 px wins, else the best passing one
  -> far-end crop pass (accepted when its width is within 40 % of the full frame's and it passes the gates)
  -> pin rack on up to three standing-pin frames (before the ball reaches the pin row): alias margin >= 0.03,
     contrast >= 2.5 sigma, score > 0.2; the largest group of fits agreeing within 2.5 px (one-column
     alias lands ~10 px away) -> metric homography (foul corners + 10 bases) -> replaces the edge lines
  -> lane top = the mask's top row minus one far-end ball radius (a tenth of the lane's width there);
     positions above it are the ball deflected into the pins
  -> per-frame lane, per-position board, final board = median over the last five positions on the lane
  -> <out>_lane_calibration.json, summary.json (final_board, entry_board, lane_method, lane_edges),
     the debug video re-rendered with the per-frame lane (scripts/sam_lane_pass.py)
```

Every stage degrades to the previous one; nothing in the pass raises. Modules: `lane_geometry.py`
(prompts, component, robust lines, row band, crop box, merge), `frame_alignment.py`
(`FrameAligner`), `sam_prompter.py` (`SamLaneSegmenter`, ultralytics behind a two-method interface),
`pin_rack.py` (template, fit, refinement, DLT with line constraints), `lane_calibration.py`
(orchestration, `LaneCalibration`). Tests: `tests/test_lane_tracking/test_{lane_geometry,
frame_alignment,pin_rack,lane_calibration}.py`, the last on a synthetic drifting throw with fake
segmenters (a blob, a moving object, a mask that stops short, an occluded first frame). The
service passes `--sam-lane` when `SAM_LANE=1` and reads the new summary fields.

## What the engine taught the research recipe

The research prompted SAM from the *annotation's* ball path on a frame chosen from the
annotation's pin-hit marker. The engine has neither, and the first four runs on real tracker
output each failed for a reason the loops never met:

- **The tracker's output is not the ball path.** On Chardie with `--yolo` the cleaned track was
  the bowler's approach (ball in hand, 40 frames), a two-frame spike at the pins, then the roll;
  the pass calibrated on the spike. The longest run of frames moving toward the pins (frame gaps
  <= 12, y never rising more than 3 px) is the roll on all three videos.
- **The tracker loses the ball early.** Chardie's track ends at frame 108 of a roll that reaches
  the pins at 134, while the bowler still stands on the lane; every frame near the track's end is
  occluded. Candidate frames now run to 30 frames past the track's end.
- **A bowler's legs pass every geometric gate.** Residual 1.8-3 px, far end narrower than the
  near end, the prompts inside: the ball path in image space runs through where the bowler stands.
  Two things separate legs from a lane: the mask must reach the path's far end (the lane ends
  where the ball stops), and it must not move between two frames six apart once the camera motion
  is removed.
- **Neither the mask top nor the track's end is "the pins".** SAM stops 10-20 px short of the
  pin bases (the deck darkens), so the ball's centre hovers just above the mask's top row for its
  last 20-30 frames (perspective compresses the last feet into a few rows), then jumps 19 px when
  it is deflected into the pins, and those last tracked positions map to boards 30-34 through edge
  lines that describe nothing there. Reading the board at the mask top cut sample_input's roll 25
  frames early; reading it at a pin row derived from the track's highest point read the deflected
  positions. The median over the last five positions still on the lane surface (mask top plus one
  far-end radius, a tenth of the local lane width; the tracker's own radius is a fixed 22-33 px)
  is what holds on all three.
- **The one-column pin alias is frame-sensitive.** The same lane hypothesis on frame 119 gave the
  true rack (margin 0.07) and on frame 120 the alias (0.026, then 0.007 on the re-run), and on
  tom_old the alias passed at 0.032 with the far end 8.8 px (one column) from the true fit. Loop
  4's 0.03 margin is necessary, not sufficient; fitting three standing-pin frames and taking the
  group that agrees within 2.5 px is what holds.
- **The far-end crop's width depends on the crop box.** On tom_old two boxes 10 px apart gave
  far-end widths of 74.7 and 86.9 px for the same prompts (truth 70 at the pin row). The rack
  refit is what makes the far end reproducible; without it the crop is a coin toss on that video.

## Results

Board MAE of the annotated ball path through the engine's lane on each frame of the throw, the
loops' metric, against the pins-based truth (loop 4; the hand corners are 1-2 boards off at the
pins) and the annotated corners. Before = deployed config. Before+yolo = the same lane with the
YOLO ball detector (Chardie has no track without it). After = the new pass; the ablations switch
one stage off or move the calibration frame.

<!-- TABLE -->
| config | video | lane | throw MAE ann mean/med | throw MAE pins mean/med | <=2 bd (pins) | clean med (pins) | tail med (pins) | pre-hit / last (pins) | far-end width err px | final board engine / truth (err) | pass s |
|---|---|---|---|---|---|---|---|---|---|---|---|
| before | sample_input | static classical lane | 6.79 / 7.05 | 6.09 / 6.37 | 0.0 % | 6.3 | 10.54 | 4.51 / None | 65.3 | 15.0 / 17.43 (2.43) | - |
| before | Chardie | static classical lane | 180.88 / 165.44 | 181.74 / 166.31 | 0.0 % | 161.56 | 354.89 | 143.11 / None | 29.3 | 27.0 / 13.59 (13.41) | - |
| before | tom_old | static classical lane | 11.72 / 11.69 | 13.25 / 13.22 | 0.0 % | 13.22 | 21.56 | 13.22 / 14.48 | 22.1 | 28.0 / 20.24 (7.76) | - |
| before_yolo | sample_input | static classical lane | 6.79 / 7.05 | 6.09 / 6.37 | 0.0 % | 6.3 | 10.54 | 4.51 / None | 65.3 | 13.0 / 17.43 (4.43) | - |
| before_yolo | Chardie | static classical lane | None / None | None / None | 0.0 % | None | None | None / None | None | 23.0 / 13.59 (9.41) | - |
| before_yolo | tom_old | static classical lane | 3.32 / 3.28 | 4.86 / 4.82 | 0.0 % | 4.82 | 5.55 | 4.87 / 5.93 | 20.1 | 1.0 / 20.24 (19.24) | - |
| after | sample_input | sam_full+crop | 1.38 / 1.27 | 0.76 / 0.59 | 96.3 % | 0.65 | 0.67 | 0.15 / 0.15 | 1.2 | 15.0 / 17.43 (2.43) | 78.78 |
| after | Chardie | sam_full+crop | 0.84 / 0.65 | 1.1 / 1.09 | 97.3 % | 1.09 | 1.32 | 0.83 / 1.26 | 2.7 | 10.0 / 13.59 (3.59) | 219.01 |
| after | tom_old | sam_full+crop | 1.95 / 1.97 | 0.43 / 0.44 | 100.0 % | 0.44 | 1.04 | 0.43 / 0.59 | 7.5 | 18.0 / 20.24 (2.24) | 73.15 |
| after_full | sample_input | sam_full | 1.53 / 1.44 | 0.86 / 0.76 | 95.1 % | 0.78 | 1.08 | 0.25 / 0.24 | 4.9 | 15.0 / 17.43 (2.43) | 81.91 |
| after_full | Chardie | sam_full | 0.87 / 0.62 | 0.98 / 0.92 | 100.0 % | 0.92 | 1.13 | 0.6 / 1.02 | 1.2 | 11.0 / 13.59 (2.59) | 219.42 |
| after_full | tom_old | sam_full | 2.06 / 2.08 | 0.53 / 0.55 | 100.0 % | 0.55 | 1.3 | 0.53 / 0.7 | 9.4 | 18.0 / 20.24 (2.24) | 94.61 |
| after_pins | sample_input | sam_full+crop | 1.38 / 1.27 | 0.76 / 0.59 | 96.3 % | 0.65 | 0.67 | 0.15 / 0.15 | 1.2 | 15.0 / 17.43 (2.43) | 83.69 |
| after_pins | Chardie | sam_full+crop | 0.84 / 0.65 | 1.1 / 1.09 | 97.3 % | 1.09 | 1.32 | 0.83 / 1.26 | 2.7 | 10.0 / 13.59 (3.59) | 215.64 |
| after_pins | tom_old | sam_full+crop | 1.95 / 1.97 | 0.43 / 0.44 | 100.0 % | 0.44 | 1.04 | 0.43 / 0.59 | 7.5 | 18.0 / 20.24 (2.24) | 73.07 |
| after_back2 | sample_input | sam_full+crop | 1.45 / 1.48 | 0.8 / 0.8 | 97.6 % | 0.83 | 0.82 | 0.34 / 0.22 | 1.1 | 15.0 / 17.43 (2.43) | 74.8 |
| after_back2 | Chardie | sam_full+crop | 0.84 / 0.65 | 1.1 / 1.09 | 97.3 % | 1.09 | 1.32 | 0.83 / 1.26 | 2.7 | 10.0 / 13.59 (3.59) | 212.2 |
| after_back2 | tom_old | sam_full+crop | 1.54 / 1.56 | 0.15 / 0.12 | 100.0 % | 0.12 | 0.31 | 0.12 / 0.87 | 5.9 | 16.0 / 20.24 (4.24) | 71.21 |
| after_back8 | sample_input | sam_full+crop | 1.26 / 1.25 | 0.62 / 0.57 | 100.0 % | 0.61 | 0.7 | 0.16 / 0.16 | 3.1 | 14.0 / 17.43 (3.43) | 74.89 |
| after_back8 | Chardie | sam_full+crop | 0.84 / 0.65 | 1.1 / 1.09 | 97.3 % | 1.09 | 1.32 | 0.83 / 1.26 | 2.7 | 10.0 / 13.59 (3.59) | 213.37 |
| after_back8 | tom_old | sam_full+crop | 1.64 / 1.65 | 0.17 / 0.15 | 100.0 % | 0.15 | 0.48 | 0.12 / 0.22 | 6.8 | 15.0 / 20.24 (5.24) | 71.52 |
<!-- /TABLE -->

<!-- SAY -->
## What the results say

1. **The lane is fixed on every video, and the fix is the recipe, not a retune.** Median board MAE
   through the throw against the pins-based truth: sample_input 6.4 -> 0.6, Chardie 166 (the
   classical detector chose the neighbouring lane) -> 1.1, tom_old 13.2 -> 0.4, with 96-100 % of the
   throw frames within two boards where the deployed engine had 0 %. The pre-hit frames match the
   loops' own single-frame numbers (0.15 / 0.8 / 0.4 against 0.31 / 0.69 / 2.27 for loop 2's
   full-frame prompts and its crop's 0.6 / 1.3 / 1.3 re-scored on the pins): the engine's tracker
   supplies prompts as good as the annotation's once the rolling segment is used.

2. **The product number improves by less than the lane does, and the remainder is the ball
   tracker.** The engine's final board (median board over the ball's last five frames on the lane
   surface) goes from 2.4 / 13.4 / 7.8 boards off to 2.4 / 3.6 / 2.2. On Chardie the tracker loses
   the ball at frame 108 of a roll that reaches the pins at 134 and the ball hooks 3-4 boards in
   those 26 frames, so the pass can only report where the track ends. On sample_input the last
   frames on the lane surface are about ten frames before contact and the ball hooks 1.5 boards
   in them; reading the board at the tracker's later positions is worse, not better, because those
   positions are the ball deflected into the pins (a 19 px jump after 25 frames of hovering at
   the lane's top row), where the edge lines describe nothing. A pin-row crossing was tried and
   dropped for exactly that reason.

3. **Four things the research never met, because it prompted from the annotation.** The tracked
   path carries the approach and pin-area spikes; the tracker loses the ball while the bowler still
   stands on the lane; a bowler's legs are a lane to every geometric gate; the mask top is not the
   pin row. Each of the eight engine runs before the final one failed on one of these (see "What the
   engine taught the research recipe"). The fixes are model-free and cost one extra SAM call per
   candidate frame.

4. **The far-end crop helps on the handheld 1080p and the tripod videos and is neutral on 720p;
   the pin rack is not shippable from this initialisation.** Without the crop (`after_full`)
   sample_input is 0.76 instead of 0.59 and tom_old 0.55 instead of 0.44 (median, pins truth);
   Chardie moves from 1.09 to 0.92, within the 720p annotation floor. The calibration frame
   matters more than the loops suggested: pin-hit −8 (`after_back8`) is as good or better than −4
   on every video (0.57 / 1.09 / 0.15 against 0.59 / 1.09 / 0.44) and −2 is best on tom_old
   (0.12); the default stays at −4 pending a sweep on more videos. The rack refit, loop 4's headline, converges
   on the one-column alias from the SAM lane on 8 of 9 standing-pin frames (alias margins
   0.025-0.032 against loop 4's 0.03 threshold) and on tom_old the alias moves the far end by one
   column, 4 boards; gated by margin, cross-frame agreement and far-end centre shift it never fires,
   which is the right outcome. It is behind `--pin-refit`. A rack fit that is initialised from the
   lane it then corrects is circular where the alias is one column away; the fix is a pin detector
   that does not start from the lane (loop 4's own recommendation).

5. **Cost.** 25-80 s per video on this Mac: ORB alignment at half resolution 10-20 s, 0.6-0.7 s
   per SAM 2 tiny call, two to ten calls (Chardie tried eight candidates), re-render a few seconds.
   Cloud Run at 8 CPU should be similar; the image needs torch + ultralytics (+~250 MB) and the
   78 MB weights.

## Recommendation for the engine

1. Merge the pass behind `--sam-lane` and turn `SAM_LANE=1` on in the service after adding torch,
   ultralytics and `models/sam2.1_t.pt` to the image; the summary carries `final_board`,
   `entry_board`, `lane_method` and `lane_edges`, and `final_board_static` keeps the old number for
   comparison.
2. Ship `--yolo` with it: the deployed config has no track on Chardie at all, and the pass needs
   a track. Then fix the tracker's early loss near the pins (Chardie 108/134): that is now the
   largest error in the product number.
3. Keep `--pin-refit` off until the rack is found by a detector that does not start from the lane.
4. Keep the loop's evaluator: any lane change is one `run_engine.py` + `evaluate.py` away from a
   number against both truths, and the before videos are kept for side-by-sides.

## Retro

Solo loop, ~4.5 h. What worked: writing the evaluator against the loops' own truth before touching
the engine, so every run was a number in ten seconds; running the deployed engine first (the
Chardie wrong-lane / 0 % finding shaped the whole loop); one rewrite of the orchestrator after the
second failure instead of patching. What cost time: eight engine runs to learn that real tracker
output needs gates the research never needed, each a 5-minute round trip; a fake-segmenter test
that moved the lane opposite to its own background; block-buffered logs that hid a run's progress;
and running edits while a batch was mid-way, which produced two runs with mixed code (v5, v8's
sample_input). Next time: fail fast with a one-video run before the batch, and never edit modules
the running batch imports.
<!-- /SAY -->

## Reproducing

```
V=~/code/bowling-app/analysis-engine/.venv/bin/python
cd docs/research/2026-09-13-engine-lane-integration
export EI_SCRATCH=/path/to/scratch          # frames + runs; loop 1's gt.extract_frames fills frames/
$V -c "import common as C; [C.gt.extract_frames(s) for s in C.STEMS]"
$V run_engine.py before old --simple-detect --telemetry
$V run_engine.py before_yolo old --simple-detect --yolo
$V run_engine.py after new --simple-detect --yolo --sam-lane
$V run_engine.py after_full new --simple-detect --yolo --sam-lane --no-far-crop --no-pin-refit --no-rerender
$V run_engine.py after_crop new --simple-detect --yolo --sam-lane --no-pin-refit --no-rerender
$V run_engine.py after_back2 new --simple-detect --yolo --sam-lane --sam-back 2 --no-rerender
$V run_engine.py after_back8 new --simple-detect --yolo --sam-lane --sam-back 8 --no-rerender
for c in before before_yolo after after_full after_crop after_back2 after_back8; do $V evaluate.py $c; done
$V tables.py before before_yolo after after_full after_crop after_back2 after_back8 && $V fill_readme.py
$V make_review_video.py after
```
