# Refuter round 2 notes (2026-11-14 03:17-03:20Z), production, read-only

Evidence: refute2/. Scripts: refute2/scripts/r2.mjs (Playwright), refute2/scripts/bundle.py (bundle crawl). Every
browser case: fresh context, ctx.unrouteAll + page.unrouteAll, FUNCTION matcher fulfilling every non-GET with a stub,
1500 ms wait + networkidle + 500 ms, viewport 390x844 (innerWidth asserted 390). The only non-GET seen in every case
was POST /log-error (stubbed). Nothing signed in, nothing typed, nothing wrote. git: only the two pre-existing
modifications, 0 staged, HEAD 668529b.

## A. Live rows: unchanged (live_rows_unchanged = true)
- 03:17Z and 03:19Z (after all browser runs): GET leaderboard 200 / 3996 B, `cmp` byte-equal to live-before.json
  (python == True). caleb.li.larson 1/375/147/14, Toka 2/350/162.5/14. Could fail: any field change breaks byte-equality.
- GET /users/<reporter>/lifts: byte-equal to reporter-lifts.json, 15 lifts; f47a8848 squat, total_reps 12, grade D, completed.
- gsutil: f47a8848 summary.json 33496 B, mtime 2026-11-12T16:56:40Z (no re-analysis). Not covered: DB rows.

## B. C1 renders at 390x844 (results in run-chromium.log; *.txt / *.png per case)
| case | storage | you-row | you-row-unknown | "Not logged yet" |
|---|---|---|---|---|
| anon | localStorage.length 0, userId null | 0 | 1, href /find-profile?next=%2Fchallenges%2F<club> | 0 |
| reporter | userId = his id (3 keys) | 0 | 0 | 0 |
| random uuid | userId = fresh uuid | 1, data-entered="false" | 0 | 1 |
- Page text is byte-identical to prove-c1-{anon,reporter,random}-390.txt (diff empty, all three).
- anon discriminates: old build text (before-you-row-anon.txt) was "— / YOU / Not logged yet"; now "? / YOU / Find your
  profile / This device doesn't know who you are yet". Direct load of the href (empty storage) renders "Who am I?", 0
  console errors. Minor copy: that page says "we'll take you straight to your profile" while next= returns to the board.
- reporter case does NOT discriminate (re-checked myself): `git show 5ef44cb:frontend/src/pages/ChallengeDetail.tsx`
  line 882 `showTable = tableRows.length > 0 || !viewerEntered` and line 1029 `{!viewerEntered && <YouRow entered={false}/>}`:
  podium viewer + empty table -> no YouRow on the old build either. B2 as worded is false (prover says so too).
- random: 1 console 404 = profile of my fake id.
- WebKit: NOT run (Playwright webkit-2248 executable not installed). Chromium only; Caleb is on iPhone Chrome (WebKit).
- B4 flows: not re-driven this round; round-1 refuter re-ran them at 390. I did not observe a real finalize response.

## P2-2 confirmed: ?upload=1 re-opens the form on reload
- Fresh load of /challenges/<club>?upload=1: input[type=file] count 2 (anon and reporter id) vs 0 on the plain board.
  After the inline upload flow the URL keeps ?upload=1 (prover), so a reload re-opens the upload form. Minor.

## C. C2 copy: bundle and page
- Crawled live index (200, 1430 B, byte-equal to bundle-after-2/index.html, build-timestamp 1794625712) and 81 JS files,
  0 empty; my file list equals bundle-after-2 (one regex miss on mp4box.all-*.js, unrelated library).
- Canaries: "Not logged yet" 1, consistency-hero 1, you-row-unknown 1 (ChallengeDetail-CL-vy90B.js) -> the fetch worked.
- Old sentence "Most of a lift type in a week" 0 (bundle-before/metric-EKQEc23D.js has 1, so the count could match);
  round-1 clause "nobody logs more than you" 0; old lock line "Type bonuses (+25 each) are added" 0; new clause
  "where nobody logs more" 1 (metric-Dd4wUX1y.js). Page text: old 0, new 2, in every case.
- P2-1 confirmed: `git show HEAD:docs/reference/100-club.md` line 16 still reads "25 extra for each lift type where
  nobody logs more than you that week": disagrees with the app copy C2 asked to align.
- First-reader reading (judgement, no user test): "+25 extra for each lift type you log that week where nobody logs
  more, up to +100; any mix counts toward the quota."
  * "spread your 100 evenly as a requirement": ruled out by "extra" and "any mix counts toward the quota".
  * Still possible: the first ten words, "+25 extra for each lift type you log that week", read as a per-type
    participation bonus (log all four types, get +100). The comparison is only in the trailing "where nobody logs
    more" with no "than you", and the sentence never says lead/most/anyone else, while the hero shows "LEADING" and the
    receipt "Squat lead". That is close to Caleb's misreading (spread over the 4 lifts) and short of C2's "unmistakably a
    bonus for doing more of one lift type than anyone else". Logged as a low-severity frontend issue.

## D. C3: engine not deployed (held)
- bowling-service: 100 % on bowling-service-00053-fxm, image gcr.io/toms-gym/bowling-service:situp-13b49b5; newest
  three revisions all 2026-09-13. Prod still reads 12 (A). Engine fix result itself taken from notes-engine.md.

## E. APK (held, install not covered)
- gsutil: apk/tomsgym-debug-20261113-221223.apk 4815373 B 2026-11-14T03:12:24Z. curl -sI backend /s/oVzVrt: HTTP/2 302
  to the signed URL of that object. I did not download or install it; asset contents taken from the prover.

## X. Reporter device (held)
- Every one of my renders was headless desktop Chromium with stubbed writes. His device/browser state is unknown.

## Addendum (03:20-03:22Z): supersedes the "not re-driven" and "taken from the prover" lines above
- B4 re-driven on this build (ChallengeDetail-CL-vy90B.js) at 390: I read all of prove-c1.mjs first. Every non-GET is
  fulfilled, by-email and the fake attempt's GETs are stubbed, and all other GETs pass through. I ran
  `TAG=-refute2 CASES=flow-findprofile,flow-inline WIDTHS=390x844 OUTDIR=refute2 LIVE=refute2/lb-start.json`, so the
  prover's files were not overwritten. Results are in refute2/prove-c1-results-refute2.json.
  * flow-findprofile: start userId null, you-row-unknown 1, "Who am I?" loaded, by-email stubbed 200. End: userId =
    reporter, you-row-unknown 0, "Not logged yet" 0, ring 147 / 125. The only non-GET was POST /log-error (stubbed).
  * flow-inline: start userId null. Stubbed: POST signed-url, PUT fake-gcs.invalid, POST finalize, POST analyze, POST
    /log-error. Toast "This device now logs as prover@example.invalid. / Not me". End: userId = reporter,
    you-row-unknown 0, "Not logged yet" 0, ring 147 / 125, URL still ?upload=1. pageerrors 0; the one console 404 is
    the stubbed by-email response.
  * This does not show prod's real finalize returning user_id, because finalize was stubbed.
- 1280x800 (r2.mjs W=1280): anon storage length 0, you-row-unknown 1, "Not logged yet" 0; reporter you-row 0,
  "Not logged yet" 0; random data-entered="false", "Not logged yet" 1. The page text of all three is byte-identical
  to prove-c1-*-1280.txt.
- APK: downloaded through backend /s/oVzVrt to refute2/apk-dl/app.apk (200, 4815373 B, equal to the gsutil size).
  Its index has build-timestamp 1794625920. Counts: new clause 1 (metric-Dd4wUX1y.js), old sentence 0, round-1
  clause 0, you-row-unknown 1 and canary "Not logged yet" 1 (both ChallengeDetail-Dr99dmtJ.js). Not installed.
- Final GETs at 03:22Z, after every run: the leaderboard and the reporter's lifts are both byte-equal to the gate copies.
- B1 "prompt leads to": the href was read and loaded directly by r2.mjs, and the flows above clicked it
  (findProfileLoaded true).
- X: rests on the stubbed lists in prove2/prove-c1-results.json, which the prover's script writes, plus the unchanged
  live GETs. The prover's own conduct beyond that is not independently observable.
