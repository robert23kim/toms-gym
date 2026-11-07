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
