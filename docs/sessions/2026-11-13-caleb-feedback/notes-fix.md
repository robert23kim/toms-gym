# Fix round notes (review + QA findings), 2026-11-13

Decision needed (Tom), engine does not deploy: E1 is open (no labelled squat clips besides the reporter's, so the C3
regression check cannot fail). E1, E2, E3 deferred; squat-engine not touched in this round.

## Commits (feat/100-club, by pathspec, trailer "Co-Authored-By: Claude Opus 5.5" as in the earlier commits of this run,
per the harness attribution reminder, not the computed task's "Claude Fable 5.2" line)
- be2b683 fix(challenge): never fail a finished board upload on a storage error (QA-1, QA-5, QA-8)
- 26fc964 fix(challenge): say when the board form makes this device log as the uploader (R5)
- 808029b fix(profile): only take a challenge board as Find Profile's way back (QA-4, R7)
- 5c0cfc1 fix(challenge): open the upload form when Find Profile sends a new visitor back to upload (R1, QA-3)
- ef3ce94 fix(challenge): one bonus clause that counts ties, capped by the lift types that score (R2, QA-7, R9, R3)
- 50fb8cc fix(test): anonymise the reporter in the live 100 Club board fixture (R8, frontend half)

## Outcomes
- QA-1 fixed: setItem has its own try/catch; a storage failure can no longer reach the upload catch. Test: setItem throws
  QuotaExceededError -> triggerLiftingAnalysis('new-1') called, toast shown, no "Upload failed", reportUploadError not called.
- QA-5 fixed (partly): readStoredUserId() treats "", "undefined", "null" as no id (unknown-viewer row, and the inline upload adopts
  the response id). A stored real id that no longer resolves to a user is still kept (needs a network check; not done).
- QA-8 fixed: the same helper catches a throwing getItem; used in the viewerId initializer, fetchData and join.
- R5 fixed: adoption toast "Analyzing your form automatically. This device now logs as <email>." with a "Not me"
  ToastAction (10 s) that removes userId only if it still equals the adopted id, and resets viewerId (board returns to the
  unknown prompt). Wording only when the write succeeded. Not changed: UploadVideo's pre-existing adoption.
- R1 / QA-3 fixed, Decision needed (Tom): kept on every board; isConsistency-only is a one-line change. Rationale: the unknown-viewer row stays on every board. C1(b) is unconditional, and the baseline
  "Not logged yet" was equally false for an anonymous viewer on a legacy board. The loop is closed: not-found
  "Upload something" -> /challenges/<id>?upload=1, and the board opens + scrolls to the form once the challenge loads.
  The row itself no longer uploads in one tap; header and sticky CTAs still do. Tom can still choose isConsistency-only.
- QA-4 / R7 fixed: next must match ^/challenges/[A-Za-z0-9-]+$, so the "Back to the challenge" text is always true and
  //, backslash, tab, /profile/u1, dot segments and absolute URLs are rejected (6 test cases).
- R2 / QA-7 / R9 fixed: consistency.py gives every athlete tied at the top the full type_bonus. One shared clause
  (metric.ts typeBonusClause) on both surfaces: "+25 extra for each lift type where nobody logs more than you that week",
  then ", up to +100; any mix counts toward the quota." (rules line) / ", locked in when the week ends on Sunday." (hero).
  100-club.md says the same and "Everyone tied at the top gets the full 25, and zero never wins."
  Stale-copy grep ("than anyone else|Each type you" over frontend/src, e2e, docs/reference, backend/toms_gym,
  docs/superpowers): 0 hits; canary "nobody logs more than you" hits 4 files, so the grep can match.
- R3 fixed: cap counts liftTypes in Situp/Pushup/Squat/Plank (mirrors COUNTED_LIFT_TYPES); test with "Bench" added.
- R8 open half first: the engine pose fixture (squat_walk_in_out_real_keypoints.npz) is Tom's call, and his id/name sit
  in unpushed history (589dfb3). Frontend half fixed: liveClubBoard.ts now has placeholder UUIDs (his user id and both
  production attempt ids), "athlete.one" and storage.example clip URLs; a UUID grep leaves only the club id and Tom's own id. His id/name remain in the history of 589dfb3 (branch has no upstream, nothing pushed, so a
  squash before pushing would drop them). squat-engine's squat_walk_in_out_real_keypoints.npz (his pose) is Tom's call.
- R6 fixed with evidence (read-only Cloud Run logs, 2026-11-12 16:50-16:56Z): all three of his uploads came from an
  iPhone Chrome browser (CriOS/157, iOS 27.2), not the Android APK, from origin https://t30g.com (referer).
  All three finalize lines (16:50 Pushup, 16:53 Situp, 16:55 Squat f47a8848) logged user_id=None with his email.
  UploadVideo stores the id after an upload and then posts user_id, so it is ruled out for at least the 2nd and 3rd;
  the board's inline form always posts email only. Within 0.4 s of the squat finalize the backend saw POST
  /lifting/analyze/<attempt>, GET /competitions/<club>/lifts and a /lifting/result/* burst; those lines carry no client
  identity, so that part is only consistent with ChallengeDetail's post-upload refresh, not proof.
  Conclusion: consistent with the inline-form gap 589dfb3 closed. New gap the frontend cannot close: t30g.com and the
  run.app URL are separate origins with separate localStorage (an id saved on one is absent on the other); mitigated by
  the you-row-unknown prompt.
- R4 deferred (minor): viewerId frozen at mount; every identity-clearing path reloads; the new "Not me" path updates it
  through setViewerId.
- QA-2 refuted as a defect: unchanged from baseline; a podium viewer gets no you-row because the table is empty. For the
  prod proof assert ring "147 / 125" and that you-row and you-row-unknown are both absent. Podium "you" marker = product call.
- QA-6 deferred (minor), overwrite half refuted: UploadVideo reads userId right before posting and sends user_id when one
  is stored (UploadVideo.tsx:130,148), so the response echoes that id; it cannot replace a different id. The missing
  UploadVideo test needs a new page harness; left for a follow-up.
- E1 deferred: Decision needed (Tom). Collect >=3 labelled squat clips (side-on, walk in/out, paused, handheld side-on for
  E2), re-run before/after, then deploy from a clean checkout. E2, E3 deferred with it (E3 is small: apply
  drop_walking_strides to both view candidates before the "more reps wins" comparison).

## Mutation checks (restore from in-memory copy, sha256 re-read: all "sha ok"; all 17 KILLED)
U1a setItem unguarded; U1b garbage strings kept; U1c getItem throw uncaught; U2a silent adoption; U2b no Not me;
U2c Not me keeps id; U2d Not me keeps viewer; U4a old next guard (3 tests); U4b no end anchor; U4c any char; U3a flag
ignored; U3b form always open (10 tests); U3c not-found drops flag; U5a cap counts every type; U5b/U5c strict wording;
U5d hero drops lock.

## Gates
- npx tsc --noEmit: rc 0 (root config checks no files). -p tsconfig.app.json: rc 2, 43 errors, 0 in a changed file
  (the log names 43 src/ paths, so the file filter could match). Same 43 as the earlier rounds.
- jest --maxWorkers=4: 110 suites, 811 tests, 811 passed, 0 failed (was 798). jest-fix.json, re-run after the last edit
  (the fixture amend).
- Backend not changed; backend gate not run.

## Browser (local vite dev of HEAD at :5199, headless Playwright 390x844, fresh context, unrouteAll, function matcher,
GETs proxied to prod, every non-GET stubbed: 1 stubbed, 0 page errors; /users/by-email stubbed to 404, no real email typed)
render-fix.txt, render-fix-upload-open.png:
1 plain anon visit: you-row-unknown 1, "Not logged yet" 0, form email inputs 0; both new bonus lines render as above.
2 tap row -> /find-profile?next=%2Fchallenges%2F<club>; not-found "Upload something" -> /challenges/<club>?upload=1.
3 click it -> board with the form open (form email inputs 1).
4 next=/<tab>/evil.example -> "Upload something" falls back to /upload.
5 adoption toast (render-fix-toast.txt / .png; signed-url, GCS PUT, finalize and analyze all stubbed, fake user id):
  "Upload Successful! / Analyzing your form automatically. This device now logs as nobody@example.invalid. / Not me";
  userId set to the fake id, you-row-unknown 0; after tapping Not me: userId null, you-row-unknown 1. 5 non-GETs stubbed,
  0 page errors. Toaster (components/ui/toaster.tsx, mounted in App.tsx:55) renders {action}.
Not covered: production (not deployed in this step), the APK, a real upload; a known viewer at HEAD (reporter id, other
id) is covered in jsdom only this round (the first round's local-render.mjs covered it before these edits).

## Handoffs
- Deploy + prod proof: next workflow step (frontend only). Engine: none until E1 is decided.
- Backend (from the earlier round): identity marker on the analysis-ready / email-upload links.
