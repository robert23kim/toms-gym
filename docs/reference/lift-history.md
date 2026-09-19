<!-- Moved verbatim from CLAUDE.md on 2026-09-19; CLAUDE.md keeps a pointer. -->
# Lift History on Profile (shipped 2026-07-06)

Fixes "past lifts are invisible": the profile endpoint's `uploaded_videos` is hard-capped at LIMIT 10 (unchanged — still feeds the thumbnail gallery), so a proper history now lives beside it. Spec: `docs/superpowers/specs/2026-07-06-lift-history-design.md`; plan: `docs/superpowers/plans/2026-07-06-lift-history.md`.

- **`GET /users/<id>/lifts?limit=&offset=`** (upgraded in place — the old unpaginated/broken version had zero consumers): Attempt ⋈ UserCompetition ⋈ Competition ⟕ LiftingResult, newest first, `limit` default 20 cap 50, returns `{lifts, total, limit, offset}`. Grade/hold extracted in SQL via JSONB `->>` (`overall_grade`, `total_in_plank_s`, report `lift_type`) so `per_second` never ships on list rows. Row shaping is DB-free in `services/lift_history.py` (`shape_lift_row`), tested in `tests/test_lift_history.py` (registered in `run_ci_tests.sh`).
- **`components/profile/LiftHistoryList.tsx`** — paginated rows on the Profile Lift tab (above the gallery): date · lift type (report lift_type wins over the attempt's) · weight (hidden for planks) · payoff (plank `m:ss` hold / colored grade pill / "analyzing…" / "—"), row links to `/challenges/{comp}/participants/{user}/video/{attempt}`. "Load more" while `lifts.length < total`; renders nothing on empty/error.
- Suite at ship: frontend 49/307; backend CI gate 138.
