# Deploy round 2 (2026-11-14 ~07:00Z)

## Pre-flight
- 26 commits after 74a2519 (09a4a5a .. dc4a066).
- git status --porcelain: 79 lines, identical (sorted) to git-status.txt baseline.
- Backend gate: 483 passed, 7 skipped, 8 deselected (deploy-2-backend-gate.log). tsc --noEmit clean (deploy-2-tsc.log, 0 bytes).

## Engine
Not built/deployed. bowling-service-00053-fxm at 100%. engine_deployed=false.

## Backend
- No auto-capable engine -> AUTO_LIFT_TYPE stays "0" (deploy.py:694 already "0"); no commit.
- Pre-deploy live revision was my-python-backend-00197-vvw (round 1). New: my-python-backend-00198-8kd, 100% traffic, env AUTO_LIFT_TYPE=0. /health 200.
- Startup log for 00198-8kd: "Attempt lift_type_source 020 migration complete" x2; severity>=ERROR filter in the same query returned nothing.
- competition-after-2.json: only change vs competition-before.json is the added auto_lift_type_enabled=false.
- live-after-2.json vs live-before.json: rank/score/this_week.lifts/attempt_count identical
  (b7bb417c 1/375/147/14, 7844e26d 2/350/162.5/14). attempt_count unchanged, no uploads.

## Frontend
- Revision my-frontend-00207-h4l (100%).
- bundle-after-2/: 80 files (round 1 had 85; this crawler's regex missed some chunks). lift-type-automatic = 2, canary you-row-unknown = 1.
- Shipping the marker does not mean Auto is offered: auto_lift_type_enabled=false keeps it hidden. Not checked in a browser.

## APK
- VITE_BUILD_TIMESTAMP=1794639762 (apk-build-stamp-2.txt); android:build exit 0 (apk-build-2.log).
- Unzipped: stamp in 2 files under assets/public; lift-type-automatic in ChallengeDetail-BNJQ7Ren.js and UploadVideo-CXuVIMFk.js;
  capacitor.plugins.json lists @capacitor/preferences (com.capacitorjs.plugins.preferences.PreferencesPlugin); class in classes2.dex (AppPlugin canary in the same file).
- Published gs://jtr-lift-u-4ever-cool-bucket/apk/tomsgym-debug-20261114-020259.apk (4819418 bytes, same as local).
- Short link https://my-python-backend-quyiiugyoq-ue.a.run.app/s/zFFWCs -> 302 to the signed object, body starts PK (curl only, not installed on a phone).
