# Fix round 2 (2026-11-07)

Input: prove found nothing; refute marked B-guard (B1b, server-side Pushup/Situp/Plank weight -> 0) "refuted":
not proven in production because cloudsql=false, so there was no canary and no SQL read.

## Diagnosis: a proof gap, not a code defect
- The guard is on every Attempt write path: `upload_routes._create_attempt_record` (finalize, :131),
  multipart `/upload` (:389), `attempt_routes.create_attempt` and `update_attempt` (both call
  `bodyweight_weight_kg`). The email integration posts through `/upload`, and bowling inserts its own lift type.
  Commits 5bb001f and 2174e0a, deployed as my-python-backend-00195-jbg (notes-deploy.md).
- Local gap: every existing finalize test posted `user_id`. The Sep-13 APK (6244abe `ChallengeDetail.tsx:215`
  -> `lib/upload.ts:82`) posts `{object_name, public_url, competition_id, lift_type, weight: "60", email}`,
  with **email and no user_id**, so it goes through `_resolve_user_id`. That body had no test.
- Prod-proof gap: the finalize path (the one the stale APK uses) logged only
  `Created attempt X (lift_type=...)`, so a real upload could not show the stored weight without SQL.

## Change (commit 0916ee9, backend only)
- `backend/toms_gym/routes/upload_routes.py`: the finalize log line now reads
  `Created attempt <id> (lift_type=<t>, weight_kg=<w>)`.
- `backend/tests/test_bodyweight_weight.py::test_stale_apk_finalize_by_email_stores_zero_and_logs_it`
  replays the exact stale-APK body (Situp, "60", email, no user_id, live competition id). It asserts
  the Attempt bind is lift_type Situp, weight_kg 0, and that the log carries `lift_type=Situp, weight_kg=0)`.
- Mutation checks ran from an in-memory copy, with the file re-read and its sha256 confirmed after restore:
  `BODYWEIGHT_LIFT_TYPES = set()` -> the test fails (rc 1); dropping `, weight_kg={weight_kg}` from the log -> fails (rc 1).

## Gates
- Backend `PYTEST_ADDOPTS="-p no:cov" PYTHON=venv/bin/python tools/run_ci_tests.sh`: rc 0, 402 passed,
  8 deselected (was 401, +1).
- Frontend `npx tsc --noEmit`: rc 0. jest --maxWorkers=4 -> jest-fix2.json: success true, 737/737 tests,
  105 suites, 0 failed. Frontend is unchanged this round.

## Outcome: B-guard deferred
- Still NOT proven in production. This round does not change that. It makes a future proof possible read-only.
  After this commit is deployed, the next real Pushup/Situp/Plank finalize writes a log line that shows the stored
  weight. Read it with:
  `gcloud logging read 'resource.type="cloud_run_revision" AND resource.labels.service_name="my-python-backend" AND textPayload:"Created attempt" AND textPayload:"weight_kg="' --project=toms-gym --limit=10`.
  Expect `weight_kg=0` on every bodyweight row. The stored row can also be checked with SQL once the Cloud SQL proxy is allowed.
- This commit is NOT deployed. It needs `python3 deploy.py --backend-only --skip-iam` (deploy phase). I did not
  deploy, write to prod or retry the Cloud SQL proxy.
- Commit trailer: I used `Co-Authored-By: Claude Opus 5.5`, following the harness attribution reminder, not the
  computed task's `Claude Fable 5.1` line.
