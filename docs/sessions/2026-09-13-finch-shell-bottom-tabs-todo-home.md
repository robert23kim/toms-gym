# Finch-style shell: bottom tabs + to-do home — 2026-09-13

## What this was
Tom wanted the phone app to feel like Finch: a bottom button row for Bowl / Golf / Lift and a
list of prompts, so the bowling-night score photo takes as few taps as possible (it was ~6
before the camera opened). Three rounds of feedback followed in the same session: to-do first,
library pickers, one-tap challenge video, Champions as a tab, two bowling rows, sport names.

## What changed
Frontend only. Split by width (`md` = 768px), never by platform. All on `main`, pushed
(`941f68a..ed4cccf`). Spec `docs/superpowers/specs/2026-09-13-finch-shell-design.md`, plan
`docs/superpowers/plans/2026-09-13-finch-shell.md`, CLAUDE.md section "Finch-style Shell".

- `427a616` `lib/tabs.ts` — `activeTab(pathname)` by route prefix, `meTarget(userId)`.
- `4aa81af` `components/BottomTabBar.tsx` mounted in `Layout` (`md:hidden`, safe-area padded,
  `<main>` padded `pb-24 md:pb-6`); `Navbar` lost the hamburger + phone menu.
- `8862a30` `lib/bowlingSheetForm.ts::buildSheetForm` + `lib/dates.ts::todayLocal`, shared with
  `BowlingSheetUpload`.
- `3a90c9f` / `8f1d7a4` `lib/prompts.ts::buildPrompts` + `components/home/PromptList.tsx`;
  `Index.tsx` drops tiles and the challenge strip for returning users.
- `5537b24` to-do above the streak; bowling row gets a library picker; a single-bodyweight-lift
  challenge becomes a video row (record / upload) that calls `resumableUpload.uploadVideo` with
  the challenge's lift type, weight `"0"`, triggers analysis, navigates to
  `/lift/status/<id>?challenge=<id>` with progress on the row.
- `4382582` Champions tab (`/champions`) between Golf and Me; champion spotlight removed from
  Home (`ChampionSpotlight.tsx` retained, unused).
- `696f151` `quickLiftType` filters to lift categories before the "single bodyweight lift" test.
- `8abdf5b` two bowling rows: "Snap tonight's bowling recap" (`sheet_type=night`) and "Snap a
  bowling game" (`game`), ids `home-bowl-*` / `home-game-*`.
- `6244abe` "Snap a golf scorecard".
- Deployed: frontend revisions `my-frontend-00192-dxt` → `00193-7jh` → `00194` → `00196`.
  APK short links (7 days): `/s/KxfoER`, `/s/3LapLw`, `/s/pmD8ux`, `/s/PXvHsd` (current).

## What we learned
- **`getCompetitions()` appends `Men`/`Women` (and weight classes) to `categories`**, so a
  "challenge with exactly one category" rule never matches a real challenge. The situp row
  shipped as a plain link in prod before `696f151`; jest fixtures used bare `["Situp"]`.
- **The old `/challenges/<id>/upload` link defaulted the form to Squat** — a "situp" prompt
  linking there would have posted the wrong lift type. Preset the lift on the row instead.
- **A fresh APK install looks stale because the WebView has its own localStorage.** No
  `userId` → anonymous home (pitch, demo, tiles, to-do at the bottom as links). Diagnose from
  Cloud Run logs: `action=boot platform=capacitor` carries the build stamp (matched the APK),
  and the app's boots hit `/competitions` but never `/users/<id>/activity`. One-time fix on the
  phone: Me tab → Find Profile → email. Recorded in memory `android_app.md`.
- The pre-existing uncommitted CLAUDE.md engine-lane hunk was stashed around the branch
  fast-forward and later committed by another session (`ef1dec4`); this session's CLAUDE.md
  edits were staged hunk-by-hunk (`git apply --cached --recount` on a filtered diff) so the two
  never mixed.
- `getByRole("link", {name: /bowl/i})` in `Index.test.tsx` became ambiguous once to-do rows
  mentioned the sport; anchored the regexes (`/^bowl/i`, `/^golf/i`, `/^lift/i`).
- No eslint config exists in `frontend/` (`npx eslint` errors out); tsc + jest are the gates.

## Still broken / next steps
- **The real camera → upload → review path is unverified on the phone.** Only desktop Chromium
  at 390px was walked; `capture="environment"` and the Android file picker need one bowling
  night / one situp clip to prove.
- **Anonymous home still buries the to-do list** (pitch/demo/tiles first, links only). Tom
  worked around it by signing in once; a to-do-first anonymous layout that asks for an email on
  first use is the obvious follow-up so a reinstall needs no sign-in step.
- Both bowling rows are dated today with no confirmation; a different date or a game screen
  from another night still needs the Bowl tab's full form.
- `ChampionSpotlight.tsx` and `TopLifts.tsx` are dead code; delete in a hygiene pass.
- Android hardware back button, deep links, icon/splash and a release keystore remain open
  from the Android session.
- The `.env.production` local modification predates this session and is still uncommitted.

## Verification
- Jest via `node node_modules/jest/bin/jest.js --json`: 92 suites / 634 tests green at the final
  commit (621 → 632 → 634 across the session). `npx tsc --noEmit` clean at every commit.
- Mutation checks: lift type hardcoded to Squat → 2 PromptList tests fail; sheet type hardcoded
  to night → 2 game-row tests fail; both reverted.
- Production (Playwright MCP, 390×844, `userId` seeded in localStorage): to-do section first;
  six file inputs present (`home-bowl-camera/library`, `home-game-camera/library`,
  `home-challenge-95b60b42…-record/upload`); tab bar shows the correct active tab on `/`,
  `/bowl`, `/bowling/insights/me`, `/golf`, `/challenges`, `/champions`; hidden at 1280px; no
  horizontal overflow; no console errors. Row copy confirmed on rev 00196.
- APK `/s/PXvHsd` returns 302 to the signed object and its bundled JS contains all three renamed
  row titles. Tom confirmed the new home on his phone after signing in via Me.
- Push confirmed: `git ls-remote origin refs/heads/main` == local HEAD `ed4cccf`.
- Not verified: the on-phone camera flows above; the situp upload end to end with a real clip.
