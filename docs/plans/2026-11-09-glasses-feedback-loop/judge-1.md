# Judge 1 (skeptic of capabilities): three glasses-feedback designs, 2026-11-09

Lens: every Meta or phone-app capability counts as unavailable until a primary source says otherwise. **V** means I read the file or fetched the page in this pass. **INF** means my inference. **UNV** means I looked and could not confirm it.

## What I verified myself (not carried over from the options doc)

- **Meta auto-import** [V, fetched meta.com/help/ai-glasses/1510723473009423]. It runs when the glasses "are in the charging case or their hinges are closed", with phone Bluetooth and Wi-Fi on, and >30 % battery is recommended. It is "on by default for Android (13+) and iOS phones". **The page gives no timing.** Files land "in your phone's photo app".
- **"Meta AI" folder** [V, fetched .../1964061290737893]. Imported media goes to a "Meta AI" folder in the mobile photo gallery. Cloud backup (Google Photos) must be told to back that folder up. The page does not say this is Android-only.
- **DAT 1.0** [V, iOS and Android CHANGELOG.md fetched via `gh api`]:
  - iOS 1.0.0 shipped 2026-09-24; iOS and Android 1.0.1 shipped 2026-10-09.
  - Inputs (`CapturePressType`), Speech, Motion, voice invocations, photo capture and **camera audio streaming** are all `[Experimental]`. Experimental means "can be built and tested against, though apps using them cannot be published yet".
  - `donState`/`hingeState` were added in 1.0.0.
  - "High resolution (720x1280) video can now be requested".
  - `hvc1` "continues in the background" (iOS line 198).
  - The changelog contradicts itself on background recording. Line 57 says the sample records "continuing while the app is backgrounded". Line 65 says it "now ends the active preview session when the app backgrounds".
  - The iOS changelog has a bare "[Feature] WiFi transport." line (93) with no detail.
- **DAT integration doc** [V, fetched]: "Developer mode allows your unpublished app to register and interact with your AI glasses". It supports iOS 17.2+ and Android 10+. The page says nothing about stream resolution or recording.
- **Autosync** [V, partial, metactrl.com]: "New files in your device are uploaded to cloud storage". The apps "can be configured to instantly upload new photos". Wi-Fi-only is an option.
  - **Not confirmed:** one-way/upload-only mode for the Drive app (the page describes two-way behaviour, with deletes applying on both sides), original-file fidelity, and free-tier file-size limits. The user-guide URL returned 404, and the Play listing did not render.
  - [INF, from my own memory, unverified] Autosync's free tier has historically capped the upload file size at about 10 MB. Our clips are 27-51 MB, so the paid tier may be required.
- **GCP project `toms-gym` enabled APIs** [V, `gcloud services list --enabled`, 46 services]. The canary `run.googleapis.com` is present, so the listing worked.
  - `cloudtasks` and `iamcredentials` are enabled.
  - **`drive.googleapis.com`, `cloudscheduler.googleapis.com` and `eventarc.googleapis.com` are NOT enabled.**
- **Phone OS evidence** [V, header bytes of a `drive_raw` clip; INF on the meaning]. The container is `ftyp isom / iso2 mp41`, an ISO MP4, not a QuickTime `qt` brand. The metadata reads `app=Meta AI&device=Meta Smart Glasses`. This leans weakly toward Android but does not settle it.
- **Repo files** [V, Bash `-e`/`wc`/`grep`]. These exist:
  - `auto_cuts.py` (286 lines; `--no-cut` and `--release`; `audio_rises`, `onsets`, `CRASH_LAG`)
  - `track_v3.py` (919 lines; hard-codes `S` and `Q` at lines 57-58; `MAX_PASSES = 4`; round-4 extrapolated crossing in the docstring)
  - `make_session_video.py` (hard-coded `CLIPS`/`VIDEO_ONLY`, no argparse)
  - `work/judge_r1/judge_rules.py` (79 lines), `work/judge_r3/rules.py` (61), `work/judge_r4/rules.py` (62). **The whole `work/` folder is gitignored** (`.gitignore:1:work/`).
  - `work/cuts/eye_releases.json` (dict of 31), `work/cuts/grids/` (82 JPGs), `work/structure/person_A.jpg` and `person_B.jpg`
  - `results/session_map.json`, `results/judged_final.json`
  - `experiments/motion-only/run.py` (`--no-sam` at line 437, `--device`)
  - `run_all.sh` and the other three batch scripts
  - the scratchpad `wait_drive.sh` and `drive_upload.sh` (in this session's scratchpad, so they will be reclaimed)
  - `.claude/workflows/bowling-pov-session.js`
  - `docs/sessions/2026-11-07-glasses-pov-hook-loop.md:42` (the `--enable-gdrive-access` recipe)
  - `analysis-engine/Dockerfile.gpu` ("DRAFT ... UNTESTED"); engine `deploy.sh` 8 cpu / 8Gi / 600 s
  - backend routes at the cited lines: `bowling_routes.py:32` upload with `upload_from_string` at line 127 and `competition_id` required; `:179`, `:225`, `:370`, `:437`, `:696`
  - `upload_routes.py:173` `_generate_signed_upload_url`
  - `analysis_dispatch.py:34` whitelist `('lifting','bowling')`; `jobs_routes.py:93` `run_bowling_job`; `bowling_processor.py` `/analyze` `timeout=360`
  - `analysis_notify.py` `_create_short_link`, `_send_ready_email`, `notify_analysis_complete` (`_generate_code` is imported from `short_link_routes.py:43`)
  - frontend `AnalysisStatus.tsx`, `BowlingResult.tsx`, `BowlingUpload.tsx`, `capacitor.config.ts`, and the route `/bowling/status/:attemptId`
  - the round-4 log line for 112413: `sam_s 92.6`, `wall_s 119.2`
- **`auto_cuts.py` writes no images** [V]. It has no `imwrite` and no grid or strip code; its only `strip` match is the Python `.strip()`. The 82 grids in `work/cuts/grids/` were written by agents with code that does not survive.

## Scores (0-5; accuracy risk: higher = lower risk)

| design | steps removed | time to feedback | feasible now | accuracy risk | total |
|---|---|---|---|---|---|
| design-now (fold -> sync app -> cloud inbox -> laptop worker -> session page) | 4 | 3 | 3 | 3 | 13 |
| design-toolkit (DAT companion app, per-throw stream + TTS) | 4 | 5 | 2 | 1 | 12 |
| design-session (keep the manual transfer, codify everything after Drive) | 3 | 3 | 4 | 3 | 13 |

### Why

- **design-now**
  - **Steps removed.** It removes the phone upload, the Claude prompt, the Drive download, the workflow start, the agent judge rounds and the manual render. The bowler map becomes one tap per game.
  - **Steps added.** It adds a human release tap on every null (about 60 % of throws at v3's rate, by its own estimate).
  - **Time.** About 90-150 min after folding, and only while the Mac is awake. Every number in that range is INF.
  - **Feasible now.**
    - Auto-import is V.
    - The sync hop is **3P only**: one-way mode, original fidelity and the free-tier size cap are all UNV or INF.
    - If Tom's phone is an iPhone, Autosync/FolderSync do not apply at all.
    - The Drive API, Cloud Scheduler and Eventarc are all disabled on `toms-gym` (V). Enabling them is easy, but the design relies on them.
    - The laptop worker is feasible.
  - **Accuracy.** Human taps on nulls are honest. Wrong cuts still render as "verified" (conceded in the design), and J2 is unchanged.
- **design-toolkit**
  - **Time.** The best on paper: about 3-5 min per throw.
  - **Feasible now (scored low under this lens).** DAT 1.0 and Developer Mode are V, but the per-throw loop rests on unverified pieces:
    - the Inputs capture button (Experimental, V);
    - glasses-side audio for the auto-stop (Experimental, V; the phone mic is pocketed);
    - background or locked recording (Meta's own changelog contradicts itself, V);
    - TTS routing to the glasses during a DAT session (INF);
    - stream-start latency (UNV);
    - battery over a 65-minute stream (UNV);
    - a new native app for an OS that is still unknown.
  - It also costs 3-4 weeks before the first alley use (its own estimate).
  - **Accuracy.** It is the worst of the three. The tracker would get a different input: a 720x1280 Bluetooth-compressed stream that can fall to 504x896 at 15 fps (V), while the tracker was tuned on 1184-1424 px native clips. J2 already fails 9 of 31 at native resolution. The design would also speak a `partial` tracker's verdict per throw with no review.
- **design-session**
  - **Feasible now.** It uses only the transfer that already ran end to end on 11-08 (auto-import -> phone -> Drive, V), plus the user-token Drive access Tom already granted (V, session doc line 42). No new Meta, phone-app or GCP capability is needed.
  - **Unproven.** The vision release read and STT of the spoken tag are untested. The design says so.
  - **Steps removed.** Fewer than the others: fold and the manual phone upload stay. That is the weakest fit to the user's ask ("integrated with the meta glasses so there is less manual steps").
  - **Accuracy.**
    - An unattended vision read replaces the agent's read.
    - The validation set is the agent's own labels (model-vs-model, conceded).
    - A read that is off by a few frames but agrees with both cross-checks passes silently.
    - The two cross-checks (audio crash window, tracker seed) catch some of the "verified: true" wrong cuts that design-now lets through.
    - A forgotten voice tag falls back to inheritance.

## Refuted or resolved-false claims

### design-now
1. **REFUTED:** "one LLM-vision call on the release strip `auto_cuts` already writes" (accuracy section; the same phrase appears in current-pipeline-steps step 10). `auto_cuts.py` writes no images (V). A grid writer has to be built first, so the week-3 candidate is bigger than stated.
2. **RESOLVED FALSE (it was marked UNV):** that the Drive API is enabled on `toms-gym`. It is not, and neither Cloud Scheduler (step 4's trigger) nor Eventarc (plan B) is enabled (V, `gcloud services list`). This is fixable with `gcloud services enable`, but as of today the ingest route cannot run as written.
3. **NOT CONFIRMED (not refuted):**
   - Autosync "uploads new files one-way" with the original bytes. The vendor page describes two-way sync and does not cover the size cap or fidelity (V partial).
   - The free tier may cap uploads at about 10 MB (INF, from memory). That would fail on every clip.
   - The design's week-1 md5 test is the right gate for this.
4. **NOT CONFIRMED:** "Tom's phone is Android". The container brand leans that way weakly (INF). An iPhone kills step 3 as written.
5. Minor: `_generate_code` lives in `short_link_routes.py` and is imported into `analysis_notify.py`. The claim is substantively correct.

### design-toolkit
1. **REFUTED:** "a depth-4 find over `toms_gym` and `bowling-app` did not locate [`judge_rules.py`, `rules.py`], so the judge is reusable as a spec, not yet as a file". All three files exist at `docs/research/2026-11-09-glasses-pov-session/work/judge_r1/judge_rules.py`, `work/judge_r3/rules.py` and `work/judge_r4/rules.py` (V). The find was too shallow: they sit at depth 6. They are gitignored, so "commit first" (design-now) is the right fix.
2. **REFUTED:** "(a) one LLM-vision call per clip on the release-6..+6 strip `auto_cuts` already writes". There is no such strip (V).
3. **SELF-UNDERMINED (V):** the step-3 audio stop on the "mid-band pin-crash onset". The phone mic is pocketed, and glasses camera audio is `[Experimental]` in 1.0.0. The addendum concedes this. Until tested, the automatic per-throw stop does not exist.
4. **CONTRADICTED BY PRIMARY SOURCE (V):** that "Recording keeps running with the phone locked" is merely open. Changelog line 65 says the sample ends the session on backgrounding, and the current README says so too (per the options doc). The design marks this UNV-1, which is fair, but the per-throw no-touch claim in the pitch depends on it.
5. **UNV, not refuted:** TTS through the glasses speakers during a DAT session; stream-start latency; battery over a 65-minute stream; whether a capture press also starts a native recording.
6. Minor: `upload_routes.py:183` is inside `_generate_signed_upload_url`, which starts at line 173. Not material.

### design-session
1. **REFUTED (internal contradiction):** the time table's "cuts + 62 vision calls ... the grids are already written by auto_cuts". Its own reuse list says correctly that `auto_cuts.py` writes no grids (V). `grid_write.py` has to run, which adds decode time per clip (INF, a few minutes per session). Week 1 can still use the 82 grids already on disk (V).
2. **Verified, not refuted:**
   - SAM 2 at 92.6 of 119.2 s on 112413 in the round-4 log
   - 82 grids
   - `eye_releases.json` with 31 entries
   - the `--no-cut` flag
   - the `MAX_PASSES` loop that includes the round-4 extrapolated crossing
   - the judge files (`judge_r1/judge_rules.py` 79 lines, `judge_r4/rules.py` 62 lines)
   - the session-doc line 42 Drive recipe
   - `upload_routes.py:171-190`
3. **Open (UNV):** whether the user gcloud token refreshes unattended under launchd (INF: refresh tokens usually do, but the `--enable-gdrive-access` scope has not been exercised by a daemon); STT on alley noise.

## Winner: design-session as the base

It ties design-now on total and wins on the skeptic's tiebreak, feasible-now. It is the only design whose transfer path is already proven (11-08) and that needs no unverified Meta, phone-app or GCP capability. It also removes the costs that actually dominate: the 21.6 h "wait for a laptop session", Claude prompt, ~87 min of agent eye-reads and mapping, and the ~3 h judge/rerun loop.

### Graft from design-now
- **The phone-side sync hop, gated by its own week-1 md5 and latency test, as the step that removes the manual Drive upload once it passes.** This is what answers "integrated with the glasses, fewer steps".
  - On Android: Autosync/FolderSync (check the paid-tier size cap first).
  - On iPhone: C1 Shortcuts or C3 osxphotos instead.
  - Settle the phone OS on day 1.
- Commit `work/judge_r1/judge_rules.py` and `work/judge_r4/rules.py` out of the gitignored `work/` first.
- Bypass the 32 MiB cap server-side (Drive -> GCS). Never re-POST through Flask.
- Suppress the per-attempt emails and send one session digest.
- The release-tap fallback on the session page for `release: unresolved` throws (a human 5 s tap is better than a silent video-only).
- Guard `kind='bowling-pov'` so POV clips never reach the old `/analyze`.
- Enable the Drive API (and Cloud Scheduler, if the ingest moves to the cloud) on `toms-gym` before relying on a service account.

### Graft from design-toolkit
- The cheap twin-clip spike only: the CameraAccess sample, 5 throws, stream vs native, with an explicit kill criterion. Run it after the laptop is free, as research that does not block anything.
- One fixed sentence per fail class on every card. That answers Tom's 17:29 question.
- Optionally, a wearer per phone if both bowlers ever use separate phones.
- Do not build the app until that spike passes.

## Inferences flagged
- All feedback-time totals in all three designs are INF. No part of any chain has been timed end to end except the 11-08 manual path.
- The Autosync free-tier size cap is from my memory, not a fetched page.
- The phone OS reading from the `ftyp` brand is INF.
