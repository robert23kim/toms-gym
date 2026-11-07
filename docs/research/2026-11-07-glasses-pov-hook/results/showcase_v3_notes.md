# Showcase v3 notes (exit pass, 2026-11-07)

`showcase.mp4`: 1920x1080, 30 fps, 33.9 s, H.264 + AAC (ffprobe). Rendered by `make_showcase.py` from `results/tracks` (exit pass) and `results/final_v3.json`. Frames saved in `work/showcase_frames_v3/`.

## Timeline
| # | throw | split | start s | end s | source frames |
|---|---|---|---|---|---|
| - | title card | | 0.0 | 2.0 | |
| 1 | 191253 | HOLDOUT | 2.0 | 4.87 | f372-f457 |
| 2 | 191820 | HOLDOUT | 4.87 | 7.07 | f406-f471 |
| 3 | 191913 | HOLDOUT | 7.07 | 10.0 | f436-f523 |
| 4 | 192142 | HOLDOUT | 10.0 | 13.03 | f410-f500 |
| 5 | 192636 | HOLDOUT | 13.03 | 16.1 | f386-f477 |
| 6 | 185121 | dev | 16.1 | 18.87 | f292-f374 |
| 7 | 185331 | dev | 18.87 | 21.73 | f293-f378 |
| 8 | 185454 | dev | 21.73 | 24.3 | f321-f397 |
| 9 | 185645 | dev | 24.3 | 27.23 | f232-f319 |
| 10 | 190115 | dev | 27.23 | 29.9 | f385-f464 |
| - | closing card | | 29.9 | 33.9 | |

## What the panels show
- **Left:** the source frame with the tracked circle, cyan when tracked and orange when interpolated. It continues through the pin deck to the last real ball point. After that a note says where the tracker lost the ball: behind the pins, or in the gutter on 191820. On the pin-row frame the label says "pin row (detected)", or "cut label" on the three fallbacks.
- **Top-down lane:** the depth axis is ft_cv with 60 ft at the detected pin row. The lane runs 0-60 ft, the pin deck is a lighter band from 60 to 62.6 ft with the 10 pins placed by row, and the pit is a dark band after it. The magenta line is the 5-frame median board to the pin row. A yellow dotted line runs from the entry ring through the deck to the exit marker on the deck's back edge. The loop-1 trace is faded grey. The vertical board ruler is gone. The current-frame readout says "gutter" below board 0.5.
- **Markers:** the break shows as a cross with "break <board> @ <ft> ft", on throws whose minimum is interior and rises at least 2 boards after it. The entry is a cyan ring with "entry at the pin row: board X". The exit is a large yellow box with "EXIT board Y" and the deflection in words. "Straight through" or "through the pocket" applies within 1.5 boards of the entry, and "deflected left/right" otherwise. Under the box a grey note gives the last tracked frame and board when the tracker followed the ball past the lead-rule exit.
- **Pin deck zoom:** an inset at about 7x shows 58.5-64.6 ft, so the deck path, entry and exit are readable.
- **Closing card:** before (v2: cut label, stops at pin_hit+4) against after (exit pass), holdout and dev side by side. Rows are pin row, entry at the pin row, exit by the lead rule, and exit at the last tracked frame. Caveat lines below.

## Frames read (Read tool)
- **Pin-row and exit frames, all 10 throws (20 images):** read on the render before the label fixes. The gutter pin-row and the exit frames for 191820 were re-read after the gutter fix, and 192142 pin-row and exit were re-read on the final render (the last two renders changed only the closing card). The closing card was read on the final render. The start and mid frames and the title card were saved but not read.
- **Fixes made from reading:**
  - Per-point dots made the magenta line look dotted, so they were removed.
  - The break label ran into the legend. It is now placed on the lane side and boxed.
  - The legend and inset labels were clipped at the right edge. They were shortened and moved.
  - The inset entry label was cyan on wood. It now sits on a dark strip.
  - The EXIT box covered the deck in the lane panel. It moved to the right column.
  - The fallback throws said "pin row (detected)". They now say "cut label".
  - The gutter ball said "behind the pins". It now says "in the gutter", with "GUTTER BALL, in the gutter from ~39 ft".
  - The 185454 exit frame was missing because the clip ended at cut_end-1. The clip now ends at cut_end.

## Not checked
- Audio sync and playback in a player. The audio track is the source clip audio per throw, concatenated as before.
- The exit marker uses the lead's exit rule, which fires 3 frames after the pin row. On 192142 the box reads 20.7 while the truth exit is 36.1. The grey note gives the last tracked board, 29.9.
