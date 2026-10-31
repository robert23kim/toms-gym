# 100 Club — frontend doer notes (2026-10-31)

## Gates
- `npx tsc --noEmit`: exit 0. Stricter `tsc -p tsconfig.app.json`: the same 20 errors in the same 11 files as HEAD
  (I checked HEAD from a `git archive` copy), so none are new.
- Full jest (`--maxWorkers=4`, results in `jest-frontend.json`): **682 passed, 0 failed, 98 suites**. Baseline was 634, so 48 tests are new.
- Mutation run: **35/35 guards failed when broken.** Each mutated file was restored from an in-memory copy and asserted byte-identical.

## What was built (frontend only)
- `lib/types.ts`
  - `ChallengeMetric` gains `"consistency"`.
  - New types: `ConsistencyRules`, `ConsistencyBlock`, `ConsistencyLeader`, `ConsistencyStatus`, `ConsistencyThisWeek`, `ConsistencyWeek`.
  - The row gains optional `streak`, `best_streak`, `weeks_met`, `this_week`, `weeks`, `warmup_lifts`.
  - `ChallengeLeaderboard.consistency?`, plus `Competition.mode?` and `rules?`.
- `lib/api.ts`
  - `transformCompetitionData` fills `mode` and `rules`. It reads flattened fields, or else parses the description JSON after ` - `.
  - `ChampionMetric` gains `"consistency"`, and `formatChampionScore` returns `325 pts` (one decimal on a half).
- `lib/championStats.ts`: `PHOTO_FINISH.consistency = 25`. Required by the `Record` type; this is a guess.
- `components/challenge/metric.ts`
  - POINTS / pts / integer-or-.5 / "Log this week's lifts".
  - `scoringNote` takes an optional third arg `rules` and returns a one-line rules sentence built from the rules, with defaults.
- `lib/standing.ts`
  - `ctaLabelFor` always returns "Log this week's lifts" on consistency.
  - `formatWithUnit` returns `N pts`.
  - `attemptScore` returns null on consistency, so the result ladder never shows a misleading "below your best".
- New `components/challenge/ConsistencyHero.tsx` (`data-testid="consistency-hero"`)
  - Week line: "Week 3 of 8 · 4 days left" / "Starts Monday 2 Nov" / "Ended". The date is formatted by hand from `week_start + T00:00:00`, so locale does not change it.
  - SVG ring `42 / 150`, 🔥 N-week streak (hidden at 0), "N video(s) still analysing", and a warm-up line before the start.
  - Leader chips marked LEADING, in lift-type order, shown only while live. Plank amounts show in seconds.
  - Anonymous visitors and non-entrants get the week line and chips but no ring.
- New `components/challenge/ConsistencyMeta.tsx`: `thisWeekText` ("42/150 this week", plus " · N warm-up" on a 0-point row), `StreakFlame`, `hasWeeks`.
- New `components/challenge/ConsistencyWeekTable.tsx`: Week | Quota | Lifts | Met | Bonuses | Points, oldest first. The live week is tagged "now" and shows "…" in the Met column.
- `LeaderboardRow` / `YouRow` / `Podium`: pts, a flame with the streak, and `42/150 this week`. The toggle chip reads "Weeks" instead of "N attempts" and shows when the row has any week.
- `pages/ChallengeDetail.tsx`
  - The hero renders before the leaderboard IIFE, so it also shows in the all-zero pre-start state. The viewer row comes from `rows`, not `deriveStanding`, so a 0-point viewer still gets a ring.
  - On consistency boards:
    - zero-point rows still list (table = every row not on the podium), and the "No entries yet" early return is skipped when rows exist;
    - StandingCard is hidden;
    - the expand panel is the week table, so AttemptHistory is not fetched;
    - the weight input takes `min=0`, Squat defaults to 0, and the hint reads "0 for air squats.".
  - `React.Fragment` was changed to a named `Fragment`, because ts-jest gives a default `React` of undefined and the page had never been rendered under jest. No behaviour change in the browser.
  - Scope re-read: `consistencyBlock`, `viewerBoardRow` and `liveWeekIndex` are defined at component scope after the early returns. The IIFE and the upload form both sit inside the later return. `handleLiftTypeChange` reads the `leaderboard` state declared at the top.
- `lib/prompts.ts`
  - `consistencyPill(board, userId)` returns `42 / 150 · 4 days left`, `1 day left`, `Starts Mon` before the start, and null after the end, for no user, or for a non-entrant.
  - `buildPrompts(open, pills = {})`: a consistency challenge is always a link row to `/challenges/<id>`.
- `pages/Index.tsx`: when a `userId` is saved, it makes one `getChallengeLeaderboard` call per ongoing `mode === "consistency"` challenge. The call is non-fatal; anonymous visitors make no call.
- `components/challenge/ResultLadder.tsx`: on consistency boards "Beat this →" links to `/challenges/<id>` instead of the bare `/upload` route. That route's `UploadVideo` page has no Plank and no per-challenge filtering.
- Fixture: `src/__fixtures__/consistencyLeaderboard.ts` (`consistencyLeaderboard`, plus derived `upcoming…` and `ended…` variants).

## Tests added
- New files:
  - `components/challenge/__tests__/ConsistencyHero.test.tsx` (11)
  - `components/challenge/__tests__/ConsistencyRows.test.tsx` (10)
  - `pages/__tests__/ChallengeDetail.consistency.test.tsx` (4: hero, rules, rows and week table; anonymous; pre-start warm-up rows; upload form with four lifts, hidden weight and Squat 0)
  - `pages/__tests__/Index.consistency.test.tsx` (3)
  - `components/__tests__/ChampionSpotlight.consistency.test.tsx` (1)
  - `lib/__tests__/competitionMode.test.ts` (3)
- Additions to existing files: `metric.test.ts` (4), `prompts.test.ts` (7), `standing.test.ts` (2), `champions.test.ts` (1), `TrophyCase.test.tsx` (1), `HallOfChampions.test.tsx` (1).

## Mutation table (each guard broken, tests run, file restored; failures out of tests run)
| guard | failed |
|---|---|
| pill text `42 / 150` spacing | 3/15 |
| pill singular day | 1/12 |
| pill Starts Mon | 1/12 |
| hero upcoming "Starts Monday 2 Nov" | 1/11 |
| hero "Ended" | 1/11 |
| hero live days left | 2/11 |
| hero start-day bare-ISO UTC parse | 2/11 |
| hero anonymous → no ring | 1/11 |
| hero streak flame at 0 | 1/11 |
| hero pending line | 1/11 |
| hero leader chips live only | 1/11 |
| pts unit | 4/24 |
| points .5 half-credit | 1/14 |
| POINTS label | 1/14 |
| CTA label | 3/18 |
| ctaLabelFor short-circuit | 3/30 |
| row flame at 0 | 1/10 |
| row "this week" text | 5/10 |
| row warm-up note | 2/14 |
| week table bonuses | 2/10 |
| week table points column | 2/10 |
| week table met | 2/10 |
| detail panel = week table | 1/4 |
| detail zero-point rows listed | 2/4 |
| detail empty-state skip | 1/4 |
| detail hero render | 4/4 |
| detail StandingCard hidden | 1/4 |
| detail Squat min 0 | 1/4 |
| detail Squat default 0 | 1/4 |
| home anonymous → no fetch | 1/3 |
| home pill override | 2/15 |
| champion `pts` formatting | 4/15 |
| mode parsed from description | 1/3 |
| rows "Weeks" chip | 1/10 |
| podium this-week line | 1/10 |

## Browser check (local only)
Local vite dev ran with `VITE_API_URL` set to a fake host. Playwright served the fixture by intercepting requests, at 390 px and 1280 px, for these cases: Ana live, Ben live, anonymous, and pre-start. Results:
- Hero text matched every case, and the week table rendered.
- The upload select listed exactly Squat, Plank, Pushup and Situp. Picking Squat gave value 0 and min 0.
- The home pill read `42 / 150 · 4 days left` for Ana, `10 / 125 · 4 days left` for Ben and `Starts Mon` before the start. Anonymous visitors kept the plain `Situp` pill.
- Zero console errors and zero page errors.
- The phone week table overflowed at first (the Points column was clipped). I tightened the padding; it now fits (scrollWidth 324 = clientWidth 324).

Not covered: the real backend payload and production. The deploy and prod verification belong to a later stage.

## Contract guesses (please diff against the backend fixture)
- `attempt_id` and `clip_url` in the fixture are made-up strings (`att-a1-situp-1117`, …) and cannot match the backend's generated ids. Expect a diff there, and only there.
- The fixture omits `reps_total` and `clean_reps`, because the contract does not list them for consistency rows.
- On the pre-start board I assumed `weeks: []` and `this_week = {index 1, quota 100, …}` (that variant is frontend-only).
- Anonymous home row keeps the legacy `categories[0]` pill ("Situp"). I read "plain link row" as the unchanged existing row.
- Hero leader chips are hidden once the challenge has ended (the leaders are locked by then, not "leading").
- `championTitle` (the profile flair) shows no score at all, so it is unchanged. TrophyCase cards format through `formatChampionScore` and now read `325 pts`.
- PHOTO_FINISH margin for consistency is 25 pts (one type bonus).

## Open issues (not acted on)
- **Already broken before this work, all challenges:** on phones, `BottomTabBar` (`fixed bottom-0 z-50`) covers the lower half of ChallengeDetail's sticky upload CTA (`z-40`). Playwright's centre click is intercepted by the tab bar. A tap on the top ~24 px of the button works. Hand to a frontend doer.
- `/challenges/:id/upload` (`UploadVideo.tsx`) still hardcodes Squat/Bench/Deadlift/Pushup/Situp: no Plank, and no per-challenge filtering. On consistency boards I re-pointed ResultLadder's link away from it. `ChallengeVideos`' empty-state "Upload Video" link still points there.
- ChallengeDetail's inline form posts the hidden weight state (e.g. "60") for bodyweight lifts. This was already the case and does not affect consistency scoring.
- The pre-start payload shape is assumed (`weeks: []`). If the backend instead sends week 1 with zeros before `week_start`, the "Weeks" chip will show on every row before the start. That is harmless but untested against the real payload.
