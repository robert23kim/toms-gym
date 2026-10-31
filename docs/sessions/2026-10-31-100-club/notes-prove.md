# 100 Club round 1: prove notes (2026-10-31)

Challenge 32ca7bad-a970-4a09-acec-02b768793063; backend my-python-backend-00193-dd9, frontend my-frontend-00196-tt8.
Scripts in the session scratchpad `prove/` (db.py = pg8000 via cloud_sql_proxy on :5433, per notes-gate.md).

## Pre-state
- `GET /competitions/<id>/leaderboard` before anything: 200, rows [], momentum joined 0, status upcoming, week_index 0, days_left 0.

## A. Canary user
- `POST /auth/register {email: hundredclub-canary-2026-10-31@example.com, name: "Canary 100"}` (no password) ->
  **HTTP 500 `{"error":"Database error"}`**. Cloud Run log 2026-10-31T15:12:09Z:
  `invalid input value for enum auth_method: "passwordless"`. DB: `enum_range(NULL::auth_method)` = `{google,password}`.
  Pre-existing defect (auth_routes.py register writes 'passwordless' when no password is given); not 100 Club code.
  No User row was written (SELECT by email -> []).
- Workaround: same body plus a random `secrets.token_urlsafe(24)` password (never printed, discarded) -> 201,
  **user_id 6d365544-066a-45eb-a345-79d42bc17648**. DB: name "Canary 100", is_test false, auth_method password.

## B. Real upload
- `curl -F video=@backend/tests/fixtures/test_video_plank_10s.mp4 -F user_id=... -F competition_id=32ca7bad... -F lift_type=Plank -F weight=0 /upload`
  -> 200, **attempt_id 9a849d80-2798-4f54-8069-714795d3a830**, user_competition_id 8656a607-bc09-432e-b6e6-b5f4a8a620a3,
  url https://storage.googleapis.com/jtr-lift-u-4ever-cool-bucket/videos/20261031_151256_test_video_plank_10s.mp4
- `/upload` does not dispatch analysis (the frontend calls `POST /lifting/analyze/<attempt_id>`, api.ts:394). Called it ->
  201 `{"lifting_result_id":"a5c49d8c-b942-4e53-ab97-8afc5253c035","status":"queued"}` at 2026-10-31T11:13:02-04:00.
- Poll (`poll.py`, `GET /users/<uid>/lifts` every 45 s, field `hold_s` since that endpoint renames total_in_plank_s):
  11:13:17 analysis_status processing; **11:14:03 completed, hold_s 6.0**, steadiness 3.66, lift_type "plank".
- `GET /competitions/<id>/leaderboard` (public) -> canary row: rank 1, score 0, attempt_count 0, history [], weeks [],
  **warmup_lifts 0** (= floor(6.0/10) = 0), streak 0, this_week {index 0, quota 100, lifts 0, pending 0};
  consistency.status upcoming, week_index 0, days_left 0, type_leaders {}; momentum joined 1, uploaded_today 1.
  All asserted values match. Caveat: with a 6 s hold, expected warm-up is 0, so the warm-up count could not have
  failed from this upload alone; a 35 s warm-up row is seeded in C (expected warmup_lifts 3) to make it discriminate.
- Observation (not a defect): before the start `this_week.index` is 0 (= week_index); the design says both
  "this_week.index is week_index" and "before the start this_week describes week 1" - quota 100 matches week 1.

## C. Seeded weeks (cloudsql writable)
`seed.py` (one transaction, own UUIDs saved to seed_ids.json first, weight_kg 0, status completed, created_at = updated_at = ts,
video_url = the real upload's URL, LiftingResult processing_status completed). Rows, all on UserCompetition 8656a607-...:
| attempt_id | LiftingResult id | created_at (UTC) | lift | report |
|---|---|---|---|---|
| f191b232-702d-4483-b999-63e58e759225 | 80e78d75-86dd-47cf-8162-60c8dbac713e | 2026-11-03T12:00Z (Tue wk1) | Plank | total_in_plank_s 950, form 80 |
| bdc40249-74a6-4429-a0ab-0a5d3b8b106f | a0b8c6ec-3e57-4420-9f69-6787053683ad | 2026-11-04T12:00Z (Wed wk1) | Situp | total_reps 20, form 75, rep_metrics 10x80 + 10x60 |
| 16541880-ccbb-4e74-8ac1-90acbb252cbc | 2ba8e24a-e01a-4a64-874d-f4d936cedae5 | 2026-11-10T12:00Z (Tue wk2) | Plank | total_in_plank_s 950, form 80 |
| 99d4314e-ca5f-4557-9b46-c0145b186887 | da4e2916-18f0-4f89-8e6d-ed3e432dcb1f | 2026-10-31T16:00Z (warm-up) | Plank | total_in_plank_s 35 (added by the prover so warmup_lifts discriminates: expect 0+3) |
Read back by SELECT join: 5 attempts on the UC (the real one + 4 seeded), all completed with their reports.

`asof.py` (admin token read inside the Python process via `gcloud secrets versions access`, stripped, never printed; urllib):
- `?as_of=2026-11-12T12:00:00-05:00` without header -> **401 `{"error": "Admin token required"}`**.
- with `X-Admin-Token` -> **200**. 31 assertions, **31 PASS, 0 FAIL**:
  weeks[0] = {index 1, quota 100, lifts 110, met true, bonuses [Plank, Situp], points 200, by_type {Plank 95, Situp 15,
  Pushup 0, Squat 0}, plank_seconds 950}; weeks[1] = {points 95, bonuses []}; len(weeks) 2;
  this_week = {index 2, quota 125, lifts 95, met false, leading includes Plank, pending 0};
  score 295; streak 1; best_streak 1; weeks_met 1; warmup_lifts 3; attempt_count 3; history scores [95, 15, 95]; rank 1;
  consistency.status live, week_index 2, week_start 2026-11-09, week_end 2026-11-15, type_leaders.Plank = [canary];
  **days_left observed 4** (design: Thu 12 Nov -> Thu, Fri, Sat, Sun = 4).
- Public board (no as_of, now = 2026-10-31) after seeding -> 200: canary score 0, attempt_count 0, history [], weeks [],
  warmup_lifts 3, status upcoming. So future-dated rows do not leak into today's board, and the warm-up sum is live
  (35 s -> 3; 6 s -> 0).
- Not covered: only one participant on the board, so ties, a second athlete stealing a bonus, ranking tiebreaks and
  the reset-after-miss ramp were not exercised in prod (they are covered by unit tests per notes-backend/qa, not re-run here).
  Pushup and Squat lifts were not seeded. The situp half-credit was proven via seeded rep_metrics, not a real engine report.

as_of JSON (consistency block + canary row):
```json
{
    "consistency": {
        "days_left": 4,
        "rules": {
            "base_quota": 100,
            "plank_seconds_per_lift": 10,
            "quota_bonus": 50,
            "ramp": 25,
            "type_bonus": 25,
            "tz": "America/New_York",
            "week_start": "2026-11-02",
            "weeks": 8
        },
        "status": "live",
        "type_leaders": {
            "Plank": [
                {
                    "amount": 950,
                    "name": "Canary 100",
                    "user_id": "6d365544-066a-45eb-a345-79d42bc17648"
                }
            ]
        },
        "week_end": "2026-11-15",
        "week_index": 2,
        "week_start": "2026-11-09",
        "weeks_total": 8
    },
    "row": {
        "attempt_count": 3,
        "attempt_id": "16541880-ccbb-4e74-8ac1-90acbb252cbc",
        "best_by_lift": {},
        "best_streak": 1,
        "clip_url": "https://storage.googleapis.com/jtr-lift-u-4ever-cool-bucket/videos/20261031_151256_test_video_plank_10s.mp4",
        "date": "2026-11-10",
        "form_score": null,
        "gender": "male",
        "history": [
            {
                "date": "2026-11-03",
                "score": 95
            },
            {
                "date": "2026-11-04",
                "score": 15
            },
            {
                "date": "2026-11-10",
                "score": 95
            }
        ],
        "name": "Canary 100",
        "rank": 1,
        "score": 295,
        "steadiness": null,
        "streak": 1,
        "this_week": {
            "by_type": {
                "Plank": 95,
                "Pushup": 0,
                "Situp": 0,
                "Squat": 0
            },
            "index": 2,
            "leading": [
                "Plank"
            ],
            "lifts": 95,
            "met": false,
            "pending": 0,
            "plank_seconds": 950,
            "quota": 125
        },
        "thumbnail_url": null,
        "user_id": "6d365544-066a-45eb-a345-79d42bc17648",
        "warmup_lifts": 3,
        "weeks": [
            {
                "bonuses": [
                    "Situp",
                    "Plank"
                ],
                "by_type": {
                    "Plank": 95,
                    "Pushup": 0,
                    "Situp": 15,
                    "Squat": 0
                },
                "index": 1,
                "lifts": 110,
                "met": true,
                "pending": 0,
                "plank_seconds": 950,
                "points": 200,
                "quota": 100,
                "start": "2026-11-02"
            },
            {
                "bonuses": [],
                "by_type": {
                    "Plank": 95,
                    "Pushup": 0,
                    "Situp": 0,
                    "Squat": 0
                },
                "index": 2,
                "lifts": 95,
                "met": false,
                "pending": 0,
                "plank_seconds": 950,
                "points": 95,
                "quota": 125,
                "start": "2026-11-09"
            }
        ],
        "weeks_met": 1,
        "weight_class": "85kg"
    }
}
```

## D. Browser: SKIPPED
Gate notes-gate.md section 6: chrome NOT confirmed (writable=false); the task scopes D to "only if chrome is writable".
No Chrome or Playwright call was made. **Not covered:** the /challenges listing, the consistency-hero render (pre-start
state, rules line, Canary warm-up row), the 390x844 layout and the home to-do "The 100 Club" pill. The deployer's bundle
canary (consistency-hero string present in the live ChallengeDetail chunk) is the only frontend evidence, and it is not
a render.

## Side effects observed before cleanup
- Analysis completion wrote AnalysisNotification 7a817939-2a73-49b5-9e0f-3523862ac14f (email = canary @example.com,
  short_code null) and ShortLink gpeQMD (id 39c664e1-a546-4241-aac7-b9fd57ffc755, created_by_user_id NULL, target
  .../challenges/32ca7bad.../participants/<canary>/video/9a849d80...). A completion email to the example.com address
  may have been attempted (not checked).
- GCS inventory: videos/20261031_151256_test_video_plank_10s.mp4 (6,826,224 B); lifting/9a849d80-.../annotated.mp4,
  summary.json. No objects under lifting/<seeded ids>/ (seeded rows have no media). No og-cards/gpeQMD*. A bucket-wide
  `gsutil ls "**9a849d80...**"` returned exactly the two lifting objects (search canary); `**<user_id>**` returned none.
- WeeklyMaxLift, SecurityAudit, UserSession, BowlingResult rows for the canary: 0 each.

## E. Cleanup (2026-10-31 ~11:20 EDT)
`cleanup.py`, one transaction, `DELETE ... RETURNING id` per table (pre-check: 0 non-canary attempts reference the video URL):
```
video refs by non-canary attempts: [[0]]
attempts: ['99d4314e-ca5f-4557-9b46-c0145b186887', '9a849d80-2798-4f54-8069-714795d3a830', 'f191b232-702d-4483-b999-63e58e759225', 'bdc40249-74a6-4429-a0ab-0a5d3b8b106f', '16541880-ccbb-4e74-8ac1-90acbb252cbc']
AnalysisNotification 1 ['7a817939-2a73-49b5-9e0f-3523862ac14f']
ShortLink 1 ['39c664e1-a546-4241-aac7-b9fd57ffc755']
LiftingResult 5 ['80e78d75-86dd-47cf-8162-60c8dbac713e', 'a0b8c6ec-3e57-4420-9f69-6787053683ad', '2ba8e24a-e01a-4a64-874d-f4d936cedae5', 'da4e2916-18f0-4f89-8e6d-ed3e432dcb1f', 'a5c49d8c-b942-4e53-ab97-8afc5253c035']
Attempt 5 ['99d4314e-ca5f-4557-9b46-c0145b186887', '9a849d80-2798-4f54-8069-714795d3a830', 'f191b232-702d-4483-b999-63e58e759225', 'bdc40249-74a6-4429-a0ab-0a5d3b8b106f', '16541880-ccbb-4e74-8ac1-90acbb252cbc']
UserCompetition 1 ['8656a607-bc09-432e-b6e6-b5f4a8a620a3']
User 1 ['6d365544-066a-45eb-a345-79d42bc17648']
after: SELECT COUNT(*) FROM "User" WHERE email LIKE 'hundredclub-canary%' [[0]]
after: SELECT COUNT(*) FROM "UserCompetition" WHERE user_id=CAST(:u AS uuid) [[0]]
after: SELECT COUNT(*) FROM "Attempt" WHERE id::text = ANY(:a) [[0]]
after: SELECT COUNT(*) FROM "LiftingResult" WHERE attempt_id::text = ANY(:a) [[0]]
after: SELECT COUNT(*) FROM "AnalysisNotification" WHERE attempt_id::text = ANY(:a) [[0]]
after: SELECT COUNT(*) FROM "ShortLink" WHERE target_url LIKE '%6d365544-066a-45eb-a345-79d42bc17648%' [[0]]
```
GCS: `gsutil rm` videos/20261031_151256_test_video_plank_10s.mp4, lifting/9a849d80-.../annotated.mp4, summary.json ->
"Operation completed over 3 objects", exit 0. Re-list of each path and og-cards/gpeQMD* -> "matched no objects".
Board after: `GET /competitions/<id>/leaderboard` -> rows [], momentum joined 0 (the pre-cleanup public snapshot
lb_public_seeded.json had the Canary row, so the empty after-state could have read otherwise).
cloud_sql_proxy stopped with `pkill -f cloud_sql_proxy`.

## Leftovers
- None in DB or GCS found by the queries above. SecurityAudit had 0 rows for the canary user_id (register's audit went
  only to the log). Cloud Run log lines mentioning the canary email/user id remain (not deletable, not data).
- A completion email may have been sent to hundredclub-canary-2026-10-31@example.com (not checked).

## Defects
- D1 (pre-existing, backend, not 100 Club code): passwordless `POST /auth/register` returns 500. auth_routes.py writes
  auth_method 'passwordless', but the prod enum `auth_method` is `{google,password}` (22P02, log 2026-10-31T15:12:09Z).
  The CLAUDE.md "Passwordless Users ... registration without password" flow is broken in prod. Email-based /upload
  writes 'password' and so is unaffected.

## Final GCS sweep
`gsutil ls "gs://.../**a5c49d8c-...**"` (LiftingResult id) and `gsutil ls "gs://.../videos/20261031_151256*"` -> both
"matched no objects". Snapshots copied here (untracked, not staged): prove-lb-warmup.json (B), prove-lb-asof.json (C),
prove-asof-checks.txt (31/31 + public checks), prove-lb-public-seeded.json (before cleanup, has the Canary row),
prove-lb-after.json (rows []).
