# Prove notes, round 2 (2026-11-14 03:13-03:16Z), production

Revisions read back with `gcloud run services describe` at 03:13Z: my-frontend-00205-95c 100 %, my-python-backend-00196-mtt
100 %, bowling-service-00053-fxm 100 % (image gcr.io/toms-gym/bowling-service:situp-13b49b5). Live index build-timestamp
1794625712, entry index-DVWVYKuZ.js; bundle-after-2/index.html is byte-equal to the live index I fetched.
Nothing was written: every non-GET in every browser case was fulfilled by a stub (prove2/prove-c1-results.json, "stubbed").
git status at the end: only .claude/settings.json and frontend/.env.production modified (pre-existing), nothing staged, HEAD
668529b. I edited only prove-c1.mjs in this notes dir (env NEW / LIVE / OUTDIR, plus a round1Bonus count); evidence is in prove2/.

## A. API (curl, read-only)
- GET /competitions/<club>/leaderboard at 03:13Z (prove2/lb-prove2.json) and at 03:15Z after all browser runs
  (prove2/lb-prove2-end.json): whole JSON equal to live-before.json (python == True; end copy cmp byte-equal).
  caleb.li.larson 1/375/147/14, Toka 2/350/162.5/14 (rank/score/this_week.lifts/attempt_count). Could have failed: any field change breaks equality.
- GET /users/<reporter>/lifts: 15 lifts, equal to the gate copy reporter-lifts.json; f47a8848 = squat, total_reps 12, grade D, completed.
- `gsutil ls -l .../lifting/f47a8848.../summary.json`: 33496 B, mtime 2026-11-12T16:56:40Z (original analysis, no re-analysis).
- Not covered: DB rows directly.

## B. C1 in a real browser (prove-c1.mjs, headless Chromium via Playwright, fresh context per case, ctx.unrouteAll +
page.unrouteAll, function matcher, every non-GET stubbed, 1500 ms wait; innerWidth asserted 390 and 1280 in every case)
Run: `OUTDIR=prove2 LIVE=prove2/lb-prove2.json NEW='where nobody logs more' node prove-c1.mjs`, rc 0, no crashes.
Text per case: prove-c1-<case>-<width>.txt (+ -findprofile / -after), overwriting round 1's copies; screenshots in prove2/.

| case | 390 and 1280 (identical results) |
|---|---|
| 1 anon, empty storage (userId null) | you-row-unknown 1, "Not logged yet" 0, text "? / YOU / Find your profile / This device doesn't know who you are yet", href /find-profile?next=%2Fchallenges%2F<club>. Before (before-you-row-anon.txt): "— / YOU / Not logged yet". Click -> /find-profile?next=..., "Who am I?" rendered, nothing submitted |
| 2 reporter id via addInitScript | you-row 0, you-row-unknown 0, "Not logged yet" 0; viewer block 1, ring "147 / 125", receipt "175 pts this week / 200 if the lead holds · 375 overall" |
| 3 random uuid | you-row data-entered="false", "— / YOU / Not logged yet" |
| 4a Find Profile page path | empty storage -> prompt -> /find-profile?next -> fake email -> GET by-email STUBBED 200 with his id -> "Back to the challenge" -> board: userId = his id, you-row-unknown 0, "Not logged yet" 0, ring 147 / 125 |
| 4b board inline upload | empty -> prompt -> find-profile -> by-email STUBBED 404 -> "Upload something" (/challenges/<club>?upload=1) -> form -> fake email + 4 KB fake clip -> signed-url, GCS PUT, finalize (user_id = his id), analyze all STUBBED -> toast "Upload Successful! / Analyzing your form automatically. This device now logs as prover@example.invalid. / Not me"; userId = his id; you-row-unknown 0, "Not logged yet" 0, ring 147 / 125 |
| synthetic (his id; board GET STUBBED = live JSON + 3 fake rows ahead) | you-row data-entered="true": "4 / caleb.li.larson · You / 147/125 this week / 325pts to reach #3 / 375pts" |

- (2) literal "you-row data-entered=true with his live rank and score" does NOT hold on the live board and cannot: both
  athletes are on the podium, the table is empty, and ChallengeDetail renders no YOU row for a recognised podium viewer
  (unchanged from baseline, QA-2). Identity on the live board is shown by the hero (ring 147 / 125); data-entered="true"
  with his rank/score is shown only on the stubbed synthetic board. The reporter case does not discriminate the fix
  (the old build also showed no "Not logged yet" with his id stored; refute notes).
- Console errors: random case 1 x 404 /users/<fake uuid>/profile (my fake id); flow-inline 1 x 404 by-email (my stub);
  every other case 0; pageerrors 0 everywhere. No pre-deploy baseline captured, so "none new" = none not explained by my fake inputs.
- The only non-GET on every plain page load is POST /log-error (boot telemetry), stubbed.
- Closed identity paths NOT driven: Login (credentials), MagicLink (real token), navbar FindProfile dialog, UploadVideo
  /challenges/:id/upload (pre-existing setItem, unchanged), Home to-do PromptList (needs an existing id), "Not me" on prod.
- 4b stubs finalize, so prod returning user_id was not observed (dating evidence only, see round 1 addendum).
- After 4b the URL still ends ?upload=1 (observed); whether a reload re-opens the form was not checked.

## C. C2 wording
- Live page text, every case at both widths: rules line "... +25 extra for each lift type you log that week where nobody
  logs more, up to +100; any mix counts toward the quota." and hero note "+25 extra for each lift type you log that week
  where nobody logs more, locked in when the week ends on Sunday." Old sentence "Most of a lift type in a week" 0;
  round-1 clause "nobody logs more than you" 0; new clause 2 per page.
- Bundle bundle-after-2/ (83 files, 0 empty, index byte-equal to live): canaries "Not logged yet" 1, consistency-hero 1,
  you-row-unknown 1, so the fetch is valid. Old sentence 0, round-1 clause 0, new clause 1 (metric-Dd4wUX1y.js; live
  copy re-fetched 200, cmp identical). bundle-before/: old sentence 1, so the count could have matched.
- Defect: docs/reference/100-club.md:16 (committed at HEAD) still says "25 extra for each lift type where nobody logs more
  than you that week", the round-1 clause the app no longer uses; C2 asked every wording to agree (flagged in notes-fix-2.md, not fixed).

## D. C3 (engine NOT deployed)
Production still counts 12 on his squat (A; bowling-service-00053-fxm, image situp-13b49b5 unchanged). Why (notes-engine.md
sections 5-6): the miscount reproduces (12 in the prod image; rep 12 is the walk-out stride) and the fix gives 10 offline, but
deploy_ok = false because the labelled squat regression set is 0 clips (< 3), so the regression check could not fail:
Decision needed (Tom). 12 vs 10 does not change his points: over the 125 cap (147 lifts) and leads Squat either way.

## E. APK
`gsutil ls -l`: gs://jtr-lift-u-4ever-cool-bucket/apk/tomsgym-debug-20261113-221223.apk, 4815373 B, 2026-11-14T03:12:24Z.
`curl -sI /s/oVzVrt`: HTTP/2 302, location = storage.googleapis.com signed URL for that object (7 days).
Downloaded the object: index build-timestamp 1794625920; metric-Dd4wUX1y.js has the new clause 1 and the old sentence 0;
ChallengeDetail-Dr99dmtJ.js has you-row-unknown 1. Installing on a phone or emulator: NOT covered.

## Not covered
- The reporter's actual device (iPhone Chrome, CriOS 157, origin t30g.com) and browser were never touched; his storage
  there is unknown. t30g.com not re-run this round.
- Headless desktop Chromium only: no WebKit / iOS, no APK WebView; no real upload, sign-in or email.
- Analysis-ready email links and shared /s/ links still do not establish identity (open by design, needs a backend marker).
