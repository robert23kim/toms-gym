# Session map, 2026-11-08 glasses-POV session (written 2026-11-09)

Quarantine: this stage did not open /Users/toka/pov-holdout/2026-11-09-glasses-pov-session. Everything below was read from the source clips in /Users/toka/pov-2026-11-08/drive_raw and from work/cuts/cuts.json.

Output: `results/session_map.json` (32 rows). Images and scripts: `work/structure/` (grid_*.jpg, scoreboard_*.jpg, deck_*.jpg, hands_*.jpg, lane_r20_*.jpg, person_A.jpg, person_B.jpg).

## Result
- **Game 1 = Tom** (10 clips, 104714..110948, frames 1-10). **Game 2 = Chardie** (10 clips, 111238..113113, frames 1-10). **Game 3 = Tom** (11 clips, 113541..115157: frames 1-10, plus 115157 as a 10th-frame bonus ball).
- 111218 is a no-throw clip from between games 1 and 2. Its boards show the game-1 finals. The wearer is unidentified (guessed Tom, conf 0.4, game 0).
- **Naming caveat:** the scoreboard spells the second bowler **"Chris"**, not "Chardie". The map uses "Chardie" because the brief says Tom and Chardie took turns, and only Tom and Chris appear on the boards. If that is wrong, rename game 2. Every game-2 row says so in its evidence.

## How the two wearers were told apart
1. **Appearance cluster.** All 31 throw clips were checked (`hands_*.jpg`, release-75/-40).
   - **A** looks down at the approach in the stance. The ball is below the view, the head shadow is on the approach, the forearms are bare, and the ball is the navy/red swirl house ball.
   - **B** holds a black ball with yellow inserts up at chest height in view. B wears dark navy long sleeves to the wrist and a wedding band on the left hand (112146 f90).
   - The two clusters split exactly at the game boundaries: A in games 1 and 3, B in game 2. Reference crops: `person_A.jpg` (110442 f15/f317) and `person_B.jpg` (111631 f45, 112800 f212).
2. **Lane and monitor.** The pair is lanes 27/28 (masking labels "26 27" and "28 29" sit over the outer dividers). Bowlers alternate lanes every frame, and each monitor shows the bowler currently on its lane.
   - The wearer's lane matched the "Tom" monitor at 114631 (lane 27, frame 7) and 114810 (lane 28, frame 8).
   - It matched the "Chris" monitor at 111238 and 112146 (lane 27, frames 1 and 5).
   - Ball-return side (right = lane 27, left = lane 28) alternates strictly through game 1.
3. **Pin counts against the board rows.**
   - 104946 (game 1 frame 2) left 1-2 pins. Tom spared that frame and Chris struck.
   - 111238 (game 2 frame 1) left 3-4 pins: Chris 6 split, Tom X.
   - 112146 (game 2 frame 5) left pins: Chris 9/, Tom X.

## Scoreboard transcriptions (frame = source frame)
| clip | frame | read |
|---|---|---|
| 111218 | f40 | Game 1 final. Chris 29 48 57 85 104 113 122 141 150 169. Tom 9 27 35 44 .. 123 (frame 1: 5 split 4). End-of-game screen on the console. |
| 111238 | f0, f182 | Game 2 start, both rows empty. Series pinfall: Chris 169, Tom 123. |
| 111420 | f144 | Chris game 7, Tom game 10 (133-123). |
| 111941 | f3 | Chris 34 (pinfall 203), Tom 37 (160). |
| 112146 | f136 | Chris 6 1, 6/, 8 1 (split), 6/ -> 34+. Tom game 47. |
| 112413 | f126 | Tom X, 8 1 (split), 8 1 (split), X, X -> 37 shown, game 67. Chris 6 1, 6/, 8 1, 6/, 9/ -> 53. Frame 6 highlighted. |
| 112936 | f98-105 | Frame 9 highlighted. Tom through 8 (X X X X X 9/ in 4-8). Chris through 8. |
| 113113 | f99 | Tom (left) through 9 = 171. Chris (right) 6 1, 6/, 8 1, 6/, 9/, 7 2, X, X, X = 109 shown, game 139. |
| 113541 | f80 | Game 3 start: Tom (left) 0, Chris (right) empty. |
| 114059 | f142 | Tom (right) X, 7/, 8 1 = 47. Chris 30 through frame 1 (X X X). |
| 114631 | f76 | Tom (left) X, 7/, 8 1, 8(split) 1, 9/, X = 76. Chris X X X 9- X .. = 117. Series pinfall Tom 396, Chris 473. |
| 114810 | f108 | Tom (right) adds 9/ in frame 7, 96 shown. Chris 117 shown. |
| 114919 | f60, f121 | Motion-blurred. Tom about 110-116, through frame 8. |
| 115105 | f0 | Tom X, 7/, 8 1, 8 1, 9/, X, 9/, X, 9- = 144. Frame 10 current. |
| 115157 | f177 | Tom game 154 (pinfall 464). |

Series arithmetic: game 2 is Tom 197 and Chris 187. Game 3 is in progress at the last board.

Unreadable or absent:
- Game 1 has no in-game board read. The wearer never looked up.
- 113716, 113911, 114236 and 114438 have no board.

## Game boundaries and frame numbers
- Games 2 and 3: frame numbers are pinned by board reads in 9 clips. The clips between them are filled in by order, one clip per frame.
- Game 1: frames come from order plus the strict 27/28 alternation. There is no in-game board.
- 110622 -> 110713 is only 51 s apart, but it changes lane, so it is the next frame and not a second ball.
- 115105 -> 115157 (52 s) stays in frame 10. 115157 is ball 2 or 3 of frame 10: either 115105 was a strike, or a spare ball between them went unfilmed. This was not resolved.
- Capture gaps between games: 2.5 min after 110948 and 4.5 min after 113113. These were used only as a prior.

## ball_in_frame
- Every clip is the wearer's first ball of a frame on a full rack, except 115157 (10th-frame bonus on a fresh rack). This rests on one clip per frame plus the board progressions. Racks were not individually inspected on every clip.
- 113541: at f45 a hand with a dark sleeve moves a black ball on the return. The rolled ball reads blue-purple (cuts stage), and the stance is cluster A.
- 114236: the swirl ball is in hand at f15. The ball is not visible after release.

## Not done / caveats
- Pin-count checks were run on 4 clips (104946, 111238, 112146, 114631). 114631 was too blurred to count, so it rests on lane + monitor. Other clips rest on the cluster and order.
- "Chris" vs "Chardie" is unresolved (see above).
- The masking-label lane reading assumes the label sits over the 26|27 and 28|29 dividers. The alternation and the monitor swaps are consistent with that reading.
