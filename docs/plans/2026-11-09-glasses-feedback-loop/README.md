# Glasses feedback loop: staged roadmap (2026-11-09)

Goal: per-throw bowling feedback from the Meta glasses, fewer manual steps, less waiting. **V** = read or fetched; **I** = inferred. All feedback times are I; only the 11-08 manual path was timed.

**Judge split.** Judge 1 picked `design-session`, judge 2 `design-now` (25.5 vs 26). Both share the post-Drive pipeline; only the manual upload is proven (V, 11-08). Stage 1 is that pipeline; the sync hop is a gated graft.

## 1. Today (`current-pipeline-steps.md`, V)

| step | actor | min |
|---|---|---|
| Record one clip per throw | Tom | ~5 s each |
| Fold glasses, Meta import to phone | Tom/app | unknown |
| Wait for a laptop session | Tom | ~1300 |
| Upload 32 clips to Drive | Tom | ~6 |
| Prompt Claude, approve | Tom | ~7 |
| Release eye-reads, bowler/game map | agent | ~87 |
| Judge, amend, rerun loop | agent | ~180 |
| Render, critic, re-render, upload | agent | ~25 |
| Watch, ask "why no line" | Tom | ~3 |

Tom: ~15 hands-on min, ~27 h wait. Latest: 20 of 31 pass, 11 video-only (`docs/research/2026-11-09-glasses-pov-session/README.md:6`; round 3 was 18 and 13).

## 2. Target flow

| step | who |
|---|---|
| Record a clip per throw, say "Tom, game two" at the start | human, ~1 s |
| Fold glasses; sync app pushes clips to the Drive inbox | machine (Stage 2) |
| Inbox watch, download, md5 dedupe | machine |
| Cuts, vision release read, audio + tracker cross-checks | machine |
| STT bowler tag with gap/lane inheritance | machine |
| Tracker pass loop, frozen code judge | machine |
| Cards with one fixed fail sentence, publish, one digest email | machine |
| Open the link; tap a release only for `unresolved` throws | human |

Expected: ~90 min after clips land, ~2 h after the last throw, Mac awake (I). Per-throw needs Stage 3.

## 3. Stages

### Stage 1: this week. Verified pieces only; removes the trigger wait and ~3.5 h of agent work
- **Deliverable.** The Drive folder is the start button. A launchd worker lists it with Tom's user token (`docs/sessions/2026-11-07-glasses-pov-hook-loop.md:42`), skips `.adding` names, downloads with md5 check, runs cuts, tracker, judge and render, publishes to GCS with a short link and one email.
- **Files.** New `tools/pov/`: `pov_worker.sh` + plist, `judge_session.py`. Commit `work/judge_r1/judge_rules.py`, `work/judge_r4/rules.py`, `work/cuts/tools/grid.py` out of gitignored `work/`. `make_session_video.py`: argparse, `VIDEO_ONLY` from the judge file. Make `auto_cuts.py:33 FF` and `track_v3.py:57-58 S,Q` arguments. Publish via `upload_routes.py:173`, `short_link_routes.py:65`, `analysis_notify.py:133-208`.
- **Side tests, no code.** Day 1: settle both phone OSes. Then 5 clips via Autosync/FolderSync (Android) or Shortcuts/osxphotos (iPhone): time to Drive, md5 vs phone copy. Pass: 5 of 5 within 30 min, md5 equal.
- **Proof.** Re-upload the 11-08 clips to a fresh inbox; an emailed link arrives unprompted with the same 20 of 31 verdicts.
- **Not fixed.** Tom still uploads. Mac must be awake. No release read, so uncut throws render video-only. Bowler by clip order only.

### Stage 2: the pipeline's human steps
- **Deliverable.** `release_read.py`: overview + fine grid via `grid.py`, two pinned vision calls, accepted only if the crash onset sits in release+50..+130 (`auto_cuts.py:24`) and the tracker seed in release+1..+15, else `unresolved`. `tag_read.py`: STT on the first 4 s, inheritance under 3 min with lane alternation. Judge frozen with the 12:50 and 17:40 amendments disclosed. One fixed sentence per fail class on every card. Per-attempt emails suppressed. Release-tap strip for `unresolved` only (`bowling_routes.py:437`, `:696`). Adopt the sync hop if its test passed.
- **Files.** `tools/pov/release_read.py`, `grid_write.py`, `tag_read.py`. `analysis_dispatch.py:34` gains `kind='bowling-pov'`, covering `/reanalyze` (`bowling_routes.py:370`) too, or tapped throws hit the old `/analyze`. Enable the `drive` and `cloudscheduler` APIs only if ingest leaves the laptop (V: disabled).
- **Proof.** Release read on the 82 grids on disk vs `work/cuts/eye_releases.json`: >= 28 of 31 within +-2 frames, no silent miss over 5, as-first-run number. No GPU.
- **Not fixed.** J2 pin-row crossing, the dominant fail. Validation is model vs model. STT in alley noise untested.

### Stage 3: glasses-side integration, gated
- **Deliverable.** The twin-clip spike only: build the DAT CameraAccess sample, record 5 throws at 720x1280 `hvc1` beside the native clips, run Stage 1 on both. Android first: the iOS sample ends on backgrounding (V). Kill: stream clips pass J1-J5 on fewer than 3 of 5 while natives pass 3+, or no ball found in 2+. No app before that number.
- **Verified.** DAT 1.0 shipped, Developer Mode for unpublished apps, 720x1280 cap over Bluetooth, capture-button Inputs experimental: https://developers.meta.com/wearables/faq/ , https://wearables.developer.meta.com/docs/develop/dat , https://github.com/facebook/meta-wearables-dat-ios , https://github.com/facebook/meta-wearables-dat-android . Auto-import needs folded or cased glasses: https://www.meta.com/help/ai-glasses/1510723473009423/
- **Not fixed.** Release detection, J2, battery, TTS to the glasses (all UNV).

## 4. Decisions only Tom can make
1. Which phone, yours and Chardie's? Decides the sync tool and DAT platform.
2. Will you speak the tag? If not, bowler stays a per-game tap.
3. Cards say "Chardie" or the monitor's "Chris"?
4. Mac awake ~90 min per session, or pay for Cloud Run CPU (SAM 2 CPU time unmeasured)?
5. Adopt the round-4 extrapolated crossing as a labelled rule, or drop it?
6. Pay for Autosync if the free tier caps file size?

## 5. Dropped claims
- "`auto_cuts` writes a release strip": no `imwrite` (V); grids came from `work/cuts/tools/grid.py`.
- "Judge files not found": they exist at depth 6.
- "`/reanalyze` as is" and "`enqueue('bowling')` then a POV worker picks it": both route to the old `/analyze`.
- iOS pocket recording: contradicted by the sample README.
- "Drive API enabled on `toms-gym`": false (V).
- "Phone is Android", "Autosync caps at 10 MB", "import takes 10-30 min", "400x faster": unsourced; no gate uses them.
