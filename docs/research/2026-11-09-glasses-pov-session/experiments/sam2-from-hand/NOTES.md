# sam2-from-hand (session 2026-11-08 clips, dev stems only) - NOTES

Lens: SAM 2 prompted from the ball just out of the hand, whatever its colour, propagated through the roll; loop-2 lane
stage, pin-row detection and deck events kept by import from `L2/track_v2.py`. Ran ONLY on the 8 dev stems
(104946, 105652, 110442, 111631, 112800, 113911, 114631, 115157). The truth stems and the quarantine folder were not
opened, not run, not listed. `looked_at_truth_clips = false`.

## What was built (`run.py <stem> [--device mps|cpu] [--no-refine]`)
- **Prompt**: the loop-1 fine-tuned YOLO11n (colour-agnostic) at imgsz 320 on release+2..release+10, first box with conf >= 0.3,
  side 60-450 px, centre below the top 10 % of the frame. It fired on 8/8 dev stems at release+2..+5 (conf 0.33-0.65). The task's
  "release-2..release+2, bottom third" window does not hold: YOLO sees nothing at any imgsz while the hand is still on the ball
  (release-2..release+1 on both probed stems), and on the head-down release of 104946 the ball sits 38 % from the TOP of the frame at
  release+4 (the first version with a bottom-65 % constraint found no prompt there). A contour fallback (round non-wood blob in the lower
  2/3) exists but was never needed on dev.
- **SAM 2**: loop-1 `sam_track.track()` (full-frame propagation + up to 3 far-end 2x crop re-prompts) from the prompt frame to the END of
  the cut, plus `track_back()` to release. The backward pass recovered release..k0-1 on 8/8 (2-4 frames each).
- **Lane gate** on every mask centroid, per-frame edge lane (lane-first mask + RANSAC, centroid as component hint): board outside
  [-0.5, 40.5] dropped unless the last kept point was already at board <= 2.5 or >= 37.5 (gutter balls 110442/115157 keep their gutter
  points: with the loop-2 1.0 threshold 110442 lost 13 frames, its entry and its roll coverage); from release+8 a lateral step > 3 boards x min(2, frames
  skipped) from the last kept point is dropped (113911: SAM wandered 10 boards right through a head whip; with the loop-2 per-gap
  allowance the excursion was re-accepted after 4 frames). Gate runs through cut pin_hit+2 only; deck points are read by the lane stage on
  the extended edge lines as in loop 2.
- **Far-end refine** (colour-agnostic replacement for the loop-2 purple disc): per-clip ballness map = Lab k-means (k=2) of the prompt
  box's central disc, Gaussian in Lab distance, thresholded 0.5; LGB's disc-minus-annulus filter at r_geo where r_geo <= 16 px, same
  acceptance (resp >= 0.40, annulus <= 0.35, lateral <= 3 boards). It accepted 0-15 frames per stem (mean 3.4) and rejected 37-62: the
  SAM centroid is kept on most far frames, with its known deck bloat (r 17-25 px where r_geo is 7-10).
- Then the track_v2 sequence unchanged: `CM.run` edge+smooth3 with the ball stage injected, `clean_series`, `pin_row_estimate`,
  `pin_motion`, `deck_decoy`, `add_depth`, `compute_events`, `draw_overlay_v2`; plus `overlays/check__<stem>.jpg` = crops at the frames
  nearest 20/40/55 ft with that frame's own circle (the final overlay stacks all circles on one frame and cannot answer J6).
- `CM.load_cut` / `LGB.load_cut` are patched to the session `work/cuts/cuts.json`; nothing is written into the loop-1/2 folders.

## Dev proxies (no truth; `summarize.py` -> `dev_summary.json`)
| stem | det. rate (rel+5..pin row) | max 5-med jump | pin row | pin row src | cut pin_hit | entry | exit f | deck | break ft | points | gated | refined | series rej | prompt (k0, source frame) | wall s | SAM s |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 104946 | 1.000 | 1.29 | 457 | geometric | 455 | 0.21 | None | 0 | 60.0 | 96 | 0 | 15 | [486] | yolo320 conf 0.37 (398) | 90.4 | 76.4 |
| 105652 | 1.000 | 2.91 | 385 | geometric | 375 | 11.92 | None | 0 | 50.1 | 92 | 0 | 0 | - | yolo320 conf 0.40 (317) | 84.0 | 69.9 |
| 110442 | 1.000 | 1.55 | 421 | fallback | 421 | -2.05 | None | 0 | 55.3 | 96 | 0 | 3 | [435] | yolo320 conf 0.37 (361) | 143.3 | 128.0 |
| 111631 | 0.984 | 2.88 | 363 | geometric | 358 | 20.21 | None | 0 | 18.8 | 92 | 1 | 3 | - | yolo320 conf 0.65 (300) | 78.6 | 62.3 |
| 112800 | 1.000 | 0.5 | 310 | fallback | 310 | 11.0 | 317 | 8 | 32.1 | 93 | 0 | 4 | [334, 335, 336] | yolo320 conf 0.37 (254) | 81.0 | 65.7 |
| 113911 | 0.906 | 1.11 | 525 | geometric | 518 | 20.42 | None | 0 | 29.1 | 73 | 6 | 2 | [522, 532] | yolo320 conf 0.33 (460) | 104.0 | 91.5 |
| 114631 | 1.000 | 0.86 | 578 | fallback | 578 | 14.46 | None | 0 | 56.1 | 96 | 0 | 0 | - | yolo320 conf 0.33 (520) | 80.4 | 66.0 |
| 115157 | 0.923 | 1.56 | 580 | pin motion | 561 | None | None | 0 | 37.3 | 77 | 0 | 0 | - | yolo320 conf 0.42 (502) | 103.5 | 90.9 |
Means over 8 dev stems (all 8 from the final code, every stem rerun after the gate change): detection_rate 0.977,
max_board_jump (5-frame median, release..pin row) 1.58, pin_row_detected 5/8 (4 geometric + 1 pin motion; fallbacks 110442, 112800, 114631),
wall 95.7 s/clip (SAM alone 81.3 s; per-stem walls in the table; the same code ran 84-175 s on the first pass, so MPS load varies 2x).

## Picture check (J6-style, read by me from `overlays/check__*.jpg`)
- 104946 (purple swirl): circle ON the ball at 20, 40 and 55 ft; at 55 ft (f452) the circle is ~1.4x the ball (SAM bloat) but centred.
- 112800 (black ball): ON the ball at 20/40/55 ft, tight radius; the ball is in front of the pins at 55 ft (f305).
- 110442 (purple, gutter ball): ON the ball at 20 and 40 ft; at 55 ft (f416, board -2.5) the circle sits in the right gutter on a
  dark blur where the ball should be, and I cannot confirm it is on the ball (a dark ball in a dark gutter at r 16 px).
- 114631 (purple): ON the ball at 20/40/55 ft.
- 105652 (purple): ON at 20 and 40 ft; at 55 ft (f379, after the cut pin_hit 375) the crop is a motion-blurred smear over the pins and I
  cannot confirm the circle sits on the ball. Its pin row came out 10 frames after the cut pin_hit; one of the two is wrong.
- 113911 final overlay: the raw SAM track loops ~10 boards right at 475-489 (head whip, blurred frame). 6 frames were gated (475-477, 489; 518-519 at the pin row), 10 more have
  no lane quad (edge fit failed on the blur) so they stay as ball points without a board: the board series is clean but detection_rate
  counts them. A follow-up rule: drop quad-less points enclosed by gated runs.

## What the lens says so far
- Prompting SAM 2 from the in-hand ball works colour-free on all 8 dev stems (black, purple/blue swirl; no green/red stem is in dev, so
  that is untested). 100 % roll coverage on 5/8, >= 0.875 on the other 3; no stem needed the fallback.
- The weak end is the same as loop 2 said: the SAM centroid at the deck (r bloated 2x) and the far-end refine. The learned-colour disc
  filter rarely fires (3.4 frames/stem); the purple-specific one fired on most far frames in loop 2. Candidates: lower REFINE_MIN_RESP for
  dark balls, or a per-clip colour learnt from the SAM mask at 40 ft rather than the prompt disc (which includes highlights: 104946's second
  Lab centre is (129,128,135), near wood).
- Pin row: 5/8 detected. 112800's ball centre never reaches the headpin base row (y 683-698 vs base 666, pd 690): either column_top reads the
  masking unit instead of the pin heads at this camera height or the ball stops short; pin_motion also failed (threshold 53 from a jittery
  baseline). 115157 (gutter ball) got its pin row from pin motion at cut+19, and entry_board is None because the track ends 6 frames before
  it; a gutter flag rather than None is what J3 wants.
- Gutter balls read as boards -3..0 (110442 entry -2.05, 115157 ~0-2): J3's gutter flag can be set from entry < 0.5.

## Not done / partial
- Budget was not exhausted (about 50 tool calls); 'partial' is false. Not done: the quad-less-point rule above, a refine threshold sweep,
  and any check on green/red balls (not in dev).
- Runtime: 96 s/clip mean (79-143 s) on the final pass, so 32 clips = 50-75 min with one torch process; SAM is 85 % of it (full-frame pass 48-80 s).
  Halving imgsz (1024 -> 512) for the full pass is the obvious lever, untested.
