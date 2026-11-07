# Refute: hook-in-data (skeptic lens), 2026-11-07

Claim under test: the path track_v2 draws (ball lane-gated-ball + lane composition/edge+smooth3, path none) reflects
the measured ball and not a model prior.

Verdict: **NOT refuted on 9 of 10 throws. One throw, 191820, triggers the literal rule.** On 191820 the drawn marker
and the trimmed drawing disagree with the raw board at pin hit by 20.8 boards. The disagreement runs in the safe
direction (the raw point is a lane-fit artefact and the drawing is closer to the truth). Two separate measured problems
with the drawing are listed under "must fix for the showcase".

## Raw series recoverable? Yes
Every `results/tracks/<stem>.json` has `boards_raw` (55-73 frames). None of the 10 has a `path_fit` key
(`stages.path` = "none"). `path_fit_diag` is stored and is not drawn. Checked in code:
- track_v2.py:168 passes `path_fit={'board_at_60ft': final_board, 'kind': 'none (raw boards)'}` to the overlay.
- `composition.draw_overlay` draws the red top-down line only from `path_fit.boards_by_frame`, which is absent here.
- So what gets drawn is the `lane_top_down` points plus a marker at `final_board`.
- On 10/10 stems, `lane_top_down.board` equals `boards` (the rolling 3-frame median of boards_raw) within 0.01 on every frame.
- `final_board` is Theil-Sen over the raw-derived boards in pin_hit-10..pin_hit.
- Script: scratchpad hook_check.py. Its table is reproduced below.

## Per throw: raw vs path_fit_diag vs truth (f = SOURCE frame)
raw trend = least-squares slope x12 over boards_raw in pin_hit-11..pin_hit (lane/gutter zones). The truth trend is the
same slope over truth points up to the cuts pin_hit (n 6-10).

| stem | split | raw min @f | raw rise after min | raw trend12 | diag kind (rise) | diag b60 | raw @pin_hit | final_board | truth min @f | truth hooks | truth trend12 | truth @cut pin_hit | truth entry |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 185121 | dev | 10.13 @349 | 1.01 | +0.63 | line | 11.14 | 11.14 | 11.1 | 9.47 @350 | F | +0.21 | 11.00 | 11.13 |
| 185331 | dev | 3.78 @348 | 3.97 | +3.86 | line+hook (3.14) | 8.31 | 7.75 | 8.3 | 5.27 @346 | T | +2.54 | 7.95 | 6.88 (+-4.4) |
| 185454 | dev | 10.90 @376 | 0.15 | -1.19 | line | 11.04 | 11.05 | 11.0 | 11.62 @377 | F | -0.90 | 11.62 | 11.61 |
| 185645 | dev | 7.26 @295 | 0.62 | -0.42 | line | 7.59 | 7.88 | 7.6 | 7.41 @299 | F | -0.07 | 7.41 | 7.52 |
| 190115 | dev | 8.62 @441 | 0.26 | -0.48 | line | 8.79 | 8.88 | 8.8 | 8.74 @443 | F | -0.55 | 8.82 | 8.99 |
| 191253 | hold | 6.49 @425 | 2.95 | +3.01 | line+hook (2.74) | 8.69 | 9.44 | 8.7 | 5.75 @430 | T (marginal) | +3.45 | 8.94 | 9.47 |
| 191820 | hold | -2.40 @458 | 21.56* | +9.73* | line+hook (20.07)* | -1.60 | **19.16*** | -1.6 | 0.55 @441 | F | +2.57 | -2.69 | -2.41 |
| 191913 | hold | 7.61 @491 | 3.61 | +3.60 | line+hook (3.54) | 11.12 | 11.22 | 11.1 | 5.97 @503 | T | +2.81 | 9.89 | 10.10 |
| 192142 | hold | 6.18 @461 | 4.67 | +5.28 | line+hook (4.88) | 10.99 | 10.85 | 11.0 | 6.58 @466 | T | +4.47 | 11.19 | 21.65 @490 |
| 192636 | hold | 6.99 @441 | 7.05 | +5.97 | line+hook (6.52) | 13.79 | 14.04 | 13.8 | 7.49 @443 | T | +6.10 | 14.68 | 20.55 @461 |

\* 191820 f463 raw 19.16 is the known edge-fit artefact (camera whip at pin hit). The neighbours read -1.9 and -0.27.

### Test (i): fit hooks but raw boards do not
**0/10.** Every `line+hook` diag fit sits on a raw series that rises at least 2.95 boards after its minimum (185331,
191253, 191913, 192142, 192636), apart from 191820 (see test ii). Every `line` fit sits on a raw rise of at most 1.01.
The diag rise matches the raw rise within 0.83 on all five real-hook stems.

The raw hook direction agrees with the truth on 10/10:
- The 6 truth-hooking stems (185331, 191253, 191913, 192142, 192636) have raw trends of +3.0 to +6.0, against truth trends
  of +2.5 to +6.1.
- The 4 truth-monotonic dev stems have raw trends of -1.19 to +0.63.

The min position agrees within 5 frames and 1.5 boards everywhere except:
- 185331: raw min 3.78 is a single-frame dip at f348; its med3 is 5.5, against truth 5.27.
- 191913: see below.

### Test (ii): diag board_at_60ft more than 2 boards from raw at the pin-row frame
The track's own pin-row frame is the cuts pin_hit, because lane_top_down rescales depth so that the ball at pin_hit reads
60 ft.
- 9/10 are within 0.75 (185645 7.59 vs 7.88, 191253 8.69 vs 9.44; the rest are within 0.45).
- **191820: 20.8 boards (fit -1.60 vs raw 19.16). This is a literal refutation of that throw.**
  - The fit (and the drawn marker) is the right one: truth -2.69 at f463, entry -2.41.
  - The drawing also leaves out f463 under the more-than-6-boards trim (`overlay_trimmed_frames: [463]`).
  - So on 191820 the drawn path does not show the raw measured board at pin hit. A robust estimator and a trim rule
    stand in for it.
  - The scored series still contains it, which is why path_err_far is 7.98 there.
  - The 20-board diag hook is not drawn. The raw series also hooks, through that single frame only.
- If the truth's own pin_row_frame is used instead:
  - 185331 is off by 2.33 (raw 5.98 at f350 vs 8.31).
  - 191913 is off by 3.45 (raw 7.67 at f492 vs 11.12).
  - 191253 is off by 1.87.
  - The truth itself moves by a similar amount between its pin_row_frame and the cut pin_hit (185331 truth 5.36 -> 7.95,
    +2.59; 191913 truth 6.81 @495 -> 9.89 @509). So this is the cuts.json pin_hit vs observed pin row timing convention,
    not a prior.

### Is the far-end ball itself a prior?
In the last 12 frames, some points are `pred+refine`:
- 191913: all 12 (f498-509)
- 192636: 9 of 12
- 185331: 8 of 12
- 192142: 2 of 12

That means the SAM candidate was gated out and a purple matched filter searched +-max(2r,12) px around a straight-line
lane-coordinate prediction. The accepted point is a purple-weighted centroid (it needs response >= 0.40 and annulus
<= 0.35), not the prediction. Coasts in the far window: 0.

A straight-line prediction pulls toward continuing right. The raw series rises against it, so the hook is not
prior-made.

Crop check on 191913 f495-509 (scratchpad crop_191913.jpg): the track centre sits on the purple ball and within about
1 px of the truth's hand-read centre on all 7 frames. Example: f503 raw board 9.04 vs truth 5.97, with the same ball
pixel.

So 191913's far-end board gap comes from the per-frame edge lane, not the ball. The raw series turns at f491, and the
truth turns at f503 (or f495 if the truth's lone 5.97 read is noise; its own limits say +-1-1.5 boards per far point).
This is measured, not prior, but the shape of the drawn hook on 191913 is not the truth's shape.

## Overlay check (Read: final__192142, final__192636, final__191820)
All overlays show frame pin_hit-4, with the camera-compensated green path running to pin_hit.
- Green at the shown frame lands on the ball at that frame: 0.0 px (192142, 192636, 191913), 1.0 (191253), 2.4 (191820).
- The green end (the last drawn point) is 5.0 / 9.3 / 5.7 / 8.2 px from the ball at pin_hit-4, at full resolution
  (ball r 8-9). 191820 is 25.1 px, because its last drawn point is f462 after the trim.
- **The drawn path ends at the ball at the cut pin_hit: yes.**

## Must fix for the showcase (measured, not refutations of this lens)
1. **The drawn hook is truncated by the input pin_hit, not by the data.**
   - On 192142 and 192636 the observed pin contact is f490 and f461, 10 and 4 frames after the cuts pin_hit. The truth
     entry there is 21.65 and 20.55.
   - The drawing places the ball at 60 ft at the cut pin_hit and ends at 10.9 and 14.0: 10.8 and 6.5 boards short of
     the truth entry.
   - Raw at the cut pin_hit matches the truth at that frame (10.85 vs 11.19, 14.04 vs 14.68).
   - The 60-ft-at-pin_hit rescale of depth is the one model prior in the drawing. For the bowling-sense line, extend the
     track to the observed contact, or label the end "pin_hit (cuts)" rather than "pin row".
2. **Per-frame ft is noisy and drives the green zig-zag.**
   - Top-down points more than 5 ft from their neighbours' median: 191913 12, 185645 10, 192636 9, 185331 6, 191820 6.
   - Examples: 192636 f434/435 at 57.9 and 59.4 ft between 39.5 and 43.7; 192142 f416 at 21.4 ft at release.
   - Because the hook packs into f466-480, which read 51-60 ft, it occupies the top ~8 ft of the top-down panel, and it is
     invisible in the image-space line on 192636.
   - Draw from boards against the cv_fit (constant-speed) ft, not the per-frame ft.
3. Points at the pin_hit frame flagged `past_pins` by that per-frame ft fall out of the drawing: 185331 f358, 185645 f299
   and 191253 f434. On 185331 the drawn line therefore ends at f357.
4. 191820 is the one stem where the scored raw series (f463 = 19.16) and the drawing disagree. The before/after
   path_err_far mean of 1.394 includes its 7.98.

Inputs read: L2/results/tracks/*.json, L2/truth/*.json, the holdout folder (numbers only above), integrate_notes.md,
track_v2.py, composition/run.py (draw_overlay, path fit, smoothing), lane-gated-ball/run.py (prediction, gates, refine).
