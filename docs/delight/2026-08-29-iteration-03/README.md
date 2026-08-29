# Delight loop — iteration 03 (2026-08-29)

Moment-first (rule from iteration 02). Personas unchanged. This tick takes the
three peaks that iteration 02 left on the table: the *return* (P5), the *night*
(P2) and the *share* (P1).

## Walkthrough of the peaks (build `v2026-08-29 16:40 UTC`, 390×844)

| Peak | Persona | What happens today | Screenshot |
|---|---|---|---|
| `/find-profile` success | P5 Sam | Enter email → `navigate('/profile/:id')`. The one moment the app knows *who came back* is spent on a redirect; no name, no "last time you…". | `before-find-profile.jpeg` (form) |
| Bowling sheet → confirm | P2 Marcus | "This is me" → `/bowling/insights/:id`. Insights is a good page but timeless: tonight's three games are just three rows, indistinguishable from any other night. No "+7 vs your average", no "best game since". | `before-insights.jpeg` |
| Result → Share | P1 Priya | Share copies a bare short link ("Short link copied!"). Pasted into a group chat it is a URL with no words; the unfurl card carries the grade but not the rank the ladder now shows. | `before-result-share.jpeg` |

Data check: `GET /users/by-email/:email` → `{id, name}`; `GET /users/:id/lifts?limit=1`
gives the last lift with `lift_type`, `grade`, `total_reps`, `hold_s`, `weight`,
`created_at`. `GET /bowling/games?user_id=` gives every game with `sheet_id`,
`played_on`, `total_score` — enough to isolate one night and compare it with
every other. The ladder's `Standing` already carries rank/field/best for the
share copy. `navigator.share` exists on iOS Safari and Android Chrome.

## Ideas (moment-shaped)

1. **Welcome back** on `/find-profile` success: name, avatar, "Last lift · 4 months ago · Bench press · 80kg · D", then *Open my profile* / *Upload a new lift*.
2. **Tonight** card at the top of insights after a confirm: hero average, ▲/▼ vs every other night, "202 high — your best game since Jul 10 / your best game yet / first night on the books".
3. **Share with words**: native share sheet with "I'm #2 of 5 in the Pushup challenge — 35 reps. Beat me:" + link; clipboard gets words + link where there is no sheet.
4. Streak milestone toast on home (2 / 4 / 8 weeks).
5. Golf: "your best round at Birch Hill" on the handicap card.
6. Challenge page: "you moved up" banner when rank improved since last visit (localStorage).

## Critical review

| # | Reach | Moment | Effort | Verdict |
|---|---|---|---|---|
| 1 | every returning user without a session | recognition — the app knows you | small (one page, one fetch) | **BUILD** |
| 2 | every league bowler, right after the confirm | progress — tonight vs. you | small-medium (pure lib + card + `?sheet=`) | **BUILD** |
| 3 | every uploader who shares; the viral loop | surprise — the message writes itself | small (share helper + copy builder) | **BUILD** |
| 4 | daily users | low-medium, toast fatigue | small | backlog |
| 5 | golfers | medium | medium (needs course-level history) | next |
| 6 | challengers | medium | medium (client state) | next |

Opportunistic bug fix (not counted): **B6** — Re-analyze becomes owner-only.

## Design

- **Welcome back**: the form is *replaced* by the card, not stacked above it.
  Avatar, "Welcome back, {first name}", one grey line with the last lift in the
  same vocabulary the profile uses (`lib/welcome.ts`: `sinceCopy`,
  `lastLiftCopy`), then two actions. No lifts → "Your profile is ready."
- **Tonight**: same settle-in motion as the completion reveal so the two
  "your number" moments rhyme. Hero = tonight's average (bowlers think in
  averages), delta pill uses green only when positive, high-game line ends
  with the strongest true statement (`since <date>` > `best yet` > `first
  night`). Only rendered when the URL carries `?sheet=` — it is a moment, not
  a fixture; a reload of `/bowling/insights/me` shows the normal page.
- **Share**: words first, link second, one sentence, in the athlete's own
  units, ending in a dare. Owner: "Beat me:" (leader: "Take my spot:");
  visitor: "Can you beat it?". Native sheet on phones; on desktop the
  clipboard gets words + link and the toast shows the sentence so the user
  sees what they are about to paste.

## Decisions

**D1** — `FindProfilePage` keeps the lookup, then fetches the last lift and
renders `WelcomeBack`; `localStorage.userId` is still set on success.
**D2** — `BowlingSheetReview` navigates to `/bowling/insights/:id?sheet=<id>`;
`BowlingInsights` fetches games (limit 100), `summarizeNight` (pure) → `NightCard`
above the tiles.
**D3** — `lib/share.ts::shareResult(meta, text)` (native sheet → clipboard);
`lib/standing.ts::standingShareText`; `VideoPlayer.handleShare` uses both when a
standing exists and falls back to today's link-only behaviour otherwise.

## Results (verified in production, build `v2026-08-29 17:10 UTC`)

Verification: `.playwright-mcp/verify3.js` — the by-email lookup was intercepted
(`page.route`) so no real address was typed; the last-lift fetch, the games
fetch and the short-link POST were real.

| Moment | Before | After (prod, real data) |
|---|---|---|
| `/find-profile` success | redirect to profile | **"Welcome back, Toka" · "Last lift · today · Pushup · 35 reps · C"** · Open my profile / Upload a new lift; `localStorage.userId` set |
| Insights after confirm | timeless page | **"TONIGHT · AUG 29 — 169 avg over 3 games — 202 high — first night on the books"** above the tiles; plain page without `?sheet=` |
| Share (owner) | bare link copied | **"I'm #2 of 5 in the Pushup challenge — 35 reps. Beat me: https://…/s/tDgBPm"** — native sheet on phones, clipboard + toast elsewhere |
| Share (visitor) | bare link | **"Toka is #2 of 5 in the Pushup challenge — 35 reps. Can you beat it? https://…/s/S0whju"** |
| Re-analyze (B6) | offered to everyone | owner only (verified: present with session, absent anonymous) |

Gates: frontend **77 suites / 523 tests** (+17: welcome 3, bowlingNight 4,
NightCard 2, share 3, standing 2, FindProfilePage 2, BowlingInsights 1),
`tsc --noEmit` clean. Backend untouched.

Commits: `d2dc924` (welcome back), `7b40062` (Tonight card + `?sheet=`),
`aa34aa1` (share with words + owner-only Re-analyze).

## Bug log (new this iteration; earlier ones remain as listed in iterations 01–02)

| # | Where | Bug / note | Status |
|---|---|---|---|
| B6 | Result page | Re-analyze exposed to every visitor. | **Fixed** (`aa34aa1`) |
| B19 | Insights, first night | With a single night on record, the Tonight card and the Average / High game tiles below it show the same two numbers — duplicate information for exactly the user who just uploaded their first sheet. | Open — hide the duplicated tiles while a Tonight card is showing, or fold Tonight into the tile row |
| B20 | Share, desktop Chromium/macOS | `navigator.share` exists on desktop Chrome for macOS, so the OS share sheet opens on a laptop too; if it throws anything other than `AbortError` we fall back to the clipboard, so nothing is lost — but the desktop experience is a sheet rather than a copy. | Open — consider gating the sheet on a coarse pointer / touch |
| B21 | Welcome back | "Last lift · today · Pushup · 35 reps · C" wraps the grade onto its own line at 390px because the avatar takes the left column. | Open — small; put the grade in a pill or shorten the date |

## Retro

**Went well**
- All three picks are moments, all three are tiny (~400 lines including tests),
  and each reuses a derivation that already existed (`Standing`,
  `BowlingGameRow`, the lifts endpoint). Small moments on top of real data beat
  big features.
- Route interception again did the heavy lifting in verification: no real
  email typed, no fixture upload needed.
- The share sentence is the first thing in the app that a *third party* reads
  before they ever open it — cheapest possible growth loop, one function.

**Didn't**
- The clipboard shim was installed with `addInitScript` after the page had
  already loaded once; and desktop Chromium turned out to implement
  `navigator.share`, which sent the first verification down the sheet path.
  Lost one round. Stub `navigator.share` explicitly when testing the copy path.
- Still no live end-to-end upload (waiting → reveal seen only via mocks). Carry.

**Change next time**
- Iteration 04 candidates: B19 (fold Tonight into the tiles on a first night —
  the clutter lens applied to my own feature), the streak milestone (P4),
  "you moved up" on the challenge page (P1/P4 return visits), and the kg/lbs
  decision (B15/B17) which now leaks into the share sentence for weight
  challenges ("— 115lbs").
- Do the live fixture upload on a throwaway account and delete the attempt
  afterwards (`DELETE /attempts/:id` exists).
