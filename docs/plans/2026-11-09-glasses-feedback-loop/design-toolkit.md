# Design: a companion phone app on the Meta Wearables Device Access Toolkit (DAT) for per-throw bowling feedback

Written 2026-11-09 by the "toolkit" Design agent. Inputs read: `current-pipeline-steps.md` and `meta-glasses-options.md` in this folder (both present), the session folder `docs/research/2026-11-09-glasses-pov-session/` (RULES.md, README.md, `auto_cuts.py`, `track_v3.py` headers), `backend/toms_gym/routes/bowling_routes.py`, `backend/toms_gym/routes/upload_routes.py`, `backend/toms_gym/services/analysis_dispatch.py`, `backend/toms_gym/integrations/bowling_processor.py`, `frontend/capacitor.config.ts`, and the DAT iOS and Android `CHANGELOG.md` (fetched 2026-11-09).

Tags: **[V]** verified by reading a file or a fetched page; **[INF]** my inference; **[UNV]** looked, could not confirm; **[3P]** third-party claim carried over from the options doc.

## 1. One-line pitch

A small native phone app, built on DAT 1.0 in Developer Mode, records each throw from the glasses' camera stream the moment Tom presses the capture button, uploads the 720p clip to Toms Gym by signed URL, and reads the entry board back through the glasses' speakers about 3-5 minutes later, with no folding, importing, Drive or Claude in the loop.

## 2. Where the toolkit actually stands (so the word "preview" is used precisely)

- DAT is **1.0, not preview**: iOS SDK 1.0.0 shipped 2026-09-24, 1.0.1 on 2026-10-09; Android 1.0.1 is also dated 2026-10-09 [V, both CHANGELOGs]. Developer Mode lets an unpublished app pair with your own glasses with no review [V, options doc citing the DAT integration page; `Wearables.isDevMode` in Android 0.7.0 changelog].
- **Publishing is not open**, and a fixed set of features is **experimental**: Inputs (capture button), Motion, Speech, voice invocations, standalone photo capture, camera audio streaming. "They can be built and tested against, though apps using them cannot be published yet" [V, iOS CHANGELOG 1.0.0 header]. For a sideloaded personal app this is not a blocker. It is a blocker only if this is ever meant for other bowlers through an app store.
- The code runs on the **phone**, not the glasses [V, DAT FAQ via options doc]. The glasses stream frames to the phone over Bluetooth Classic at most 720x1280, with 504x896 and 360x640 fallbacks, at 2/7/15/24/30 fps [V, camera-streaming skill via options doc; 720x1280 and the fps list confirmed in the Android changelog 0.5.0 and 0.2.0].
- There is **no API to read clips already stored on the glasses** [V for "not found in FAQ, changelogs, skills"; UNV as a negative]. So the toolkit path is a *different recording*, not a faster import of the native one. The native 1184x1584-1424x1904 HEVC clip the tracker was tuned on is simply not what this path produces.

## 3. End-to-end flow (H = human, M = machine)

0. **H, once per phone.** Install the app (Xcode sideload on iPhone, APK on Android), enable Developer Mode in the Meta AI app, pair. Weekly re-sign on iOS with a free Apple ID [INF, standard iOS rule].
1. **H, once per session.** Open the app, sign in as the wearer, choose the alley/lane (or accept the last one). The app opens a `DeviceSession` and a `Camera` stream with codec `hvc1`, 720x1280 at 30 fps, and holds it for the whole session. Phone goes in a pocket. **Depends on UNV-1 (background recording while locked), see section 7.**
2. **H, per throw, about 1 s.** Before picking up the ball, press the glasses' capture button. The app receives the `.capture(pressType)` `InputEvent` and starts writing the stream to a file [V that the Inputs module exists and reports `CapturePressType`; UNV-2 whether the same press also fires the glasses' native recording; UNV-3 stream-start latency]. Fallback trigger if Inputs is unusable: a tap on the phone, or the app simply records continuously and cuts on audio.
3. **M.** The app listens to the mic/camera audio for the mid-band pin-crash onset and stops the recording about 1.5 s after it, with a hard stop at 25 s. The onset rule is the one `auto_cuts.py` already has (`audio_rises`, `onsets`, `CRASH_LAG`), today used only to place `pin_hit_frame` [V]. On the phone it is an end-of-throw gate, not a release detector.
4. **M.** The app calls `POST /bowling/sign-upload` (new) and PUTs the clip straight to GCS with the V4 signed URL that `upload_routes.py:183 _generate_signed_upload_url` already issues for lifting [V, lifting only today]. A 720p 15-20 s HEVC clip is roughly 5-15 MB [INF], so it would probably also fit under the 32 MiB cap of the existing `/bowling/upload` `upload_from_string` path [V, bowling_routes.py:32], but the signed URL keeps the bowling route out of the request body and is the pattern the app already uses.
5. **M.** The app then calls `POST /bowling/throws` (new) with `{object_name, wearer_user_id, session_id, lane, device_ts}`. The route creates the `BowlingResult` row and calls `enqueue_analysis_job('bowling', id)` (`analysis_dispatch.py:26`, Cloud Tasks, `ANALYSIS_DISPATCH_MODE=tasks`) [V].
6. **M.** A **POV worker** picks the task. In the first version this is the laptop: a small watcher that polls GCS or the DB for `status=queued, kind=pov`, downloads the clip, runs `auto_cuts.py <clip>` then `track_v3.py <stem> --device mps`, and writes `entry_board`, `pin_row_source`, the J1-J5 verdict and the overlay frame back [INF; both scripts exist and run on the laptop today, V]. Cloud `bowling-service` cannot run this yet: it is CPU-only, SAM 2 is about 46 of the 58 s per clip on the laptop GPU, L4 quota is pending, and `exp/r2-glasses-pov` is unmerged and undeployed [V, pipeline doc and memory notes].
7. **M.** The judge is code, not an agent: J1-J5 as written in RULES.md, one pass, no reruns in the live loop. A fail maps to a fixed sentence per class ("ball lost before the pins", "no pin row seen", "release not found").
8. **M.** The backend writes the result; the app polls `GET /bowling/result/<id>` (exists, bowling_routes.py:179) [V] and speaks the sentence with the phone's TTS. The glasses are the phone's Bluetooth audio device, so it comes out of the glasses' speakers [INF; UNV-6 whether DAT's own session interferes with the A2DP/HFP route]. On Meta Ray-Ban Display the Display module could show the board number instead [V that display APIs exist in 0.4.0+/0.9.0; not Tom's hardware as far as any note says].
9. **H, optional, per throw with a bad read.** Open the throw in the app and tap the release frame on a 13-frame strip; the app PUTs it through the existing `/result/<id>/annotation/*` routes [V those routes exist] and the worker re-cuts with `--release N` (exists, V). This replaces the agent eye-read with a 2 s tap, but it is still a human step and section 8 says why.
10. **M, end of session.** `make_session_video.py` is run once with `session_map.json` and `judged_final.json` as arguments (it needs argparse; paths are hard-coded today, V) and the Drive upload is the scratchpad `drive_upload.sh` moved into the repo (V that it is not durable today). Tom gets one link.

## 4. Manual steps that remain

1. Press the capture button before each throw (or trust the audio-only cut: then zero per-throw steps, at the cost of recording the walk-back and the waiting).
2. Open the app and sign in as the wearer once per session; hand the phone+glasses pair over when Chardie bowls, or Chardie runs her own copy (then bowler identity is free, section 8).
3. Listen to the result, and optionally tap a release frame when the app says "release not found".
4. Watch the end-of-session video.

Gone compared with the 26-step table: fold-to-import (step 2), the 21.6 h laptop gap (3), the Drive upload (4), the Claude prompt (5), the Drive download (6), the workflow start (7), the agent judge rounds (17, 20, 22) and the manual render (23).

## 5. Expected time from last throw to feedback

Honest split: **clip available on the phone: about 2 s after the pin crash** [INF from the design]. **Feedback available: about 3-5 min** [INF]: upload 5-15 MB over alley Wi-Fi or LTE 10-60 s, Cloud Tasks dispatch a few seconds, laptop tracker 59-165 s per clip measured (median 71 s over 116 log lines, first-pass 59 s, reruns to 165 s) [V], plus queue wait when two throws land inside one tracker run. With two bowlers alternating at roughly 1-2 min per turn, **the result lands one to two throws late**, not before the next ball. It is still about 400x faster than the 21.6 h + 6 h of 11-08/09. A GPU Cloud Run worker or a trimmed tracker (no SAM 2 reseed on passing stems) is what brings this under one throw; neither exists.

Battery: a continuous 65 min Bluetooth stream from the glasses has no published figure [UNV-5]. Meta recommends >30 % for import; the stream is heavier [INF].

## 6. What is reused from the repo (verified by reading)

| Piece | File | State today |
|---|---|---|
| Signed PUT URL to GCS via IAM signBlob | `backend/toms_gym/routes/upload_routes.py:183 _generate_signed_upload_url` | lifting only; add a bowling variant |
| Bowling result row + queue | `backend/toms_gym/routes/bowling_routes.py:32 upload_bowling_video`, `:179 get_bowling_result` | multipart body under the 32 MiB cap, `competition_id` required, no session or wearer field |
| Cloud Tasks dispatch | `backend/toms_gym/services/analysis_dispatch.py:26 enqueue_analysis_job` | live in `tasks` mode; the task target is `bowling-service`, which cannot run POV tracking |
| Service-to-service token and 360 s call | `backend/toms_gym/integrations/bowling_processor.py` | poller mode, disabled under tasks; shows the auth pattern a laptop worker would copy |
| Release/cut detection, audio onsets, `--release N` override | `docs/research/2026-11-09-glasses-pov-session/auto_cuts.py` | 4 right / 6 wrong / 15 null on untouched clips |
| Tracker with per-clip fallbacks | `docs/research/2026-11-09-glasses-pov-session/track_v3.py` (`--device mps`) | laptop only, partial verdict, 18 of 31 pass |
| Judge rules J1-J6 and the amendment history | `docs/research/2026-11-09-glasses-pov-session/RULES.md` | RULES.md names `judge_rules.py` and `rules.py`; a depth-4 find over `toms_gym` and `bowling-app` did not locate them, so the judge is reusable as a spec, not yet as a file I can point at |
| Pin-row detector, scorer | `docs/research/2026-11-07-glasses-pov-hook/track_v2.py`, `score_v2.py` | exist |
| Session renderer | `docs/research/2026-11-09-glasses-pov-session/make_session_video.py` | hard-coded paths, no argparse |
| Annotation and reanalyze routes | `bowling_routes.py:331-842` | exist; host for the release-frame tap |
| Android wrapper | `frontend/capacitor.config.ts` (`com.tomsgym.app`), `frontend/android/` | Capacitor WebView; DAT is a native SDK, so the spike is a separate app (the CameraAccess sample, modified), not a Capacitor plugin [INF] |

## 7. What must be built, and what each part depends on

**Phone app (new, native, two platforms or one):** DeviceSession + hvc1 stream + file sink; capture-button start; audio-onset stop; signed-URL upload; result poll + TTS; release-frame tap screen. Start from the DAT CameraAccess sample, which already records the stream to a file with optional mic audio [V, iOS CHANGELOG 0.9.0].

**Backend (small):** `POST /bowling/sign-upload`, `POST /bowling/throws` with `session_id`, `wearer_user_id`, `lane`; a `kind=pov` marker on `BowlingResult`; a result payload with `entry_board`, `verdict`, `fail_class`, `say`.

**Worker:** laptop watcher around `auto_cuts.py` + `track_v3.py`, writing back by API. Later: a GPU Cloud Run job from `exp/r2-glasses-pov` once L4 quota lands.

**Unverified or experimental dependencies (the list the design stands or falls on):**

| # | Dependency | Status | If false |
|---|---|---|---|
| UNV-1 | Recording keeps running with the phone locked in a pocket | Contradictory sources: `hvc1` "continues in the background" since 0.5.0, but 0.9.0 says "Camera Access now ends the active preview session when the app backgrounds" and the same release says the sample records "continuing while the app is backgrounded" [V, iOS CHANGELOG] | Phone sits on the ball-return shelf with the screen on; or Android foreground service [INF] |
| UNV-2 | A capture-button press reaches the app without also starting the glasses' native recording | Inputs module exists and is experimental [V]; interaction with native capture not documented [UNV] | Use audio-only cut, or a phone tap; accept duplicate native clips |
| UNV-3 | Stream-start latency after the press is under about 1 s | Not documented [UNV] | Trigger "before you pick up the ball" rather than at the approach; or stream continuously and cut |
| UNV-4 | 720x1280 Bluetooth-compressed hvc1 is enough for the ball and pin-row detectors | Tracker tuned on 1184-1424 px native clips [V]; Meta says Bluetooth drops resolution then fps under load, never below 15 fps [V via options doc] | iOS "WiFi transport" (0.8.0, no details, V) might lift quality [UNV]; Android changelog has no Wi-Fi transport line [V]. Otherwise fall back to section 9 |
| UNV-5 | Glasses and phone battery survive a 65 min stream | No figure [UNV] | Stream only between press and crash (the design already does this); keep the case nearby |
| UNV-6 | TTS routes to the glasses' speakers while a DAT session is open | Inferred from the glasses being a BT audio device [INF] | Phone speaker, or a vibration + screen |
| UNV-7 | Phone OS | Memory says Android (APK), the clips are HEVC which Meta ties to iOS [V, options doc]. Unresolved | Build for whichever phone Tom and Chardie actually carry; the SDKs are at parity on the features used here except Wi-Fi transport |
| EXP | Inputs is "experimental": cannot be published | [V] | Irrelevant for a sideloaded app |

## 8. Where the accuracy problems survive (be blunt)

1. **Release detection is untouched.** A button press gives a clip boundary a few seconds before the approach; it is not a release frame. `auto_cuts` v3 stays at 4 right, 6 wrong, 15 null of 25, and every wrong cut said `verified: true` [V, README]. The v3.1 `MIN_ROLL=45` gate is a post-hoc fit with no holdout [V]. In the live loop the choices are: (a) one LLM-vision call per clip on the release-6..+6 strip `auto_cuts` already writes, cross-checked against the audio pin hit, or (b) the release-frame tap in step 9. I would build (b) first because it is a UI on existing routes and gives labelled releases for free; (a) is unvalidated and adds a network call per throw. Either way, until a release detector is validated on a holdout, "release not found" will be spoken on roughly half the throws and the eye-read of 24 of 31 becomes a tap on about the same number.
2. **J2, the 60 ft pin-row crossing, is a tracker problem and survives unchanged.** 13 of 31 throws rendered video-only; 9 of them failed J2 (104714, 105322, 112413, 113716, 113911, 114059, 114438, 114631, 114810) [V, README table]. Nothing in the glasses path changes this, and at 720p with Bluetooth compression the pins are smaller and softer, so it may get worse (UNV-4). The round-4 extrapolated-crossing rule is a rule-owner call over the rerun budget, disclosed as such [V, RULES.md 17:40 amendment]; a product should either adopt it as J2-extrapolated with its own label or not use it.
3. **Bowler identity is the one place this design helps.** The stream lands on a specific phone, so the wearer is whoever is signed into the app. If both bowlers run the app on their own phones, step 12 of the pipeline (27 agent-minutes, clothing clusters, lane alternation, monitor OCR) disappears. If only Tom's phone runs it, Chardie's throws still need a "who is wearing them" tap at handover, and a missed tap mislabels a whole game, with no clothing fallback because nobody is reading grids any more [INF].
4. **The tracker verdict is still `partial`.** No experiment reached `works` [V]. The live loop makes a partial tracker speak with confidence; every spoken result must carry its fail class, and the end-of-session video should keep the title-card flag.
5. **Judge drift goes away, which is a gain and a loss.** Three agent judge rounds and a 3 h amend/rerun loop (12:17-15:14) are replaced by one code pass and no reruns [V, pipeline doc]. The loss is that nobody notices a systematic failure mid-session; the gain is that the numbers are the as-first-written ones.

## 9. Fallback if the toolkit cannot do it

If UNV-1 or UNV-4 fails in week 1, drop the stream and keep the native recording: option **B** (Android: Meta AI auto-import plus FolderSync/Autosync pushing the "Meta AI" gallery folder to a GCS or Drive folder) or **C1** (iPhone: a Shortcuts automation on the glasses' Bluetooth disconnect, Find Photos, POST), as written in `meta-glasses-options.md`. Full-resolution clips, no phone code, feedback per batch (import needs the glasses folded or in the case), latency minutes after folding rather than seconds after the throw. Steps 5-10 of section 3 (signed URL or bucket notification, Cloud Tasks, worker, code judge, TTS or push notification, scripted render) are the same, so none of the backend work is wasted.

## 10. First-week deliverable: prove the riskiest assumption

**The riskiest assumption is UNV-4, the 720p stream, with UNV-1 (pocket recording) as the second.** Deliverable by end of week 1:

1. Confirm the phone OS of Tom and Chardie (UNV-7). Half a day including Developer Mode pairing.
2. Build the DAT CameraAccess sample unchanged, set `hvc1` 720x1280 30 fps, and record **5 throws of Tom's** at the same alley, plus the native glasses recording of the same throws if UNV-2 allows (press once, both record). One visit.
3. Test pocket recording on 3 of them with the phone locked (UNV-1). Yes/no, logged.
4. **When the laptop is free** (a tracker batch is running on it today), run `auto_cuts.py` and `track_v3.py --device mps` on the 5 stream clips and on the 5 native twins. Report, per clip: release found or null, J1-J5 pass, entry board, pin-row source, and the entry-board difference between twin clips.
5. **Kill criterion:** the stream clips pass J1-J5 on fewer than 3 of 5 while the native twins pass on at least 3, or the ball is never detected on the lane in 2 or more stream clips. Then go to section 9 and do not build the app.
6. Side output: the 5 twin pairs are the start of a real 720p truth set, kept outside the repo like the current quarantine.

No backend or app code is written until item 5 has a number.

## 11. Cost (rough)

- **Money:** DAT SDKs free; Developer Mode free; Apple free-tier sideload (7-day re-sign) or $99/yr developer account to stop re-signing; Android APK free. GCS and Cloud Tasks for 30 clips a week: cents. A GPU Cloud Run job later (L4) is the only real line item: on the order of a dollar an hour while running, so a few dollars per session at 3-5 min per clip [INF, order of magnitude only; quota pending].
- **Effort:** week 1 spike as above, about 2 days of engineering plus one alley visit. If it passes: app with press-to-record, upload and TTS, about 1 week; backend routes and the laptop worker, 2-3 days; release-frame tap screen, 2 days; renderer argparse and durable Drive upload, half a day. Call it **3-4 weeks to a loop someone would actually use at the alley**, with the tracker's accuracy where it is. The GPU worker and a validated release detector are separate, open-ended work.

## Addendum (same day, after review)

- **UNV-8, who hears the pin crash.** Step 3 stops the recording on the mid-band crash onset, but the CameraAccess sample's "optional mic audio" is the **phone's** microphone, which is in a pocket under step 1 (muffled; the UNV-1 pocket test does not cover audio). Glasses-side audio is "camera audio streaming", which is **experimental** in 1.0.0 [V, iOS CHANGELOG]. So the automatic stop is itself unverified. Fallbacks, in order: the 25 s hard stop already in step 3; a second capture-button press; glasses audio stream if it works in Developer Mode. Add "does the pocketed phone mic register the crash" to the week-1 alley visit.
- **The onset rule is reused as a rule, not a file.** `auto_cuts.py` shells out to `ffmpeg` for the audio band energies [V, `audio_rises`]; on the phone the 40-300 Hz / mid-band onset has to be reimplemented natively over the recorded PCM.
- **The "about 400x faster" line** compares last-throw-to-rendered-video (21.6 h + ~6 h) with last-throw-to-spoken-board (about 4 min); the artefacts differ. The end-of-session video still arrives after the session.
