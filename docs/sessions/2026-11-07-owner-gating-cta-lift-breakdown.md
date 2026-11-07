# Owner-only Bowl/Golf, past-challenges fold, sticky CTA fix, lift breakdown — 2026-11-07

## What this was
One session, four asks from Tom after the 100 Club week-1 review: hide bowling and golf for every account but
`toka778@gmail.com`, fold ended challenges behind a toggle, fix the challenge upload button his phone screenshot
showed buried under the tab bar, then design and build a way to see each lift behind the week's score on a phone.
Narrative detail for each piece lives in `2026-11-07-declutter.md`; this file is the index.

## What changed
Commits on `feat/100-club` (laptop-only, no upstream):
- `b2de568` feat(frontend): show bowling and golf only to the owner's account — `lib/owner.ts`, `hooks/useIsOwner.ts`,
  Navbar, BottomTabBar (4 vs 6 tabs), Index tiles/pitch/demo/to-do, UploadChooser, Profile tabs, `lib/prompts.ts`.
- `9d3781b` feat(frontend): `/challenges` lists Open now / Coming up once, past ones behind "Past challenges (N)".
- `bed7ed3` feat(frontend): challenges with a Bowling or Golf category hidden from everyone but the owner.
- `dc06fd3` docs(shell): `docs/reference/finch-shell.md` section + CLAUDE.md reference row.
- `110d052` fix(frontend): sticky "Log a lift" button lifted above the bottom tab bar (`.above-tab-bar`, `pb-44`).
- `a939057` docs(shell): proof and APK for the CTA fix.
- `35c6eb5` feat(100-club): `components/challenge/clubBreakdown.ts` + `ConsistencyHero` segmented ring, legend per
  lift type, points receipt, uploads of the live week behind a 44 px toggle (lifts from results the page already fetches).
- `7edb772` docs(100-club): hero breakdown section in `docs/reference/100-club.md`, proof files.

Deployed: frontend `my-frontend-00201-5vm` → `00202-4gg` (CTA) → `my-frontend-00203-7gg` (breakdown, current).
Backend unchanged at `my-python-backend-00196-mtt`.

APK: `gs://jtr-lift-u-4ever-cool-bucket/apk/tomsgym-debug-20261107-152132.apk`, short link
`https://my-python-backend-quyiiugyoq-ue.a.run.app/s/7uv33h` (stamp 1794082851, expires 2026-11-14). Supersedes
`/s/wCz0Hq`, `/s/jciS2g`, `/s/VrMWQb`, `/s/LSOd2h`. Not installed on any device by this session.

Design canvas for the breakdown options (A ring, B tiles, C receipt, D log, E week cards, recommended A+C+D):
https://claude.ai/artifact/RxeQSFX7riSkVfkgoDhzno (private).

Memory: `project_owner_gating.md` updated with the gating recipe, canvas, decision and current APK.

## What we learned
- Passwordless viewers can be identified as the owner from the public `GET /users/<id>/profile` email; cached per device
  in localStorage `ownerCheck`, deduplicated in flight. Unknown reads as hidden, so strangers never see a flash.
- Challenge categories always carry a gender entry, so "sport challenge" must be `some`, not `every`, over categories.
- Two `fixed bottom-0` elements with different z-index silently stack; the tab bar (z-50) hid the CTA (z-40). jsdom drops
  `env()` from inline styles, so the offset lives in a CSS class and the test asserts the class.
- The uploads list needed no backend work: `ChallengeDetail` already fetches `GET /lifting/result/<id>` for every video.
  The per-attempt plank floor (`attemptLifts`) summed exactly to the backend week total for both live athletes.
- CSS `text-transform: uppercase` changes Playwright `innerText`; compare `textContent` with whitespace stripped.
- A proof script against a build that lacks the new test ids fails for the wrong reason; the negative control must
  locate by something both builds share (done for the CTA proof; the breakdown control failed on an empty segment list).

## Still broken / next steps
- Tom must install `/s/7uv33h` on his phone before 2026-11-14; nothing was opened on a device.
- Eight files under `docs/research/2026-10-10-glasses-pov-tracking/truth/` show as deleted in the working tree since
  15:16 today. Another Claude session (`5f479c86`) was active in this repo at that minute; this session did not touch
  them and did not restore them. Check that session before committing or restoring.
- Open decisions from the week-1 review: B12 (type-bonus minimum), R8 (should club squats store weight 0).
- `StreakCard` share text still reads "Lifting, bowling and golf" for everyone.
- Owner gating hides rather than blocks: `/bowl`, `/golf` and friends open by URL, and the owner email is a literal in
  the bundle. Fine for clutter, not for privacy.
- Branch has no upstream; eight commits today are laptop-only.

## Verification
- Jest: 766 → 767 → 786 green across the three features (`node node_modules/jest/bin/jest.js --json`).
- tsc: 43 pre-existing errors throughout, none in changed files.
- Mutation checks with byte-identical restores: 15 (gating), 1 (CTA), 12 (breakdown), all killed.
- Prod, scripted Playwright with injected `localStorage.userId` (owner, caleb, anonymous), every non-GET answered
  locally: `prove-owner.mjs` 58/58 on 00201 at 1280 and 390 px; `prove-cta.mjs` 4/14 on 00201 (control) then 14/14 on
  00202; `prove-breakdown.mjs` failed on 00202 (control) then 57/57 on 00203 at 390 px, numbers checked against the
  live board and lifts. Outputs and screenshots in `docs/sessions/2026-11-07-declutter/`.
- APK: build stamp read from `assets/public/index.html`, feature marker found in `ConsistencyResult-*.js` with
  `vite:preloadError` as the fetch control, short-link download byte-identical via `cmp`.
- Not verified: Tom's real signed-in session, any physical device, the JWT owner path outside jsdom, desktop width for
  the breakdown, a failed or still-analysing upload in prod.
