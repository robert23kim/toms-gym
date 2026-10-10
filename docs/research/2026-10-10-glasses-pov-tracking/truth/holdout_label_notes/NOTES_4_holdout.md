# Holdout truth notes, agent 4 (eeb210f6, 7c7fbfb0)

Scripts: a4_fit.py (blob fit + circle on gridded crop), a4_chain.py, a4_lane.py (per-row edge walk + line fit),
a4_gc.py, a4_build.py (assembles JSON + overlays; all readings are hardcoded there). Crops in ../<stem>/.

20260915_192142_eeb210f6: release 415 (+-1), pin hit 480 (+-2; ball overlaps pin bases from 479, among pins/dim at 481,
hidden 482) - cut window agrees. 17 points 416-480. Board 10.0 +-0.9 (edge 10.74, pin ruler 8.91 at f479).
Uncertain: 416 (motion blur, r +-10), 432 (vertical blur). Pin rows at 425 (y~290) are a guess on a blurred,
rolling-shutter frame. Lane-edge line at 425 fitted on a blurred frame (vanishing y 164, inconsistent with later frames).
20260915_192636_7c7fbfb0: release 391 (+-2; hand still on the ball at 393), pin hit 457 (+-2) - cut window agrees.
18 points 393-457. Board 12.5 +-0.5 (edge 12.2, pin ruler 12.32 at f456). Uncertain: 393 (ball cut by the frame
bottom, hand on it), 400 (blur). At 453 the lane's left edge leaves the frame below y~1545 so the quad's near row
is y=1540; at 401 the pin row (y~75) is blurred and the edge-line fit has a vanishing y of -75 (rolling shutter).
Both: edge lines are fitted over the near lane and extrapolated ~20-60 px to the pin row; lane width at the pin row
by edges vs pin ruler: 79.9 vs 70.3 px (eeb), 89.7 vs 71.5 px (7c7).
