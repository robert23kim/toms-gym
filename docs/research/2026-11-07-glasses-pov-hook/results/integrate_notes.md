# Loop 2 integration: track_v2 (2026-11-07)

## Stage picks (fixed decision rule, applied per stage)
| stage | loop 1 | loop 2 pick | why |
|---|---|---|---|
| ball | sam2-video | **lane-gated-ball** | ball/both with verdict works: lane-gated-ball (far recall 100, far px 1.90) and composition (97.5, 4.10). Highest far recall wins. far-end-stacking is partial. |
| lane | engine SAM quad carried by a 2x3 affine | **composition edge lane** (`--lane edge --smooth 3`, board at the ball centre row, final_board = Theil-Sen over pin_hit-10..pin_hit evaluated at pin_hit) | lane/both with verdict works: composition only (path_err_far 2.53). pin-anchored-geometry is partial (crashed on 191913, entry<=3 on 2/5). |
| path | none | **none** | physics-smoother verdict is partial (entry regresses 8.04 -> 9.14, entry<=3 on 0/5, drew a 7.4-board hook on the 191820 gutter ball). The rule is "works AND the refit improves", so it fails on the first condition and the refit was not needed. No `path_fit` is written. Composition's own line/hook fit is stored as `path_fit_diag` and is not drawn or scored. |

Two picks changed from loop 1, ball and lane. This ball+lane pair was never judged together: composition was judged with the appearance-prior ball. The numbers below are a fresh run of track_v2, not a prediction.

The final_board rule is part of the lane pick: composition's judged entry came from the Theil-Sen entry. The loop-1 median of the last 5 lags the last-15-ft move.

## Build
- `track_v2.py <stem> [--device]` loads `experiments/lane-gated-ball/run.py` and `experiments/composition/run.py` with importlib under distinct names. The ball step calls `LGB.main()` with `LGB.X` pointed at `work/track_v2/lgb`. The lane step calls `CM.run()` with `CM.ball_stage` replaced by the lane-gated-ball points, writing into `work/track_v2/comp`. No stage logic is re-implemented.
- The overlay uses composition's camera-compensated `draw_overlay` (each point is converted to (board, ft) in its own frame's lane and then drawn in the pin_hit-4 frame), with no fitted path. Following loop 1's rendering rule (trim jumps over 6 boards), a top-down point more than 6 boards from the median of its neighbours (f <= pin_hit) is left out of the drawing only. That happened once, on 191820 f463. boards{} and the scores keep the point.
- Fallback rule, fixed before the run: ball fails on an exception or no point in release..pin_hit; lane fails on an exception, boards on less than 50 % of roll frames, or no final_board. **fallback_stems: none.** All 10 ran on the chosen stages with exit 0. Each stem takes 10-15 s of process time, and wall_s also counts the 64-226 s loop-1 sam2-video wall the ball stage reads from disk.

## Results (score_v2; dev against L2/truth, holdout against the holdout folder; v1 = loop-1 sam2-video track on the same truth)
| split | stem | n | final | min | far rec v2/v1 | far px v2/v1 | path_far v2/v1 | entry v2/v1 | hook v2/v1 | dir v2/v1 |
|---|---|---|---|---|---|---|---|---|---|---|
| dev | 185121 | 55 | 11.1 | 10.2 | 100/100 | 0.9/2.0 | 0.63/- | 0.03/- | 0.71/- | T/- |
| dev | 185331 | 65 | 8.3 | 5.0 | 100/100 | 2.1/8.3 | 0.95/5.05 | 1.42/1.88 | 1.66/3.87 | T/F |
| dev | 185454 | 56 | 11.0 | 11.1 | 100/100 | 0.9/1.1 | 0.49/0.82 | 0.61/0.61 | 0.04/1.82 | T/T |
| dev | 185645 | 67 | 7.6 | 7.3 | 100/100 | 1.1/1.9 | 0.39/1.42 | 0.08/0.52 | 0.16/1.90 | T/F |
| dev | 190115 | 59 | 8.8 | 8.7 | 100/100 | 0.6/2.1 | 0.20/1.05 | 0.19/1.01 | 0.12/1.80 | T/T |
| hold | 191253 | 65 | 8.7 | 6.6 | 100/100 | 1.8/3.6 | 0.80/1.51 | 0.77/3.47 | 1.57/2.95 | T/T |
| hold | 191820 | 57 | -1.6 | -2.4 | 100/100 | 4.4/5.4 | **7.98**/2.49 | 0.81/3.41 | 3.74/10.06 | T/F |
| hold | 191913 | 73 | 11.1 | 7.6 | 100/0 | 1.4/30.8 | 1.55/16.07 | 1.00/3.10 | 0.67/13.49 | T/F |
| hold | 192142 | 70 | 11.0 | 6.3 | 100/100 | 1.0/4.0 | 0.51/2.15 | 10.65/16.65 | 10.37/13.38 | T/T |
| hold | 192636 | 71 | 13.8 | 7.1 | 100/100 | 0.9/10.5 | 0.44/4.66 | 6.75/13.55 | 6.38/10.50 | T/T |

> Superseded for 191820 and the holdout means by the fix pass below (path_err_far 1.11, direction 80 %); the other 9 rows are unchanged.

Holdout means, v2 vs v1:
- far recall 100 vs 80
- far px 1.90 vs 10.86
- path_err_rms 1.68 vs 5.39
- path_err_far 2.26 vs 5.38
- entry 4.00 vs 8.04
- hook 4.55 vs 10.08
- direction 100 % vs 60 %
- entry<=3 on 3/5 vs 0/5

Dev means are in-sample, because the refine thresholds and the smoothing were tuned on dev: path_far 0.53, entry 0.47, hook 0.54. Before/after over all 10, nulls skipped: far recall 90 -> 100, entry_err 4.91 (n 9) -> 2.23 (n 10), path_err_far 3.91 (n 9) -> 1.39 (n 10). 185121 gets a board for the first time, because SAM refused its lane in loop 1.

Caveats, all measured:
- **191820 is the one regression**: path_err_far 7.98 vs 2.49. At f463 (pin_hit, camera whip) the per-frame edge fit picks another component and the board reads 19.2 where its neighbours read about -1.6. A 3-frame median cannot fix the last frame of a series. The Theil-Sen entry is robust to it (entry 0.81). The far trend +8.3 and direction_ok=True on that stem come from the same outlier, not from a real hook. Without 191820, holdout path_err_far is 0.83 vs 6.10.
- 192142 and 192636 entry (10.65 / 6.75) are scored against the truth entry at the observed pin contact, 6-10 frames after cuts.json pin_hit. Against the truth's `entry_at_cut_pin_hit` (unscored), v2 is off by 0.17 / 0.21 and v1 by 5.83 / 6.59. Most of the holdout entry_err left is that convention, not the tracker.
- Hook in the raw boards (far-window slope x12, v2): 191253 +2.5, 192142 +4.8 and 192636 +5.7 all rise, matching the truth (the hook back left is in the measured series). 191913 rises +3.4, matching the truth, where loop 1 sat on the gutter object. 191820's +8.3 is the f463 artefact. Every dev stem except 185331 is flat or falling, and 185331 rises +3.1 against a truth that also rises.
- Diagnostic only: putting composition's line+hook fit back as path_fit gives holdout entry 4.01, hook 4.78 and path_far 2.26, so it adds nothing. It also draws line+hook on all 5 holdout stems, including a **20-board hook on the 191820 gutter ball**. That fit must not be drawn as-is. A path stage needs an outlier rejection at pin_hit before any hook form.

## Sensitivity (leave one holdout stem out, picks re-made from the judges' per-stem rows; results/final_v2.json "sensitivity")
- Rule at n=4: a lane/both experiment works if its path_err_far mean is below loop-1's AND entry<=3 holds on >=3 stems (count kept). A ball experiment works if it has no per-stem regression (the lane-gated-ball judge's override). Under the literal ball rubric it works if far recall beats loop-1 on >=3 stems.
- **The lane pick is fragile.** Leaving out 191253, 191820 or 191913 flips it to the loop-1 engine lane, because composition's entry<=3 stems are exactly those three. The 192142 and 192636 leave-outs keep it. path_err_far without 191913 is 2.68 vs 2.70, nearly a tie.
- Ball pick under the judges' rule: leaving out 192636 flips it to far-end-stacking. Its only regression, hook on 192636, goes away, and it wins the far-px tiebreak (1.80 vs 2.15). No other leave-out flips it. With 191820 out, composition reaches 100 far recall but loses the tiebreak (3.95 vs 1.28).
- Under the literal ball rubric, lane-gated-ball "fails" (beats loop-1 far recall on 1/5 only, since loop-1 is already 100 on 4/5). The full-set ball pick would then be composition's appearance-prior ball, and it flips to loop-1 sam2-video on the 191253, 191820 and 191913 leave-outs. The judge's override is what makes lane-gated-ball the pick.
- The path pick never flips: entry<=3 holds on 0 of 4 in every leave-out.

## Truth isolation
- Audit hook (`audit_run.py`, `sys.addaudithook` on `open`, installed before track_v2 is imported): 155-165 opens per stem and **0** paths containing truth, label or pov-holdout across all 10 runs. Canary: cuts.json and the L1 tracks appear in every log (3 per stem), so the hook was recording. cv2.VideoCapture does not go through Python open, but truth is JSON. Logs: `work/track_v2/audit/<stem>.json`.
- Static scan of every loaded project module: camdiff.py, lane-first/lane.py, lane_geom.py, composition/run.py and lane-gated-ball/run.py, plus track_v2.py by grep. It found 4 text hits and no file I/O: composition/run.py:15 (docstring "like the dev truth"), :435 (meta string "dev truth convention"), lane-gated-ball/run.py:13 (docstring "within ~1 px of the truth r") and track_v2.py:14 (docstring "Never opens truth"). No label or holdout-path hits.
- final_v2.json holds scores only: every truth_* scorer field was dropped. hook_err together with entry and min still lets the truth hook size be back-computed, as in the judge files.

## Files
`track_v2.py`, `audit_run.py`, `score_final_v2.py`, `results/tracks/<stem>.json` (10), `overlays/final__<stem>.jpg` (10), `results/final_v2.json`, `work/track_v2/` (stage outputs, logs, audits).

## Verification addenda
- The overlays folder holds 10 `final__<stem>.jpg` files (counted from `ls -l`). 191900 was excluded, as everywhere else.
- Lazy import not loaded at run time: `L1/experiments/sam2-video/sam_track.py` (6.7 KB) is lane-gated-ball's SAM re-prompt, which never fired. A separate grep of it for truth, label and pov-holdout found 0 hits (grep exit 1). In total, 5 loaded modules plus 1 lazy-import candidate were scanned.
- For the showcase: the clean path representation is `lane_top_down` (board, ft), which the right-hand panel draws as a monotone path. The green image-space polyline zig-zags on some stems (192142, 192636) because it re-projects (board, ft) through `LG.image_point` into the pin_hit-4 quad. Build the video's path from lane_top_down/boards, not from that warp. This was not fixed here.

## Fix pass (2026-11-07, after refute_hook-in-data and refute_provenance)
No stage was demoted. Neither skeptic showed output that was not the tracker's, and no hook is drawn that the raw boards do not contain. Picks stay ball lane-gated-ball, lane composition, path none. Only fix 3 moves numbers; fixes 4-6 change the drawing only, and fixes 1-2 change the wording. Pre-fix tracks, overlays and final_v2.json are kept in `work/fixpass/before/`; the pre-fix script is `work/track_v2/track_v2.pre_fixpass.py`.

### Claim wording (fixes 1, 2; also in final_v2.json `claim_caveats`)
- **Shared instrument.** The holdout ball truth is a purple/dark HSV blob fit, confirmed by eye, and the lane-gated-ball far refine is a purple disc filter. The truth boards come from same-frame wood->gutter edge lines, and the composition lane is per-frame wood-mask gutter edges. So "far px 1.9 / path_err_far 1.1" means agreement with that shared instrument, and v1 (SAM masks) is being scored on the instrument v2 copies. Absolute board accuracy below about 1.5 boards is **not established**: the truth's own pin ruler and edge profile disagree by 1-2 boards.
- **Post-selection.** The ball and lane stages were picked from the judges' holdout rows, which is why the leave-one-out flips exist. The v2 holdout means are therefore not a fresh test. The n=10 before_after includes the 5 dev stems used to tune the refine thresholds and the smoothing. `before_after_holdout` (n=5) is now written next to it.
- The fix-pass series rule was itself written after the skeptics had read the 191820 holdout row.

### Series: outlier rejection at pin_hit (fix 3), in `clean_series`
- Rule: a frame from pin_hit-2 to the end of the track is dropped from boards{} and lane_top_down when its raw board is more than 6 boards (the size of the loop-1 trim) from a Theil-Sen line over raw pin_hit-10..pin_hit-3. The raw value stays in boards_raw and is listed in `series_rejected`. boards{} is the 3-frame median re-run on the cleaned raw, and final_board is composition `fit_path`'s entry re-run on the cleaned series.
- The rule is one-sided because 191820's f463-467 **all** read 17.9-19.2. A two-sided neighbour median would have kept f463 and dropped the good f462 (measured: deviations +10.4 and -11.3).
- Rejected: **191820 f463-467 only** (raw 19.16/19.03/17.87/18.67/18.26 against predictions of -2.1 to -2.4). The other 9 stems have byte-identical boards{}, lane_top_down boards and final_board compared with the pre-fix tracks.
- Margin: the largest kept tail deviation is 4.51 (191253 f440, after pin_hit), then 4.29 (192636 f461, the real hook at contact). The smallest rejected deviation is 20.12. The fixed linear reference would start rejecting a real hook that kept curving more than ~6 boards past the reference line. On these 10 that does not happen within pin_hit+4, but the rule is not safe for a longer post-pin window.
- f463 is **omitted, not imputed**. 191820 path_missing_far is now 1.
- Mutation check (`work/fixpass/mutation/mutation_191820.txt`, a scratch re-run with REJECT_BOARDS=1e9): rejected [] and path_err_far 7.98 (the pre-fix value), against 2.26 with the shipped rule. The scratch re-run with the shipped rule matches the shipped boards exactly.
- 191820 after the fix: final_board -1.6 -> -1.7, path_err_far 7.98 -> 2.26 (v1 2.49), entry 0.81 -> 0.71, hook 3.74 -> 3.64. **direction_ok True -> False**: the track's far trend is -0.15 against a truth of +2.57. The earlier True came from the artefact.
- Composition's diagnostic line+hook fit on the cleaned series is now a plain `line` on 191820, so the 20-board hook is gone. It picks line+hook on exactly 185331, 191253, 191913, 192142 and 192636, all of which hook in the truth. It is still not drawn and not scored (path stays none).

### Re-scored (score_v2, same truth)
| | holdout v2 pre-fix | holdout v2 fixed | holdout v1 | all-10 v2 pre-fix | all-10 v2 fixed | all-10 v1 |
|---|---|---|---|---|---|---|
| path_err_far | 2.26 | **1.11** | 5.38 | 1.39 | **0.82** | 3.91 (n 9) |
| path_err_rms | 1.68 | 0.92 | 5.39 | | | |
| entry_err | 4.00 | 3.98 | 8.04 | 2.23 | 2.22 | 4.91 (n 9) |
| hook_err | 4.55 | 4.53 | 10.08 | | | |
| direction_ok | 100 % | **80 %** | 60 % | | | |
| entry<=3 | 3/5 | 3/5 | 0/5 | | | |
| far recall | 100 | 100 | 80 | 100 | 100 | 90 |
Only 191820's row changed. Dev means are unchanged (in-sample). Both caveats above apply to every v2 number in this table.

### Drawing (fixes 4, 5, 6): `draw_overlay_v2` in track_v2.py
- Depth is now **constant speed anchored at release = 0 ft and cuts.json pin_hit = 60 ft**: `ft_cv = 60 (f - release) / (pin_hit - release)`, stored per lane_top_down point. The per-frame `ft` and `zone` are unchanged in the JSON.
  - This departs from the literal cv_fit `v`. The raw cv_fit puts pin_hit at 63-67 ft on 7 of 10 stems (191820: 1.2942 x 52 = 67.3 ft; implied_pin_frame is 4-7 frames before the cut pin_hit), so `v (f - rel)` would push the hook off the panel and drop pin_hit again. Like cv_fit, the anchored version is linear in time, which removes the per-frame noise. It uses the same pin_hit=60 ft prior the old drawing already used.
- Frames are selected by f (release..pin_hit drawn solid) and by board (-8..47, so the 191820 gutter ball draws), not by the per-frame zone. pin_hit now draws on 185331 f358, 185645 f299 and 191253 f434. It does not draw on 191820, where f463 was rejected.
- The end is labelled "board at cut pin_hit (cuts.json input, f<pin>)" on the image and "@cut pin_hit" on the panel, not "pin row".
- The tracker's own frames after pin_hit (4 on every stem except 191820, where all 4 were rejected) are drawn as a dashed grey extension above the 60 ft line and labelled unscored. Nothing is extrapolated and no scored window moved.
  - **Not done: extending the track to observed contact.** The ball stage's track ends at pin_hit+4, which reaches 192636's contact (f461) but not 192142's (f490, pin_hit+10). The scored entry on 192142/192636 stays at the cut pin_hit.
- The loop-1 6-board drawing trim still runs on the cleaned series as a check. It now trims nothing on all 10 (`overlay_trimmed_frames: []`). Before the fix it trimmed 191820 f463.
- Read on the target surface (the overlay JPEGs):
  - 192636: the panel line moves out right to ~board 7 and comes back left to 13.8 over the last ~15 ft, then the dashed extension continues left. The image green line no longer zig-zags (pre-fix: scattered panel points and a kinked image line).
  - 192142: same shape, ending at 11.0.
  - 191820: a straight gutter line to -1.7, with no 19-board spike and no hook.
  - In the image the hook is still compressed near the pins by perspective; the top-down panel is where it can be read.

### Truth isolation (re-run under audit_run.py with the new code)
All 10 stems were re-run sequentially under the audit hook (exit 0). Each made 155-165 opens, **0** of them on a truth, label or pov-holdout path. The canary held: cuts.json and the L1 sam2-video track were opened in every log. Static hits are the 3 known docstring/meta strings (composition/run.py:15, :435; lane-gated-ball/run.py:13). The scratch mutation run read the holdout truth only in its own scorer step, after the tracker had run.
