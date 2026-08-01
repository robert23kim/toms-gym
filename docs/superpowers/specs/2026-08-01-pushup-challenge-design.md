# Pushup Challenge — Design Spec

**Date:** 2026-08-01
**Status:** Draft — written autonomously in a /loop session; decisions flagged for review are marked ⚠️.
**Repos touched:** `~/code/bowling-app/analysis-engine` (the bowling-service analyzer) and `~/code/toms_gym` (backend + frontend).

## Goal

Users film themselves doing pushups, upload to a pushup challenge, the analyzer
counts reps and scores form, and the challenge leaderboard ranks athletes by
their best rep count. This is the third challenge metric alongside `time`
(plank) and `weight` (lifting totals).

## What exists today (research findings)

- **Analyzer is config-driven.** `analysis-engine/src/lifting/config.py` →
  `EXERCISE_CONFIGS` defines each lift by `signal_angle_fn`, ROM thresholds,
  and `form_weights`. Rep counting (`rep_segmenter.py`) is generic peak
  detection over the smoothed signal angle: a rep spans consecutive
  extension peaks (used by bicep_curl/squat/deadlift). Plank branches to a
  separate static-hold analyzer.
- **`total_reps` already flows end-to-end.** `summary.py` emits
  `total_reps: len(report.reps)` in the report JSON; toms_gym stores it in
  `LiftingResult.report` (JSONB) and already extracts it in
  `services/lift_history.py` and `user_routes.py`. Nothing new to persist.
- **Challenge metric selection** (`competition_routes.py`
  `_leaderboard_payload`): declared lift types come from a `lifttypes` tag in
  `Competition.description`; declared `{"Plank"}` → `time`, anything else →
  `weight`. Ranking is pure/DB-free in `services/challenge_leaderboard.py`
  (`_rank_time` / `_rank_weight`).
- **`lift_type` is a Postgres enum** (`schema.sql`), extended by migration
  (`009_add_plank_lift_type.sql` is the template). Frontend label → DB enum in
  `upload_routes.py` `LIFT_TYPE_MAPPING`; DB enum → engine name in
  `lifting_processor.py` `_normalize_lift_type`.
- **Frontend metric rendering** is centralized in
  `components/challenge/metric.ts` (`ChallengeMetric = "time" | "weight"`),
  consumed by `ChallengeDetail`, `Podium`, `LeaderboardRow`, `StandingCard`,
  `AttemptHistory`.

## Approaches considered

**A. Config-only analyzer change (recommended core).** Add a `pushup` entry to
`EXERCISE_CONFIGS` reusing the existing elbow-angle rep segmentation and
existing form metrics. Zero new analyzer math; rep counting works because a
pushup's elbow-angle trace has the same peak/trough shape as a bicep curl
(lockout ≈ extension peak, bottom ≈ contraction trough).

**B. Dedicated pushup analyzer** (new module like `plank_analyzer.py`) with
hip-sag detection, per-rep depth, tempo coaching. Most accurate, most work,
and duplicates the rep pipeline.

**C. A + one new form metric ("body line").** Pushups' signature fault is
sagging/piking hips — measurable as the shoulder-hip-ankle angle the plank
analyzer already computes per frame. Add it as a scored rep metric.

**Decision: A for v1, C as a stretch task in the plan.** B is YAGNI — the rep
pipeline already generalizes.

## Design

### 1. Analyzer (`bowling-app/analysis-engine`)

Add to `EXERCISE_CONFIGS`:

```python
"pushup": {
    "signal_angle_fn": "compute_elbow_angle",
    "primary_angles": ["elbow_angle"],
    "rom_extension_deg": 155.0,   # lockout at top
    "rom_contraction_deg": 90.0,  # chest near floor
    "max_rep_duration_s": 8.0,
    "form_weights": {"rom": 0.50, "momentum": 0.25, "body_sway": 0.25},
},
```

- ⚠️ ROM thresholds and weights are initial guesses — must be tuned against a
  real fixture video before ship (same practice as the plank fixture
  `test_video_plank_10s.mp4`).
- Elbow-drift is weighted 0 (meaningless when the hand is planted).
- Camera guidance: side view, whole body in frame — same filming-tips surface
  the low-detection fallback already shows.
- Service change: none — `/analyze-lift` passes `lift_type` straight through
  to `analyze_lift()`, which reads `EXERCISE_CONFIGS`.
- **Stretch (approach C):** `score_body_line` in `form_scorer.py` — mean
  shoulder-hip-ankle deviation per rep (reuse the plank body-line math), added
  to `primary_angles`/`form_weights` and a `PUSHUP_METRIC_TARGETS` block so
  the dashboard shows "Body Line" with plain-language coaching.
- Tests: extend `test_config.py` (config completeness), add a
  `test_rep_segmenter` case with a synthetic pushup elbow-angle trace, and an
  end-to-end fixture test with a short real pushup video.

### 2. Backend (`toms_gym`)

- **Migration `016_add_pushup_lift_type.sql`:** `ALTER TYPE lift_type ADD
  VALUE 'Pushup';` (mirror of 009, registered in the startup-migration
  runner).
- **Mappings:** `LIFT_TYPE_MAPPING['Pushup'] = 'Pushup'` (upload_routes);
  `_normalize_lift_type` adds `'Pushup': 'pushup'` (lifting_processor).
- **Metric selection** (`competition_routes.py`): declared `{"Pushup"}` →
  `metric = "reps"`; same inference fallback as plank (all completed attempts
  Pushup → reps). Leaderboard SQL adds `lr.report->>'total_reps' AS reps`
  next to the existing `held_s`/`steadiness` extraction, carried onto each
  attempt dict.
- **Ranking** (`challenge_leaderboard.py`): new `_rank_reps`, mirroring
  `_rank_time`: qualifying = non-failed attempts with `lift_type == "Pushup"`
  and `reps is not None`; score = **max reps across attempts** (⚠️ chosen over
  cumulative-total-for-the-window — best-single-effort matches how the plank
  board works; revisit if the challenge should reward volume). Tiebreak:
  higher form score, then earlier `created_at`. Same `history[]` shape so
  AttemptHistory and nickname/chips plumbing keep working.
- **No new storage.** `total_reps` already lives in `LiftingResult.report`;
  profile lift history already surfaces it.

### 3. Frontend (`toms_gym/frontend`)

- `lib/types.ts`: `ChallengeMetric = "time" | "weight" | "reps"`.
- `components/challenge/metric.ts`: reps cases — column label `REPS`, unit
  `""` (value rendered as integer + " reps" where the unit suffix is used),
  `formatScoreValue` → integer, CTA "Upload your pushups".
- `ChallengeDetail.tsx`: treat Pushup like Plank in the upload form — no
  weight field (reps are the score); lift type pre-set/locked when the
  challenge declares only Pushup (the `allowedFormIds` mechanism already does
  this from declared categories).
- `AttemptHistory.tsx`: reps board payoff = "N reps" + grade pill (mirrors the
  weight branch minus kg).
- `UploadVideo.tsx` (standalone `/lift/upload`): add "Pushup" to the lift
  type options; weight field hidden for Pushup.
- `VideoPlayer` needs no structural change — pushup reports are ordinary
  rep reports (rep breakdown, grades, coaching). Stretch: pushup entries in
  `lib/liftCoaching.ts` copy map.
- ⚠️ Reminder from CLAUDE.md: ChallengeDetail scope bugs are only caught by
  rendering — verify in a browser, not just tsc.

### 4. Rollout

1. Ship analyzer change + deploy bowling-service; verify with a test upload
   using lift_type=pushup before any toms_gym change (old backend simply
   won't send it).
2. Ship toms_gym backend (migration + mappings + metric) and frontend
   together; deploy via `python3 deploy.py --skip-iam`.
3. Create the pushup challenge (Competition with declared `lifttypes:
   Pushup`), upload a real test video end-to-end in prod, then delete/mark
   the test entry (`is_test` flow).

### Error handling

- Zero reps detected (`total_reps === 0`) already triggers the low-detection
  filming-tips fallback on the result page; the leaderboard treats the
  attempt as non-qualifying (reps present but 0 ranks last — acceptable).
- Analyzer failure → attempt `status='failed'` → excluded, as today.
- Unknown lift_type on an old deployed engine falls back to bicep_curl
  analysis — prevented by rollout order (engine first).

### Testing

- Analyzer: config/segmenter unit tests + real-video fixture test.
- Backend: `tests/test_challenge_leaderboard.py` reps cases (rank, tiebreaks,
  mixed-lift exclusion, metric inference); registered in `run_ci_tests.sh`;
  DB-free.
- Frontend: `metric.ts` unit tests, ChallengeDetail reps-board render test,
  AttemptHistory reps payoff test.

## Out of scope (YAGNI)

- Knee-pushup / cheat-rep classification.
- Pushup-specific steadiness nicknames (plank-only stays plank-only).
- Cumulative-volume leaderboards, daily streaks.
- Dedicated pushup analyzer module (approach B).

## Open questions for review

1. Best-single-attempt vs cumulative reps as the board score (chose best).
2. ROM thresholds (155°/90°) pending real-video tuning.
3. Include the body-line stretch metric in v1 or fast-follow?
