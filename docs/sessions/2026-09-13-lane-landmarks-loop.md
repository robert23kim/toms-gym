# 2026-09-13 — Lane landmarks loop (pins, arrows, foul line as homography constraints)

Autonomous `/loop` run of `docs/research/2026-09-13-lane-landmarks/BRIEF.md`. Everything is in that
folder (README, scripts, `results/*.json`, `overlays/`, `review.mp4` gitignored). Nothing committed
(the brief says commit only when asked); the earlier loops' folders were not edited.

## What was done

- **E1 truth.** Ten-pin rack fitted as a rigid template (rule-book base coordinates through the
  annotated quad, similarity search on a white-map matched filter, per-column centroid refine),
  seven arrows as dark blobs on the rectified lane with a V-shape filter, foul-line ends from the
  annotation. Two independent pin widths agree to ~1 px; the arrows (no pin input) agree with the
  pins truth to ~1 px under one homography. Hand corners: 10 % too wide (sample_input), 4 % too wide
  (Chardie), 7 % too narrow + 4 px left (tom_old). Truth stored as fractions along the annotated top
  edge → applies per frame with no camera warp (`common.truth_corners(stem, f, "pins"|"all")`).
- **Re-scored loops 2-3** in three truths (loop 3's corners rebuilt from stored corner distances +
  widths + MAE; 92-100 % of frames unambiguous). tom_old's student: 3.15 → 1.61 boards; loop 2's
  far-end crop on sample_input: 0.89 → 0.15.
- **E2 detectors** from a rough lane on every frame: rack fit (0.8 s coarse search) with a
  one-column alias guard; classical arrows (55 ms). Learned arrows (two-class yolo11n-seg) = 0
  detections at 640 px; 1024 px training crashed in ultralytics' MPS assigner at batch 8/16, ran at
  batch 4.
- **E3 fits** (weighted robust DLT, x-only constraints for arrows, two-pass arrow re-detection,
  pins carried via ORB or via arrow similarity after the hit). Pins fix the far end on every frame
  (sample_input 1.19 → 0.37, tom_old 1.61 → 0.41 vs pins; 1.83 → 0.77 vs hand corners); arrows
  alone cannot extrapolate to the far end and add nothing with pins present; `arrows+pins10` with
  no foul-line input recovers the pre-hit lane to 0.05 boards.
- **E4**: landmarks as the camera model beat ORB on sample_input's hand per-frame corners (4.0 vs
  5.3 px; 2.4 vs 5.2 at the pin end) while the pins stand; arrows alone are ill-conditioned.

- **Refit floor.** Whatever lane goes in (0.26-1.62 boards), `corners+pins10` lands at 0.35-0.41 on
  tom_old: the per-frame rack fit's own noise. Pool the rack over the standing-pin frames next time.
- **Aside.** The two-class 1024 student (batch 4, no flip) gives a lane on every tom_old frame at
  0.26 boards vs pins (loop 3's 1024 model: 60 confident frames, 0.64) — recipe not isolated.

## Gotchas learned

- The brief said loop 3's per-frame rows carry `corners`; they carry `corner_err_px` + widths only.
  Rebuild by sign enumeration validated against the stored widths and MAE.
- Loop 1's `make_review_video` shadows a same-named module here (loop 1 is on `sys.path`) — name
  new scripts distinctly (`review_video.py`).
- `camera_all_*.json`'s `static_frame` is 122 for sample_input but the static corners match frame
  ~0; judging camera models on the static corners is meaningless there — carry the hand corners
  of frame 0 instead.
- ultralytics on MPS crashes in `tal.py::get_box_metrics` (`index out of bounds`, `shape mismatch`)
  with 8 instances per image at batch 8-16; batch 4 or `mosaic=0` avoided it on the folds tried.
- The loop-3 student's foul-line corners are 2-3 boards off on two videos: the "far end is the
  only error" premise held for SAM, not for the mask student.
- E3 default-argument bug: `kw.get("foul")` returns None for an absent key — use a default when
  None is itself a meaningful value.

## Open

- Foul-line / gutter-edge landmark detector at the near end (the student's near end is the next
  floor). Gradient snap was worse.
- Learned arrows: zero held-out detections at 640 and 1024 px. Measured cause: with mosaic the arrow
  class has AP 0 even in-distribution (half-scale tiles put a 6 px arrow under the stride); without
  mosaic it reaches AP50 0.7 on the training videos and 0 on a new video — memorised positions, not
  appearance (README, Blocked). Aside: the two-class 1024 student at batch 4 gives a lane on every
  tom_old frame at 0.26 boards vs pins — a lead, recipe not isolated.
- Real board-number ground truth still does not exist; the pins truth is the best available ruler.
