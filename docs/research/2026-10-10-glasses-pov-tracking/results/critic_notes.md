# Completeness critic, glasses-POV loop, 2026-10-10

## (a) Is the rendered trace tracker output?  YES, with one declared input
- `grep -i truth|label` over track.py, make_showcase.py, lane_geom.py, experiments/sam2-video/{run,sam_track}.py: 0 hits.
- make_showcase.py reads only work/cuts/cuts.json and results/tracks/<stem>.json.
- Declared dependency: release_frame/pin_hit_frame come from cuts.json and set the SAM prompt window AND the showcase window.
  On dev 185121/185331/185645 cuts.json copied those from the 09-19 truth (`method: truth (2026-09-19 L/truth)`).
  On the holdout they are visual reads that differ from the holdout truth by at most 1 frame (window_err [1,0] on 191820 and 191913).
  So the trace is tracker output, but the tracker is told when the ball is on the lane. Nothing in the loop detects release or pin hit on its own.

## (b) Recall on fewer than 8 truth points: none
`ball` entries per truth file: 185121 18, 185331 60, 185454 52, 185645 62, 190115 55, 191253 53, 191820 24, 191913 23,
192142 17, 192636 18, 191900 0 (no throw, excluded). The minimum is 17 (192142, 100 %).
The thin truth is the board instead: 192142 and 192636 have only 3 `board_reads` each, and those are the two stems every method misses.

## (c) Cuts not visually verified
Only 191900 (verified=false, no throw, no cut). The other 10 are verified=true, but on dev 185121/185331/185645
"verified" means the truth frames were copied and frame-0 alignment checked (frame0 MAD 0.7-0.8), not a fresh visual read.

## (d) Single-method storyline
fallback applied on 0 of 11 stems. It triggered on 2: 185121 (no board, kept sam2-video because the baseline was worse)
and 191900 (no throw). The showcase would label a fallback (`sam2-video+fallback`). It shows 185121 as throw 1 with
"no lane fit - no top-down trace". The title says 10 throws. Honest.

## (e) Numbers that could not have come out otherwise
1. window_err [0,0] on all dev stems: true by construction (the windows were copied from the truth).
2. Dev 97.5 % recall / board 1.0: the dev stems were used to tune, and three of them were already worked on 09-19, using truth windows.
   A judge "reproducing" a dev number only re-ran a deterministic script on the same input (a determinism check, not an independent test).
   Same for the judges' "fresh holdout identical to experiment's track": expected for deterministic code.
3. **The method choice depends on a lucky board.** sam2-video counts as "works" only through board<=3 on 3/5, and one of those three is
   191913 board_err 0.0, which its own judge calls luck: from f493 the track is on a gutter object, and the board was read at 492.
   The top-down data shows the drift starting before that: board 8.2 -> 4.0 over f488-492. Without it, sam2-video is 2/5, which is "partial", the same as
   appearance-prior (98.8 % recall). Then the fixed rule would pick detector-tiling (78.6). The integration should report that sensitivity.
4. Holdout boards 192142 (truth 10.0) and 192636 (truth 12.5): sam2-video misses by 5.0 and 5.5, lane-first by 3.4 and 5.2, wildcard by 4.0 and 5.5,
   appearance-prior by 4.0 and null, detector-tiling by ? and 5.5, always on the low side. Five of the six methods share the engine SAM lane pass, so their errors are correlated.
   Each truth board rests on 3 reads, and the detector-tiling judge read 192636 by eye as "~8-12". Either the truth or the shared lane stage is biased, and nothing settles which.
5. Scorer mutation (work/scorer_mutation): only empty, shift100 and gap8. No small shift (~25 px at the far end, where r is 6-15 and the tolerance is max(2r,20)),
   so the tolerance has never been shown to reject a near miss at the pins. 191913's 56.5 % shows it can fail on a 26-41 px drift.

## (f) What Tom asks first
"Throw 8's circle sits in the gutter at the pins and throws 9 and 10 read board 5 and 7 where your truth says 10 and 12.5. Which is right, and how did you check?"

## (g) Showcase must-fix (showcase.mp4, 1920x1080, 28.9 s, 867 frames, audio)
Checked at full resolution by cropping the actual mp4 at the tracked point:
- MUST: throw 8 (191913), source f493-~513, showcase ~22.0-22.7 s (output frames ~662-682): the cyan circle is on a dark object in the right gutter/kickback,
  ~45 px right of the purple ball. Seen at f500 (frame 669) and f506 (frame 675). The cut is verified. The right panel hides it
  (past_pins points filtered), so the two panels disagree. Fix: stop drawing the circle after last_lane_frame 492, or gate the jump.
- MUST: throw 1 (185121, 2.0-4.67 s, e.g. f332): the right panel is empty ("no lane fit - no top-down trace") on the OPENING throw.
  Move it out of first place, or drop it, or label it at the start.
- SHOULD: throw 10 (192636, f443): the trace starts with an outlier at the right gutter (board ~-1 near the foul line), drawn as a long diagonal.
- SHOULD: the pin rack on the lane diagram is upside down. make_showcase.py draws the rows at 60 - row*0.866 ft, so the headpin is farthest from the bowler
  and the 7-10 row is nearest. A bowler will notice.
- NOTE: "final board" on 192142/192636 (5, 7) disagrees with truth by 5 boards. The circle is drawn on interpolated positions (gaps <=6) as if tracked.
  The left-panel label (stem + source frame) is readable but cryptic, with no dev/holdout tag.
- OK: <60 s; live board readout plus final board after pin hit; circle on the ball at full res in 185121 f332, 191253 f413, 192636 f443, 192142 f470.

## Overlays read (2 per experiment: 191913, 192636)
The experiment overlays draw the raw per-frame track in each frame's own coordinates over one frame's lane quad. The camera moves, so every one
swirls above the pins and crosses gutters. They cannot show whether the ball was on the lane or which board it was on. Only overlays/final__*.jpg (green camera-compensated path)
can. So the per-experiment overlays are not visual evidence for board accuracy.
