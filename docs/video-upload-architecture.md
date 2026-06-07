# Video Upload Architecture

**Date:** 2026-06-06
**Status:** Shipped to production (`main`)
**Scope:** Lifting / challenge video uploads (`/upload` flow). Golf scorecard and bowling uploads are separate.

---

## TL;DR

Video uploads now go **directly to Google Cloud Storage from the browser**, bypassing Cloud Run's 32 MiB request limit that was silently failing large phone videos. Large videos are **compressed to ~720p client-side first**, then sent over the **fastest reliable transfer method for their size** (parallel → resumable → single-PUT), with progress, resume, interrupt guards, and failure telemetry throughout.

The single entrypoint is `uploadVideo()` in `frontend/src/lib/resumableUpload.ts`.

---

## The problem (root cause)

Two friends (one iPhone, one Android) "couldn't upload." Investigation found **zero server-side trace** of their attempts — not in the Flask app logs, not in the Cloud Run request logs.

**Cloud Run hard-caps request bodies at 32 MiB.** Anything larger is rejected by the Google Front End with `413 Request Entity Too Large` (an HTML response) **before the request reaches Flask** — so the app never logs it. Confirmed with a live test: a 40 MB `POST /upload` → 413 HTML; a 10 MB POST reached Flask.

The app's `MAX_CONTENT_LENGTH = 500 MB` (`backend/toms_gym/app.py`) is meaningless because the platform rejects first. A normal phone video easily exceeds 32 MB (a real Pixel test file was **372 MB**: 1080p HEVC, 2m37s). Bumping Cloud Run CPU/memory does **not** lift the 32 MiB cap.

> Older "Lifting analysis failed" log errors (NaN JSON, a 404 to a stale `analysis-engine` URL) are a *different*, already-fixed issue (commits `b72aef7`, `ba21332`) and unrelated to the upload failures.

---

## Architecture

The browser uploads bytes **straight to GCS** (no size limit there), then calls a small backend endpoint to record the DB row. Nothing large flows through Cloud Run.

```
            ┌─────────────────────────────────────────────┐
 browser    │  uploadVideo(file, fields, onProgress)       │   frontend/src/lib/resumableUpload.ts
            │   1. compress (>=24 MiB, best-effort)         │
            │   2. route by resulting size:                 │
            │        >=48 MiB  parallel composite           │──┐ direct PUT(s)
            │        >=32 MiB  resumable chunked             │──┤  to storage.googleapis.com
            │        else      single-PUT signed URL         │──┘  (no Cloud Run involved)
            └───────────────────────┬─────────────────────┘
                                    │ small JSON only
                                    ▼
            ┌─────────────────────────────────────────────┐
 backend    │  /upload/signed-url | /upload/resumable-url   │   mints signed URLs / sessions
 (Cloud Run)│  /upload/composite/sign | /complete           │   composes parts (server-side)
            │  /upload/finalize                             │   creates the Attempt row
            └─────────────────────────────────────────────┘
```

### Upload methods & when each is used

Selection happens in `uploadVideo()` on the **post-compression** size:

| Method | Trigger | How it works | Resilience |
|---|---|---|---|
| **Single PUT** (signed URL) | `< 32 MiB` | One signed `PUT` straight to GCS | Whole-file retry only |
| **Resumable chunked** | `>= 32 MiB` | 8 MiB chunks to a GCS resumable session; resumes from the confirmed offset (308 `Range`) after a dropped chunk; capped exponential backoff | Resumes mid-upload |
| **Parallel composite** | `>= 48 MiB` | Split into 16 MiB parts, PUT 4-in-parallel via per-part signed URLs, backend `compose`s them in order; **falls back to resumable on any failure** | Per-part, + resumable fallback |

All three upload directly to GCS. After the bytes land, the browser calls `/upload/finalize` to create the `Attempt`.

### Client-side compression

`frontend/src/lib/videoCompress.ts` — runs before upload for files `>= 24 MiB`.

- **Primary:** WebCodecs — `mp4box` demux → `VideoDecoder` → draw/scale onto an `OffscreenCanvas` at 720p → `VideoEncoder` (H.264, probes `isConfigSupported`) → `mp4-muxer`.
- **Fallback:** MediaRecorder (`<video>` → canvas → `captureStream` → `MediaRecorder`, prefers `video/mp4` then `video/webm`).
- **Final fallback:** the original file.
- **Contract:** `compressVideo()` **never throws** and returns the **original** file unless the result is at least 10% smaller (`MIN_SHRINK_RATIO`). `canCompressVideo()` gates on `VideoEncoder && VideoDecoder && OffscreenCanvas`.
- **v1 caveat:** **audio is dropped.** Fine for form/plank scoring; flagged as a follow-up.

Verified: a 43 MB H.264 1080p clip compressed to **9.0 MB** (`video/mp4`) in-browser. (Chromium can't decode HEVC, so HEVC inputs fall back to the original in a desktop test browser, but compress fine on a real phone with hardware HEVC decode.)

---

## Backend endpoints

All in `backend/toms_gym/routes/upload_routes.py`. The legacy multipart `POST /upload` is kept for back-compat (e.g. the email-upload integration) but the frontend no longer uses it for browser uploads.

| Endpoint | Purpose |
|---|---|
| `POST /upload/signed-url` | Mint a V4 signed `PUT` URL (via IAM signBlob). Returns `{upload_url, object_name, public_url, content_type}`. |
| `POST /upload/resumable-url` | Start a GCS resumable session (server-side, CORS-scoped to the caller `Origin`). Returns `{session_uri, object_name, public_url, content_type}`. |
| `POST /upload/composite/sign` | `{filename, content_type, parts}` → N signed part-`PUT` URLs. Returns `{final_object, public_url, content_type, parts:[{part_number, object_name, upload_url}]}`. |
| `POST /upload/composite/complete` | `{final_object, content_type, part_object_names[]}` → GCS-`compose`s parts in order (32-source batching via `<final>.tmpN` intermediates), sets content-type, deletes parts/temps. Returns `{public_url}`. |
| `POST /upload/finalize` | `{object_name, public_url, competition_id, user_id\|email, lift_type, weight}` → verifies the blob exists, then creates the `Attempt` via shared `_resolve_user_id` / `_create_attempt_record`. Returns the same shape as legacy `/upload`. |
| `POST /log-error` | Frontend telemetry sink (`telemetry_routes.py`). Logs `FRONTEND_ERROR` (a WARNING) to Cloud Run. |

Shared helpers in `upload_routes.py`: `_generate_signed_upload_url`, `_resolve_user_id`, `_create_attempt_record`, `LIFT_TYPE_MAPPING`.

---

## Frontend modules

| File | Responsibility |
|---|---|
| `lib/resumableUpload.ts` | **Entrypoint** `uploadVideo()` (compress + size-routing) and the resumable chunked uploader. |
| `lib/upload.ts` | `uploadVideoViaSignedUrl()` (single PUT) + shared `UploadFields` / `FinalizeResponse` types. |
| `lib/parallelUpload.ts` | `uploadVideoParallel()` — parallel composite, 4-wide pool. |
| `lib/videoCompress.ts` | `compressVideo()` + `canCompressVideo()`. |
| `lib/useUploadGuard.ts` | `beforeunload` warning + screen Wake Lock while an upload is in flight. |
| `lib/telemetry.ts` | `reportError()` + `reportUploadError()` (file size/type, stage, HTTP status → `/log-error`). |

Both upload pages (`pages/ChallengeDetail.tsx`, `pages/UploadVideo.tsx`) call `uploadVideo()`, show a progress bar with a "keep this page open" hint, and report failures via `reportUploadError`. The footer (`components/Layout.tsx`) shows `APP_VERSION` (from `VITE_BUILD_TIMESTAMP`, set by `deploy.py`).

---

## Infrastructure

Codified in `deploy.py` `setup_iam` (runs unless `--skip-iam`):

- **IAM:** the runtime SA `toms-gym-service@toms-gym.iam.gserviceaccount.com` is granted `roles/iam.serviceAccountTokenCreator` **on itself** — required because Cloud Run has no private key, so V4 signing goes through the IAM `signBlob` API. Without it, `/upload/signed-url` returns 500.
- **Bucket CORS** on `gs://jtr-lift-u-4ever-cool-bucket`: methods `GET, PUT, POST`; response headers `Content-Type, x-goog-resumable, Content-Range, Range` (the last two are needed for resumable chunking — the browser sends `Content-Range` and reads the confirmed `Range` from GCS 308 responses).

Apply with `python3 deploy.py --backend-only` **without** `--skip-iam`. Objects are already public-read (`allUsers` → `objectViewer`), so read URLs work without signing; only uploads (PUT) are signed.

---

## Deployment

Per the repo's standard flow:

```bash
python3 deploy.py --backend-only            # applies IAM + CORS, deploys backend (drop --skip-iam to (re)apply infra)
python3 deploy.py --frontend-only --skip-iam # deploys frontend
```

Production URLs: frontend `https://my-frontend-quyiiugyoq-ue.a.run.app`, backend `https://my-python-backend-quyiiugyoq-ue.a.run.app`.

---

## Verification done

- **32 MiB cap:** 40 MB `POST /upload` → 413 (GFE HTML, never reached Flask); 10 MB reached Flask.
- **Signed URL:** signed `PUT` URL minted with `X-Goog-Credential=toms-gym-service` + valid RSA signature.
- **Single-PUT bypass:** 40 MB PUT straight to GCS → 200, blob landed.
- **Resumable:** 40 MB in 8 MiB chunks with a **simulated interruption + resume**; and a real **372 MB Pixel HEVC video through the browser** (~80 chunks → finalize).
- **Compression:** 43 MB H.264 1080p → **9.0 MB** MP4 in-browser via WebCodecs.
- **Parallel composite:** 3 parts uploaded in parallel, composed in correct byte order (A·B·C), finalized.
- **CORS preflight:** browser `OPTIONS` for chunked PUT returns `Allow-Methods: PUT`, `Allow-Headers: content-range`.
- **Telemetry:** synthetic `FRONTEND_ERROR` round-tripped into Cloud Run logs.

To find upload failures now: query Cloud Run logs for `textPayload:"FRONTEND_ERROR"` (a 413-class failure shows `phase=http-error, httpStatus=413` with a large `fileSizeMB`).

---

## Caveats & follow-ups

- **Compression drops audio** (v1).
- **Parallel parts have no per-part retry** — mitigated by the parallel→resumable fallback. Adding per-part retry would let parallel stand alone on flaky networks.
- **HEVC** can't be re-encoded in browsers that lack HEVC decode (most desktop Chromium); those inputs upload uncompressed. Real phones with hardware HEVC decode compress fine.
- **`deploy.py` hardcodes backend `--memory=2Gi --cpu=1`** and reverts manual `gcloud run services update` bumps; change the deploy command (~lines 699-700) to persist a different size. (The earlier memory bump is now moot — uploads no longer buffer through backend memory.)
- Further speed levers not yet built: client-side **trim**, adaptive chunk sizing via the **Network Information API**, and a cellular "use WiFi" warning.

---

## Commit history (branch `feat/signed-url-upload`, merged to `main`)

| Commit | What |
|---|---|
| `e958bbd` | telemetry: report upload failures to `/log-error` |
| `62c851c` | direct-to-GCS upload via signed URL |
| `88dff1a` | progress bar, interrupt guards, footer build version |
| `5658b1b` | resumable chunked uploads |
| `3b7d06e` | parallel composite uploads |
| `07085c2` | client-side WebCodecs compression |
| `7d1bca5` | wire compression + parallel into `uploadVideo()` |
