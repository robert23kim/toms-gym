# wildcard: NCC template relay from a YOLO-chain seed (2026-10-10)

Lens: two ideas outside the parallel experiments. Probed dense optical-flow residual (dead) and NCC template
tracking (kept), built the NCC relay out. Scored with L/score_tracks.py (existing; mutation-checked below).

## What was built (`run.py <stem>`, `ncc_relay.py`)
1. Engine `scan_video` on the cut: YOLO boxes (conf 0.05) + ORB frame-to-frame similarity (8-11 s).
2. Engine `chain_detections`: the YOLO chain is used ONLY as a seed (its most confident box among its first 6;
   the chain starts 9-22 frames after release, so it never gives the near end). `seed_from_box` replaces the
   2-3x loose YOLO box by the dark blob inside it (ball centre + radius).
3. `relay()` forward to the cut end and backward to release: Lab-space TM_CCOEFF_NORMED template taken from the
   previous frame at 1.4 r, searched around the ORB-shifted prediction + ball velocity in a window of
   max(2.5 r, 40) px (+ half the speed); match accepted at NCC >= 0.55 (0.45 backward, with template scales
   1.0/1.15/1.3 because the ball grows toward release); up to 3 misses coast on the prediction. Each match is
   re-centred on the dark blob (L < ring median - 25) when a blob of 0.45-1.6 r sits within 0.7 r, which stops
   the template walk. Forward the radius may grow at most 1.03x/frame, backward 1.35x/frame; a backward ball
   bigger than 170 px ends the relay (ball still in the hand). Relay wall 0.1-1.6 s per video.
4. release = first tracked frame with the whole ball in frame and r <= 150 px. pin_hit = first frame (after
   seed+20) where the 5-frame mean camera-compensated speed < max(0.2 r, 1.5 px), plus 8 frames.
5. Engine `run_sam_lane_pass` with segment = track[release+12 .. pin_hit] (the 12 frames after release are the
   head swing: the aligner blew up on them, "mask top 166278 px short of the path"). Per-frame lane quads,
   boards and final_board come from the calibration; CANDIDATE_BACKS/AHEADS monkeypatched to (4,6,8)/(6,12)
   to bound the wall time when candidates fail. Overlay = pin_hit-4 frame, track polyline (raw image
   coordinates of every frame, so it bends with the camera), the SAM quad at that frame, the board as text.

## Dev table (v3 = final run, L/experiments/wildcard/tracks + overlays, scored by score_tracks.py)
| stem | recall % | median px | board_err | lane_err | window_err [rel, pin] | pass | wall s (scan/relay/sam) |
|---|---|---|---|---|---|---|---|
| 185121 | 88.9 (16/18) | 10.3 | 9.0 (WRONG LANE: SAM accepted the left neighbour, lane_err 57.3; baseline refused it) | 57.32 | [10, 1] | no | 155.9 (8.9/0.1/146.2) |
| 185331 | 91.7 (55/60) | 6.4 | 0.5 | 0.74 | [1, 3] | strong | 53.7 (8.4/1.1/43.6) |
| 185645 | 100 (62/62) | 4.3 | 1.5 | 0.32 | [1, 4] | strong | 48.9 (8.2/0.9/39.2) |
| 185454 | 100 (52/52) | 3.3 | 1.5 | 2.10 | [1, 9] | strong | 54.2 (9.6/1.2/42.6) |
| 190115 | 100 (55/55) | 3.1 | 0.5 | 4.85 | [0, 3] | strong | 131.9 (8.5/1.6/121.1) |
| **mean** | **96.1** (baseline yolo_chain_sam 72.0) | | 2.6 (1.0 over the 4 right-lane stems; baseline 0.5/3.5/2.5/0.5 on 4) | | | 4/5 (baseline 1/5) | 88.9 |

Wall time: 49-54 s when SAM accepts its first candidate; 132-156 s when it has to try 5 (190115, 185121) on
this shared 12-core box (other agents' torch runs were live; 185454 measured 93.7 s and 52.0 s on identical
input across the session). The relay itself is ~1 s; the budget is all SAM. Two of five dev stems missed the
120 s target.

## What worked
- NCC one-step oracle: 36/36 and 27/27 mid-lane, 14/15 and 15/15 at the far end (r 6-15 px). Sequential
  tracking with no oracle from the chain seed: 49/50 (185331), 37/41 (185454) before the blob re-centring.
- Backward relay reaches release on 4 of 5 (185454/185645/190115 within 1 frame; 185331 at 298 = truth).
- The far-end collapse (recall 57-60 % in the baseline) is gone: tolerance at the pins is 20 px and the relay
  holds 3-7 px median.

## What failed, with the number
- Farneback flow residual (probe A): one-step oracle 3/35 mid on 185331, 2/27 mid on 185454; the argmax
  residual blob sits at the search-window edge (errors 53-75 px = the window radius) because the global
  affine's own error exceeds the ball's residual on a head camera. Dead after ~20 min; not pursued.
- NCC alone drifted: 185454 sequential errors grew 5 -> 21 px over 40 frames (template walk); fixed by the
  dark-blob re-centring.
- Radius balloon at the pins: the blob merged the ball with the dark masking, r 10 -> 91 px on 185645
  (recall 85.5 %, last 9 frames 24-71 px off) and 185331 (end 8/15). Fixed by the 1.03x forward cap and the
  0.45-1.6 r blob gate: 185645 100 %, 185331 91.7 %.
- Lane-end gap pin-hit rule (scan the ball column upward in L or b* for the masking/pins): saturates at 1.2 r
  (scan from 1.3 r) or 2.4 r (from 2.5 r) on every frame of every stem - the scan hits the ball's own blur,
  not the deck. Dead; the speed rule replaced it (raw errors vs truth -9, -5, -12, +1, -5 frames).
- 185331 frames 301-307: truth r is 2.2-4 px on a ~100 px ball at 301 (tolerance 20 px); the relay is 28-61
  px off there (2 of the 5 misses); 356-358 among the pins 21-25 px off (the other 3).
- 185121: the backward relay stops at 307 (truth release 297: hand/arm over the ball), and SAM accepts a
  neighbour lane (board 3 vs truth 12). Same stem the baseline SAM refused; the segment end at pin-hit+8 put a
  "static" candidate at frame 64 with residual 7.8 px past the gate.
- Post-pin frames are still tracked (into the masking / ceiling on 185121, loops on 185331/190115): outside the
  scored window, harmless to recall, ugly on the overlay. 190115 also keeps 3 in-hand frames (387-389).

## Tuned on dev truth (say it plainly)
- Forward radius cap 1.03x, backward 1.35x, blob gate 0.45-1.6 r: chosen after reading the 185645/185331
  far-end failures against truth.
- release `max_r` 150 px (truth release r 107-130 px); SAM segment start release+12.
- pin-hit bias +8 frames: picked from the dev error distribution of the speed rule (-9,-5,-12,+1,-5). This is
  the most truth-fitted knob; it also moves the final-board read (185645 board 9 -> 7 vs truth 5.5).
- NCC thresholds 0.55/0.45, window sizes, 3 misses: set by hand on 185331/185454, not swept.
Holdout truth was never read or searched for; holdout stems were not run.

## Scorer mutation check (our track, 185454)
original: recall 100.0, median 3.3 px, board_err 1.5, lane_err 2.1. x+100 px on every track point and lane
corner: recall 13.5 (7/52), median 110.8 px, lane_err 44.16, board_err unchanged (1.5, the board is a number).
The 7 residual hits are near-release points with truth r 50-116 px (tolerance 2 r >= 100 px), as expected.

## Files
run.py, ncc_relay.py, tracks/<stem>.json, overlays/<stem>.jpg, work/: dump.py (box cache), probe_flow.py,
probe_ncc.py, offline_relay.py (relay vs truth without SAM), zoom.py (far-end crops), pin_probe*.py,
mutate_check.py, devrun_v3.log (the final run's SAM lines + scores), sam_<stem>.jpg (engine SAM overlays).
## Probes (two dev videos, 185331 and 185454; one-step oracle = start from the truth at f-1, moved by the camera model, and ask whether the method lands on the truth at f within max(2r, 20) px)

| probe | 185331 start/mid/end | 185454 start/mid/end | verdict |
|---|---|---|---|
| A. Farneback flow residual after a RANSAC affine global fit (half res, 97th-pct blob in a 60+ px window) | 2/8, 3/35, 0/0 | 7/9, 2/27, 3/15 | dead: the strongest residual blob sits at the window edge (errors 53-75 px = the window radius), the ball's own residual is weaker than the global-fit error on a head camera |
| B. NCC template (Lab, TM_CCOEFF_NORMED, template from f-1 at 1.3 r, ORB-shift prediction, window max(2r, 40)) | 3/8, 36/36, 14/15 | 8/9, 27/27, 15/15 | kept |
| B sequential, no oracle, seeded once at release+10 with per-frame template refresh | 49/50 | 37/41 (errors grew 5 -> 21 px: template walk) | drift fixed by re-centring on the dark blob each frame |
