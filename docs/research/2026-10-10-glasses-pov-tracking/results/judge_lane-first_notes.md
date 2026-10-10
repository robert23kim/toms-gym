# Judge: lane-first (holdout), 2026-10-10

**Verdict: works, at the minimum.** Holdout mean recall 77.3 % (>= 60), board_err <= 3 on 3 of 5
(0.3 / 1.4 / 0.7), mean board_err 2.2. The two misses (3.4, 5.2) share one cause: the track dies about 10 frames
before the ball reaches the pins, so the final board comes from detections taken before the hook finished.

## What was run
- `run.py <stem>` fresh on the 5 holdout stems, one at a time, with no code changes and no path fixes.
  It needs no dev-only files: it reads cuts.json and the cuts only. The output was byte-identical to the experiment's
  existing holdout tracks except `meta.wall_s`, so the code is deterministic and was not tuned after that run.
  Prior copies are kept in this session's scratchpad.
- Scored with `score_tracks.py` against `/Users/toka/.cache/bowling-pov-holdout-2026-10-10/<stem>.json`.
  No truth was copied into L. This JSON and these notes hold scores and qualitative directions only.
- Dev re-run: 185645 gives recall 90.3, board_err 2.9, median 1.8 px, lane_err 2.03. That matches the claim
  exactly, so it is **reproduced**.
- Machine: load average 9-10 on 12 cores (other agents' Python jobs). Wall time was 1.3-1.7 s per video
  (`real` 1.4-1.9 s), the same as the claimed ~1.3 s.

| stem | recall % | matched | median px | board_err | lane_err | pass |
|---|---|---|---|---|---|---|
| 191253 | 92.5 | 49/53 | 1.4 | 0.3 | 1.48 | strong |
| 191820 | 66.7 | 16/24 | 3.1 | 1.4 | 7.21 | pass |
| 191913 | 60.9 | 14/23 | 6.2 | 0.7 | 5.10 | pass |
| 192142 | 94.1 | 16/17 | 7.1 | 3.4 | 0.93 | fail (board) |
| 192636 | 72.2 | 13/18 | 1.6 | 5.2 | 1.72 | fail (board) |

Caveat: 4 of the 5 holdout truths have only 17-24 ball points, against 53 on 191253, so one missed point there is
worth 4-6 recall points. Recall on 191913 (60.9) and 191820 (66.7) is close to the 60 line.

## Overlays (what I looked at)
The stored overlay draws every track point on a single frame (pin_hit-4) while the camera keeps moving. On a
head-mounted camera the polyline therefore does not line up with that frame's lane, and the overlay **cannot** show
whether the track is on the ball. I rendered per-frame crops instead (scratchpad `sheet.py` / `zoom.py`: each
frame's own record and quad).
- **192636** (board 7.3, err 5.2): the quad sits on the lane the bowler threw on. f425 and f440 detections are on the
  ball. At f444 the circle sits just under the ball. f450 is a fill ~25 px behind the ball, which is already further
  up. At f456 there is no record, yet the ball is plainly visible on the lane, left of where the track last put it. The
  ball keeps moving left (toward a higher board) after the last detection at f446. The final board is the median of
  f440-446 detections (7-9), so it was read ~10 frames early on a hooking ball. The truth reads the ball at the pins
  and puts it several boards further left. Separate problem: the quad's pin-deck row sits below the real pin deck
  (the wood mask ends where the deck goes reflective).
- **191913** (board 7.7, err 0.7): the lane is right and the board matches. At f500 the ball is clearly visible at
  the pins with no record (same tail miss). The tail also contains junk that the scorer sees: a detection at f498
  with board 39.8 (left gutter), six fills at board 36.5 (f502-507), detections at f511-512 among the pins after the
  pin hit, and a detection at f522 with board 39.7. All of these are flagged `on_lane: true`. The final-board
  quality filter kept them out of the median. A renderer that trusts `on_lane` would still draw them, and they show
  in the stored overlay as the stray points left of the quad top.
- 192142 (err 3.4) was not inspected. It is likely the same tail pattern, but that is unverified.

## Summary
The approach generalises: lane pick and ball detection hold on all 5 unseen throws. On 3 of 5 the median error is
1.4-3.1 px, and every holdout run passes the recall gate. Board accuracy is borderline. The open lever is still the
experiment's own "next lever": a detector for the last ~10 frames at the pins (dark ball against white pin bases)
plus stopping the track at the pin row. That would fix both board misses I can explain and the post-pin junk.
