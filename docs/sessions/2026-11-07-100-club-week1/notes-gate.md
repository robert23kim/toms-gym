# Gate notes 2026-11-07 (secrets redacted)

1 gcloud: project toms-gym, print-access-token rc 0. writable.
2 cloudrun: backend my-python-backend-00194-8wr, frontend my-frontend-00197-h8f. writable.
3 gcs: gsutil cp then rm of gs://jtr-lift-u-4ever-cool-bucket/gate/2026-11-07-x both completed. writable.
4 admin_token: secret access piped to wc -c = 48. writable.
5 cloudsql: NOT writable. Starting `cloud_sql_proxy -instances=toms-gym:us-east1:my-db=tcp:5433` in the background plus a pg8000 SELECT 1 script (db-password read in a python subprocess) was denied by the auto mode classifier: "judged this action dangerous (it gave no explanation)". Not retried. Intended recipe (from docs/reference/100-club.md): cloud_sql_proxy at /Users/toka/Downloads/google-cloud-sdk/bin, `-instances=toms-gym:us-east1:my-db=tcp:5433`, pg8000 to 127.0.0.1:5433 with the db-password secret; db/user names unverified. No proxy is running.
6 chrome: tab opened, /challenges page text contains "The 100 Club" (Consistency, Open). Tab closed. writable.
7 playwright: version 1.58.2; gate-pw.mjs printed "Challenges | Tom's Gym 390". writable.
8 android: java 21, cmdline-tools, credentials.json present; package.json has android:build (l.68) and android:publish (l.71); bash -n on both scripts ok. writable (not built).
9 git: head 993990f36d48cdb199ee2516c8454d95229ac73d; modified tracked files only .claude/settings.json, frontend/.env.production. writable.

Baseline: backend 367 passed, 0 failed (8 deselected); frontend tsc ok; jest 696 tests, 0 failed (jest-baseline.json).

Snapshots (live-before.json, monday-before.json):
- live: caleb.li.larson:150:1, Toka:150:2 (tied score, ranks 1 and 2), week_index 1, days_left 2, leaders Plank/Pushup caleb, Situp Toka.
- monday as_of 2026-11-09T12:00-05:00: caleb.li.larson:200:1, Toka:175:2, week_index 2, type_leaders empty.
