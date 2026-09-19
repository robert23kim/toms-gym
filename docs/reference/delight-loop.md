<!-- Moved verbatim from CLAUDE.md on 2026-09-19; CLAUDE.md keeps a pointer. -->
# Delight Loop (started 2026-08-29)

Recurring product-quality loop, one folder per tick under `docs/delight/<date>-iteration-NN/`:
personas (P1 Priya first-timer · P2 Marcus bowler · P3 Dana golfer · P4 Tom regular · P5 Sam
lost-session) → Playwright walk of production at 390×844 with per-route metrics (height, CTA
count, horizontal overflow, console errors) → idea list → critical review with an explicit
**clutter / duplicate-information** lens → top 3 shipped → verified in prod → bug log (every
bug seen, fixed or not) + retro. Iteration 01 shipped the profile Lift-tab de-clutter
(6941→2012px), the "See your result" deep-link from `/lift/status` (backend `/lifting/result`
now returns `user_id`/`competition_id`), the returning-user home (no pitch/demo when
`localStorage.userId` exists) and the `/challenges` pill-wrap fix. Start the next tick from the
previous doc's bug log. **Rule since iteration 02: each top-3 pick must create a moment
(recognition / progress / surprise) at an emotional peak — friction fixes go to the bug log.**
Iteration 02 shipped the result-page **ladder** (`lib/standing.ts` extended with `below`,
`podiumGap`, `personalBest`, `attemptScore`, `metricForLift`; `components/challenge/ResultLadder.tsx`
— rank, the athlete above/below with gaps, new-best pill, Beat-this for visitors), the waiting-screen
target (`/lift/status/:id?challenge=<id>`), and the completion reveal (number → grade → ladder).
`deriveStanding` also feeds the older challenge-page `StandingCard` — extend it, don't fork it.
Iteration 03 shipped the welcome-back card on `/find-profile` (`lib/welcome.ts`), the Tonight card on
`/bowling/insights/:id?sheet=<id>` (`lib/bowlingNight.ts`, `components/bowling/NightCard.tsx`),
share-with-words (`lib/share.ts::shareResult` + `standingShareText`) and owner-only Re-analyze.
Iteration 04: rank-shift banner on the challenge page (`lib/rankMemory.ts`, localStorage key
`rank:<challenge>:<user>`), streak milestones (`lib/streak.ts::milestoneReached`, key
`streak-milestone:<user>`), round-in-context pill on the golf handicap card (`lib/golfBest.ts`).
Verification recipe for confirm screens: `page.route` with a *function* matcher (globs' `*` does not
cross `/`), patch the GET to enable the button, fulfil the PUT — never let a verification write. Iteration 05 (consolidation): status pill hidden
once analysis exists, bodyweight tips filtered (B5), last-place share copy, "Steadiest plank yet"
(`lib/steadiest.ts`, ladder `extraPill`). Iteration 06 (hygiene): `lib/dates.ts::formatDay` for list
dates, empty stat tiles hidden, "N boards left/right of your last throw" on the throw result
(`lib/throwCompare.ts`, owner-only via the viewer's own results list). Verification gotchas: call
`page.unrouteAll` at the start of every Playwright MCP script (routes persist across runs), and wait
~1s after the first navigation post-deploy (`staleChunk` self-reload kills a racing `evaluate`). Gotchas: `tools/run_ci_tests.sh` needs `PYTHON=venv/bin/python`; get
jest results via `node node_modules/jest/bin/jest.js --json --outputFile=…` (the shell hook
rewrites jest stdout); `jest.setup.js` stubs `localStorage` with `jest.fn()` — mock
`getItem`'s return value, `setItem` is a no-op.
