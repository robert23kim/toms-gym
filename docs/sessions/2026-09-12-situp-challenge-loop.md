# Situp challenge with quality-weighted scoring — 2026-09-12

## What this was
A `/loop` to add a situp challenge mirroring the pushup one, deploy it, verify it in
production and clean up the test data. Two mid-session twists from Tom: rep quality must
affect the score, and sloppy reps should still count, just weighted less.

## What changed
- **Live challenge:** https://my-frontend-quyiiugyoq-ue.a.run.app/challenges/95b60b42-9220-4195-a659-b1d362093ea1
  (id `95b60b42-9220-4195-a659-b1d362093ea1`, 2026-09-12 → 2026-10-12, lifttypes `["Situp"]`, gender `MF`).
- **Scoring rule:** per-rep form score ≥ 70 (grade C) counts 1.0, anything lower counts 0.5.
  Constants `CLEAN_REP_MIN_FORM` / `SLOPPY_REP_CREDIT` in `backend/toms_gym/services/challenge_leaderboard.py`,
  mirrored in `frontend/src/lib/cleanReps.ts`. Only Situp is quality-scored; pushup boards are unchanged.
  Tunable without re-analysis (computed from `report.rep_metrics[].form_score` at read time).
- **Engine** (`~/code/bowling-app/analysis-engine`, worktree `/private/tmp/situp-engine`): branch
  `feat/situp-config` @ `d4d8bb2`, branched off the still-unmerged `feat/pushup-config`. Hip-angle rep
  config, new `side_view_only` + `side_keypoints` config keys, ROM branch generalised to pushup+situp.
  Deployed as `bowling-service-00050-q8m` (rollback `00049-knc`).
- **toms_gym** commits on `main` (unpushed at time of writing):
  - `1427a35` feat(situp): Situp lift type with a quality-weighted reps board — migration 019, `REPS_LIFT_TYPES`,
    `attempt_rep_score()`, `rep_form_scores` leaderboard SQL column, `reps_total`/`clean_reps` on rows.
  - `89044fe` feat(situp): situp upload, coaching copy and clean-rep board display — `lib/cleanReps.ts`,
    scoring note under the challenge hero, "N clean of M" on rows, "Board score" line on the result card.
  - `57a7f0c` fix(situp): hide arm metrics from the situp set card; clean-of count on podium and own row.
  - `9edb973` docs(situp): CLAUDE.md "Situp Challenge" section.
- **Deployed:** backend rev `my-python-backend-00192-rhl`, frontend rev `my-frontend-00189-p57`.
- Memory note `~/.claude/projects/-Users-toka-code-toms-gym/memory/situp_challenge.md`.

## What we learned
- **The engine's "pick the view with more reps" fallback is a trap for non-arm lifts.** The front-view
  signal is shoulder-to-wrist height; on a synthetic 5-rep situp set it produced 10 peaks and won the
  tie-break. `side_view_only` in `EXERCISE_CONFIGS` is the fix; any future hip/knee-driven lift needs it.
- **A synthetic fixture must be insensitive to the *wrong* signal** or the mutation check passes vacuously.
  The first situp fixture swung its arms with the torso, so an elbow-angle segmenter also "counted" reps
  and swapping the signal function did not fail the tests. Rigid folded arms fixed it.
- **Never `git checkout <file>` to undo a mutation while the real edit is unstaged** — it wiped the
  config and analyzer edits and they had to be re-applied. Stage first, then mutate, then `checkout`.
- Cloud Build launched from the scratchpad failed instantly because the scratchpad directory did not
  exist yet; `mkdir -p` it before redirecting a log there.
- Engine `[REP_SEG]`/`[ANALYZE]` prints do not reach Cloud Logging; only `ANALYSIS_STAGES` does. The local
  CLI (`scripts/analyze_lift.py --lift-type situp`) is the only way to see why a prod job counted what it did.
- The browser walk found two real defects that 574 green jest tests and a clean tsc did not: the set card
  listed the engine's Elbow Stability / Shoulder Swing for a situp, and the "N clean of M" line was only on
  ranked rows so a one-entrant board never showed it. Both fixed in `57a7f0c`.
- Prod cleanup is SQL-only: `DELETE /attempts/<id>` fails on an analysed attempt because `LiftingResult`
  and `AnalysisNotification` reference `Attempt` without cascade, and there is no user-delete route. Recipe:
  `~/Downloads/google-cloud-sdk/bin/cloud_sql_proxy -instances=toms-gym:us-east1:my-db=tcp:5433` + pg8000
  as `postgres` with secret `db-password`; delete in order AnalysisNotification → ShortLink → LiftingResult →
  Attempt → UserCompetition → User, then `gsutil rm` `lifting/<attempt>/`, the `videos/…` upload and
  `og-cards/<code>.png`.

## Still broken / next steps
- **No real situp footage exists**, so the 130°/70° hip ROM band and rep-count accuracy are unvalidated.
  Get one clip from Tom, run it through the local CLI, and tune `EXERCISE_CONFIGS["situp"]` before the
  challenge gets real entrants.
- **Two unmerged engine branches** (`feat/pushup-config`, `feat/situp-config`) hold the pushup and situp
  configs. Anyone deploying the engine from `main` ships without both. Merge them.
- The four toms_gym commits are **not pushed**.
- `AttemptHistory` per-attempt rows show raw `total_reps`; on a situp board the best attempt is chosen by
  weighted score, so the 🏆 marker can disagree with the rank.
- The low-tracking tip on bodyweight lifts still says "keep the whole bar/body in frame"
  (`frontend/src/pages/VideoPlayer.tsx` ~L620).
- Completion emails are attempted for `@example.com` uploaders; only `.local` / `e2e-lift-*` are skipped.
- `DELETE /attempts/<id>` cannot delete an analysed attempt (FK without cascade) — add a cascade or a
  cleanup route so prod test data does not need direct SQL.

## Verification
- Backend CI gate (`PYTHON=venv/bin/python tools/run_ci_tests.sh`): 294 passed, 8 deselected.
- Frontend: `tsc --noEmit` clean; jest 85 suites / 574 tests passed (via `--json --outputFile`).
- Engine lifting suite under `.venv`: 208 passed, 2 skipped. Mutation checks: swapping the situp signal
  to `compute_elbow_angle`, forcing `side_view_only=False`, and narrowing the ROM branch back to pushup
  each failed 4–5 situp tests; restored state passes.
- Prod, after each deploy, Playwright walk at 390×844 with `localStorage.userId` set: no console errors,
  no horizontal overflow on `/challenges`, the challenge page, `/lift/upload`, `/lift/status/…`,
  the result page and `/profile/…`.
- Prod end-to-end with test user `situp-e2e@example.com`: deadlift sample clip → 0 reps (one slow rep
  exceeds the 8s rep cap; not a situp bug) and the honest low-tracking state rendered; curl sample clip →
  4 hip cycles, per-rep form 77.7 / 64.4 / 40.6 / 70.5 → board score 3.0, "2 clean of 4", identical on the
  status page, the result ladder, the result card and the leaderboard.
- Cleanup verified: `User`/`UserCompetition`/`Attempt` counts for the test user are 0, the four bucket
  paths return "matched no objects", and `GET /competitions/<id>/leaderboard` returns 0 rows.
- Not verified: rep counting on a real situp; Situp enum on any environment other than prod (there is only prod).
