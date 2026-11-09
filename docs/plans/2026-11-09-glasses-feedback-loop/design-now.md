# Design "now": fold the glasses, get a per-throw session page. No new Meta APIs, no store app.

Written 2026-11-09 from `current-pipeline-steps.md` and `meta-glasses-options.md` (both read in full) plus the repo code named below. **V** = I read the file or doc; **I** = inferred; **3P/UNV** = carried over from the options doc's labels.

## Pitch

Fold the glasses when the game ends; a sync app on the phone pushes every clip to a cloud inbox, a Cloud Scheduler tick turns each clip into a queued Toms Gym bowling attempt, a worker runs the existing cut + tracker + judge code, and one digest email links to a `/bowling/session/<date>` page with a recap frame per bowler and game and a per-throw video (line, or "no line: J2 pin-row crossing" on the card). Tom types nothing and never opens a laptop session. Feedback is **per batch, not per throw**: Meta auto-import only runs when the glasses are folded or cased (V, options doc A). The only per-throw path is the DAT phone app (option D), which is outside this lens.

## End-to-end flow (H = human, M = machine)

| # | who | step | today | in this design |
|---|---|---|---|---|
| 1 | H | Record one clip per throw on the glasses (5 s of effort per throw) | same | same. Clip boundaries stay; nothing new on the glasses. |
| 2 | H | Fold the glasses / put them in the case at the end of a game (phone BT + Wi-Fi on, >30 % battery) | happens anyway | the only deliberate manual step. Meta AI app auto-import moves the clips into the phone's "Meta AI" gallery folder (V, options A; on by default on Android 13+). Tom's phone is Android (I: it runs the toms_gym APK; the glasses pair to his phone, so Chardie's phone is irrelevant, I). |
| 3 | M | Autosync for Google Drive (or FolderSync "Instant sync") watches the "Meta AI" folder and uploads new files one-way to a Drive folder `glasses-inbox/` (3P; the combined Meta-import + sync chain is UNV). Plan B: FolderSync -> GCS through the S3-compatible endpoint with an HMAC key (3P), straight into `gs://jtr-lift-u-4ever-cool-bucket/bowling/glasses-inbox/`. | manual Drive upload from the phone, 6 min | zero taps. Uploads about 30 MB per clip; 1 GB per 32-clip session. |
| 4 | M | **Ingest.** Cloud Scheduler hits `POST /bowling/glasses/ingest` every 2 min (new route, `X-Admin-Token` like the ticket routes, V `ticket_routes.py` pattern per CLAUDE.md). It lists the inbox folder with the runtime service account (folder shared to `toms-gym-service@toms-gym.iam.gserviceaccount.com`; UNV that Drive API is enabled on the project), skips names ending `.adding` (V: Drive shows in-flight uploads with that suffix, `wait_drive.sh`) and md5s already seen (V: `drive_list.json` carries `md5Checksum`), streams each new file **server-side** Drive -> GCS `bowling/input/<name>`, and creates User/UserCompetition/Attempt/BowlingResult through a helper extracted from `upload_bowling_video` (V `bowling_routes.py:32-176`). Never re-POSTs through Flask: the multipart route does `blob.upload_from_string(file.read())` and sits behind Cloud Run's 32 MiB body cap (V); these clips are 27-51 MB (V, `ls -l drive_raw`). New columns on `BowlingResult`: `source='glasses'`, `session_key` (the `YYYYMMDD` prefix of the Meta file name, V: names are `20261108_104714_593f3a1d.mp4`), `release_frame`, `judge` (JSON), `fail_reason`. Migration 020 in `app.py` (startup-migration pattern, V CLAUDE.md). Config: `GLASSES_INBOX_FOLDER_ID`, `GLASSES_USER_ID`, `GLASSES_COMPETITION_ID` (a standing "Glasses POV" competition, since `competition_id` is required, V). With plan B the trigger is a GCS Object Finalize notification -> Eventarc -> the same route with the object name, and the Drive listing and polling disappear. | Tom pastes a Drive link into Claude, approves; agent-typed curl + gcloud token (steps 5-6, ~11 min + the 21.6 h wait) | zero taps, under 2 min after the file lands. |
| 5 | M | **Dispatch.** `enqueue_analysis_job` whitelists `kind in ('lifting','bowling')` and `/jobs/bowling/<id>` calls the old `bowling-service /analyze` with a 360 s client timeout (V `analysis_dispatch.py`, `jobs_routes.py`, `bowling_processor.py:170-174`). A POV clip must **not** go there. Week 1-3: glasses rows stay `queued` and are pulled by a laptop worker (6a). Later: add `kind='bowling-pov'` to `analysis_dispatch.py` plus `/jobs/bowling-pov/<id>` in `jobs_routes.py` that calls a new `pov-service` (6b). | n/a | code change, named. |
| 6a | M | **Compute, phase 1: laptop worker.** `tools/glasses/worker.py` under launchd polls `GET /bowling/glasses/pending` every minute, downloads the clip from GCS, runs `auto_cuts` -> `track_v3` (`--device mps`) -> `judge_rules.judge` -> the per-throw renderer, uploads `overlay.mp4`, `track.json`, `recap.png` to GCS, and calls `PUT /bowling/result/<id>/complete` (new, admin-token) with `debug_video_url`, `trajectory_png_url`, `entry_board`, `board_at_pins`, `judge`, `fail_reason`. Serialized, one torch process at a time (V: `run_all.sh` already spins on other torch processes). Measured 59-165 s per clip on MPS, median 71 s over 116 log lines (V pipeline doc). **This moves the 21.6 h gap to "whenever the Mac is awake"; it does not remove it.** | laptop GPU runs started by an agent | same compute, no agent. |
| 6b | M | **Compute, phase 2: cloud.** Containerize `tools/glasses/` as `pov-service` (Cloud Run, CPU, 8 cpu / 8 Gi like `bowling-service`, V `deploy.sh`) running `run.py --no-sam` (V: the flag exists in `experiments/motion-only/run.py:437`) or SAM 2 on CPU. Per-clip CPU time is **unknown** and is the week-2 measurement; SAM 2 is 46 of 58 s per clip on MPS (V), so CPU SAM could approach the 600 s service / 900 s Cloud Tasks ceiling (I). Do not plan on the L4: `Dockerfile.gpu` says "DRAFT, UNTESTED" (V) and the quota request has been pending since 2026-06-07 (V memory). | n/a | removes the Mac. |
| 7 | M | **Release frame.** `auto_cuts.py` v3.1 runs first. If it returns null, the throw is marked `needs_release_tap` and the card says so; if it returns a frame, it is used as-is. | agent reads frame grids, 24 of 31 by eye, 36 min | nulls become a 5 s tap each (step 9); wrong cuts still slip through (see "Where the accuracy problems survive"). |
| 8 | M | **Judge and one rerun.** `judge_rules.judge` (J1-J5) as code; a fixed fail-class -> fallback map taken from `track_v3`'s per-clip fallbacks (pin-row second pass, SAM deck reseed, entry crossing; V track_v3 header); at most one rerun; no amendments. A fail renders video-only with the failing rule on the card (what Tom asked for at 17:29, V). | three agent judge rounds, amendments, two reruns, ~3 h | one code pass, about 2-5 min per clip for the rerun subset. |
| 9 | H | **Phone taps on the session page** (`/bowling/session/<date>`): tap the release frame for each `needs_release_tap` throw (frame strip from `GET /result/<id>/frames`, V `bowling_routes.py:437`; store via `PUT .../annotation/markers`, V `:696`; re-queue via `POST .../reanalyze`, V `:370`), and tag the wearer once per game ("game 2 = Chardie"). Default wearer is Tom. | agent clusters clothing, lane alternation, monitors, 27 min | about 2 min of taps per session in week 1 (15 nulls of 25 at v3's rate, I). |
| 10 | M | **Render.** Per-throw overlay mp4 plus a recap frame per bowler and game, from `make_session_video.py` refactored to take `session_map.json` + judged JSON as arguments and to derive the video-only list from the judge (V: today VIDEO_ONLY, CLIPS and the group order are hard-coded, no argparse). | agent runs the script, critic pass, re-render, 23 min | automatic; the critic's must-fix items are already rules in the renderer (V pipeline doc step 23). |
| 11 | M | **Deliver.** A session digest: when no glasses row for `session_key` has changed for 10 min, send one email with a short link to `/bowling/session/<date>` (new, built on `analysis_notify.py`'s SMTP + `_generate_code` short-link code, V). The per-attempt `notify_analysis_complete` is suppressed for `source='glasses'` rows, or Tom gets 32 emails (V: it is per attempt). The APK Home to-do list gets a "Session 11-08: 18 of 31 lines ready" row (I: pattern exists per `finch-shell.md`). `useIsOwner` hides every bowling surface from anyone but Tom's email (V CLAUDE.md), so Chardie sees her throws only through the short link, or the gate is relaxed for `/bowling/session/*`. | resumable Drive upload from a scratchpad script, Tom opens Drive | one email, one page. |

## Manual steps that remain

1. Start and stop a clip per throw on the glasses (unchanged).
2. Fold the glasses or case them at the end of a game, with the phone nearby, Bluetooth and Wi-Fi on.
3. Tap the release frame on throws the detector returned null for (about 60 % of throws at v3's rate; 5 s each).
4. Tag the wearer once per game when Chardie bowled (default Tom).
5. Keep the Mac awake until phase 2 ships (or accept that the batch waits for it).
6. One-time setup: install the sync app and point it at the Meta AI folder; share the inbox folder with the runtime SA; create the standing competition; install the launchd worker.

## Expected time from last throw to feedback (I, no measurement of the chain exists)

| stage | estimate |
|---|---|
| fold -> clips on the phone (Meta import of ~1 GB over the glasses' Wi-Fi) | 10-30 min; latency UNV, forum posts report stalls |
| phone -> cloud inbox (1 GB) | 3-5 min on Wi-Fi, 10-20 min on LTE; Autosync may wait for Wi-Fi (3P) |
| ingest tick | <= 2 min |
| compute, 32 clips serialized on the Mac at 60-165 s each, one rerun for about a third | 35-75 min |
| release taps by Tom + reanalyze of those throws | 2 min of taps, then 15-25 min of compute |
| render + digest quiet period | ~15 min |
| **Total, Mac awake** | **about 90-150 min after folding the glasses** (today: 21.6 h wait + ~6 h of session) |
| **Total, Mac asleep** | the compute waits until the Mac wakes: the 21.6 h latency survives until phase 2 |


## Reused from the repo vs rewritten

| file (V = read) | fate | note |
|---|---|---|
| `backend/toms_gym/routes/bowling_routes.py:32-176` `upload_bowling_video` | **rewrite into a helper** `_create_bowling_attempt(session, user_id, competition_id, video_url, source, session_key)`; the multipart route keeps calling it | the GCS write part is bypassed for glasses clips (server-side copy) |
| `bowling_routes.py` `/result/<id>` `:179`, `/results` `:225`, `/frames` `:437,545`, `/annotation/markers` `:696`, `/reanalyze` `:370` | **as-is** | result read, frame strip for the release tap, marker store, re-queue |
| `backend/toms_gym/services/analysis_dispatch.py` | **extend** with `kind='bowling-pov'` (phase 2) | today's whitelist would send POV clips to the old analyzer |
| `backend/toms_gym/routes/jobs_routes.py` | **extend** with `/jobs/bowling-pov/<id>` (phase 2) | copy of `run_bowling_job` targeting `pov-service` |
| `backend/toms_gym/integrations/analysis_notify.py` | **wrap**: suppress per-attempt mail for glasses rows; reuse SMTP config + `_generate_code` for the digest | |
| `backend/toms_gym/routes/short_link_routes.py` `/short-link`, `/s/<code>` | **as-is** | the digest link and Chardie's share link |
| `backend/toms_gym/routes/upload_routes.py:477-620` signed-url / resumable / finalize | **not used** | the phone never talks to Flask in this design; kept as the fallback "share-sheet upload" if the sync chain fails |
| `frontend/src/pages/AnalysisStatus.tsx`, `BowlingResult.tsx` | **as-is** for a single throw | `/bowling/status/:attemptId` already polls `/bowling/result/<id>` |
| `frontend/src/pages/BowlingUpload.tsx` | **unchanged**; still multipart `FormData` (V `:43`) and still subject to the 32 MiB cap | out of scope |
| `docs/research/2026-11-09-glasses-pov-session/auto_cuts.py` | **wrap**: lift into `tools/glasses/cuts.py`, make the ffmpeg path an argument (hard-coded `/opt/homebrew/bin/`, V `:33`), keep `--release` | the algorithm is unchanged, v3.1 gate included |
| `.../track_v3.py` | **reuse the algorithm, rewrite the shell**: hard-codes `S` (the research folder) and `Q` (the quarantine) at `:57-58`, imports `experiments/motion-only/run.py` and `sam_track`; package as `tools/glasses/track.py` with `--clip`, `--release`, `--out`, `--device` | the quarantine audit hook stays off in production |
| `.../experiments/motion-only/run.py` (`--no-sam`, `--device`) | **as-is** inside the package | the CPU candidate for phase 2 |
| `.../work/judge_r1/judge_rules.py` (J1-J5) | **commit first, then as-is** | lives in `work/`, which the session doc says is not committed (V); until it is committed the product judge does not exist |
| `.../work/judge_r3/rules.py` | **drop** | a driver with hard-coded stems and round folders |
| `.../make_session_video.py` | **rewrite the entry**: argparse for `session_map.json`, judged JSON, clip dir, out dir; emit per-throw mp4s + recap PNGs; derive video-only from the judge | drawing code reused verbatim |
| `.../run_all.sh`, `rerun_r1.sh`, `rerun_r2.sh`, `run_missing.sh` | **drop**; replaced by `worker.py` | the "wait for other torch process" spin becomes the worker's lock |
| `.../work/cuts/drive.py` | **drop** | one-off driver over `eye_releases.json` |
| scratchpad `wait_drive.sh`, `drive_upload.sh` (session-scoped, reclaimed, V) | **move into the repo** as the Drive listing/`.adding` logic of `glasses_ingest.py`; the upload script is no longer needed once delivery is a page | the only Drive code that exists; it uses Tom's user `gcloud` token with `--enable-gdrive-access` (V 11-07 session doc), which a Cloud Run service cannot use |
| `~/code/bowling-app/analysis-engine/deploy.sh`, `Dockerfile` | **copy the shape** for `pov-service` | never run `deploy.sh` itself (CLAUDE.md) |
| `.claude/workflows/bowling-pov-session.js` | **retire for recurring sessions**; keep for research loops | its Truth/Experiments/Critic phases are one-off research (V pipeline doc steps 13-14) |

## What must be built (new)

1. `backend/.../routes/glasses_routes.py`: `POST /bowling/glasses/ingest` (admin token; Drive list + server-side copy + attempt creation), `GET /bowling/glasses/pending`, `PUT /bowling/result/<id>/complete`, `GET /bowling/session/<date>`, `PUT /bowling/session/<date>/wearer`. Migration 020.
2. `tools/glasses/`: `ingest.py` (also runnable from the laptop in week 1), `worker.py` (launchd plist), `cuts.py`, `track.py`, `judge.py`, `render.py`, `requirements.txt` pinned to the engine venv.
3. Cloud Scheduler job + the runtime SA's Drive access (or plan B: GCS inbox + Eventarc).
4. Frontend `pages/GlassesSession.tsx` at `/bowling/session/:date`: recap per bowler/game, per-throw cards with the judge reason, release-tap strip, wearer tag.
5. Session digest email + APK to-do row.
6. Phase 2: `pov-service` container, `kind='bowling-pov'`, `/jobs/bowling-pov/<id>`.

## Depends on unverified or preview-only capabilities

- Meta AI auto-import + Autosync/FolderSync as a combined chain: nobody documents it (UNV); import latency UNV, stalls reported (3P); Android may kill the sync app (I).
- Autosync delivers the **original** file (md5 equal to the phone copy), not a recompressed one (UNV; Google Photos would recompress and is a dead end, V options doc).
- Drive API enabled on project `toms-gym` and a Drive folder shared to the runtime SA is readable with `google.auth.default()` credentials (UNV; the repo only has user-token Drive access).
- FolderSync -> GCS S3 interop (3P), only for plan B.
- Tom's phone is Android (I from the APK; the clips being HEVC does not contradict it, Android can write HEVC in `.mp4`).
- CPU per-clip time of `run.py --no-sam` and of SAM 2 on CPU: not measured; nothing in the repo ran the POV tracker off MPS (V: every `.done` log is `--device mps`).
- L4 GPU on Cloud Run: quota pending since 2026-06-07, `Dockerfile.gpu` untested (V). Not relied on.
- Meta file names always carry the capture timestamp `YYYYMMDD_HHMMSS_<hash>` (V for 32 of 32 clips in this session; I for other firmware).

## First-week deliverable: prove the phone -> cloud -> Attempt chain

The riskiest assumption is the one with zero prior evidence and zero code: that folding the glasses ends with full-quality clips in a cloud folder without a tap, in minutes rather than hours. Everything downstream already runs (on the Mac).

Deliverable: a timing table for 5 throws (a ball rolled anywhere; no alley needed).

1. Install Autosync for Google Drive (or FolderSync), pair the "Meta AI" gallery folder to `glasses-inbox/` in Drive, upload-only, instant sync, Wi-Fi and cellular both allowed.
2. Record 5 clips, fold the glasses, note the wall time.
3. Record: time each clip appears in Drive (first as `.adding`, then final), its `md5Checksum` vs `md5` of the copy on the phone (`adb pull`), and its size.
4. Run the durable `tools/glasses/ingest.py` from the laptop against prod (the user-token Drive path, the one that exists today) and record the time each `Attempt` row appears with `source='glasses'` and `processing_status='queued'`. This step also lands the helper extraction from `upload_bowling_video` and migration 020.
5. Side test, non-blocking: once the current tracker batch on this machine has finished, run `run.py --device cpu` on one clip and record the wall time, with and without `--no-sam`. This sizes phase 2. (Not run now: a tracker batch is live and must not be slowed.)

Pass: 5 of 5 clips in Drive within 30 min of folding, md5 equal to the phone copy, 5 queued attempts without typing. Fail on md5 means the sync app recompresses and plan B (GCS direct) or the share-sheet signed-URL upload becomes primary. Fail on latency means the Meta import stall is real and the design degrades to "feedback the next time the glasses sit in the case".

## Cost (rough)

- Money: Autosync/FolderSync one-off purchase, single-digit dollars (3P, price UNV). Drive: 1 GB per session inside the free 15 GB, so about 15 sessions before a 100 GB plan at about $2/month (I). GCS: cents per session. Cloud Scheduler + the ingest calls: cents. Phase 2 Cloud Run CPU: to be measured; a guess at 8 vCPU x 5 min x 32 clips is a few dollars per session (I). No GPU cost.
- Effort: week 1, 1-2 days (sync-app test, `ingest.py`, helper extraction, migration). Week 2, 3 days (`worker.py`, `track.py`/`cuts.py` packaging, judge as code with the fixed fallback map, renderer argparse, `complete` route). Week 3, 3 days (session page, release tap, wearer tag, digest email, owner gate). Phase 2, 3-5 days plus the CPU measurement; it may stall on SAM 2 CPU time.

## Where the pipeline's accuracy problems survive this design (honest)

- **Release detection (v3: 4 right, 6 wrong, 15 null of 25; every wrong cut said `verified: true`, V).** Not fixed. The design converts nulls into taps (60 % of throws at that rate) and **lets the wrong cuts through**: they render a wrong line and look verified. The v3.1 clip-end gate turned 5 of the 6 wrongs into nulls, but it is a post-hoc fit with no holdout (V). A cross-check against the audio pin hit or one LLM-vision call on the release strip `auto_cuts` already writes is the week-3 candidate; it needs a holdout before it is trusted, and nothing here gives it one.
- **The 60 ft crossing short (J2; 13 of 31 throws video-only, the track stops 2-10 px short of the headpin base row, V memory).** Survives unchanged: the worker runs the same `track_v3` fallbacks. The round-4 pin-row extrapolation was still running at 17:59 and is unproven. Expect 10-13 of 31 cards to say "no line: J2" until that lands.
- **Entry error on the truth clips (mean 3.16 boards at the detected pin row, 4 of 6 within 2.5, V).** Unchanged; the design adds no truth and no scorer.
- **Bowler identity.** No automatic answer under this lens; it becomes one tap per game. Names stay as the brief says ("Chardie"), the monitors' "Chris" is ignored.
- **Game and frame numbers.** By clip order within the date plus the wearer tags; no monitor read. Game boundaries are the wearer taps or a time gap, which this session shows is unreliable (I).
- **Ball colour.** The motion-only tracker is colour-free (V), so the 4 colour overrides disappear; the truth still covers no green or red ball (V).
- **Compute.** Unchanged per clip; the Mac dependency stays until phase 2 proves CPU timing.
