# auto_cuts.py: release and cut window with no hand labels

## Round 2 (2026-11-09): colour-free release rule (v3)

**Headline.** v3 was frozen on the 11 September clips before any 2026-11-08 clip was run.

- **September:** no regression. Release is within 1 frame on 10/10, 191900 returns null, and every cut window is identical to v2.
- **Honest test, 6 new clips:** 3/6 found, each within 1 frame of the eye release (errors 0, 0, +1). The other 3/6 returned null, so the failures are visible nulls, not wrong cuts.
- **111218:** returns "too short".
- **Cause of the misses: a diagnosis, not a test.** On the two black-ball clips the measured cause is the gutter baseline of an upright view. That does not depend on ball colour, but colour and view are confounded on those two clips. The third miss was a dark navy ball failing the post gate.
- **Post-hoc fix not shipped.** One fix was tried after viewing the strips (see below). v3 is what `auto_cuts.py` runs now.

### Usage

```
/Users/toka/code/bowling-app/analysis-engine/.venv/bin/python auto_cuts.py <source.mp4> [--out-dir DIR] [--no-cut]
/Users/toka/code/bowling-app/analysis-engine/.venv/bin/python score_auto_cuts.py <entries_dir> [--shift-release N] [--set-cut-end STEM=FRAME] [--json OUT]
```

Each entry now carries `runtime_s`. The default out-dir is `work/auto_cuts/` (gitignored). Round-2 outputs:

- **September entries (v3):** `work/entries_v3/`, scored in `work/score_v3_sept.json`.
- **2026-11-08 entries:** `work/entries_1108/`, with cuts in `work/auto_cuts_1108/`.
- **Scorer:** `score_auto_cuts.py` only knows the September labels, so the new clips are scored by eye in the table below.
- **Scorer mutation re-run on v3:** with `--shift-release 8` on the v3 entries, every release error moved by 8 and containment dropped to 0/3 dev and 0/7 holdout.

### The v3 rule, and what changed from v2

Only the release mask and the candidate selection changed. The blip shape, post gate, thud tag, rough pin hit, cut mechanics and scorer are unchanged.

- **Region.** Rows 65-100 % and columns 10-90 % of the 1/8-scale frame.
- **Mask.** A pixel counts as ball if its luma is below 0.6 of the region's median luma, or its chroma (a, b) is more than 30 from the region's median chroma. The median is the lane wood, so the mask means "not lane": black by luma, coloured balls by chroma. Skin is close to wood, so the arm mostly drops out.
- **Selection.** The EARLIEST candidate with T >= 0.04 and post < 0.04, not the strongest. With any colour-free mask, post-pin camera whips make strong blips 95-131 frames after release, on 185121, 185454, 191253, 191913 and 192142. A held ball before release fails the post gate, as 191900 shows.
- **How it was chosen.** I compared 12 masks on the September clips only: purple, Lab distance 20/30/40, relative V darkness, saturated non-wood, luma 50/60 %, chroma 20/30, and luma-or-chroma combinations. I also swept T in 0.03-0.06 and post in 0.03-0.05.
  - Full Lab distance failed: it picks up the arm and lane texture, giving post 0.1-0.3 at release.
  - With earliest selection, every luma, chroma and luma-or-chroma mask scored 10/10 plus the 191900 null across the whole plateau.
  - I took the most colour-general mask at mid-plateau thresholds.
- **September slack.**
  - The weakest true-release T is 0.074 (185331) against the 0.04 threshold.
  - The largest true-release post is 0.022 (191913) against 0.04.
  - No frame before release passes both gates on any September clip. The best pre-release T with post < 0.04 is 0.003, and the lowest pre-release post with T >= 0.04 is 0.458.
  - The 191900 blips all have post >= 0.477.

### Honest test: 6 new clips, rule frozen before any was run or viewed

Eye release follows the loop-1 convention: the ball enters the frame bottom at X and is on the lane, hand trailing, at X+1, so release = X+1. It was read from frame-by-frame grids. For the 3 detected clips the grid was auto-6..+6, Read only after the run. The 3 nulls have no auto release, so I first read the grid around the top rejected blip, then a whole-clip overview, then a frame-by-frame grid at the throw.

| clip | ball at release (as seen) | auto release | eye release | error | cut | runtime |
|---|---|---|---|---|---|---|
| 104946 | dark navy | 394 | 393 | +1 | 384-489, verified | 6.4 s |
| 114438 | dark navy | 524 | 524 | 0 | 514-619, verified | 8.1 s |
| 115105 | dark navy | 557 | 557 | 0 | 547-651, verified, clamped to clip end | 7.6 s |
| 105652 | dark navy, a blue/red swirl ball in hand at f0-64 | null | 312 | missed | none | 4.2 s |
| 111238 | black | null | 407 | missed | none | 5.0 s |
| 112413 (team-mate) | black | null | 310 | missed | none | 3.9 s |
| 111218 (2.6 s, `--no-cut`) | - | null, "too short: 2.65 s < 4.0 s" | - | - | - | 0.1 s |

**Colour caveat.** At release, 4 of the 6 balls look dark navy in the strips. This does not match the brief's green-skull ball for 114438 or red-swirl ball for 115105. Motion blur and the lighting may hide the colour, or the bowler may have used his own ball. So the colour-free mask was effectively tested on dark navy (4 clips) and black (2 clips), not on green or red. Runtime is 4-8 s per clip with the cut on these clips and 5-16 s on September; 0.1 s for a too-short clip.

### Why the 3 nulls failed

Diagnosis from the per-frame bands at the eye release:

- **111238 and 112413: upright head, dark gutters in the region.** The camera looks down the lane from standing height, so the black gutters run through rows 65-100 %. The mask baseline sits at mid 0.20-0.48 and bot 0.28-0.39 before, during and after release. The small ball (the far half of the lane is visible) never makes a blip: T at the eye release is -0.03 and -0.02. Both black-ball clips are also the two upright-view clips, so ball colour and view are confounded. Darkness alone would not cause it; the gutter baseline does.
- **105652: post gate.** The blip is there: bot 0.15 at 311-312, mid 0.17 at 313. But the region stays at about 0.14 from f314 on, presumably the left gutter entering the region as the head turns, so post reads 0.25-0.29 and T peaks at only +0.033.

### Post-hoc attempt, driven by 105652, 111238 and 112413 (not shipped)

I tried keeping only compact mask components (fill >= 0.5, aspect 0.5-2, area >= 6 px at 1/8 scale) to remove the diagonal gutter bands.

- **Recovered:** 105652's blip, with T 0.085 and post 0.0 at f313.
- **Broke:** earliest selection now picks walk-up or ball-return blobs at f5-f30 on 4/6 clips.
- **Did not recover:** 111238 or 112413, with T -0.01 and +0.02 at release.

It was reverted. This is a RULES.md rule 28 situation: any future rule fitted after reading these strips needs new untouched 2026-11-08 clips to test it. 26 of the 32 are still untouched.

### Lane thud on the new clips

A low-band onset falls 1-7 frames after the eye release on 5/6 clips; 115105 has none. Each clip has 10-21 low-band onsets, 7-17 of them more than 10 frames before release. So option (c), thud as the primary candidate, cannot select the release alone.

### Next step

These are untested proposals.

- **Make the region lane-relative instead of fixed rows.** Use track_v2's per-frame wood-mask gutter edges and measure the blip only on wood pixels between the gutters, near the bottom of the visible lane. This removes the gutter baseline that killed 111238 and 112413 and the gutter entry in 105652.
- **Re-test on fresh clips.** Freeze that rule on the 10 September clips plus these 6, then score it on 6 untouched 2026-11-08 clips the same way.
- **Do not batch blindly.** Until then, a batch run of the 32 clips will return null on upright-view throws. Every null needs an eye pass or a hand label.

---

*Round 1 below describes v1 and v2. v2, the purple mask with strongest-blip selection, is superseded by v3; its September numbers are identical to v3's.*

## Round 1 (2026-11-09): v1 jerk rule and v2 purple blip

**Headline.** The rule frozen on the 3 dev stems before holdout scoring (v1, first up-frame camera jerk) scored **3/7 on holdout** within 2 frames: 2 picks were 100+ frames late and 2 found nothing. The shipped rule (v2, purple bottom-of-frame blip) was built **after reading those holdout failures**. Its **10/10 within 1 frame** is an all-10 post-selection fit with no independent holdout left (loop-2 RULES.md rule 28). The next batch of new clips is the first real test of v2. Every v2 cut contains release-5 .. pin_row+15 and verifies at frame-0 offset 0. 191900 returns no cut.

### Usage

```
/Users/toka/code/bowling-app/analysis-engine/.venv/bin/python auto_cuts.py <source.mp4> [--out-dir DIR] [--no-cut]
python score_auto_cuts.py <entries_dir> [--shift-release N] [--set-cut-end STEM=FRAME] [--json OUT]
```

Default out-dir is `work/auto_cuts/` next to the script (`work/` is gitignored here). Entries for the 11 September clips are in `work/entries/` (v2) and `work/entries_v1/` (v1). Scores are in `work/score_v2.json` and `work/score_v1.json`. Sources: `~/Downloads/20260915_*.mp4`.

### Rule chosen (v2) and why

- **Release.** Purple mask (HSV hue 115-165, S > 40, V > 30) on the 1/8-scale frame. It is measured as a fraction in two row bands: bot = rows 80-100 %, mid = rows 65-80 %. At release the ball crosses the frame bottom in about one frame: it shows in bot at k-1/k, in mid at k, then is gone. The blip score is `T[k] = min(max(bot[k-1],bot[k]) - max(bot[k-3],bot[k+1],bot[k+2]), mid[k] - max(mid[k+1],mid[k+2]))`. Candidates need T >= 0.02 and mean(bot+mid) over k+1..k+3 < 0.03, meaning the ball has left the bottom 35 %. release = argmax T. No offset is applied.
- **Why this signal.** All 10 throws show the same one-frame transient, and it was the top-ranked T in every clip. The post gate removes the one false blip: 191900 f59 is the bowler lifting a ball off the return, filling the bottom of the frame.
- **No candidate means no cut.** The entry gets `cut_path: null` and a reason. The v1 jerk is attached as `jerk_release_candidate`, advisory only, never used to cut. A null is visible in a batch; a cut 100 frames late is not.
- **Thud.** A low-band (40-300 Hz) onset within release+1..+10 is a confidence tag (`blip+thud` vs `blip, no thud`). It never gates. 191820, the gutter ball, has no thud.
- **Rough pin hit.** The strongest mid-band (300-2000 Hz) onset within release+50..+130, minus 17. If there is none, release+60. The lag of 17 was fitted on dev, where crash minus pin_hit was 16-18.
- **Cut.** cut_start = release-10. cut_end = max(pin_hit+20, release+95), clamped to the clip, inclusive. The release+95 floor is a departure from the spec's plain pin_hit+20. It exists because late is free (track_v2 finds the pin row itself over the whole cut) and early is fatal. I had seen the loop-1 holdout crash fields and the truth pin_rows (up to release+75) when choosing 95 (RULES.md rule 23).
- **Cut mechanics.** `ffmpeg -i src -ss <pts[cut_start] - half a frame> -frames:v N -t (N+1)/fps -fps_mode passthrough -c:v libx264 -crf 18 -pix_fmt yuv420p -c:a aac`. That is output seek, so it is frame accurate, with no 120 fps duplication. The seek time comes from packet pts, because 191253's first pts are irregular. The check: decoded frame count = cut_end-cut_start+1, best frame-0 MAD offset = 0, MAD(0) < 3. Source frames are always read sequentially. Loop 1's exact encoder line is not recorded anywhere I found, so crf 18 is my choice. The MAD at offset 0 is 1.00-1.19 here against 0.74-0.83 in loop 1; offsets ±1, ±2 read 17-38.
- **Labels.** Release truth is the loop-1 `cuts.json` release_frame. The loop-2 truth files say 412 and 442 for 191820 and 191913, one frame later. pin_row is the loop-2 `pin_row_frame`, except 191820 (gutter, none), which uses cuts pin_hit+10 = 473.

### Per-stem results, v2 (superseded by v3, post-selection on all 10)

release_err = auto - label. pin_err = auto rough pin_hit - cuts.json pin_hit. need_end = pin_row+15. "w/o floor" asks whether pin_hit+20 alone would have contained the window.

| stem | split | label rel | auto | rel err | pin err | cut | need | margin | w/o floor | source | blip T | post |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 185121 | dev | 297 | 296 | -1 | +1 | 286-391 | 292-364 | +27 | yes | blip+thud | 0.032 | 0.001 |
| 185331 | dev | 298 | 298 | 0 | +1 | 288-393 | 293-365 | +28 | yes | blip+thud | 0.029 | 0.012 |
| 185645 | dev | 237 | 237 | 0 | -1 | 227-332 | 232-306 | +26 | yes | blip+thud | 0.053 | 0.015 |
| 185454 | holdout | 326 | 327 | +1 | -8 | 317-422 | 321-392 | +30 | **no** | blip+thud | 0.042 | 0.003 |
| 190115 | holdout | 390 | 390 | 0 | +8 | 380-485 | 385-458 | +27 | yes | blip+thud | 0.088 | 0.000 |
| 191253 | holdout | 377 | 377 | 0 | +2 | 367-472 | 372-444 | +28 | yes | blip+thud | 0.071 | 0.013 |
| 191820 (gutter) | holdout | 411 | 411 | 0 | +30 | 401-513 | 406-488 | +25 | yes | blip, no thud | 0.085 | 0.003 |
| 191913 | holdout | 441 | 442 | +1 | -7 | 432-537 | 436-507 | +30 | yes | blip+thud | 0.046 | 0.001 |
| 192142 | holdout | 415 | 416 | +1 | +2 | 406-511 | 410-505 | **+6** | **no** | blip+thud | 0.052 | 0.002 |
| 192636 | holdout | 391 | 392 | +1 | -25 | 382-487 | 386-476 | +11 | **no** | blip+thud | 0.106 | 0.001 |
| 191900 (no throw) | - | none | none | - | - | no cut | - | - | - | null, reason given | top T 0.092 at f59, post 0.47 | |

Summary table:

| split | n | release abs err mean / max | pin abs err mean / max | contains | verified |
|---|---|---|---|---|---|
| dev | 3 | 0.33 / 1 | 1.0 / 1 | 3/3 | 3/3 |
| holdout (post-selection) | 7 | 0.57 / 1 | 11.7 / 30 | 7/7 | 7/7 |

### v1 (frozen on dev before holdout scoring): the only clean holdout number

The rule: first run of frames with phase-correlation dy < -12 (1/8 scale, Hanning window), release = argmin - 1. Dev was exact: -1, 0, 0.

| stem | split | rel err | what happened |
|---|---|---|---|
| 185121 / 185331 / 185645 | dev | -1 / 0 / 0 | ball sweeping up through the frame bottom drags the whole-frame shift |
| 190115 | holdout | 0 | as dev |
| 191820 | holdout | 0 | as dev |
| 192636 | holdout | +2 | as dev |
| 191253 | holdout | +103 | no jerk at release; the first jerk was the post-pin camera whip |
| 191913 | holdout | +127 | same: post-pin whip |
| 185454 | holdout | missed | no frame below dy -12 anywhere (min -3.6) |
| 192142 | holdout | missed | no frame below dy -12 anywhere (min -6.1) |
| 191900 | no throw | correct null | no jerk |

Holdout: 3/7 within 2 frames, 3/5 cuts containing the window, 4/5 verified. The fifth, 191253, lost its last frame to `-shortest` at the clip end; that bug is fixed. v1 also showed the jerk is a post-pin whip detector as often as a release detector (185645 f336 on dev was already one). It now survives only as the advisory `jerk_release_candidate`.

### Slack in the v2 thresholds

This is the whole case for v2 generalising.

- **Blip T >= 0.02.** The weakest true release is 0.029 (185331). The strongest non-adjacent rejected candidate that passed the post gate is 0.011 (192142 f516).
- **Post < 0.03.** The largest true release value is 0.015 (185645). The one negative example, 191900 f59, reads 0.47. The post gate is fit against exactly one no-throw clip.
- **Runner-up ratio.** The closest runner-up anywhere is 191913: 0.046 at release against 0.029 at f102, which the post gate also rejects at 0.28.

### Mutation checks (all observed to fail as they should)

| mutation | expected | observed |
|---|---|---|
| `--shift-release 8` | every release error moves by +8, cut_start follows, contains fails | -1 to +7, 0 to +8, +1 to +9 on every row; contains 0/3 dev, 0/7 holdout |
| `--set-cut-end 192142=500` (pin_row 490 + 10) | contains False on that stem | False, margin -5; holdout contains 6/7 |
| 3 s `ffmpeg -t 3 -c copy` trim of 190115 | "too short" | `too short: 3.02 s < 4.0 s`, cut_path null |
| 191900 end to end | null with reason | null, "no release found …" |
| 191253 truncated to 450 frames | cut clamped to the clip end and still verified | cut 367-449, 83/83 frames, verified, note "cut_end clamped" |

The truncated-clip run also exposed and fixed a bug. When `--out-dir` equals the source folder, the cut path equalled the source path and ffmpeg refused. It now writes `<stem>_cut.mp4`.

### What failed or is weak

- **v1 jerk rule.** See above.
- **Rough pin hit.** Holdout abs error is 11.7 mean and 30 max. The crash onset ranges from 8 frames before pin_hit (192636: probably a neighbour's crash, -25) to 30 after on the gutter ball, which has no crash. The release+95 floor carries containment on 185454, 192142 and 192636. 192142's margin is only 6 frames. A ball slower than about release+80 to the pin row would end the cut early on a clip whose crash onset is also early. track_v2 reads `pin_hit_frame` for its jump rule and its no-crossing fallback, so a -25 rough pin hit matters there even when the cut is fine.
- **Encoder.** Loop 1's cut encoder settings were not recorded. Mine give MAD(0) 1.0-1.2 instead of 0.74-0.83, still far from ±1 (17+).

### Not tested

- **Any clip outside these 11.** v2 has no independent holdout.
- **Another ball colour.** The hue window 115-165 is this bowler's purple ball. A different ball, a different glasses resolution (the rule runs at 1/8 scale with fixed row bands), or a release that never crosses the bottom 35 % of frame is untested. All of these would give a null, by design.
- **Multiple throws in one clip.** v2 takes the strongest blip. A clip with two throws gets one cut.
- **Untested branches.** The no-audio path and the no-crash fallback (release+60) were exercised only by the truncated clip, where the crash window ran past the end.
- **Downstream.** Running track_v2 on the auto cuts was not done.
- **Runtime.** Per-clip runtime was not measured.
