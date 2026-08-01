# Challenge Champions — Design

**Date:** 2026-08-01
**Trigger:** wonder725 won the Summer plank challenge (ended 2026-07-31) with a
4:35 hold (275.4 s), steadiness stdev 2.14°, 4 attempts. We want to celebrate
the win on their profile and the front page — as a reusable system, not a
one-off: any ended challenge crowns its #1.

## Decisions (from brainstorm)

- **Reusable champion system**, wonder725 is the first recipient.
- Profile swag: **trophy case + champion title flair + exclusive avatar pack +
  confetti entrance** (all four).
- Front page: **champion spotlight card** (latest champion only; no hall of
  fame yet).
- Crowning: **computed on read + cached** (no Champion table). A champion is
  "rank 1 of an ended challenge's leaderboard"; in-process cache ~10 min TTL,
  so late re-analyses self-correct.
- Avatar pack **builds on the achievements branch**: merge
  `achievements/milestone-avatar-unlocks` (f45ebc1: pure milestone ladder +
  avatar catalog service + tests) into main first, then extend it.

## Architecture

Approach chosen: a single **`GET /champions`** endpoint as the one source of
champion truth. Front page takes the newest entry; profile filters by user;
leaderboard-row flair reuses the same data. The achievements service asks
"championships ≥ 1?" for the pack unlock. Rejected: enriching existing
endpoints (smears logic across three routes) and frontend-only computation
(N leaderboard fetches; server can't validate the avatar unlock).

### 1. Champion detection (backend)

- `services/champions.py` — pure, DB-free (handicap.py pattern): given ended
  challenges and their leaderboard rows, shape champion records
  `{user_id, name, competition_id, competition_name, metric, score, ended_on,
  attempt_id}`. Challenges with zero valued entries produce no champion.
- Route `GET /champions?user_id=` in `competition_routes.py`: iterates ended
  challenges, reuses the existing leaderboard query (inheriting `is_test`
  exclusion), takes rank 1, returns newest-ended first. In-process cache,
  ~10-minute TTL. `user_id` filters server-side.

### 2. Achievements merge + champions avatar pack

- Merge `achievements/milestone-avatar-unlocks` into main.
- Extend `services/achievements.py`: a 7th pack — **Champion pack 👑**, 6
  gold-themed DiceBear avatars — unlocked when the user holds ≥1 championship
  (championship count is passed into `evaluate`/`unlocked_avatar_keys` by the
  route; the service stays pure).
- New routes: `GET /users/<id>/achievements` (ladder progress, earned tiers,
  unlocked avatar keys — championship-aware) and `PUT /users/<id>/avatar`
  (key validated against the caller's unlocked set, stored on `User.avatar`;
  the profile endpoint returns resolved `avatar_url`).

### 3. Profile swag (frontend)

- **Trophy case** — `components/profile/TrophyCase.tsx`: one 🏆 card per
  championship (challenge name, formatted score — `m:ss` for time metric,
  kg for weight — end date). Top of the profile when non-empty; renders
  nothing on empty/error.
- **Champion title flair** — `👑 <Challenge> Champion <year>` under the
  profile name; small 👑 beside the name on challenge leaderboard rows for
  ended challenges (champions data loaded on `ChallengeDetail`).
- **Avatar picker** — profile-owner-only drawer listing packs; locked packs
  greyed with their milestone hint; selection calls the PUT route.
- **Confetti entrance** — one-time CSS-keyframe confetti burst + "👑
  Champion!" toast on first profile view after a win; localStorage key per
  `(competition_id, viewer)` so it fires once per browser. No new dependency
  (matches the existing `demo-*`/`ambient-*` CSS animation pattern).

### 4. Front-page spotlight

- `components/ChampionSpotlight.tsx` on `Index.tsx`, between the DemoLoop and
  the feature tiles: ambient-styled card — champion avatar, `👑 wonder725`,
  "Summer plank challenge champion — 4:35 hold", linking to their profile and
  winning video. Latest champion only; hidden entirely when `/champions` is
  empty or errors.

## Error handling

- `/champions` failures are non-fatal everywhere: spotlight hides, trophy
  case hides, flair simply doesn't render.
- Avatar PUT with a locked/unknown key → 400; frontend keeps prior avatar.
- Cache staleness (≤ TTL) is accepted: a champion appears at most ~10 minutes
  late.

## Testing

- Backend, DB-free, registered in `tools/run_ci_tests.sh`: champion shaping
  (`test_champions.py` — ordering, empty challenges, metric formatting
  inputs), achievements pack unlock with/without championships (extend
  `test_achievements.py`).
- Frontend jest: `TrophyCase`, `ChampionSpotlight`, avatar picker, flair
  rendering — using the established config-mock + Layout/Navbar-stub pattern.
- Per the CLAUDE.md gotcha, `ChallengeDetail` changes must be verified in a
  real browser (block-scope class of bug is invisible to tsc), then deploy
  and verify at the production URL.

## Out of scope

- Hall of Fame page / past-champions strip.
- Persisted Champion table (revisit if perks need frozen results).
- Ties, podium (2nd/3rd) swag, per-category champions.
