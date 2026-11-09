# Critic notes: session.mp4 (2026-11-09)

Quarantine Q was not opened. Inputs: session.mp4 frames in work/session_frames and work/session_frames_all, results/session_map.json, results/judged_final.json, results/tracks/*.json, work/session_timeline.json, make_session_video.py. Scripts are in the session scratchpad (crit_lines.py, crit_recap.py, crit_all.py). They re-implement the renderer's lxy/zxy/runmed and read the PNGs back.

## Verdict
The lines come from the tracker: on 4 throws, each recomputed point lands within 3 px (0.3 board) of the drawn magenta. Each recap holds exactly its group's clips, and the labels match the map. The defects are in what the screen says around the lines: deck points labelled "gutter" or "left gutter", a throw segment that stops before its own pin row, a break printed off the lane, and captions with no backing box. The weakest numbers are recall 100 % (the metric is loose), releases read by eye on 24 of 31 clips, and two passers that rely on SAM fill or on the amendment made after the results.

## (a) Line vs track JSON, 2 throws per bowler, 15/30/45 ft
I recomputed each point as runmed5 of `boards`, with depth = 60*(f-rel)/(pr-rel), mapped through lxy, then measured the nearest magenta run on that pixel row.

| stem | who | 15 ft board / px | 30 ft | 45 ft | throw frame dist | recap dist |
|---|---|---|---|---|---|---|
| 104946 | Tom G1 f2 | 14.84 / 458 | 10.50 / 500 | 7.64 / 527 | 0,0,0 | 1,0,0 |
| 114919 | Tom G3 f9 | 9.80 / 506 | 6.25 / 540 | 6.29 / 539 | 0,1,0 | 0,1,1 |
| 111420 | Chardie G2 f2 | 5.83 / 544 | 4.06 / 561 | 5.61 / 546 | 0,0,0 | 2,0,0 |
| 112936 | Chardie G2 f9 | 10.86 / 496 | 11.03 / 494 | 13.34 / 473 | 0,0,0 | 2,3,2 (overlapping lines) |

I also checked that the board axis is not mirrored. In the video, the ball sits right of centre at 104946 mid, 114919 mid, 115157 mid and 111420 pin row, and the panel reads boards 3-11 there (board 1 = right gutter). Every hooker turns toward higher boards after its minimum, which is right for a right-hander, so no hook is drawn the wrong way.

## (b) Recaps contain exactly their group
- Table rows equal the map rows per group: G1 104714..110948 (10), G2 111238..113113 (10), G3 113541..115157 (11), Unassigned 111218.
- Leader tags equal the non-video-only stems: G1 2,4,5,7,9,10 (6). G2 1-5,7-10 (9). G3 1,9,10b (3).
- I read the entry rings on the deck at the expected x for each entry (for example G1 frame 2 at 6.2, x=1494, and frame 10 at 18.5, x=1337).
- None of the 13 video-only stems has magenta in the lane panel or a ring in the video panel, on any start or exit capture (pixel sweep). The canary: every lined exit frame has at least 200 magenta pixels.

## (c) Labels
All 31 timeline labels equal "Game {game} {bowler} frame {frame}" from the map, and every video_only flag equals the 13-stem list. 111218 is labelled "Unassigned no throw", and the screen shows "bowler uncertain (confidence 0.4)".
- Caveat for Tom: the map calls bowler B "Chardie", but the overhead monitors in the clips spell "Chris" (disclosed in session_map.json).

## (d) What a bowler notices in 10 seconds (render defects first)
1. **The headline says "gutter" or "left gutter" on throws that hit the pins.** The headline is `bstr(cur)` applied to the last deck point.
   - 112936: the headline says "gutter" while the same frame shows entry 20.4 and LAST SEEN board 0.0.
   - 112146: the headline says "left gutter" next to entry 20.2, "LAST SEEN board 40.0" and "ball hidden by pins after f408". A ball hidden by pins cannot be at board 40.
   - 110948 (40.5) takes the same path.
2. **105652's segment stops before its own pin row.**
   - `exit_frame` is None, so the segment stops at last_real+8 = f379, before pr f384. It is the only lined throw with no pinrow capture (17 of 18).
   - The throw never shows its entry. The recap draws a ring at 20.9 while the line stops at 50 ft on board 14.5, a 6.4-board gap with nothing joining them.
   - The caption says "tracker loses the ball behind the pins here" at f373, while the panel shows the loss at about 50 ft.
   - Smaller gaps between line end and ring: 110713 (ends at 55.3 ft, 2.3 boards), 114919 (57.5 ft, 2.0), 113541 (56.8 ft, 0.9).
   - The recap title claims "N with a line to the pin row". 4 of the 18 lines stop short of it.
3. **115157 prints "break -0.3 @ 45 ft".** The line runs into the gutter band, then returns to an entry at 10.9, labelled "straight through". In the video the ball reaches the right side of the rack, so it was not a gutter ball. The tracking data is wrong, but the off-lane board is printed without a guard.
4. **Captions sit straight on the video with no backing box.**
   - On 111218, "clip 111218" and "bowler uncertain (confidence 0.4)" are drawn over the lit scoreboards and are partly unreadable.
   - On 114236 (and other camera-up clips), "video only: no line drawn" sits over ceiling lights.
5. **The pin rack on the lane panel is not readable.** It has 10 pins of radius 18 px on an 11.5 px row pitch, so they overlap into a 7-circle clump with the back row hidden. This shows on every throw frame and every recap. The deck zoom is fine.
6. Small wording issues:
   - The Unassigned recap reads "1 throws, 0 with a line to the pin row" for a clip with no throw.
   - Headers repeat the bowler ("Game 1 Tom frame 2 - Tom").
   - The 115105 and 115157 headers both say "frame 10", while the recap says 10a/10b.
   - The G2 deck tags crowd together (1/10/7, 5/8, 3/9), but they stay legible.
7. Break readouts disagree with the picture. This comes from the data, and I list it here only because the screen shows it.
   - The Chardie breaks read 11.7 @ 12 ft (111238), 10.7 @ 11 ft (111631), 10.9 @ 13 ft (112936), 11.0 @ 8 ft (113113) and 8.4 @ 19 ft (112146).
   - On each of these, the line stays within 1 board of that minimum until 31-43 ft, where the visible turn is.
   - The breakpoint is the argmin of a flat stretch. A bowler will not believe a break at 8 ft.

## (e) Weakest numbers and checks that could not have failed
- **Truth recall_pct 100 on all 6 does not discriminate.** Each truth path has 13-15 sparse points. A point counts as matched if a track point, or one interpolated across a gap of up to 6 frames, lies within max(2r, 15) px, and SAM fill counts. The motion-only judge's own supplementary recall is 85.25 % (far 67.95 %). The metric can fail (ball-colour-model scored 74 %), but it reads 100 for the pick and for the final tracks alike.
- **Truth numbers that did move:**
  - entry_err_pr: mean 3.16, and only 4 of 6 are within 2.5 (110224 at 3.25, 113716 at 8.66). The final_board entry mean is 5.64.
  - pin_row_err: mean 8.83, and 4 of 6 are within 4 frames (104714 at 34, 113716 at 14).
  - All score fields are byte-identical across the reruns, so two rerun rounds did not move the truth clips.
- **J1 counts SAM fill as "real".**
  - 105652 passes J1 at 97.1 % on `src: sam` points f373-397 that have no board.
  - J6 for 105652 says the 55 ft circle sits on empty deck.
  - Its entry of 20.94 is a Theil-Sen extrapolation from f367-372 (boards 13.4-15.1) across 12 frames (`entry_n` 0).
  - Strict J5 for 105652 is 87.7. J5 as implemented (carried quad) reads 100 % on 15 of 16 round-3 stems.
- **2 of the 18 passers exist only under the 12:50 dead band, which was written after the rule owner saw the results:** 110713 (raw J4 sign changes 5) and 113113 (raw 6). 115157 passes J2 only through the "relaxed hold" detection added in rerun 1.
- **J fail counts:** 13 of 31 fail, 10 of them on J2. The ball ends 2-11 px short of the headpin base row while the gap is still closing (round-3 pinrow_gap table). Game 3 keeps lines on 3 of 11 throws.
  - 5 stems marked "pending rule-owner call" (110224, 105322, 113911, 114236, 115105) were rendered video-only from the task list.
  - The `video_only` key in judged_final.json lists 8, not 13, and is stale.
- **Release frames:**
  - RULES.md lists release as "detected, not hand-labelled", but 24 of 31 finals are eye reads. Auto v3 got 4 of 25 untouched clips right (15 null, 6 wrong and marked `verified: true`).
  - The release spot-check could test only 3 auto reads, and 2 were off by more than 100 frames (112146 at -182, 113113 at +130).
  - The v3.1 fix was a post-hoc fit with no holdout.
  - Every line's 0 ft anchor and its constant-speed depth rest on these eye reads.

## must_fix (render only)
1. Never label a deck or last-seen point "gutter" or "left gutter". Say "last seen board X" or "off the deck". Affects 112936, 112146 and 110948.
2. Run every lined segment to at least max(pr, last_real)+8. When `entry_n == 0`, or the line ends more than 3 ft short, draw the recap ring dashed and labelled extrapolated, or leave it out. The "behind the pins" caption must not fire before pr. Affects 105652, and the 110713, 113541 and 114919 gaps.
3. Do not print a break board outside 0.5-39.5. Mark it "edge read off lane" (115157).
4. Put a dark backing box behind the on-video captions (111218, video-only captions).
5. Shrink or simplify the pin rack on the lane panel so the 4 rows read.
6. Wording: Unassigned recap "1 clip, no throw". Drop the duplicate bowler from the header. Show 10a/10b in the throw headers. Change "with a line to the pin row" to "with a line".
