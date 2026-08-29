# Delight loop — iteration 04 (2026-08-29)

Moment-first. Personas unchanged. This tick covers the two personas that have
had the least attention — P3 Dana (golf) and P4 Tom on a *return* visit — plus
the return-visit version of P1's challenge page.

## Walkthrough of the peaks (build `v2026-08-29 17:10 UTC`, 390×844)

| Peak | Persona | What happens today |
|---|---|---|
| Challenge page, return visit | P1 / P4 | The "Your standing" card shows rank and best, exactly as it did last time. If someone passed you overnight, or you passed them, nothing marks it — the page has no memory of your previous visit. |
| Home, streak card | P4 | "Your streak · 1 week". At week 2, 4, 8 the card looks identical to week 1; the habit forming is never named. |
| Golf confirm | P3 | `HandicapResultCard`: hero index + delta. Good — but it says nothing about *this round*: was it your best at this course? your best 18 ever? Every round in the list is a Birch Hill round; none of them says so. |
| Insights, first night (B19) | P2 | The Tonight card and the Average/High tiles under it show the same numbers. |

Data check: standing (rank, best, gap, nextName) is already derived on the
challenge page → a `rank:<challenge>:<user>` snapshot in `localStorage` is enough
to detect a shift between visits. `computeStreak` already yields `weeks`.
`GET /golf/rounds?user_id=` returns `holes`, `total_score` and nested `course`
per round → best-at-course / best-ever / first-at-course are computable on the
confirm screen with one extra read.

## Ideas (moment-shaped)

1. **You moved up / you slipped** banner above "Your standing", with "4 reps to pass rob and take it back" on a slip.
2. **Streak milestone** — the streak card's title becomes the line ("Four weeks. A month of showing up.") once, at 2 / 4 / 8 / 12 / 26 / 52 weeks, with an orange ring for that visit.
3. **This round in context** — a pill under the handicap index: "Your best 18 yet" / "Your best at Birch Hill" / "First round at Birch Hill".
4. Bowling: "3 nights in a row over 170" (needs session series).
5. Result page: "Your steadiest plank yet" (needs per-attempt stdev history).

## Critical review

| # | Reach | Moment | Effort | Verdict |
|---|---|---|---|---|
| 1 | every challenger who comes back | recognition of *change* — the most motivating kind | small (localStorage snapshot + banner) | **BUILD** |
| 2 | every weekly user, six times a year | progress named at the moment it becomes true | small | **BUILD** |
| 3 | every golfer, every round | recognition on the benchmark screen | small (pure lib + one prop + one read) | **BUILD** |
| 4, 5 | narrower | medium | medium | next |

Opportunistic: **B19** fixed (tiles that duplicate the Tonight card are dropped
on a first night).

## Design

- **Rank shift**: one line, `role="status"`, green only when up; a slip is
  quiet grey and ends with the way back ("· 4 reps to pass rob and take it
  back"). Computed once per page load, then the snapshot is overwritten — so
  the banner shows exactly once per change, and a reload shows nothing.
- **Milestone**: no toast, no confetti — the card itself changes for one
  visit: title becomes the sentence, border warms to orange. Celebrated
  milestones are remembered per user so it fires once per threshold.
- **Round in context**: a success-coloured pill under the index using the
  Fairway tokens the card already uses. Strongest true statement wins
  (best-ever > best-at-course > first-at-course); ties say nothing; 9-hole
  and 18-hole rounds never compare.

## Decisions

**D1** — `lib/rankMemory.ts` (`readRank`/`writeRank`/`rankChange`),
`components/challenge/RankChangeBanner.tsx`, wired in `ChallengeDetail` above
`StandingCard`.
**D2** — `lib/streak.ts` gains `STREAK_MILESTONES`, `milestoneReached`,
`milestoneCopy`; `StreakCard` reads/writes `streak-milestone:<userId>`.
**D3** — `lib/golfBest.ts` (`roundHighlight`, `highlightCopy`);
`HandicapResultCard` gains `highlight`; `GolfReview` fetches rounds once on
confirm.

## Results (verified in production, build `v2026-08-29 17:47 UTC`; banner trim in `v2026-08-29 17:52 UTC`)

Verification: `.playwright-mcp/verify4.js` plus an interactive golf run. All
transient states were produced without writing to production: the rank
snapshot was seeded in `localStorage`, the activity feed was rewritten in
flight to four consecutive weeks, and the golf confirm's `PUT …/scores` was
intercepted (the round GET was patched to carry a tee so the button enabled).
A first golf attempt that missed the interception was rejected by the backend
with a 400 and wrote nothing (handicap snapshot still dated 2026-07-02).

| Moment | Before | After (prod) |
|---|---|---|
| Challenge page, first visit | — | no banner; snapshot `{rank:2,best:35}` stored |
| Seeded at #5 | — | **"▲ You moved up — #5 → #2 since your last visit"** |
| Seeded at #1 | — | **"▼ You slipped — #1 → #2 since your last visit"** (the "4 reps to pass rob" clause was trimmed in `01375e1` because the standing card beneath already says it) |
| Reload | — | quiet |
| Home, 4-week streak | "Your streak" | **"🔥 Four weeks. A month of showing up."**, orange ring; `streak-milestone:<id> = 4`; quiet on reload |
| Golf confirm | index + delta | index + delta + **"First round at Birch Hill"** |
| Insights, first night (B19) | Tonight + duplicate tiles | Tonight + Games / Last-5 tiles only |

Gates: frontend **80 suites / 537 tests** (+14: rankMemory 3, golfBest 4,
streak 2, RankChangeBanner 2, StreakCard 2, HandicapResultCard 1),
`tsc --noEmit` clean. Backend untouched.

Commits: `2dbe0b0` (rank shift), `ba08807` (milestone), `277a342` (round in
context), `7b0cda3` (B19), `01375e1` (banner trim).

## Bug log (new this iteration)

| # | Where | Bug / note | Status |
|---|---|---|---|
| B19 | Insights, first night | Tonight card duplicated the Average/High tiles. | **Fixed** (`7b0cda3`) |
| B22 | Challenge page | First draft of the slip banner repeated the standing card's "to pass rob" line one row above it. | **Fixed** (`01375e1`) |
| B23 | Golf review | A round whose tee was never resolved (`needs_tee`) keeps *Confirm and save* disabled with no visible reason — the tee picker is behind a small "Change" link on the course header. Found while trying to confirm Tom's Birch Hill round. | Open — surface "Pick a tee to confirm" next to the disabled button |
| B24 | Rank memory | The snapshot is per browser; a rank change seen on the phone is announced again on the laptop. Accepted — it is a per-device moment, not a notification system. | Won't fix |

## Retro

**Went well**
- Three moments for three under-served personas (return visitor, weekly
  regular, golfer), all client-side, all under ~120 lines each, all verified in
  prod without a single production write.
- Interception got sharper: patching a GET to enable a disabled button, then
  swallowing the PUT, is a reusable recipe for verifying any confirm screen.
- Applying the clutter lens to my own banner before shipping the polish (B22)
  is the loop working as intended.

**Didn't**
- Playwright's `*` glob does not cross `/`; the first golf run hit the real
  backend. It was rejected (400), but only because the injected tee id took a
  path the backend refused — luck, not design. **Use a function matcher for
  route interception whenever a write is involved, and prove the write was
  blocked before reading results.**
- The existing StreakCard tests stub `localStorage.getItem` with one value for
  every key; adding a second key to the component broke them. Key-aware stubs
  from the start.

**Change next time**
- Four iterations in, the obvious peaks are covered. Iteration 05 should
  re-walk *all five* persona flows on the new build (the iteration-01 recipe)
  and score them again — the ladder, welcome, tonight, milestone and banner
  now coexist and may crowd each other; the clutter lens applies to the
  additions as much as to the original.
- Still open, needs a product call from Tom: kg vs lbs (B15/B17) — it now
  shows in the share sentence for weight challenges.
- B23 is a small fix with real friction (a disabled button with no reason).
