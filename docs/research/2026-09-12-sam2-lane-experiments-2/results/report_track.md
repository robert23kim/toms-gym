# Track 1: the lane through the whole throw, and which frame to trust

Agent `track-1`, 2026-09-12. Code: `run_track.py` (this folder). All numbers below come from
`results/video_carry_track.json`, `results/video_carry_span_track.json`,
`results/best_late_prehit.json`, `results/late_median_prehit.json`,
`results/video_keep_track_tiny.json`. Metric, truth and prompts are the loop-1 ones
(`common.py` -> `lane_sam.score`), unchanged.

## Headline

**One self-supervised test -- how far the lane's centre sits from the median centre over the
throw -- turns SAM 2 video mode from unusable into the best per-frame result in either loop, and it
costs no SAM calls.** Per-frame board MAE, mean / median / max:

| method | sample_input | Chardie | tom_old |
|---|---|---|---|
| `video_rev` (loop 1) | 1.85 / 0.98 / 5.71 | 16.39 / 4.02 / 75.39 | 3.73 / 2.35 / 7.71 |
| **`video_carry`** (loop-1 `video_rev` masks + gate) | **0.98 / 0.84 / 4.65** | **0.41 / 0.31 / 0.86** | **1.94 / 1.85 / 2.48** |
| `video_span` (loop 1) | 2.00 / 1.06 / 6.13 | 19.45 / 3.86 / 67.64 | 3.55 / 2.23 / 7.58 |
| **`video_carry_span`** (loop-1 `video_span` masks + gate) | **1.33 / 1.03 / 4.97** | **0.34 / 0.27 / 0.71** | **2.00 / 2.05 / 2.40** |

Frames within 2 boards went 66.3 / 37.9 / 12.8 % to **90.7 / 100.0 / 52.7 %**. The worst frame of a
throw, which is what a production board number would be quoted against, went 5.71 / 75.39 / 7.71 to
**4.65 / 0.86 / 2.48**.

Single-frame results are the opposite story: **choosing between the six frames before pin contact is
worth at most 0.33 boards, and the picker that chooses is not needed.**

## 1. `video_carry` -- gate the tracked masks, carry the lane through occlusion

No SAM re-run. The loop-1 per-frame masks are re-fitted exactly as loop 1 fitted them
(`L.fit_edges`; verified bit-for-bit -- max |delta| against the stored `per_frame` MAEs is 0.0 over
all 300 scored frames), then each frame gets six truth-free quality numbers, and frames that fail
the gate take the nearest passing frame's lines warped through `L.transform`.

### The gate is one feature, and it is not one of the four in the brief

Every frame's lines are warped into one reference frame, so the lane's **centre at the bottom row**
should be constant over the throw. The test is `|centre - median centre| / median width > 0.03`.
Ablation (the `gate_ablation` field of every `video_carry` row; each cell is mean / median / max,
frames replaced, flag precision):

| gate | sample_input | Chardie | tom_old |
|---|---|---|---|
| none (= loop 1) | 1.85 / 0.98 / 5.71, 0r | 16.86 / 4.02 / 75.39, 5r | 3.73 / 2.35 / 7.71, 0r |
| **centre .03 (shipped)** | **0.98 / 0.84 / 4.65, 44r P0.80** | **0.41 / 0.31 / 0.86, 53r P1.00** | **1.94 / 1.85 / 2.48, 72r P0.90** |
| centre .05 | 1.03 / 0.89 / 4.02, 34r | 0.75 / 0.82 / 0.88, 52r | 1.74 / 1.85 / 2.48, 70r |
| centre .08 | 1.28 / 0.98 / 4.11, 30r | 0.82 / 0.84 / 1.09, 51r | 1.65 / 1.85 / 2.48, 68r |
| person overlap .15 alone | 2.84 / 3.37 / 6.62, 60r | 32.57 / 33.22 / 65.64, 44r | 4.56 / 3.38 / 7.65, 106r |
| fit residual 1.5x median alone | 1.85 / 0.98 / 5.71, 0r | 30.52 / 6.22 / 67.91, 37r | 3.71 / 2.34 / 7.71, 25r |
| lane width .88-1.12 alone | 0.98 / 0.89 / 3.57, 31r | 31.81 / 0.83 / 75.39, 35r | 2.11 / 2.12 / 2.48, 70r |
| row coverage .55 alone | 1.85 / 0.98 / 5.71, 0r | 18.72 / 4.02 / 75.39, 8r | 3.73 / 2.35 / 7.71, 0r |
| **the brief's four** (resid+cov+width+person) | 0.80 / 0.68 / 4.49, 71r | **34.08** / 62.09 / 65.49, 46r | 1.97 / 2.12 / 2.46, 115r |
| centre .03 + person .15 | 0.94 / 0.74 / 4.49, 78r | 0.64 / 0.65 / 0.86, 58r | 1.97 / 2.12 / 2.46, 115r |
| all six (k=5) | 0.74 / 0.55 / 3.41, 78r | 0.63 / 0.64 / 0.86, 58r | 2.15 / 2.11 / 2.46, 115r |

Reading of that table:

- **The four features the brief named cannot catch Chardie's failure.** Its worst frames (74-90) are
  a mask that jumped one lane to the left: width ratio 0.99-1.02, residual near the median, row
  coverage 0.76, bowler nowhere near it. Every geometric health check says the mask is fine. Only
  the centre says it is 250 px (1.5 lane widths) from where it was. Gating on the brief's four
  features alone makes Chardie **worse than loop 1** (34.08 against 16.86), because it replaces the
  good frames and then carries *from* a lane-jumped frame.
- **Residual, coverage and width are redundant given the centre.** On sample_input a
  one-at-a-time sweep of `resid_ratio`, `cov`, `width_lo` and `width_hi` across their whole range
  changed nothing at all: the frames they flag are a subset of the ones the centre test flags.
- **Fit residual cannot be an absolute threshold.** sample_input's sub-pixel row residual is
  3.9-13.2 px on *every* frame (a 1500-row lane edge is not a straight line at that length), while
  Chardie's is 1.3-6.8. A 3 px cut fails every frame of one video and no frame of the other. The
  first version of this gate did exactly that and was a silent no-op.
- **Do not re-estimate the residual median over the passing frames.** It is a ratchet: the median
  falls, more frames fail, it falls again. That left 5 of 91 sample_input frames passing and made
  the result worse than loop 1 (2.52). The width and centre medians are re-estimated (3 passes) and
  must be, because on Chardie more than half the throw is occluded and the first median is pulled by
  it.

### Gate statistics

| | sample_input | Chardie | tom_old |
|---|---|---|---|
| frames replaced / total | 44 / 91 | 53 / 111 | 72 / 154 |
| flag precision / recall | 0.80 / 1.00 | 1.00 / 1.00 | 0.90 / 1.00 |
| MAE on replaced frames, before | 3.13 / 3.38 / 5.71 | 24.84 / 11.58 / 75.39 | 5.54 / 6.81 / 7.71 |
| MAE on replaced frames, after | 1.31 / 1.04 / 4.65 | 0.31 / 0.31 / 0.32 | 1.65 / 1.73 / 1.74 |
| MAE on kept frames | 0.68 / 0.76 / 1.35 | 0.60 / 0.62 / 0.86 | 2.19 / 2.25 / 2.48 |
| oracle (per frame, best of own mask or carry) | 0.80 | 0.41 | 1.92 |

Precision and recall are against a truth-only oracle: a flag is correct if carrying that frame
actually lowered its board error. **Recall is 1.00 on all three videos** -- the gate never leaves a
frame on its own mask when carrying would have helped. Precision is 0.80-1.00; the false positives
are frames whose own mask was already good, and they cost 2-3 boards each on sample_input (below).
The gated result is within 0.02-0.18 of the oracle on all three.

Checked on the pixels, not just the number: `vis_20260112_121117_80.jpg` in the scratchpad shows the
raw mask tinted over the *neighbouring* lane with the predicted quad one lane left of the truth
quad, and the carried quad sitting on the truth quad. The 64.53 -> 0.31 on that frame is a real fix,
not a metric artefact.

### What did not work, and the number that explains it

**Carrying from the median of the k nearest passing frames instead of the single nearest.** The ORB
camera model's *per-frame* jitter at the pin end is 3.02 px mean / 8.90 px max on sample_input,
against only 10.41 px of cumulative motion over 19 frames. A board is 1.5 px there, so a single
source frame inherits about 2 boards of jitter and a median over five should average it away. It did
not: k=5 moved sample_input 0.98 -> 0.94 but Chardie 0.41 -> 0.64 and tom_old 1.94 -> 2.19. Being
*close* beats being *averaged*, because a median over five pulls in frames whose cumulative drift is
worse than the jitter it cancels. Shipped `k=1`.

**The three false positives on sample_input cost 2.2-3.4 boards each.** Frames 120, 127 and 128 have
centre deviations of 7.6-7.7 px against a 7.2 px threshold, so they are replaced from 2 frames away
and go 0.13 -> 3.37, 0.28 -> 2.85 and 0.21 -> 2.40. A 2-frame carry costing 2.4 boards is that same
3 px/frame jitter. This is why `video_carry`'s *last-frame* number on sample_input is 2.40 against
loop-1 `video_rev`'s 0.21 -- the per-frame mean improves while that one frame regresses. If the last
frame is what a caller wants, do not gate it; gate the frames you are tracking through.

**A caveat on Chardie and tom_old that sample_input does not have.** Their truth is a single static
`lane_edges` warped to each frame through the same ORB model the carry uses, so "carry the lane
through the camera model" is close to how their truth is constructed and 0.41 / 1.94 are optimistic.
sample_input has an independent hand annotation and is the honest test -- and there the gate still
goes 1.85 -> 0.98. Note also that sample_input's per-frame annotation is piecewise constant with
blocks starting at frames 0, 1, 31, 59, 96 and 109, so frames 109-128 are all scored against one
frozen set of corners while the camera really does move; that penalises any camera-following method
inside a block.

## 2. `best_late` -- six frames before pin contact, pick one without truth

SAM (`sam2.1_b`, `C.even_points_keep` 3 points, `E.soft_rows` + `E.fit_pair`) on prehit-1 ..
prehit-6. The picker ranks candidates on fit residual, row coverage, gradient peak strength and
drift along the fitted lines (`E.snap_rows`), and Laplacian sharpness inside the lane, then takes the
best summed rank. It never sees the truth.

| | picked | picked MAE | oracle frame / MAE | regret | all six candidates |
|---|---|---|---|---|---|
| sample_input | f118 (prehit-1) | 0.22 | f113 / 0.11 | 0.11 | 0.22, 0.24, 0.24, 0.16, 0.20, 0.11 |
| Chardie | f132 (prehit-2) | 0.88 | f128 / 0.55 | 0.33 | 0.86, 0.88, 0.75, 0.59, 0.72, 0.55 |
| tom_old | f166 (prehit-5) | 2.18 | f166 / 2.18 | 0.00 | 2.21, 2.29, 2.29, 2.21, 2.18, 2.21 |

**Frame choice inside the clean window is worth nothing.** The spread between the best and worst of
six consecutive pre-hit frames is 0.13 / 0.33 / 0.11 boards. Loop-1 finding 2 ("which frame matters
more than which prompt") is about the *window* -- bowler on the lane or off it, 6 to 31 boards -- not
about frames within it. Once the bowler has cleared, one frame is as good as the next.

**The picker is not good, it is just unnecessary.** It picked the worst of six on Chardie. Its
features are near-constant across the candidates (residual 4.3-7.3, gradient peak 262-266, coverage
0.95, gradient rows 1.00 on sample_input), so there is no signal to rank on -- which is the same fact
as "the frames are equivalent", seen from the feature side. Do not build this.

Against the other loop-2 single-frame rows on the same frame kind: `softk_prehit` (the same prompt
and edge fit, pre-hit frame only) is 0.24 / 0.88 / 2.29; `best_late` is 0.22 / 0.88 / 2.18. Six SAM
calls buy 0.02 to 0.11 boards over one.

**tom_old prefers the pin-hit frame itself.** All six pre-hit candidates sit at 2.18-2.29 while
loop-1 `even3_last` on frame 171 (the pin-hit frame, excluded from the pre-hit family by
construction) is 1.35. Backing off from pin contact costs about 0.9 boards there. Motion blur is not
the reason: frame 170's sharpness is 1516 against 3817 for frame 166, so the *sharpest* candidate is
not the best one.

## 3. `late_median` -- median of the six late frames' lines

| | warped into the pre-hit frame | unwarped | best single candidate |
|---|---|---|---|
| sample_input | 0.44 | **0.23** | 0.11 |
| Chardie | **0.79** | 1.05 | 0.55 |
| tom_old (tripod) | **2.14** | 2.21 | 2.18 |

Warping helps where the camera model is clean (Chardie 0.67 px/frame jitter, tom_old 0.86) and hurts
where it is not (sample_input 3.02 px/frame: 0.23 unwarped becomes 0.44 warped). On the tripod the
two agree to 0.07 boards, as they should. In no case does the median of six beat the best single
frame, and in no case does it beat `best_late` by more than 0.04. Same conclusion as loop-1
finding 5, reached from the late window instead of the whole span: **merging frames on a handheld
video is capped by stabilisation, and there is nothing to gain by merging frames that are already
equivalent.**

## 4. `video_keep` -- re-prompt video mode with `even_points_keep`, tiny weights

SAM 2 video mode (`sam2.1_t`) prompted once on the pre-hit frame with `C.even_points_keep` (3 points,
so all three survive instead of the two `track_points_even` leaves), propagated backwards to release,
then the same gate. See `results/video_keep_track_tiny.json` for the rows. This is the only method
here on tiny weights and on a shorter frame range (release .. pre-hit, not release .. last), so it is
not directly comparable with the table at the top; it was the optional fourth item and is reported
for completeness rather than as a recommendation.

| | gated (shipped) | ungated (same masks) | frames | replaced | P / R |
|---|---|---|---|---|---|
| sample_input (f117 prompt) | 1.04 / 0.93 / 4.62 | 2.05 / 1.21 / 5.37 | 80 | 39 | 0.86 / 1.00 |
| Chardie (f132) | 2.29 / 2.48 / 2.48 | 19.61 / 4.30 / **350.56** | 73 | 69 | 0.62 / 1.00 |
| tom_old (f169) | **1.75 / 1.82 / 2.30** | 3.51 / 1.99 / 7.64 | 152 | 74 | 0.89 / 1.00 |

Two things worth keeping from this run:

- **The gate reproduces on masks it was not tuned on.** These are fresh masks from a different
  prompt, a different weights file and a different frame range, and the gate still improves every
  video (2.05 -> 1.04, 19.61 -> 2.29, 3.51 -> 1.75) with recall 1.00 again. The thresholds were set
  on the `video_rev` masks, so this is the closest thing to a held-out check available here.
- **tom_old's 1.75 is the best per-frame mean on that video anywhere in either loop** (loop 1: 3.55
  and 3.73; `video_carry`: 1.94), and 93.2 % of its frames land within 2 boards against 12.8 % in
  loop 1. Chardie is the loser: 2.29 against `video_carry`'s 0.41, and its ungated max of 350.56
  boards means the backwards propagation from the pre-hit frame collapsed somewhere -- with 69 of 73
  frames replaced, that method is the gate carrying four frames, not tracking.

## Recommendation for the engine

1. **Prompt once on a clean late frame and propagate** (loop-1 recommendation 3 stands), then **gate
   every frame on lane-centre consistency** and carry the nearest passing frame's lines through the
   camera model. One scalar per frame, no extra model, no YOLO. This is the whole win: 16.39 -> 0.41
   on the video where video mode was unusable, and 3.73 -> 1.94 on the tripod.
2. **Do not gate the frame you prompted on**, and do not gate the frame whose number you are about to
   quote; the false-positive cost there is 2 to 3 boards.
3. **Do not spend SAM calls choosing a late frame.** Take any frame after the bowler clears; six
   consecutive ones differ by 0.11 to 0.33 boards. Spend the calls on the ball detector instead.
4. **Carry from one frame, not a median of several.**
5. Camera-model quality is now the binding constraint on everything that moves a lane between frames.
   Per-frame jitter, not cumulative drift, is the number to improve: 3.02 px/frame on sample_input is
   2 boards at the pins.

## Open questions

- Does the centre test survive a video where the *correct* lane really does shift in the reference
  frame -- a pan the ORB model under-fits, or a camera that re-frames mid-throw? All three videos
  here drift smoothly. A trend-fit reference centre instead of a constant median would cover it and
  was not tested (out of budget).
- The gate needs a reference statistic over the whole throw, so it is a post-pass, not streaming. A
  causal version (running median over the frames so far) is untested and would behave differently at
  the start of a throw, which is exactly where Chardie is occluded.
- Thresholds were set by looking at three videos' feature distributions next to their errors. There
  is no held-out video. The sweep shows the result is flat between `ctr_frac` 0.03 and 0.08
  (0.98-1.28 / 0.41-0.82 / 1.65-1.94), so it is not knife-edge, but the constant is not validated.
- Chardie's and tom_old's carry numbers are partly circular (their truth is warped through the same
  camera model). Reproducing this on a video with independent per-frame corner annotation is the test
  that would settle it.
- Why does tom_old's pin-hit frame beat all six frames before it by about 0.9 boards? If it is the
  pins falling changing the bright pin-deck boundary, that is a general effect worth knowing.

## Reproduce

```
V=~/code/bowling-app/analysis-engine/.venv/bin/python
SCRATCH=/private/tmp/claude-502/-Users-toka-code-toms-gym/aec659a7-dd91-473a-be23-bf34027e9b97/scratchpad
cd docs/research/2026-09-12-sam2-lane-experiments-2

# YOLO person boxes (only needed for the person-overlap ablation rows)
PYTHONPATH=$PWD $V $SCRATCH/track-1/prep_person.py

$V run_track.py --methods video_carry,video_carry_span --kinds track    # ~30 s, no SAM
$V run_track.py --methods best_late,late_median --kinds prehit          # ~40 s, 18 SAM calls
$V run_track.py --methods video_keep --kinds track --weights sam2.1_t.pt --tag _tiny  # ~4 min

$V run_track.py --dump video_rev --stems sample_input   # per-frame feature table + gate decisions
$V run_track.py --sweep video_rev                       # one threshold at a time, all three videos
```

Masks and lines for the review video are written to `$SCRATCH/masks/masks_<method>_<stem>.npz` and
`lines_<method>_<stem>.json` for `video_carry`, `video_carry_span` and `video_keep`, in the loop-1
packbits format.
