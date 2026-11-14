# QA notes: commits 5ef44cb..ab3c2ee (C1, C2), 2026-11-13

Scope: frontend only (589dfb3, ea97f61, 8d4591a, ab3c2ee). Engine (C3) not assessed by QA. Nothing fixed or committed by QA.
QA spec (ran from frontend/src/__qa_tmp__, dir deleted afterwards): qa-spec.tsx.txt in this dir. It renders HEAD
ChallengeDetail and the baseline ChallengeDetail/YouRow (git show 5ef44cb:<path>, imports rewritten) on live-before.json.

## Results (real jest runs, 17 QA tests)
| id | case | result |
|---|---|---|
| Q1 | live payload, no userId | HEAD: you-row-unknown, "Not logged yet" absent. BASE: you-row "Not logged yet" (bug reproduced at baseline). PASS |
| Q2 | live payload, userId = reporter | podium shows caleb.li.larson 375, ring "147 / 125", no "Not logged yet", no you-row-unknown, **no you-row at all**. The brief expected you-row data-entered="true"; that cannot happen while he is on the podium (tableRows empty). Podium.tsx takes no viewer prop, so nothing marks him as "you" except the ring. Unchanged from baseline. DEVIATION from brief (minor) |
| Q2b | synthetic: 3 rows above him, he is rank 4 | you-row data-entered="true", data-rank="4", text has 375. PASS (synthetic, labelled) |
| Q3 | userId with no row | "Not logged yet". PASS |
| Q4 | userId with processing attempt | HEAD "Analysing your upload…"; BASE "Not logged yet". PASS |
| L1 | legacy reps board, viewer in table | HEAD innerHTML === BASE innerHTML. PASS |
| L2 | legacy reps board, viewer id with no row | identical. PASS |
| L3 | legacy reps board, no userId | CHANGED: BASE = "Not logged yet" button that opens the upload form; HEAD = you-row-unknown link to /find-profile. Intended by C1(b) but it is a behaviour change on non-club boards too, and the anon visitor loses the one-tap upload from that row (upload CTA elsewhere remains). |
| E1 | localStorage.getItem throws at mount | HEAD and BASE both crash on render. Not a regression. |
| E2 | setItem throws after a successful upload (no saved id) | **REGRESSION**. BASE: analysis triggered, no error. HEAD: "Upload failed. Please try again." shown, triggerLiftingAnalysis NOT called, no toast. The new getItem/setItem lines (ChallengeDetail.tsx:241-246) sit inside the upload try, before triggerLiftingAnalysis. Real trigger: QuotaExceededError / old iOS private mode where getItem works but setItem throws. The upload row exists but never analyses, reportUploadError fires falsely, and the user is invited to upload again (duplicate attempt in the live club). |
| E3 | stored userId "undefined" (garbage) | row says "Not logged yet"; an upload as the reporter does not repair it (setItem not called) and the toast says "Logged to <email>'s profile. This device stays on its current profile." The "different userId" branch of C1 is messaged, not closed. minor |
| E4 | stored userId "" | treated as unknown -> you-row-unknown. PASS |
| E5 | Find Profile round trip (stateful localStorage) | board -> tap you-row-unknown -> /find-profile?next=... -> lookup -> "Back to the challenge" -> board; store.userId = reporter, you-row-unknown gone, ring 147 / 125. PASS |
| E6 | next validation | "//x" and "/\x" rejected; "/\t/evil.example" accepted and new URL() parses its host as evil.example (tab stripped). As an <a href> that is an off-site link on middle-click / open-in-new-tab; a normal click goes through pushState. minor |

## Mutation checks (QA-run, script restores from an in-memory copy, sha256 re-read: all 8 "sha ok")
Evidence: scratchpad mut/summary.txt (copied below).
- M1 drop setViewerId -> KILLED (remembers the uploader ...)
- M2 `!storedId && data.user_id` -> `data.user_id` -> KILLED (does not replace a different saved userId)
- M3 `viewerId ?` -> `true ?` (null viewer gets Not logged yet) -> KILLED (5 tests)
- M4 next regex `(?![/\\])` -> `(?![/])` -> **SURVIVED** (FindProfilePage.test.tsx only tests "//evil.example"; "/\evil" open-redirect guard is untested)
- M5 YouRow analysing text removed -> KILLED
- M6 `analysing={false}` -> KILLED (2 tests)
- M7 not-found link ignores next -> KILLED
- M8 cap dropped from scoring note -> KILLED
Before-state "in spirit": M2/M3/M6 are the fix lines removed, and Q1/Q4 BASE runs show the baseline renders "Not logged yet" in exactly the cases the new tests forbid.

## Copy (C2)
Grep canary: "Most of a lift type" matched only metric.test.ts:90 (the negative assertion), so the grep could match; no stale copy in
frontend/src, frontend/e2e, backend/toms_gym, docs/reference, docs/superpowers.
Wording is NOT identical across surfaces (the brief asked identical); it agrees in substance:
- metric.ts:69 "Log more of a lift type than anyone else that week for +25 extra each, up to +100; any mix counts toward the quota."
- ConsistencyHero.tsx:348 "Each type you log more of than anyone else is +25 extra, locked in when the week ends on Sunday."
- docs/reference/100-club.md:16 "+ 25 extra for each type where you log more than anyone else that week, on top of a quota any mix fills"
Nuance: consistency.py:231/238 gives the bonus to everyone tied at the top; "more than anyone else" reads as strict. minor.

## Tests modified (flag)
- ConsistencyHero "says type bonuses are added when the week ends" removed, replaced by "says each led type is an extra +25 ..." (copy change; replacement is a stricter anchored regex).
- ChallengeDetail.consistency.test.tsx: 3 existing anon tests changed `you-row` -> `you-row-unknown` (anonymous visitors, drops Everyone else header x2). Matches the intended C1(b) change (L3 above).
- 12 tests added. None deleted without replacement.

## Gate (after deleting __qa_tmp__; frontend git status shows only pre-existing .env.production and persona-walk.mjs)
- npx tsc --noEmit: rc 0 (root config; checks no files). npx tsc --noEmit -p tsconfig.app.json: rc 2, 43 errors, none in a changed file; QA has no recorded baseline for this config (doer reports 43 pre-existing).
- jest --maxWorkers=4: 110 suites, 798 tests, 798 passed, 0 failed (baseline 786/786). jest-qa.json in this dir.

Not covered: production, the APK, a real browser render (all checks are jsdom), a real upload.
M1 drop setViewerId: KILLED (passed 18, failed 1, suiteErr 0) remembers the uploader from the inline form's response when this browser had no userId
   restored src/pages/ChallengeDetail.tsx: sha ok
M2 overwrite a different id: KILLED (passed 18, failed 1, suiteErr 0) does not replace a different saved userId with the uploader's
   restored src/pages/ChallengeDetail.tsx: sha ok
M3 null viewer gets Not logged yet: KILLED (passed 14, failed 5, suiteErr 0) shows anonymous visitors the week line and leaders without a ring | on the live board with the reporter's row but no saved userId, asks who he is instead of saying nothing is logged | remembers the uploader from the inline form's response when this browser had no userId | drops the Everyone else header when the podium holds everyone | drops the Everyone else header on a legacy board whose podium holds everyone
   restored src/pages/ChallengeDetail.tsx: sha ok
M4 next regex drops backslash: SURVIVED (passed 5, failed 0, suiteErr 0) 
   restored src/pages/FindProfilePage.tsx: sha ok
M5 YouRow analysing text: KILLED (passed 8, failed 1, suiteErr 0) not-entered variant says the viewer's upload is analysing
   restored src/components/challenge/YouRow.tsx: sha ok
M6 analysing never passed: KILLED (passed 17, failed 2, suiteErr 0) says the upload is analysing for a known viewer with no row and a processing attempt | remembers the uploader from the inline form's response when this browser had no userId
   restored src/pages/ChallengeDetail.tsx: sha ok
M7 not-found ignores next: KILLED (passed 4, failed 1, suiteErr 0) sends someone with no profile back to the board to upload
   restored src/pages/FindProfilePage.tsx: sha ok
M8 cap dropped: KILLED (passed 14, failed 1, suiteErr 0) words the type bonus as an extra per type, not a split of the quota
   restored src/components/challenge/metric.ts: sha ok

## Add-on round (after the advisor review)
- A1 PASS: no saved id, live payload, inline upload whose response carries the reporter's user_id -> setItem("userId", reporter),
  you-row-unknown gone, ring "147 / 125", no "Not logged yet", toast "Analyzing your form automatically...". The null->id flip
  does not raise a rank banner (rankChange(null, s) returns null, rankMemory.ts:39); it writes the rank snapshot.
- A2 RUN: FindProfilePage with next=%2F%09%2Fevil.example renders "Back to the challenge" with href attr "/\t/evil.example",
  which resolves to http://evil.example/ (jsdom). Middle-click / new tab goes off-site. A normal click goes through react-router
  history push; whether its pushState SecurityError fallback (location.assign) also navigates off-site was NOT run: unverified.
- Identity writers marked "already closed": M9 MagicLink setItem removed -> KILLED (2 tests); M10 FindProfilePage setItem removed
  -> KILLED (1 test). UploadVideo.tsx:158 has NO test file at all (no *.test.tsx renders UploadVideo), so that path is unguarded;
  it also overwrites a different saved id unconditionally, unlike the new inline-form policy (pre-existing, inconsistent).
- "No gap" claims: PromptList renders ChallengeVideoRow only when userId is truthy (PromptList.tsx:194, read). No backend file
  builds "/lift/status" (grep over backend *.py/*.html/*.txt; the same pattern matches frontend routes/index.tsx:98, so the grep can match).
  Not verified by QA: GolfUpload, Login, the FindProfile navbar dialog, APK WebView, email links (no test run for these).
- Both mutation rounds restored by sha; source is byte-identical to the state the full jest gate ran on, so jest-qa.json stands.
- __qa_tmp__ deleted again; frontend git status: only pre-existing .env.production and scripts/persona-walk.mjs.
- qa-spec.tsx.txt updated (E2 title renamed to say it asserts the regression; A1, A2 added).
M9 MagicLink drops userId: KILLED (passed 2, failed 2, suiteErr 0) stores userId for a passwordless account and redirects to the profile | calls the consume endpoint exactly once (single-use guard)
   restored src/pages/MagicLink.tsx: sha ok
M10 FindProfilePage drops userId: KILLED (passed 4, failed 1, suiteErr 0) welcomes the person back by name with their last lift, and remembers them
   restored src/pages/FindProfilePage.tsx: sha ok
