# Glasses-POV bowling tracking (research, 2026-10-10)

`docs/research/2026-10-10-glasses-pov-tracking/` (scripts, `results/`, `experiments/`, `overlays/`, `truth/`; `showcase.mp4` and `work/` are gitignored).

## Asked
Analyse 11 new bowling videos filmed first person with Meta glasses (HEVC, ~1376x1824 portrait, 30 fps). Run experiments to see what works. Cutting out the walk-up is allowed. Finish with a showcase video: the video on one side, the rendered ball trace on the other.

## The 11 videos
Frame indices are source numbering. Cut frame k = source frame cut_start + k. Cuts are in `work/cuts/` (gitignored); offsets in `work/cuts/cuts.json`. Cut check = frame-0 mean absolute difference of the cut against the source at offsets -2..+2; offset 0 is 0.7-0.8, the others 17-32.

| stem (after 20260915_) | split | cut frames | release | pin hit | release/pin source |
|---|---|---|---|---|---|
| 185121_23d80f05 | dev | 287-376 (90) | 297 | 356 | 09-19 truth |
| 185331_19de9ec7 | dev | 288-378 (91) | 298 | 358 | 09-19 truth |
| 185645_9fde3c16 | dev | 227-319 (93) | 237 | 299 | 09-19 truth |
| 185454_f240c883 | dev | 316-397 (82) | 326 | 377 | visual read |
| 190115_a7cf2c70 | dev | 380-464 (85) | 390 | 444 | visual read |
| 191900_106ea7ca | dev | none | - | - | no throw in the clip (258 frames) |
| 191253_6cf2480f | holdout | 367-457 (91) | 377 | 437 | visual read |
| 191820_0196b564 | holdout | 401-483 (83) | 411 | 463 | visual read (gutter ball) |
| 191913_907c358b | holdout | 431-529 (99) | 441 | 509 | visual read |
| 192142_eeb210f6 | holdout | 405-500 (96) | 415 | 480 | visual read |
| 192636_7c7fbfb0 | holdout | 381-477 (97) | 391 | 457 | visual read |

191900: the bowler holds the ball on the approach while the neighbour bowls. No cut, no baseline run, empty track. It is excluded from every mean. 10 cuts verified, 1 not (191900).
ffprobe's `r_frame_rate` prints 120. The real rate is 30 (nb_frames / duration; cv2 agrees).

## Truth and its limits
- 185121, 185331, 185645: reused from the 2026-09-19 loop (`docs/research/2026-09-19-new-alley-videos`).
- 185454, 190115, 191900: labelled this loop (`work/truth/NOTES_*.md`). Ball points come from an HSV chain seeded by eye, radius from the Lab b* bounding box, 18 frames per video eye-checked on 3x gridded crops. Board = middle of the edge-profile and pin-ruler reads, rounded to 0.5, uncertainty floored at 1.0.
- Holdout truth was written after the experiments were scored (`truth/`, notes in `truth/holdout_label_notes/`). Experiments never read it.
- Limits: release frames are hand reads on motion-smeared blobs (+-15-20 px near, +-1-2 frames). Near-end radii are +-15 px. The pin ruler and the lane edges disagree by 1-2 boards (px/in 1.67 vs 2.1). The foul line is not visible, so lane quads use the lowest row with both edges (`fl_is_foul_line: false`). 192142 and 192636 have 3 board reads each. Truth point counts: 17-62 per stem.
- Boards 1-39 count from the right gutter. The engine's convention was checked on the baseline: unflipped errors 0.5-6.5, flipped 16.5-30.5.

## Baseline (engine ad2c96e, branch exp/r2-glasses-pov, recall % / board_err, `results/baseline_summary.md`)

| config | 185121 | 185331 | 185645 | 185454 | 190115 | 191253 H | 191820 H | 191913 H | 192142 H | 192636 H | dev recall | holdout recall | pass dev/holdout |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| service | 0 / - | 0 / - | 3 / - | 38 / - | 0 / - | 0 / - | 8 / 6.5 | 9 / - | 0 / - | 0 / - | 8.3 | 3.4 | 0/5, 0/5 |
| yolo | 0 / - | 0 / - | 0 / - | 48 / - | 0 / - | 0 / - | 0 / 32.5 | 30 / - | 0 / - | 0 / - | 9.6 | 6.1 | 0/5, 0/5 |
| yolo_chain | 89 / - | 57 / - | 86 / - | 60 / - | 69 / - | 92 / - | 0 / 6.5 | 30 / - | 41 / - | 56 / - | 72.0 | 43.9 | 0/5, 0/5 |
| yolo_chain_sam | 89 / - | 57 / 0.5 | 86 / 3.5 | 60 / 2.5 | 69 / 0.5 | 92 / 0.5 | 0 / 6.5 | 30 / 2.0 | 41 / 4.0 | 56 / 5.5 | 72.0 | 43.9 | 1/5, 1/5 |

Best baseline: yolo_chain_sam. The chain starts 8-11 frames after release because the big blurred ball at the frame bottom is never linked. The static lane is meaningless on a moving head camera. SAM lane calibration refuses 185121 and the gutter ball 191820.

## Experiments (recall %, board_err in boards)

| key | dev recall | holdout recall | board_err | verdict | what the lens taught |
|---|---|---|---|---|---|
| cam-diff | 95.3 | 73.0 | 2.7 | works | ORB homography + three-frame residual + purple gate; the residual of a dark ball is only its rim, so re-measure radius on the purple component. Two-way extension recovers the post-release blur. |
| lane-first | 90.9 | 77.3 | 2.2 | works | Lane wood mask + ball in lane coordinates, cv2/numpy only, 1.3 s per video. Z from the vanishing point is too noisy; predict the image row, take only the across-lane coordinate from the Kalman filter. |
| appearance-prior | 97.5 | 98.8 | 3.25 | partial | Learned histograms are dead (17-24 % vs 97.5 % for a fixed purple hue window). Fixed hue + motion peak at the far end gives the best recall, but SAM lane refuses 2 of 5 dev stems, so board <= 3 on 2/5 holdout. |
| sam2-video | 97.5 | 90.46 | 2.5 | works | One box prompt at release+3, forward propagation plus a backward pass for the blurred ball, far-end 2x crop re-prompt. Slowest (112 s mean). |
| detector-tiling | 91.9 | 78.56 | 2.25 | works | Far-end tiling and YOLO-World are dead (16-20 % and 0 % far recall vs 91 % native). The fine-tuned YOLO11n is scale-specific, so pooling four inference scales is what beat the baseline. |
| wildcard | 96.1 | 76.5 | 2.75 | partial | NCC template relay: one-step 36/36 mid-lane, 14/15 far. Farneback flow residual is dead (3/35). |

Dev board_err is over the stems that produced a board (1.0-2.2 for the working methods). Holdout recall is the judge's re-scored number. No experiment read holdout truth. Every method beat the baseline holdout recall (43.9).

## Chosen method: sam2-video, one method for all 11
Rule fixed in advance: highest holdout mean recall among verdict `works` (cam-diff 73.0, lane-first 77.3, detector-tiling 78.6, sam2-video 90.5). appearance-prior (98.8) is excluded by its `partial` verdict. No composition: no judge measured the lane stage alone. Fallback to yolo_chain_sam applied on 0 stems. Entry point `track.py`; geometry `lane_geom.py`; scorer `score_tracks.py`.

| stem | split | points | recall % | median px err | final board | board_err | pass | wall s |
|---|---|---|---|---|---|---|---|---|
| 185121 | dev | 55 | 94.4 | 8.4 | none | - | no | 129.5 |
| 185331 | dev | 65 | 93.3 | 5.0 | 5 | 0.5 | yes | 89.7 |
| 185645 | dev | 67 | 100 | 3.5 | 7 | 1.5 | yes | 78.2 |
| 185454 | dev | 56 | 100 | 2.1 | 11 | 0.5 | yes | 69.8 |
| 190115 | dev | 59 | 100 | 2.0 | 10 | 1.5 | yes | 166.5 |
| 191900 | dev | 0 | - | - | - | - | - | - |
| 191253 | holdout | 64 | 100 | 1.9 | 6 | 0.5 | yes | 78.6 |
| 191820 | holdout | 56 | 95.8 | 4.2 | 1 | 1.5 | yes | 62.2 |
| 191913 | holdout | 73 | 56.5 | 2.8 | 7 | 0.0 | no | 96.3 |
| 192142 | holdout | 70 | 100 | 2.7 | 5 | 5.0 | no | 88.1 |
| 192636 | holdout | 71 | 100 | 7.7 | 7 | 5.5 | no | 222.9 |

Dev: mean recall 97.5, board_err 1.0 over 4 boards, 4/5 pass. Holdout: mean recall 90.5, board_err 2.5, board <= 3 on 3/5, 2/5 pass.

## Showcase (`showcase.mp4`, gitignored)
28.9 s, 1920x1080, 30 fps, audio from the sources, 10 throws (191900 has none). Left panel: the cut video with the ball circle (cyan = tracked, orange = interpolated gap) and a label with stem, frame and dev/HOLDOUT tag. Right panel: top-down lane diagram with the ball path (ft = a*s + b fitted per throw, a = 66-73), board readout, pin rack with the headpin nearest the bowler. Order is stem order with 185121 last, labelled "no lane fit" (no top-down trace). The circle stops after the last lane frame, so the 191913 gutter-object circle is gone. Fallback stems: none.
Timeline (s): 185331 2.0-4.7, 185454 4.7-7.1, 185645 7.1-9.9, 190115 9.9-12.4, 191253 12.4-15.1, 191820 15.1-17.5, 191913 17.5-20.5, 192142 20.5-23.3, 192636 23.3-26.2, 185121 26.2-28.9.
Not fixed: the board readout on 192142 (5) and 192636 (7) is about 5 boards below truth (10, 12.5).

## Limits (critic)
- The choice rests on 191913's board_err 0.0, read at f492, one frame before the track drifts to a gutter object. Without it sam2-video is `partial` and the rule picks detector-tiling (78.6).
- 192142 and 192636 board misses are shared by every method, always low. Five of six methods use the engine SAM lane pass. Each truth board rests on 3 reads.
- Release and pin windows are given by `cuts.json`, not detected. On dev 3 stems they were copied from truth, so window_err is 0 by construction and dev numbers are not end-to-end.
- Dev numbers were tuned on dev. Judge reproductions test determinism, not generalisation. 191913 recall is 56.5 % because the far-end crop pass drifts.
- Per-experiment overlays draw raw per-frame tracks over one frame's lane quad, so they swirl with camera motion. Only `overlays/final__*.jpg` are camera-compensated.
- Scorer mutations tested only empty, shift +100 px and gap 8. No small far-end shift (15-25 px) has been shown to fail.
- `track.py` opens no label file (static scan of 57 local modules, audit-hook run: 0 opens).

## Next
1. Read the 192142 and 192636 boards again with more frames and pin-deck geometry, then score the lane stage separately from the ball track.
2. Fix the 191913 far-end drift (gate the jump), re-score, and report the method choice with and without it.
3. Detect release and pin hit automatically (audio thud, YOLO seed) and score window_err end to end.
4. Add 15 and 25 px far-end shift mutations to `score_tracks.py`.
5. Give 185121 an image-space trace when the lane is refused.
6. Run the lane-first stage (1.3 s) as a fast prior for the board and compare against the engine lane pass.
