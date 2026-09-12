# SAM 2 lane detection experiments — 2026-09-12

## What this was
Tom asked how Segment Anything works and whether it can be tuned for bowling, then
whether it had been tried before, then started a self-paced loop: run SAM 2 lane
experiments with several prompting methods, document them, and produce a review video.
Ball tracking was out of scope (annotated ball positions stand in for a detector).

## What changed
- New research folder `docs/research/2026-09-12-sam2-lane-experiments/`: `README.md`
  (setup, camera-motion truth, results table, nine findings, recommendation),
  `lane_sam.py` (prompt builders, edge fit, per-frame truth, metric, overlays),
  `run_methods.py` (35 registered methods), `camera_motion.py` (ORB similarity per frame
  + validation against sample_input's per-frame annotation), `make_review_video.py`,
  `results/*.json` + `results/summary.md`, `overlays/*.jpg`, and `review.mp4`.
- `CLAUDE.md` gained a "Bowling Lane via SAM 2 (research, 2026-09-12)" section with the
  durable rules (prompt spacing, frame choice, the ultralytics nested-points gotcha, the
  prompt-anchored component rule, handheld drift, the pin-hit cut, tiny weights).
- Committed as `132280e` on `main` (165 files; overlays shrunk to ~8 MB; `review.mp4` is
  gitignored inside the research folder). The earlier new-stack folder went in as `3c99747`.
  Not pushed.
- Memory note `sam2_lane_experiments.md`. No product, engine or deploy code touched.

## What we learned
- **The Feb-2026 attempt exists and failed on prompts alone.** `sam2_segmentor.py` in the
  engine (branch `_annotations`, behind `--sam2-lane`, never in the service image) used a
  fixed centre box and three centre-line points; the memory note records 0 % detection.
  The same model with path points scores under a board on two of three videos.
- **ultralytics reads a flat point list as N one-point prompts.** `points=[[x,y],...]`
  returns N masks and `masks[0]` is the first point's mask. Nest as `points=[[...]]`,
  `labels=[[...]]` for one multi-point object. The 2026-09-12 new-stack report's "5 points"
  was really one point; its numbers still hold because one path point is enough on a clean
  frame.
- **Two of the three engine videos are handheld** (24 px and 36 px of drift over the
  throw; tom_old 3 px). The static `lane_edges` annotation is wrong by 10+ boards at the
  pin end by the end of a throw. sample_input carries per-frame corners; the others do not.
  Truth is now per frame via an ORB+RANSAC similarity model (3.5 px mean vs the hand
  annotation). Chardie's static corners were assumed to belong to the last frame.
- **Chardie's ball is annotated 36 frames past pin contact**, into the pit; prompts and the
  metric now stop at `pin_hit_frame`. **The mask component is chosen by the prompts, not by
  area**: leaked masks span the next lane and the bigger component was the wrong lane (video
  mode on Chardie read 66 boards on every frame until this was fixed).
- **Which frame beats which prompt.** Mid-throw, the bowler occludes the lane on all three
  videos: 6.1 / 31 / 7.2 boards. Last frame: 0.09 / 1.07 / 0.93. Pre-release: 1.42 / 1.13 / 1.12.
- **Space prompt points by image length, not time**, and keep them between 15 % and 85 %
  of the on-lane path: time-even points cluster at the pin end and leak the mask into the
  next lane (Chardie 1 pt 0.39, 5 pts 1.07, 9 pts 3.9 boards). Even spacing: 0.17 / 0.50 / 1.54
  with five points, 0.24 / 0.39 / 1.35 with three.
- **Negatives, boxes and multimask do not help**; per-frame person negatives are harmful
  (catastrophic frames), and outside-mask negatives only help on the tripod video.
- **Cross-frame combination on handheld video is capped by stabilisation (~2 boards at
  the pins)**; gradient snap within 6 px recovers it (median-of-5: 3.33 → 1.97 on
  sample_input).
- **SAM 2 video mode tracks a handheld lane at ~2 boards mean** (sample_input, median ~1)
  from one prompt with no explicit stabilisation. Forward and backward propagation are
  within a board of each other everywhere; Chardie's second half is 1.4 boards and its
  first half 31 to 38, which is the bowler standing in the lane and not a model problem.
  Independent per-frame SAM is no better and costs twice as much.
- **sam2.1_t is as accurate as base at 0.7 s/frame CPU**; large is no better.
- Pin-end floor unchanged: 1 to 2 boards where a board is 1 to 1.7 px.

## Still broken / next steps
- Ground-truth board numbers still do not exist; the metric is relative to hand-clicked
  corners, and Chardie's per-frame truth rests on the last-frame assumption.
- Nothing is wired into the engine. Recommended order in the README: even path prompts →
  clean late frame(s) → video-mode propagation for handheld → gradient snap → tiny weights.
  ultralytics + weights still need adding to `requirements-service.txt`.
- `main` is 7 commits ahead of `origin/main` and none of this is backed up; push it.
- The session scratchpad (frames, weights, per-frame masks, clips) is gone. `review.mp4`
  exists only on this laptop; the README has the regeneration commands (~35 min CPU).
- `make_review_video.py` and `run_methods.py` hard-code the old scratchpad path in
  `SCRATCH`; set `SAM_FRAMES` / `SAM_WEIGHTS` and edit `SCRATCH` before rerunning.

## Verification
- Every number in the README is read from `results/*.json` by `make_review_video.py`
  (which also writes `results/summary.md`); the tables were not typed by hand.
- The camera model was validated against sample_input's hand-annotated per-frame corners
  (3.5 px mean, 11 px max) before being used as truth for the other two videos.
- Overlays for every method/video were rendered and the ones driving conclusions (track
  mid/last/pre, Chardie point-count series, tom_old even/neg) were inspected by eye.
- `review.mp4` was rendered twice at short holds and spot-checked (cards, triptychs,
  tracked clips, summary) before the final render.
