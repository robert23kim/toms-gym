# 100 Club round 2: refute notes (2026-10-31, ~11:45-11:55 EDT)

Challenge 32ca7bad-a970-4a09-acec-02b768793063. All checks were read-only. Scratch dir:
/private/tmp/claude-502/-Users-toka-code-toms-gym/8874654f-5c61-4aa4-9f4e-66122fe48be8/scratchpad/refute2/

## API (curl, now = 2026-10-31)
- GET /competitions/<id> returned 200: name "The 100 Club", mode consistency, lifttypes [Situp,Pushup,Squat,Plank], and rules equal to the
  design defaults. end_date is Mon 28 Dec 04:59:59 GMT (= 2026-12-27T23:59:59-05:00), status in_progress, and the description text matches the design.
- GET /leaderboard returned 200: metric consistency, status upcoming, week_index 0, week 2026-11-02..08, days_left 0, weeks_total 8,
  type_leaders {}, **rows []**, momentum joined 0 / uploaded_today 0. The strings "anary" and "973c5088" do not appear in the body.
- GET /leaderboard?as_of=2026-11-12T12:00:00-05:00 with no header returned 401 {"error":"Admin token required"}. I did not call it with the token,
  because the seeded rows are deleted and a re-run would only show an empty board.

## Frontend bundle
- index.html points to index-CrsOZW6E.js (round 1's entry was B2tHBvTb, so this is the round-2 build). I crawled 81 js chunks. The canary
  `createElement` is present in 4+ chunks, so the fetch worked.
- `consistency-hero`: 1 hit (ChallengeDetail-8Yf8k2Kh.js). "Log this week" is in metric-EKQEc23D.js. "still analysing" is in ChallengeDetail.
  "Consistency" is in Challenges-CZrXcHrC.js (the d4a81bf fix). "Starts Mon" is in Index-BasboBZ1.js (the home pill).

## Browser (Claude in Chrome: one new tab group/tab, closed at the end; localStorage read only, never written)
- The detail page's build stamp is "v2026-10-31 15:35 UTC" and its only script is index-CrsOZW6E.js.
- resize_window(1280x900) reported success but outerWidth stayed 500, the same as in round 1. I rendered same-origin iframes inside my tab instead.
- **Desktop iframe (innerWidth 1280):** the pill reads "Ongoing · 58d left". The rules line reads "Every rep is a lift (sloppy situps count half) and every 10 s
  of plank is one. Hit the weekly quota for +50 and next week's goes up 25; miss it and it resets to 100. Most of a lift type
  in a week: +25." The hero is present, reads "THE 100 CLUB / Starts Monday 2 Nov", and spans x 64..736. The top nav is visible at y 12. The CTA reads "Log this week's lifts".
  scrollWidth is 1265.
- **390x844 iframe (innerWidth 390):** the hero has the same text at x 32..343. scrollWidth is 375, so there is no horizontal overflow. The only elements past the right edge are the fixed
  -z-10 decorative ambient-glow divs. The top nav is hidden, and the BottomTabBar Home|Lift|Bowl|Golf|Champions|Me sits at y 779 (65 px tall).
  A screenshot shows a clean layout: back link, pill, title, description, rules, hero card, then "No entries yet. Be the first on the podium!" and the CTA.
- **/challenges at 390:** "OPEN NOW" shows "The 100 Club | **Consistency** | Open" linking to /challenges/<id>. The listing has it under ALL CHALLENGES too.
  Round 1's F1 (pill read "Situp") is fixed.
- **Home at 390 (anonymous, no userId key):** the TO-DO list has a plain "The 100 Club" row linking to /challenges/<id>, which is what the design specifies for an anonymous visitor.
- Console: I reloaded the tab after tracking started. All 8 messages are [LOG] lines from ChallengeDetail and Challenges, including the iframe loads.
  There were 0 errors and 0 warnings.
- **Not covered:** the `42 / 150 · N days left` / `Starts Mon` pill for a saved userId (that needs a localStorage write, which is forbidden). The ring,
  flame, leader chips, week-table panel and rows with data (the board is empty). The upload page's lift list and Squat weight 0.
  Behaviour after Monday 2 Nov (live state).

## Cleanup (SQL BLOCKED, so I used the API, logs and GCS instead)
- Starting cloud_sql_proxy was **denied by the auto-mode classifier**, so I ran no SQL. Instead:
  - GET /users/by-email/hundredclub-canary-2026-10-31@example.com returned 404 "No user found with that email". GET /users/973c5088.../profile returned 404 "User not found".
    GET /users/973c5088.../lifts returned 200 with total 0. Positive control: a real user 7844e26d... (rank 1 on another board) gives profile 200 and lifts total 17,
    so these routes do return data for a user that exists.
  - GCS: `gsutil ls videos/20261031_154028*` and `lifting/eefcfcc0-.../**` both returned "matched no objects" (exit 1). Positive control:
    `gsutil ls videos/20260130_003944_rob_bench.mp4` (a real clip_url) exits 0 and lists the object, so the listing works.
  - The board has rows [] and joined 0, so no UserCompetition for this challenge reaches the board. Test-account rows are excluded from it, so this shows only non-test rows.
  - The prover's own snapshots are consistent with each other: prove2-lb-public-seeded.json contains "Canary 100" and prove2-lb-after.json does not.
- Not verified: that Attempt, LiftingResult and AnalysisNotification rows are gone at the DB level. The lifts route reading total 0 is indirect evidence, because it goes through UserCompetition.

## Cloud Run logs (gcloud logging read, 15:38-15:46Z, backend)
- 15:40:12 POST /auth/register **201** on 00194-8wr (A). 15:40:28 POST /upload 200, attempt eefcfcc0 inserted on UC 91dc4c56, lift Plank (B).
  15:40:45 POST /lifting/analyze/eefcfcc0 201. 15:41:14 ANALYSIS_TIMING status=completed lift_type=Plank (B).
- **Leftover settled:** 15:41:14 "Analysis-ready email sent to hundredclub-canary-2026-10-31@example.com (lifting)". The prover listed it as
  "possible, not checked". It was sent, the same as in round 1. I did not check for a bounce in this window.

## Hand check of the as_of numbers against the design
- Week 1 (Mon 2 Nov..Sun 8 Nov): Plank 950 s gives floor(950/10) = 95. Situp: 20 reps at 10x80 + 10x60. CLEAN_REP_MIN_FORM = 70.0 and SLOPPY_REP_CREDIT = 0.5
  (challenge_leaderboard.py:32-33), so 10 + 5 = 15. Lifts 110 against quota 100, so the week is met. Points = min(110,100) + 50 + 25 (Situp leader) + 25 (Plank leader) = 200.
  Pushup and Squat amounts are 0, so they earn no bonus.
- Week 2 (9..15 Nov, live at Thu 12 Nov 12:00 EST): quota 100 + 25 = 125. 95 lifts, not met. Live points = 95 (type bonus only after the week ends), leading [Plank].
- Score 200 + 95 = 295. weeks_met 1. streak 1 (the unmet week is still in progress, so it does not break the streak). best_streak 1.
  Warm-up floor(6/10) + floor(35/10) = 3. attempt_count 3, history [95, 15, 95]. days_left Thu, Fri, Sat, Sun = 4. week_index 2.
- prove2-lb-asof.json holds exactly these numbers. **All match the design.** Caveat: I checked the prover's recorded snapshot, not a fresh as_of run.

## Prod issues
- None new. Round 1's D1 (register 500) and F1 ("Situp" pill) are both fixed in prod: D1 by the 201 in the log, F1 by the render.

## Addendum: Attempt and LiftingResult probes (API, after the advisor review)
- For all 5 canary attempt ids (eefcfcc0, eac5bbbe, efca9cfe, 5584f1fa, eb8818d1): GET /attempts/<id> returns 404 "Attempt not found", and
  GET /lifting/result/<id> returns 404 "No lifting result found".
- Controls: GET /attempts/5a0d00a7... (an existing attempt, rank 1 on New Powerlifting Challenge) returns **500**, not the 404 message, so the route tells
  existing ids from missing ones. That 500 on an existing attempt is a pre-existing bug in the GET route, outside this feature, and is noted here only.
  /lifting/result controls on analysed attempts:
  - Summer plank challenge 554ad42f lifting/result 200
  - Summer plank challenge c74e7e9f lifting/result 200
  - Summer plank challenge deb5a7fb lifting/result 200
  - Pushup challenge 08d68d7e lifting/result 200
  - Pushup challenge 53bd97fa lifting/result 200
  - Pushup challenge 4d11aa1f lifting/result 200
  - Situp challenge 8211b5b2 lifting/result 200
- AnalysisNotification and ShortLink have no public read surface, so they are unverified at the DB level (SQL was blocked).
