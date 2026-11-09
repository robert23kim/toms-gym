# Rerun round 1: track_v3 fallbacks for the judge's hints (2026-11-09)

Input: `results/judge_all_round1_notes.md` + `judged_round1.json` as issued 12:28 (19 stems failing; 7 marked NO RERUN as
rule-owner decisions; that file is now `work/judge_r1b/judged_round1.before_rejudge.json`, the current `judged_round1.json`
was re-issued ~14:00 on the rerun outputs). Rerun candidates: the 12 stems with a tracker hint. `global_change = false`:
every change is a per-clip fallback keyed on a condition measured from the track, installed from `track_v3.py` as a wrapper
over the imported `experiments/motion-only/run.py` / L2 `track_v2.py` (neither file edited). The 10 non-rerun stems were
not re-run; their `results/tracks` JSONs and overlays are byte-identical to round 1 (backup of all 22 in `work/round1_backup/`).

This file was written in two passes: the rerun agent (13:27, mechanism, batch, check) and the verification pass (13:50:
check re-run, hint-answered column, amended-rule column, the 9 skipped clips). The 13:27 text is kept as
`work/rerun_r1/rerun_round1_notes.13-27.md`. No tracker was run in the second pass.

## What changed in track_v3.py (sha256 prefix of the round-1 file 4eba95aa823e59ae, see `meta.track_v3.track_v3_sha256_16` for the new one)

| fallback | measured trigger | change when it fires | hint it answers |
|---|---|---|---|
| `far_seed` | the unfiltered seed is < release+20 frames and at depth >= 55 ft (lane-first `lf.depth`, 60 ft at the pin-deck row; 55 = within a pin-column height of the headpin base row) | candidates at that depth in that window are dropped and the seed search re-runs | 105857 (seed on a static deck blob) |
| `pin_row_pass2` | pass 1 `events.pin_row_source` starts with `fallback` | the whole pipeline runs again with the SAM forward pass to the cut end (`MO.SAM_TAIL` lifted from cut pin_hit+12) | the 8 J2 stems: "widen the crossing window to cut_end before falling back" |
| `pin_row_relaxed_hold` | still fallback after the SAM pass to the cut end, and 3 consecutive real points sit at/above the headpin base row | the pin row is that first point (`pin_row_source` = `detected (relaxed hold): ...`, counted as geometric downstream) | same 8 stems; see "what the window was not" below |
| `late_jump_reclean` | the judge's own J4 statistic (5-frame median of `boards`, 15 ft..pin row) has a jump > 3 boards | `clean_series` re-runs with the jump rule at 3 boards (+1 per skipped frame) walked from the 4th roll frame instead of 6 boards from cut pin_hit-2; `add_depth` re-runs | 113541, 114919 |
| gutter channel + `events.gutter` | (a) in `merge_sam`, neighbour and SAM candidate both inside one gutter channel (board in -9..0.5 or 39.5..48.5 by the per-frame lane-first fit); (b) median of the last 10 cleaned roll boards before the pin row outside 0.5..39.5, or >= 5 SAM points kept inside one channel within the last 15 frames of the track | (a) the lateral gate is waived for that point; (b) `events.gutter = {side, evidence, late_median, frames, n, rule}`; a pin-motion pin row is not used over a detected geometric crossing while (b) holds | 110622, 112413 |

Trigger check on the 22 round-1 JSONs (`work/rerun_r1/verify_triggers.py`, the same functions `far_seed`, `med5_max_jump`,
`gutter_state` imported from track_v3): fires on 104714, 105857 (far_seed + late jump 15.24), 112413, 113541 (4.06 at
f610), 113716, 114059, 114438, 114631, 114810, 114919 (5.29 at f681), 115157 and on none of the 10 non-rerun stems (their
max med5 jumps are 0.77-2.79, seeds 9.9-28.3 ft, late medians inside the lane). 110622 fires nothing on the round-1
JSON (late median 0.9, not < 0.5; the channel evidence needs the ball-stage lane fit, so only a run shows it). The
`merge_sam` channel clause is the one wrapper that runs unconditionally; it can only waive a `sam_lateral` rejection
whose neighbour and candidate are both in a gutter channel by the lane-first fit: 6 of the 10 non-rerun stems had
`sam_lateral = 0` in round 1, the other four (110442: 2, 111420: 1, 111941: 3, 112936: 0 lateral but min board 0.0)
have cleaned boards >= 3.5 except 112936, so the clause is very unlikely to have changed them, but this is not proven
by a run.

## What the "crossing window" was not
`pin_row_estimate` already walks every ball point and `pin_motion` already searches to the cut end, so the window was
never capped at the cut pin_hit. The diag over the 8 fallback stems (`work/rerun_r1/diag.py`): the ball track ends 11-22
frames after the cut pin_hit (SAM dies at the deck: mask area/jump gate, max 3 crop passes), and either the ball is
still below the headpin base row when the track ends (104714: +13.5 px at f372, 112413, 113716, 114059, 114438,
114631) or it crosses with only 1-2 real frames after (114810 at f672, 115157 at f570), which fails `first()`'s ">= 3
real frames after". Pass 2 (SAM to the cut end) was tried first as the hint asks; on 115157 it changed nothing
(SAM died at k85 in both passes), so the relaxed hold is the fallback that actually detects. Pass-1 tracks of the
pass-2 stems are kept as `work/v3/tracks/<stem>.pass1.json`.

## Batches (both finished, neither re-run)
- `S/rerun_r1.sh` (12 stems in `work/rerun_r1/stems.txt`): detached 13:01:27, `work/rerun_r1.done` 13:26:17 =
  `{"n": 12, "failed_stems": [], "wall_s": 1490}`; 57-197 s per stem (the 8 pass-2 stems run the whole pipeline twice).
- `S/run_missing.sh` (the 9 stems the first batch skipped): started 13:26:18 after `rerun_r1.done`, `work/run_missing.done`
  13:40:50 = `{"n": 9, "failed_stems": [], "wall_s": 872}`; 7-156 s per stem.
- All 21 outputs carry `meta.track_v3.track_v3_sha256_16 = 86a42d3466b8f4c3` (= the file as it is now) and
  `round = rerun_round1`. All 31 expected `results/tracks/<stem>.json` exist (the 22 + the 9; 111218 has no throw and
  no track). The 10 non-rerun stems: 10/10 JSON + final overlay shasums equal the round-1 backup. Overlays: `final__` +
  `picture__` for every stem except 115105, which has only `final__` (0 ball points, nothing to picture).
- Audit log for the first rerun stem: `work/v3/audit_open_rerun_r1_20261108_104714_593f3a1d.tsv`.

Driver finding: the "one torch process" wait loop in run_all.sh / rerun_r1.sh never fires. `ps` shows the venv
interpreter as `/opt/homebrew/Cellar/python@3.13/.../Python -I .../track_v3.py <stem>`, not
`analysis-engine/.venv/bin/python`, so the match string is dead; that is also why round 1 logged no waits. The batch
overlapped another track_v3 run for ~2 min at 13:01 (reported to main). Fix for the next copy: match on
`track_v3.py|motion-only/run.py` in the ps command, excluding the driver's own pid tree. Not edited while running.

## Own J1-J5 check on the 12 rerun stems (`work/rerun_r1/check_rerun.py`, re-run 13:49; `check.json`)
`judge()` from `work/judge_r1/judge_rules.py` unchanged, on the rerun JSON and on the round-1 backup. Two readings per
stem: **as written** = `rules_failed_auto` (J4 counts every sign change); **amended** = RULES.md as it stands since the
12:50 amendment (J4 passes when `J4_pass_deadband1`, which is "<= 1 sign change with the 1-board dead band and max
jump <= 3"). The hint is the one in the 12:28 `judged_round1`; "answered" = yes (fired, the targeted rule flipped),
partial (fired, the targeted number moved, rule still fails), no (did not fire, or fired and changed nothing).

| stem | hint (12:28) | fired | as written: round 1 -> after | amended after | pin row | entry | J1 % | J4 max jump / raw sign changes (dead-band pass) | hint answered |
|---|---|---|---|---|---|---|---|---|---|
| 104714 T | widen the crossing window to cut_end | pin_row_pass2 | J2 J4 -> **J2 J4** | **J2** | 350 fb -> 350 fb | 16.87 | 100 | 1.24 / 2 (yes) | no: pass 2 added 10 points (62 -> 72, ends f382, 2.0 px below the base row), still no held crossing |
| 105857 | reject seeds at/above the headpin row within release+20 | far_seed | J1 J4 -> **pass** | **pass** | 437 -> 499 geometric | 37.34 -> 15.65 | 50.0 -> 98.5 | 15.24 -> 1.17 / 1 | yes |
| 110622 | follow the ball into the gutter channel, emit a gutter flag | none (gutter flag right, `evidence: ball-stage lane-first channel`, late median 0.78) | J1 J3 J4 -> **J1 J3 J4** | **J1 J3 J4** | 483 pin motion | None | 52.3 -> 53.2 | 2.46 / 2 (no) | partial: the flag is emitted; the chain still ends at f437 and the judge's J3 code has no gutter clause |
| 112413 | widen the window into the gutter channel, flag gutter when late series < 0.5 | pin_row_pass2 | J2 J3 J4 -> **J2 J3 J4** | **J2 J3** | 371 fb | -0.74 | 96.5 | 1.14 / 5 (yes) | no: SAM dies at f380 in both passes; cleaned late boards inside the lane, so no flag (entry -0.74 is the Theil-Sen extrapolation) |
| 113541 | 3-board clean_series jump rule over the whole roll | late_jump_reclean | J4 -> **J4** | **pass** | 614 pin motion | 24.77 -> 14.8 | 95.8 | 4.06 -> 1.09 / 3 (yes) | yes on the jump (amended pass); the 3 raw sign changes are the NO RERUN jitter class |
| 113716 T | widen the crossing window to cut_end | pin_row_pass2 | J2 -> **J2** | **J2** | 544 fb | 11.7 | 98.3 | 1.1 / 1 | no: no points added, SAM dies at the deck in both passes |
| 114059 | widen the crossing window to cut_end | pin_row_pass2 | J2 J4 -> **J2 J4** | **J2** | 614 fb | 13.22 | 98.2 | 1.33 / 3 (yes) | no: the full pass lives to the cut end but every later mask fails the merge radius band |
| 114438 | widen the crossing window to cut_end | pin_row_pass2 | J2 J4 -> **J2 J4** | **J2** | 584 fb | 14.22 | 100 | 1.17 / 5 (yes) | no: no points added |
| 114631 | widen the crossing window to cut_end (recheck J4 with the dead band) | pin_row_pass2 | J2 J4 -> **J2 J4** | **J2 J4** (see note) | 578 fb | 14.58 | 98.2 | 1.02 / 5 (no: 3 with the shared code's `>= 1` band) | no: no points added |
| 114810 | widen the crossing window to cut_end | pin_row_pass2 + late_jump_reclean | J2 -> **J4** | **J4** | 661 fb -> 672 geometric (standard rule) | 9.0 -> 1.41 | 98.2 -> 97.0 | 1.23 -> 1.65 / 1 -> 3 (no) | partial: J2 now passes (3 points added, 73 -> 76); the deck points f661-674 that make the new J4 failure are the ones the re-issued judge wants gated to the residual chain |
| 114919 | 3-board clean_series jump rule over the whole roll | late_jump_reclean | J4 -> **J4** | **pass** | 684 pin motion | 22.67 -> 15.42 | 100 | 5.29 -> 1.07 / 3 (yes) | yes on the jump (amended pass); 3 raw sign changes = jitter class |
| 115157 | widen the crossing window to cut_end | pin_row_pass2 + pin_row_relaxed_hold | J2 J4 -> **J4** | **pass** | 561 fb -> 570 `detected (relaxed hold)` | 4.41 -> 10.91 | 98.3 -> 98.5 | 1.91 -> 2.95 / 4 -> 5 (yes) | yes, conditional: J2 passes only through the relaxed hold (rule owner's call; J6 cannot confirm the deck points) |

As written: 1 of 12 passes (105857). Amended: 4 of 12 pass (105857, 113541, 114919, 115157), 8 still fail: 104714,
110622, 112413, 113716, 114059, 114438, 114631, 114810. That is the re-issued judge's round-1 table for these stems.
J5 is 100 on all 12 before and after. Hint answered: yes 2 (105857, 115157 conditional), partial 2 (110622, 114810),
yes-on-the-jump 2 (113541, 114919), no 6 (the J2 stems where pass 2 added nothing or not enough).

114631 note: RULES.md says a dead-band move must *exceed* 1 board; `judge_rules.sign_changes` tests `>= dead` (line 22-28,
`DEAD = 1.0`). The median series 16.59 -> 14.21 -> 15.52 -> 14.52 -> 15.86 has one leg of exactly 1.00 board, so the
shared code counts 3 sign changes and the strict reading 1. Verdict unchanged either way (J2 fails). Not changed here;
the judge stage owns the rule code.

The judge's J3 has no gutter clause in code: 110622 fails J3 with `events.gutter.side = right` present (the 12:28 judge's
frame read agreed it is a gutter; the re-issued judge could not confirm it, camera tilted up), 112413 fails J3 with no flag.

### Still failing, by class
(a) **Jitter only, the class the judge marked NO RERUN / rule-owner** (max med5 jump <= 3, > 1 raw sign change):
113541, 114919 (both jumps gone; 3 sign changes, pass with the 1-board dead band), 115157 (J2 now passes only
through `detected (relaxed hold)`: rule owner's call whether that counts as a detection; 5 sign changes, dead-band
pass), 114810 (J2 passes by the standard geometric rule after pass 2; 3 sign changes that survive the dead band, entry
1.41 after the re-clean rejected f661-664/668 at 3 boards: the deck series is noisy on this stem).
(b) **Tracker failure**: 110622. The ball is in the right gutter from ~f415 (13 SAM points inside the channel by the
lane-first fit, boards -4.75..0.48; the composition lane reads it at ~0.4-1.4 because its right edge fit sits on the
gutter lip, late median 0.78, so the hint's "< 0.5" rule did not fire and the flag carries `evidence: ball-stage
lane-first channel`). The ball reaches the deck at f437, 4 px below the headpin base row, and the SAM mask then drifts
left into the pit (boards 10-15 at k78-81, rejected by the lateral gate, which is right). No geometric crossing
exists, so the pin-motion frame f485 (the pit, not pins) stands and J1 is 53 %. Next step for this stem is a gutter
pin row (ball passing the pd row in the channel), not a tracker change.
(c) **Fallback still fallback after the SAM pass to the cut end**: 104714 T, 112413, 113716 T, 114059, 114438,
114631. Measured cause (`work/rerun_r1/check.json` + the tail of `base_rows`): pass 2 added points only on 104714
(62 -> 72, track now ends f382 with the ball 2.0 px below the base row; truth pin row 384, so it stops two frames short)
and 114810 (73 -> 76, which resolved it). On the other five the SAM forward pass dies at the deck in both passes
(sam_track's area/jump gate, three crop passes exhausted; 114059's full pass lives to the cut end but every later mask
fails the merge radius band), so the track ends 8-15 frames after the cut pin_hit with the ball still 12-24 px below the
headpin base row (112413 1.4 px at f380 with nothing after). Neither the window nor the hold rule is the limiter there;
the ball is lost 1-3 ft before the pins. On 112413 the entry -0.74 is the Theil-Sen extrapolation; the cleaned late
boards are inside the lane, so no gutter flag. The re-issued judge's hint for this class (re-seed SAM from the last
real residual detection with one more crop pass, hold the crossing on 3 real frames) is a round-2 change, not done here.

### What the global form would have done (for the rule owner)
`work/rerun_r1/sim_jump.py` over the 22 round-1 JSONs: the whole-roll 3-board jump rule (the hint as written) changes
the series on 14/22 stems, including passing 110442 (f411 rejected) and NO RERUN 110948, 111420, 111631, 112936; on
111631 it raises the max med5 jump from 0.77 to 5.61 (the re-clean opens a gap right at the pin row and the judge's
index-based median then spans it). That is why the re-clean is conditional on the measured jump; choosing the global
route means re-running all 22 and re-judging.

## The 9 clips the first batch skipped (`work/rerun_r1/check_missing.py`, same `judge()`; `check_missing.json`)
Tracked once by `run_missing.sh` with the same track_v3.py (sha 86a42d34…), so the fallbacks were live on their first
and only run; there is no round-1 baseline for them. RULES.md (12:50 amendment) keeps them out of the round-1 counts and
the judge stage owns their verdict; these are the same rules run by the same function, reported, not judged. No hint
exists for them yet.

| stem | fired | points | pin row (source) | entry | J1 % | J4 max jump / raw sign changes (dead-band pass) | J5 % | J1-J5 as written | amended |
|---|---|---|---|---|---|---|---|---|---|
| 105322 | pin_row_pass2 | 61 | 445 fallback (cut pin_hit) | -1.87 | 90.2 | 2.51 / 0 (yes) | 100 | J2 J3 | **J2 J3** |
| 105652 | pin_row_pass2 + late_jump_reclean | 68 | 375 fallback | 17.64 | 98.3 | 2.70 / 1 (yes) | 100 | J2 | **J2** |
| 110713 | pin_row_pass2 + late_jump_reclean | 91 | 400 geometric (pass 2; pass 1 fell back at 388) | None (`entry_n` 1) | 98.6 | 1.17 / 5 (yes) | 100 | J3 J4 | **J3** |
| 112146 | none | 76 | 401 pin motion | 20.24 | 100 | 1.17 / 3 (yes) | 100 | J4 | **pass** |
| 112800 | none | 82 | 320 geometric | 16.16 | 100 | 1.12 / 3 (yes) | 100 | J4 | **pass** |
| 113113 | pin_row_pass2 | 52 | 356 fallback | 9.61 | 92.2 | 0.30 / 5 (yes) | 100 | J2 J4 | **J2** |
| 113911 | pin_row_pass2 + late_jump_reclean | 61 | 518 fallback | 18.08 | 98.2 | 0.95 / 3 (yes) | 100 | J2 J4 | **J2** |
| 114236 | none | 56 | 417 geometric | 6.73 | 79.7 | 1.13 / 1 (yes) | 100 | J1 | **J1** |
| 115105 | none | 0 | 595 pin motion | None | 0.0 | none | 0.0 | J1 J3 J4 J5 | **J1 J3 J4 J5** |

As written 0 of 9 pass; amended 2 of 9 pass (112146, 112800), 7 fail. Facts per failing stem, from the JSONs only:
- 105322: SAM dies at f440 with the cut pin_hit at 445, so pass 2 added nothing held; one SAM point sits in the right
  channel (`sam_channel_points` k70 f440 board_lf -0.74) but not the >= 5 the gutter flag needs, so entry -1.87 fails
  J3 with no flag. Same shape as 112413.
- 105652, 113113, 113911: last real point 1-4 frames before the cut pin_hit (371/375, 352/356, 517/518), SAM dies at
  the deck in both passes; class (c) above.
- 110713: the one skipped stem where pass 2 produced a geometric pin row (388 fallback -> 400 detected), but
  `entry_board` is None with `entry_n` 1 (one deck point; `final_board` 6.7, last real board 9.54 at f393), so J3 fails
  on a missing entry, not an out-of-lane one. The re-issued judge's 110224 hint (entry read at the sub-frame base-row
  crossing) is the matching change.
- 114236: track is continuous (56 real points f367..f422, no gaps) but starts late; J1 79.7 means ~14 of the frames
  from release+5 were never seeded. A seed problem, not a far-end one; `far_seed` did not fire (it only drops deck-depth
  seeds).
- 115105: 0 ball points. Detection window [562, 595], `real_in_window` 0; the ball stage found no seed at all, pin row
  is pin motion f597-2. Nothing downstream could apply; the clip needs its cut and ball appearance looked at before any
  fallback is relevant. Only a `final__` overlay exists for it.

## Quarantine
Not opened in either pass. The audit hook refused nothing (no open of pov-holdout, truth or label paths in
`work/v3/audit_open_rerun_r1_20261108_104714_593f3a1d.tsv`); truth numbers in this file are copied from the judge's
notes (104714 truth pin row 384, 113716 +14), not re-read. `check_missing.py` reads only `results/tracks`.

## Files
- `track_v3.py` (round-1 copy `work/round1_backup/track_v3.round1.py`), `rerun_r1.sh`, `run_missing.sh`, `work/rerun_r1.log`,
  `work/rerun_r1.done`, `work/run_missing.log`, `work/run_missing.done`
- `results/tracks/<12 stems>.json` overwritten, `<9 stems>.json` new; `overlays/final__*.jpg`, `overlays/picture__*.jpg`;
  pass-1 tracks `work/v3/tracks/<stem>.pass1.json` for the pass-2 stems
- `work/rerun_r1/`: `check_rerun.py`, `check.json`, `check_run.out`, `check_missing.py`, `check_missing.json`, `stems.txt`,
  `verify_triggers.py`, `diag.py`, `diag2.py`, `sim_jump.py`, `notes_head.md`, `rerun_round1_notes.13-27.md`
- `work/round1_backup/`: all 22 round-1 tracks and 44 overlays
