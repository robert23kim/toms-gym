# Per-Challenge Leaderboard — Design

**Date:** 2026-07-03
**Status:** Draft (awaiting review)
**Author:** Claude + Tom
**Design handoff:** `docs/design/challenge-leaderboard/` (`handoff.md` +
`Challenge Redesign.dc.html`) — podium direction, approved. Mobile `#2b` is
PRIMARY; desktop `#1b` second. Worked example is the "Summer plank challenge".

## Problem

A challenge (`Competition`) page today shows an unranked "Lifts" feed sorted by
weight, with the key metric (for a plank, the hold time) buried in a tiny chip.
There is no true *leaderboard* scoped to a single challenge. The only ranked view
(`/leaderboard`) flattens every competition into one global list.

**The primary driver is the plank challenge** — a plank has no weight; it's ranked
by how long you hold it. The redesign reframes the challenge page as what it
actually is: a **leaderboard** — a podium for the top 3 and a ranked table for
everyone else, with each entrant's clip reachable from their row. Time-based
ranking is the headline path; weight ranking is the secondary mode.

## Decisions

| Question | Decision | Confirmed? |
|---|---|---|
| Where it lives | **The challenge page itself is the leaderboard** (`ChallengeDetail.tsx` redesigned). No separate "leaderboard vs feed" tab — clips are folded into the leaderboard rows (podium avatar play-badge; list-row thumbnail). | ✅ user + handoff |
| Layout | **Podium (top 3) + "Everyone else" ranked table**, per the approved handoff. Mobile-first (`#2b`), then desktop (`#1b`). | ✅ handoff |
| Grouping | **One flat board** — a single ranked list. No weight-class/gender segmentation this iteration. | ✅ user |
| Ranking metric | **Per-challenge metric.** Plank → **longest hold** (`total_in_plank_s`, DESC). Lifting → **best-lift total**. | ✅ user (plank primary) |

## The two metrics

A challenge is ranked by exactly one metric, chosen from its lift type (see
"Metric selection"). The endpoint returns a `metric` field (`"time" | "weight"`)
telling the frontend how to render the score.

**`time` (plank challenges) — headline path.**
- Rank by the athlete's **best (longest) hold** across their `completed` plank
  attempts, descending. Score shown as `65.8s` (one decimal, unit muted/smaller).
- Held time comes from the analysis result, not the attempt row:
  `LiftingResult.report->>'total_in_plank_s'`. The pipeline sets
  `Attempt.status='completed'` and writes the report in the same commit
  (`lifting_processor.py:183,202`), so any `completed` plank attempt has a hold time.
- `report->>'overall_form_score'` is carried through for display and as a tiebreak.

**`weight` (lifting challenges).**
- Rank by **best-lift total**: per athlete, `max(weight_kg)` per `lift_type`
  among `completed` attempts, summed. Classic powerlifting total; reduces to "best
  single lift" for a single-lift challenge. Score column labeled "Total" (lbs).

Only `status = 'completed'` attempts count; `pending`/`failed` are ignored for
ranking (they still surface their clip if we choose to show them — MVP shows only
completed).

### Metric selection (how the route decides)

`metric = "time"` iff the challenge is **plank-only**, else `"weight"`.

1. The challenge's declared lift types (`lifttypes` parsed from
   `Competition.description` metadata, as `get_competition_by_id` already does).
   Exactly `{"Plank"}` → `time`.
2. Fallback when metadata is absent: infer from `completed` attempts — all `Plank`
   → `time`.
3. Otherwise → `weight`. A challenge mixing Plank with weighted lifts ranks by
   weight and excludes planks (you can't add seconds to kilograms) — documented,
   not silently blended.

## Architecture

Ranking lives **server-side** in a new endpoint + a pure, DB-free helper
(mirrors the `/golf/leaderboard` pattern). The redesigned page renders whatever
the endpoint returns.

```
ChallengeDetail.tsx  (redesigned as the leaderboard)
   │  GET /competitions/:id/leaderboard ──▶ rank_challenge(metric=…)  (pure)
   │  → { metric, lift_types, rows:[{rank, name, score, clip_url, thumbnail_url, …}] }
   └─ Upload flow (kept; sticky CTA on mobile, top-right button on desktop)
```

### Component 1 — `rank_challenge()` (pure helper)

New module `backend/toms_gym/services/challenge_leaderboard.py`. Pure, DB-free,
unit-testable.

```python
def rank_challenge(participants, *, metric):
    """
    metric: "time" | "weight"
    participants: list of {
        user_id, name, weight_class, gender,
        attempts: [{
            attempt_id, lift_type, weight_kg, status, created_at,
            video_url, annotated_video_url,   # clip sources
            held_s, form_score,               # from LiftingResult report (plank); None otherwise
        }]
    }
    Returns ranked rows, best-first:
    [{
        rank, user_id, name, weight_class, gender,
        score,             # time: best hold seconds; weight: best-lift total kg
        best_by_lift,      # weight: {lift_type: max_kg}; time: {"Plank": best_hold_s}
        form_score,        # time only; None otherwise
        clip_url,          # video for the athlete's best attempt (annotated if available)
        thumbnail_url,     # poster if we have one; else None (frontend derives from video)
        date,              # created_at of the best attempt (ISO) — shown under the name
        attempt_count,
    }]
    """
```

Common rules:
- Only `status == 'completed'` attempts.
- Sort by `score` descending.
- **Tiebreak:** equal score → for `time`, higher `form_score` first, then earliest
  `created_at`; for `weight`, earliest `created_at`. Deterministic.
- Zero qualifying attempts → `score = 0`, sorted last (kept for the "who joined"
  signal; frontend may dim them and they never occupy the podium).
- `clip_url`/`thumbnail_url`/`date` come from the **best** attempt (the one that
  set the score).

Metric-specific: `time` → `score = max(held_s)` over completed planks with
non-null `held_s`; `weight` → `sum` of per-lift maxes.

### Component 2 — `GET /competitions/<id>/leaderboard`

New route in `competition_routes.py`. Flat board, no query params this iteration.

- Loads the challenge (404 if missing); determines `metric`.
- Loads participants + `completed` attempts, **LEFT JOIN `LiftingResult`** on
  `attempt_id` to pull `report->>'total_in_plank_s'` (`held_s`),
  `report->>'overall_form_score'` (`form_score`), and `annotated_video_url`. Also
  selects each attempt's `created_at` and `video_url`.
- Calls `rank_challenge(participants, metric=metric)`.
- Response:
  ```json
  {
    "competition_id": "...",
    "metric": "time",
    "lift_types": ["Plank"],
    "rows": [
      { "rank": 1, "user_id": "…", "name": "robert23kim", "score": 65.8,
        "best_by_lift": {"Plank": 65.8}, "form_score": 0.91,
        "clip_url": "https://…", "thumbnail_url": null, "date": "2026-07-01",
        "weight_class": "83kg", "gender": "male", "attempt_count": 2 }
    ]
  }
  ```
- Weights returned raw in kg (frontend → lbs); hold times raw in seconds
  (frontend → `65.8s`).

### Component 3 — Redesigned challenge page (`ChallengeDetail.tsx`)

Recreate the approved podium mockups using the existing stack (React + Tailwind +
framer-motion + lucide, `Layout`). The app is already dark-themed
(`--background: 240 10% 3.9%` ≈ handoff `#0a0a0b`), so tokens map to existing
theme vars; see "Visual design". Existing data-fetching and the upload
handler/flow are **kept**; only the presentational body (the flat feed) is
replaced.

Top → bottom (mobile `#2b`, primary):
1. **App bar / Layout** — existing nav.
2. **Hero** — Back link; **status pill with countdown** ("Ongoing · 23d left",
   derived from start/end dates — extend the existing `determineStatus`); H1
   title; description microcopy; (desktop) top-right "Upload your plank" button.
3. **Podium** — top 3, columns ordered **2 · 1 · 3**, bottom-aligned. Each: avatar
   (with blue **play badge** → opens that entrant's clip), name, score, pedestal
   bar (heights 1st=96 / 2nd=70 / 3rd=56 mobile; larger on desktop). Champion has a
   gold crown/trophy above the avatar. Medal colors gold/silver/bronze.
4. **"Everyone else" table** — ranks 4+. Row: rank number, **clip thumbnail**
   (44×44 mobile / 30×30 desktop, play glyph → opens clip), name + date, score
   right-aligned. Desktop header row: `RANK · ATHLETE · HOLD · CLIP`
   (label "HOLD" for time, "TOTAL" for weight).
5. **"You" row** — highlighted (`rgba(47,123,246,.1)` fill, blue border). If the
   viewer has no entry: blue "YOU" avatar, "Not logged yet" + "Upload →". Once
   logged, it becomes their ranked row.
6. **Sticky bottom CTA** (mobile) — full-width blue "Upload your plank", fades in
   over a bottom gradient. Opens the existing upload flow.

**Clips:** avatar play-badge (top 3) and row thumbnail (4+) open the entrant's
clip. Reuse the existing pattern (`<video preload="metadata">` seeked to 0.5s as
the poster) since we have no separate poster frames; play opens the current
video player route/modal.

**Metric-aware rendering:** score unit + column label switch on `metric`
(`s`/"Hold" for time, `lbs`/"Total" for weight); the layout is identical.

**Empty / thin states:** 0 entrants → hide the podium, show the upload prompt
only. 1–2 entrants → fill only the occupied podium places (no empty pedestals);
remaining ranks table may be empty.

A thin `getChallengeLeaderboard(id)` is added to `frontend/src/lib/api.ts`;
`ChallengeLeaderboard` / `ChallengeLeaderboardRow` types to `types.ts`.

## Visual design (from handoff)

Recreate pixel-close using existing libraries; the HTML is reference, not code to
ship. Map tokens to Tailwind theme vars where they already exist.

- **Colors:** app bg `#0a0a0b`; surface `#141416`; border `rgba(255,255,255,.07)`
  (dividers `.06`); text `#fafafa` / muted `.6/.45/.4`; brand blue `#2f7bf6`
  (light text `#7fb0ff`); button shadow `0 8px 22px -6px rgba(47,123,246,.7)`;
  success pill `#4ade80` on `rgba(52,199,89,.14)`; tag purple `#b39dff` on
  `rgba(147,112,255,.14)`; medals gold `#f5c542` / silver `#cbd5e1` / bronze
  `#cd7f52`; "You" row `rgba(47,123,246,.1)` fill + `rgba(47,123,246,.3)` border.
- **Type:** display/numbers/titles **Space Grotesk** (600–700, tight tracking);
  body/UI **Inter**. Add both (Google Fonts / self-host) or map to the codebase's
  display/body pairing. Mobile H1 ≈ 27px, desktop 42px. Podium champion score 23px
  (mobile) / 32px (desktop); list scores 16–17px. Score unit ("s") ≈ 55–60% of the
  number, muted.
- **Radius:** cards 11–14px · thumbnails 8px · avatars 50% · pills 999px · buttons
  13px · pedestal tops `10px 10px 0 0`.
- **Spacing (mobile):** page padding `16px 18px` (bottom `96px` to clear sticky
  CTA); row padding `9–11px 14px`; gaps 8–12px.
- **Avatars:** reuse `getGolfAvatar` / `GhibliAvatar` (initials/deterministic)
  until real user photos exist.

## Data flow

1. `ChallengeDetail` mounts → fetch challenge (as today) + `GET /competitions/:id/leaderboard`.
2. Backend determines metric, loads participants + completed attempts (LEFT JOIN
   `LiftingResult` for hold time/form/annotated clip), calls `rank_challenge()`.
3. Component renders hero → podium (rows 1–3) → table (4+) → "You" row → sticky CTA.
4. Tapping a podium play-badge or a row thumbnail opens that entrant's clip.

No schema migration. No new tables. Derived at read time from existing `Attempt` /
`UserCompetition` / `LiftingResult` rows.

## Error handling

- Unknown `competition_id` → 404.
- No participants / no completed attempts → 200 with `rows: []` and correct
  `metric`; page shows the upload-prompt empty state (no podium).
- Plank attempt `completed` but no hold time yet (`held_s` null) → excluded from
  score; athlete falls to `score = 0` if it was their only attempt.
- Leaderboard fetch failure → inline error + retry in the body; hero + upload CTA
  still render so the user can still upload.

## Testing

- **`tests/test_challenge_leaderboard.py`** (pure helper):
  - `time`: longest hold wins; `held_s=None` excluded; best-of-multiple per athlete;
    tiebreak form-then-`created_at`; zero-hold athletes last; `clip_url`/`date`
    taken from the best attempt.
  - `weight`: best-of-per-lift rollup; single-lift reduces to best single lift;
    `pending`/`failed` excluded; tiebreak by `created_at`.
- **Route test** (`test_competition_routes.py`): plank challenge → `metric="time"`
  + hold-ranked rows with clip fields; lifting challenge → `metric="weight"`; 404;
  empty challenge; metric selection (plank-only vs mixed).
- **Frontend**: render tests for podium (2·1·3 order, champion crown, medal colors),
  the "Everyone else" table, the "You" row (logged vs not), and empty/thin states
  (0 and 2 entrants); metric-aware unit/label switch.

## Out of scope (explicit)

- Weight-class / gender segmentation and filter chips — flat board only. Response
  carries per-row `weight_class`/`gender` so filters are additive later. (The
  Plank/Men/Women pills in the desktop mock are the challenge's category tags,
  display-only — not filters.)
- Real poster-frame thumbnails — derived from `<video>` client-side for now.
- Real-time updates / websockets — fetched on page load.
- Historical/podium snapshots — computed live.
- Blended plank + weighted metrics in one board.
- Changes to the global `/leaderboard` page.

## Files touched

| File | Change |
|---|---|
| `backend/toms_gym/services/challenge_leaderboard.py` | **New** — pure `rank_challenge()` (time + weight). |
| `backend/toms_gym/routes/competition_routes.py` | **New** `GET /competitions/<id>/leaderboard`; metric selection; participant query extended with `created_at`, `video_url`, LEFT JOIN `LiftingResult` (hold time, form, annotated clip). |
| `backend/tests/test_challenge_leaderboard.py` | **New** — helper unit tests. |
| `backend/tests/test_competition_routes.py` | Add route tests. |
| `frontend/src/lib/api.ts` | **New** `getChallengeLeaderboard()`. |
| `frontend/src/lib/types.ts` | `ChallengeLeaderboard` / `ChallengeLeaderboardRow`. |
| `frontend/src/pages/ChallengeDetail.tsx` | Redesign body as podium leaderboard + ranked table + "You" row + sticky CTA; keep data-fetch + upload flow. |
| `frontend/src/components/challenge/*` | **New** presentational pieces: `Podium`, `LeaderboardRow`, `YouRow`, `StatusPill` (countdown). Keeps `ChallengeDetail` focused. |
| `frontend/index.html` or theme | Load **Space Grotesk** + **Inter** (or map to existing display/body fonts). |
| `frontend/tailwind.config.ts` | Add medal / brand-blue / display-font tokens as needed. |

## Build order

1. Backend helper + endpoint + tests (metric = time first, the plank path).
2. Mobile `#2b`: hero + status pill, podium, table, "You" row, sticky CTA.
3. Desktop `#1b`: same components, desktop layout + top-right CTA.
4. Weight-metric rendering parity (label/unit switch) + weight tests.
