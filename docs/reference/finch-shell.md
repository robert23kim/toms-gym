<!-- Moved verbatim from CLAUDE.md on 2026-09-19; CLAUDE.md keeps a pointer. -->
# Finch-style Shell (shipped 2026-09-13)

Bottom tab bar + Home to-do list, modelled on Finch, so the bowling-night score photo is two taps
from opening the app. Spec: `docs/superpowers/specs/2026-09-13-finch-shell-design.md`; plan:
`docs/superpowers/plans/2026-09-13-finch-shell.md`. Frontend only, split by **width** (`md` =
768px), never by platform: phone browsers and the APK get the same shell, desktop keeps the top nav.

- **`components/BottomTabBar.tsx`** (`md:hidden`, safe-area padded, mounted in `Layout`, which pads
  `<main>` `pb-24 md:pb-6`): Home · Lift · Bowl · Golf · Champions · Me. Active tab by route prefix in the pure
  `lib/tabs.ts::activeTab` (`/bowling/*` → Bowl, `/challenges|/upload` → Lift, `/champions` → Champions,
  `/profile|/find-profile|/signin|/auth` → Me); `meTarget(userId)` is `/profile/<id>` or
  `/find-profile`. `Navbar` lost its hamburger + phone menu; Feedback/Store are footer/desktop only.
- **`components/home/PromptList.tsx`** renders `lib/prompts.ts::buildPrompts(openChallenges)`:
  "Snap tonight's bowling recap" (night sheet) → "Snap a bowling game" (game sheet) → one row per
  ongoing challenge → "Snap a golf scorecard" `/golf/snap` → "Log a lift" `/lift/upload`. With a saved
  `userId` each bowling row has two pickers, camera (`home-bowl-camera` / `home-game-camera`,
  `capture="environment"`) and library (`home-bowl-library` / `home-game-library`), both uploading the
  photo immediately with that row's `sheetType`, **dated today**, via `lib/bowlingSheetForm.ts::buildSheetForm`
  (shared with `BowlingSheetUpload`) and navigating to the review page. A challenge whose only
  category is a bodyweight lift (`quickLiftType`: Plank/Pushup/Situp) becomes a **video row** with
  record (`home-challenge-<id>-record`) and upload (`-upload`) pickers that call
  `resumableUpload.uploadVideo` with `{competition_id, lift_type, weight:"0", user_id}` (Plank →
  `fast-only` compression), trigger analysis and go to `/lift/status/<attempt>?challenge=<id>`, with
  progress on the row; weighted or multi-category challenges link to `/challenges/<id>` (never the
  bare `/challenges/<id>/upload`, which defaults to Squat). Anonymous visitors get links to
  `/bowling/snap` / `/challenges/<id>` (email needed). `lib/dates.ts::todayLocal` is the date source.
- `Index.tsx`: returning users see to-do → streak only (tiles, challenge strip and the champion
  spotlight are gone; `ChampionSpotlight.tsx` is retained but unused, like `TopLifts`); first-timers
  keep pitch/demo/tiles with the to-do below.
- Tests: `lib/__tests__/tabs|prompts|bowlingSheetForm`, `components/__tests__/BottomTabBar|PromptList`,
  `Index.test.tsx` rewritten. Suite at ship: 92 suites / 634 tests. No eslint config in `frontend/`
  — tsc + jest are the gates.
