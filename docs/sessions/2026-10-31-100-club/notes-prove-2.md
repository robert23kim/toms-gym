# 100 Club round 2: prove notes (2026-10-31, ~11:39-11:43 EDT)

Challenge 32ca7bad-a970-4a09-acec-02b768793063. Live revisions confirmed via `gcloud run services describe`:
backend **my-python-backend-00194-8wr** (100% traffic), frontend **my-frontend-00197-h8f**.
Scripts: session scratchpad `prove2/` (db.py = pg8000 via cloud_sql_proxy :5433 per notes-gate.md; reg.py, poll.py,
seed.py, asof.py, cleanup.py; the last four adapted from round 1's `prove/`).

## Pre-state
`GET /competitions/<id>/leaderboard` -> 200, metric consistency, rows [], momentum joined 0, status upcoming,
week_index 0, days_left 0, type_leaders {}.

## A. Canary user (re-proves round-2 fix f5eee14)
- `POST /auth/register {"email":"hundredclub-canary-2026-10-31@example.com","name":"Canary 100"}` (**no password field**) ->
  **201** `{"message":"Registration successful","user_id":"973c5088-3a2b-4b22-af7c-a7fd21286c57"}`.
  Round 1 got 500 on the identical body (D1), so this could have failed and did not.
- DB read-back: name "Canary 100", is_test **false**, auth_method **NULL**, password_hash NULL.
- Not covered: the magic-link / Find Profile flows for this user were not exercised.

## B. Real upload
- `curl -F video=@backend/tests/fixtures/test_video_plank_10s.mp4 -F user_id=973c5088-... -F competition_id=32ca7bad-...
  -F lift_type=Plank -F weight=0 /upload` -> 200, **attempt_id eefcfcc0-f4ea-4c6d-9c0c-2c70c3f86652**,
  user_competition_id 91dc4c56-269d-4318-983a-f8aa2ccc4cda,
  url https://storage.googleapis.com/jtr-lift-u-4ever-cool-bucket/videos/20261031_154028_test_video_plank_10s.mp4
- `/upload` does not dispatch analysis; the client calls `POST /lifting/analyze/<attempt_id>` (frontend api.ts:394,
  lifting_routes.py:14). Called at 11:40:45 -> 201 `{"lifting_result_id":"ed3be202-1a0f-4f5e-8c80-96d4112e77f8","status":"queued"}`.
- poll.py (`GET /users/<uid>/lifts` every 45 s, in-process time.sleep): 11:40:52 analysis_status processing, hold_s null;
  **11:41:37 completed, hold_s 6.0**, steadiness 3.66. (That endpoint renames total_in_plank_s to hold_s; DB
  `LiftingResult.report->>'total_in_plank_s'` = "6.0", processing_status completed.)
- Public `GET /leaderboard` (prove2-lb-warmup.json): 7/7 PASS - canary row warmup_lifts **0** (= floor(6.0/10)),
  score 0, attempt_count 0, history [], weeks [], streak 0, this_week {index 0, quota 100, lifts 0, pending 0},
  consistency.status upcoming, week_index 0, days_left 0; momentum joined 1, uploaded_today 1; 1 row.
  Caveat: a 6 s hold makes the expected warm-up count 0, so this alone could not distinguish "warm-up counted" from
  "warm-up ignored"; a 35 s warm-up row was seeded in C (prover's addition, as in round 1) so the count discriminates.

## C. Seeded weeks (cloudsql writable)
Column shapes copied from the real attempt (`SELECT * FROM "Attempt" WHERE id=<real>`: id, user_competition_id,
lift_type, weight_kg, status, video_url, created_at, updated_at) and information_schema for LiftingResult.
seed.py: one transaction; ids written to seed_ids.json before insert; weight_kg 0, status completed,
created_at = updated_at = ts, video_url = the real upload's URL, LiftingResult processing_status completed.
| attempt_id | LiftingResult id | created_at (UTC) | lift | report |
|---|---|---|---|---|
| eac5bbbe-3355-46ee-92e0-67d05b83fba6 | 3c95be36-8380-4d4d-b526-919ea9c4e971 | 2026-11-03T12:00Z (Tue wk1) | Plank | total_in_plank_s 950, form 80 |
| efca9cfe-b5ba-49d1-8576-51e10696e823 | 4ed26d1b-f382-4512-857c-595259ce9b73 | 2026-11-04T12:00Z (Wed wk1) | Situp | total_reps 20, form 75, rep_metrics 10x80 + 10x60 |
| 5584f1fa-8358-44aa-9fef-7397024de4ff | 6a30d3a4-7025-4f64-87fb-4d9a3dd650ea | 2026-11-10T12:00Z (Tue wk2) | Plank | total_in_plank_s 950, form 80 |
| eb8818d1-8707-4f8c-924a-6bf76ca20af1 | f31b25b1-22ee-4de2-9cc7-001c9baf661f | 2026-10-31T16:00Z (warm-up) | Plank | total_in_plank_s 35 (prover addition) |
Read-back join: 5 attempts on the UC (real + 4 seeded), all completed, reports as above (rep_metrics length 20).

asof.py (admin token fetched inside the Python process via `gcloud secrets versions access`, never printed; urllib):
- `?as_of=2026-11-12T12:00:00-05:00` no header -> **401** `{"error": "Admin token required"}`; wrong token -> **401**.
- with `X-Admin-Token` -> **200**. **37 PASS, 0 FAIL** (prove2-asof-checks.txt):
  weeks[0] = {index 1, quota 100, lifts 110, met true, bonuses [Situp, Plank], points 200,
  by_type {Plank 95, Situp 15, Pushup 0, Squat 0}, plank_seconds 950}; weeks[1] = {points 95, bonuses []}; len(weeks) 2;
  this_week = {index 2, quota 125, lifts 95, met false, leading [Plank], pending 0};
  score 295; streak 1; best_streak 1; weeks_met 1; warmup_lifts 3 (6 s -> 0 + 35 s -> 3); attempt_count 3;
  history scores [95, 15, 95]; rank 1; consistency.status live, week_index 2, week_start 2026-11-09, week_end 2026-11-15,
  type_leaders.Plank = [canary]; **days_left observed 4** (design: Thu 12 Nov -> Thu, Fri, Sat, Sun = 4).
- Public board (no as_of, now 2026-10-31) after seeding -> 200: canary score 0, attempt_count 0, history [], weeks [],
  warmup_lifts 3, status upcoming (future-dated rows do not leak into today's board).
- Not covered: single participant, so ties, a second athlete taking a bonus, ranking tiebreaks and the reset after a
  missed week were not exercised in prod (unit tests only, not re-run here). No Pushup or Squat lifts seeded. Situp
  half-credit proven with seeded rep_metrics, not an engine-produced situp report.

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
     "user_id": "973c5088-3a2b-4b22-af7c-a7fd21286c57"
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
  "attempt_id": "5584f1fa-8358-44aa-9fef-7397024de4ff",
  "best_by_lift": {},
  "best_streak": 1,
  "clip_url": "https://storage.googleapis.com/jtr-lift-u-4ever-cool-bucket/videos/20261031_154028_test_video_plank_10s.mp4",
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
  "user_id": "973c5088-3a2b-4b22-af7c-a7fd21286c57",
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
The task scopes D to "only if chrome is writable"; the gate says chrome=false (notes-gate.md section 6). No Chrome or
Playwright call was made. **Not covered:** the /challenges listing (and the round-2 "Consistency" pill fix d4a81bf),
the consistency-hero render (pre-start state, rules line, Canary warm-up row), the 390x844 layout, and the home to-do
"The 100 Club" pill. The only frontend evidence is notes-deploy-2.md's bundle canary (strings present in the served
chunks), which is not a render.

## Side effects observed before cleanup (precleanup inventory)
- Analysis completion wrote AnalysisNotification 86e6c6c3-de32-4f64-a573-4caefd544649 (email = canary @example.com,
  short_code null) and ShortLink E6WNaa (a687dadb-1747-4cf7-86da-804556e15a57, created_by_user_id NULL, target
  .../challenges/32ca7bad.../participants/973c5088.../video/eefcfcc0..., og_image_url NULL). A completion email to the
  example.com address may have been attempted (not checked).
- WeeklyMaxLift, SecurityAudit, UserSession, BowlingResult rows for the canary: 0 each.
- GCS: videos/20261031_154028_test_video_plank_10s.mp4; lifting/eefcfcc0-.../annotated.mp4 and summary.json.
  Bucket-wide `gsutil ls "**eefcfcc0-...**"` returned exactly those two lifting objects (search canary works);
  `**973c5088-...**` and `**E6WNaa**` and `og-cards/E6WNaa*` matched no objects.

## E. Cleanup (~11:43 EDT)
cleanup.py, one transaction, `DELETE ... RETURNING id`, pre-check: 0 non-canary attempts reference the video URL.
```
video refs by non-canary attempts: [[0]]
attempts: ['eefcfcc0-f4ea-4c6d-9c0c-2c70c3f86652', 'eac5bbbe-3355-46ee-92e0-67d05b83fba6', 'efca9cfe-b5ba-49d1-8576-51e10696e823', '5584f1fa-8358-44aa-9fef-7397024de4ff', 'eb8818d1-8707-4f8c-924a-6bf76ca20af1']
AnalysisNotification 1 ['86e6c6c3-de32-4f64-a573-4caefd544649']
ShortLink 1 ['a687dadb-1747-4cf7-86da-804556e15a57']
LiftingResult 5 ['ed3be202-...', '3c95be36-...', '4ed26d1b-...', '6a30d3a4-...', 'f31b25b1-...']
Attempt 5 (the five above)
UserCompetition 1 ['91dc4c56-269d-4318-983a-f8aa2ccc4cda']
User 1 ['973c5088-3a2b-4b22-af7c-a7fd21286c57']
after: User email LIKE 'hundredclub-canary%' [[0]]; UserCompetition [[0]]; Attempt [[0]]; LiftingResult [[0]];
       AnalysisNotification [[0]]; ShortLink target LIKE '%973c5088...%' [[0]]
```
GCS: `gsutil rm` the video + 2 lifting objects -> "Operation completed over 3 objects", exit 0. Re-list of
`videos/20261031_154028*`, `lifting/eefcfcc0-.../**`, `og-cards/E6WNaa*`, `**ed3be202-...**` -> all "matched no objects".
Board after: `GET /leaderboard` -> 200, rows [], momentum joined 0 (prove2-lb-public-seeded.json contains the Canary
row, prove2-lb-after.json does not, so the empty after-state could have read otherwise).
cloud_sql_proxy stopped with `pkill -f cloud_sql_proxy` (exit 0).

## Leftovers
- None found in DB or GCS by the queries above. Cloud Run log lines with the canary email/id remain (logs, not data).
- A completion email may have been sent to hundredclub-canary-2026-10-31@example.com (not checked).

## Defects
- None found in this run. Round 1's D1 (passwordless register 500) is fixed in prod: same body -> 201, auth_method NULL.

## Snapshots (untracked, not staged)
prove2-lb-warmup.json (B), prove2-lb-asof.json (C, full board), prove2-asof-checks.txt (37/37), prove2-lb-public-seeded.json
(before cleanup, has Canary row), prove2-lb-after.json (rows []).
