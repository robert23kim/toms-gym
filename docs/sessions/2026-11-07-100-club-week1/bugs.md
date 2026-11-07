# The 100 Club: week-1 review (2026-11-07, Saturday of week 1)

Read-only pass over production (backend `my-python-backend-00194-8wr`, frontend `my-frontend-00197-h8f`,
both still the ship revisions) from the public API, the admin `as_of` preview, Cloud Run request logs and
an anonymous Chrome walk at desktop width. No data was changed. This file is the input to the
fix/deploy/prove workflow `.claude/workflows/100-club-fix-deploy-prove.js`.

## Where it stands

- Two athletes: caleb.li.larson (rank 1, 150 pts, 107.5 lifts: Pushup 65, Situp 31.5, Plank 11 = 119.5 s)
  and Toka (rank 2, 150 pts, 100 lifts: Pushup 52, Situp 40, Plank 8 = 82.8 s). Both met the 100 quota,
  streak 1. Leaders: Situp Toka, Pushup and Plank caleb. 11 uploads, all `/upload/signed-url` +
  `/upload/finalize` pairs returned 200; no 5xx on the backend since 2 Nov.
- Monday preview (`?as_of=2026-11-09T12:00:00-05:00`, admin token): week 1 locks as caleb 200 pts
  (100 + 50 + 2 x 25), Toka 175 (100 + 50 + 25); both start week 2 at quota 125, streak 1, leaders `{}`.
  Nothing on the page tells either of them this is coming (B4).
- No user tickets mention the 100 Club. One open ticket from 2026-09-15 ("email link is wrong",
  analysis-ready email) is unrelated to this change and untouched here.

## Findings

Severity: major = a user is misled or blocked; minor = confusing or cosmetic. Side: frontend / backend /
android / data / decision.

### B1 major, android + backend: Tom's phone runs the 13 Sep APK, which predates the 100 Club
Evidence: every Toka upload this week came from `Mozilla/5.0 (Linux; Android 16; SM-S926U1 ... wv)` (Cloud
Run request log, 2 Nov 12:43Z, 3 Nov 12:38Z, 6 Nov 13:20-13:24Z); every caleb upload from iPhone Chrome.
Toka's five attempts carry `weight 60`, caleb's `0`. The inline challenge form posts `0` for consistency
lifts since bc8665c; the Sep 13 bundle posted the `"60"` default. The last APK in
`gs://jtr-lift-u-4ever-cool-bucket/apk/` is `tomsgym-debug-20260913-165022.apk` (2026-09-13T20:50Z) and
`frontend/android/app/src/main/assets/public/index.html` is stamped 1789332615 (13 Sep). At commit 6244abe
(the Sep 13 tree) `metric.ts` renders an unknown metric as `TOTAL` / `lbs` and the challenges list pill is
`categories[0]`, so on the phone the board reads "150 lbs", the pill says "Situp", and there is no hero,
ring, week line, leader chips or week table. This is very likely the "confusing" experience.
Fix: (a) rebuild and publish the APK (`cd frontend && VITE_BUILD_TIMESTAMP=$(date +%s) npm run android:build
&& npm run android:publish`, see `docs/reference/android-app.md`; the new short link has to be installed on
the phone); (b) backend guard in `upload_routes.py` (and the signed-url finalize path): coerce `weight_kg`
to 0 when `lift_type` is Pushup, Situp or Plank, so a stale client cannot post 60 again; (c) leave the five
`weight 60` rows alone: weight does not enter the consistency score (data, deferred).

### B2 major, frontend: the result pages still show the rank ladder on a consistency board
Evidence (live page text, `/challenges/<id>/participants/<toka>/video/c9dec98b...`): "WHERE TOKA STANDS
#2 of 2 · 0 pts to pass caleb.li.larson · caleb.li.larson 150 pts · 0 pts to pass · Toka 150 pts · Beat
this →", then "Board score 13 · 13 clean of 13 · sloppy reps count half". `lib/standing.ts::deriveStanding`
has no consistency branch (only `attemptScore` returns null), `ChallengeDetail` hides `StandingCard` for
consistency but `AnalysisStatus.tsx` and the video page still render `ResultLadder`. After an upload the
reveal shows only "Grade C" (score null for consistency). Nobody is told "13 lifts banked, 40 / 100 this
week, 2 days left", which is the one number the challenge is about.
Fix: on a consistency board replace `ResultLadder` on both pages with a small consistency result block
(lifts this attempt added, this week's `lifts / quota`, met or not, days left, link to the board); keep the
form grade. `deriveStanding` can return null for `metric === "consistency"` so no caller shows a ladder.

### B3 major, frontend: type bonuses are invisible until the week locks
Evidence: hero chips say "Pushup caleb.li.larson 65 LEADING" and "You lead ..." (for the viewer), but the
podium shows 150 pts for both and the expanded week table shows Bonuses "—", Points 150 (live week).
Monday both scores jump (200 / 175) with no warning. By design the live week's leaders are provisional
(`consistency.py`, `bonuses = led if finished(w) else []`), but the page never says so.
Fix (copy only): in `ConsistencyWeekTable` render the live week's provisional leads as e.g. "Pushup, Plank ·
locks Sun" from `this_week.leading` (pass the viewer row or the row's `this_week.leading`), and add one
line under the hero chips: "Type bonuses (+25 each) are added when the week ends on Sunday." In the podium
`this week` line, nothing changes.

### B4 minor, frontend: tied points with no visible tiebreak
Evidence: caleb #1 with the trophy, Toka #2, both "150 pts". The tiebreak is this week's lifts (107.5 vs
100), shown only as the small "107.5/100 this week" text. Fix (copy): when the row above has the same
score, the podium/this-week line can say "tied · more lifts this week", or the hero caption for the viewer
can say "Tied with caleb.li.larson on points; lifts this week break the tie." Decide the wording in the
fixer; keep it one short line.

### B5 minor, frontend: two countdowns on one page
Evidence: status pill "Ongoing · 51d left" (challenge end, and one day high: end is Sun 27 Dec local, stored
as 28 Dec 04:59Z) next to the hero's "Week 1 of 8 · 2 days left". Fix: on a consistency board the
`StatusPill` reads "Week 1 of 8 · ends 27 Dec" (or just hide the day count); the hero keeps the week line.

### B6 minor, frontend: the Lift hub advertises the 100 Club as "Plank challenge"
Evidence: `/lift` shows "Plank challenge · Record your plank — straight to the board". `LiftHub.tsx` picks
the first ongoing challenge whose categories include "Plank", which is now the 100 Club. Fix: when the
picked challenge has `mode === "consistency"`, label the tile "The 100 Club · Log this week's lifts"; also
the hub's primary "Upload a lift" (`/lift/upload`) posts `competition_id '1'`, so a lift logged from there
never counts for the club. Add the club tile above it; do not change the generic upload.

### B7 minor, frontend: the week table has no per-type breakdown and fractions look odd
Evidence: caleb's week row reads "107.5" with no sign that 31.5 came from sloppy situps; the hero says
"Situp Toka 40" but his own situps (31.5) are nowhere. The payload already carries `by_type` and
`plank_seconds` per week. Fix: a second line per week row (or a tooltip-free small text) "Situp 31.5 ·
Pushup 65 · Plank 11 (119 s)".

### B8 minor, frontend: "Everyone else" header over an empty table
Evidence (anonymous, 2-athlete board): the podium holds everyone, so the section below is the header
"Everyone else", the column header row and the single "YOU · Not logged yet" button. Fix: when
`tableRows` is empty, drop the header and the column row and show the YOU row alone (keep it as the CTA).

### B9 minor, frontend: profile shows "Situp · 60kg" / "Pushup · 60kg"
Evidence: `/profile/<toka>` lift list. Consequence of B1 (weight 60 posted) plus `LiftHistoryList.tsx`
hiding weight only for plank, and the pre-existing lbs-on-the-form vs kg-on-the-profile mismatch. Fix: hide
the weight for pushup and situp rows too (bodyweight), independent of the stored value.

### B10 minor, frontend: hero eyebrow repeats the title
Evidence: "The 100 Club" h1, then the hero card's eyebrow "THE 100 CLUB" directly under it. Fix: eyebrow
"WEEKLY QUOTA" (or drop it).

### B11 data, unexplained: two 404s on `GET /lifting/result/5a0d00a7-cf40-4063-80d5-49e163f02b93`
4 Nov 05:25Z and 07:55Z on the backend host. That is the `AnalysisStatus` poll URL; the id is not one of the
club's attempts and nothing else was logged around it. Noted, not chased.

### B12 decision (QA-5, now concrete): no minimum for a type bonus
On Monday caleb's +50 comes from leading two types with 65 pushups and 119 s of plank, which is fine, but
the same +25 would go to a single 10 s plank if nobody else planked. Decision needed: keep as is, or require
a minimum (e.g. 10 lifts of the type) before a type bonus is awarded.

## Not covered by this pass
- No render with Tom's viewer state (ring, caption, "You lead", home pill): writing `userId` into
  localStorage in Tom's Chrome is blocked, correctly. The workflow proves it with a scripted Playwright
  context instead.
- No phone-width render: `resize_window` reported success but `window.innerWidth` stayed 1684 (checked).
- Console errors on a tracked load were not captured (tracking started after the first navigation).
- Squat counting and the engine are out of scope.
