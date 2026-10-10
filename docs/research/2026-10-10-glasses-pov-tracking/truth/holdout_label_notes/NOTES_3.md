# Truth notes, agent 3 (holdout: 191820_0196b564, 191913_907c358b), 2026-10-10

These notes are kept out of L on purpose, because both stems are holdout.
Tools: ../tools/{sheet,cands,chain,refine,gc,gc2,full,strips,make_truth_holdout}.py. Crops are in work/<stem>/.

## Corrections to cuts.json
- 191820: release 412 (cuts said 411). The hand covers the ball at 411, fingers still cross it at 412, and it is free at 413. Pin hit 463 kept (+-2).
- 191913: release 442 (cuts said 441). The ball enters at the frame bottom at 441 and is on the lane with the hand trailing at 442-443. Pin hit 509 kept (+-2): the ball overlaps the 6/10 pin columns at 507-509, the pins are still up at 511 and scattered by 515.
- Both are one frame later and inside the stated +-1. The release+10/+30 quads use the corrected releases (422/442 and 452/472).

## 191820 is a RIGHT GUTTER BALL
- The ball drifts right from about board 9 at 422 and hugs the right edge about 10 px inside from 437 to 440. Its centre crosses the edge at 441-442, and it is in the gutter from 443 until it reaches the deck at about 463.
- I put the board at the last on-lane frames (437/440): 2.5 +-0.5. In the gutter at the deck it would be about -4 (stored as board_in_gutter_at_pin_deck_f459_approx). A method that reports the board where the track ends will read about -4. Decide which one the scorer wants.
- The pin-spacing ruler cannot be used here: the ball leaves the lane far from the rack. I used the ball's 8.5 in diameter as the second ruler instead.
- The camera rolls hard (the head turns right). From 450 the image x of the ball reverses even though the ball keeps going, which is camera rotation. The neighbour lane's ball (left, around (90-460, 860-1070)) is a second YOLO track at conf 0.6-0.8. Do not let a chain jump onto it.
- Uncertain points: 412 (hand overlap, +-10 px) and 459-463 (in the dark gutter with motion blur, +-4-5 px). The 422 quad is heavily blurred (+-10 px).

## 191913
- The lane is right of the '38 39' label (lane 39). Seven pin columns are visible at 6 in spacing (10.1 px at 505), so the head-pin column gives board 20. That is a clean ruler.
- Board 7.0 +-0.5 (f505 reads: edge 6.7, pin ruler 7.4). The f503 reads are 6.0/6.5, so a 6-7 band is the honest range.
- From about 487 the ball is tiny (r 10 down to 6.5) and sits on top of the pin reflections in the deck. The purple blob refine is fine to 506. From 507 the blob merges with the pin shadows (refine r about 13), so those radii were read by eye (about 7).
- YOLO's long track at (400->213, 860) from 492 on is another lane's ball or a pin cluster, not this ball.

## Overlays
These are the pin_hit-4 frame with the lane quad and every ball point. Each ball point is in its OWN frame's pixels and the camera moves, so early points scatter across the frame (the big circles at the top). Only the last ~10 points sit on the pin-hit-4 geometry.
