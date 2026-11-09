# Judge 2 of 2: Tom's time (2026-11-09)

Angle: count only minutes Tom spends or waits. Unattended compute is free. Agent eye-reads and judge rounds already cost Tom zero minutes today, so a design that turns them into Tom taps adds cost. Folding the glasses (happens anyway) and one press per throw (Tom already does it today) count as neither added nor removed.

Tags: **V** = I read the file, ran the check, or read a fetched page this pass. **I** = my inference.

## Verdict
**Winner: design-now, with session's vision release read and voice tag grafted in.** Plain sums: now 13, session 12.5, toolkit 11 (0-20). With steps and time-to-feedback weighted x1.5 for this angle: now 16.5, session 15.25, toolkit 15. Design-now is the only one that removes Tom as the *trigger*. That trigger is what the 21.6 h was. Its weak point is that it adds about 2 min of Tom taps per session, and session's vision read removes them.

## Tom-minutes per 31-throw session (recurring, I unless marked)
Baseline, today: about 15 min of hands-on work (V, pipeline doc). That is about 6 min of Drive upload wall time, about 7 min of prompting and approving, and about 3 min of watching. On top of that he waited 21.6 h and then about 6 h.

| design | Tom adds per session | Tom removed | who starts the pipeline | wait after the last throw |
|---|---|---|---|---|
| now | release taps on nulls: about 60 % x 31 x 5 s, so about 1.6 min, plus opening the page, about 1 min. Wearer tag about 3 x 10 s. **Total about 3 min.** | upload, prompt, approve (about 12 min) | **machine** (fold, then sync, then a Scheduler tick) | 90-150 min with the Mac awake (I, the design's own table). Import latency is UNV. |
| toolkit | open the app, sign in, pick the lane: about 1 min. Handover tag when Chardie bowls: about 30 s. Optional release taps: about 0.5-1 min. A weekly Xcode re-sign (about 5 min/week) **if** the phone is an iPhone. **Total about 2-3 min**, plus the re-sign. | fold/import, upload, prompt, approve | machine, per throw | 3-5 min per throw (I). Needs the 720p stream to pass, a live home-laptop worker, and the dispatch fix below. The session video still comes after the session. |
| session | voice tag about 1 s x 31, so about 0.5 min. The phone upload stays: about 1-2 min of active selecting (I; 6 min wall, V). **Total about 2 min.** Zero taps if the vision read passes. | prompt, approve, all agent stages | **Tom** (upload) | about 90 min after the upload lands. The upload happens whenever Tom does it, so on 11-08 the gap was overnight (I). |

All three run compute on the laptop in phase 1. Every wait above assumes the Mac is awake and polling. Design-now says this plainly. Toolkit's "3-5 min" assumes a home worker is live during the game and does not list "keep the Mac awake" as a manual step.

## Scores (0-5; accuracy: higher = lower risk)

| design | steps removed | time to feedback | feasible now | accuracy risk | sum |
|---|---|---|---|---|---|
| now | 4 | 3 | 3 | 3 | **13** |
| toolkit | 4 | 4 | 2 | 1 | 11 |
| session | 3 | 2.5 | 4 | 3 | 12.5 |

Why each score:
- **now.**
  - Steps 4: removes the whole trigger chain, but adds about 3 min of taps.
  - Time 3: per batch, 90-150 min, and nobody has to start it.
  - Feasible 3: each piece exists, but the Meta-import plus Autosync chain is documented only by third parties (options doc B). Drive access by the runtime service account is UNV, while the user-token path works today (V, 11-07 session doc:42).
  - Accuracy 3: Tom's taps are real labels for the nulls, but wrong cuts still pass as `verified: true`.
- **toolkit.**
  - Steps 4: removes import, upload and prompt.
  - Time 4: it would be 5 for a per-throw spoken board, but the laptop gate, results arriving 1-2 throws late, and the misrouted dispatch (refuted below) cut it.
  - Feasible 2: needs a native app on experimental Inputs (V `android_CHANGELOG.md:22`, header `:8`). Inputs must also be enabled for the app in Wearables Developer Center (V `ios-inputs.md:8`), which the design does not list. The 720p kill test has not run, and the phone OS is unresolved. Its own estimate is 3-4 weeks.
  - Accuracy 1: Bluetooth-compressed 720x1280 input against a tracker tuned on 1184-1424 px clips. J2 is likely worse (I). The auto-stop depends on audio that is either experimental (glasses) or muffled (pocketed phone).
- **session.**
  - Steps 3: keeps the manual upload, which is the trigger.
  - Time 2.5: about 90 min, but the clock starts only when Tom uploads.
  - Feasible 4: everything is on the laptop with existing scripts (all verified below), and the validation set is on disk. The vision read is untested.
  - Accuracy 3: two cross-checks catch gross misreads, but its validation is model against model. Wrong-but-consistent reads pass silently. STT on alley audio is untested. The post-hoc amendments get frozen into the rules.

## Refuted claims

### design-now
1. **`/reanalyze` reused "as-is" to re-queue a tapped throw (step 9, reuse table).** Refuted, V. `bowling_routes.py:370-393` sets `queued` and calls `enqueue_analysis_job('bowling', result_id)`. In tasks mode that goes to `/jobs/bowling/<id>`, then `bowling-service /analyze` with a 360 s timeout (V `bowling_processor.py:170-174`). That is exactly the path the design's own step 5 says a POV clip must never take. The `bowling-pov` kind has to cover reanalyze too, or every tapped throw goes to the old analyzer.
2. **"the release strip `auto_cuts` already writes" (accuracy section).** Refuted, V. `auto_cuts.py` has no `imwrite`, `jpg` or `png`, so it writes no images. The 82 grids came from `work/cuts/tools/grid.py` (35 lines, argparse, `cv2.imwrite`) and `stack.py`. Both are under `work/`, which is gitignored (V `.gitignore:1:work/`). Usable, but not from `auto_cuts`.
3. Not refuted, but unsourced: "Meta import of about 1 GB, 10-30 min". The options doc marks import latency UNV, and the 10-30 figure has no source.
4. Not refuted, but still I: "Tom's phone is Android". The clip's `ftyp` is `isom/iso2/mp41`, with the tag string `app=Meta AI&device=Meta Smart Glasses` (V, read from the first and last 400 KB of `20261108_104714_593f3a1d.mp4`). Neither names an OS.
5. Verified, not refuted:
   - `run.py:437 --no-sam`
   - `auto_cuts.py:33 FF='/opt/homebrew/bin/'`
   - `track_v3.py:57-58 S/Q`
   - `make_session_video.py` hard-codes `CLIPS` and `VIDEO_ONLY` and has no argparse
   - routes at `:32/179/225/370/437/545/696`
   - `upload_from_string` at `:127`
   - the `enqueue_analysis_job` whitelist at `analysis_dispatch.py:34`
   - `drive_list.json` has 32 entries carrying `md5Checksum`
   - `Dockerfile.gpu` "DRAFT ... UNTESTED"
   - `deploy.sh` 8 CPU / 8 Gi / 600 s
   - L4 quota pending since 2026-06-07 (memory)
   - `_generate_code` is defined in `short_link_routes.py:43` and imported by `analysis_notify.py:35`, so the reuse works

### design-toolkit
1. **"a depth-4 find did not locate `judge_rules.py`/`rules.py`; reusable as a spec, not a file" (section 6).** Refuted, V. `work/judge_r1/judge_rules.py` (79 lines), `work/judge_r3/rules.py` (61) and `work/judge_r4/rules.py` (62) exist. The find was a level too shallow. The real caveat is that they are gitignored and not committed.
2. **Step 5 then step 6: `enqueue_analysis_job('bowling', id)`, then "a POV worker picks the task".** Refuted, V. A Cloud Task is an HTTP POST to `/jobs/bowling/<id>` (`analysis_dispatch.py:45`, `jobs_routes.py:93 run_bowling_job`). It runs the old analyzer, and a laptop watcher cannot "pick" it. A new kind or a non-dispatched status is needed.
3. **"the release-6..+6 strip `auto_cuts` already writes" (section 8.1).** Refuted, V (same check as now #2).
4. **Step 1, "phone goes in a pocket", with week-1 item 2, "build the CameraAccess sample unchanged".** Refuted for iOS, V. The current iOS sample README says "Backgrounding the app ends the active preview session" (`ios-sample-CameraAccess.md:12`) and "If the app backgrounds while previewing or recording, CameraAccess ends the active session" (`:47`). On iOS the unchanged sample fails the pocket test by design. On Android the 0.9.0 changelog has only "continuing while the app is backgrounded" (V `android_CHANGELOG.md:58`) and no "ends session" line. The section 7 UNV-1 text cites iOS 0.9.0 as if it applied to both platforms.
5. Minor: `upload_routes.py:183 _generate_signed_upload_url`. The def is at `:173` (V).
6. Verified, not refuted:
   - Android 1.0.1 is dated 2026-10-09 and 1.0.0 is dated 2026-09-24 (V, fetched)
   - Inputs exists with `CapturePressType` and is experimental (V, Android `:22`, iOS inputs skill `:28`, `:54`)
   - 720x1280 high resolution (V, Android `:217`)
   - camera audio streaming is experimental (V, Android `:27`)
   - `auto_cuts` has `audio_rises`, `onsets` and `CRASH_LAG` (V `:43`, `:89`, `:114`)
   - The "400x" comparison is conceded in its own addendum.

### design-session
1. **"82 such JPGs exist in `work/cuts/grids/` but no script that wrote them survives".** Refuted, V. `work/cuts/tools/grid.py` (argparse: `src out --frames --every --range --tw --cols`, `cv2.imwrite`) and `stack.py` survive. Most of `grid_write.py` is already written, which lowers its cost.
2. Verified, not refuted:
   - `auto_cuts.py` writes no grids
   - `eye_releases.json` is a dict of 31
   - `judge_rules.py` has 79 lines and `judge_r4/rules.py` has 62
   - SAM 92.6 of 119.2 s on 112413 (V `work/rerun_r2_r4.log:459`)
   - `--no-sam` exists
   - `run.py:30-32` hard-codes `S/L1/L2`
   - the crash window release+50..+130 (V `auto_cuts.py:24`)
   - `.claude/workflows/bowling-pov-session.js` exists
   - the Drive auth recipe at `docs/sessions/2026-11-07-glasses-pov-hook-loop.md:42`
   - the `upload_routes.py:173-192` signed URL and `public_url`
   - `analysis_notify.py` has `_create_short_link`, `_send_ready_email` and `notify_analysis_complete`
3. Not refuted, but a gap: the judge and grid code it reuses lives in gitignored `work/`. Item 7 (copy into `tools/pov/`) covers it only if it lands first.
4. The design makes no glasses or Meta-app capability claims beyond auto-import (V, options doc A), because it keeps the transfer.

## Grafts onto design-now
1. **From session: the vision release read** (`release_read.py`, crash onset inside release+50..+130 and a tracker-seed cross-check), built on the existing `work/cuts/tools/grid.py`. Taps stay only for `unresolved`. This moves about 1.6 min per session off Tom. Validate first on `work/cuts/eye_releases.json` against the grids on disk. That needs no GPU or video decode, so it can run while the tracker batch runs (I).
2. **From session: the spoken tag at clip start** ("Tom, game two") read by STT, with gap and lane inheritance. It replaces the per-game wearer taps and settles "Chris" vs "Chardie".
3. **From session: its payback order.** Build the trigger and publish first, then the judge freeze with the post-hoc amendments disclosed.
4. **From toolkit: a fixed sentence per fail class** on every card ("ball lost before the pins", "no pin row seen", "release not found"). This answers Tom's 17:29 question with no extra Tom time.
5. **From toolkit: its kill-criterion style for week 1.** Keep the DAT 720p twin-clip spike as a deferred side test on Android, where no source contradicts background recording. It is the only route to per-throw feedback.
6. **Fixes both designs need:** a `bowling-pov` dispatch kind that also covers `/reanalyze`, and committing (or copying into `tools/`) `work/judge_r1/judge_rules.py`, `work/judge_r4/rules.py` and `work/cuts/tools/grid.py` before anything depends on them.

## Method
- Read in full: the pipeline doc, the options doc and all three designs.
- Checked existence and line numbers with find, sed and grep over `docs/research/2026-11-09-glasses-pov-session/`, `backend/toms_gym/` and `~/code/bowling-app/analysis-engine/`.
- Read the DAT Android and iOS CHANGELOGs, re-fetched this pass with `gh api`, plus the iOS inputs skill and the CameraAccess README already fetched into the session scratchpad by the research agent.
- Read the header and metadata strings of one clip from `~/pov-2026-11-08/drive_raw` (not the holdout).
- No tracker, ffmpeg or torch was run, and `/Users/toka/pov-holdout` was not opened.
