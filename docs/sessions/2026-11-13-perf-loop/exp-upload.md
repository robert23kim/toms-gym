# Experiment: upload time (2026-11-13)

Branch `perf/upload-analysis-2026-11-13`, worktree `/Users/toka/code/toms_gym-perf`. Nothing here is deployed.

## Headline

- The part of an upload the backend can see is short: **median 6.65 s** from the signed-URL request to the analysis request being accepted (n=28 real uploads, 14 days). Signing, finalize, the two CORS preflights and the analysis trigger together are about 0.5 to 0.9 s of that. The rest is the PUT.
- The part the backend cannot see is longer on Android. Every Android upload was compressed on the phone first, and the encode took **7 to 21 s, about 0.25 s per second of clip** (read off the container timestamps of 5 fixtures, one device). Then the PUT took 1 to 12 s.
- iPhone uploads are slow because of the link, not the code: **median 5.5 Mbit/s** (0.7 to 12.9) against 45.5 Mbit/s on the Android phone. The files are already tiny (480x360, 0.7 Mbit/s).
- No cheap change moves the median for these 28 uploads. Two changes are committed: client timing telemetry so the next pass has real-device numbers, and removal of a realtime fallback that cost a full clip length when hit (0 of 28 hit it).

## 1. Baseline from prod logs (my-python-backend, 2026-10-30 to 2026-11-14)

Source: `gcloud logging read` on the app log lines and on the Cloud Run request log, plus `gcloud storage ls -l` for object sizes. Scripts: `upload/parse_logs.py`, `upload/baseline.py`. Full per-upload table: `upload/baseline-table.md`. The raw pulls contain emails, IPs and user agents, so they sit outside the repo in `/Users/toka/code/bowling-app/perf-fixtures-2026-11-13/upload-logs/`.

Path taken: **28 single PUT, 0 composite, 0 resumable.** Largest object 27.3 MB; the parallel path starts at 32 MiB. Two more `POST /upload` (legacy multipart) calls exist, both `curl` on 2026-10-31, 6.8 MB each: the 100 Club prod proof, not users. All 28 are in the live 100 Club challenge. 13 distinct client IPs.

| | n | size MB (median, max) | PUT window s (median, p90, max) | Mbit/s, lower bound (min, median, max) | sign to analysis accepted s (median, p90, max) |
|---|---|---|---|---|---|
| All | 28 | 10.4, 27.3 | 5.6, 14.9, 88.1 | 0.7, 14.1, 92.0 | 6.65, 19.96, 88.88 |
| Android WebView (the APK, SM-S926U1) | 14 | 18.3, 27.3 | 3.4, 6.6, 11.7 | 15.2, 45.5, 92.0 | 4.08, 7.53, 12.17 |
| iOS Safari | 14 | 6.3, 12.4 | 9.7, 20.2, 88.1 | 0.7, 5.5, 12.9 | 10.50, 21.05, 88.88 |

Content type: 14 `video/mp4` (Android), 14 `video/quicktime` (iOS). Lifts: 11 Pushup, 8 Situp, 8 Plank, 1 Squat.

"PUT window" runs from the sign response leaving the backend to the finalize preflight arriving, so it holds the PUT plus one client round trip. The Mbit/s column is therefore a lower bound on the real transfer rate.

Control-plane cost per upload (backend request log, n=28):

| step | median | p90 | max |
|---|---|---|---|
| sign preflight to sign POST (one round trip) | 0.10 s | 0.16 s | 4.42 s |
| `/upload/signed-url` server time | 0.09 s | 0.12 s | 0.14 s |
| finalize preflight to finalize POST | 0.10 s | 0.16 s | 0.33 s |
| `/upload/finalize` server time | 0.10 s | 0.14 s | 0.41 s |
| finalize response to `/lifting/analyze` arriving | 0.12 s | 0.19 s | 0.24 s |
| `/lifting/analyze` server time | 0.18 s | 0.55 s | 0.69 s |

Client telemetry in the same window (303 `FRONTEND_ERROR` lines): boot 172 (157 web, 15 capacitor), resource-error 107 (avatar SVG loads), window-error 20, render-error 4. **`upload-died`: 0. `video-upload` (reportUploadError): 0.** The filter matched every `FRONTEND_ERROR` line, so those zeros are real for reports that reached the backend; a report that never got sent is invisible.

### What the logs cannot see

- Time compressing on the phone before the first byte.
- Time between picking the file and the signed-URL request (taps, the iOS picker export).
- The original file size before compression.
- Whether a slow PUT was a slow link or a backgrounded tab.
- Anything about an upload that never reached the sign request.

### What the fixtures add (inferred, not logged)

The 5 Android fixtures are all 1280x720, 30 fps, about 2.55 Mbit/s, no audio, with handler `mp4-muxer-hdlr`. That is the output of our own WebCodecs pipeline, so compression ran on every one. The other 9 Android objects were not downloaded; their sizes and timings fit the same pipeline, but that is not verified. mp4-muxer stamps `creation_time` in its constructor, which runs right before the encode loop, so sign time minus `creation_time` is the encode time (plus one round trip, +-1 s):

| fixture | clip s | encode s | per clip second |
|---|---|---|---|
| Pushup | 28.4 | 7.4 | 0.26 |
| Pushup | 34.1 | 9.1 | 0.27 |
| Situp | 57.5 | 14.3 | 0.25 |
| Situp | 66.2 | 16.8 | 0.25 |
| Plank | 86.5 | 20.9 | 0.24 |

One device (Samsung S24+, WebView Chrome 156), five clips. The camera file name gives recording start; from that, recording end to sign was 10 to 31 s on all 14 Android uploads (`upload/android-presign-bound.json`; 9 of the 14 clip lengths are estimated from file size), which is the encode plus the taps.

The 3 iOS fixtures are 480x360, 24 fps, 0.7 Mbit/s H.264. Recording end to sign was 4.0, 16.1 and 23.3 s: taps plus the iOS picker export, which we do not control.

Does compression pay on that Android phone? Unknown, because the original size is not logged. It costs 0.25 s per clip second and saves (source bitrate minus 2.56 Mbit/s) of transfer per clip second, so it breaks even at an uplink of 4 x (source minus 2.56) Mbit/s: about 58 Mbit/s for a 17 Mbit/s source (an assumption, not a measurement). That phone measured 15 to 92 Mbit/s, median 45.5. So it is close to break-even on time there and a clear win on slower links. The new telemetry logs `srcBytes`, which settles it.

## 2. Code read: the September findings against current code

- **"Non-Plank lifts pass `auto`": true, but the stated consequence was wrong.** `ChallengeDetail.tsx:235` and `PromptList.tsx:149` pass `auto` for anything but Plank; `UploadVideo.tsx` passes nothing, so it was `auto` for Plank too. But `runUpload` only attempts compression when `canCompressVideo()` is true, so a browser without WebCodecs uploads the original and never reaches MediaRecorder. The realtime fallback ran only when WebCodecs exists and the encode throws or saves under 10 %.
- **Analysis trigger is a second round trip: true** in all three callers. Measured cost: 0.12 s gap plus 0.18 s server time at the median.
- **Parallel settings:** `PARALLEL_THRESHOLD` = `RESUMABLE_THRESHOLD` = 32 MiB, so the plain resumable tier is only reachable as the fallback. Part size 16 MiB, 4 in flight, 3 attempts per part. The doc comment said 48 MiB; corrected.
- **Compression gate:** files under 24 MiB, any iOS device, and files over 200 MiB are not compressed.
- **Preflights:** the backend sends no `Access-Control-Max-Age`, so sign and finalize each cost a preflight on every upload (28 OPTIONS for 28 POSTs on both).

## 3. Experiments

### Compress cost against bytes saved (MacBook, headless Chrome 157 via Playwright `channel: 'chrome'`, other jobs running on the laptop)

Harness: `upload/harness/entry.ts` + `run.mjs`, bundled with esbuild so nothing is written into the shared `node_modules`. Results: `upload/compress-harness-results.json`. A laptop is not a phone: the same encode ran at 0.08 s per clip second here against 0.25 on the S24+. The 1080p sources are synthetic (fixtures upscaled with ffmpeg to 1920x1080 at 17 Mbit/s), because the originals were never uploaded.

| input | mode | in MB | out MB | time | MediaRecorder ran |
|---|---|---|---|---|---|
| synthetic 1080p pushup, 28 s | fast-only (n=3) | 59.7 | 8.9 | 2.4 to 3.2 s | no |
| synthetic 1080p pushup, 28 s | auto | 59.7 | 8.9 | 2.4 s | no |
| synthetic 1080p plank, 86 s | fast-only | 185.1 | 26.8 | 7.2 s | no |
| plank fixture, already 720p, 86 s | fast-only (n=2) | 27.3 | 27.3 (original) | 6.2 s | no |
| plank fixture, already 720p, 86 s | **auto (n=2)** | 27.3 | 27.3 (original) | **92.7 s** | **yes** |
| situp fixture, already 720p, 57 s | fast-only | 18.4 | 18.4 (original) | 4.1 s | no |
| situp fixture, already 720p, 57 s | auto | 18.4 | 18.4 (original) | 61.6 s | yes |
| iOS squat fixture, 360p .mov, 32 s | fast-only | 3.1 | 3.1 (original) | 2.0 s | no |
| iOS squat fixture, 360p .mov, 32 s | auto | 3.1 | 3.1 (original) | 34.0 s | yes |

The synthetic 1080p rows are the canary that the encoder works in this browser. With that proven, the `auto` rows show the pathology: when WebCodecs cannot shrink the clip, `auto` plays the whole clip through MediaRecorder and then keeps the original anyway. Only the plank row is over the 24 MiB gate, so only that one could happen in the app today.

### Signing endpoints from the laptop (wifi, unused `perf-bench-unused.mp4` URLs, nothing uploaded)

`upload/sign-probe.txt`. `/upload/signed-url` on a new connection: 0.14 to 0.18 s (n=7). On a reused connection: 0.10 s, and the preflight 0.09 s. `/upload/composite/sign` with 4 parts: 0.17 to 0.20 s (n=3).

`/upload/finalize` was not probed on prod: if its storage check throws, the handler carries on and creates an attempt. The 28 real finalize latencies above cover it.

## 4. What changed

Two commits, frontend only.

**`4af22d5 feat(upload): report client upload timing through the telemetry route`**
Each successful upload sends one `upload-timing` event through `/log-error` (logged as `FRONTEND_ERROR page=upload action=upload-timing`). It is emitted once inside `uploadVideo`, so all three callers are covered without touching them. Fields: `liftType`, `mode`, `compress` (`skipped:<reason>`, `kept-original`, `webcodecs`, `mediarecorder`), `path` (`single-put`, `parallel`, `resumable`, `resumable-fallback`), `srcBytes`, `sentBytes`, `srcType`, `sentType`, `compressMs`, `signMs`, `putMs`, `completeMs`, `finalizeMs`, `transferMs`, `totalMs`, `putMbps`, `hiddenCount` (times the page went to the background), `netType`, `netEffective`, `netDownMbps`. No file name. `reportError` now caps `userAgent` and `url` at 300 characters, because `/log-error` drops any body over 2 KB without logging it. New file `frontend/src/lib/uploadTiming.ts`; an optional timer argument is threaded through `upload.ts`, `parallelUpload.ts` and `uploadVideoResumable`.

**`962dd5b perf(upload): never run the realtime MediaRecorder fallback before an upload`**
`uploadVideo` defaults to `fast-only` and treats `auto` as the same thing. Effect on the 28 observed uploads: none (all 14 Android encodes succeeded in WebCodecs, iOS is not compressed). Effect when hit: one clip length less waiting (92.7 s to 6.2 s on the laptop for the 86 s clip), and a canvas re-recording can no longer stand in for the athlete's video. It does not change which files WebCodecs compresses or what it produces, so rep counts, the clean/sloppy split and plank hold time are untouched for every clip that uploads today.

### Checks

- jest, full suite, `--coverage=false --maxWorkers=4`: 113 suites, 810 tests, all pass (24 tests are new, in `uploadTiming.test.ts`, `uploadVideoTiming.test.ts`, `uploadVideoCompression.test.ts`).
- Mutation checks: 16 of 16 mutants killed (12 telemetry, 4 fast-only), each mutation re-read from disk and restored from memory. Specs and results in `upload/gates/`.
- `tsc --noEmit -p tsconfig.app.json`: 49 error lines, the identical set on a clean export of base `b5792eb` and on HEAD; none in the new files. A planted type error in `uploadTiming.ts` was caught. Bare `npx tsc --noEmit` uses a root tsconfig with `files: []` and checks nothing, which is why `-p` was used.
- Real browser: `uploadVideo` itself ran in headless Chrome against a local fake backend (`upload/harness/entry2.ts`, `run2.mjs`, results `upload/upload-harness-after.json`). Five cases covered single PUT, WebCodecs compression, kept-original under `auto`, and the 4-part parallel path. Each sent one event by `sendBeacon` as `text/plain`, 624 to 635 bytes, with no request leaving localhost and no MediaRecorder start.
- Backend gate (`tools/run_ci_tests.sh`): not run, no backend file changed.
- Not checked: a phone, iOS Safari, the APK, or the event landing in prod logs. The receiving route is the one boot pings already use.

## 5. Left alone, on purpose

- **Compression policy (threshold, 720p, bitrate, iOS skip).** Changing which clips get re-encoded changes what the analyzer sees, and form changes the score in the live challenge. It is also near break-even on the one Android phone measured.
- **Encode speed (the canvas scale step, encoder settings).** Likely where the 0.25 s per clip second goes, but any change alters output pixels and needs an engine equivalence run on a phone-made file.
- **Trigger analysis inside finalize.** Worth about 0.3 s at the median against 6.65 s, needs a coordinated backend and frontend deploy, and stale clients (the APK) would trigger twice.
- **Part size, concurrency, `PARALLEL_THRESHOLD`.** 0 of 28 uploads used the parallel path. No evidence either way; `putMbps` by `path` will provide it.
- **CORS preflight caching.** One line (`max_age` in the `CORS(...)` block of `app.py`) would drop up to two round trips per repeat upload, about 0.1 to 0.3 s. Not done: small, a backend deploy, and `app.py` is being edited by the other session.
- **Skip the encode when the source is already at or under 720p and 2.5 Mbit/s.** It would save the wasted WebCodecs pass (6.2 s on the laptop, about 0.25 x clip length on the S24+). 0 occurrences in 14 days, so not built.
- **The callers.** `ChallengeDetail.tsx` and `PromptList.tsx` still pass `auto` for non-Plank lifts; it now means fast-only. Left untouched to avoid conflicts with the bug-fix session. `PromptList.test.tsx` still asserts `auto`.
- **iOS link speed.** Nothing cheap in our code; the files are already 0.7 Mbit/s.
- **The 200 MiB compression cap.** An 86 s plank at 17 Mbit/s would be about 184 MB; a plank a little longer skips compression and uploads the full file through the parallel path. Not observed. `compress=skipped:file-too-large` will show it.

## 6. For the next pass

- The Android half of the traffic is the APK. It will not send `upload-timing` until the frontend is deployed **and** the APK is rebuilt and published.
- Query: `textPayload:"action=upload-timing"` on `my-python-backend`. `details=` is a Python dict repr (single quotes, `None`), so parse it with `ast.literal_eval`.
- Questions the data answers: `compressMs` against `(srcBytes - sentBytes) * 8 / putMbps` per device (does compression pay), `putMbps` on iOS with `hiddenCount` (link or backgrounding), and how often `compress` is `kept-original`.
- These events are logged at WARNING under the `FRONTEND_ERROR` prefix, like boot pings. Anything counting that prefix will count them.
