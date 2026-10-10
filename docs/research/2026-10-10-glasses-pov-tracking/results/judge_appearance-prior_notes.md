# Judge: appearance-prior (fixed hue + motion peak + SAM lane), holdout, 2026-10-10

**Verdict: partial.** Tracking generalises: holdout mean recall 98.8 % (95.7-100 on all 5 stems, median error
3.5-4.8 px). The board read is the weak part. It is within 3 boards on only 2 of 5 stems, so the result misses
`works`. In every board miss the lane step (SAM) is at fault, not the ball track.

## How it was run
- I ran `run.py <stem>` fresh, one at a time, from `experiments/appearance-prior/` with the engine venv python. No code
  changes or path fixes were needed. Exit 0 on all 5. run.py ran the YOLO+ORB cache scan itself (7-10 s per stem).
- Scored with `score_tracks.py` against `/Users/toka/.cache/bowling-pov-holdout-2026-10-10/<stem>.json`. The truth
  was not copied into L. Logs, scores and check images are in
  `/Users/toka/.cache/bowling-pov-holdout-2026-10-10/judge_appearance-prior/`.
- The machine was loaded. At the start, other agents' run.py jobs (cam-diff, detector-tiling, sam2-video) were
  running, and load average was 4-9 on 12 cores during the runs. Wall times are `time -p` real values under that load.
- Declared input: run.py prompts SAM with cuts.json `pin_hit_frame`, a hand-labelled visual frame, and the cut bounds
  encode release. That holds for the holdout cuts too. So this is not an end-to-end pipeline: the pin hit comes from a
  person.

## Holdout
| stem | recall % | median px | final board | board_err | lane_err | window_err | pass | wall s |
|---|---|---|---|---|---|---|---|---|
| 191253 | 98.1 (52/53) | 3.7 | 5.0 | 1.5 | 2.78 | [1, 9] | strong | 51.6 |
| 191820 | 100 (24/24) | 3.9 | 1.0 (raw -3.7) | 1.5 | 6.62 | [2, 1] | strong | 71.0 |
| 191913 | 95.7 (22/23) | 4.8 | 1.0 | 6.0 | 7.25 | [0, 17] | no | 142.2 |
| 192142 | 100 (17/17) | 4.7 | 6.0 | 4.0 | 2.64 | [1, 11] | no | 51.3 |
| 192636 | 100 (18/18) | 3.5 | null (SAM refused) | null | null | [0, 0]* | no | 133.8 |
| **mean** | **98.8** | | | 3.25 over 4; <= 3 on 2/5 | | | 2/5 | 90.0 |

\* When SAM refuses, `pin_hit_frame` is the cuts.json value echoed back, so window_err [0,0] does not measure the tracker.
Dev claim: 97.5 % recall, boards 0.5/1.5/1.5 over 3 of 5. On holdout, recall held and the board did not: 2 of 5
within 3, and SAM refused 1 of 5 (2 of 5 on dev).

## Dev reproduction
I re-ran 185331 after backing up the experiment's track. The fresh track was identical: same frames and lane, and the
same score (recall 93.3, median 3.2, board_err 0.5, lane_err 0.21) as claimed. Wall time was 61.5 s. **Reproduced.**
I then restored the original file.

## Overlays and frames I read
The overlay .jpg draws every track point in raw image coordinates on the pin_hit-4 frame, and the head moves. So the
polyline does not lie on the lane in that frame (on 191913 it curls up into the backdrop). To check the track, I
re-drew the track point and the SAM quad on their own frames (`frames/191913*.jpg`, `frames/191820.jpg`).
- **191913 (board_err 6.0)**: the red circle is on the purple ball at 460, 485, 488, 492, 500, 505 and 509, all the way
  into the rack. The quad is the lane the bowler threw on. Its far edge stops about 40-50 px short of the pin deck
  (SAM's own gates logged "mask top ... 41-50 px short of the path's far end" on 5 candidates). SAM's
  last_lane_frame is 492, 17 frames before the 509 pin hit. At 492 the ball sits on the quad's right edge, which
  gives raw board 0.52 -> 1.0. On the 505-509 crops the ball is among the right-centre pins of the rack, not at the
  right gutter. So the final board does **not** match what I see; the truth error of 6 fits that.
- **191820 (right gutter ball, board_err 1.5)**: the track is on the ball at 430, on the right side of the centre lane.
  At 448-463 it rides the right edge into the gutter, which matches the cuts note "RIGHT GUTTER BALL". A purple
  neighbour ball rolls on the lane to the left (visible at 448 and 458), and this tracker did not take it. That is
  the stem where the wildcard experiment locked onto the neighbour and scored 0 %. The final board of 1.0, clamped
  from raw -3.7, matches a gutter ball. The quad is on the right lane but is 3-4.6 boards off-centre (lane_err 6.6).
- After the pin hit, the track runs to the cut end and makes false jumps when the camera whips away (on 191820,
  the excursion to the top left of the overlay). Trim at pin_hit for the showcase, as the notes say.

## Caveats
- 5 videos. If one board read moved under 3 (192142 at 4.0), the verdict would flip to `works`.
- 191820's pass rests on a clamp. The raw board is -3.7, the lane centre is 3-4.6 boards off, and the scorer counts
  the clamped value.
- Per-frame `boards` are empty in every track. Only `final_board` is written.
