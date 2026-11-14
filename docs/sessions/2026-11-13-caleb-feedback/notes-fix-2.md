# Fix notes, round 2 (R1)

## R1: type-bonus copy promised a lead at zero (fixed, ff08557 + 668529b)
- Cause: shared clause `typeBonusClause` in frontend/src/components/challenge/metric.ts read
  "+25 extra for each lift type where nobody logs more than you that week". Literally true when nobody, the viewer
  included, logged a type; backend/toms_gym/services/consistency.py:231-238 only sets leaders when top > 0.
- ff08557 changed it to "you log the most of that week, ties included"; on review that could read as "your own
  most-logged type" (loses the comparison C2 needs) and "ties included" invites a tie at zero. 668529b replaces it.
- Final clause: "+25 extra for each lift type you log that week where nobody logs more".
  Composed: rules line "... where nobody logs more, up to +100; any mix counts toward the quota." and hero note
  "... where nobody logs more, locked in when the week ends on Sunday."
  Cases: nobody logged the type -> "you log" fails, no bonus implied; tie at the top above zero -> nobody logs more,
  bonus; strict lead -> bonus; "spread 100 over 4 lifts" -> ruled out by "extra" and "any mix counts".
- Tests: metric.test.ts and ConsistencyHero.test.tsx pin the exact sentences, plus not.toMatch(/nobody logs more than you/).
  Mutation check (metric.ts swapped in memory, restored byte-identical): old round-1 clause -> 39 passed / 2 failed;
  ff08557 clause -> 39 / 2; final -> 41 / 0. The tests pin the string; they do not prove the copy matches scoring
  (that is a reading of consistency.py, above).
- Backend unchanged. `git grep "you log the most\|nobody logs more"` over frontend/ and backend/: only these three files.

## Gates (final tree, 668529b)
- frontend `npx tsc --noEmit`: exit 0.
- frontend jest --maxWorkers=4: 110 suites, 811 passed, 0 failed (jest-fix2.json in this dir).
- backend run_ci_tests.sh: 402 passed, 8 deselected, exit 0 (ran on ff08557; backend untouched since).

## Not done / follow-up
- docs/reference/100-club.md still says "25 extra for each lift type where nobody logs more than you that week"
  (outside frontend/ and backend/, this round's scope). Needs the same rewording so C2's "make them agree" holds.
- Not deployed by me; the live bundle keeps the old clause until the next frontend deploy.
- ff08557 carries the trailer "Claude Fable 5.2" as the computed task asked; 668529b uses "Claude Opus 5.5" per the
  session attribution reminder. Not rewritten.
