| method | description | sample_input | Chardie | tom_old | per-frame mean (s / C / t) |
|---|---|---|---|---|---|
| `generic_box` | Feb-2026 engine prompt: fixed box over the middle of the frame, no scene knowledge | 6.27 | fail | fail |  |
| `center3` | Feb-2026 fallback prompt: three points down the frame centre line | 13.00 | 6.89 | 7.77 |  |
| `track_pre` | 5 positive points along the ball path, pre frame | 1.42 | 1.13 | 1.12 |  |
| `track_mid` | 5 positive points along the ball path, mid frame | 6.06 | 31.11 | 7.20 |  |
| `track_last` | 5 positive points along the ball path, last frame | 0.09 | 1.07 | 0.93 |  |
| `track1_last` | A single positive point on the ball path (the 2026-09-12 report's prompt), last frame | 0.12 | 0.39 | 16.54 |  |
| `track9_last` | 9 positive points along the ball path, last frame | 4.85 | 3.90 | 1.31 |  |
| `even_last` | 5 points spaced evenly along the path's image length (15-85%), last frame | 0.17 | 0.50 | 1.54 |  |
| `even3_last` | 3 evenly spaced path points, last frame | 0.24 | 0.39 | 1.35 |  |
| `even_neg_last` | Evenly spaced path points plus negatives half a lane-width outside the first mask, last frame | 0.15 | 1.67 | 0.80 |  |
| `even_person_last` | Evenly spaced path points plus negatives on detected people, last frame | 0.29 | 0.38 | 1.54 |  |
| `track_box_last` | Path points plus a loose box around the path (x +-25% of frame width), last frame | 4.02 | 3.84 | 1.25 |  |
| `lane_neg_last` | Two passes: path points, then negatives half a lane-width outside the first mask, last frame | 2.93 | 3.78 | 1.20 |  |
| `person_neg_mid` | Path points plus negative points on every YOLO-detected person, mid frame | 6.15 | fail | 7.08 |  |
| `person_neg_last` | Path points plus negative points on every YOLO-detected person, last frame | 0.90 | 2.47 | 0.93 |  |
| `multimask_sam_last` | 3 candidate masks from the path points; keep the one SAM scores highest | 0.38 | 1.07 | 1.07 |  |
| `multimask_geo_last` | 3 candidate masks; keep the straightest full-height one containing the path | 0.38 | 1.07 | 1.07 |  |
| `median3_span` | Path points on 3 frames spread pre..last, median of the (camera-warped) edge lines | 2.10 | 1.51 | 0.93 |  |
| `median5_span` | Path points on 5 frames spread pre..last, median of the edge lines | 3.33 | 0.72 | 0.89 |  |
| `median9_span` | Path points on 9 frames spread pre..last, median of the edge lines | 3.28 | 0.77 | 0.92 |  |
| `median5_late` | Path points on 5 frames in the last 30% of the throw, median of edge lines | 1.79 | 0.43 | 2.00 |  |
| `outer5_span` | 5 frames pre..last, outermost left/right edge across frames (occlusion only narrows) | 1.08 | 0.40 | 1.49 |  |
| `outer9_span` | 9 frames pre..last, outermost edges | 1.10 | 32.60 | 1.86 |  |
| `vote5_span` | 5 frames pre..last, pixel-wise majority vote of warped masks, then one edge fit | 2.50 | 0.41 | 0.85 |  |
| `vote9_span` | 9 frames pre..last, pixel-wise majority vote of warped masks, then one edge fit | 3.06 | 0.43 | 1.68 |  |
| `vote9_person_span` | vote9_span with negative points on detected people in every frame | 2.89 | 0.68 | 1.40 |  |
| `vote5_even_span` | vote5_span with evenly spaced path points | 2.48 | 0.40 | 0.91 |  |
| `median5_span_snap` | median5_span, then snap each edge line to the strongest gradient within +-6 px | 1.97 | 0.76 | 1.36 |  |
| `vote9_span_snap` | vote9_span, then gradient snap | 1.60 | 0.75 | 1.83 |  |
| `perframe_track` | SAM on every 2nd ball frame with path points; each frame scored against its own lane | 0.08 | 0.48 | 2.08 | 2.08 / 12.42 / 5.91 |
| `perframe_person` | perframe_track with negative points on detected people | 2.84 | 0.51 | 2.08 | 3.11 / 95.99 / 5.29 |
| `video_span` | SAM 2 video mode: prompt once on the pre-release frame, propagate forward to the last frame; per-frame scoring | 0.29 | 0.37 | 1.21 | 2.00 / 19.45 / 3.55 |
| `video_rev` | SAM 2 video mode run backwards: evenly spaced prompts on the clean last frame, propagate back to release | 0.21 | 0.38 | 1.53 | 1.85 / 16.39 / 3.73 |
