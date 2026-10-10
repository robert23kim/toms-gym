# Judge: detector-tiling on the holdout (2026-10-10)

**Verdict: works** (by the brief's rule, with one board short of failing it): holdout mean recall **78.6 %**, board_err <= 3 on **3 of 5** (0.5 / 2.0 / 1.0); 191820 has no board (lane refused) and 192636 is 5.5 boards off.

## What was run
- `run.py <stem>` fresh, no `--cache`, sequentially on the 5 holdout stems, engine venv python, nothing edited. No crash, no dev-only file needed (grep: run.py / tracker.py / dump_dets.py read no truth; cuts.json `pin_hit_frame` is used only to pick the overlay frame).
- Scored with `L/score_tracks.py` against the holdout truth in the cache (truth not copied into L).
- Machine loaded: 2-3 other torch jobs (cam-diff, appearance-prior, sam2-video), load average 7-11 on 12 cores. Wall times below are under that load.
- The fresh holdout tracks have identical positions and boards to the experiment's own (max position diff 0.0 px; files differ only in wall_s) on all 5; the experiment's originals are kept in `~/.cache/bowling-pov-holdout-2026-10-10/judge_detector-tiling/orig_tracks/`.

## Holdout scores
| stem | recall % | median px | board_err | lane_err (boards) | window_err | pass | wall s |
|---|---|---|---|---|---|---|---|
| 191253 | 96.2 | 5.2 | 0.5 | 3.55 | [4, 7] | yes | 65.4 |
| 191820 (gutter ball) | 58.3 | 7.5 | - (lane refused) | - | [3, 13] | no | 73.7 |
| 191913 | 60.9 | 8.3 | 2.0 | 2.35 | [2, 20] | yes | 68.2 |
| 192142 | 94.1 | 6.1 | 1.0 | 2.19 | [4, 4] | yes | 76.6 |
| 192636 | 83.3 | 3.6 | 5.5 | 3.54 | [5, 15] | no | 94.9 |
| mean | **78.6** | | 2.25 over 4 | | | 3/5 | 75.8 |

Holdout recall drops 13 points from dev (91.9 -> 78.6). The loss is at the END of the track: window_err end is 13 / 20 / 15 frames on 191820 / 191913 / 192636 (dev: 0-4). The chain stops well before the pin hit on those three, so recall is capped by missing far-end frames, not by wrong positions (median px 3.6-8.3).

## Dev reproduction
185645 re-run fresh: recall 95.2, board_err 3.5, lane_err 0.36, median 6.4 px, 56.8 s. Claimed 95.2 / 3.5: **reproduced exactly**.

## Overlay read
- The experiment's own overlays (`overlays/<stem>.jpg`) draw every frame's position on the pin_hit-4 frame, so on the head camera the polyline sweeps across the backdrop and cannot be judged. I built per-frame contact sheets instead (`judge_detector-tiling/sheet_<stem>.jpg` in the cache, tool `tools/sheet.py`): 8 evenly spaced chain frames, circle at the track point, lane quad.
- **192636**: circle on the ball on all 8 frames (r 97 at release down to 19-24 at the deck), lane quad on the lane the ball is rolling on. Final board 7.0: at f446/f455 the ball sits roughly 8-12 boards from the right edge of the quad top, so 7 reads low; consistent with board_err 5.5.
- **191913**: circle on the ball on all 8 frames, quad on the right lane. The chain ends at 498 with the ball still on the lane short of the pins (cutter pin hit 509, window_err end 20), which is where its 61 % recall comes from. Board 9-11 over the last tracked frames, final 9.0, board_err 2.0.
- No overlay read for 191820 (gutter ball; lane refused because the candidate frames failed on camera motion, 180 and 152 px between frames, and the third had a 51.6 px residual).

## Caveats
- The verdict sits on the threshold: 3 of 5 boards <= 3, exactly the minimum. One more stem like 192636 would make it partial.
- 191820 counts as a board failure (null), and the method gives no board at all on a gutter ball.
- The board is still the weak part, as the experiment said: 192636 is 5.5 off with a correct lane (lane_err 3.5).
- Holdout lane_err (2.2-3.6 boards) is worse than the 3 good dev stems (0.4-1.7).
