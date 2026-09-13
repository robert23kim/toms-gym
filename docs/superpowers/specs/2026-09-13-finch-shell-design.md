# Finch-style shell: bottom tabs + Home to-do list

**Date:** 2026-09-13 · **Scope:** frontend only · **Goal:** fewer taps from opening the app to
uploading the bowling-night score photo (today ~6 before the camera; target 2).

## Split

By viewport width, not platform. Below `md` (768px): bottom tab bar, no hamburger, Home to-do
list. At `md` and up: today's top nav, no bottom bar; Home gets the to-do list only.

## 1. Bottom tab bar (`components/BottomTabBar.tsx`)

- Fixed bottom, `md:hidden`, five tabs: Home `/`, Lift `/lift`, Bowl `/bowl`, Golf `/golf`,
  Me (`/profile/<userId>` when localStorage `userId` exists, else `/find-profile`).
- Active tab by pathname prefix (`lib/tabs.ts`, pure):
  - Home: `/` exactly.
  - Lift: `/lift`, `/upload`, `/challenges`, `/champions`, `/video-player`.
  - Bowl: `/bowl`, `/bowling`.
  - Golf: `/golf`.
  - Me: `/profile`, `/find-profile`, `/signin`, `/auth`.
  - Anything else: none.
- Safe-area padding: `padding-bottom: env(safe-area-inset-bottom)`.
- `Layout` mounts it and adds `pb-24 md:pb-0` to `<main>` so content clears the bar.
- `Navbar` on phones shows the brand only (hamburger + mobile menu removed). Desktop nav unchanged.

## 2. Home to-do list (`components/home/PromptList.tsx`, `lib/prompts.ts`)

`buildPrompts({ userId, openChallenges })` returns an ordered list:

| id | title | action |
|---|---|---|
| `bowl-snap` | Snap tonight's scores | camera (see §3); anonymous → link `/bowling/snap` |
| `challenge:<id>` (one per ongoing challenge) | challenge title, pill = first category | link `/challenges/<id>/upload` |
| `golf-snap` | Snap a scorecard | link `/golf/snap` |
| `lift-upload` | Log a lift | link `/lift/upload` |

Row = icon chip · title (+ pill) · trailing action button (camera icon or arrow). Header
"Tonight's to-do". Whole list renders for every visitor; only the camera behaviour depends on
`userId`.

`Index.tsx`: returning users see streak → to-do list → champion spotlight (vertical tiles and the
open-challenges strip are removed for them). First-time visitors keep pitch → streak → demo →
spotlight → tiles, then the to-do list.

## 3. Two-tap bowling snap

- Hidden `<input type="file" accept="image/*" capture="environment">` behind the camera button.
- On change: `uploadBowlingSheet(buildSheetForm(file, { sheetType: "night", playedOn: todayLocal(),
  userId }))` → `navigate(/bowling/scoresheet/<sheet_id>)`. Row shows "Reading…" while pending;
  error text inline under the row; the input is reset so the same photo can be retried.
- `lib/bowlingSheetForm.ts::buildSheetForm(file, {sheetType, playedOn, userId?, email?})` is shared
  with `BowlingSheetUpload.tsx`. `todayLocal` moves to `lib/dates.ts`.
- Review page already displays date and type; no change there.

## 4. Tests

Jest: `lib/__tests__/tabs.test.ts`, `lib/__tests__/prompts.test.ts`,
`components/__tests__/BottomTabBar.test.tsx` (active tab, Me target),
`components/__tests__/PromptList.test.tsx` (file change uploads with night/today/userId and
navigates; anonymous camera row is a link to `/bowling/snap`; error shown), `Index.test.tsx`
and Navbar updates. Existing `BowlHub`/`GolfUpload` tests untouched.

## 5. Ship

`python3 deploy.py --frontend-only --skip-iam`, Playwright walk of production at 390×844 (Home,
tab bar on every hub, snap row present), then `npm run android:build` + `android:publish`.

## Out of scope

Done-state checkmarks, day-aware ordering, Android hardware back button, deep links.
