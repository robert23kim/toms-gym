# SAM 2 lane detection, loop 2 (resolution, anchors, tracking) — 2026-09-12

## What this was

Asked for a `/loop` of SAM 2 experiments to beat loop 1's lane numbers (0.24 / 0.39 / 1.35 boards on
sample_input / Chardie / tom_old), to be creative about getting more out of the model, and to answer
whether the lane can be anchored the way the fitness (pose-landmark) model anchors. Mid-run: "create a
video similar to last one with the results". Two `creative` agents ran in parallel on the anchor and
tracking questions while the lead ran the resolution track.

## What changed

- New research folder `docs/research/2026-09-12-sam2-lane-experiments-2/`: `README.md` (findings,
  tables, recommendation, retro), `review.mp4` (5.5 min, gitignored, regenerate with the README
  commands), 98 result files in `results/` (loop-1 row schema), curated overlays + diagnostics,
  and the scripts: `common.py` (loop-1 metric/truth via sys.path, `even_points_keep`,
  `frame_for`), `sam2x.py` (`SamImage`: encode once, decode any prompts as float logits),
  `edges.py`, `run2.py` (method registry; `--prompts keep`, `--kinds last,prehit,prehit-6`),
  `run_anchors.py` (agent anchors-1), `run_track.py` (agent track-1), `centre_check2.py`,
  `rescore_pins.py`, `tables.py`, `make_review_video2.py` + `video_cards.json`, `diag_*.py`.
- `CLAUDE.md`: "Bowling Lane via SAM 2" gained a Loop 2 block (prompt bug, encode-once, pins as
  same-row centre ruler, one-rule tracking gate, landmark anchoring, harness notes).
- Memory: `sam2_lane_loop2.md` (+ MEMORY.md line).
- Nothing wired into the engine; no production change.

Numbers that matter (board MAE, sample_input / Chardie / tom_old):

| | last frame | pre-hit frames |
|---|---|---|
| loop 1 headline | 0.24 / 0.39 / 1.35 | not run |
| prompt fix only (`even3_k`) | 0.24 / 0.39 / 1.17 | 0.31 / 0.69 / 2.27 |
| far-end crop (`zoom_lo`) | 0.70 / 0.32 / 0.49 (tiny 0.46 / 0.48 / 0.57) | 0.89 / 0.37 / 1.86 |
| pin-centred far end (`pins_m`) | — | 0.21 / 0.88 / 0.60 (tiny 0.54) |
| landmarks, no ball path | 0.37 / 0.41 / 1.44 | 0.38 / 0.87 / 2.37 |
| tracking per-frame mean, loop 1 → gated | 1.85 / 16.4 / 3.7 → 0.98 / 0.41 / 1.94 | |

## What we learned

- **Loop 1's prompt rule was a bug.** `track_points_even` drops any prompt within 3 ball radii of the
  ball, so any frame with the ball at the far end ran on 2 of 3 prompts. Sliding the point instead
  (`even_points_keep`) is the only change that helps everywhere it applies. A ball detector always
  puts prompts next to the ball, so the engine needs this rule.
- **Resolution: only a crop of the far end helps** (Chardie 0.47 → 0.32, tom_old 1.23 → 0.49).
  Sub-pixel logit edges, 10-prompt ensembles (spread 0.1-0.2), polarity-aware gradient snap, trimmed
  or extrapolated fits, a neighbour-lane vanishing point, imgsz 2048, tiles, gutters as extra SAM
  objects, medians of late frames, k>1 carry and truth-free frame pickers all do nothing or hurt.
- **The pins are a same-row centre ruler, and they sort the residual by video.** At the pin-base
  row the annotation is −0.9 / +2.3 / +1.7 px from the pin cluster centre and SAM is +1.1 / +0.8 /
  **+5.2 px** for every full-frame prompt. sample_input is at the annotation floor, Chardie's
  annotation is two boards off, and tom_old's residual is a real 5 px SAM shift of the far end on its
  standing-pin frames that only re-centring on the pins removes (0.09 against a pin-centred truth).
  The shift shrinks once the pins fall, which is why tom_old's blurred pin-hit frame beat its sharp
  ones in both loops.
- **Compare centres at one row.** The agent's JSON field `pin_centre_err_px` mixes the pin-base row
  with the annotated top row (5.7 rows apart on a lane whose edges slope −1.13 and −0.30 px/row) and
  reads +6.4 on tom_old. My first README draft, plus a 5x crop read by eye, called the tom_old
  annotation four boards off on that basis; the agent's report corrected it and everything was
  re-derived (`centre_check2.py`, `rescore_pins.py`). A number that agrees with what you eyeballed is
  the one to re-derive.
- **SAM's other measurable error is far-end width**: 2-3 % from the annotation at the foul line,
  5-12 % narrow at the deck (the mask stops where the lane darkens toward the gutters); the crop
  halves it. The pins' *extent* is not a width ruler (0.85 / 0.92 / 1.07 of the annotation); pin
  spacing would be. The annotated ball radius is a fixed 25 px marker, so the ball is no ruler either.
- **Tracking is one rule.** Flag frames whose foul-line lane centre is > 3 % of the lane width from
  the throw's median (re-estimated over passing frames), carry the nearest clean lane through the
  camera model. Recall 1.0 on every run; the brief's four other features cannot catch a mask sitting
  on the neighbouring lane (Chardie 34.1 without the centre). Held-out check with fresh tiny
  video-mode masks: 2.05 / 19.6 / 3.51 → 1.04 / 2.29 / 1.75. The ORB camera model's per-frame jitter
  (3.0 px mean at the pins on sample_input) is now the binding constraint: a two-frame carry costs
  2.4 boards, so never gate the frame you quote. Chardie's and tom_old's carry gains are partly
  circular (static truth warped through the same model).
- **Landmark anchoring works.** MediaPipe sliding foot at release (visibility 0.67-0.84; wrists
  0.02-0.23 from behind; no pose at all on sample_input, the YOLO box bottom stood in and still put
  every prompt on the lane) → pin cluster centre finds the lane with no ball path. Ball-free for
  prompting, not yet for timing.
- **Harness.** Subagents cannot write `results/report_*.md` (one used a shell heredoc after the
  refusal; do not brief report files); one inline report was cut at 16 KB, the other never arrived,
  and both came through fine as ≤9 KB chunks on request. `run2.finish` applies `extra` after the
  score, so passing an earlier row through as `extra` silently overwrites `board_mae` and the corners
  (produced one wrong row before it was caught). Every number in the write-up was taken from
  `results/*.json`, not from the agents' prose.

## Still broken / next steps

1. **Ground truth at the far end.** Below one board at the pins the current hand-clicked corners
   measure nothing (Chardie's are two boards off). Annotate the 7-/10-pin bases on a standing-pin
   frame of all three videos and re-score; build a pin-*spacing* width ruler. Blocked on nothing but
   annotation time.
2. **Engine wiring** (none done): keep-n prompts → pre-hit frame → far-end crop → tiny weights →
   re-centre the far end on the pin cluster (measured on the same frame; gate partial racks by pin
   count) → centre-jump gate + carry for handheld tracking; landmark prompts (foot + pins) for a lane
   before the ball track. `sam2_segmentor.py` in the engine is still the Feb-2026 skeleton.
3. **Open questions from the agents:** a release detector so the landmark path is ball-free for
   timing too; whether the centre gate survives a camera that re-frames mid-throw (all three videos
   drift smoothly); why tom_old's pin-hit frame beats every pre-hit frame by ~0.9 boards (the pin
   shift shrinking is the current explanation, unverified on a second lane).
4. `docs/sessions/2026-09-12-cheap-lane-model-loop.md` and the "Cheap Lane Model" CLAUDE.md block
   belong to another session and were left uncommitted here.

## Verification

- Every method's numbers come from `results/*.json` rows written by `run2.py` / `run_anchors.py` /
  `run_track.py`; `tables.py wide` and `centre_check2.py` / `rescore_pins.py` were re-run after the
  agents' corrections and the README tables regenerated from them. The `even3` baseline reproduced
  loop 1's 0.24 / 0.39 / 1.35 exactly before any new method ran.
- Overlays were inspected for every headline number (prompt bug, crop, pins, tracking clips); the
  review video was rendered three times and checked by contact sheet after each set of card edits.
- Not verified: nothing was run in the engine or in production; the tracking agent's
  `results/report_track.md` exists on disk but was not used as a source; the agents' latency figures
  are indicative only (three SAM processes shared one CPU).
