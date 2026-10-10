# Judge: sam2-video on the holdout (2026-10-10)

**Verdict: works** (mean recall 90.5 %, board_err <= 3 on 3 of 5). The rule is met, but the margin is thin:
only 2 of 5 stems pass the per-stem gate, and one of the 3 good boards is luck (191913, below).

## What I ran
- `run.py <stem>` fresh on all 5 holdout stems, sequentially, MPS, Bash timeout 600 s. No crash, no dev-only
  file read (run.py reads only cuts.json, the cut and the engine worktree). No edits.
- Scored each with `score_tracks.py` against `~/.cache/bowling-pov-holdout-2026-10-10/<stem>.json`
  (logs in `results/judge_sam2-video/logs/`; per-frame lane errors only, no truth coordinates).
- Re-ran dev 185454: 100.0 % / board_err 0.5, same as claimed. Wall 69.3 s against the claimed 77.6 s. **Reproduced.**
- The fresh holdout tracks are identical (0.0 px, same boards) to the ones the experiment had already
  written for its showcase. So the pipeline is deterministic, and the showcase shows exactly what was scored.
- Machine: load average 1.6-3.7, no other torch job seen. Walls are close to unloaded.

## Holdout table
| stem | recall | median px | board_err (final) | lane_err | wall s | gate |
|---|---|---|---|---|---|---|
| 191253 | 100.0 (53/53) | 1.9 | 0.5 (6.0) | 2.44 | 78.8 | strong |
| 191820 | 95.8 (23/24) | 4.2 | 1.5 (1.0, gutter) | 6.25 | 62.0 | strong |
| 191913 | 56.5 (13/23) | 2.8 | 0.0 (7.0) | 4.88 | 96.5 | fail (recall) |
| 192142 | 100.0 (17/17) | 2.7 | 5.0 (5.0) | 2.74 | 87.9 | fail (board) |
| 192636 | 100.0 (18/18) | 7.7 | 5.5 (7.0) | 2.67 | 223.6 | fail (board) |
| mean | 90.5 | 3.9 | 2.5 | 3.80 | 109.8 | 2/5 pass |

## Overlays (read the official overlays, then made per-frame zoom sheets `judge_sam2-video/sheet_<stem>.jpg`)
The official overlay draws every frame's point on one frame. The glasses pan, so the polyline does not land on
the lane in that frame: on 192636 it appears to cross the right gutter. That overlay cannot tell you whether the
track is on the ball. The per-frame sheets show the tracker circle on that frame:
- **191913**: on the ball through f491. From f493 to the end (f509) the circle sits on a dark object in the
  right gutter/kickback, while the purple ball is plainly visible 26-41 px to its left, inside the lane.
  The crop re-prompt (seeded at f495) locked onto the wrong object. This is where all 9 far-end misses come from.
  The per-frame board goes negative (gutter) from f493. The final board 7.0 still matches only because the
  engine's last_lane_frame is f492, one frame before the drift.
- **192636**: the circle is on the ball in every frame from f425 to f457. The quad is on the bowler's lane,
  but its pin-deck edge stops well short of the ball's far positions. The board reads 7.0 and the truth is
  further left (err 5.5): the error is in the lane calibration, not the track.
- **192142**: the circle is on the ball throughout. The quad's right edge runs through the ball at f430-f440,
  but the real wood-to-gutter edge is clearly further right. The quad is too narrow on the right side, so the
  ball reads too close to the right gutter: 5.0, truth further left (err 5.0).

## What this says about the claim
- The ball tracking claim holds on the holdout: SAM 2 forward propagation from one chained-blob prompt at
  release+3, plus the backward pass, recalls 100 % on 4 of 5 stems with a median of 1.9-7.7 px. The prompter
  found a blob at release+3 on all 5 stems.
- The weak point is the crop re-prompt when the full-frame mask dies near the pins. It can lock onto a dark
  gutter or kickback blob (191913), and the 4r+40 jump gate cannot catch a 30-40 px offset at r 7-10.
  A colour or purple check on the re-prompted mask would probably have rejected it.
- Board accuracy is limited by the engine SAM lane pass. Its lane width error is 2.3-6.5 boards per frame on
  the holdout, and the two 5-board misses both come from the quad, both reading too far right.
- Wall time: mean 109.8 s, but 192636 took 223.6 s (lane pass 181 s), as the experiment said it would.
