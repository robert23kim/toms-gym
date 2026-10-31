# 100 Club round 1: refute notes (2026-10-31, ~11:20-11:30 EDT)

Challenge 32ca7bad-a970-4a09-acec-02b768793063. All checks below are read-only, apart from starting and stopping cloud_sql_proxy.
Scratch: /private/tmp/claude-502/-Users-toka-code-toms-gym/8874654f-5c61-4aa4-9f4e-66122fe48be8/scratchpad/refute/

## API (curl, now = 2026-10-31)
- GET /competitions/<id>: 200. name "The 100 Club", mode consistency, lifttypes [Situp,Pushup,Squat,Plank], rules match the
  design defaults exactly, end_date Mon 28 Dec 04:59:59 GMT (= 2026-12-27T23:59:59-05:00), status in_progress.
  Odd but harmless: `location` holds the description text.
- GET /leaderboard: 200. metric consistency, consistency.status upcoming, week_index 0, week 2026-11-02..08, days_left 0,
  weeks_total 8, type_leaders {}, rows [] (no Canary), momentum joined 0.
- GET /leaderboard?as_of=2026-11-12T12:00:00-05:00 with no header: 401 {"error":"Admin token required"}. I did not
  re-run the as_of call with the token, because the seeded rows are gone.

## Frontend bundle
- index.html -> index-B2tHBvTb.js -> 71 chunk refs, all fetched (72 js files). `consistency-hero`: 1 hit, in ChallengeDetail-C82ndvRW.js.
  "Log this week's lifts" is in metric-EKQEc23D.js, and "still analysing" is in ChallengeDetail. Canary: 4 chunks contain createElement, so the fetch worked.

## Browser (Claude in Chrome, one tab in a new group, closed at the end; localStorage was not written)
- Desktop (innerWidth 1272): the detail page shows the status pill "Ongoing · 58d left", the title, the description, and the rules line
  "Every rep is a lift (sloppy situps count half) and every 10 s of plank is one. Hit the weekly quota for +50 and
  next week's goes up 25; miss it and it resets to 100. Most of a lift type in a week: +25.". The hero
  [data-testid=consistency-hero] reads "THE 100 CLUB / Starts Monday 2 Nov". There is an empty-board state, and the CTA reads "Log this week's lifts".
  After a reload there were 0 console errors (tracking started before the reload).
- 390x844: resize_window reported success twice but had no effect (outerWidth stayed 1272). Instead I rendered the
  same-origin URL in a 390x844 iframe inside my tab, where the iframe's innerWidth was 390. The hero was present at x 32..343 with the same text,
  scrollWidth was 375 (no horizontal overflow), the top nav was hidden, and the BottomTabBar (Home|Lift|Bowl|Golf|Champions|Me) sat at y 779..844.
  A screenshot (zoom) shows a clean layout. I did not capture console output from inside the iframe.
- /challenges at 390: "OPEN NOW" lists The 100 Club and links to /challenges/<id>, not the upload route. **Its pill reads
  "Situp"** (Challenges.tsx RowCard pill={c.categories?.[0]}). This is a pre-existing pattern ("Biceps and Bench" shows only
  "Bench Press"), but it labels a four-type consistency challenge as a situp challenge.
- Home at 390, anonymous (no userId key): the TONIGHT'S TO-DO list has a plain "The 100 Club" row linking to
  /challenges/<id>. That matches the design for anonymous visitors. **Not covered:** the `42 / 150 · N days left` / `Starts Mon` pill
  needs a saved userId, and I did not write localStorage.
- Not covered: the hero ring, flame and leader chips (no participants), the upload page's lift list and Squat weight 0,
  and the week table panel.

## SQL (cloud_sql_proxy :5433, read-only SELECTs, proxy stopped with pkill)
- Canaries: User count 158; the Competition 32ca7bad row exists (1); ShortLink count 40.
- 0 User rows by canary email, id or name "Canary 100". 0 UserCompetition rows for the canary user or for this competition. 0 Attempt rows
  for the 5 attempt ids or UC 8656a607. 0 LiftingResult rows for those attempts. 0 AnalysisNotification rows by canary email. 0 ShortLink rows by
  id 39c664e1 or by target containing the user id.
- enum_range(auth_method) = {google,password}. auth_routes.py:389 writes 'passwordless', so D1 is confirmed in code.

## Cloud Run logs (gcloud logging read, 15:11-15:25Z)
- 15:12:09 POST /auth/register 500, with 22P02 invalid enum "passwordless" (A1). 15:12:46 register 201 for user 6d365544 (A2).
- 15:12:56 upload with Plank, weight 0.0, attempt 9a849d80 on UC 8656a607. 15:13:02 analyze 201. 15:13:34 ANALYSIS_TIMING status=completed (B1).
- **Leftover settled:** at 15:13:34 the log reads "Analysis-ready email sent to hundredclub-canary-2026-10-31@example.com". At 15:13:40 a
  mailer-daemon bounce reached the app's email-upload inbox and was skipped as auto-submitted. One real outbound email therefore bounced. The prover listed this as
  "may have been sent". It was sent.

## Hand check of the as_of numbers against the design
- Week 1: Plank 950 s -> 95 lifts. Situp: 20 reps at 10x80 + 10x60, with CLEAN_REP_MIN_FORM 70 and SLOPPY 0.5, gives 10 + 5 = 15. Lifts 110 against quota 100, so the week is met.
  Points = min(110,100) + 50 + 2x25 (Plank and Situp leader, sole participant, amounts > 0) = 200. Correct.
- Week 2 (live at Thu 12 Nov): quota 100+25 = 125, Plank 95 lifts, not met. Live points = 95 (no type bonus mid-week). Correct.
- Score 295, streak 1 (the in-progress week does not break it), weeks_met 1, warm-up floor(6/10)+floor(35/10) = 3, attempt_count 3,
  history [95,15,95], days_left Thu..Sun = 4, week 2026-11-09..15. All consistent with the design.

## Prod issues
- D1 (backend, pre-existing): passwordless register returns 500 (confirmed in log, enum and code).
- F1 (frontend, low): the /challenges "Open now" card pill says "Situp" for The 100 Club.
