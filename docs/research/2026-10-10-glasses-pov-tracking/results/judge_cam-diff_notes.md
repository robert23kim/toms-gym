# Judge: cam-diff on the holdout (2026-10-10)

**Verdict: works (borderline).** Holdout mean recall 73.0 (dev claim 95.3; baseline yolo_chain_sam 43.9),
board_err <= 3 on 3 of 5 (1.5 / 1.5 / 1.0 / 4.0 / 5.5, mean 2.7). The scorer's own per-stem pass
(recall >= 60 and board <= 3) holds on only 2 of 5 (191253, 191820): 191913 and 192142 fall just under 60 % recall.

## What was run
- `run.py <stem>` with no flags, once per holdout stem, sequentially, engine venv. All 5 rc 0, no path fixes,
  no dev-only files needed. Wall 26-34 s per video (mean 30), with another agent's `sam2-video/run.py` (torch)
  running concurrently the whole time (load avg 2-3.7).
- Fresh tracks equal the experiment's own holdout tracks (frames, lane, boards, final_board; only meta wall_s differs) on all 5: the
  pipeline is deterministic. The experiment's originals are backed up at
  `~/.cache/bowling-pov-holdout-2026-10-10/judge_cam-diff/orig_tracks/`; scores, logs and the miss locator also live there.
- Scored with `L/score_tracks.py` against the holdout truth in `~/.cache/bowling-pov-holdout-2026-10-10/` (not copied into L).
- Dev reproduction: 185454 re-run gives recall 100.0 / px 1.1 / board 0.5 / lane 2.15 / 66.7 s, identical to the
  claim. **Reproduced.**

| holdout stem | recall % | matched/truth | median px | board_err | lane_err boards | window_err [rel, pin] | scorer pass | wall s |
|---|---|---|---|---|---|---|---|---|
| 191253 | 77.4 | 41/53 | 0.9 | 1.5 | 2.15 | [0, 16] | yes | 30.5 |
| 191820 (gutter ball) | 100.0 | 24/24 | 4.3 | 1.5 | 6.23 | [0, 0] | strong | 26.3 |
| 191913 | 56.5 | 13/23 | 2.5 | 1.0 | 22.94 | [1, 21] | no | 29.1 |
| 192142 | 58.8 | 10/17 | 3.7 | 4.0 | 4.27 | [0, 14] | no | 33.9 |
| 192636 | 72.2 | 13/18 | 1.1 | 5.5 | 5.94 | [0, 14] | no | 30.0 |
| mean | 73.0 | | | 2.7 | | | 2/5 | 30 |

## Where the recall goes (frame numbers only)
- **Far end, every stem except the gutter ball.** The track ends 5-15 frames before the truth pin hit
  (track last frame 432 / 494 / 471 / 452), so the last 5-9 truth points (ball at the pins) have no track. On dev the track ran 0-16 frames PAST contact, which is why
  `pin_hit_guess = end - 12` was chosen; on the holdout it stops short. Those 5-9 misses cost 25-45 % of a stem's truth points.
- **Release, 191253 only.** The first 7 truth frames are 106-1023 px from the track
  point: the track starts on the right frame but not on the big near ball. Mid-roll matching is clean
  (median px 0.9-4.3).
- The pin_hit window is 14-21 frames early on 4 of 5, as the experiment itself predicted from the cuts.json
  visual reads (SAM mask top short of the pin bases).

## Board and lane
- The two board misses (192142 4.0, 192636 5.5) are the same numbers as the baseline yolo_chain_sam on those
  stems (4.0, 5.5) with the identical final boards (6.0, 7.0 in results/baseline.json): both read the board on the right-gutter side of truth, both have pin_hit 14 frames early and a
  far-end lane error of 7.6-8.0 boards. That points at the shared SAM lane / board read, not at the cam-diff
  tracker. The tracker's gain over the baseline on the holdout is recall (+29 points) and 191820 (gutter ball:
  the baseline tracked 0 % and SAM refused it; cam-diff 100 % and board 1.5).
- 191913 lane_err 22.9 is one frame: 505 (after the track ended, err 54.8); its mid-roll frames are 11.8 and 2.3.
  The per-frame quad propagated past the track end is unreliable; the board (1.0) is not affected.

## Overlays read (fresh run)
- **192636**: head turned left at pin_hit-4. The cyan quad sits on the bowler's lane (bottom-left of the frame);
  the white path (track warped into this frame) is inside it, runs up the right half and ends near the right
  pin-deck corner. The orange per-frame polyline loops with the head motion as described, and its big yellow
  guided circles near the bottom fall on the next lane only because those points are in their own frames'
  coordinates. On ball and lane: yes. The final board 7 is consistent with a path ending near the right edge,
  but by truth it is 5.5 boards toward the right gutter; the overlay alone could not have told me that.
- **191913**: lane straight ahead; cyan quad on the bowler's lane, white path inside it from near the bottom to
  the deck, with a zigzag at the near end (release frames, where the ORB chain is weakest). Final board 8 matches
  a path ending right of centre at the deck; board_err 1.0.

## Caveats
- Verdict margin: 3 of 5 board_err <= 3 is the minimum; one more board miss would make it partial. Mean recall
  clears 60 by 13 points.
- The 22-point dev-to-holdout recall drop is mostly the `end - 12` / far-end behaviour tuned on dev overshoot
  that did not transfer.
- Holdout truth was read only by the scorer and by a frame-level miss locator in the cache dir; no truth
  coordinates are written in L.
