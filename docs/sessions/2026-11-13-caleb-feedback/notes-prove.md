# Prove notes, round 1 (2026-11-14 ~02:40-03:00Z), production

Revisions read back with `gcloud run services describe` at ~02:55Z: my-frontend-00204-rnr 100 %, my-python-backend-00196-mtt
100 %, bowling-service-00053-fxm 100 % (image situp-13b49b5). Live index build-timestamp 1794623705, entry index-Co1bRjjV.js
(same on run.app and on https://t30g.com, the origin the reporter used, and in bundle-after/index.html).
Nothing was written: every non-GET in every browser case was fulfilled by a stub (lists in prove/prove-c1-results*.json).
git status at the end: only .claude/settings.json and frontend/.env.production modified (pre-existing); nothing staged or committed by me.

## A. API (curl, read-only)
- GET /competitions/<club>/leaderboard at 02:41Z (prove/lb-prove.json) and again at the end (prove/lb-prove-end.json):
  (name, rank, score, this_week.lifts, attempt_count) = caleb.li.larson 1/375/147/14, Toka 2/350/162.5/14, identical to
  live-before.json both times.
- Reporter attempt f47a8848-dba0-42ce-9f31-7ef9ac585fbd in GET /users/<reporter>/lifts: squat, total_reps 12, grade D.
  All 15 of his lifts (attempt, type, reps, grade, status) are identical to the gate copy reporter-lifts.json.
  `gsutil cat .../lifting/f47a8848.../summary.json`: total_reps 12, grade D; `gsutil ls -l` mtime 2026-11-12T16:56:40Z
  (the original analysis), so nothing re-analysed it.
- /health healthy.

## B. C1 in a real browser (prove-c1.mjs; headless Chromium 145 via Playwright 1.58.2, fresh context per case,
context.route + page.unrouteAll, function matcher, every non-GET stubbed, 1500 ms after first load; innerWidth asserted 390 / 1280)
Results: prove/prove-c1-results.json (both widths), prove/prove-c1-results-t30g.json (390 on t30g.com). Text per case:
prove-c1-<case>-<width>.txt (+ -findprofile / -after), screenshots in prove/.

| case | 390 | 1280 |
|---|---|---|
| 1 anon (empty storage) | you-row-unknown 1, "Not logged yet" 0, text "? / YOU / Find your profile / This device doesn't know who you are yet" (before: "— / YOU / Not logged yet", before-you-row-anon.txt); tap -> /find-profile?next=%2Fchallenges%2F<club>, "Who am I?" rendered, nothing submitted | same |
| 2 reporter id (addInitScript) | you-row 0, you-row-unknown 0, "Not logged yet" 0; hero viewer block present, ring "147 / 125", receipt "175 pts this week / 200 if the lead holds · 375 overall", Squat 12 LEAD | same |
| 3 random uuid | you-row data-entered="false", "— / YOU / Not logged yet" | same |
| 4a Find Profile path (empty storage -> you-row-unknown -> /find-profile?next -> typed prover@example.invalid -> GET by-email STUBBED 200 with his id -> "Back to the challenge") | userId = his id after lookup; on board: you-row-unknown 0, "Not logged yet" 0, ring 147 / 125 | same |
| 4b board inline upload (empty storage -> you-row-unknown -> find-profile -> by-email STUBBED 404 -> "Upload something" (href /challenges/<club>?upload=1) -> form open -> fake email + 4 KB fake clip -> signed-url / GCS PUT / finalize (user_id = his id) / analyze all STUBBED) | toast "Upload Successful! / ... This device now logs as prover@example.invalid. / Not me"; userId = his id; you-row-unknown 0, "Not logged yet" 0, ring 147 / 125 | same |
| synthetic (his id; leaderboard GET STUBBED = live JSON + 3 fake rows ahead, so he is off the podium) | you-row data-entered="true": "4 / caleb.li.larson · You / 147/125 this week / ... / 375pts" | same |
| t30g.com anon + reporter | same as rows 1 and 2 | not run |

The literal ask "(2) you-row data-entered=true with his live rank and score" does NOT hold and cannot on live data: both
athletes are on the podium, so the table is empty and ChallengeDetail renders no YOU row for a recognised viewer
(lines 893-931, unchanged by this run; fix notes QA-2). Identity is proven through the hero instead; data-entered="true"
was only seen on the synthetic board.

Console errors (all cases listed in the results json; no pageerrors in any case):
- random: 1 x "Failed to load resource 404 /users/<random uuid>/profile": caused by my fake id.
- flow-inline: 1 x 404 on /users/by-email/prover@example.invalid: my stub returning 404 on purpose.
- every other case: 0. No 00203 baseline was captured, so "none new" means "none not explained by my own fake inputs".
- The one stubbed POST on every page load is /log-error with action "boot" (telemetry beacon, not an error).

Identity paths the doer marked closed and NOT driven here: Login (needs credentials), MagicLink (needs a real token),
FindProfile navbar dialog (the page variant was driven), UploadVideo /challenges/:id/upload (pre-existing setItem,
unchanged), Home to-do PromptList (needs an existing userId), the "Not me" action (doer covered it locally, not on prod).

## C. C2 wording
- Live page text at both widths and on t30g: rules line "... +25 extra for each lift type where nobody logs more than you
  that week, up to +100; any mix counts toward the quota." and hero note "+25 extra for each lift type where nobody logs
  more than you that week, locked in when the week ends on Sunday." "Most of a lift type in a week" count 0 in every case.
- Bundle (python count over bundle-after/, 83 files; bundle-after/index.html = live index; live metric-DhnGFCo6.js re-fetched,
  byte-identical): old sentence 0, new clause 1 (metric-DhnGFCo6.js). Canaries: "Not logged yet" 1, you-row-unknown 1;
  the old sentence itself is 1 in bundle-before/ (metric-EKQEc23D.js), so the count could have matched.

## D. C3 (engine NOT deployed)
Production still counts 12 on his squat (A above; bowling-service-00053-fxm, image situp-13b49b5 unchanged). Why
(notes-engine.md): the fix (73852de on fix/squat-rep-count, gives 10 offline) was not deployed because the contract's
regression gate needs >= 3 labelled squat clips and none exist (labelled set 0), so it is a Decision for Tom. 12 vs 10
does not change his points: he is over the 125 cap (175 this week, 375 total, rank 1) and leads Squat with 12 or 10.

## E. APK
`gsutil ls -l`: gs://jtr-lift-u-4ever-cool-bucket/apk/tomsgym-debug-20261113-213836.apk, 4815376 B, 2026-11-14T02:38:38Z.
`curl -sI https://my-python-backend-quyiiugyoq-ue.a.run.app/s/oeg31K`: HTTP/2 302 to a 7-day signed URL for that object.
Not installed on any phone or emulator by me.

## Not covered
- The reporter's real device (iPhone Chrome, CriOS 157) and browser were never touched; his storage state there is unknown.
- Headless desktop Chromium only, no WebKit / iOS; no real upload, sign-in or email; the APK WebView.
- Analysis-ready email links and shared /s/ links still do not set identity (open gap by design, needs a backend marker).

## Addendum: the stubbed finalize response
4b stubbed /upload/finalize, so it does not observe prod returning user_id. Evidence it does, by dating only:
`'user_id': str(resolved_user_id)` was added in 62c851c (2026-06-06) and is in upload_routes.py at 5ef44cb (count 1);
backend revision my-python-backend-00196-mtt was created 2026-11-07T16:10Z (no backend/ diff since 5ef44cb).
I did not tie the image digest (sha256:b632aba1...) to a commit, and no real finalize response was observed.
