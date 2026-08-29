# Delight loop — iteration 01 (2026-08-29)

Goal of the loop: make using Tom's Gym on a phone feel delightful. Each iteration:
personas → mobile walkthrough of their real flows in production → idea list →
critical review (with an explicit **clutter / duplicate-information** lens) →
implement the top 3 → deploy → verify in prod → document decisions, artifacts and
every bug seen (bugs are logged even when not fixed).

Production build walked: see "Walkthrough" below. Viewport: 390×844 (iPhone 14),
Chromium via Playwright MCP. Screenshots in `screenshots/`.

## Personas

Five people, chosen to cover every vertical plus the two "I came back" states the
app has to handle (has a session / lost the session). Each has a job-to-be-done, a
device context, and the exact route path they take today.

### P1 — Priya, first-time plank challenger (shared link)
- **Who:** 29, does a lunchtime plank with coworkers. Never heard of the app. A
  coworker sent a short-link to the Pushup challenge in a group chat.
- **Device/context:** iPhone in one hand, gym mat on the floor, 5 minutes.
- **Job:** "Enter the challenge, record my set, see where I rank."
- **Route today:** `/s/<code>` → `/challenges/4bd57523…` (Pushup challenge) →
  Record now → `/lift/status/:attempt` → `/challenges/…/video/:attempt` → Share.
- **Delight bar:** from tap-on-link to "recording" in ≤2 taps; result explains
  itself without jargon; she can send *her* result back to the chat.

### P2 — Marcus, Thursday-night league bowler
- **Who:** 41, bowls 3 games every Thursday. Wants to know if he is getting better
  and what to work on. Not interested in video analysis.
- **Device/context:** Android phone, bowling alley lighting, photographing the
  overhead RESULTS monitor at the end of the night while packing up.
- **Job:** "Snap the screen, claim my row, see my average trend and one tip."
- **Route today:** home → Bowl hub → `/bowling/snap` → `/bowling/scoresheet/:id`
  (review, claim "This is me") → `/bowling/insights/me` → profile Bowl tab.
- **Delight bar:** camera opens immediately; review page needs zero typing when
  the OCR is right; insight page has *one* headline number and *one* tip.

### P3 — Dana, weekend golfer
- **Who:** 35, plays 18 holes every other Sunday with two friends. Keeps score on
  paper. Wants a handicap without joining a club.
- **Device/context:** in the parking lot after the round, card on the dashboard.
- **Job:** "Photograph the card, confirm my row, see my new handicap and whether
  it moved."
- **Route today:** home → Golf hub → `/golf/snap` → `/golf/review/:round`
  (pick row, resolve course/tee/date, confirm) → HandicapResultCard →
  `/golf/leaderboard` / `/golf/profile/:id`.
- **Delight bar:** the confirm screen asks only for what OCR could not read;
  the handicap delta is the hero; her friends appear on the leaderboard too.

### P4 — Tom, the regular (owner / power user)
- **Who:** the app's owner and heaviest user. Lifts, bowls, golfs. Has champion
  titles, a streak, dozens of attempts.
- **Device/context:** phone, checks in most days; opens the home page cold.
- **Job:** "Show me my streak, my progress, and what is open right now — then let
  me upload in one tap."
- **Route today:** `/` (streak card, champion spotlight, open challenges) →
  `/profile/7844e26d…` (Lift/Bowl/Golf tabs, trophy case, history) →
  `/champions` → `/challenges/:id`.
- **Delight bar:** home is a dashboard, not a landing page; nothing on the home
  page repeats what the profile says and vice-versa; ≤1 scroll to reach an upload.

### P5 — Sam, the returning lurker (lost session)
- **Who:** 52, uploaded a bench video once in April, then got a new phone. No
  localStorage, no password. Wants to see the old video and upload a new one
  under the same account.
- **Device/context:** new iPhone, Safari, evening on the couch.
- **Job:** "Find my old profile from my email, then upload again as me."
- **Route today:** `/` → nav "Find Profile" → `/find-profile` (email) → either
  `/profile/:id` directly or `/signin` magic link → `/lift/upload`.
- **Delight bar:** one email field, no account jargon, and the upload form
  remembers who they are afterwards.

## Workflow map (today)

```
                 ┌──────────── / (home) ────────────┐
                 │ streak · spotlight · tiles · open │
                 └──┬──────────┬──────────┬──────────┘
                    │          │          │
                 /lift      /bowl      /golf         (hubs = 1 primary CTA + rows)
                    │          │          │
            /lift/upload  /bowling/snap  /golf/snap   (P1 enters here via /challenges/:id)
                    │          │          │
            /lift/status  /bowling/     /golf/review
                    │      scoresheet/:id     │
        /challenges/:id/…/video   │     HandicapResultCard
                    │     /bowling/insights   │
                    └──────────┬──────────────┘
                        /profile/:id (Lift · Bowl · Golf tabs)
                        /champions · /challenges · /find-profile · /signin
```

## Walkthrough (production, 2026-08-29, build `v2026-08-29 03:55 UTC`)

Method: Playwright MCP, Chromium, viewport 390×844, `localStorage.userId`
injected for the "has a session" personas (P2/P3/P4), cleared for P1/P5. One
script (`.playwright-mcp/walk.js`, not committed) visited 25 routes, saved a
full-page screenshot per route into `screenshots/` and recorded page height,
headings, visible CTAs, word count, horizontal overflow and console errors.
Zero console errors on any page.

| Persona · screen | Height (px) | CTAs | What it felt like |
|---|---|---|---|
| P1 challenge page | 1129 | 9 | Good hero + podium. Sticky "Upload your pushups" **and** a "YOU · Not logged yet · Upload →" row right under it — same action twice. |
| P1 result page (pushup) | 1540 | 11 | Grade, set breakdown and coaching read well. But the *Tips* card repeats the coaching lines, "consider lighter weight" is nonsense for a pushup, "Approved" pill is unexplained, and "Re-analyze" is offered to any visitor. No way for a visitor to enter the challenge from here. |
| P1 "Analysis complete!" | 1053 | 8 | **Dead end.** The page says "Your results are ready to view" but offers only *View Your Profile* / *Upload Another* — there is no link to the result. |
| P5 home (anon) | 1789 | 12 | Fine as a landing page. |
| P5 find profile / sign in | 844 | 7 / 1 | Clean, single field, honest copy. Best screens in the app. |
| P5 lift upload | 1053 | 7 | Email field first, then a `Weight (kg)` default of 60 — reasonable. |
| P4 home (session) | 1945 | 13 | A daily user scrolls past a marketing headline + a 12s demo animation *every visit* before reaching their own streak. |
| P4 profile | **6941** | **54** | The same 10 attempts listed **three times** (My lifts → Lift Videos → Competition History). "Personal Bests: Plank 60.00 lbs / snatch 0.00 lbs", "Best Snatch: 1 lifts", raw `in_progress` pills, "120.00 lbs total" on a pushup challenge, kg in one list and lbs in the next. Champion toast covers the page title. |
| P4 champions | 1772 | 20 | Rich and fun; toast overlaps the title. |
| P4 challenges | 895 | 16 | **Scrolls horizontally** — the filter-pill row is 443px wide on a 390px screen. |
| P2 bowl hub / sheet upload | 844 / 1005 | 9 | Camera-first, short. Good. |
| P2 insights | 1299 | 9 | One headline + one tip: exactly right. Dates are ISO (`2026-08-29`), "Last 5 vs before —" is an empty tile. |
| P2 bowling result | 1898 | 9 | Two of four stat tiles are "—". |
| P3 golf hub / upload / leaderboard | 844–1053 | 8–10 | Short, clear. |
| P3 golf profile / round | 1199 / 1801 | 12 / 7 | Good density; dates are ISO. |

## Ideas (unfiltered)

1. Profile Lift tab: one history list instead of three; drop the garbage stat cards.
2. "Analysis complete!" → deep-link straight to the result page.
3. Returning-user home: skip the pitch + demo, lead with streak and what's open.
4. `/challenges` filter pills wrap instead of overflowing.
5. Humanize ISO dates on golf profile, golf round, bowling insights.
6. Bodyweight lifts: drop/remap weight-based tips ("consider lighter weight") and the duplicate Tips card when set coaching is present.
7. "Re-analyze" only for the owner of the attempt.
8. Shared result page: "Beat this →" CTA into the challenge when it is ongoing.
9. Challenge page: remove the duplicate "Upload →" row under the sticky button.
10. Bowling result / insights: hide empty "—" stat tiles.
11. Champion toast: don't cover the h1 (bottom-anchor or auto-dismiss).
12. Page `<title>` per page (video page says "Challenges").
13. Profile email visible to everyone → owner only.
14. Explain the "Approved"/"Successful" pill on results (or drop it).

## Critical review

Lenses, in order: (a) does a *phone* user hit it on a first or daily visit,
(b) clutter / duplicate information, (c) is the data it shows true,
(d) effort and blast radius. Scores are impact × reach ÷ effort, roughly.

| # | Idea | Reach | Impact | Effort | Verdict |
|---|---|---|---|---|---|
| 1 | Profile de-clutter | every persona lands here | very high — 6.9k px → ~2k px, removes false numbers | medium (delete-heavy, one page) | **BUILD** |
| 2 | Result deep-link | every uploader, at the emotional peak | high — turns a dead end into the payoff | small (+2 fields backend, 1 branch frontend) | **BUILD** |
| 3 | Returning-user home | daily users | high — first screen becomes *theirs* | small (one page, one flag) | **BUILD** |
| 4 | Pill overflow | everyone on /challenges | medium — feels broken | trivial | bonus fix, shipped with #3 |
| 13 | Email privacy | every profile visitor | medium (privacy) | trivial, same section as #1 | folded into #1 |
| 5 | ISO dates | golf + bowl | low-medium | small | next iteration |
| 6, 7, 8, 14 | Result-page cleanups | pushup/plank uploaders | medium | medium (VideoPlayer is 48k) | next iteration, as one pass |
| 9, 10, 11, 12 | small polish | narrow | low | small | backlog |

Rejected for now: a "dashboard" rebuild of home (too speculative), changing the
engine's tip text (lives in another repo — a frontend remap is the right layer,
see the pushup-copy precedent in `lib/liftCoaching.ts`).

## Decisions (top 3)

**D1 — Profile Lift tab = one honest history.** Remove *Competition Stats*,
*Personal Bests* and *Achievements* cards (their numbers are placeholder
weights and mislabeled units), the *Lift Videos* gallery and the *Competition
History* block (both re-list what `LiftHistoryList` already shows, with wrong
units and a link to a route that does not exist, `/competitions/:id`). Keep:
header, trophy case, tabs, `LiftHistoryList`, *Track Weekly Lifts* row, and an
upload CTA (empty state keeps "Upload your first lift"). Email shows only to the
owner. Bowl and Golf tabs untouched.

**D2 — "Analysis complete!" links to the result.** `GET /lifting/result/<id>`
gains `competition_id` and `user_id` (Attempt ⋈ UserCompetition). The status
page's lifting `resultPath` builds
`/challenges/:comp/participants/:user/video/:attempt` from them; the primary
button reads "See your result". Profile stays the fallback when either id is
missing (older rows, tests).

**D3 — Home knows you.** When `localStorage.userId` exists, `Index.tsx` skips
the hero headline and the demo loop and orders the page streak → open
challenges → verticals → champion spotlight. Anonymous visitors see the page
exactly as today.

Bonus: `/challenges` filter pills wrap (`flex-wrap`).

## Bug log (everything seen on this walk — fixed or not)

| # | Where | Bug | Status |
|---|---|---|---|
| B1 | `/lift/status/:id` | "Analysis complete! Your results are ready to view" with no link to the result — only profile / upload again. Cause: `KIND_CONFIG.lifting.resultPath` returned `null` and the result payload had no ids to build the route. | **Fixed** (D2, `fd821f6` + `5b9912e`) |
| B2 | `/challenges` | Page scrolls horizontally on a 390px phone; the filter-pill row is 443px wide. | **Fixed** (`1ac42ee`) |
| B3 | `/profile/:id` | The owner's **email address is shown to every visitor** (verified anonymously via Playwright: `anonSeesEmail: true`). | **Fixed** (D1, owner-only) |
| B4 | `/profile/:id` Lift tab | "Personal Bests: Plank 60.00 lbs / Pushup 60.00 lbs / snatch 0.00 lbs", "Heaviest Lift 240.00 lbs" (it is 240 *kg*), "Best Snatch: 1 lifts"; kg in *My lifts*, lbs two sections later; "Competition History" links to `/competitions/:id`, which is not a route (404 page). | **Removed** (D1) |
| B5 | Pushup result page | Tips card says "Range of motion decreasing — consider lighter weight" on a bodyweight lift. Text comes from the analysis engine (not in this repo); the frontend already remaps pushup *metric* copy in `lib/liftCoaching.ts` but not *tips*. | Open — next iteration, remap/drop weight tips for `isBodyweightLift` |
| B6 | Video result page | **"Re-analyze" is offered to anonymous visitors** on anyone's attempt — any visitor can trigger a paid engine run on someone else's video. | Open — should be owner-only (localStorage userId === participant) |
| B7 | `/profile/:id`, `/champions` | The one-shot "👑 Champion! Nice work." toast is `fixed` at the top and sits over the page title on mobile. | Open — bottom-anchor or auto-dismiss |
| B8 | Video result page | `<title>` is "Challenges \| Tom's Gym"; a shared/bookmarked result reads as "Challenges". | Open |
| B9 | Golf profile, golf round, bowling insights | Dates render as ISO (`2026-07-02`, `2026-08-29 Game 3`). Everywhere else uses "Jul 2". | Open — small |
| B10 | Bowling result, bowling insights | Stat tiles render "—" (Ball Speed, Hook; "Last 5 vs before") instead of hiding until there is data. | Open — cosmetic |
| B11 | Challenge page | Sticky "Upload your pushups" button **and** a "YOU · Not logged yet · Upload →" row directly beneath it — same action twice on one screen. | Open |
| B12 | Plank result page (`370a028b…`) | The original video plays rotated 90° (person lying sideways); the annotated version is upright. Looks like the browser ignores the source's rotation metadata after normalization. Only observed on this one attempt. | Open — needs a second sample |
| B13 | `GET /competitions` | "Summer plank challenge" (ended 2026-07-31) still reports `status: in_progress`; the frontend derives "completed" from `end_date` so lists look right, but the raw status leaked into the (now removed) Competition History pills. | Open — data/backend status never flips |
| B14 | Carried from 2026-08-28 | Status pages poll forever on unknown ids; `/profile` with no session hangs on "Loading profile…"; gallery cards say "Plank - 60.00kg" (now gone from the profile, still on `/challenges/:id/videos`); pending weight lifts show a manual "Analyze Form" button. | Open |

## Artifacts

- `screenshots/p*-NN-*.jpeg` — 25 full-page mobile captures, one per persona step, plus `p4-02-profile-chunk0..8.jpeg` (the 6,941px profile in viewport-sized slices).
- Walk script: `.playwright-mcp/walk.js` (gitignored; the route table is in the "Walkthrough" section above — recreate from it).
- Commits: `fd821f6` (backend ids), `5b9912e` (status deep-link), `c35f0d4` (returning-user home), `1ac42ee` (pill wrap), plus the profile de-clutter commit listed under "Results".
- Tests added: `backend/tests/test_lifting_routes.py` (3), `AnalysisStatus.test.tsx` (+2), `Index.test.tsx` (+2), `Profile.test.tsx` (new).

## Results (verified in production, build `v2026-08-29 15:57 UTC`)

Verification: `.playwright-mcp/verify.js` (same viewport/session setup as the
walk) re-measured each changed screen; `after-*.jpeg` screenshots sit next to
the befores.

| Screen | Before | After | Check |
|---|---|---|---|
| `/lift/status/:id` (completed) | no result link | primary button "See your result" → `/challenges/4bd57523…/participants/7844e26d…/video/53bd97fa…` | ✅ href verified |
| `/challenges` | scrollWidth 443px (horizontal scroll) | `overflowX: false` | ✅ |
| `/` with a session | 1945px, pitch + demo first | **1429px**, order streak → open challenges → verticals → champion | ✅ |
| `/` anonymous | 1789px, pitch + demo | unchanged | ✅ |
| `/profile/:id` (owner) | **6941px / 54 CTAs**, 3 copies of the history | **2012px / 30 CTAs**, one list + upload link | ✅ no "Personal Bests" / "Lift Videos" / "Competition History" |
| `/profile/:id` (visitor) | email shown | email hidden, "Change avatar" hidden | ✅ |

Backend: `GET /lifting/result/<id>` now returns `user_id` + `competition_id`
(revision after `my-python-backend-00181`, verified with curl). Frontend
revision built at 15:57 UTC.

Gates: backend CI gate **236 passed** (`PYTHON=venv/bin/python
tools/run_ci_tests.sh`), frontend **71 suites / 490 tests**, `tsc --noEmit`
clean. ESLint not run (broken install, known).

Commits on `main`: `fd821f6` `5b9912e` `c35f0d4` `1ac42ee` `c47083e`.

## Retro

**Went well**
- The metrics dump (height / CTA count / overflow per route) found the two
  biggest problems before a single screenshot was opened — 6,941px and
  `overflowX: true` are hard to argue with. Keep leading with numbers.
- Splitting D1 to a `doer` in a worktree while doing D2/D3 here worked: zero
  merge conflicts, one ff-merge, and the agent surfaced a real caveat
  (`uploaded_videos` LIMIT-10 vs the history's `total` as the empty-state signal).
- The persona lens surfaced a privacy bug (email to visitors) that a feature
  walk would have skipped past.

**Didn't**
- The brief quoted a stale test baseline (61/411; it was 70/483) and the wrong
  `localStorage` recipe — both cost the agent a detour. Check `jest.setup.js`
  and the current suite count before briefing.
- `rtk` rewrote jest output to a 20-byte line even through a file redirect.
  Only `node node_modules/jest/bin/jest.js --json --outputFile=…` is reliable.
  `tools/run_ci_tests.sh` needs `PYTHON=venv/bin/python` (no bare `python`
  on this machine).
- Playwright MCP only reads files under the repo or `.playwright-mcp/` — the
  scratchpad copy of the walk script was rejected.

**Change next time**
- Re-walk only the persona flows touched by the previous iteration plus one
  new flow (an actual upload, with a fixture video) — the static routes are
  now well covered.
- Pull B5/B6/B14 (result-page cleanups) as a single pass; they share
  `VideoPlayer.tsx`.
- Consider a 10-second "sanity" check in CI that renders `/profile/:id` under
  390px and asserts `scrollHeight < 3000` — the clutter regression class is
  cheap to catch mechanically.
