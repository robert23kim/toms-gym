# Implementation Plan — Upload/Analysis Pipeline Hardening (Items 1–3)

**Repo:** /Users/toka/code/toms_gym · **Date:** 2026-07-05
**Sequencing:** Items 1 and 2 run in parallel. Item 3 starts as soon as Item 2's "where does normalization run" decision is ratified (decided below: inside the engine) — not after Item 2 ships.

> Origin: produced by a planning agent after the 2026-07-05 incident (764 MiB raw
> iPhone upload → analysis timeout chain). Companion shipped work from that
> incident: iOS compression gate (`compressionPolicy.ts`), crash-surviving
> upload telemetry (`uploadJourney.ts`/`telemetry.ts`), gunicorn 300→900s
> stopgap, processing banner, and the stuck-analysis sweeper
> (`POST /admin/sweep-stuck-analysis`).

Verified line-level facts this plan is built on:

- `frontend/src/lib/videoCompress.ts:335-339` — `demuxVideo()` calls `file.arrayBuffer()` (whole file resident) and lines 325-332 push **every** sample into a `samples: Mp4Sample[]` array before any decoding starts (≈2× file size resident). `compressWithWebCodecs` (lines 399-549) then consumes the full array with proper 8-frame backpressure (`MAX_INFLIGHT_FRAMES`, line 53) — the backpressure exists only *after* the memory damage is done.
- `frontend/src/lib/compressionPolicy.ts:39-45` — `shouldCompress()` refuses all iOS (`ios-webkit`) and >200 MiB anywhere (`COMPRESS_MAX_BYTES`, line 23).
- `frontend/src/lib/resumableUpload.ts:219-247` — gate wiring; `COMPRESS_THRESHOLD = 24 MiB` (line 23); breadcrumbs via `markStage`; crash reporting via `uploadJourney.ts` + `telemetry.ts:172-180` (`action=upload-died` with `stage` and `fileSizeMB`).
- `backend/toms_gym/integrations/lifting_processor.py:171-178` — sync POST to bowling-service `/analyze-lift`, `timeout=620`.
- `backend/toms_gym/routes/jobs_routes.py:64-90` — Cloud Tasks push handler runs `_process_job` synchronously, holding a gunicorn worker; 200 = done, 500 = Cloud Tasks retry.
- `backend/toms_gym/services/analysis_dispatch.py:26-57` — enqueue with `dispatch_deadline: 900s`; never raises; gated by `ANALYSIS_DISPATCH_MODE=tasks`.
- `backend/Dockerfile:79-82` — gunicorn `--timeout 900` stopgap; comment hand-links three timeouts (620s hold / 900s deadline / 900s worker).
- `deploy.py:687-692` — `ANALYSIS_DISPATCH_MODE=tasks` live, rollback documented as `=poller`; queue `projects/toms-gym/locations/us-east1/queues/analysis-jobs`; SA `toms-gym-service@toms-gym.iam.gserviceaccount.com`.
- `backend/toms_gym/storage.py:52` — bucket `jtr-lift-u-4ever-cool-bucket` via `GCS_BUCKET_NAME`.
- Existing test seams: `frontend/src/lib/__tests__/videoCompress.test.ts`, `compressionPolicy.test.ts`, `uploadJourney.test.ts`; `backend/tests/unit/test_analysis_dispatch.py`.

---

## ITEM 1 — Streaming-demux client-side compression (re-enable iOS)

### Goal
Replace whole-file demux with incremental `file.slice()` feeding so peak memory is O(inflight frames + output buffer), not O(2× input). Then relax `shouldCompress` so iOS compresses instead of uploading 764 MiB originals.

### Design decisions

1. **Chunked feeding, honoring mp4box seek offsets.** mp4box's `appendBuffer` returns the next byte offset it wants (videoCompress.ts:238 already types the `number` return but discards it at line 339). iPhone `.mov` files frequently have `moov` at the end, so mp4box will return a jump offset after scanning `mdat` — the feeder must `file.slice(nextOffset, nextOffset+CHUNK)` from wherever mp4box asks, not just march linearly. Chunk size: 8 MiB (matches `CHUNK_SIZE` in resumableUpload.ts).
2. **Bounded sample queue + demux-level backpressure.** `setExtractionOptions(trackId, null, { nbSamples: 100 })` instead of the current all-samples-at-once (line 321). `onSamples` pushes into a bounded async queue; the *file feeder pauses* (stops appending chunks) above a high-water mark. After each batch is fed to the decoder, call `mp4file.releaseUsedSamples(trackId, lastSampleNumber)` so mp4box frees its internal copies — this is the second half of the memory fix; chunked appends alone don't help if mp4box retains every extracted sample.
3. **Muxer target: keep `ArrayBufferTarget`, add a duration gate.** Output at 2.5 Mbps ≈ 19 MB/min — fine in memory for 1–10 min clips, but a 30-min video would buffer ~560 MB (`fastStart: "in-memory"` holds everything anyway). Gate: if track duration (known at `onReady`) exceeds **15 minutes**, skip compression and upload the original, with a telemetry reason. `StreamTarget` + chunked Blob assembly is a documented follow-up, not v1.
4. **HEVC handling.** iPhone default capture is HEVC (`hvc1`/`hev1`); Safari's `VideoDecoder` supports it, others may not. At `onReady`, before building the pipeline, probe `VideoDecoder.isConfigSupported({codec: sourceCodec, description})`. Unsupported → throw a typed `DecodeUnsupportedError`. On iOS the call site must use `fastPathOnly: true` so this falls through to **uploading the original**, never the MediaRecorder realtime path. `compressVideo`'s existing catch-and-fall-through (lines 108-137) gives this for free once `fastPathOnly` is set.
5. **Framerate derivation without the full sample array.** Current code sums all sample durations (lines 417-421). Replace with `nb_samples / (track.duration / track.timescale)` from the `onReady` info (add `duration` to `Mp4VideoTrackInfo`), fallback 30.
6. **Policy relaxation — staged.** `shouldCompress` changes: new field `mode: "auto" | "fast-only"` (`fast-only` for iOS); iOS allowed with a **1 GiB** sanity cap; reasons extended to `"ok" | "ok-ios-fast-only" | "file-too-large" | "duration-too-long"` (last reported from inside videoCompress via markStage since duration isn't known at gate time); non-iOS cap raised 200 MiB → 1 GiB. `resumableUpload.ts:219-236` consumes `decision.mode` to set `fastPathOnly` (ORed with caller `options.compression`).

### Tasks

| # | Task | Files |
|---|---|---|
| 1.1 | Pure, jsdom-testable chunk feeder: `createChunkFeeder(file, mp4file, chunkSize)` with `pause()/resume()` and seek-offset honoring; move/extend the `Mp4File` interface decls (add `releaseUsedSamples`) | new `frontend/src/lib/mp4Stream.ts` |
| 1.2 | Bounded sample queue (`AsyncSampleQueue`, high-water 100 / low-water 25) with release accounting — pure data structure | `mp4Stream.ts` |
| 1.3 | Rewrite `demuxVideo` → `streamDemux(file, callbacks)`; rework `compressWithWebCodecs` to consume the stream: onReady → probe decoder support → configure decoder/encoder/muxer → feed loop pulls from queue with existing MAX_INFLIGHT_FRAMES backpressure → flush. Keep `compressVideo`'s public signature and NEVER-throws/never-bigger contract untouched (lines 17-19, 90-138, 141-143). Progress = `samplesProcessed / nb_samples` mapped over 10→90% | `videoCompress.ts` |
| 1.4 | Duration gate + `DecodeUnsupportedError` + breadcrumbs (`compress-skip-duration`, `compress-hevc-unsupported`) via existing `markStage` | `videoCompress.ts`, `resumableUpload.ts` |
| 1.5 | Policy change: iOS enabled fast-only, caps raised, `mode` field — one small isolated diff, this is the rollback lever | `compressionPolicy.ts`, `resumableUpload.ts:219-236` |
| 1.6 | Tests + device verification pass | `frontend/src/lib/__tests__/` |

### Test strategy
**Unit (jest/jsdom — WebCodecs unavailable, so test up to the codec boundary):**
- `mp4Stream.test.ts`: feeder issues slices at mp4box-requested offsets (mock `Mp4File` returning linear offsets then a jump simulating moov-at-end); pauses at high-water, resumes at low-water; `releaseUsedSamples` called with monotonically increasing sample numbers; total bytes appended == file size; never-emits-samples mock rejects (preserves the "no video samples extracted" fallback path).
- `compressionPolicy.test.ts` update: iOS now `{compress: true, mode: "fast-only"}`; 1 GiB caps; UA/touch-point matrix unchanged.
- `videoCompress.test.ts` update: contract regression tests (resolves with original on unsupported/demux failure) extended, not replaced. Framerate helper table-driven.

**Manual device matrix (before relaxing policy in prod):**
- iPhone Safari, HEVC .mov ~700 MiB (reproduce the 764 MiB prod case) → compress-done, no reload
- iPhone Safari, H.264 ~100 MiB → compress-done
- iPhone without HEVC WebCodecs → original uploaded, `compress-hevc-unsupported` breadcrumb, no MediaRecorder attempt
- Android Chrome 4K 500 MiB (previously blocked by 200 MiB cap) → compress-done
- Desktop Chrome: 24 MiB boundary + >1 GiB → compress vs. skip

**Field loop (already built):** after deploy, watch Cloud Run logs for `FRONTEND_ERROR` `action=upload-died`, filter `stage=compress-*`. A death at compress-start on iOS means the streaming fix isn't holding; journey carries `fileSizeMB`.

### Verification
```bash
cd frontend && npm test -- mp4Stream videoCompress compressionPolicy uploadJourney
cd frontend && npx tsc --noEmit && npm run build
python3 deploy.py --frontend-only --skip-iam
# device pass at https://my-frontend-quyiiugyoq-ue.a.run.app/upload
gcloud logging read 'textPayload:"FRONTEND_ERROR" AND textPayload:"upload-died"' --project=toms-gym --freshness=7d
```

### Rollback
Cheap lever: revert Task 1.5 only (compressionPolicy.ts) — iOS back to `compress:false`; streaming code stays (strictly better on desktop too). One-file revert + frontend deploy. Full lever: revert branch; the never-throws contract means worst case is today's behavior (originals upload).

### Success criteria
1. 764 MiB-class iPhone HEVC video: tab survives; compressed output or original uploads via typed fallback — zero Safari auto-reloads (device-verified + 7-day telemetry: no `upload-died` at compress stages on builds ≥ this `APP_BUILD`).
2. Jest green, `tsc --noEmit` clean, existing contract tests untouched-and-passing.
3. Peak JS heap compressing a 700 MiB file < ~300 MB in Safari Web Inspector.
4. Desktop behavior unchanged for files < 200 MiB.

**Estimate:** 3–5 days (≈2 code, 1 test, 1–2 device verification + telemetry soak).

---

## ITEM 2 — Server-side video normalization before analysis

### Decision: normalize **inside bowling-service**, first step of every analysis, writing the normalized copy to GCS
- Backend container has no ffmpeg, 1 CPU/2 GiB, and a transcode hold there recreates the request-lifetime problem Item 3 removes.
- A separate normalization service/job is a third moving piece with its own dispatch/retry story — unjustified when the engine already downloads the video and owns the CPU.
- **Item-3-proof:** whether analysis runs as a Cloud Tasks push or a Cloud Run Job, the normalize step travels with the engine unchanged.
- Item 1 reduces how often this does heavy work but never removes the need: iOS fallbacks, direct API uploads, and email uploads still deliver raw 4K.

### Contract (cross-repo interface to freeze)
- **Naming:** `normalized/{original_object_path}.720p15.mp4` in `jtr-lift-u-4ever-cool-bucket` — deterministic, so idempotency needs no DB.
- **ffmpeg:** `ffmpeg -y -i src -vf "scale=-2:'min(720,ih)':flags=bicubic,fps=15" -c:v libx264 -preset veryfast -crf 23 -an -movflags +faststart out.mp4` (15 fps matches the analyzer's existing subsample rate; `-an` since analysis is visual; `-2` keeps width even).
- **Idempotency:** before encoding, HEAD the normalized blob; reuse iff its custom metadata `source-generation` equals the source blob's current GCS generation (re-uploads get new generations and correctly re-normalize).
- **Skip condition:** source already ≤ 720p and ≤ ~50 MB → use original URL (don't re-encode Item-1 output).
- **Response:** `/analyze` and `/analyze-lift` gain nullable `normalized_video_url`. Env flag `NORMALIZE_BEFORE_ANALYZE` in bowling-service (false at first deploy, true after soak).
- **Cleanup:** GCS lifecycle rule deleting `normalized/` objects after 30 days (pure derivatives, re-created on demand).

### Tasks
| # | Task | Where |
|---|---|---|
| 2.1 | Write the contract into `docs/plans/2026-07-05-video-normalization.md`; get engine owner ack. Blocks 2.2 and Item 3 kickoff | this repo |
| 2.2 | `normalize_video(video_url) -> normalized_url`: download → ffprobe → skip-or-encode → upload with `source-generation` metadata; wire as step 0 of both analyze endpoints; add ffmpeg to image if absent | **bowling-service repo** |
| 2.3 | Migration 013: nullable `normalized_video_url` on `LiftingResult` + `BowlingResult` (startup-migration pattern like ShortLink/Ticket 012). Additive | backend migrations |
| 2.4 | Persist `result.get("normalized_video_url")` in both success UPDATEs; tolerate absence (older engine) | `lifting_processor.py:185-200`, `bowling_processor.py:177-200` |
| 2.5 | Lifecycle rule, prefix-scoped so it can never touch originals: `gcloud storage buckets update gs://jtr-lift-u-4ever-cool-bucket --lifecycle-file=...` with `matchesPrefix: ["normalized/"]`, age 30; review the JSON twice | docs + one-time command |
| 2.6 | Regression A/B: run analyzer on `backend/tests/fixtures/test_video_plank_10s.mp4` + one bowling + one squat fixture pre/post normalization; diff rep counts / entry boards. Guards against 15fps-input × 15fps-subsample double-decimation — if the engine's subsampler assumes 30fps input timing, fix it to read container fps | manual + engine tests |

### Verification
```bash
cd backend && venv/bin/python -m pytest tests/unit -x
gcloud storage ls -L gs://jtr-lift-u-4ever-cool-bucket/normalized/ | head
# second dispatch of same video logs "normalized copy exists, skipping encode"
# LiftingResult.normalized_video_url populated; analysis wall time bounded in engine logs
```

### Rollback
`NORMALIZE_BEFORE_ANALYZE=false` on bowling-service (config-only). DB column and lifecycle rule are inert with the flag off.

### Success criteria
1. 764 MiB 4K upload → `normalized/` object ≤ ~50 MB; engine analyzes the normalized copy; analyze wall time bounded regardless of input size.
2. Re-dispatch reuses the copy (no second encode in logs).
3. Fixture results unchanged pre/post (2.6).
4. `normalized/` prefix under lifecycle control (no orphan growth).

**Estimate:** 2–3 days (~0.5 in this repo; 1.5–2 in bowling-service incl. the A/B).

---

## ITEM 3 — Decouple analysis from request lifecycles

### Evaluation
- **(a) Cloud Run Jobs execution per analysis — RECOMMENDED.** No request timeout anywhere in the chain; executions get their own machine class — exactly where the pending NVIDIA L4 quota attaches (`gcloud run jobs update --gpu`); retries are Jobs-native; scale-to-zero cost. Needs a result callback since the engine has no DB access.
- (b) Engine-side queue pull — rejected: requires an always-on puller (kills scale-to-zero) or Pub/Sub push, which is just (c) with more parts.
- (c) Cloud Tasks → engine direct + callback — viable smaller step but still request-bound: dispatch_deadline caps at 30 min, engine request timeout still exists (heavy plank already 8.8 min on CPU, trajectory up), and GPU on Cloud Run *services* forces always-allocated CPU pricing. It recreates the "N timeouts must agree" disease at a higher ceiling — the exact thing the July strategic review flagged.

Any architecture where analysis duration lives inside an HTTP request needs another timeout patch in six months. Jobs is the only option with no clock.

### Target architecture
```
upload → LiftingResult(queued) → dispatch (mode='jobs'):
  backend launches Cloud Run Jobs execution (job=lifting-analyzer,
    args=[--kind lifting --result-id <id> --video-url <url> --lift-type <t> --callback <backend>])
  backend marks row 'processing' at dispatch
Job container (bowling-service image, CLI entrypoint):
  normalize (Item 2 code path) → analyze → POST OIDC-signed result to
  backend POST /jobs/<kind>/<result_id>/complete
Backend callback: validates OIDC (engine SA), stores via the same UPDATE logic
  _process_job uses today, flips Attempt status.
Sweeper: 'processing' > threshold → 'failed' (safety net for lost executions).
```

**State machine (explicit — sweeper and late callbacks will race):**
- queued → processing: dispatcher at launch
- processing → completed/failed: callback
- processing → failed: sweeper (age > threshold)
- **failed → completed: late callback (job retry finished after sweeper fired) — late success wins, clears `error_message`**
- completed → anything: forbidden; callback 200s idempotently (mirrors `jobs_routes.py:80`)

**Sweeper interaction (landed 2026-07-05, processing>30min→failed):** with job task timeout 20 min and `maxRetries=1`, worst-case legitimate runtime ≈ 40 min + scheduling. Plan: **both** (i) raise sweeper threshold to **60 min** once mode=jobs is live, and (ii) allow the failed→completed late-success transition as belt-and-braces. Note for the sweeper: do **not** make `failed` terminal in any DB constraint.

**Retries:** Jobs `maxRetries=1` handles engine crashes/OOM. Callback client retries 3× with backoff before exiting non-zero (execution retry as last resort). Cloud Tasks retry machinery drops out of the analysis path entirely (mode `tasks` kept only during transition).

### Tasks
| # | Task | Files |
|---|---|---|
| 3.1 | Refactor result storage out of `_process_job`: `store_lifting_success/failure(...)` (+ bowling equivalents) so sync path and callback share one implementation. Pure refactor, lands first, alone | `lifting_processor.py:185-226`, `bowling_processor.py:174-234` |
| 3.2 | Dispatch: `ANALYSIS_DISPATCH_MODE` gains `jobs`; `enqueue_analysis_job` branches to `google.cloud.run_v2.JobsClient.run_job` with container-args overrides; marks row `processing` on successful launch; still never raises (launch failure → row stays `queued` for sweeper/manual). New env: `ANALYSIS_JOB_NAME_LIFTING/_BOWLING` + region; `google-cloud-run` in requirements | `analysis_dispatch.py`, `requirements.txt` |
| 3.3 | Callback `POST /jobs/<kind>/<result_id>/complete`: OIDC verify (reuse `_verify_oidc` pattern, expected SA = new env `ENGINE_SERVICE_ACCOUNT`); body `{status, annotated_video_url?, summary_url?, report?, processing_time_s?, normalized_video_url?, error_message?}`; enforce state machine; idempotent 200 on repeat. Existing push handlers untouched (serve mode=tasks during cutover) | `jobs_routes.py` |
| 3.4 | Engine CLI entrypoint `job_main` (normalize → analyze → callback with OIDC token, audience = backend URL; exit non-zero only when callback delivery ultimately fails). No HTTP server in the job | **bowling-service repo** |
| 3.5 | Infra: `gcloud run jobs create lifting-analyzer` / `bowling-analyzer` (bowling-service image, `--task-timeout=1200s --max-retries=1 --memory=4Gi --cpu=2`, callback base URL env); IAM: backend SA gets `run.jobs.run`. Pin job image to the same digest the bowling-service *service* runs so both modes analyze identically during cutover. GPU flag added when L4 quota lands | `deploy.py` or `scripts/` |
| 3.6 | Sweeper coordination: 60-min threshold under mode=jobs + confirm failed→completed permitted | `admin_routes.py` sweeper |
| 3.7 | Cutover + cleanup: flip `deploy.py:689` to `ANALYSIS_DISPATCH_MODE=jobs` (lifting first, bowling ~2 days later); after 7-day clean soak, drop gunicorn `--timeout` 900 → 120 (`backend/Dockerfile:82`) and fold into the existing poller-deletion task (Task 11, on/after 2026-07-10) | `deploy.py`, `backend/Dockerfile` |

### Test strategy
- **Unit** (extend `tests/unit/test_analysis_dispatch.py` pattern): mode branching (`poller`/`tasks`/`jobs`), run_job override args, never-raises on launch failure with row left `queued`.
- **Unit, callback:** table-driven state-machine matrix — every (current_status × callback_status) cell, incl. failed→completed clearing `error_message` and completed→* idempotent 200 without UPDATE; OIDC rejection paths (wrong SA, wrong audience, missing header).
- **Unit, refactor (3.1):** pin existing `_process_job` behavior first (success UPDATE fields, 1000-char error truncation at `lifting_processor.py:214`, Attempt auto-complete lines 202-209).
- **Integration (prod, flag-gated):** with mode still `tasks`, manually `gcloud run jobs execute lifting-analyzer --args=...` against a synthetic queued row; verify callback lands, row completes, Attempt flips. Then flip mode for lifting only, push one real upload.
- **Failure drills before declaring done:** kill an execution mid-run (Jobs retry → completed); temporarily block the callback route (job exits non-zero, retry succeeds); let a row age past threshold (sweeper fails it, late callback resurrects it).

### Verification
```bash
cd backend && venv/bin/python -m pytest tests/unit/test_analysis_dispatch.py tests/unit/ -x
gcloud run jobs executions list --job=lifting-analyzer --region=us-east1
gcloud logging read 'resource.type="cloud_run_job" AND resource.labels.job_name="lifting-analyzer"' --freshness=1d --project=toms-gym
gcloud tasks queues describe analysis-jobs --location=us-east1 --project=toms-gym  # tasks-mode traffic → 0
```

### Rollback
`ANALYSIS_DISPATCH_MODE=jobs → tasks` (config-only; exact precedent in `deploy.py:687-688` from the 2026-07-03 cutover; `poller` remains the deep fallback until Task-11 deletion). Push handlers, queue, and IAM stay intact until post-soak cleanup. Do **not** lower the gunicorn timeout (3.7) until rollback is off the table.

### Success criteria
1. Zero gunicorn workers held by analysis: `/jobs/*/complete` p99 < 1 s; no backend 503/worker-timeout lines during long analyses.
2. A deliberately slow analysis (> 15 min) completes — impossible today — proving the request clock is gone.
3. All failure drills pass with documented transitions; no row permanently stuck in `processing`.
4. Post-soak: gunicorn timeout back to 120 s and the three-way hand-synced timeout comment in `backend/Dockerfile:79-81` deleted.
5. L4 GPU attach is a `gcloud run jobs update`, no code change.

**Estimate:** 4–6 days (1 refactor+dispatch, 1 callback+tests, 1 engine CLI cross-repo, 0.5 infra, 1–2 cutover drills + staged flip) + 7-day passive soak before cleanup.

---

## Risk register (top 5)

1. **iOS WebCodecs edge cases (HEVC configs, VideoFrame GPU-buffer pressure) still kill the tab** — Item 1, Med/High. Mitigation: fastPathOnly on iOS + never-throws fallback to original; policy relaxation is a one-file revert; `upload-died` telemetry gives per-build crash visibility within hours.
2. **mp4box streaming quirks (moov-at-end seeks, fragmented MP4s, `releaseUsedSamples` mis-accounting)** — Item 1, Med/Med. Mitigation: honor `appendBuffer` return offsets by design; unit-test seek jumps against a mocked Mp4File; real-file corpus for the manual pass; any demux failure falls back to original upload.
3. **Sweeper vs. long-running Jobs race → wrong statuses or double-processing** — Item 3, High-if-uncoordinated/Med. Mitigation: explicit state machine with late-success allowed; sweeper threshold ≥ job worst case (60 min); coordinated before Item 3 lands.
4. **Normalization silently changes analysis outputs (fps resample vs. engine's own 15fps subsampler double-decimating)** — Items 2→3, Med/High (no accuracy eval exists per strategic review). Mitigation: Task 2.6 fixture A/B before enabling; `NORMALIZE_BEFORE_ANALYZE=false` instant rollback.
5. **Cross-repo coordination drift (bowling-service owns 2.2 + 3.4)** — Items 2–3, Med/Med. Mitigation: contract frozen in the Task 2.1 doc before engine work starts; job image pinned to the service's digest during cutover.

## Sequencing & totals
```
Week 1:  Item 1 (frontend) ─────────────────► device verify → policy flip → telemetry soak
         Item 2 (contract → engine + backend) ► fixture A/B → enable flag
Week 2:  Item 3 (starts once the normalize-in-engine decision is ratified;
         engine CLI reuses Item 2's normalize step) ► drills → lifting cutover → bowling cutover
Week 3:  soak → gunicorn timeout restore + poller deletion (aligns with existing Task 11)
```
Total ~9–14 engineering days across the two repos, with two config-only rollback levers (`compressionPolicy` revert, `ANALYSIS_DISPATCH_MODE`) available at every stage.
