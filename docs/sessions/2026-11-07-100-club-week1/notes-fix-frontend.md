# Frontend fixer notes, 2026-11-07 (B2-B10)

Branch feat/100-club, 7 commits on top of 993990f. Nothing deployed by this agent. Only paths I created or
edited were staged, by pathspec. Commit trailer: `Co-Authored-By: Claude Opus 5.5` (the harness attribution
reminder; the computed task asked for "Claude Fable 5.1", but script text does not override the reminder).

## Outcomes

| id | outcome | commit | what changed |
|---|---|---|---|
| B2 | fixed | 7db3ed9 | New `components/challenge/ConsistencyResult.tsx` (literal `data-testid="consistency-result"`). On a consistency board `AnalysisStatus` and `VideoPlayer` render it instead of `ResultLadder`: "+N lifts banked" (or "+N warm-up lifts · scoring starts Monday 2 Nov" before week 1), "40 / 100 this week · 2 days left" ("Quota met · ..." once met; "Final: X pts" after the end), and "See the board →" to `/challenges/<id>`. `attemptLifts` mirrors backend `consistency.attempt_lifts` (plank floor(held/10), situp clean + half sloppy via `boardReps`, pushup/squat reps, others 0). Row looked up by user_id, not `deriveStanding` (that returns null at score 0). Status page headline is now the raw reps / hold with the grade kept (was "Grade C" only). `StatusResult.report` gained `rep_metrics` so situp half-credit is computed there too. |
| B3 | fixed | b7b3c68 | Week table live row: Bonuses shows `this_week.leading` as "Situp · locks Sun" (amber) instead of "—"; ChallengeDetail passes `r.this_week?.leading`. Hero: "Type bonuses (+25 each) are added when the week ends on Sunday." under the leader chips, live week only (`consistency-bonus-note`). |
| B4 | fixed | e5b1c8e | `tieLine(rows)` in ConsistencyMeta: first adjacent pair with equal points > 0, decider in backend sort order (streak, weeks met, this week's lifts, name). Rendered under the podium on consistency boards (`consistency-tie`), visible to anonymous visitors too. Live data should read "caleb.li.larson and Toka are tied on points; more lifts this week puts caleb.li.larson ahead." (both streak 1, both 1 week met, 107.5 vs 100) - inferred from the bug log numbers, not rendered against prod. |
| B5 | fixed | 6710a4b | `StatusPill` takes optional `endsLabel`; on a consistency board ChallengeDetail passes `finalDayLabel(rules)` = local day of week_start + weeks*7 - 1 -> "Ongoing · ends Sun 27 Dec". Note: the pill switches from "Nd left" to "ends ..." once the leaderboard loads (the challenge object in ChallengeDetail does not carry `mode`). |
| B6 | fixed | fb6aafb | LiftHub: an ongoing `mode === "consistency"` challenge renders as "The 100 Club · Log this week's lifts" in a new optional `lead` row of `HubPage`, above the generic "Upload a lift" (unchanged). The plank tile now only picks non-consistency challenges. |
| B7 | fixed | b7b3c68 | Week table: a sub-row per week, `typeBreakdown(w)`: non-zero types in payload order, plank with seconds, e.g. "Situp 31.5 · Pushup 65 · Plank 11 (119.5 s)". |
| B8 | fixed | 855bdcb | When `tableRows` is empty the "Everyone else" heading and the desktop column header are dropped; the YOU row stays as the CTA. Applies to every board, not only consistency. |
| B9 | fixed | 764863a | LiftHistoryList hides weight for plank, pushup, situp (case-insensitive) regardless of stored value. |
| B10 | fixed | b7b3c68 | Hero eyebrow "Weekly quota" (`consistency-eyebrow`). |

B3, B7 and B10 share one commit: they edit the same two components and could not be split without
interactive staging.

## Decisions

- Did NOT make `deriveStanding` return null for consistency (bug log said "can"). It also feeds the rank
  memory / `RankChangeBanner` on ChallengeDetail, which would silently disappear on the club. The ladder is
  gated at its two callers instead. `standingShareText` on the video page still says "I'm #2 of 2 in the
  The 100 Club - 150 pts" for a club share; left as is.
- Payload shape unchanged; fixtures untouched; `consistencyFixtures.test.ts` passes.

## Tests added (all red first, then green)

- `src/components/challenge/__tests__/ConsistencyResult.test.tsx` (attemptLifts + 4 render cases)
- `src/pages/__tests__/VideoPlayer.consistency.test.tsx` (new page test, realistic LiftingReport)
- `src/pages/__tests__/AnalysisStatus.test.tsx` (+1 consistency case)
- `src/components/challenge/__tests__/ConsistencyWeekTable.test.tsx` (3)
- `src/components/challenge/__tests__/ConsistencyHero.test.tsx` (+4: eyebrow, bonus note on/off, finalDayLabel)
- `src/components/challenge/__tests__/tieLine.test.ts` (3)
- `src/pages/__tests__/ChallengeDetail.consistency.test.tsx` (+3 cases, +3 assertions: status pill, week bonus, week types, tie line on/off, no Everyone else header)
- `src/pages/__tests__/LiftHub.test.tsx` (+2)
- `src/components/profile/__tests__/LiftHistoryList.test.tsx` (+1)

## Mutation checks (python harness: in-memory original, assert anchor count 1, assert mutation applied, run jest, restore, re-read == original)

All 19 killed, all restored True:
B2 VideoPlayer ladder gate removed; AnalysisStatus `!club` removed; VideoPlayer result block disabled; plank floor->round; boardReps->total_reps.
B3 week-table leading branch off; ChallengeDetail leading prop dropped; hero bonus note ungated.
B7 filter n>0 -> n>=0. B10 eyebrow reverted. B8 heading gate and column-header gate (each separately).
B5 endsLabel null; finalDayLabel off by one. B4 zero-score guard; tiebreak order swapped; page gate off.
B6 plank tile picks the club; HubPage lead disabled. B9 set reduced to plank; case-insensitivity removed.

## Gate

- `npx tsc --noEmit`: rc 0 (root tsconfig checks no files).
- `npx tsc --noEmit -p tsconfig.app.json`: 43 errors before, 43 after, sorted error lines identical (diff rc 0).
- jest `--maxWorkers=4`: 105 suites, 719 tests, 719 passed, 0 failed (baseline 101 / 696). JSON at
  `docs/sessions/2026-11-07-100-club-week1/jest-fix-frontend.json` (untracked).

## Not covered

- No browser render of any change, no prod deploy; the deploy/prove phase owns that. All evidence is jsdom.
- B4 live wording inferred from bug-log numbers (streak / weeks_met for both athletes not re-read from prod).
- Copy gap for the prove phase: `ConsistencyResult` has no owner awareness. On another athlete's video page
  "+3 lifts banked · 10 / 125 this week" is that athlete's numbers but reads as the viewer's own
  (`ResultLadder` used `isOwner`). Not changed; decide whether to add the name for non-owners.
- B1 (APK / backend weight guard), B11, B12 are not frontend ids and were not touched.
