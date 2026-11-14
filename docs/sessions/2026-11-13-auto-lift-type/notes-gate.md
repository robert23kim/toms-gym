# Gate notes 2026-11-13 auto-lift-type (all 9 targets writable)

1 gcloud: project toms-gym; print-access-token rc=0. writable.
2 cloudrun (us-east1): my-python-backend-00196-mtt, my-frontend-00205-95c, bowling-service-00053-fxm; bowling image gcr.io/toms-gym/bowling-service:situp-13b49b5; traffic 100% on latest revision (all three). writable.
3 gcs: gsutil cp then rm of gs://jtr-lift-u-4ever-cool-bucket/gate/2026-11-13-auto-x both completed. writable.
4 cloudsql: proxy started (allowed this time); SELECT 1 returned [1] (read-only session). writable.
  Recipe: `nohup /Users/toka/Downloads/google-cloud-sdk/bin/cloud_sql_proxy -instances=toms-gym:us-east1:my-db=tcp:5433 > <notes>/proxy.log 2>&1 &` (pid 13926, LEFT RUNNING);
  `backend/venv/bin/python -I <script>` with pg8000.native.Connection(user="postgres", database="postgres", host="127.0.0.1", port=5433), password from
  `subprocess.run(["gcloud","secrets","versions","access","latest","--secret=db-password","--project=toms-gym"])` inside python, never printed; first statement `SET default_transaction_read_only = on`.
  Script: scratchpad ro.py (read-only SELECTs only).
  Attempt has NO competition_id: join "Attempt".user_competition_id -> "UserCompetition".competition_id.
  lift_type storage: "Attempt".lift_type is character varying (plain text), NOT the pg enum. An enum type `lift_type` exists with labels
  snatch, clean_and_jerk, Squat, Bench Press, Deadlift, Bicep Curl, Bowling, Plank, Pushup, Situp but the column does not use it (migrations ALTER TYPE it anyway).
  Constraints on Attempt: only PK and FK user_competition_id (ON DELETE CASCADE); no check constraint on lift_type.
  Distinct lift_type (all attempts): Plank 26, Pushup 17, Squat 11, Situp 11, snatch 4, Bicep Curl 4, Bowling 3, Deadlift 1.
  With video_url, overall: identical counts (every attempt has a video_url).
  Club 32ca7bad: attempts with video_url: Pushup 11, Plank 8, Situp 8, Squat 1 (= all 28 club attempts).
5 playwright: 1.58.2; gate-pw.mjs (copied here) at 390x844: innerWidth 390; you-row absent for an anonymous viewer. writable.
6 android: java 21.0.10 at /opt/homebrew/opt/openjdk@21/bin/java; commandlinetools dir present (build-tools, emulator, platform-tools, platforms, system-images);
  package.json l.68 android:build, l.71 android:publish; AVD t30g exists (emulator -list-avds). Not built.
7 git: HEAD 74a25191b1c8242808429fd95f5127134623b7d5 on feat/100-club. Modified tracked: only .claude/settings.json and frontend/.env.production.
  Full porcelain set (79 lines) in git-status.txt in this folder: every path there at start is NOT mine; never stage. writable.
8 engine: feat/situp-config = 93378b009593fa0aef83be361027dae4b0947c09 resolves; /Users/toka/code/bowling-app/auto-engine does not exist. writable.
9 clips: public GET /competitions/<cid>/leaderboard -> rows[].user_id; GET /users/<uid>/lifts?limit=100 -> {lifts[{attempt_id, competition_id, lift_type, total_reps, ...}]};
  GET /competitions/<cid>/participants/<uid>/attempts/<attempt_id> -> {video_url: https://storage.googleapis.com/jtr-lift-u-4ever-cool-bucket/videos/<file>.MOV, lift_type,...}.
  Download read-only with gsutil cp gs://jtr-lift-u-4ever-cool-bucket/videos/<file>. Annotated output at gs://.../lifting/<attempt_id>/annotated.mp4.
  /lifts returns lowercase lift_type (plank/situp/pushup/squat) while the DB stores Plank/Situp/Pushup/Squat.
  Club clips per lift type (API): plank 8, situp 8, pushup 11, squat 1. Real athletes: read only.

Canary: bundle-before/ = index.html + 84 chunks (85 fetched, recursive from entry). lift-type-automatic = 0 (expected); you-row-unknown = 1 (>=1, fetch valid). marker_hits_before = 0.

Baselines: backend gate 402 passed, 0 failed (8 deselected; backend-baseline.log); tsc rc=0; jest 811 tests, 0 failed (jest-baseline.json).
Live (live-before.json, competition-before.json, live-scores.txt): 1:375:147:14,2:350:162.5:14
