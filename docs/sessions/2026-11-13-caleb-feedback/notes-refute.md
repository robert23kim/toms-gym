# Refuter round 1 notes (2026-11-14, finished 03:04Z)

Evidence is in refute/. My scripts are refute/refute.mjs (Playwright) and refute/bundle.py (bundle crawl). It ran in a fresh context with unrouteAll, a function matcher that fulfils every non-GET with a stub, a 1500 ms wait and a 390x844 viewport. The only non-GET was the stubbed POST /log-error. I re-ran the prover's flow script for the stubbed flows (TAG=-refute, 390 only) after reading that it stubs every non-GET and the by-email GET. Nothing signed in and nothing wrote.

## Live data (A1): unchanged
- I called GET /competitions/<club>/leaderboard myself and got 200 with 3996 B. The whole JSON is equal to live-before.json (python `a==b` True): rank, score, this_week.lifts and attempt_count are caleb 1/375/147/14 and Toka 2/350/162.5/14. This check could have failed, because any field change breaks the equality.
- GET /users/<reporter>/lifts returned 200 and equals the gate copy reporter-lifts.json, with 15 lifts. f47a8848 reads squat, total_reps 12, grade D, completed.
- `gsutil ls -l` on lifting/f47a8848.../summary.json gives 33496 B with mtime 2026-11-12T16:56:40Z, which is the original analysis and not a re-analysis.
- I re-fetched the board at 03:04Z, after all my Playwright runs including the stubbed upload flow. refute/lb-refute-end.json still equals live-before.json.
- Not covered: DB rows directly.

## C1 page renders at 390x844 (B1, B2, B3)
- anon: localStorage.length was 0 (no keys, userId null), so the case really had empty storage. you-row-unknown 1, "Not logged yet" 0, text "? / YOU / Find your profile / This device doesn't know who you are yet", href /find-profile?next=%2Fchallenges%2F<club>. The click lands on find-profile and "Who am I?" renders. Console errors 0. Before the fix this rendered "— / YOU / Not logged yet" (before-you-row-anon.txt), so the check discriminates.
- reporter: localStorage held userId = his id. you-row 0, you-row-unknown 0, "Not logged yet" 0, viewer block 1. Console errors 0.
- random uuid: you-row data-entered=false with "— / YOU / Not logged yet". The one console error is the 404 for the fake id's profile.
- My page text is byte-identical to the prover's prove-c1-{anon,reporter,random}-390.txt (diff empty).
- **The reporter case is NOT discriminating.** In the old ChallengeDetail (5ef44cb, lines 882 and 1029), a viewer whose row is on the podium with an empty table gets showTable=false and no YouRow. So with his id stored, the old build also showed no "Not logged yet". B2-identity is true, but it is not evidence of the fix. It does confirm the bug log's inference: his screenshot showing "Not logged yet" means his browser had no matching userId.
- B2-literal: confirmed false. He is on the podium and you-row is 0.

## Flows (B4) and synthetic table, re-run at 390
- synthetic-table: you-row data-entered=true, "4 / caleb.li.larson · You / 147/125 this week / 375pts". The board was stubbed.
- flow-findprofile: storage starts empty and the prompt is shown. The stubbed lookup stores his id. Back on the board: you-row-unknown 0, "Not logged yet" 0, ring 147 / 125.
- flow-inline: signed-url, the GCS PUT (fake-gcs.invalid), finalize and analyze were all stubbed. The toast read "This device now logs as prover@example.invalid. / Not me". userId was stored, and the board then recognised him (ring 147 / 125).
- The code path is real. lib/upload.ts, parallelUpload.ts and resumableUpload.ts all return the finalize res.data. ChallengeDetail.tsx:248-259 stores data.user_id when nothing is stored. The backend finalize line 605 `'user_id': str(resolved_user_id)` comes from 62c851c3 (2026-06-06), which is an ancestor of HEAD and predates backend rev 00196-mtt (2026-11-07). No real finalize response was observed.
- Nit: after the inline flow the URL still carries ?upload=1, so a reload probably re-opens the form. This is not verified.

## C2 bundle (with canaries)
- I crawled the live index and its JS imports: 82 files, all 200 and non-empty, build-timestamp 1794623705. This matches bundle-after/, which holds the same 82 JS files plus index.html (83).
- Canaries: "Not logged yet" 1 and consistency-hero 1, so the fetch worked. you-row-unknown 1 (ChallengeDetail-wRBSQ4v6.js), new clause 1 (metric-DhnGFCo6.js), old sentence "Most of a lift type in a week" 0, old lock line "Type bonuses (+25 each) are added" 0.
- The old sentence appears once in the local bundle-before/, so the count could have matched.
- First-reader test of "+25 extra for each lift type where nobody logs more than you that week, up to +100; any mix counts toward the quota.": I do not think it can be read as "spread your 100 evenly over 4 lifts". "extra" plus "any mix counts toward the quota" rules that out. The second live line ("+25 extra for each lift type where nobody logs more than you that week, locked in when the week ends on Sunday.") lacks the "any mix" clause, but it sits under the per-type leader list and still says "extra". I judged both lines.
- Minor copy and logic mismatch: consistency.py:231-238 says "zero never wins" (a type only has leaders when top > 0). Read literally, "nobody logs more than you" is also true when nobody, including you, logged that type. Low severity.

## C3 / engine
bowling-service serves 100% of traffic on bowling-service-00053-fxm, image gcr.io/toms-gym/bowling-service:situp-13b49b5, created 2026-09-13. The latest three revisions are all from 09-13, so no engine deploy happened. Prod still counts 12, as the A1 reads above show.

## APK
`gsutil ls -l` shows apk/tomsgym-debug-20261113-213836.apk at 4815376 B, dated 2026-11-14T02:38:38Z. `curl -sI /s/oeg31K` returns HTTP/2 302 to a storage.googleapis.com signed URL for that object. I did not install it.

## Not covered (by me either)
- No WebKit, iOS or APK WebView render.
- The reporter's real device.
- "Analysing your upload…" in prod.
- The navbar FindProfile dialog.
- 1280 width: I took it from the prover. I re-ran only 390.
