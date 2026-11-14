# Deploy round 1 (2026-11-14 ~05:45Z)

## Pre-flight
- 21 commits after 74a2519 (09a4a5a .. 9ebbd3d).
- git status --porcelain: 79 lines, byte-identical (sorted) to git-status.txt baseline; still 79 after APK build.
- Backend gate: 483 passed, 7 skipped, 8 deselected (deploy-backend-gate.log). tsc --noEmit: clean (deploy-tsc.log, 0 bytes).

## Engine
Not built/deployed. bowling-service-00053-fxm at 100%. engine_deployed=false.

## Backend
- No auto-capable engine deployed -> AUTO_LIFT_TYPE stays "0" in deploy.py (line 694 already "0"); no commit.
- Revision my-python-backend-00197-vvw (100% traffic), env AUTO_LIFT_TYPE=0. /health 200.
- Startup log: "Attempt lift_type_source 020 migration complete" (x2 workers), no ERROR severity lines; only the pre-existing Redis fallback WARNING.
- competition-after.json: auto_lift_type_enabled=false; everything else equal to competition-before.json.
- live-after.json vs live-before.json: 2 rows, rank/score/this_week.lifts/attempt_count identical
  (b7bb417c 1/375/147/14, 7844e26d 2/350/162.5/14). No uploads in between.

## Frontend
- Revision my-frontend-00206-dxd (100%).
- bundle-after/: index.html + 84 chunks = 85 files (same count as bundle-before). Crawler regex initially missed mp4box.all-Cb4wIdk6.js (dotted name); fetched separately, 200.
- lift-type-automatic = 2 (was 0). Fetch canary you-row-unknown = 1.
- The marker shows the code is shipped, not that Auto is offered: with auto_lift_type_enabled=false it should stay hidden. Not checked in a browser this round.

## APK
- VITE_BUILD_TIMESTAMP=1794635557 (apk-build-stamp.txt). npm run android:build exit 0, 4.6M.
- Unzipped: stamp found in 2 files under assets/public; lift-type-automatic in ChallengeDetail-C8lMhlgC.js and UploadVideo-CBAK2I7s.js;
  capacitor.plugins.json lists @capacitor/preferences (com.capacitorjs.plugins.preferences.PreferencesPlugin); class path present in 2 of 4 dex files.
- Published gs://jtr-lift-u-4ever-cool-bucket/apk/tomsgym-debug-20261114-005300.apk (4819425 bytes, same as local).
- Short link https://my-python-backend-quyiiugyoq-ue.a.run.app/s/qu1t84 -> 302 to the signed object; body starts PK.. (curl only, not installed on a phone).
