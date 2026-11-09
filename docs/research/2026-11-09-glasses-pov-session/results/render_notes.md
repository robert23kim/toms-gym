# Session video render notes (2026-11-09, re-render after critic must-fix items)

Script: make_session_video.py. Output: session.mp4, 1920x1080, 30 fps, 117.5 s, audio from the clips (silence on cards). Frames: work/session_frames/ (5 cards, 4 recaps, one exit frame per clip = 31 throws + the no-throw clip); work/session_frames_all/ has start/mid/pinrow/exit frames. Timeline: work/session_timeline.json.
Quarantine Q was not opened. Inputs: results/session_map.json, results/judged_final.json, results/tracks/*.json, work/cuts/cuts.json.

## Group timeline (start second, clips)
- 0.0 s title card (2 s)
- 2.0 s Game 1 Tom, 10 clips (6 with a line, 4 video only: 104714, 105322, 110224, 110622)
- 37.8 s Game 2 Chardie, 10 clips (9 lines, 1 video only: 112413)
- 72.8 s Game 3 Tom, 11 clips (3 lines: 113541, 114919, 115157 as 10b; 8 video only; 115105 is 10a)
- 108.4 s Unassigned, 1 clip (111218, no throw, confidence 0.4, raw 2.6 s clip)
- Game 1 Chardie has no clips in the map, so no group (it would be empty).
Each group: title card 1.5 s, recap 5 s, throws release-5 .. max(pin row, last real, exit)+8, capped at cut end.

## Critic must-fix items, how each was applied
1. Deck / last-seen points no longer say gutter: headline reads "last seen: board X" or "last seen: off the deck" when the point is outside 0.5-39.5; table says "off deck (last seen)". Checked on 112936, 112146 frames. "gutter" is kept only for throws judged gutter by entry.
2. Segments run to at least max(pin row, last real)+8. 105652 now reaches f386+ and shows its entry. Entry is "extrapolated" (dashed ring, label, table text "extrapolated") when entry_n == 0 or the line ends before 57 ft: 105652, 110713, 113541. Caption "behind the pins" only when last real >= pin row - 2, else "short of the pin row".
3. Break outside 0.5-39.5 is not printed: table "edge read", note on the lane panel (115157). Line still runs through the gutter band as the tracker says.
4. Left-panel captions now sit on a dark box (btxt). Checked on 111218.
5. Lane-panel pins drawn as 20x5 px ellipses (depth axis is compressed, 11.5 px row pitch), all 10 readable. Deck zoom and recap zoom unchanged.
6. Wording: no repeated bowler in headers; header uses 10a/10b; recap title "N throws, M with a line, K reaching the pin row" (singular and "1 clip, no throw" for 111218; table says "no throw").

## Checked
Read: recaps Game 1 Tom, Game 2 Chardie, Game 3 Tom, Unassigned; throw frames 105652, 112936, 112146, 115157, 111218. Not checked: other throw frames, audio sync by ear, the other three extrapolated throws as images (110713, 113541 follow the same code path as 105652 and appear in the recap tables as extrapolated). No mutation check of the new guards.

## Still wrong in the data (rendered as the tracks say)
- Chardie breakpoints read 8-13 ft on flat stretches (111238, 111631, 112936, 113113): argmin of a flat line, not a visible break. Not in the must-fix list; left.
- 115157 line wanders into the gutter band at 45 ft; the tracker's edge read, flagged as such.
- Game 3 has only 3 of 11 lines; the recap says little about Tom's third game.
- Title card flags the motion-only partial pick. The map calls bowler B "Chardie" but the overhead monitors spell "Chris".
