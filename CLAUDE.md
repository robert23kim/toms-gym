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
Users photograph a scorecard — nothing else to type. The grid parser (`services/scorecard_grid.py`: OpenCV rectification + table-line detection + Vision OCR symbols assigned to cells) extracts players, per-hole scores, pars, and tee rating/slopes; the review page resolves course/tee/date; confirming produces a WHS handicap differential. See `docs/reference/golf.md`.

### Tickets (`backend/toms_gym/routes/ticket_routes.py` + `pages/FileTicket.tsx`, `pages/TicketList.tsx`)
Bug reports and feature requests, shipped 2026-07-03 (design: `docs/plans/2026-07-03-ticket-feature.md`). `Ticket` table via migration 012 (startup-migration pattern, like ShortLink). `POST /tickets` is public (optional-auth model); `GET /tickets`, `GET /tickets/<id>` and `PUT .../status` require header `X-Admin-Token` matching the `ADMIN_TOKEN` env (GCP secret `admin-token`, wired in `deploy.py`; 503 if unset, 401 on mismatch). The `/feedback/list` page prompts for the token and keeps it in localStorage `adminToken`. Endpoints: `POST /tickets` (`{type: bug|feature, title, description, page_url?, email?, user_id?}` — invalid `user_id` is dropped via FK retry, never rejected), `GET /tickets?status=&type=&limit=` (newest first, limit capped at 100), `GET /tickets/<id>`, `PUT /tickets/<id>/status` (`open|in_progress|closed`). Frontend: `/feedback` form (auto-attaches localStorage `userId` + referrer) and `/feedback/list` triage page (status tabs, optimistic status select); linked from navbar and footer. Admin gate shipped 2026-08-28 (ticket ecbcf8dd). Footer 'Request a feature' links `/feedback?type=feature` (FileTicket reads the param). `lib/staleChunk.ts` reloads once on Vite `vite:preloadError` so post-deploy stale-chunk imports self-heal (ticket b761fc1e). Tests: `tests/test_ticket_routes.py` (needs a Postgres, e.g. `docker run --rm -d -p 5434:5432 -e POSTGRES_PASSWORD=test -e POSTGRES_DB=toms_gym_test postgres:15` + `DATABASE_URL=postgresql://postgres:test@localhost:5434/toms_gym_test`).

## Working Rules (apply to every change)

- **Gates:** backend `PYTHON=venv/bin/python tools/run_ci_tests.sh` (DB-free; register new suites there); frontend `npx tsc --noEmit` + jest. There is no eslint config in `frontend/`. Read jest results via `node node_modules/jest/bin/jest.js --json --outputFile=<path>` (the shell hook rewrites jest stdout). `jest.setup.js` stubs `localStorage` with `jest.fn()`: mock `getItem`'s return value, `setItem` is a no-op. Page tests mock `../../config` (Vite `import.meta`) and stub `Layout`/`Navbar`.
- **tsc does not catch scope bugs.** A block-scoped name read from component scope shipped `metric is not defined` to prod. Render changed pages in a browser, especially `ChallengeDetail`.
- **Bare ISO dates parse as UTC** and render a day early. Use `` new Date(`${iso}T00:00:00`) `` or `lib/dates.ts` (`formatDay`, `todayLocal`).
- **Migrations** are startup migrations inline in `app.py` (latest: **019**, `Situp` lift type). pg8000 binds ints as ints: use `make_interval(days => :days)`, not `CURRENT_DATE - :days`.
- **Leaderboards:** build through `_leaderboard_payload(session, competition_id)` in `competition_routes.py`, never a second query (it carries the `is_test` exclusion and metric selection). Adding a column to the leaderboard SQL means updating `_prow` in `tests/test_competition_routes.py` in the same change.
- **Test accounts** (`User.is_test`) are excluded from boards and emails, not from their own profile reads.
- **Playwright prod checks:** call `page.unrouteAll` first (routes persist across runs); wait ~1 s after the first navigation post-deploy (`lib/staleChunk.ts` self-reloads); use a *function* matcher in `page.route` (a glob `*` does not cross `/`); never let a verification write: fulfil the PUT.
- **Phone vs desktop is split by width** (`md` = 768px), never by platform. Phones and the APK get `BottomTabBar` + the Home to-do list.
- **Analysis engine** lives in `~/code/bowling-app/analysis-engine` (Cloud Run `bowling-service`). Prod runs the **unmerged** `feat/situp-config` (off the also unmerged `feat/pushup-config`). **Never run its `deploy.sh`** (it drops env vars): `gcloud builds submit --tag …` then `gcloud run services update --image …`, from a **clean checkout** (the main tree has uncommitted deletions that break the bowling analyzer). Its venv is `.venv/`, not `bowlingenv/`. Details: `docs/reference/situp-challenge.md`, `docs/reference/pushup-challenge.md`.

## Reference Docs (read before working in the area)

Each file holds the full notes that used to live here: design decisions, endpoints, gotchas, test suites, open follow-ups. **Read the matching file before changing that area, and add new notes there, not here.** This file gets one line per feature.

| Area | Read | One-line summary |
|---|---|---|
| Golf (OCR, WHS handicap, data model, API) | `docs/reference/golf.md` | Photo-only scorecard upload → grid parser (`services/scorecard_grid.py`, legacy symbol parser as fallback) → review → WHS differential. Pure engine in `services/handicap.py`. |
| Bowling score sheets | `docs/reference/bowling-score-sheets.md` | Lane-monitor photo → Vision OCR → DB-free parser → review, `save_as` per bowler, insights. Fixtures must match truth exactly. |
| Situp challenge | `docs/reference/situp-challenge.md` | `reps` metric where form changes the score (clean full, sloppy half); tracked pose; engine deploy recipe. |
| Pushup challenge | `docs/reference/pushup-challenge.md` | `reps` metric, set-oriented result page, frontend copy overrides, untuned ROM thresholds. |
| Challenge champions / Hall of Champions | `docs/reference/challenge-champions.md`, `hall-of-champions.md` | Computed on read from ended challenges (no table), `/champions` page, avatar packs. |
| Challenge attempt history / plank nicknames | `docs/reference/challenge-attempt-history.md`, `plank-nicknames.md` | Expandable attempts per athlete; nicknames from `body_line_stdev_deg`. |
| Plank stats / lift history | `docs/reference/plank-stats.md`, `lift-history.md` | `lib/plankStats.ts` + `PlankSteadiness`; `GET /users/<id>/lifts` paginated. |
| Activity streak | `docs/reference/activity-streak.md` | `GET /users/<id>/activity`, streak math client-side in `lib/streak.ts`. |
| Home / navigation shell | `docs/reference/finch-shell.md`, `home-redesign.md`, `ux-roadmap.md`, `easy-upload-flows.md` | Bottom tabs + to-do home; hubs; camera-first capture; status page, completion email, share cards, magic-link sign-in. |
| Android app | `docs/reference/android-app.md` | Capacitor 7 in `frontend/android`; `npm run android:build` / `android:publish`; emulator smoke test. |
| Delight loop | `docs/reference/delight-loop.md` | One folder per tick in `docs/delight/`; start from the previous bug log; **top-3 picks must create a moment, friction fixes go to the bug log.** |
| Bowling lane research | `RULES.md` in each of `docs/research/2026-09-12-sam2-lane-experiments`, `2026-09-12-cheap-lane-model`, `2026-09-13-lane-landmarks`, `2026-09-14-alley-face`, `2026-09-13-engine-lane-integration` | Rules learned per loop. Engine integration is on branch `feat/sam-lane-calibration` (worktree `~/code/bowling-app/lane-engine`), **not deployed**. |
| Auth history | `docs/reference/auth-key-files.md` | Files touched by the passwordless change. |

### Rules that bite without reading the doc

- **Golf:** `HandicapSnapshot` is append-only and the 12-month cap MINs over it, so a garbage low from a deleted round clamps every future index; cleanup is direct SQL + `POST /golf/handicap/<id>/recompute`. On snapshot queries, `WHERE handicap_index IS NOT NULL` goes **outside** `DISTINCT ON`. Any handicap change must re-pass `tests/fixtures/whs_reference_cases.json`. `GET /users/:id/profile` nests under `.user`.
- **Bowling sheets:** Vision returns nothing usable on a 180° photo, so the 0/180/90/270 OCR retry is load-bearing. Keep `SILENT-WRONG` at zero in `tools/bowling_sheet_stress.py`.
- **Challenges:** a weighted or multi-category challenge links to `/challenges/<id>`, never the bare `/challenges/<id>/upload` (defaults to Squat). Bodyweight lifts (Plank, Pushup, Situp) hide weight and post `0`.
- **`DELETE /attempts/<id>` 500s on analysed attempts** (no cascade from `LiftingResult`/`AnalysisNotification`); there is no user-delete route. Test data cleanup is SQL.
- **Android:** APK web assets go stale with every frontend deploy until rebuilt; publish objects are versioned per build on purpose.

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

