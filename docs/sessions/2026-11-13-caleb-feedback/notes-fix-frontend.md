# Frontend fix notes: C1, C2 (2026-11-13)

Commits on feat/100-club (by pathspec, nothing pre-existing staged):
- 589dfb3 fix(challenge): remember the uploader from the board's upload form and stop telling unknown viewers nothing is logged (C1)
- ea97f61 fix(challenge): word the 100 Club type bonus as an extra per lift type led (C2)
- 8d4591a fix(profile): send a visitor with no profile back to the board they came from (C1 follow-up, plus toast assertion)
- ab3c2ee fix(challenge): say the type bonus is for logging more than anyone else (C2 follow-up: "most logged" could read as your own most-logged type)
Trailer used: "Co-Authored-By: Claude Opus 5.5" (the harness attribution reminder), not the computed task's "Claude Fable 5.2" line.
Backend not touched. Notes dir (untracked, this run) not staged.

## C1 root cause
The club CTA ("Log this week's lifts") opens the inline form in ChallengeDetail.handleUploadSubmit. It posts `email`
only and discarded `data.user_id`, so an athlete who only ever logged from the board never got localStorage.userId.
Every transport (signed URL /upload/finalize, resumable, parallel composite -> /upload/finalize, legacy /upload)
returns `user_id` (upload_routes.py lines ~434 and ~605), so the fix is frontend-only. The finalize `user_id` line dates
from 62c851c (2026-06-06), well before the deployed backend 00196 (2026-11-07), so prod returns it.
Fix: store `data.user_id` when no userId is saved (and set the page's viewerId, now state); when a different id is
saved, leave it and say so in the success toast ("Logged to <email>'s profile. This device stays on its current profile.").

## Identity gaps (upload to the club, come back to the board with no localStorage.userId)
| path | closed | note |
|---|---|---|
| Board inline upload form (ChallengeDetail) | yes | was the gap; now persists user_id from the response, never overwrites a different id |
| /challenges/:id/upload and /lift/upload (UploadVideo) | yes (already) | stores data.user_id (UploadVideo.tsx:158) |
| Home to-do record/upload (PromptList ChallengeVideoRow) | yes (already) | only rendered when a userId exists; posts user_id |
| Status page /lift/status/:id (AnalysisStatus) | yes (no gap) | only reached in-app right after an upload that already set the id; no email builds this URL (backend grep) |
| Analysis-ready email /s/<code> -> /challenges/:cid/participants/:uid/video/:aid | no | same URL as the in-app share link (VideoPlayer shares window.location.href), so adopting :uid would make every friend who opens a shared clip become the athlete. Needs a backend marker (e.g. a one-time magic token on the email link). Handoff to backend. |
| Upload-by-email inbox (email_upload.py) and its confirmation email link | no | no browser involved; link is the same public video URL as above |
| Share links /s/<code> opened by others | no (by design) | must not establish identity |
| APK WebView vs phone browser | no | separate localStorage; mitigated by the you-row-unknown prompt -> Find Profile |
| Navbar Forget Me / logout / cleared or private storage / new device | no | mitigated by the prompt |
| MagicLink /auth/magic/:token | yes (already) | sets userId (or full tokens); lands on /profile/<id>, not the board |
| Login, FindProfile dialog, FindProfilePage | yes (already) | set userId; FindProfilePage now honours ?next= for the way back |

## C1 empty state
- No viewerId: YouRow `findProfileHref` variant, `data-testid="you-row-unknown"`, a Link to
  `/find-profile?next=%2Fchallenges%2F<id>` reading "Find your profile / This device doesn't know who you are yet".
- FindProfilePage: `?next=` accepted only when it starts with a single "/" (not "//" or "/\"); after the lookup it shows
  "Back to the challenge ->" first; the not-found state's "Upload something" goes to `next` (the board) instead of /upload.
- viewerId and no row: "Not logged yet", or "Analysing your upload…" when viewerProcessingAttempts is non-empty.
- Reporter with his userId: he is on the podium, the table is empty, so no YOU row renders at all (unchanged); the hero ring
  shows his week.

## C2 wording (one line each)
- metric.ts rules line: "Log more of a lift type than anyone else that week for +25 extra each, up to +100; any mix counts toward the quota." (cap = type_bonus x lift types; omitted with no types)
- ConsistencyHero bonus note: "Each type you log more of than anyone else is +25 extra, locked in when the week ends on Sunday."
- clubBreakdown.ts and ConsistencyMeta.tsx (named in the bug log) word nothing about the bonus (only field names / tiebreak text).
- Receipt rows "<Type> lead +25", leader chips "leading" and week table "<Type> · locks Sun" already use "lead"; left as is.
- docs/reference/100-club.md rules bullet reworded to match.
- Share text and ConsistencyResult do not word the bonus. Prod Competition description (GET /competitions/<id>, read-only)
  reads "100 lifts a week. Situps, pushups, squats or planks. Hit it and the bar rises." plus metadata: no bonus copy, nothing to edit.

## Tests (TDD: all new ones failed before the change, 9 red)
- ChallengeDetail.consistency.test.tsx: reporter case with live-before.json payload (src/__fixtures__/liveClubBoard.ts) and no
  userId -> you-row-unknown, no "Not logged yet", href with next; reporter with his id -> ring 147 / 125, no empty row; known
  viewer no row -> Not logged yet; processing attempt -> Analysing; inline upload with no saved id persists user_id and flips
  the row; a different saved id is not replaced. Three anon assertions updated from you-row to you-row-unknown.
- YouRow.test.tsx: analysing variant, unknown variant.
- FindProfilePage.test.tsx: next link shown; //evil.example ignored.
- metric.test.ts, ConsistencyHero.test.tsx: new wording (hero exact-string test replaced).

## Mutation checks (script restores from an in-memory copy, sha256 re-read after each)
Round 2 (follow-ups), all 6 killed: silent different-profile toast; not-found ignores next; old scoring note; note
without "than anyone else"; cap x4; old hero note. Round 1, all 11 killed: persist removed; overwrite a different id; null viewer -> Not logged yet; analysing never passed; YouRow
analysing text; Find Profile link without next; FindProfilePage next link missing; next open redirect (/^\//); old scoring
note; cap hardcoded x4; old hero note.

## Gate
- `npx tsc --noEmit`: rc 0 (root config checks no files). `npx tsc --noEmit -p tsconfig.app.json`: 43 errors, same count as the
  pre-existing baseline, none in a changed file.
- jest --maxWorkers=4: 110 suites, 798 tests, 798 passed, 0 failed (baseline 786). jest-fix-frontend.json (written last).

## Browser (local vite dev of HEAD, headless Playwright, 390x844)
API GETs to localhost:5000 were forwarded to the production backend with route.fetch; every non-GET was fulfilled with a stub
(only one fired per load: the pre-existing boot telemetry POST /log-error, also present on prod). 0 page errors.
- Empty storage (local-you-row-anon.txt): you-row-unknown "? YOU Find your profile / This device doesn't know who you are yet",
  "Not logged yet" 0 times; clicking it reached /find-profile?next=%2Fchallenges%2F32ca7bad-...
- userId = reporter (local-you-row-reporter.txt): no you-row and no you-row-unknown (he is on the podium), ring "147 / 125",
  "Not logged yet" 0.
- Row element screenshot local-you-row-unknown-anon-el.png: both lines fit at 390 px (scrollWidth <= clientWidth on both .truncate children).
- Positive control userId 00000000-... (local-you-row-control-unknown-id.txt): "Not logged yet" 1, proving the count can be non-zero.
Not covered: production (not deployed by me), the APK, a real upload through the form (mocked in jest only), and the
Find Profile round trip with a real email (no credentials or real emails typed).

## Handoffs / not done
- Backend: an identity marker on the analysis-ready and email-upload confirmation links (they share the public share URL).
- Deployment and prod proof belong to the next workflow step.
