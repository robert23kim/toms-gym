# Experiment ball-colour-model (stage: ball) — session 2026-11-08, written 2026-11-09

Lens: per-clip ball appearance. The loop-2 tracker with its ball candidate source replaced; the lane stage
(composition edge+smooth3), clean_series, pin_row_estimate, pin_motion, deck_decoy, add_depth, compute_events and
draw_overlay_v2 are imported from `L2/track_v2.py` and not changed.

Quarantine: this experiment did not open /Users/toka/pov-holdout/2026-11-09-glasses-pov-session and did not run on or
open the truth stems (104714, 110224, 111238, 111420, 112638, 113716). Only the 8 dev stems were run.

## What was built (`run.py <stem> [--device] [--mutate-purple]`)

1. **Ball colour model, learned per clip.** Deviation from the brief: the cut starts at release-10 and the in-hand ball
   is below the frame on every dev clip (the camera looks down the lane during the swing; the ball enters at the frame
   bottom at release). The Cuts stage already measured the raw-clip in-hand reads at V 13-32 (hand shadow). So the
   model is learned from the on-lane ball at release+1..+8: the big round not-lane blob in the lower 70 % of the frame
   at 320 px (the Cuts-stage sampler), eroded core, median Lab/HSV, spread = MAD pooled over the 4-8 frames found.
   median V < 70 -> `dark` branch, else `colour`. **All 8 dev balls are dark (navy V 55-63, black V 22-31): the colour
   branch exists but ran on 0/8 clips and is untested.**
2. **The absolute darkness test failed and was replaced by a relative one.** The first version (V < v_thr learned from
   the near ball, 100 for navy) found the ball only to release+13: the navy ball reads V 61 at release+2 and V 122-152
   at 45-55 ft (glare, exposure), while the lane wood reads V 150-220. Measured on 104946: ball/lane V ratio 0.82-0.87
   at 35-55 ft, but the Lab ab distance to the near-ball model stays 10-11. So the mask is now, inside the lane polygon:
   *not lane* against a band-local wood reference (8 row bands of the polygon below the pd row; dark branch: L < 0.8 x
   band L or ab distance from the band > 18; colour branch: the ab test only) AND ab distance to the ball model <=
   ab_tol (= clamp(2.5 x spread, 22, 40); 22-32 on dev). Then connected components, roundness >= 0.6 (0.5 within 1.5 r
   of the prediction), r within [0.4, 2.2] r_geo(row), nearest to the prediction. The chroma gate is what separates the
   ball from the black pin deck at 55-60 ft (navy: yes; black: no, see limits).
3. **Lane polygon per frame** from the loop-1 lane-first edge fit (`LN.lane_mask` + `LN.fit_lane`, hinted by the
   prediction), edges inset 0.25 r_geo, rows from 0.6 of the way up the pin column (TV2.column_top) to the frame
   bottom. Candidates above the pd row count only once the prediction is within 4 r_geo of it (112800's first run put the
   pin row at release+8 on a deck blob). When the edge fit fails the last lane is carried through the ORB homography
   chain (loop-1 cam-diff Motion) for up to 10 frames (quad src `edge-carry`); 105652 lost 9 frames of lane at 25-35 ft
   and the LGB track died at 3 coasts before this.
4. **LGB runs unchanged** on a synthetic base track {frames: the detections, lane: the edge quads}, so its lane gates,
   r_geo prior and SAM 2 re-prompts are live; `LGB.purple` is replaced by the model mask (crop mode: ab distance to the
   model, dark branch also L < 0.8 x crop median L), so the far-end disc filter looks for this ball.
5. LGB coast points (homography predictions, no detection) are dropped before the lane stage: on 113911 f475-477 they
   read boards 31 on a 20-board line during a head whip (max_board_jump 12.2 -> 0.9).

## Mutation check
`run.py 20261108_111631_9c1e9211 --mutate-purple` puts the loop-2 fixed purple window back in both the coarse source
and the refine: 0 coarse points on 96 frames, LGB and lane both fall back, detection_rate 0.0 (`work/mutation/*__mutpurple.json`).
The learned model is what finds the ball. The check ran on the code before the carried lane, the deck gate and the
coast drop were added; the mask swap sits upstream of all three, so the result stands. Files: `work/mutation/`.

## Dev proxies (8 stems, no truth; `dev_proxies.json`, `summarize.py`)

| stem | ball | det. rate (rel+5..pin row) | max 5-med jump | pin row | entry | wall s |
|---|---|---|---|---|---|---|
| 104946 | navy | 1.000 (49/49) | 0.74 | detected 447 (cut 455) | 6.1 | 48 |
| 105652 | navy | 1.000 (59/59) | 3.05 | fallback | 15.6 | 51 |
| 110442 | navy | 0.956 | 5.27 (at the pin-row frame itself, 8.8 -> 13.4 over a 2-frame gap) | detected 429 (421) | 9.6 | 37 |
| 111631 | black | 0.984 | 0.69 | detected 363 (358) | 16.7 | 37 |
| 112800 | black | 1.000 | 0.90 | detected 321 (310) | 16.4 | 34 |
| 113911 | navy | 0.947 | 0.88 | fallback | 22.3 | 33 |
| 114631 | navy | 1.000 | 1.22 | fallback | 17.1 | 31 |
| 115157 | navy | 1.000 | 1.73 | fallback | 6.1 | 32 |

Means: detection_rate 0.986, max_board_jump 1.81, pin_row_detected 4/8, wall 37.6 s per clip (max 51).
Stage split (typical): read+model 0.5 s, coarse 6-8 s (ORB Motion ~4 s + per-frame lane fit + mask), LGB 12-30 s
(3-4 SAM 2 re-prompts at 6 s each; the first run of the night adds ~15 s of model load), lane 1 s, pin row/events ~10 s
(ORB Motion is computed a third time there). 32 clips at ~38 s = ~20 min. Sharing one Motion would save ~8 s per clip
but means touching LGB.

Picture reads (`overlays/check__<stem>.jpg`, the tracked circle in its own frame at ~20/40/55 ft, `picture_check.py`):
104946, 111631, 110442, 112800: circle on the ball at all three depths. 113911: on the ball at 20 and 40 ft, at 55 ft
on a 9 px dot at the pin bases (plausible, too small to be sure). 105652: on the ball at 20 and 40 ft, at 55 ft the
circle (sam+refine) sits on empty lane in front of the pins — a re-prompt drift. 115157: on the ball at 20 ft; at 40 ft
the `sam` circle sits on empty lane and there is no point at 55 ft: the boards read 0.3-1.2 at 540-548 (right gutter)
and the SAM re-prompts then follow something along the gutter; this is probably a gutter ball and needs the J3 gutter
flag, not a line. Reading note: the full overlay (`final__*.jpg`) draws the raw circles in one frame, so J6 cannot be
read from it; use the check images.

## Limits found
- **Pin row 4/8.** The geometric detector needs real ball points at/above the headpin base row held for 3 real
  frames. LGB's SAM re-prompts stop at the cut pin_hit (`k <= k_pin`), so deck frames only come from `pred+refine`,
  and the refine fails on the deck (black deck: inner = annulus). 113911 crosses the base row at f523 = cut pin_hit+5
  with no real frame after it; 114631 and 105652 never cross; 115157 is the gutter case. A black ball on the black deck
  is invisible to any colour or darkness test; the pin-motion clock is the only instrument there (it fired on none of
  the four).
- **Board jumps at the window edges.** 105652 (3.05 at f342) is a lane read: the left edge is out of frame (fl_l x = 0.1)
  on the first frames after a carried lane. 110442 (5.27 at the pin-row frame f429) is this ball stage: f425-426 are
  unrefined `sam` points (r 10.3-10.9), f429 is `base` (r 6.6), x 559 -> 541, the loop-2 SAM-centroid bloat at the deck
  where the dark-branch refine cannot fire (black deck: inner = annulus). 110442 fails J4 as written (5.27 > 3).
- **The colour branch is untested** (no ball with V >= 70 on dev; the session's red/green balls were never thrown per
  the Cuts notes).
- The model's `kind` and tolerances, the per-frame sample reads and the coarse diagnostics are in
  `tracks/<stem>.json` under `stages.ball_model`, `meta.ball_model_per_frame`, `meta.coarse_info`.

## Files
`run.py` (entry), `picture_check.py`, `summarize.py`, `dev_proxies.json`, `tracks/<stem>.json` (loop-2 format +
`proxies`), `overlays/final__<stem>.jpg`, `overlays/check__<stem>.jpg`, `work/` (coarse base tracks, LGB/composition
intermediates, batch logs, debug sheets; gitignored).
