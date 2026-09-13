# Android app: Capacitor wrapper on Tom's phone — 2026-09-13

## What this was
Tom asked for a native Android version of Tom's Gym (frontend only, same production backend) that he could install on his phone to test. A `/loop` drove it from the July scaffold to a verified install.

## What changed
- `f06586f` feat(android): committed `frontend/android/` (Capacitor 7, AGP 8.7.2, targetSdk 35) and added `@capacitor/{core,cli,android,app,splash-screen,status-bar}` to `package.json`. The scaffold had been git-ignored since July with no Capacitor packages installed, so nothing could rebuild it.
- `0e775d5` feat(android): `frontend/scripts/publish-apk.sh` + `npm run android:publish`.
- npm scripts `android:build`, `android:install`, `android:release` wrap the existing `scripts/build-android.sh`.
- `capacitor.config.ts`: `android.adjustMarginsForEdgeToEdge: 'auto'`, dark `StatusBar` plugin config.
- `android/app/src/main/res/values/styles.xml`: `#09090b` window/status/navigation bar colours.
- `AndroidManifest.xml`: `CAMERA`, `RECORD_AUDIO`, `MODIFY_AUDIO_SETTINGS`, optional camera feature.
- Root `.gitignore`: `frontend/android/` un-ignored, `frontend/*.apk` ignored.
- CLAUDE.md gained an "Android App (Capacitor, shipped 2026-09-13)" section (uncommitted at the time of writing; committed with this doc).
- Installed on Tom's phone and confirmed working by Tom via short link `https://my-python-backend-quyiiugyoq-ue.a.run.app/s/25QvvB` (7-day signed URL, build stamp 1789329040, object `apk/tomsgym-debug-20260913-155234.apk`).

## What we learned
- **Gmail's in-app browser will not complete an APK download.** Cloud Run logs showed six 302s from `android-app://com.google.android.gm/` and no install. Signing the URL with `response-content-disposition=attachment;filename=tomsgym.apk` (no spaces or quotes; a quoted filename made GCS return 403) plus opening in real Chrome fixed it.
- **GCS edge-caches a re-uploaded object for an hour** (`cache-control: public, max-age=3600`), so the first short link served the previous build with a matching HEAD but a 227 KB larger body. Publish each build under a new object name with `--cache-control=no-store` and verify by md5 of a full download.
- `gcloud storage sign-url` with the system-managed key caps at 12 h; `backend/credentials.json` (`toms-account@toms-gym`) signs 7 days. Public ACLs on the bucket are blocked by policy.
- **targetSdk 35 forces edge-to-edge**: the status bar overlapped the navbar. `adjustMarginsForEdgeToEdge` fixed the overlap but exposed the default white window background as bands above and below the WebView until `styles.xml` painted them.
- The headless API 35 arm64 emulator (`t30g` AVD) boots in ~25 s and was enough to catch both visual bugs before anything reached the phone. `adb shell input tap` coordinates move when the header margin changes.
- WebView `capture="environment"` inputs silently fall back to a file picker without `CAMERA` in the manifest.
- The Claude Code app's file card also delivers the APK to the phone; the SendUserFile tool is not available in headless sessions.

## Still broken / next steps
- App icon and splash are Capacitor defaults; a Tom's Gym icon set (`res/mipmap-*`) is the obvious next step.
- No deep-link intent filter, so `/s/<code>` share links open the browser, not the app.
- No release keystore, so every install is a debug build and Play Protect prompts on first launch.
- The bundled web assets go stale with each frontend deploy; either rebuild the APK on `deploy.py --frontend-only` or point the WebView at the hosted frontend (`server.url`) so the app self-updates.
- Camera capture from inside the app is untested on the real phone (verified only that the permission is in the manifest).
- No `platform=capacitor` log line has been checked yet; query `textPayload:"platform=capacitor"` in Cloud Run to confirm the on-phone boot telemetry fires.
- `main` is 24 commits ahead of `origin/main` and nothing here is pushed.

## Verification
- `bash scripts/build-android.sh` exit 0 four times; `aapt2 dump badging` showed the four permissions and package `com.tomsgym.app` versionCode 1; the build stamp string was found in exactly one bundled JS chunk each time.
- Emulator: install `Success`, app process alive after menu open, Lift navigation and hardware back; zero `CONSOLE`/`Uncaught` lines in logcat; screenshots reviewed for the header overlap and white bands before and after the fix.
- Publish: downloaded through the short link and md5-compared to the local APK (match) for the versioned object; the reused-name object was shown to mismatch (4969559 vs 4742008 bytes).
- Real phone: Tom reported "it worked!" after the attachment link. No further on-device checks were run.
- Frontend jest/tsc were not run (no TypeScript source changed); backend untouched.
