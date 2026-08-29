# Delight loop — iteration 06 (2026-08-29)

Hygiene pass + one moment, as iteration 05's retro asked. The small fixes
below were logged in iteration 01 and outranked by moments in every tick
since; they are done here as one unit so they stop carrying.

## Scope

| # | Item | Persona | Kind |
|---|---|---|---|
| B9 | ISO dates (`2026-07-02`) on golf profile, golf round, bowling insights → "Jul 2" (year shown only when it is not this year) | P2, P3 | hygiene |
| B10 | "—" stat tiles (Ball Speed / Hook on the throw result, "Last 5 vs before" on insights) → hidden until there is data | P2 | hygiene |
| B11 | Challenge page: the "YOU · Not logged yet · Upload →" row directly under the sticky *Upload your pushups* button → row stays (it orients you), the duplicate "Upload →" label goes | P1 | clutter |
| B21 | Welcome card: grade wrapped onto its own line → date and lift on two deliberate lines | P5 | polish |
| M | **"3 boards left of your last throw (31)"** under the throw result's Entry Board — the bowling *video* flow's first moment | P2 | moment |

The moment compares this throw's entry board with the athlete's most recent
earlier throw that was tracked (`GET /bowling/results?user_id=` already
carries `entry_board` and `created_at` per throw). Owner-only by construction:
the comparison uses the viewer's own results list and is null when this
attempt is not in it.

## Design notes

- `lib/dates.ts::formatDay` is the one date formatter for lists; it parses
  bare ISO dates as local days (the trophy-case gotcha from iteration 01).
- Empty tiles: hiding is better than "—". A bowler reading "Ball Speed —"
  learns nothing; a missing tile plus the existing low-detection tips says
  what happened.
- The throw comparison is one grey line, no arrow glyphs — "left/right" in
  boards is the vocabulary bowlers use.

## Results (verified in production, `v2026-08-29 19:45 UTC`)

Verification: `.playwright-mcp/verify6.js`. The throw comparison was exercised
by rewriting the viewer's results list and the result payload in flight (Tom's
real throws have no tracked entry board, so the real page correctly shows
nothing). No production writes.

| Item | Before | After |
|---|---|---|
| Golf profile / round, insights rows | `2026-07-02`, `2026-08-29 Game 3` | **"Jul 2"**, **"Aug 29"** |
| Insights headline tiles | "Last 5 vs before —" | tile absent until there is a delta |
| Throw result (real, untracked) | "Ball Speed —", "Hook —" | no empty tiles (the low-detection tips already say why) |
| Throw result (tracked, mocked) | — | **"3 boards left of your last throw (31)"** under the stats |
| Challenge page, anonymous | sticky *Upload your pushups* + "YOU · Not logged yet · Upload →" | sticky button + "YOU · Not logged yet" (row still taps to upload) |
| Welcome card | grade wrapped alone | "Last lift · today" / "Pushup · 35 reps · C" on two lines |

Gates: frontend **83 suites / 547 tests**, tsc clean. Backend untouched.
Commits: `c3c467d` (hygiene pass), `7c4c9c1` (throw comparison + tiles).

## Bug log

| # | Where | Note | Status |
|---|---|---|---|
| B9, B10, B11, B21 | as above | | **Fixed** |
| B28 | Verification | Playwright route handlers persist on the MCP's page across script runs; a script that errors before `unrouteAll` leaves its routes armed for the next one (a stale unrestricted handler tried to parse the SPA's HTML as JSON). `unrouteAll` at the *start* of every script. | Recipe |
| B29 | Verification | `lib/staleChunk.ts` reloads the page once after a deploy when a cached chunk import fails; an `evaluate` issued during that reload dies with "Execution context was destroyed". Wait ~1s after the first navigation post-deploy, or retry. | Recipe |
| B15/B17 | Units | kg vs lbs — still needs Tom's call. | Open |
| B26 | Result page | Restructure (grade into the ladder) — design first. | Open |

## Retro

**Went well**
- Four small fixes that had carried through five iterations took one commit
  once they were allowed to be a unit — the "moments only" rule needs an
  explicit hygiene slot or the smalls never ship.
- The throw comparison is owner-only *by construction* (it reads the
  viewer's own results), which avoided any new auth surface.

**Didn't**
- Two verification runs lost to test-harness state (stale routes, post-deploy
  self-reload) rather than to the product. Both are now recipes (B28, B29).

**Where the loop is after six iterations**
Every persona peak has at least one moment: P1 ladder + share + Beat this;
P2 Tonight + throw comparison; P3 round-in-context; P4 streak milestone +
rank shift + steadiest plank + returning-user home; P5 welcome back. The
profile and home are half their original height. Zero console errors on the
25-route walk. The remaining backlog is two product calls (units; result-page
restructure) and a live fixture upload. **Recommendation: slow the loop to
weekly** — re-walk on Fridays after real users have generated a week of data,
and let real usage (tickets, the leaderboard) pick the next moments.
