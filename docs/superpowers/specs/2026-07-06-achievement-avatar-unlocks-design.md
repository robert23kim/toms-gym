# Achievement Milestone Path + Avatar Unlocks — Design

> **⚠️ Partly built (2026-08-01).** The pure service and the avatar half of this
> design shipped as a dependency of Challenge Champions; the milestone-path UI
> never did. Read `CLAUDE.md` → "Challenge Champions" for what actually exists.
> Specifics where this document no longer matches the code:
>
> - **Shipped:** `services/achievements.py` (ladder, catalog, `evaluate`,
>   `next_milestone`), `GET /users/<id>/achievements`, `PUT /users/<id>/avatar`,
>   `User.avatar`, and `components/profile/AvatarPicker.tsx`.
> - **Not built:** `BadgeStrip`, `MilestonePath`, and the whole
>   `frontend/src/components/achievements/` directory. `ladder` and `next` are
>   served but nothing renders them.
> - **Not built:** avatar propagation into `Podium` / `LeaderboardRow` /
>   `MomentumLine`, the golf pages (`GolfProfile`, `GolfLeaderboard`), or
>   `ChampionSpotlight`. The chosen avatar appears only on the profile header;
>   everywhere else still uses deterministic `getGolfAvatar`.
> - **Column type:** shipped as `avatar TEXT`, not `VARCHAR(64)`.
> - **Response shape:** shipped as flat `avatars: [{key, url}]` +
>   `locked_packs: [...]` + `avatar`, not
>   `{avatars: {unlocked, locked_by_tier}, current_avatar}`.
> - **Packs:** 7 now, not 6 — Challenge Champions added a `champion` pack that
>   unlocks on winning a challenge rather than by a ladder tier.

**Date:** 2026-07-06
**Status:** Approved (superseded in part — see banner)
**Scope:** Backend (migration 015, achievements service + routes, award hooks, avatar on existing serializers) + frontend (BadgeStrip, MilestonePath, AvatarPicker, avatar preference in challenge components).

## Problem

Nothing in the app rewards progress, and avatars are entirely deterministic
(`getGhibliAvatar(id)` sprites for lifting/challenges, DiceBear `getGolfAvatar(name)`
for golf) — no user can change their look. We want a milestone ladder that starts
easy and gets harder, unlocks avatar customization tier by tier, shows badges on
the app home, and awards retroactively ("hold a 2 min plank" → everyone who
already has counts).

## Decisions (user-confirmed)

1. **Tiered avatar packs** — each milestone unlocks a batch of avatars; your
   avatar is changeable among what you've unlocked.
2. **Home strip + profile path** — Index shows a compact badge strip for the
   remembered visitor (localStorage `userId`); the profile hosts the full
   milestone path and the avatar picker.
3. **Plank-first ladder** — v1 milestones are lifting/plank-centric, all
   computable from existing `Attempt` + `LiftingResult` data. Bowl/golf tiers
   are a future drop.
4. **DiceBear style packs** — avatar art is URL-generated DiceBear styles (the
   golf feature already uses DiceBear); no asset pipeline.
5. **Append-only ledger; once earned, always earned** — deleting a video never
   revokes a badge (avoids HandicapSnapshot-style "why did it change" issues).

## The Ladder

| Tier | Key | Badge | Requirement | Unlocks (6 avatars each) |
|---|---|---|---|---|
| 1 | `first_steps` | 🌱 First Steps | Any attempt with a video | `avataaars` pack |
| 2 | `half_minute` | ⏱️ Half Minute | Plank hold ≥ 30s | `bottts` (robots) |
| 3 | `iron_minute` | 💪 Iron Minute | Plank hold ≥ 60s | `adventurer` |
| 4 | `two_minute_club` | 🔥 Two-Minute Club | Plank hold ≥ 120s | `lorelei` |
| 5 | `statue_tier` | 🗿 Statue Tier | Plank hold ≥ 180s | `fun-emoji` |
| 6 | `plank_royalty` | 👑 Plank Royalty | ≥5 plank attempts AND a ≥120s hold | legendary `avataaars` seeds |

Stats inputs: `has_upload` (any Attempt with `video_url`), `best_hold_s`
(max `LiftingResult.report->>'total_in_plank_s'`), `plank_attempts` (count of
attempts whose report `lift_type` is plank OR attempt `lift_type` = 'Plank').

## Data model (migration 015, startup-migration pattern like 013/014)

- `ALTER TABLE "User" ADD COLUMN IF NOT EXISTS avatar VARCHAR(64)` — stores a
  **catalog key** (e.g. `bottts-3`), never a raw URL; NULL = deterministic
  fallback everywhere (existing behavior unchanged).
- `CREATE TABLE "Achievement" (id UUID PK default, user_id UUID REFERENCES "User"
  ON DELETE CASCADE, achievement_key VARCHAR(64) NOT NULL, awarded_at TIMESTAMPTZ
  NOT NULL DEFAULT now(), UNIQUE (user_id, achievement_key))`.
- **Backfill = self-healing INSERT…SELECT per tier with ON CONFLICT DO NOTHING**,
  run inside the startup-migration block every boot (idempotent, like 013's
  UPDATE). This is what awards history — and also acts as a safety net if an
  award hook ever misses.

## Backend components

- **`services/achievements.py`** (pure, DB-free): `LADDER` definitions,
  `AVATAR_CATALOG` (key → DiceBear URL), `evaluate(stats) -> [keys]`,
  `unlocked_avatar_keys(earned_keys) -> [keys]`, `resolve_avatar_url(key) ->
  url|None`, `next_milestone(stats, earned) -> {key, progress}|None`.
- **`integrations/achievement_award.py`**: `award_for_user(get_conn, user_id)` —
  stats SQL → `evaluate` → `INSERT … ON CONFLICT DO NOTHING`. Best-effort:
  swallows all errors (mirrors `analysis_notify`).
- **Hooks:** (a) `lifting_processor.py` right after `notify_analysis_complete`
  (hold-based tiers land when analysis lands); (b) **award-on-read** — the
  `GET /achievements` endpoint runs the same idempotent award pass before
  returning, so tier 1 lands the moment any badge surface fetches (no need to
  hook the four separate Attempt-insert code paths).
- **Routes (`routes/achievement_routes.py`):**
  - `GET /users/<id>/achievements` → `{earned: [{key,title,emoji,tier,awarded_at}],
    next: {key,title,emoji,progress:{best_hold_s, needed_s, plank_attempts,
    needed_attempts}}|null, avatars: {unlocked: [{key,url}], locked_by_tier:
    {tier: count}}, current_avatar: {key,url}|null, badge_total}`.
  - `PUT /users/<id>/avatar` body `{avatar_key}` → 200 `{key,url}` when the key
    is in the user's unlocked set; 403 otherwise; 400 unknown key. Public
    endpoint, consistent with the app's optional-auth model (same accepted risk
    class as ticket status updates; revisit when admin auth lands).
- **Avatar propagation:** challenge leaderboard SELECT adds `u.avatar`; ranked
  rows carry `avatar_url` (resolved server-side, null when unset). Profile
  endpoint response adds `avatar` `{key,url}|null`.

## Frontend components

- **`lib/achievements.ts`**: `fetchAchievements(userId)`, `setAvatar(userId, key)`,
  types.
- **`components/achievements/BadgeStrip.tsx`** (Index, after the IconTiles
  section): reads localStorage `userId`; renders earned emoji + 🔒 for locked +
  "N of 6 badges"; links to `/profile/{userId}`. Renders nothing when no
  userId, fetch fails, or zero earned.
- **`components/achievements/MilestonePath.tsx`** (Profile, above the sport
  tabs): earned ✅ with date · next ◯ with a progress bar ("best 1:42 — 82%
  there") · locked 🔒.
- **`components/achievements/AvatarPicker.tsx`** (own profile only —
  `resolvedUserId === localStorage.userId`): grid of unlocked avatars (click →
  PUT, optimistic update), locked tiers as silhouette rows with unlock hints.
- **Avatar preference:** `Podium`, `LeaderboardRow`, `MomentumLine`, and the
  Profile header render `avatar_url ?? getGolfAvatar(name, id)` (existing
  deterministic fallback unchanged for users who never picked one).

## Testing

- `tests/test_achievements.py` (DB-free, added to `run_ci_tests.sh`): threshold
  cases for every tier boundary, `unlocked_avatar_keys`, `next_milestone`
  progress math, catalog url resolution.
- Route tests (mock-session pattern of `test_competition_routes.py`): GET shape;
  PUT 200 unlocked / 403 locked / 400 unknown.
- Jest: `BadgeStrip` (renders, hides without userId), `MilestonePath`,
  `AvatarPicker` (locked not clickable, PUT on select), `LeaderboardRow` prefers
  `avatar_url`.
- Prod verification post-deploy: achievements GET for a real plank user, pick an
  avatar in the UI, confirm it shows on the challenge leaderboard.

## Out of scope (YAGNI)

- Bowl/golf milestones (v2 tier drop).
- Achievement notifications/toasts/emails.
- Admin CRUD for definitions (they live in code).
- Avatar upload of custom images.
- Revocation logic (append-only by design).
