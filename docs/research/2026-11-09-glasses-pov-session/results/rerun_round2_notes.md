# Rerun round 2: track_v3 pass loop for the judge's round-2 hints (2026-11-09)

Input: `results/judge_all_round2_notes.md` (16 failing stems with hints) + `results/integrate_notes.md`. `global_change = false`:
every change is a per-clip fallback keyed on a condition measured from the track, installed from `track_v3.py` as a wrapper
over the imported `experiments/motion-only/run.py` / L2 `track_v2.py` (neither edited). Round-1 copy of the file:
`work/round2_backup/track_v3.round1.py` (sha 86a42d3466b8f4c3); all 31 round-1 tracks and 61 overlays are in
`work/round2_backup/`. Passing stems were not re-run; every new code path is gated by a condition that is false for them
(table below, "cannot fire on a passing stem" column), so their outputs stay byte-identical.

## The one decision: the 110224 entry hint is NOT applied globally
The hint "read the entry as the board interpolated at the sub-frame headpin-row crossing instead of the 6-point Theil-Sen"
is a redefinition of `entry_board` on every detected crossing. Simulated from the round-1 JSONs (`scratchpad/entry_sim.py`,
no truth read), the crossing entry moves the PASSING stems by: 104946 +0.21, 105857 -0.23, 110442 +0.27, 110948 -0.42,
111238 (truth) -1.50, 111420 (truth) +2.61, 111941 -2.90, 112800 -0.01, 115157 -1.53; pin-motion stems 0. 111420's recorded
`entry_err_pr` is 0.28, so a +2.61 move would most likely flip its T-entry; 110224 itself moves only +0.68 against a recorded
gap of 3.25, so the hint would not rescue 110224 either. The value is therefore written on every re-run stem as
`events.entry_board_crossing` (+ `entry_t_star`, `entry_crossing_how`) for the judge/rule owner, and becomes `entry_board`
only under the measured condition `entry_n < 2` (the 110713 hint). 110224 is re-run so the judge can read the field; its
J1-J5 verdict cannot change from this.

## What changed in track_v3.py (round 2)
The run is now a loop of up to MAX_PASSES = 4 passes; the configuration of pass n+1 is derived from what pass n measured.
A stem whose pass 1 has a detected pin row, an entry inside the lane and a passing J4 statistic runs exactly one pass with
the round-1 code paths (the pass-2 trigger is unchanged: final `pin_row_source` startswith fallback). SAM passes with the
same prompt are cached across passes.

| mechanism | measured trigger | change when it fires | hint | cannot fire on a passing stem because |
|---|---|---|---|---|
| `deck_reseed_sam` (pass 3) | pin row still `fallback` after the pass with SAM to the cut end (relaxed hold also failed) | SAM 2 re-prompted on the last residual point within 6 frames of the track end (else the last real point) in a square crop of 28 x r_geo (128..480 px) upscaled to ~768 px, propagated to the cut end, gated by sam_track.gate and the unchanged radius/lateral gates; its points replace the SAM tail after the prompt frame | J2 class (104714, 105652, 113113, 113716, 113911, 114059, 114438, 114631) | their pin row is a detection |
| pass-2 trigger widened | geometric crossing fell back AND gutter evidence exists, even when pin motion overrode the source | same pass 2 / pass 3 as above | 110622 | needs gutter evidence (none on passers) |
| `pin_row_gutter_crossing` | no held crossing and >= 5 of the last 15 track frames are inside one gutter channel by the per-frame lane-first fit (all real points, not only SAM) | pin row = frame where the ball centre reaches the headpin base row inside the channel, from a line over the last 4 real points vs the base rows, extrapolated <= 3 frames past the track end; source `detected (gutter channel)`, pin motion suppressed | 105322, 112413, 110622 | needs a fallback crossing |
| lane-first channel check over all real points (`events.gutter` evidence c) | only when the crossing fell back / is a gutter crossing, or the entry is None or outside 0.5..39.5 | `events.gutter` from >= 5 real points in one channel within the last 15 track frames | 105322, 112413 | detected pin row and entry inside the lane |
| `deck_gate` (next pass) | the judge's J4 statistic fails on the pass (dead-band sign changes > 1 or jump > 3) AND SAM points at lane-first depth >= 55 ft in the J4 window deviate > 2 boards from the median lane-first board of the last 3 residual points | those SAM points are rejected (`sam_deck_lateral`) in the next pass | 114810 | J4 passes |
| `entry_crossing` | `entry_n < 2` (fewer than 2 cleaned boards in pin_row-6..pin_row-1) | `entry_board` = board interpolated at the sub-frame crossing (bracketing real points), else Theil-Sen over the last 6 cleaned boards before the pin row at t* | 110713 | entry_n >= 2 on every passer |
| `dark_seed` | `find_seed` returns no chained residual seed | dark-disc matched filter (255-gray; disc r_geo minus annulus to 1.6 r_geo >= 35 grey levels, inner darkness >= 100) inside the lane-first lane eroded by the annulus, quarter scale, top 4 per frame; chained by the unchanged find_seed gates; SAM runs from that seed | 115105 | they have a residual seed |
| 114236 | no tracker change (ball out of view f354-366, rule-owner call) | not re-run; round-1 output kept | - | - |

Reading of the hints where a choice was needed: "last real residual detection" is taken as the last residual point within 6
frames of the track end (on 113113 the track is 45 SAM / 7 residual, so the literal last residual point is near the start);
"ball reaching the base row inside the channel" is the centre-y crossing extrapolated at most 3 frames (the standard
`first()` hold is tried first); "within 2 boards of the residual chain" uses the median lane-first board of the last 3
residual points before the SAM point.
