# Delight loop — iteration 05 (2026-08-29)

Consolidation tick. Iterations 02–04 added five moments; this tick re-walks
all five persona flows on the new build (`v2026-08-29 17:52 UTC`) with the
iteration-01 script and applies the clutter lens to the additions themselves.

## Re-walk (390×844, 25 routes, zero console errors, no horizontal overflow)

| Screen | Iter 01 | Now | Note |
|---|---|---|---|
| Home (session) | 1945px / 13 CTAs | **1429 / 13** | pitch + demo gone for known users |
| Profile | 6941 / 54 | **2012 / 29** | one history |
| Result page (pushup) | 1540 / 11 | **1928 / 11** | +388px = the ladder; see below |
| Result page (plank) | 1401 / 11 | 1813 / 11 | +ladder; steadiness pack unchanged |
| Analysis complete | checkmark | h1 = **"35 reps"** | |
| `/challenges` | overflow | none | |
| Everything else | — | unchanged ±0px | hubs, uploads, find-profile, sign-in, insights, golf |

**Where the additions crowd each other — the result page.** Reading it top to
bottom as P1 (visitor from a share link): title → *Approved* pill → ladder
("Toka · 35 reps", Beat this) → grade card ("C · 35 reps detected · 75%") →
set breakdown ("Whole set · 35 reps") → Tips ("consider lighter weight", "5 of
35 reps flagged"). The number appears three times; the pill restates the
grade; the Tips card restates the breakdown and, for a bodyweight lift, gives
advice that cannot be followed.

## Ideas

1. Result page de-duplication: drop the status pill when a grade exists; for bodyweight lifts drop weight-based tips and hide the Tips card when nothing useful remains.
2. B23: golf review says *why* Confirm is disabled ("Pick a tee to confirm") with a link to the picker.
3. Share kindness: the last-placed athlete's sentence is "I just logged 12 reps … Beat me:", never "#7 of 7".
4. "Your steadiest plank yet" on plank results (per-attempt stdev is on the lifts endpoint).
5. Result page: fold the grade card into the ladder's "You" rung (bigger restructure).

## Critical review

| # | Reach | Effect | Effort | Verdict |
|---|---|---|---|---|
| 1 | every result view | −2 redundant blocks, corrects a wrong tip (B5) | small | **BUILD** |
| 2 | golfers with unresolved tees | a disabled button gets a reason and a way forward | small | **BUILD** |
| 3 | last-placed sharers | protects the share moment for the people most likely to feel it | tiny | **BUILD** |
| 4 | plank uploaders | a real moment, but needs a second fetch on an already-dense page | medium | next |
| 5 | all | best long-term shape of the page | medium-large | design first |

This tick is deliberately subtractive again: the moment rule says top-3 picks
must be moments, and #3 is one; #1 and #2 protect moments already shipped.
Recorded as a conscious exception, not a drift.

## Decisions

**D1** — Result page: the Approved/Failed/Successful pill is not rendered once
an analysis exists (it restated the grade or the steadiness score); for
bodyweight lifts, tips mentioning weight/load are filtered out and the Tips
card hides itself when nothing remains (closes **B5**).
**D2** — Share sentence: an athlete in last place (field > 2) shares "I just
logged 12.0s in the Summer plank challenge. Beat me:" — no rank.
**D3** — "Steadiest plank yet": `lib/steadiest.ts::steadiestYet(rows, attemptId,
stdev)` over the challenge's lifts (which carry `steadiness` per attempt); the
ladder gained an `extraPill` slot for a second recognition.
**Not a bug** — B23: GolfReview already says "Pick a tee ("Change tee") so we
can compute your differential" under the disabled button; iteration 04's check
only looked at the button. Struck from the backlog.

## Results (verified in production, `v2026-08-29 18:32 UTC`; status-pill polish in `v2026-08-29 18:37 UTC`)

| Screen | Before | After |
|---|---|---|
| Pushup result | "Approved" pill; Tips: "consider lighter weight", "5 of 35 reps flagged"; 1928px | no pill; Tips keeps only the flag count; **1844px** |
| Plank result (`370a028b`, stdev 2.39) | "Successful" pill | no pill (after polish); "New best · up from 115.4s"; no steadiest pill (correct — `d5528abc` is steadier) |
| Plank result (`d5528abc`, stdev 2.22) | — | **"▲ Steadiest plank yet"** |
| Share, last place | "I'm #7 of 7 …" | "I just logged … Beat me:" (unit-tested; no last-placed real account to drive) |

Gates: frontend **81 suites / 541 tests**, tsc clean. Backend untouched.
Commits: `77873b0` (share kindness), `3315d45` (steadiest), `a7193cc`
(de-dup + B5), `91a337a` (status pill after analysis).

## Bug log

| # | Where | Bug / note | Status |
|---|---|---|---|
| B5 | Pushup result | Weight-based tip on a bodyweight lift. | **Fixed** (`a7193cc`) — filtered in the UI; the engine still emits it |
| B23 | Golf review | Reported as "disabled with no reason" — the reason line exists. | **Not a bug** |
| B25 | Result page | Status pill ("Successful") survived on planks because they carry no letter grade. | **Fixed** (`91a337a`) |
| B26 | Result page | "35 reps" still appears three times (ladder rung, grade card, set breakdown header). Each has a job — the rung needs the number for the gap, the card needs it for the grade context, the breakdown says "whole set" — but a future restructure (fold the grade into the ladder's You rung) would get it to one. Design first; see idea 5. | Open — design |
| B27 | Re-walk | The iteration-01 walk is fully green now: 0 console errors, 0 overflow, every page ≤2012px. No regressions from four iterations of additions. | — |

## Retro

**Went well**
- A re-walk with numbers made the case for a consolidation tick in one
  table; nothing had regressed, and the one crowded screen was obvious.
- Checking the data before verifying (`steadiness` per attempt) turned a
  would-be false negative into a positive/negative pair — the pill shows on
  the steadier attempt and not on the other.
- Striking B23 rather than "fixing" it: the earlier verification's probe was
  too narrow, and reading the code before building found that.

**Didn't**
- The Tips filter is a regex on engine copy — brittle by construction. The
  right fix is in the engine's pushup tip set (other repo); noted in the log.
- Five iterations in, the profile/home/result screens are in good shape but
  the bowling *video* result ("Your Throw" with two "—" tiles, B10) and the
  ISO dates (B9) have carried through every tick untouched — small, and
  they've been outranked by moments every time. They should simply be done.

**Change next time**
- Iteration 06: the carried small fixes (B9 dates, B10 empty tiles, B11
  duplicate upload CTA, B21 wrap) as one hygiene pass, plus one moment for
  P2's *video* flow (the throw result has no "vs your last throw"). Then the
  loop has covered every peak at least once and can slow to a weekly cadence.
- Push `main` — 28 commits are local-only.
