<!-- Moved verbatim from CLAUDE.md on 2026-09-19; CLAUDE.md keeps a pointer. -->
# Hall of Champions (shipped 2026-08-28)

`/champions` replaced the old mock-data `/leaderboard` (now a redirect; `pages/Leaderboard.tsx` deleted). Lift hub + `NAV_LINKS` point here. Reads `GET /champions` — no new tables.

- **Backend:** `services/champions.py::shape_champions` now also emits `runners_up` (ranks 2–3 with a valued score), `field_size`, `margin` (winner − runner-up, null when unopposed), `winner_attempts`, `won_on` — all derived from the existing leaderboard payload. Frontend treats them as optional.
- **Frontend:** `lib/championStats.ts` (pure, fixture-tested: `championTally`, `dynastyLabel` 2=Back-to-back / 3=Three-peat / N×, `ordinalWin`, `marginCopy` with a per-metric "photo finish" threshold 5s/2.5kg/1rep, `reignDays`, `groupByYear`). `components/champions/ChampionHero` (newest win: laurel conic ring + floating crown + shimmer name — `laurel-ring`/`crown-float`/`hall-shimmer` keyframes in `index.css`, reduced-motion aware; field/attempts/reign tiles; Watch / profile / Share via `lib/share.ts`), `ChampionCard` (wall of fame, "Nth title" pill, "You" pill), `NextToBeCrowned` (ongoing challenges → current leader + days left via `getChallengeLeaderboard`). Viewer who is a champion sees "Your reign" + `ChampionConfetti` keyed `("hall", userId)`.
- `formatChampionScore` now handles `reps`; `Champion.metric` is `ChampionMetric` (time|weight|reps).
- Suite at ship: frontend 61 suites / 411 tests; backend gate 174.
