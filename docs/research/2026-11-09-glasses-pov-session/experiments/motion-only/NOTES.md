# motion-only: appearance-free ball detection (2026-11-09)

Run: `PY run.py <stem> [--device mps|cpu] [--no-sam] [--thr N] [--tag T]` from this folder (PY = analysis-engine venv).
Reads `S/work/cuts/cuts.json` + the cut; writes `tracks/<stem>.json` (loop-2 tracks format: frames [{f,x,y,r,src}],
boards, boards_raw, lane, lane_top_down with ft_cv, events, meta.stages, proxy), `overlays/final__<stem>.jpg` and
`overlays/picture__<stem>.jpg` (crops of the actual frames nearest 20/40/55 ft with that frame's circle). `summarize.py
[tag]` prints the proxy table and writes `proxies<tag>.json`. A dev-stem guard refuses any other stem unless `--any-stem`.

## What the ball stage does (nothing reads colour)
1. ORB + RANSAC homography between consecutive frames (loop-1 `camdiff.Motion`), three-frame residual
   min(|I_t - warp(I_t-1)|, |I_t - warp(I_t+1)|).
2. Per-frame lane from the loop-1 lane-first fit (`lane.fit_lane`, hint = frame bottom centre on the first frame, then
   the previous wood component), no ball needed. The residual is read inside the lane polygon widened 15 % and extended
   25 % of the span past the pd row (so the deck frames still produce candidates). Masking by the wood mask itself would
   delete a dark ball.
3. Geometric radius prior r_geo = 0.5 x 7.78 x lane_width_px(row) / 38 (ball 8.5 in). Rows with r_geo > 14 px: residual
   > 14, open 3 / close 5, blobs with aspect <= 2, fill >= 0.3 and half-extent in [0.45, 1.6] x r_geo. Rows with
   r_geo <= 14 px (roughly the last 20 ft): the three-frame min leaves only crescents of a slow small ball and the blob
   path fragments (111631 lost the ball at f355 at thr 14 and at thr 22), so the far band uses a disc-matched filter on
   the residual: mean inside a disc of r_geo minus mean in the annulus r_geo..1.7 r_geo (radii 5/8/11 px picked per
   row), peaks >= 8 with inner mean >= 6, top 6 per frame. On 111631 this returns exactly one candidate per frame,
   the ball, from 45 ft through the pin deck (f336-f368).
4. Chain: seed = first frame >= release+3 whose best blob has successors at k+1 and k+2 inside the gates (lateral <= 3
   boards/frame, radius ratio 0.6-1.6, image jump <= 4 r + 40 px, not moving toward the camera). Forward and backward
   walks with the loop-2 prediction (lane-coordinate line over the last 4 real points when the lane fits are trusted,
   else constant velocity through the homography chain), coast <= 3. Emitted r = r_geo where the lane fit is trusted.
5. SAM 2 (loop-1 `sam_track.track` / `track_back`, sam2.1_t, imgsz 1024) prompted with a box on the seed blob (never a
   colour blob), forward to cut pin_hit + 12 with the crop re-prompts, backward to release. Merge rule, fixed before the
   runs: a real chain point wins; SAM fills a frame without one when its r is inside [0.4, 2.2] x r_geo where r_geo <= 16
   and its board is within 3 boards/frame of the chain's last real point; else coast from the prediction.
6. Lane stage, series cleaning, pin-row estimate (geometric crossing, then pin motion override), deck decoy, depth,
   events and the overlay are `track_v2` functions imported from L2 with `CM.load_cut` pointed at this session's
   cuts.json and the composition `ball_stage` replaced by the injected points. Nothing in the ball stage was changed
   in L2; `pin_row_estimate` gets `{}` for the loop-1 quads (none exist for these clips).

## Off limits
Only the 8 dev stems were run (guard in `run.py`). The truth stems' cut files sit in the same `work/cuts/` folder; only
their cuts.json rows were parsed when loading the file, none of them was opened or run. The quarantine folder
`/Users/toka/pov-holdout/2026-11-09-glasses-pov-session` was not opened. `looked_at_truth_clips = false`.

## Dev proxies (8 dev stems, no truth; `proxies.json`, `proxies_nosam.json`, logs in `work/batch_dev_v1.log`, `work/batch_nosam.log`)
detection_rate = real (non-coast) ball frames / frames release+5..pin_row_frame_est (whatever its source);
max_board_jump = largest step of the 5-frame median of `boards` over release..pin_row; pin_row_detected = source not a fallback.

| stem | ball | points (sources) | detection | max jump | pin row (source) | cut pin_hit | geometric | pin motion | entry | wall s (SAM s) |
|---|---|---|---|---|---|---|---|---|---|---|
| 104946 | blue-purple | 80 (sam 16, residual 63, coast 1) | 1.000 | 1.08 | 447 (geometric) | 455 | 447 | - | 6.18 | 100 (86) |
| 105652 | blue-purple | 68 (sam 38, residual 28, coast 2) | 0.983 | 5.06 | 375 (fallback) | 375 | - | - | 8.27 | 93 (79) |
| 110442 | blue-purple | 78 (sam 8, residual 68, coast 2) | 0.985 | 1.49 | 427 (geometric) | 421 | 427 | - | 10.78 | 104 (91) |
| 111631 | black | 77 (sam 2, residual 73, coast 2) | 0.986 | 0.77 | 372 (pin motion f374-2) | 358 | 363 | 374 | 21.64 | 116 (99) |
| 112800 | black | 82 (sam 20, residual 59, coast 3) | 1.000 | 1.12 | 320 (geometric) | 310 | 320 | - | 16.16 | 67 (52) |
| 113911 | blue-purple | 61 (sam 51, residual 10) | 0.982 | 12.62 | 518 (fallback) | 518 | - | - | 18.08 | 98 (87) |
| 114631 | blue-purple | 65 (sam 19, residual 43, coast 3) | 0.982 | 0.67 | 578 (fallback) | 578 | - | - | 14.58 | 77 (65) |
| 115157 | blue-purple | 75 (sam 33, residual 41, coast 1) | 0.983 | 1.91 | 561 (fallback) | 561 | - | - | 4.41 | 94 (81) |

**Means (SAM fill on): detection_rate 0.988, max_board_jump 3.09 (0.77-1.91 on 6 stems; 5.06 on 105652 and 12.62 on
113911 are lane-fit boards during a head swing, see below), pin_row_detected 4/8, lane fallback 0/8, wall 94 s per clip
(ORB 3-6 s, lane pre-pass ~1 s, residual 2-12 s, SAM 52-99 s, lane stage + events ~2 s).**

Ablation `--no-sam` (residual chain alone, the only mutation check available without truth): detection_rate mean 0.694
(104946 0.776, 105652 0.475, 110442 0.939, 111631 0.972, 112800 0.766, 113911 0.175, 114631 0.754, 115157 0.695),
max_board_jump mean 2.53, pin row 4/8 (same stems), wall 11 s per clip. So the residual chain carries the mid and far
lane on every stem where the camera is steady (111631 and 110442 to the pins without SAM), and SAM 2 is what carries
the release frames (ORB has 0-8 failed pairs in the head swing, so the residual is undefined there) and the head
swings mid-roll (113911: the chain has 10 points, SAM 51). 115157 seeds only at release+43 (board 3, r_geo 11) and
105652 at release+30: the early blobs failed the radius band or the lane fit; SAM `track_back` filled release..seed.
Counter proof: `proxies()` on the 111631 track with frames emptied and a fallback source gives detection 0.0,
max jump None, pin_row_detected False; boards alternated +10 give max jump 9.98.

## Picture check (`overlays/picture__<stem>.jpg`, crops of the frame nearest ft_cv 20 / 40 / 55 with that frame's circle)
Read for 111631, 105652, 104946, 110442, 113911, 115157 (6 of 8).
- 20 ft: circle on the ball in all 6 (r 18-29 px; residual source on 5, SAM on 113911/105652).
- 40 ft: on the ball in all 6 (r 11-13 px, the ball sits just below the pins among their reflections: the last 20 ft of
  lane are a thin band in this POV).
- 55 ft: on the ball on 111631, 104946, 110442, 113911 (SAM centroid about r/2 right of centre on 113911); on 105652 the
  circle is on a dark round shape between standing pins (plausible, not certain); on 115157 the circle sits on the right
  gutter cap with no ball visible (`breakpoint_board` -0.28 at 51 ft, entry 4.41: likely a gutter ball, J3 case).
- `final__<stem>.jpg`: white = the track chained through the homographies into the pin-row-4 frame (frames whose chain
  crosses an ORB failure are left out), orange = raw track per frame, green = boards vs constant-speed depth, cyan =
  the edge lane used. On 111631 and 104946 the white path runs down the lane into the pins the quad marks.

## Pin row (loop-2 stage, unchanged) and what it does to the depth axis
- Geometric crossing fired on 4/8; pin motion overrode on 111631 (f374-2 = 372 vs cut 358 vs geometric 363). The cut
  pin_hit here is `audio crash onset - 17`; on 111631 the rack visibly moves at f374 in the camera-compensated
  difference, 16 frames after the cut's value, and the ball reaches the headpin base row at 363. The three disagree by
  up to 14 frames and every ft_cv readout is anchored to the pick, so the "40 ft" crops land at different real depths
  per stem. Diagnostic `pd_cross` in `summarize.py` (first ball frame whose bottom is at the edge-lane pd row) reads
  445 / 368 / 411 / 355 / 305 / 478 / 576 / 558 for the 8 stems, i.e. 2 / 16 / 8 / 15 frames before the geometric
  pick on 104946 / 110442 / 111631 / 112800 and 7 / 40 / 2 / 3 frames before the cut on the fallback stems.
- 105652, 113911, 114631, 115157 fall back to the cut pin_hit; on 105652 and 113911 the ball track ends 1 frame before
  the cut pin_hit (the ball is lost among the pins), so the "held crossing with 3 real frames after" never happens.
  The pin-motion clock needs a quiet baseline over cut-10..cut-1 and the pins are already moving there on those stems.

## Where the series goes wrong (lane stage, not ball stage)
- 113911: head swing f467-490 (ORB fails 8 pairs, the ball crosses the frame from x 563 to x 38 while standing still on
  the lane); the edge lane fit reads boards 31 on f475-477 against 20 before and 18 after, and `edge_quad` rejects f479-488
  ("ball outside the fitted lane"). `clean_series` only guards frames >= cut pin_hit-2, so the 12.6-board step stays in
  `boards`. One bad far-band accept too: f478 at (288, 894) was taken after 3 coasts with the carried r 34 making the
  jump allowance 352 px; `JUMP_GAP_CAP = 2` was added after the SAM runs (it changes nothing on the 8 no-SAM reruns,
  which are point-for-point identical; the SAM runs were not repeated because another agent's torch job was running).
- 105652: 5.06 step at the deck end (f368-374), ball among the pins.
- SAM r at the deck is 1.3-2x r_geo as in loop 2; emitted r is r_geo wherever the lane fit is trusted.

## Runtime for tonight (32 clips)
94 s per clip with SAM (MPS, SAM 2 tiny, imgsz 1024, full pass to cut pin_hit+12 then crop re-prompts, backward pass to
release) -> ~50 min sequential, one torch process at a time (do not overlap another agent's SAM job); the integration
run needs `--any-stem` (the dev guard) and 111218 (no cut) writes an empty track and exits 0; 11 s per clip without SAM (-> 6 min) but detection drops to 0.69 and 3 stems lose the
release half. Cheaper SAM: prompt from the seed and run only `track_back` plus a forward pass to seed+15 (the chain
carries the rest where the camera is steady) would cut SAM to ~30 s; not built.

## Verdict (dev proxies only; no truth seen)
Appearance-free candidates work: no colour window anywhere, black and blue-purple balls tracked alike (the dev set has
no green or red ball; those are untested), detection 0.99 with SAM fill, 0.69 without. The far-end disc-matched filter is the piece that made the residual usable past 45 ft.
Weak points are shared with loop 2 (pin-row pick, lane boards during head swings) plus a late seed on 2 stems.
Judge inputs: `tracks/<stem>.json` (events.entry_board, pin_row_source, boards), `overlays/picture__*.jpg` for J6.
