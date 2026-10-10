# Scorer + baseline notes (2026-10-10)

## score_tracks.py semantics
- Denominator: truth `ball` keys in [release, pin_hit] minus `ball_invisible`; truth NOT interpolated
  (185121 is every-3rd-frame, 18 points; 185454 dense, 52 points).
- Track interpolated only between consecutive track frames with gap <= 6; tolerance max(2 * truth r, 20 px).
- lane_err_boards: mean over truth lane_quads frames (fallback lane.ref_frames pin_end_row) of
  |centre offset| + 0.5 * |width error| at the truth pin row, board = truth pin-row width / 39; tracker quad at the
  nearest frame within 3, edges extended pd->fl.

## Mutation check (work/scorer_mutation/, re-read from scorer output)
| stem | variant | recall | median px | board_err | lane_err |
|---|---|---|---|---|---|
| 185454 | truth copy | 100.0 (52/52) | 0.0 | 0.0 | 0.0 |
| 185454 | +100 px x (lane too), board +5 | 15.4 (8/52) | 100.0 | 5.0 | 42.43 |
| 185454 | empty frames, no lane, no board | 0.0 | null | null | null |
| 185454 | every 8th truth frame (gap 8 > 6) | 13.5 (7/52) | 0.0 | 0.0 | 0.0 |
| 185121 | truth copy | 100.0 (18/18) | 0.0 | 0.0 | 0.0 (ref_frames fallback) |
| 185121 | +100 px | 5.6 (1/18) | 100.0 | 5.0 | 44.83 |
| 185121 | empty | 0.0 | null | null | null |
The +100 px residual recall is the near-release points whose truth r is 55-130 px (tolerance 110-260 px): expected.

## score.py
- Input is the cut, so every engine frame is cut-local; converter adds cut_start to trajectory, SAM per_frame keys,
  SAM positions and last_lane_frame. Asserted 0 frames outside [cut_start, cut_end] per row (`frames_outside_cut`).
- SAM per_frame top_* -> pd_*, bottom_* -> fl_* (checked top y < bottom y on 185454). Frames without a calibrated
  quad get the static lane (summary.static_lane, else the `lane_edges={...}` log line). fl_is_foul_line false everywhere.
- release/pin_hit are not engine outputs: yolo_chain.throw when applied, else first/last trajectory frame; pin from
  SAM last_lane_frame when present. window_err is diagnostic only.
- --jobs 2 (as briefed, conflicts with the one-torch-process rule); wall_s measured under 2-way contention.
- 191900 has no cut (no throw in the clip); not run.

## Baseline run
- 40/40 runs rc 0; first scoring pass crashed on holdout truth whose `ball` entries are [x, y, r] lists (191820,
  191913, 192142, 192636) instead of dicts: score_tracks.ball_point() now accepts both (plausibility checked by
  counts only: all entries in-frame with r < x; values not read). Re-scored with --skip-run; mutation results unchanged.
- Results: results/baseline.json, results/baseline_summary.md. Best by dev mean recall: yolo_chain_sam 72.0 %
  (= yolo_chain track), holdout 43.9 %; pass 1/5 dev (190115), 1/5 holdout (191253).
- List-form truth verified: 185454 truth rewritten as [x, y, r] lists (work/scorer_mutation/185454_truth_listform.json)
  scores copy 100.0 / shift100 15.4 / empty 0.0, identical to the dict form.
- 191900 (no cut) is now in baseline.json rows as processed=false, one per config.
- wall_s for yolo_chain_sam 185454 (69.2 s) is from the jobs=1 smoke run (cached); every other row ran under jobs=2.
