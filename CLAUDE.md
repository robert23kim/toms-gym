# Project Preferences

## Deployment
- Always deploy changes and test in production after completing frontend/backend modifications
- Use `python3 deploy.py --frontend-only --skip-iam` for frontend-only changes
- Use `python3 deploy.py --backend-only --skip-iam` for backend-only changes
- Use `python3 deploy.py --skip-iam` for full deployment

## Production URLs
- Frontend: https://my-frontend-quyiiugyoq-ue.a.run.app
- Backend: https://my-python-backend-quyiiugyoq-ue.a.run.app

## Testing
- After deployment, verify changes at the production frontend URL
- For video features, check that links navigate to the correct video player

## Authentication System

### Overview
The app supports **optional authentication**. Users can upload videos and create profiles without setting a password.

### User Types
1. **Passwordless Users**: Created via email-based upload or registration without password
   - Identified by `userId` in localStorage (no auth token)
   - Can view their profile at `/profile/{userId}`
   - Can upload more videos using the same email
   - Session cleared via "Forget Me" button in navbar

2. **Authenticated Users**: Have a password set
   - Full JWT token authentication
   - Access/refresh tokens stored in localStorage
   - Can login/logout normally

### Key Endpoints

#### Backend (`/backend/toms_gym/routes/`)

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/upload` | POST | Upload video. Accepts `user_id` OR `email`. Returns `user_id` in response. |
| `/auth/register` | POST | Register user. Password is optional. |
| `/users/by-email/<email>` | GET | Find user profile by email address |
| `/users/<id>/profile` | GET | Get user profile (no auth required) |

#### Frontend Routes (`/my-frontend/src/routes/index.tsx`)

| Route | Component | Description |
|-------|-----------|-------------|
| `/upload` | UploadVideo | Upload page with optional email field |
| `/profile` | Profile | Current user's profile |
| `/profile/:id` | Profile | View any user's profile by ID |

### User Flows

#### New User Uploads Video (No Account)
1. User visits `/upload`
2. Enters email address (no login needed)
3. Selects video, lift type, weight
4. Uploads video
5. Backend creates user if email doesn't exist
6. Success screen shows link to profile
7. `userId` stored in localStorage for future visits

#### Return User Finds Profile
1. User clicks "Find Profile" in navbar
2. Enters email
3. System calls `GET /users/by-email/{email}`
4. If found: navigates to profile, stores userId
5. If not found: offers to upload a video

#### User Sets Password Later
1. Register via `/auth/register` with password
2. Or create profile with "Set a password (optional)" checkbox

## Features

The app has three independent analysis features alongside the core gym/video flow. Each has its own backend routes and frontend pages.

### Lifting (`backend/toms_gym/routes/lifting_routes.py` + `pages/UploadVideo.tsx`, `VideoPlayer.tsx`)
Users upload lifting videos. An analysis service (Cloud Run `bowling-service`) produces annotated video + rep metrics. Supported lift types include squat, bench, deadlift, bicep curl.

### Bowling (`backend/toms_gym/routes/bowling_routes.py` + `pages/BowlingUpload.tsx`, `BowlingResult.tsx`)
Users upload bowling videos. Analysis detects ball trajectory, lane edges, and entry/pin impact boards. Manual annotation UI at `pages/AnnotationWorkspace.tsx`.

### Golf (`backend/toms_gym/routes/golf_routes.py` + `pages/Golf*.tsx`)
Users photograph a scorecard; OCR (Google Vision API `document_text_detection`) extracts hole scores; user confirms to produce a WHS handicap differential. See "Golf Feature" below.

## Golf Feature

> **Phase B schema migration landed 2026-04-18** (branch `golf/fairway-phase-b`, migration `008_fairway_schema.sql`). The flat `GolfRound` / `GolfHoleScore` / `GolfHandicap` tables were dropped and replaced with the normalized `Course` / `Tee` / `Round` / `HoleScore` / `HandicapSnapshot` model below. PRs or docs written before that date refer to the old shape — see the Field Rename Map at the end of this section.

### Data Model
- **`Course`** — one per golf course: `id` (UUID), `name`, `city`, `state`, `country`, `latitude`, `longitude`, `holes` (9 or 18), `status` (`'verified'` | `'pending'`). `pending` is set by the OCR matcher on a miss; admins promote to `verified`. GIN trigram index on `name` for fuzzy search.
- **`Tee`** — one per tee box per course: `course_id`, `name` (e.g. `"Blue"`), `color_hex`, 18-hole `rating_18` / `slope_18`, optional 9-hole splits (`rating_9_front` / `slope_9_front` / `rating_9_back` / `slope_9_back`), `yardage`, `par`, `hole_pars[]`, `hole_yardages[]`, `hole_handicaps[]` (per-hole stroke-allocation ranks 1..18; null falls back to the flat NDB-10 cap). Slope columns enforce WHS legal range 55–155.
- **`Round`** — one per upload: `user_id`, `course_id`, `tee_id` (nullable until user picks a tee), `played_on` (DATE), `holes` (9 or 18), `scores[]`, `total_score`, `front_nine`, `back_nine`, `score_differential`, `scorecard_image_url`, `ocr_raw` (JSONB: `{text, detected_players}`), `ocr_confidence`, `processing_status`.
- **`HoleScore`** — one per hole (9 or 18 per round): `round_id`, `hole_number`, `par`, `strokes`, `ocr_confidence`, `manually_corrected`. `UNIQUE (round_id, hole_number)`.
- **`HandicapSnapshot`** — append-only handicap history: `user_id`, `handicap_index`, `rounds_used`, `differentials_used` (JSONB), `triggered_by_round_id`, `created_at`. Written on every round save, edit, or delete; indexed by `(user_id, created_at DESC)` for history queries.

### API Endpoints
| Endpoint | Method | Description |
|----------|--------|-------------|
| `/golf/upload` | POST | Multipart form with scorecard image + course data. Accepts `user_id` OR `email`. OCR runs, `services.courses.match_or_create_course` + `match_or_create_tee` link the round. Returns `round_id`, `hole_scores` (primary player), `detected_players`, `needs_tee` (true when no tee could be matched and user must supply rating/slope), and `guest_rounds: [{name, user_id, round_id}]` — one entry per detected player (see "Multi-player auto-save" below). |
| `/golf/round/<id>` | GET | Fetch round with nested `course` and `tee` objects + `hole_scores`, `detected_players`, `needs_tee` for the review UI. |
| `/golf/round/<id>/scores` | PUT | Confirm/correct holes; computes `score_differential` via `services.handicap.compute_differential`, recalculates WHS index, writes a new `HandicapSnapshot`. (Tee-override persistence is a Phase D follow-up — the route does not yet accept `tee_id` overrides.) |
| `/golf/round/<id>` | DELETE | Delete a round and write a recalculated `HandicapSnapshot`. |
| `/golf/rounds?user_id=` | GET | List a user's rounds; each entry carries nested `course` and `tee`. |
| `/golf/handicap/<user_id>` | GET | Current handicap index + differentials used (reads latest `HandicapSnapshot`). |
| `/golf/handicap/<user_id>/recompute` | POST | Force a fresh `HandicapSnapshot` for a user from their stored rounds. Used when engine rules change (e.g. the 1-round minimum below) and existing users need to refresh their index without re-confirming rounds. |
| `/golf/leaderboard` | GET | Global leaderboard sourced from latest `HandicapSnapshot` per user; each row includes `monthly_delta` (30-day handicap change; frontend pill is a Phase D follow-up). |
| `/golf/courses?q=&near=lat,lng` | GET | `pg_trgm` fuzzy search over `Course.name`; optional geo-biased tie-break. |
| `/golf/courses` | POST | Create a new course. Body: `{name, city?, state?, country?, latitude?, longitude?, holes?}`. Authenticated callers create `status='verified'`; anonymous callers create `status='pending'`. |
| `/golf/users/<user_id>/handicap/history?range=6m\|12m\|24m\|all` | GET | Ordered `HandicapSnapshot` series for the trend chart (Phase D dashboard consumer). |

### Handicap Engine (WHS 2020+)

`backend/toms_gym/services/handicap.py` is a pure, DB-free module exposing `net_double_bogey_cap`, `compute_differential`, `compute_handicap_index`, `allocate_strokes`, `apply_twelve_month_cap`. Route code loads rounds, calls these helpers, writes snapshots.

- **Net-double-bogey cap.** Per-hole strokes are capped before the differential is computed. Cap is `par + 2 + strokes_received_on_hole` when a handicap exists; a flat **10** per hole when the user is still establishing. Hole-handicap ranks come from `Tee.hole_handicaps`; the flat-10 fallback kicks in whenever those ranks are missing (OCR rarely extracts them today — see Phase D follow-up).
- **Differential.** `((adjusted_total − rating − PCC) × 113) / slope`. `PCC = 0` (Playing Conditions Calculation is MVP-disabled). Works for both 9- and 18-hole rounds — the route picks the correct rating/slope pair.
- **WHS adjustment table (no 0.96 multiplier).** Final index = `trunc((avg_of_lowest_N + adjustment) × 10) / 10`, capped at 54.0. The pre-2020 `× 0.96` "bonus for excellence" is intentionally omitted per USGA Rules of Handicapping §5.2. Tom's Gym extended the table down to 1-and-2-round states (lowest 1, no adjustment) so a single upload produces a provisional index instead of an empty leaderboard — the 3-round floor in the official spec was dropped for UX reasons.

  | Rounds in pool | Lowest N used | Adjustment |
  |---|---|---|
  | 1 | 1 | 0 (provisional; Tom's Gym extension) |
  | 2 | 1 | 0 (provisional; Tom's Gym extension) |
  | 3 | 1 | −2.0 |
  | 4 | 1 | −1.0 |
  | 5 | 1 | 0 |
  | 6 | 2 | −1.0 |
  | 7–8 | 2 | 0 |
  | 9–11 | 3 | 0 |
  | 12–14 | 4 | 0 |
  | 15–16 | 5 | 0 |
  | 17–18 | 6 | 0 |
  | 19 | 7 | 0 |
  | 20+ | 8 | 0 |

- **Establishing state.** Only triggered at `effective < 1` (i.e. no rounds at all) → `handicap_index=None`, `status="establishing"`, `rounds_needed=1`.
- **12-month low cap.** A user's index cannot rise more than **5.0** above their lowest index in the preceding 12 months (`apply_twelve_month_cap`). The cap only prevents rises — it never pushes the index down.
- **9-hole rounds.** Weighted at **0.5** toward the "last 20" pool. `_effective_round_count` = full 18-hole rounds + (nine-hole rounds // 2).
- **Reference fixtures.** `backend/tests/fixtures/whs_reference_cases.json` + `backend/tests/test_handicap.py` exercise every adjustment-table row plus NDB cap, establishing, 12-month cap, and 9-hole weighting. Any handicap change must re-pass this fixture bit-for-bit.

### OCR Parser (multi-player)
`_parse_scorecard_symbols(symbols, page_width, page_height)` in `golf_routes.py` operates on **symbol-level** Vision output (not words — Vision tends to concatenate handwritten digits into garbage tokens like `"7864856T65854494444"`).

Pipeline:
1. Group symbols into rows by y-proximity (~2% of page height).
2. For each row, skip if it has too many letters (label/tee row) or too few digits (hole-number or blank row).
3. Extract the leftmost contiguous letter cluster as the player's name; reject known labels (`PAR`, `HANDICAP`, `BLACK`, `GOLD`, `GREEN`, `WHITE`, …) and label prefixes.
4. Cluster the row's digits by x-gap: single-digit clusters are hole scores; multi-digit clusters (`"56"`, `"105"`) are subtotals (OUT/IN/TOT) and used as column separators.
5. First 9 singles before the OUT subtotal = front 9; first 9 singles between OUT and IN = back 9.
6. Return `{players: [{name, holes: [{hole_number, par, strokes, ocr_confidence}] x18}, ...]}`.

Image rotation: `_auto_orient_image` only applies EXIF transpose. If the parser detects no players, the upload route retries OCR on a 90°-rotated copy and keeps whichever pass produced more players. It does **not** force portrait orientation (that was a previous bug that broke valid landscape scorecards).

### Multi-player auto-save (`_save_guest_player_round`)

When OCR returns two or more players on the same scorecard (e.g. TOM and CHRIS), the upload route auto-creates a guest `User` for each detected name and saves a fully-confirmed `Round` + `HoleScore` rows under that guest, in addition to the uploader's own primary round. Each guest then appears on the leaderboard with their own handicap.

Keys:
- **Deterministic email.** A detected name maps to `<slug>@guest.tomsgym.local` (slug = lowercased alphanumeric). Same name across uploads → same guest user → handicap accumulates instead of duplicating.
- **Auto-confirm.** Differential is computed at upload with the flat NDB-10 cap (`min(strokes, 10)` per hole), the round is stored with `processing_status='confirmed'`, and a `HandicapSnapshot` is written via `_recalculate_handicap`. No human review step required.
- **Failure isolation.** Each guest save runs in a try/except; a single guest failure logs a warning and rolls back that sub-transaction without killing the uploader's primary round.
- **Auth-method nullable.** Guest `User` inserts leave `auth_method` NULL because the enum only covers `('google','password')`; the guest path is neither.

### Leaderboard stale-snapshot filter

The leaderboard query picks the most-recent `HandicapSnapshot` per user with a subquery pattern:

```sql
SELECT user_id, handicap_index, rounds_used, created_at
FROM (
    SELECT DISTINCT ON (user_id)
           user_id, handicap_index, rounds_used, created_at
    FROM "HandicapSnapshot"
    ORDER BY user_id, created_at DESC
) _latest
WHERE handicap_index IS NOT NULL
```

The `WHERE handicap_index IS NOT NULL` must run **outside** `DISTINCT ON`. Doing it inside would let a stale non-null snapshot outrank a later null one, so a user who deletes all their rounds would stick around on the leaderboard with their old index. Keep this inversion on any future snapshot-based query.

### Avatars (`getGolfAvatar(name, id)`)

`frontend/src/lib/api.ts` exposes `getGolfAvatar(name, id)` — a DiceBear `avataaars` URL helper used by `GolfLeaderboard` and `GolfProfile`. A `KNOWN_GOLFER_AVATARS` map carries hand-tuned presets for recurring fictional names (today: `tom` = tanned skin / dark hair / hoodie, `chris` = lighter skin / curly hair / beard / sweater). Unknown names fall back to a deterministic avataaars seeded by the name (or `id` when name is missing), so the same golfer keeps the same face across visits. The older `getGhibliAvatar` (Pokémon sprites) is still used by lifting/challenges UI — don't remove it.

### Tests
- `tests/test_golf_parser.py` — pytest suite covering helpers + end-to-end multi-player parsing against a real OCR fixture (`tests/fixtures/golf_scorecard_ocr.json`).
- `tools/run_golf_parser_tests.py` — standalone runner that bypasses the DB-heavy conftest. Use this for quick iteration: `cd backend && venv/bin/python tools/run_golf_parser_tests.py`.
- `tools/ocr_inspect3.py` — debug tool: runs Vision API on a local image and prints symbol-level row/column layout. Requires `GOOGLE_APPLICATION_CREDENTIALS=backend/credentials.json`.

### Frontend Pages
| Route | Component | Description |
|-------|-----------|-------------|
| `/golf/upload` | `GolfUpload` | Scorecard upload + course info form. |
| `/golf/review/:roundId` | `GolfReview` | OCR result review: shows detected players, lets user pick their row, edit scores, confirm. A "Change" link on the course/tee header opens `TeePickerDrawer` (`frontend/src/components/golf/TeePickerDrawer.tsx`) — up to 4 tee cards, editable rating (step 0.1) / slope (step 1) / yardage, `DifficultyMeter` anchored at slope 113, and a live differential preview. Selected tee carries the `fw-selected` class (2px `fw-info` border from Phase A). |
| `/golf/round/:roundId` | `GolfRound` | Completed round detail; reads nested `course` / `tee`. |
| `/golf/leaderboard` | `GolfLeaderboard` | Handicap leaderboard; rows are fed from latest `HandicapSnapshot` per user. |
| `/golf/profile/:userId?` | `GolfProfile` | User's golf stats and rounds. Consumes `GET /golf/users/:id/handicap/history` for the handicap trend (Phase D dashboard surface). |

### Field Rename Map (Phase A → Phase B)
Anyone reading pre-2026-04-18 PRs, branches, or issues should map old flat fields onto the new nested shape:

| Old (flat) | New (nested) |
|---|---|
| `course_rating` | `tee.rating_18` |
| `slope_rating` | `tee.slope_18` |
| `course_name` | `course.name` |
| `played_at` | `played_on` |
| `differential` | `score_differential` |
| `adjusted_gross_score` | `total_score` |
| `holes: GolfHole[]` (array) | `hole_scores: GolfHole[]` |
| `holes` (top-level) | now a number: `9` or `18` (round length) |
| `GolfHandicap.handicap_index` | latest `HandicapSnapshot.handicap_index` |

## Secrets Management

Production secrets are stored in **GCP Secret Manager** and injected into Cloud Run at runtime via `--set-secrets`. See `docs/secrets-management-plan.md` for the full audit and migration plan.

### GCP Secret Manager Secrets
| Secret Name | Used For | Env Var |
|-------------|----------|---------|
| `jwt-secret` | JWT token signing | `JWT_SECRET_KEY` |
| `db-password` | Cloud SQL authentication | `DB_PASS` |
| `email-app-password` | Gmail SMTP/IMAP | `EMAIL_PASSWORD` |

### Key Rules
- **Never hardcode secrets** in source code, deploy scripts, or config files
- `deploy.py` uses `--set-secrets` for sensitive values and `--set-env-vars` for non-sensitive config
- Deploy command logging redacts `--set-env-vars` and `--set-secrets` values
- Flask app has **no fallback defaults** for secrets in production — missing secrets cause a startup error
- `.dockerignore` files in `backend/` and `frontend/` exclude `.env`, credentials, and key files

### Updating a Secret
```bash
echo -n "NEW_VALUE" | gcloud secrets versions add SECRET_NAME --data-file=- --project=toms-gym
# Then trigger a new Cloud Run revision to pick it up:
gcloud run services update my-python-backend --region=us-east1 --set-secrets=JWT_SECRET_KEY=jwt-secret:latest,DB_PASS=db-password:latest,EMAIL_PASSWORD=email-app-password:latest
```

## Agent Personas

Custom agent personas are defined in `.claude/agents/`. When spawning a team, read these files first to understand the available roles and their constraints:
**Note:** Always spin up a manager agent when starting a team.
**Note:** When a team is requested, spin up all available personas at the beginning.

- **manager** — Delegates tasks, reviews work, produces executive summaries. Cannot edit code.
- **creative** — Rapid prototyping and experimentation. Full tool access.
- **doer** — Heads-down implementer. Takes a task and drives it to completion autonomously. Full tool access.
- **qa** — Regression testing and edge case verification. Cannot edit production code.
- **architect** — Designs system boundaries, trade-offs, and migration plans. Cannot edit code.
- **reviewer** — Code review for correctness, regressions, and missing tests. Cannot edit code.
- **performance** — Profiling, bottlenecks, and measurable speedups. Full tool access.
- **data-quality** — Validates annotations, datasets, and evaluation integrity. Full tool access.
- **docs** — Documentation updates and runbooks. Full tool access.

## Team Spawning Notes

**Delegate mode limitation**: When a team lead enters delegate mode, spawned teammates may lose access to file/shell tools (Bash, Read, Write, Edit, Grep, Glob) even if their persona specifies them. To avoid this:
- Spawn implementation agents using the Task tool with `run_in_background: true` instead of as team members in delegate mode
- Or avoid delegate mode entirely — use regular teams where the lead retains full tool access
- Agents that only need to research/plan (architect, reviewer) work fine in delegate mode since they primarily use messaging
- Agents that need to run code, read files, or edit code (doer, creative, qa, performance, data-quality) must NOT be spawned from within delegate mode

### Key Files Modified

| File | Changes |
|------|---------|
| `backend/.../upload_routes.py` | Returns `user_id` in upload response |
| `backend/.../user_routes.py` | Added `/users/by-email/<email>` endpoint |
| `backend/.../auth_routes.py` | Made password optional in register |
| `frontend/.../UploadVideo.tsx` | Email field for non-logged-in users |
| `frontend/.../Profile.tsx` | No auth required, works with URL param |
| `frontend/.../CreateProfile.tsx` | Password optional (hidden by default) |
| `frontend/.../FindProfile.tsx` | New component for email lookup |
| `frontend/.../Navbar.tsx` | Find Profile button, Forget Me for passwordless |
| `frontend/.../AuthContext.tsx` | Handles passwordless user state |
| `frontend/.../routes/index.tsx` | Added `/profile/:id` route |
