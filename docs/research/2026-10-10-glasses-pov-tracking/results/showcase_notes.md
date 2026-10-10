# Showcase notes (re-render after critic)

10 throws (191900 has no cut/track; title card says 10 throws, not 11). 28.9 s, 1920x1080, 30 fps, speed 1.0, tail +15, audio muxed.
Order: stem order, except the one no-lane-fit throw (185121) moved to last and labelled "no lane fit" on the left panel.
Fixes: circle stops after meta.last_lane_frame (191913 gutter circle gone); leading trace outlier trimmed (jump >6 boards or >10 ft vs next point); pin rack flipped (headpin nearest bowler); interpolated circles orange, tracked cyan; label has dev/HOLDOUT tag.
Not fixed: final-board readout on 192142 (5) and 192636 (7) is about 5 boards below truth (10, 12.5); the video shows the track's value as is.

| throw | stem | split | start s | end s | frames | fallback |
|---|---|---|---|---|---|---|
| 1 | 20260915_185331_19de9ec7 | dev | 2.00 | 4.70 | 81 | no |
| 2 | 20260915_185454_f240c883 | dev | 4.70 | 7.10 | 72 | no |
| 3 | 20260915_185645_9fde3c16 | dev | 7.10 | 9.87 | 83 | no |
| 4 | 20260915_190115_a7cf2c70 | dev | 9.87 | 12.37 | 75 | no |
| 5 | 20260915_191253_6cf2480f | holdout | 12.37 | 15.07 | 81 | no |
| 6 | 20260915_191820_0196b564 | holdout | 15.07 | 17.50 | 73 | no |
| 7 | 20260915_191913_907c358b | holdout | 17.50 | 20.47 | 89 | no |
| 8 | 20260915_192142_eeb210f6 | holdout | 20.47 | 23.33 | 86 | no |
| 9 | 20260915_192636_7c7fbfb0 | holdout | 23.33 | 26.23 | 87 | no |
| 10 | 20260915_185121_23d80f05 | dev | 26.23 | 28.90 | 80 | no (fallback triggered, not applied) |
