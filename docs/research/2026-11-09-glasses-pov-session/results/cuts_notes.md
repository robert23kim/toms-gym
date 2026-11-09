# Cuts stage, 2026-11-08 session (written 2026-11-09)

Quarantine: this stage did not open /Users/toka/pov-holdout/2026-11-09-glasses-pov-session. Every release below was read from the source clips by eye.

## 1. Honest test of v3 on the 26 untouched clips (frozen number, written before any code change)

v3 = `auto_cuts.py` as left by the previous stage (backup of that exact file: `work/auto_cuts.v3.orig.py`). The only change made before this run is the `--release` override, which does not touch the detection path. Run: `work/cuts/run_auto.sh`, entries in `work/cuts/entries_auto/`.

**Of the 25 untouched throw clips, v3 got 4 right (within 1 frame), 6 wrong and 15 null. 111218 returned "too short", which is correct.**

The claim that "a null is visible, a wrong cut is not" failed. All 6 wrong picks came back `verified: true` with a cut.

| clip | v3 auto | eye release | error | what v3 picked |
|---|---|---|---|---|
| 110622 | 370 | 370 | 0 | the release |
| 114059 | 554 | 554 | 0 | the release |
| 114810 | 601 | 600 | +1 | the release |
| 115157 | 498 | 498 | 0 | the release |
| 111420 | 346 | 239 | +107 | the walk back after the throw, 12 frames from clip end (no thud, pin = release+60, cut clamped) |
| 112638 | 555 | 343 | +212 | hand over the approach after the throw, 7 frames from clip end |
| 112800 | 358 | 252 | +106 | walk back, 27 frames from clip end |
| 113113 | 431 | 301 | +130 | walk back, 19 frames from clip end |
| 113716 | 584 | 482 | +102 | walk back, 12 frames from clip end |
| 112146 | 151 | 333 | -182 | head tilting down before the approach, no ball in frame |
| 15 clips | null | read by eye | - | 104714 105322 105857 110224 110442 110713 110948 111631 111941 112936 113541 113911 114236 114631 114919 |

The tell for the 5 late picks is that all of them have `release is within 45 frames of the clip end` in their notes, 4 of the 5 have no thud, and all 5 have their rough pin hit at release+60 because there was no crash onset.

## 2. What changed in auto_cuts.py

Both changes are in `auto_cuts.py`. The diff is against `work/auto_cuts.v3.orig.py`.

- **`--release N`.** This skips detection and cuts from frame N with the same mechanics: `release_source: "eye"`, the audio pin hit, `cut_start = N-10`, `cut_end = max(pin+20, N+95)` clamped to the clip, and the same frame-0 MAD check. The detection path was refactored without changing behaviour; the September releases are identical. In eye mode the decoded frame count trims `n`, so a cut clamped to the clip end never asks for a frame that does not exist.
- **v3.1, the clip-end gate `MIN_ROLL = 45`.** A blip candidate must now sit at least 45 frames before the last frame. This was triggered by the spot-check rule: 2 or more auto reads were off by more than 3 frames. It is a **post-hoc fit with no holdout**, because by then I had viewed all 32 clips.
  - Why 45: the 5 late wrong picks sat 7-27 frames from the clip end. The correct new picks sat 95-152 frames from it. September's smallest margin is 110.
  - No threshold, mask or selection rule was touched.
  - It turns the 5 late picks into **nulls, not hits**. The true release was never a candidate on those clips.
  - It does not catch 112146, the early wrong pick, so that clip is overridden by eye.
- **September regression run.** v3.1 was re-run on the 11 September clips (`work/entries_v31_sept/`). Releases were identical to v3 (296, 298, 327, 237, 390, 377, 411, null, 442, 416, 392).
- **The guard was seen to fire.** v3.1 on the 32 new clips (`work/cuts/entries_v31/`) returned the 5 late-pick clips as null.

**v3.1 on the 25 throw clips that were untouched before this stage:** 4 right, 1 wrong (112146), 20 null. On all 31 throws: 7 right, 1 wrong, 23 null. This is a post-selection number.

## 3. Final cuts (`work/cuts/cuts.json`, loop-1 format plus provenance fields)

- 31 throw clips: all have a cut, and 31/31 are `verified` (frame count matches, best frame-0 MAD offset 0).
- 111218 has `cut_path: null` with "too short: 2.65 s".
- Release source: 7 clips use the auto release because it is within 1 frame of the eye read (104946, 110622, 114059, 114438, 114810, 115105, 115157). The other 24 use `--release` from the eye read, including the 6 former wrong picks.
- Eye releases are in `work/cuts/eye_releases.json`. 105652, 111238 and 112413 reuse the previous stage's eye reads (312, 407, 310).
- Grids are in `work/cuts/grids/`: `ov*` is a whole-clip overview at 1 frame per 0.5 s, `fn*`/`zz*` are frame-by-frame, `au*` is auto-6..+6, and `spotcheck.jpg`.
- Convention: the ball enters the frame bottom at X and is on the lane with the hand trailing at X+1, so release = X+1.
  - On upright views (111631, 112936 and other black-ball clips) the ball first appears already clear of the hand. There I took the first frame in which it is on the lane.
  - Expect ±1 on 110224, 110442 and 110948, where a faint smudge at the bottom edge one frame earlier may or may not be the ball.

| clip | split | ball | v3 auto | v3.1 auto | eye | final release (source) | pin_hit rough | cut | frames | verified | notes |
|---|---|---|---|---|---|---|---|---|---|---|---|
| 104714 | truth | blue-purple | None | None | 311 | 311 (eye) | 350 | 301-406 | 106 | True |  |
| 104946 | dev | blue-purple | 394 | 394 | 393 | 394 (auto) | 455 | 384-489 | 106 | True |  |
| 105322 | rest | blue-purple | None | None | 380 | 380 (eye) | 445 | 370-475 | 106 | True |  |
| 105652 | dev | blue-purple | None | None | 312 | 312 (eye) | 375 | 302-407 | 106 | True |  |
| 105857 | rest | blue-purple | None | None | 427 | 427 (eye) | 489 | 417-522 | 106 | True |  |
| 110224 | truth | blue-purple | None | None | 373 | 373 (eye) | 435 | 363-468 | 106 | True |  |
| 110442 | dev | blue-purple | None | None | 357 | 357 (eye) | 421 | 347-452 | 106 | True |  |
| 110622 | rest | blue-purple | 370 | 370 | 370 | 370 (auto) | 472 | 360-492 | 133 | True |  |
| 110713 | rest | blue-purple | None | None | 324 | 324 (eye) | 388 | 314-414 | 101 | True | cut_end clamped to the clip end f414 |
| 110948 | rest | blue-purple | None | None | 264 | 264 (eye) | 326 | 254-359 | 106 | True |  |
| 111218 | rest | unknown | None | None | None | None (-) | None | none | None | False | too short: 2.65 s < 4.0 s |
| 111238 | truth | black | None | None | 407 | 407 (eye) | 453 | 397-502 | 106 | True |  |
| 111420 | truth | black | 346 | None | 239 | 239 (eye) | 297 | 229-334 | 106 | True |  |
| 111631 | dev | black | None | None | 296 | 296 (eye) | 358 | 286-391 | 106 | True |  |
| 111941 | rest | black | None | None | 342 | 342 (eye) | 401 | 332-437 | 106 | True |  |
| 112146 | rest | black | 151 | 151 | 333 | 333 (eye) | 384 | 323-428 | 106 | True |  |
| 112413 | rest | black | None | None | 310 | 310 (eye) | 371 | 300-405 | 106 | True |  |
| 112638 | truth | black | 555 | None | 343 | 343 (eye) | 401 | 333-438 | 106 | True |  |
| 112800 | dev | black | 358 | None | 252 | 252 (eye) | 310 | 242-347 | 106 | True |  |
| 112936 | rest | black | None | None | 455 | 455 (eye) | 511 | 445-550 | 106 | True |  |
| 113113 | rest | black | 431 | None | 301 | 301 (eye) | 356 | 291-396 | 106 | True |  |
| 113541 | rest | blue-purple | None | None | 538 | 538 (eye) | 600 | 528-633 | 106 | True |  |
| 113716 | truth | blue-purple | 584 | None | 482 | 482 (eye) | 544 | 472-577 | 106 | True |  |
| 113911 | dev | blue-purple | None | None | 457 | 457 (eye) | 518 | 447-536 | 90 | True | cut_end clamped to the clip end f536 |
| 114059 | rest | blue-purple | 554 | 554 | 554 | 554 (auto) | 614 | 544-649 | 106 | True |  |
| 114236 | rest | unknown | None | None | 349 | 349 (eye) | 410 | 339-435 | 97 | True | cut_end clamped to the clip end f435 |
| 114438 | rest | blue-purple | 524 | 524 | 524 | 524 (auto) | 584 | 514-619 | 106 | True |  |
| 114631 | dev | blue-purple | None | None | 517 | 517 (eye) | 578 | 507-612 | 106 | True |  |
| 114810 | rest | blue-purple | 601 | 601 | 600 | 601 (auto) | 661 | 591-696 | 106 | True |  |
| 114919 | rest | blue-purple | None | None | 611 | 611 (eye) | 671 | 601-706 | 106 | True |  |
| 115105 | rest | blue-purple | 557 | 557 | 557 | 557 (auto) | 596 | 547-651 | 105 | True | cut_end clamped to the clip end f651 |
| 115157 | dev | blue-purple | 498 | 498 | 498 | 498 (auto) | 561 | 488-593 | 106 | True |  |

## 4. Spot check: every 5th stem

The rule: indices 0, 5, 10, 15, 20, 25 and 30 of the 32 stems in time order, with 111218 dropped. I extracted source frames from release-6 to release+6 (the final release) as a strip and read it (`work/cuts/grids/spotcheck.jpg`).

| clip | v3 auto | v3.1 auto | eye_release (strip) | final | auto error |
|---|---|---|---|---|---|
| 104714 | null | null | 311 | 311 eye | - (null) |
| 110224 | null | null | 373 | 373 eye | - (null) |
| 112146 | 151 | 151 | 333 | 333 eye | -182 |
| 113113 | 431 | null | 301 | 301 eye | v3 +130 |
| 114236 | null | null | 349 | 349 eye | - (null) |
| 115105 | 557 | 557 | 557 | 557 auto | 0 |

Of the 3 clips with an auto read, 2 are off by more than 3 frames, so the fix-and-rerun clause fired (section 2). The real test is the full 13-row auto-vs-eye table in section 1, together with the 3 seen clips: 104946 at +1, 114438 at 0 and 115105 at 0.

## 5. Ball colour (`results/clips.json`) and split (`results/split.json`)

**Sampling deviates from the brief.**
- **What the brief asked for, and why it failed.** The brief's in-hand sample (the largest round low-texture blob in the bottom third, 0.5 s .. release-10) picked the wrong thing:
  - 104714: the bowler's black trousers (roundness 0.59-0.65).
  - 110224: the ball-return hood (roundness 0.83).
  - 105322: nothing; the red/black in-hand look fails the texture gate.
- **What I did instead.**
  - `ball_hsv` / `ball_lab` are the on-lane ball at release+1..+5: the round "not lane" blob below 30 % of the frame, eroded, median.
  - The in-hand sample is still recorded (roundness ≥ 0.8) as `inhand_hsv` / `inhand_lab`, and is used only as a fallback.
  - `ball_sample_source` says which one was used. The in-hand reads are mostly V 13-32 and are not usable.
- **Label rule (OpenCV HSV, Lab 0-255).**
  - Chroma < 10 is `black` if V < 70, otherwise `other`.
  - Otherwise H < 10 or ≥ 160 is `red`, 35-85 is `green`, and 95-160 is `blue-purple`.
  - `ball_dark` = V < 70.
- **Eye overrides (4).** Checked against the tile contact sheet `work/cuts/colour/tiles.jpg`; recorded as `ball_label_auto` / `ball_label_note`. The tile shows only the first sampled frame, so 112638 was judged from the release grid.
  - 111238, 112638 and 113113: median polluted by a mispick, so set to `black`.
  - 114236: `unknown`. The ball is never visible after release; the sampled dark blob is a shoe.

**Clusters:** blue-purple (dark navy, H 125-134, V 48-63) has 20 clips, black has 10, unknown has 1. The black-ball clips are contiguous, 111238-113113, and every one of them is the upright view, so ball colour and view are confounded. Observed: no green or red ball appears on the lane in any of the 31 throws. The ball-return rack at clip start holds red and green balls, and the navy ball reads as a red swirl under the hand at clip start (105322, 110224). Whether the brief's green/red balls were ever thrown is not established.

**Split.**
- **Truth:** the first stem of each cluster in time order (104714 navy, 111238 black), then the 1-based every-5th stem of the remaining 29 throws: 110224, 111420, 112638, 113716.
- **Dev:** every 4th non-truth throw stem from index 0 gives 7 stems (104946, 110442, 111631, 112800, 113911, 114631, 115157). 25 non-truth throws cannot yield 8 at every 4th, so it is topped up from index 2 (105652).
- **Rest:** the other 18, including 111218.

## 6. Failures and flags for later stages

- **v3 produced 6 confident wrong cuts on 25 untouched throws** (section 1). The post-hoc gate fixes 5 of them by turning them into nulls. 112146 is still a wrong auto pick: a head-down blob at f151, about 180 frames before the throw.
- **114236 (rest):** after release the arm covers the ball, and frames 352-364 look at the feet. The ball is not visible on the lane from 367 onwards at grid scale. The roll is probably untrackable.
- **Rough pin hit:** it is release+60 (no crash onset) on several eye clips, so the pin_row must come from track_v2.
- **Cuts clamped to the clip end:** 110713, 113911 (90 frames, 79 after release), 114236 and 115105.
- **112936:** the throw is late (release 455). The ball held at 418-433 is not the release.
- **Quarantine:** /Users/toka/pov-holdout/2026-11-09-glasses-pov-session was not opened by this stage.
