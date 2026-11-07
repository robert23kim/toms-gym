# 2026-11-07: owner-only Bowl/Golf and the past-challenges fold

## Asked
Hide the bowling and golf surfaces unless the signed-in account is toka778@gmail.com, to cut clutter; and hide old challenges by default so only active ones bubble up.

## Decisions (builder's, stated as assumptions)
- Hide, not block: every `/bowl`, `/golf`, `/bowling/*`, `/golf/*` route still opens by URL. Anyone who sets `localStorage.userId` to the owner's id sees everything; the email is a literal in the bundle.
- Identity: JWT user email when signed in; otherwise one public `GET /users/<userId>/profile` read, cached per userId in localStorage `ownerCheck`. Unknown reads as hidden, so the owner gets a one-time pop-in per device and strangers never see a flash.
- Profile Bowl/Golf tabs hide for every non-owner viewer, even on profiles that have bowling rows.
- The anonymous demo loop shows only the plank scene (the bowling and golf scenes said "ball tracking" and "scorecard → handicap").
- Upcoming challenges stay visible ("Coming up"); only ended ones fold behind "Past challenges (N)".
- Hall of Champions, lift-history streak kinds and the golf avatar art are untouched.

## Shipped
Branch `feat/100-club`: b2de568 (owner gating), 9d3781b (past-challenges fold), bed7ed3 (bowling/golf challenges hidden from non-owners, found in the Chrome walk: the ended "Bowling" competition sat in the past list), plus docs. Frontend revision `my-frontend-00201-5vm` (00200 carried the first two commits). Reference: `docs/reference/finch-shell.md` (2026-11-07 section).
Gates: `npx tsc --noEmit -p tsconfig.app.json` 43 errors, all pre-existing, none in changed files; jest `--maxWorkers=4` 109 suites / 766 tests, 0 failed. 15 mutants (owner email, each gated surface, cache, dedup, auth email, past default, the challenge filter at its helper and both callers) all killed; files restored byte-identical.
APK: built with stamp 1794075479, entry chunk carries `ownerCheck` and the bowling/golf category set; published as `gs://jtr-lift-u-4ever-cool-bucket/apk/tomsgym-debug-20261107-131820.apk` (4,750,277 B), short link `https://my-python-backend-quyiiugyoq-ue.a.run.app/s/jciS2g` (302, download byte-identical to the local APK; expires 2026-11-14). Supersedes `/s/VrMWQb` (built before bed7ed3) and `/s/LSOd2h` from the week-1 workflow; neither was installed.

## Verified in production
- Bundle canary: the served entry chunk of 00201-5vm contains `ownerCheck` (1 hit) and `"bowling","golf"` (1 hit), with `vite:preloadError` as the fetch control (2 hits).
- `docs/sessions/2026-11-07-declutter/prove-owner.mjs` (scripted Playwright, fresh contexts, every non-GET answered locally with 204 so nothing wrote to prod): 58/58 checks at 1280x800 and 390x844 (`innerWidth` asserted) for three sessions.
  - Anonymous: nav has `/lift` but no `/bowl`/`/golf`; 4 bottom tabs; pitch "AI analysis of your lift — in minutes."; no "ball tracking"/"scorecard" demo scene; no bowling/golf to-do rows; `/upload` offers only `/lift/upload`; `/challenges` shows "Open now" with The 100 Club, "Past challenges (5)" collapsed (`aria-expanded=false`), the click reveals 5 rows labelled Results, none of them "Bowling".
  - Owner (`localStorage.userId` = 7844e26d…): one `GET /users/7844e26d…/profile` observed; nav has `/bowl` and `/golf`; 6 bottom tabs; home to-do rows "Snap tonight's bowling recap" and "Snap a golf scorecard" at 390; profile tabs Lift/Bowl/Golf; `/upload` offers all three; "Past challenges (6)" including Bowling.
  - Other athlete (caleb's id): nav and tabs as anonymous, no bowling/golf rows, profile shows only the Lift tab.
  - The only write each page attempted was the app's boot telemetry `POST /log-error`, intercepted.
- Claude in Chrome (Tom's real browser, anonymous on this origin): `/challenges` renders "OPEN NOW · The 100 Club" and the collapsed "PAST CHALLENGES (6)" line; expanding it listed six ended challenges including "Bowling", which is what prompted bed7ed3.

## Not covered
- Nothing was installed or opened on a phone; the APK proof is the short-link download and the bundled index.html stamp.
- A signed-in JWT session (`/auth/user` path) was proven in jsdom only; prod sessions in this proof were passwordless (`localStorage.userId`).
- The owner pop-in on first load was not timed.

## Follow-up: sticky upload button hidden under the tab bar (2026-11-07, 110d052)

Tom's phone screenshot showed only a sliver of the blue "Log a lift" button above the bottom tabs. Both were `fixed bottom-0` and the tab bar has the higher z-index. Fix: the CTA wrapper gets `.above-tab-bar` (`bottom: calc(4rem + env(safe-area-inset-bottom))`, in `index.css`) and the page's phone padding grows to `pb-44`. Guard: `ChallengeDetail.consistency.test.tsx` "pins the phone upload button above the bottom tab bar" (mutant `bottom-0` killed, file restored byte-identical).

Prod proof `docs/sessions/2026-11-07-declutter/prove-cta.mjs` (output in `prove-cta.txt`): run against `my-frontend-00201-5vm` first as a negative control it failed 4 of 14 (button bottom 820 px vs tab top 779 px, tap at the button centre landed on the tab bar); against `my-frontend-00202-4gg` it passed 14 of 14 for anonymous and owner sessions at 390x844, with the button ending at 768 px. Only boot telemetry tried to write and was answered locally.

APK rebuilt with stamp 1794081802 and published as `gs://jtr-lift-u-4ever-cool-bucket/apk/tomsgym-debug-20261107-150349.apk`, short link `/s/wCz0Hq` (download byte-identical via `cmp`). Supersedes `/s/jciS2g`.

## Follow-up: lift breakdown in the hero (2026-11-07 evening, 35c6eb5)

Tom asked for designs that show each lift behind the score on a phone. Five options were mocked up on
https://claude.ai/artifact/RxeQSFX7riSkVfkgoDhzno; he chose the recommended A + C with D behind a tap.
Shipped: segmented quota ring with a legend per lift type, a points receipt (banked lifts, quota bonus,
pending type leads, projection, overall), and the viewer's uploads of the live week behind a 44 px toggle,
with lifts taken from the analysis results the page already fetches. Details and helper names in
`docs/reference/100-club.md` (hero breakdown section).

Gates: jest 786 green (19 new cases), tsc unchanged at the 43 pre-existing errors, 12 of 12 mutants killed with
byte-identical restores.

Prod proof `docs/sessions/2026-11-07-declutter/prove-breakdown.mjs` (output `prove-breakdown.txt`, screenshots
`prove-breakdown-{owner,other}.png`): reads the live board and lifts and checks every rendered number against
them. Negative control against `my-frontend-00202-4gg` failed on the first segment check. Against
`my-frontend-00203-7gg` it passed 57 of 57 for the owner, caleb and anonymous at 390x844; the per-upload lifts
summed exactly to the board's week total for both athletes (100 and 107.5, caleb with two plank uploads), so
the per-attempt plank floor matched the backend on this data. Only boot telemetry tried to write and was
answered locally. Not covered: Tom's real signed-in session, a real device, desktop width, a failed or
still-analysing upload in prod.

APK rebuilt with stamp 1794082851 (the toggle is in its `ConsistencyResult-*.js` chunk, control marker
`vite:preloadError` present) and published as `gs://jtr-lift-u-4ever-cool-bucket/apk/tomsgym-debug-20261107-152132.apk, short link /s/7uv33h (4,911,153 B, download byte-identical via cmp, expires 2026-11-14)`. Supersedes `/s/wCz0Hq`.
