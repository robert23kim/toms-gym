# Finch-style Shell Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Bottom tab bar on phones plus a Home to-do list whose first row opens the camera and uploads the bowling-night score photo in two taps.

**Architecture:** Pure helpers (`lib/tabs.ts`, `lib/prompts.ts`, `lib/bowlingSheetForm.ts`) feed two new components (`BottomTabBar`, `home/PromptList`). `Layout` mounts the bar; `Navbar` loses its phone menu; `Index` swaps tiles for the list on returning users. Width split via Tailwind `md:` only.

**Tech Stack:** React 18, react-router v6, Tailwind, lucide-react, Jest + RTL (`node node_modules/jest/bin/jest.js`), Vite.

**Spec:** `docs/superpowers/specs/2026-09-13-finch-shell-design.md`

## Global Constraints

- Frontend only; no backend or API changes.
- Phone/desktop split is by width (`md` = 768px), never by platform.
- Page tests mock `../../config` (Vite `import.meta`) and stub `Layout`; `jest.setup.js` stubs `localStorage` with `jest.fn()` (mock `getItem`'s return value).
- No comments unless the code is non-obvious. No `any`.
- Run tests with `cd frontend && node node_modules/jest/bin/jest.js <path>`; typecheck with `npx tsc --noEmit`.

---

### Task 1: `lib/tabs.ts` — active tab by pathname

**Files:** Create `frontend/src/lib/tabs.ts`, `frontend/src/lib/__tests__/tabs.test.ts`.

**Produces:** `type TabKey = "home"|"lift"|"bowl"|"golf"|"me"`; `activeTab(pathname: string): TabKey | null`; `meTarget(userId: string | null): string`.

- [ ] Test:
```ts
import { activeTab, meTarget } from "../tabs";
describe("activeTab", () => {
  it.each([
    ["/", "home"], ["/lift", "lift"], ["/lift/upload", "lift"], ["/upload", "lift"],
    ["/challenges/abc", "lift"], ["/champions", "lift"], ["/bowl", "bowl"],
    ["/bowling/scoresheet/1", "bowl"], ["/golf/snap", "golf"], ["/profile/u1", "me"],
    ["/find-profile", "me"], ["/signin", "me"], ["/auth/magic/t", "me"], ["/terms", null],
  ])("%s → %s", (path, tab) => expect(activeTab(path)).toBe(tab));
});
describe("meTarget", () => {
  it("goes to the saved profile", () => expect(meTarget("u1")).toBe("/profile/u1"));
  it("goes to find-profile when anonymous", () => expect(meTarget(null)).toBe("/find-profile"));
});
```
- [ ] Run, expect FAIL (module missing).
- [ ] Implement:
```ts
export type TabKey = "home" | "lift" | "bowl" | "golf" | "me";
const PREFIXES: [TabKey, string[]][] = [
  ["lift", ["/lift", "/upload", "/challenges", "/champions", "/video-player"]],
  ["bowl", ["/bowl", "/bowling"]],
  ["golf", ["/golf"]],
  ["me", ["/profile", "/find-profile", "/signin", "/auth"]],
];
export const activeTab = (pathname: string): TabKey | null => {
  if (pathname === "/") return "home";
  for (const [key, prefixes] of PREFIXES)
    if (prefixes.some((p) => pathname === p || pathname.startsWith(`${p}/`))) return key;
  return null;
};
export const meTarget = (userId: string | null): string => (userId ? `/profile/${userId}` : "/find-profile");
```
- [ ] Run, expect PASS. Commit `feat(shell): active-tab helper`.

### Task 2: `BottomTabBar` + Layout/Navbar wiring

**Files:** Create `frontend/src/components/BottomTabBar.tsx`, `frontend/src/components/__tests__/BottomTabBar.test.tsx`; modify `Layout.tsx` (mount bar, `pb-24 md:pb-0` on main), `Navbar.tsx` (delete hamburger button, mobile menu and `isMobileMenuOpen` state; keep desktop nav).

**Consumes:** Task 1.

- [ ] Test (`MemoryRouter initialEntries`): renders five links with hrefs `/`, `/lift`, `/bowl`, `/golf`, `/find-profile`; on `/bowling/insights/me` the Bowl link has `aria-current="page"` and the others do not; with `localStorage.getItem` → `"u1"` the Me link href is `/profile/u1`.
- [ ] Run, expect FAIL.
- [ ] Implement: `<nav aria-label="Primary" className="md:hidden fixed bottom-0 inset-x-0 z-50 bg-background/90 backdrop-blur-md border-t border-border/40" style={{paddingBottom:"env(safe-area-inset-bottom)"}}>` with a 5-col grid of `<Link>` (icon over 11px label; active = `text-accent`, else `text-muted-foreground`; `aria-current={active ? "page" : undefined}`). Icons: Home, Dumbbell, CircleDot, Flag, User.
- [ ] Layout: import + render `<BottomTabBar />` after footer; main gets `pb-24 md:pb-0`. Navbar: remove the `md:hidden` toggle div and the `isMobileMenuOpen &&` block, the `Menu` import and the route-change effect.
- [ ] Run new test + `LayoutFooter.test.tsx`; tsc. Commit `feat(shell): bottom tab bar on phone widths`.

### Task 3: `lib/bowlingSheetForm.ts` + `todayLocal` in dates

**Files:** Modify `frontend/src/lib/dates.ts` (add `todayLocal`), create `frontend/src/lib/bowlingSheetForm.ts`, test `frontend/src/lib/__tests__/bowlingSheetForm.test.ts`; modify `pages/BowlingSheetUpload.tsx` to use both.

**Produces:** `buildSheetForm(file: File, opts: {sheetType: BowlingSheetType; playedOn: string; userId?: string | null; email?: string}): FormData`; `todayLocal(now?: Date): string`.

- [ ] Test: form has `image` = file, `sheet_type`, `played_on`; `user_id` when given and no `email`; `email` when no userId. `todayLocal(new Date(2026, 8, 3))` → `"2026-09-03"`.
- [ ] Run, expect FAIL. Implement (move `todayLocal` out of BowlingSheetUpload, accept `now` param). Replace the page's inline FormData with `buildSheetForm`. Run tests + tsc. Commit `refactor(bowling): share score-sheet form builder`.

### Task 4: `lib/prompts.ts`

**Files:** Create `frontend/src/lib/prompts.ts`, `frontend/src/lib/__tests__/prompts.test.ts`.

**Produces:**
```ts
export type Prompt =
  | { id: "bowl-snap"; kind: "camera"; title: string; fallbackTo: string }
  | { id: string; kind: "link"; title: string; to: string; pill?: string };
export const buildPrompts = (openChallenges: Pick<Competition, "id"|"title"|"categories">[]): Prompt[]
```
- [ ] Test: with `[]` → ids `["bowl-snap","golf-snap","lift-upload"]`, first is `kind:"camera"` with `fallbackTo:"/bowling/snap"`; with one challenge `{id:"c1",title:"Situps",categories:["Situp"]}` → second prompt `{id:"challenge:c1", to:"/challenges/c1/upload", pill:"Situp"}`.
- [ ] Run, FAIL. Implement. PASS. Commit `feat(home): prompt list builder`.

### Task 5: `components/home/PromptList.tsx`

**Files:** Create `frontend/src/components/home/PromptList.tsx`, `frontend/src/components/__tests__/PromptList.test.tsx`.

**Consumes:** Tasks 3, 4; `uploadBowlingSheet` from `lib/api`.

Props: `{ prompts: Prompt[]; userId: string | null }`. Renders `<section aria-label="To-do">` with heading "Tonight's to-do" and one row per prompt: icon chip (CircleDot for bowl-snap, Trophy for challenge, Flag for golf, Dumbbell for lift), title, optional pill, trailing control. Link rows: whole row is a `<Link>`, trailing `ArrowRight`. Camera row with `userId`: a `<label htmlFor="home-bowl-camera">` button wrapping a hidden `<input id="home-bowl-camera" type="file" accept="image/*" capture="environment" data-testid="home-bowl-camera">`; on change → `setBusy(true)`, `uploadBowlingSheet(buildSheetForm(file, {sheetType:"night", playedOn: todayLocal(), userId}))`, `navigate(`/bowling/scoresheet/${sheet.sheet_id}`)`; on error set inline message; `finally` `setBusy(false)` and `e.target.value = ""`. Title shows "Reading…" while busy. Camera row without `userId`: a `<Link to={fallbackTo}>` with a Camera icon.

- [ ] Test (mock `../../lib/api` `uploadBowlingSheet`, mock `useNavigate` via `jest.mock("react-router-dom", ...)` spreading actual): (a) anonymous → bowl row is a link to `/bowling/snap`; (b) userId `u1`, `fireEvent.change(input, {target:{files:[file]}})` → `uploadBowlingSheet` called once, FormData has `sheet_type=night`, `user_id=u1`, `played_on` matches `todayLocal()`; navigate called with `/bowling/scoresheet/s1`; (c) rejected upload with `{response:{data:{error:"blurry"}}}` shows text containing "blurry"; (d) challenge link row href `/challenges/c1/upload`.
- [ ] Run, FAIL. Implement. PASS. Commit `feat(home): to-do prompt list with two-tap bowling snap`.

### Task 6: Index rewrite + test update

**Files:** Modify `frontend/src/pages/Index.tsx`, `frontend/src/pages/__tests__/Index.test.tsx`.

- [ ] Update test: returning-user section order → `["Your streak","To-do","Latest champion"]`, no `/lift` tile link, bowl row link `/bowling/snap` absent when userId set (camera input present via `data-testid`), challenge row href `/challenges/c1/upload`. Anonymous order → `["Pitch","Your streak","Analysis demo","Latest champion","Verticals","To-do"]`; tiles still present. Remove the "open challenges strip" tests. Stub `PromptList`? No — render it real; mock `uploadBowlingSheet`.
- [ ] Run, FAIL. Implement: `const prompts = buildPrompts(open)`; returning: streak → `<PromptList>` → spotlight; anonymous: pitch → streak → demo → spotlight → verticals → `<PromptList>`.
- [ ] Run all jest + tsc + `npm run lint` if present. Commit `feat(home): finch-style to-do list replaces tiles for returning users`.

### Task 7: Ship

- [ ] `cd frontend && npm run build` clean.
- [ ] `python3 deploy.py --frontend-only --skip-iam` from repo root.
- [ ] Playwright (MCP) at 390×844 on production: `/` shows the tab bar + "Snap tonight's scores"; `/bowl` and `/bowling/insights/me` highlight Bowl; no horizontal overflow; console clean. Desktop 1280 wide: no tab bar, top nav intact.
- [ ] `VITE_BUILD_TIMESTAMP=$(date +%s) npm run android:build && npm run android:publish`; report the short link.
- [ ] Update CLAUDE.md with a short "Finch shell" section; commit.
