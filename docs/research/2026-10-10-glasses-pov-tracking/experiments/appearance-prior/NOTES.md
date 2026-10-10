# appearance-prior: glasses-POV ball tracker (2026-10-10)

Lens as briefed: learn the ball's appearance from the ~30 in-hand frames before release, then detect by histogram
back-projection + perspective size prior + motion continuity; compare with a fixed purple hue and with yolo11n_bowling.

**Headline: dev mean recall 97.5 % (baseline yolo_chain_sam 72.0 %), 3/5 dev pass (baseline 1/5), board_err 0.5 / 1.5 / 1.5
where SAM calibrates.** The *learned* appearance half of the lens is dead (20.7 %); what works is a fixed purple-hue
window for the first ~20 frames and a camera-compensated **motion peak** for the rest. See the table.

## The premise was wrong on these clips
The ball does not fill the bottom of the frame before release. Source frames (sheets `debug/pre_185331.jpg`, `debug/pre_190115.jpg`;
`debug/sheet_185331.jpg` is the cut): at rel-60..-50 the ball is a shadowed sliver in the hand at the bottom corner, from rel-40 to
rel-2 it is **out of frame** (backswing; the camera looks at the approach floor), and it enters at the frame bottom on the
release frame at r 105-135 px, sharp by rel+1. So the free appearance source is release..release+3, not the walk-up.

## What was built (`run.py <stem>` -> `tracks/<stem>.json`, `overlays/<stem>.jpg`)
- `cache_scan.py`: one YOLO (conf 0.1) + ORB-shift pass per cut via the engine's `yolo_chain_pass.scan_video`,
  cached in `cache/<stem>.json` (8-10 s per cut). Only the ORB shifts are used by the default config.
- `apptrack.py`:
  - start: first cut frame in [6, 18] with a *round* purple blob (fill >= 0.6 of its bbox, aspect 0.75-1.35, r >= 50) in
    the lower 70 %. Roundness is what separates the ball (fill 0.63-0.79) from the gutters / ball-return cap (0.1-0.55).
  - near/mid range: connected components of the hue mask (fixed: H 110-175, S >= 20, V >= 40; learned: H-S histogram
    back-projection), size prior r(k) = A / (k - k0 + 2) fitted from accepted blobs (truth fits r ~ 380/(f-296) on
    185331), gate 3 r + 40 px grown by the misses and by 1.5x the last step, prediction = previous position through
    the engine's `reliable_shift` ORB shift + camera-compensated velocity, first step gate 700 px (the ball leaves the
    hand at 300-450 px/frame).
  - far end (r_pred < 30 px): candidate = argmax within the gate of blackhat(gray, 4 r) x |frame - warp(prev frame)| x
    blurred purple window; radius from the prior. Re-acquisition after 2 misses: any round blob of the predicted size
    anywhere in the frame (185121: the ball leaves the frame top at 299-306 and re-enters at 307).
  - YOLO boxes (conf >= 0.2) can be added as candidates (`--yolo`); no gain, off by default.
- `run.py`: SAM lane pass = the engine's `run_sam_lane_pass(cut, segment=track)` prompted with **pin_hit from
  cuts.json** (cut-local) and a segment that starts where the ORB shifts are reliable (3 frames >= 30 inliers) and ends at
  pin_hit+2. Lane per frame from `calib.to_dict()['per_frame']`, `final_board` from the engine's board summary.
  All written frames are source numbers (asserted inside [cut_start, cut_end]). 191900 (no cut) writes an empty track.
- `eval_dev.py [flags]`: runs the 5 dev cuts sequentially, scores with `L/score_tracks.py`, writes `results/<tag>.json`.

## Dev table (final config: `--model fixed`, no YOLO candidates, SAM lane; `results/fixed_noyolo_sam.json`; a re-run under the tag final_fixed_sam was cut off by the session budget, same config)
| stem | recall % (matched/truth) | median px | board (truth) | board_err | lane_err | wall s incl. scan | pass |
|---|---|---|---|---|---|---|---|
| 185121 | 94.4 (17/18) | 5.8 | - (12.0) | - | - | ~106 | no (SAM refused: resid 8-58 px / mask 392 px short) |
| 185331 | 93.3 (56/60) | 3.2 | 4.0 (4.5) | 0.5 | 0.21 | ~71 | yes |
| 185645 | 100 (62/62) | 3.8 | 7.0 (5.5) | 1.5 | 0.18 | ~61 | yes |
| 185454 | 100 (52/52) | 3.2 | 12.0 (10.5) | 1.5 | 2.34 | ~132 | yes |
| 190115 | 100 (55/55) | 3.2 | - (8.5) | - | - | ~108 | no (SAM refused: resid 13-22 px, "far end too wide 69/50") |
| mean | **97.5** | | | 1.17 (n=3) | | | **3/5** |
Baseline yolo_chain_sam: 89 / 57 / 86 / 60 / 69 -> 72.0 %, boards - / 0.5 / 3.5 / 2.5 / 0.5, pass 1/5.
The 4 misses on 185331 are truth entries with r 1-3 px (301, 304, 306, 307) next to r 65-90 neighbours (tolerance 20 px
on an 80 px blurred ball); the 185121 miss is 307, the re-entry frame after the out-of-frame window.
During that out-of-frame window (299-306, not scored) the 185121 track holds 3 false blobs at the frame top (overlay:
the orange excursion to the top right) before re-acquisition; trim or gap-fill those frames in a render.
Wall: track 1 s, YOLO+ORB scan 8-10 s, SAM 50-120 s (refusals cost the most: 8 candidate frames). 185454 is over the
120 s target (SAM 121 s); the scan could drop YOLO (only the ORB shifts are used) for -8 s.

## Ablations (dev, no SAM, `results/cmp_*.json`, `variants/`)
| config | mean recall % | note |
|---|---|---|
| fixed hue, blobs only (no motion, no re-acquire) | 68.8 | 185121 5.6 (lost at the frame top), far end drifts 40-50 px on 185331/185645 |
| + camera-compensated motion weight + re-acquisition | 87.4 | 185121 83.3; far end still off by 36-66 px on the last 15-20 frames |
| + far-end motion peak (final) | **97.5** | |
| final + YOLO candidates | 97.5 | identical |
| learned H-S histogram (start frame), bp thresh 10/20/40/80 | 17.0 / 17.0 / 20.7 / 1.1 | loses the ball on frame 2 on 4 of 5 stems |
| adaptive histogram (blend 0.15 per accepted blob) | 20.7-24.1 | same |
| YOLO boxes only as candidates (conf >= 0.2) | 0.7 | no box on the first 10 frames: 0-2/10 per stem |
Raw YOLO any-box recall on the truth frames (conf 0.1): 78 / 42 / 60 / 63 / 64 %; first 10 frames 0-2/10,
last 15 frames 0-5/15: the detector misses both ends, which is exactly where the colour blob and the motion peak work.

## What worked
- A fixed purple window is a near-perfect detector on the lane surface (185454 100 %, 190115 94.5 % from colour alone).
- Roundness (fill + aspect) for the start frame; a perspective size prior r ~ A/(k-k0) that holds within +-50 %.
- **Camera-compensated frame difference at the far end** (probe_far.py, dev truth, +-80 px window around the shifted
  previous truth point): motion peak within 12 px on 22/23 (185331) and 21/23 (185645) frames of the last 22; blackhat x
  motion x hue 22/23 and 23/23; blackhat alone 0/23; hue 2/23 and 0/23.
- Prompting SAM with the cut's pin_hit and a segment that skips the release frames (ORB 5-17 inliers, scale 0.4; the
  warped path reached y = -167000) took SAM from 1/5 to 3/5 calibrated, boards 0.5-1.5.

## What failed, with the number
- Learned appearance: 20.7 % vs 97.5 % fixed. The ball washes out along the roll (truth HSV median: S 157 -> 50,
  V 90 -> 150, H 126 -> 147 from r 107 to r 10) and at the pin deck the glossy floor reflects the purple backdrop
  (ring S 35 vs ball S 55, V 100 vs 85): no colour model separates the far ball, and the start-frame histogram
  (motion-blurred ball + hand) does not even hold on the next frame on 4 of 5 stems.
- Colour blobs at the far end: hue mask peak 0-2/23 within 12 px (above). The fixed-hue track drifts onto the gutter
  capping / pin-deck reflections 36-66 px right of the ball for the last 15-20 frames.
- Pin-hit self-estimate from motion energy around/above the ball: no spike (4-10 throughout, probe_pinhit.py), so the
  SAM prompt uses cuts.json (declared below). SAM retry with the prompt moved -8 frames: still refused on 190115, +100 s.
- SAM on 185121 and 190115: residual 13-58 px on every candidate frame (the head swings; 185121 was refused in the
  baseline too), r x3 inflation and back=10 change nothing. No board on those two, so they fail the pass gate at 94-100 %
  recall.
- YOLO as a candidate source: 0.7 % alone, +0 on top of the final.

## Tuned on truth (dev) / declared uses of cuts.json
- The cuts themselves encode release (cut_start+10) and pin_hit (cut_end-20): the start search window [6, 18] and the
  SAM pin_hit prompt read cuts.json's `pin_hit_frame` directly. `pin_hit_frame` in the track = SAM's last_lane_frame when
  calibrated, else the cuts.json value (so window_err is not a tracker output).
- Hue window H 110-175, S >= 20, V >= 40 and the far-end purple window H 125-175, S >= 25 were set from the ball/background
  HSV percentiles along the dev truth tracks (explore_hsv.py); roundness thresholds (fill 0.6, aspect 0.75-1.35) from
  listing the components at k 6-16 on all five dev cuts; motion_r = 30, motion_full = 12 by hand on 185331.
- The probes (probe_far.py, probe_pinhit.py) read dev truth to pick the far-end map; nothing holdout was read.

## Scorer mutation check (this experiment's 185454 track, re-read from score_tracks.py output)
as-is: recall 100.0, median 3.2, board_err 1.5, lane_err 2.34, pass true; track+lane shifted +100 px, board +5:
recall 15.4, median 99.2, board_err 6.5, lane_err 44.77, pass false. (`debug/20260915_185454_f240c883_shift100.json`)

## For the showcase render
The track runs to the cut end: after `pin_hit_frame` the ball rolls along the pin deck into the pit (the leftward tail in
the overlays). Trim at `pin_hit_frame` when drawing the trace.

## Follow-ups
- Drop YOLO from the scan (ORB only) for -8 s; the SAM refusals on a swinging head need a different lane prompt (the
  far-end motion track is clean, so the pin-row / pin-rack refit path in the engine may do better than the mask-top gate).
- Holdout not run (budget); run.py works on any stem with a cut.
