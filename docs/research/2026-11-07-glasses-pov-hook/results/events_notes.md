# Exit pass events (2026-11-07)

> **Round 2 update (18:25):** the pin-row error is now scored against the truth 60-ft frame (`frame_contact_row`, else `frame`) and against `contact_frame`. All 10 truth pin rows are re-derived. A static-pit-decoy rule ends the deck track on 185331, 185645 and 191913, and exits not observed in truth (185645, 190115) are not scored. Pin-row, entry and exit numbers below are round 1. Current per-throw scores and means: `results/final_v3.json` and the "Round 2" section of `work/exit_pass_notes.md`. Holdout pin row against the 60-ft frame: 3.4 frames for the detector vs 4.8 for the cut label. Against first pin motion: 3.0 vs 8.25. The breakpoint tables are unchanged.

Source: `results/tracks/<stem>.json` "events" (track_v2 exit pass), scored in `results/final_v3.json` by `score_final_v3.py`.
Depth is `ft_cv = 60 (f - release) / (pin_row_frame_est - release)`: constant speed, 60 ft at the detected pin row.

## What is tracker output and what is input
- **Tracker output:** the ball points through the pin deck, the per-frame edge lane, every board, `pin_row_frame_est`, entry, exit, deck frames and breakpoint.
- **Still an input:** `release_frame` from cuts.json. It anchors 0 ft, so every ft value depends on it. The cut pin_hit is still used as the start of the jump-rule window, as the anchor of the legacy `final_board`, and as the fallback when no pin-row crossing is held (185121, 190115, 191820).
- **Chosen after looking:** the base-row definition (midpoint of the pin column) and the ball point (centre) were picked after seeing the 192142 and 192636 crossing frames. Their contact frames (490, 463) were in the task text. No truth file was opened by track_v2: the audit hook logged 155-165 opens per stem and 0 truth, label or holdout paths.

## How the pin row is detected
The far end of the frame shows a bright column per pin: the pin itself, and below it the pin's mirror image on the glossy deck. The edge-lane pd row is the bottom of that reflection, 54-66 px below the pin heads. The headpin base row is taken half-way between the top of the column, measured per frame at the masking unit, and the pd row. `pin_row_frame_est` is the first real ball frame whose centre is at or above that row. It must hold on the next real frame and have at least 3 real frames after it.

| variant | definition | 192142 | 192636 | 191913 | 191253 |
|---|---|---|---|---|---|
| **est (used)** | centre y <= column midpoint | 486 | 463 | 511 | 446 |
| contact | y + r <= column midpoint | none | none | none | none |
| pd15 | centre y <= pd row - 15 in (lane-edge px/in) | 489 | none | none | none |
| lane (literal spec) | centre y <= loop-1 pin_y, else edge pd row | 471 | 444 | 493 | 430 |
| cut pin_hit (input) | | 480 | 457 | 509 | 437 |
| truth pin_row.frame | | 490 | 461 | 503 | 436 |

The literal spec lands before the cut on every hooker, because the lane-stage rows are the bottom of the reflection, not the pin bases. The pin row jitters about 5 px and the ball moves about 2 px per frame at the deck, so the method's resolution is 2-3 frames.

## Breakpoint (5-frame median minimum over release..pin row, ft_cv)
| stem | split | break board | break ft (detected pin row) | break ft (cut pin_hit anchor) | break ft (truth pin row anchor, diagnostic) | rise after break | read |
|---|---|---|---|---|---|---|---|
| 191253 | HO | 6.57 | 41.7 | 48.0 | 48.8 | 8.26 | hooks back |
| 191820 | HO | -1.9 | 56.5 | 56.5 | 55.5 | 0.15 | gutter ball |
| 191913 | HO | 7.67 | 42.0 | 43.2 | 47.4 | 4.27 | hooks back |
| 192142 | HO | 6.36 | 39.7 | 43.4 | 37.6 | 9.35 | hooks back |
| 192636 | HO | 7.57 | 40.8 | 44.5 | 42.0 | 11.03 | hooks back |
| 185121 | dev | 10.2 | 51.9 | 51.9 | 60.0 | 0.92 | flat after the minimum (< 2 boards) |
| 185331 | dev | 5.03 | 43.6 | 48.0 |  | 6.56 | hooks back |
| 185454 | dev | 10.9 | 45.9 | 60.0 |  | 3.76 | hooks back |
| 185645 | dev | 7.34 | 51.0 | 55.2 |  | 1.41 | flat after the minimum (< 2 boards) |
| 190115 | dev | 8.77 | 58.9 | 58.9 |  | 0.1 | minimum at the roll end: no measurable hook back |

On the four hookers the break now lands at 39.7-42.0 ft, against 43-48 ft on the cut anchor. Tom read about 37 ft on 192142. The tracker gives 39.7 there, and 37.6 if 60 ft sat at the truth pin row: the remaining gap is the 4-frame pin-row error. On 191253 and 191913 the detected row is late (8-10 frames), which pulls the break earlier than the truth anchor would (41.7 vs 48.8, 42.0 vs 47.4). So "about 40 ft" on those two is partly a timing error, not a measured break.

## Entry and exit vs truth (all 10 truth files carry pin_row / exit since 18:06)
| stem | split | pin row est / truth (flag) | cut label | entry at est / truth | raw board at truth frame | exit f, board (lead rule) | last real tracked f, board | truth exit f, board |
|---|---|---|---|---|---|---|---|---|
| 191253 | HO | 446 / 436 | 437 | 15.6 / 8.09 | 9.1 | 449, 20.34 | 455, 24.39 | 453, 27.72 |
| 191820 | HO | 463 (fallback) / 464 | 463 | -1.29 / -2.69 |  | none (gutter) | 462, -1.08 | 463, None |
| 191913 | HO | 511 / 503 | 509 | 11.92 / 5.97 | 9.04 | 514, 12.97 | 515, 12.97 | 518, 15.73 |
| 192142 | HO | 486 / 490 | 480 | 16.33 / 22.15 | 22.21 | 489, 20.69 | 495, 29.94 | 497, 36.13 |
| 192636 | HO | 463 / 461 | 457 | 20.07 / 18.33 | 18.23 | 466, 24.17 | 470, 30.51 | 471, 35.12 |
| 185121 | dev | 356 (fallback) / 349 (flagged) | 356 | 11.54 / 9.47 | 10.13 | 358, 11.54 | 366, 14.18 | 375, 18.35 |
| 185331 | dev | 364 / 350 (flagged) | 358 | 12.47 / None | 5.98 | 367, 15.01 | 375, 21.11 | 375, 21.8 |
| 185454 | dev | 394 / 377 (flagged) | 377 | 15.0 / 11.62 | 11.05 | 397, 18.0 | 397, 18.0 | 403, 22.14 |
| 185645 | dev | 304 / 291 (flagged) | 299 | 8.93 / None | 7.53 | 307, 8.9 | 313, 8.63 | 313, 5.25 |
| 190115 | dev | 444 (fallback) / 443 (flagged) | 444 | 8.64 / 8.74 | 8.87 | 446, 8.88 | 458, 14.82 | 456, 12.47 |

Means (truth pin_row on all 5 dev throws is flagged "NOT re-derived, early" by the truth agent, so dev pin row and entry are not scored):

| metric | holdout before (v2) | holdout after | dev before (v2) | dev after |
|---|---|---|---|---|
| pin_row_err (frames; before = cut label) | 4.4 (n=5) | 5.0 (n=5) | not scored | not scored (flagged truth: 10.4 (n=5)) |
| entry_err_pr (boards) | 4.48 (n=5) | 4.48 (n=5) | not scored | not scored |
| exit_err (boards, lead rule) | 14.39 (n=4) | 9.13 (n=4) | 7.08 (n=5) | 5.0 (n=5) |
| exit_err_last (boards, last real tracked frame) | | 4.22 (n=4) | | 2.95 (n=5) |

- **The board series through the deck is right; the timing is not.** The raw board at the truth pin-row frame is within 0.1 board on 192142 and 192636 and within 1 on 191253. The entry error comes from the pin-row frame: on a ball hooking 1.5-2 boards per frame at the deck, 4 frames is 6 boards.
- **The detector beats the cut on the two hookers it was built for, and loses on two others.** It is off by 4 and 2 frames on 192142 and 192636, where the cut is off by 10 and 4. It is off by 10 and 8 on 191253 and 191913, where the cut is off by 1 and 6. On 191253 the camera pitches up at the deck, so the pin row slides down onto a ball whose image row barely moves.
- **The lead's exit rule fires too early.** Under constant speed, 63 ft comes 3 frames after the pin row. The ball really slows among the pins and stays visible 7-10 frames, until truth f497 / f471. The last real tracked frame is within 2 frames of the truth exit on 192142 (495 vs 497), 192636 (470 vs 471) and 191253 (455 vs 453), and 3 short on 191913 (515 vs 518). Its board is still 3-6 boards short of truth on the hookers, because the refine filter loses the ball behind the pins.
- **Deflection direction agrees on every hooker:** the exit board is above the entry, so the ball deflected left. The truth notes call 192142 a Brooklyn-side entry that deflected left through the 2-4-7.
- **Dev:** all 5 dev pin-row truths are kept from the earlier pass and flagged by the truth agent as early: their base row is the deck-reflection bottom, the same error the detector was built to avoid. The truth notes give first-pin-move frames of f364 (185331), f396 (185454) and f312 (185645). The detector lands at f364, f394 and f304. On 185454 a crop check shows the ball centre on the pin bases at f394 with the pins upright. Dev exits are re-derived and scored: exit_err 5.0 with the lead rule, 2.95 at the last tracked frame.
- **185454:** the cut ends at f397, 3 frames after the detected pin row, so the deck track is cut short by the cut, not by the tracker.
- **190115 and 185121 fall back to the cut label.** No crossing is held, although the ball is tracked through the deck to f458 and f366.
