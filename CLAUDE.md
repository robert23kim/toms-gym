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
Users photograph a scorecard — nothing else to type. The grid parser (`services/scorecard_grid.py`: OpenCV rectification + table-line detection + Vision OCR symbols assigned to cells) extracts players, per-hole scores, pars, and tee rating/slopes; the review page resolves course/tee/date; confirming produces a WHS handicap differential. See "Golf Feature" below.

### Tickets (`backend/toms_gym/routes/ticket_routes.py` + `pages/FileTicket.tsx`, `pages/TicketList.tsx`)
Bug reports and feature requests, shipped 2026-07-03 (design: `docs/plans/2026-07-03-ticket-feature.md`). `Ticket` table via migration 012 (startup-migration pattern, like ShortLink). `POST /tickets` is public (optional-auth model); `GET /tickets`, `GET /tickets/<id>` and `PUT .../status` require header `X-Admin-Token` matching the `ADMIN_TOKEN` env (GCP secret `admin-token`, wired in `deploy.py`; 503 if unset, 401 on mismatch). The `/feedback/list` page prompts for the token and keeps it in localStorage `adminToken`. Endpoints: `POST /tickets` (`{type: bug|feature, title, description, page_url?, email?, user_id?}` — invalid `user_id` is dropped via FK retry, never rejected), `GET /tickets?status=&type=&limit=` (newest first, limit capped at 100), `GET /tickets/<id>`, `PUT /tickets/<id>/status` (`open|in_progress|closed`). Frontend: `/feedback` form (auto-attaches localStorage `userId` + referrer) and `/feedback/list` triage page (status tabs, optimistic status select); linked from navbar and footer. Admin gate shipped 2026-08-28 (ticket ecbcf8dd). Footer 'Request a feature' links `/feedback?type=feature` (FileTicket reads the param). `lib/staleChunk.ts` reloads once on Vite `vite:preloadError` so post-deploy stale-chunk imports self-heal (ticket b761fc1e). Tests: `tests/test_ticket_routes.py` (needs a Postgres, e.g. `docker run --rm -d -p 5434:5432 -e POSTGRES_PASSWORD=test -e POSTGRES_DB=toms_gym_test postgres:15` + `DATABASE_URL=postgresql://postgres:test@localhost:5434/toms_gym_test`).

## UX Roadmap (shipped 2026-07-06)

Full plan + task breakdown: `docs/plans/2026-07-06-ux-roadmap.md`. Realigned the app around its analysis features ("upload → analysis → come back to track progress"). All 16 product tasks (T1–T16) shipped; the reliability track (T17) is deferred. Highlights and where they live:

- **Bot/e2e purge (T1).** `User.is_test BOOLEAN` (migration `013_user_is_test.sql`, startup-backfilled by name/email pattern — `e2e-lift-%`, `T30G Upload Bot`, `*.local` except golf guests). Excluded from Top Lifts / `/leaderboard` / challenge leaderboards in `competition_routes.py` via `AND COALESCE(u.is_test,false)=false`; profile reads are NOT filtered so a test account still sees its own data. Also used to skip completion/magic-link emails.
- **Challenge podium fix (T2).** Leaderboard join was `status='completed'` (only set after analysis succeeds), so pending weight-board uploads scored 0 and rendered "No entries yet". Now joins any non-failed attempt with a video (`competition_routes.py` + `services/challenge_leaderboard.py`). Plank/time boards unaffected.
- **Nav / IA (T3, T5, T6, T7).** Navbar has top-level **Lift / Bowl / Golf** hubs (`pages/LiftHub|BowlHub|GolfHub.tsx` via shared `components/HubPage.tsx`). `/upload` is now a chooser (`UploadChooser.tsx`); lifting upload moved to `/lift/upload` (`/upload/lift` redirects). Landing (`Index.tsx`) leads with analysis value + 3 feature cards. Honest copy (no fake prizes, passwordless messaging). `/athletes` deleted (was mock data). Real `/terms` + `/privacy` pages.
- **Post-upload status (T8).** `pages/AnalysisStatus.tsx` at `/lift/status/:attemptId` + `/bowling/status/:attemptId` polls the existing per-attempt result endpoints (404 = queued), honest ETA copy, survives reload. Upload pages navigate here instead of a dead-end success screen (lifting upload now also triggers analysis).
- **Completion email (T9).** `integrations/analysis_notify.py` — on lifting/bowling completion, emails the uploader a ShortLink to the result. Idempotent via an `AnalysisNotification` ledger; wrapped so SMTP failure never blocks completion; skips `is_test`/undeliverable addresses. Reuses the `email_upload.py` SMTP config (`EMAIL_PASSWORD` secret).
- **Results for humans (T10, T11, T12).** Bowling result leads with consumer stats (entry board, est. speed, hook, pocket) with debug behind an "Advanced" toggle (`bowlingStats.ts`, `BowlingStatCard.tsx`). Lifting rep breakdown shows plain-language coaching per failed metric (`lib/liftCoaching.ts`, fixture-tested copy map keyed by lift/metric/pass-fail). Low-detection results (bowling `detection_rate < 0.25`; lifting plank `pose_detection_rate < 0.25` or rep lifts `total_reps === 0`) show filming tips + retry CTA.
- **Share cards (T13).** `integrations/og_card.py` (Pillow, no new dep) renders a 1200×630 OG card cached to GCS (`og-cards/<code>.png`). The **backend** `/s/<code>` route branches crawler (server-rendered `og:*` meta) vs human (302 to SPA result); the SPA `ShortLinkRedirect` still handles frontend-origin links. Share buttons (`lib/share.ts`) on `VideoPlayer`, `BowlingResult`, `GolfRound`. NOTE: T9's emailed short-links still use the frontend origin so they don't unfurl yet — point them at the backend origin to fix (open follow-up).
- **Unified profile hub (T14).** `pages/Profile.tsx` is now a Lift/Bowl/Golf tabbed hub at `/profile/:id`, cross-linked with `/golf/profile/:userId` both ways. Added `GET /bowling/results?user_id=`. "Find Profile" promoted to full-page `/find-profile` (nav item repointed; the old `FindProfile.tsx` dialog is now dead code — safe to delete in a follow-up).
- **Magic-link sign-in (T15).** `POST /auth/magic-link` + `GET /auth/magic/<token>` (`routes/auth_routes.py`, pure logic in `services/magic_link.py`). Token TABLE `MagicLinkToken` (migration `014_magic_link_tokens.sql`) stores only SHA-256 hashes; single-use (atomic `UPDATE ... WHERE used_at IS NULL AND expires_at > now()`), 15-min expiry, per-email rate-limit (≥3/15min silently drops), and NO email enumeration (always 200 generic). Frontend `/signin` (request) + `/auth/magic/:token` (consume, restores localStorage userId + optional JWT), reachable from `/find-profile`.
- **Golf delta pill (T16).** Signed ▲/▼ pill on `GolfLeaderboard` rows from `monthly_delta` (see Golf API table).

Startup migrations now run through `013` (is_test) and `014` (magic-link tokens). CI test suites added: `test_analysis_notify.py`, `test_og_card.py`, `test_magic_link.py` (all registered in `tools/run_ci_tests.sh`, DB-free). New frontend jest suites for `bowlingStats`, `liftCoaching`, `AnalysisStatus`, `MagicLink`.

## Easy Upload Flows (shipped 2026-07-06)

Frontend-only, camera-first capture. Plan: `docs/superpowers/plans/2026-07-06-easy-upload-flows.md`; spec: `docs/superpowers/specs/2026-07-06-easy-upload-flows-design.md`. No backend changes.

- **Camera-first scorecard capture.** `GolfUpload.tsx` now renders two hidden inputs — `#golf-scorecard-upload` (library, no `capture`) and `#golf-scorecard-camera` (`capture="environment"`); "Capture photo" targets the camera one. New `autoCamera` prop auto-clicks the camera input on mount (browsers that need a user gesture ignore it — the button remains). New route `/golf/snap` = `<GolfUpload autoCamera />`, wired as a PWA `shortcuts` entry in `public/manifest.json` and as GolfHub's primary CTA (`/golf/upload` still works).
- **Handicap-first post-confirm screen.** New `components/golf/HandicapResultCard.tsx` leads with the hero handicap index + a signed ▲/▼ delta vs. the pre-confirm snapshot (lower = green improvement, matching GolfLeaderboard's pill). `GolfReview.tsx` fetches the previous index via `GET /golf/handicap/<user_id>` (non-fatal read, doesn't touch snapshot history) and renders the card in the confirmed state. OCR review logic is untouched — no auto-confirm.
- **Record-now challenge video.** New `components/challenge/VideoCaptureInput.tsx` = two affordances: "Record now" (`#challenge-video-camera`, `capture="environment"`) opens the phone camera directly, "Choose existing video" (`#challenge-video-upload`, unchanged id) keeps the library picker. Wired into `ChallengeDetail.tsx`. Plank lift-type pre-set/lock was already implemented.
- **LiftHub plank quick link.** `LiftHub.tsx` fetches `getCompetitions()` and prepends a "Plank challenge" secondary link → `/challenges/<id>` when an ongoing challenge has the `Plank` category (uses the transformed shape: `title`/`status`/`categories`).
- **Tests.** New jest suites: `GolfUpload`, `HandicapResultCard`, `VideoCaptureInput`, `LiftHub` (page tests mock `../../config` — Vite `import.meta` — and stub `Layout`/`FairwayScope` for CSS/tree isolation). Full suite: 40 suites / 272 tests green. Camera `capture` behavior itself is only truly verifiable on a real phone.

## Home Redesign + Quiet-Gym Cohesion (shipped 2026-07-06)

Minimal, centered home page + app-wide visual language. Spec: `docs/superpowers/specs/2026-07-06-home-redesign-cohesion-design.md` (mockup asset committed alongside); plan: `docs/superpowers/plans/2026-07-06-home-redesign-cohesion.md`. Frontend-only.

- **Shared primitives** (`frontend/src/components/`): `AmbientBackground` (fixed doodle-wallpaper + 3 drifting glow layers, mounted once in `Layout` → every page), `IconTile` (centered icon-chip link tile), `RowCard` (slim row: icon · title · pill · "Open →"), `DemoLoop` (home-only 12s CSS/SVG loop: plank hold + timer → bowling trace → scorecard scan; keyframes in `index.css` as `demo-*`/`ambient-*`; all reduced-motion aware).
- **Index rebuilt**: hero → DemoLoop → 3 IconTiles (`/lift/upload`, `/bowling/upload`, `/golf/snap`) → "Open challenges" strip (`getCompetitions()` filtered to `status==='ongoing'`, RowCards → `/challenges/:id`; whole strip hidden when none). Removed: TopLifts sidebar (component file retained, now unused), photo cards, How It Works, featured-challenge cards/filters.
- **Layout footer**: centered "Report a bug · Request a feature · Terms · Privacy · v{APP_VERSION}" (bug/feature → `/feedback`); copyright line dropped.
- **Page passes**: `HubPage` centered w/ RowCard secondary links (descriptions no longer rendered on hubs); `UploadChooser` = same IconTiles as home (golf → `/golf/snap`); `Challenges` centered header + "Open now" RowCard strip + pill filters; `Leaderboard` pill filters. Golf `fw-*` internals untouched.
- **Tests**: `Index`, `IconTile`, `RowCard`, `AmbientBackground`, `DemoLoop`, `LayoutFooter` suites (page tests mock `../../config` + stub Navbar/Layout). Suite at ship: 46 suites / 282 tests.

## Plank Stats v1 (shipped 2026-07-06)

Steadiness pack + personality on the plank VideoPlayer result. Spec: `docs/superpowers/specs/2026-07-06-plank-stats-v1-design.md`; plan: `docs/superpowers/plans/2026-07-06-plank-stats-v1.md`. **Frontend-only** — renders the plank report's `per_second[]` (`{t, state, body_line_deg, elbow_deg, form_score}`), which the engine has emitted since day one but the UI never used (verified present on prod reports; stale reports refresh via the existing re-analyze endpoint).

- **`lib/plankStats.ts`** — pure fixture-tested helpers: `holdRuns`, `steadinessScore` (clamp(100−stdev×10); ≥85 Rock Solid / 70 Steady / 50 Wobbly / else Jelly Mode), `wobbleEvents` (Δ>2.5° between consecutive in_plank seconds, 2s merge keeping larger delta), `decayPoint` (first ≥5s window of form<0.7), `milestones` (30/60/120/180s cumulative hold → video-time of crossing), `personality` (priority: Jelly 🪼 ≥4 wobbles or stdev>4 → Phoenix 🔥 dip≥0.15-below-rolling-avg then recovery → Slow Melter 🫠 OLS slope<−0.002/s → Statue 🗿 stdev≤1.5 & ≤1 wobble → Steady Eddie 💪; null under 10 hold seconds).
- **`components/lifting/PlankSteadiness.tsx`** — score pill + personality badge, custom-SVG timeline (state bands with labeled key, form area+line, wobble diamonds, milestone ticks, decay annotation, hover crosshair + readout, playhead), hold-segments strip. **Pointer on chart → `onSeek(t)`** (seek only, never autoplay). Renders null without per_second.
- **VideoPlayer wiring** — both video elements (annotated + original) share `videoRef` and report `timeupdate` → playhead; the steadiness card sits above the existing plank stat list, which remains the no-per_second fallback.
- Tests: `lib/__tests__/plankStats.test.ts` (18 threshold-pinned cases), `PlankSteadiness.test.tsx` (jsdom note: dispatch `MouseEvent("pointerdown")` — jsdom lacks PointerEvent so `fireEvent.pointerDown` drops clientX). Suite at ship: 48 suites / 304 tests.
- v2 candidates (not built): PB tracking vs past attempts, challenge percentile, elbow-angle viz.

## Lift History on Profile (shipped 2026-07-06)

Fixes "past lifts are invisible": the profile endpoint's `uploaded_videos` is hard-capped at LIMIT 10 (unchanged — still feeds the thumbnail gallery), so a proper history now lives beside it. Spec: `docs/superpowers/specs/2026-07-06-lift-history-design.md`; plan: `docs/superpowers/plans/2026-07-06-lift-history.md`.

- **`GET /users/<id>/lifts?limit=&offset=`** (upgraded in place — the old unpaginated/broken version had zero consumers): Attempt ⋈ UserCompetition ⋈ Competition ⟕ LiftingResult, newest first, `limit` default 20 cap 50, returns `{lifts, total, limit, offset}`. Grade/hold extracted in SQL via JSONB `->>` (`overall_grade`, `total_in_plank_s`, report `lift_type`) so `per_second` never ships on list rows. Row shaping is DB-free in `services/lift_history.py` (`shape_lift_row`), tested in `tests/test_lift_history.py` (registered in `run_ci_tests.sh`).
- **`components/profile/LiftHistoryList.tsx`** — paginated rows on the Profile Lift tab (above the gallery): date · lift type (report lift_type wins over the attempt's) · weight (hidden for planks) · payoff (plank `m:ss` hold / colored grade pill / "analyzing…" / "—"), row links to `/challenges/{comp}/participants/{user}/video/{attempt}`. "Load more" while `lifts.length < total`; renders nothing on empty/error.
- Suite at ship: frontend 49/307; backend CI gate 138.

## Challenge Attempt History (shipped 2026-07-06)

Expandable per-athlete attempt history on challenge leaderboards. Spec: `docs/superpowers/specs/2026-07-06-challenge-attempt-history-design.md`; plan: `docs/superpowers/plans/2026-07-06-challenge-attempt-history.md`.

- **Backend:** `GET /users/<id>/lifts` gained an optional `competition_id` filter (WHERE clause on page + COUNT; the clause is a fixed literal toggled by presence — no injection surface).
- **`components/challenge/AttemptHistory.tsx`** — lazy panel fetched on expand: date · payoff (time boards: `m:ss` hold; weight boards: kg + grade pill) · 🏆 on the metric-best (only when >1 valued attempt) · links to the attempt's VideoPlayer route.
- **Chips:** `LeaderboardRow` + `YouRow` (entered) accept optional `{attemptCount, expanded, onToggleAttempts}` and render an `N attempts ▾` chip at count > 1. **Podium members** (top 3 — usually the multi-attempt users) get a chips strip *below* the podium instead (podium cards stay pure visuals). `ChallengeDetail` holds a single-open accordion (`expandedAttemptsUserId`).
- Suite at ship: 50 suites / 312 frontend tests; backend gate 138.

## Plank Steadiness Nicknames (shipped 2026-07-06)

Funny steadiness-based nicknames on the plank challenge. Spec: `docs/superpowers/specs/2026-07-06-plank-steadiness-nicknames-design.md`; plan: `docs/superpowers/plans/2026-07-06-plank-steadiness-nicknames.md`. Derived from the plank report's `body_line_stdev_deg` (one number — NOT `per_second`, which never ships on list rows); the video-page `personality()` archetypes are untouched.

- **`lib/plankStats.ts`** — two pure fixture-tested helpers. `steadinessNickname(stdev)` → per-attempt base name via the existing `steadinessScore` bands: ≥85 🗿 Statue / ≥70 💪 Steady Eddie / ≥50 🌊 The Wobbler / else 🪼 Human Jellyfish (null stdev → null → no badge). `athleteNickname({stdevDeg, attemptCount, uploadDates})` → base + volume/cadence modifier, first match wins: **One-Shot** (1 attempt) > **Relentless** (≥4 attempts, median upload gap ≤1d) > **The Elusive** (≥2 attempts, a ≥14d gap) > none. Cadence gaps computed from `uploadDates` (nulls dropped, sorted internally).
- **Backend:** one new surfaced field, `body_line_stdev_deg AS steadiness`, added to the leaderboard query (`competition_routes.py` → `_rank_time` carries the **best attempt's** value onto the row) and the lift-history query (`user_routes.py` + `shape_lift_row`). Weight boards ignore it. `attempt_count` + `history[].date` (cadence inputs) were already on the leaderboard row.
- **`components/challenge/NicknameBadge.tsx`** — muted pill; renders nothing when nickname is null. Placements (time/plank challenges only): per-attempt in `AttemptHistory` (`steadinessNickname`), athlete-level on `LeaderboardRow`/`YouRow` and podium chips in `ChallengeDetail` (`athleteNickname`). Podium chips strip now shows for any top-3 with a nickname OR >1 attempt.
- **Gotcha fixed in prod:** `ChallengeDetail`'s `rowNickname` first read `metric`, which is block-scoped (destructured from `leaderboard` inside the render IIFE) → runtime `metric is not defined`; tsc did NOT catch it. Reads component-scoped `leaderboard?.metric` instead. This class of scope bug is only caught by rendering the page — verify challenge-page changes in a browser, not just tsc.
- Suite at ship: 51 suites / 332 frontend tests; backend gate 142.

## Challenge Champions (shipped 2026-08-01)

Crowns the winner of any ended challenge — trophy case, title flair, avatar pack, confetti, and a front-page spotlight. Spec: `docs/superpowers/specs/2026-08-01-challenge-champions-design.md`; plan: `docs/superpowers/plans/2026-08-01-challenge-champions.md`. Newest champion: wonder725 (Summer plank challenge, 4:35). **Because champions are computed over *all* ended challenges, turning this on retroactively crowned every past winner** — day one shipped with three champions (wonder725 plus two older Toka wins, Biceps and Bench and New Powerlifting Challenge). That is intended, but it means "champion" is not a going-forward-only award.

- **Computed on read, no Champion table.** A champion is rank 1 (with a truthy score) of an ended challenge's leaderboard. `services/champions.py::shape_champions` is pure; `GET /champions?user_id=` (`competition_routes.py`) iterates `end_date < NOW()` challenges and caches the result in-process for 10 min, so late re-analyses self-correct. Deleting the cache tier is safe; deleting the recompute is not. **The cache covers `/champions` only** — `achievement_routes.py::_championship_count` re-runs the same per-ended-challenge scan uncached on every `GET /users/<id>/achievements` (and twice more on `PUT /avatar`), so that endpoint's cost grows linearly with the number of ended challenges. Worth sharing the cache if the ladder ever gets a UI that loads it on every profile view.
- **Leaderboard builder extracted.** The per-challenge leaderboard body moved out of the route into `_leaderboard_payload(session, competition_id)` (returns `None` when the competition is missing; the route still 404s). Champions reuse it, inheriting the `is_test` exclusion and metric selection for free — do NOT duplicate that query.
- **Avatar unlocks build on the achievements ladder** (branch `achievements/milestone-avatar-unlocks`, merged here). `services/achievements.py` gained a 7th pack — **champion** (`big-smile` seeds) — plus pure `pack_hint`/`locked_packs`/`unlocked_avatars`. `champion` is a *pack key, not a LADDER tier*: `evaluate()` never emits it; `achievement_routes.py` appends it when the user holds ≥1 championship. `badge_total()` stays 6.
- **Routes:** `GET /users/<id>/achievements` (ladder, earned, next, `avatars: [{key,url}]`, `locked_packs`, current `avatar`) and `PUT /users/<id>/avatar` (400 on a locked/unknown key). The catalog resolves to URLs **server-side** — the frontend never holds the catalog. Profile endpoint now returns `user.avatar_url`. Migration **015** adds `User.avatar TEXT` (startup-migration pattern, inline in `app.py` like 013/014).
- **Frontend:** `components/profile/TrophyCase.tsx` (🏆 card per win + exported `championTitle`), `ChampionConfetti.tsx` (CSS `confetti-fall` keyframes, one-shot per `(competition, viewer)` in localStorage, reduced-motion aware), `AvatarPicker.tsx` (owner-only; locked packs show their milestone hint), `components/ChampionSpotlight.tsx` on `Index.tsx`. 👑 renders on `LeaderboardRow` (`isChampion` prop) and on `ChallengeDetail`'s podium chips — the champion is rank 1, so the **podium chip** is where it actually shows; the row prop covers non-podium edge cases.
- **Gotcha:** bare ISO dates (`ended_on: "2026-07-31"`) parse as UTC and render a day early west of Greenwich — the trophy case shipped this bug and was caught in the browser, not by tsc or jest. Parse as `` new Date(`${iso}T00:00:00`) `` (same trick as `LeaderboardRow.formatDate`).
- Cosmetic overlap to know about: the pre-existing `plank_royalty` ladder tier also uses 👑, so the picker's locked list can show a crown next to a non-champion milestone.
- **Shipped surface is narrower than the 2026-07-06 achievements plan.** `GET /users/<id>/achievements` serves `ladder` + `next` (progress toward the next milestone), but **nothing renders them** — the planned `BadgeStrip` / `MilestonePath` components were never built and `frontend/src/components/achievements/` does not exist. Likewise the chosen avatar shows **only on the profile header**; `LeaderboardRow`, `Podium`, `MomentumLine`, the golf pages, and even `ChampionSpotlight` itself still call the deterministic `getGolfAvatar(name, id)`, so a champion's picked avatar does not follow them onto the boards or their own front-page card. Both are open follow-ups, not bugs.
- Suite at ship: 56 suites / 351 frontend tests; backend gate 160.

## Hall of Champions (shipped 2026-08-28)

`/champions` replaced the old mock-data `/leaderboard` (now a redirect; `pages/Leaderboard.tsx` deleted). Lift hub + `NAV_LINKS` point here. Reads `GET /champions` — no new tables.

- **Backend:** `services/champions.py::shape_champions` now also emits `runners_up` (ranks 2–3 with a valued score), `field_size`, `margin` (winner − runner-up, null when unopposed), `winner_attempts`, `won_on` — all derived from the existing leaderboard payload. Frontend treats them as optional.
- **Frontend:** `lib/championStats.ts` (pure, fixture-tested: `championTally`, `dynastyLabel` 2=Back-to-back / 3=Three-peat / N×, `ordinalWin`, `marginCopy` with a per-metric "photo finish" threshold 5s/2.5kg/1rep, `reignDays`, `groupByYear`). `components/champions/ChampionHero` (newest win: laurel conic ring + floating crown + shimmer name — `laurel-ring`/`crown-float`/`hall-shimmer` keyframes in `index.css`, reduced-motion aware; field/attempts/reign tiles; Watch / profile / Share via `lib/share.ts`), `ChampionCard` (wall of fame, "Nth title" pill, "You" pill), `NextToBeCrowned` (ongoing challenges → current leader + days left via `getChallengeLeaderboard`). Viewer who is a champion sees "Your reign" + `ChampionConfetti` keyed `("hall", userId)`.
- `formatChampionScore` now handles `reps`; `Champion.metric` is `ChampionMetric` (time|weight|reps).
- Suite at ship: frontend 61 suites / 411 tests; backend gate 174.

## Activity Streak (shipped 2026-08-28)

Home-page "Your streak" card (Strava-style): flame with consecutive-week count + Mon–Sun strip of this week's active days. `GET /users/<id>/activity?days=` (`user_routes.py`) unions lift/bowl `Attempt.created_at` (video present; kind = bowl when a `BowlingResult` exists) with golf `Round.played_on` (noon-stamped). Streak math is client-side in `lib/streak.ts` (`computeStreak`, local time, Mon-start weeks; an empty current week does not break the streak, an empty previous week does). `components/StreakCard.tsx` reads localStorage `userId`, hides itself for anonymous visitors or on fetch failure; Share reuses `lib/share.ts` pointing at the profile. Gotcha: pg8000 binds ints as ints, so date arithmetic needs `make_interval(days => :days)`, not `CURRENT_DATE - :days`. Tests: `lib/__tests__/streak.test.ts`, `components/__tests__/StreakCard.test.tsx`.

## Pushup Challenge (shipped 2026-08-01)

Third challenge metric — `reps` — alongside `time` (plank) and `weight` (lifting). Spec: `docs/superpowers/specs/2026-08-01-pushup-challenge-design.md`; plan: `docs/superpowers/plans/2026-08-01-pushup-challenge.md`. Live challenge: `4bd57523-1ecf-4e4e-92c9-06ac594e05ee`.

- **Engine deployed** as `bowling-service-00047-tdf` from branch `feat/pushup-config` (worktree `/tmp/pushup-engine`, repo `~/code/bowling-app/analysis-engine`) — **the branch is not merged**; merge it before the next engine deploy or the pushup config is lost. Rollback target: `bowling-service-00046-c76`.
- **⚠️ Deploying the engine: do NOT run `deploy.sh` as-is.** Its `--set-env-vars` omits `NORMALIZE_BEFORE_ANALYZE=true`, which IS set on the live service — running the script would silently drop it. Build, then `gcloud run deploy` passing all three (`GCS_BUCKET_NAME`, `PLANK_POSE_WORKERS=8`, `NORMALIZE_BEFORE_ANALYZE=true`). Also build from a **clean checkout**: the main tree carries 59 uncommitted deletions of `src/detectors/`+`src/labeling/`, and `src/pipeline.py` imports `src.detectors` at module level, so building from it ships a broken bowling analyzer.
- **Analyzer (pending):** a `pushup` entry in `EXERCISE_CONFIGS` reusing the generic elbow-angle peak-detection rep pipeline — no new analyzer math. `rom_extension_deg` 155 / `rom_contraction_deg` 90, `elbow_drift` weighted 0 (hands planted). **ROM thresholds are untuned guesses** — no real pushup video exists in either repo, so rep-count accuracy has NOT been validated on real footage; only synthetic skeletons (which do exercise the real `analyze_from_skeletons` → `build_lift_summary` path, counting 3/5/8 cycles correctly). Also unverified: pose/camera-view auto-detection on prone bodies (a different regime from standing lifts), and whether the relaxed `MAX_ELBOW_SWING_PCT=500` is needed at all (synthetic geometry yields only ~64%, which passed at the old 100% too). Config **routing IS verified** — the same real clip analyzed as `pushup` vs `bicep_curl` yields different overall scores (66.1 vs 51.6), so the pushup weights and ROM band demonstrably apply.
- **Bug found and fixed while wiring this up:** `rom_extension_deg`/`rom_contraction_deg` were read **only** on the `is_deadlift` branch of `analysis/analyze.py`, so for every other lift they were dead config. Pushups were being graded against `score_rom`'s curl defaults (160°/60°) even though a pushup bottoms near 90°, marking every rep as partial ROM (`rom_score` 46.9 → 72.2 on the same clip once fixed). The fix is scoped to `lift_type == "pushup"`; **bicep_curl and squat are deliberately left on the module defaults** — squat's config says 170/90, so honoring it would silently re-baseline every existing squat grade. That generalization is a real follow-up, not a cleanup.
- **Backend:** migration **016** adds `Pushup` to the `lift_type` enum (startup-migration pattern, verified applied in prod). `_rank_reps` in `services/challenge_leaderboard.py` mirrors `_rank_time`: score = **best single attempt's** rep count (not cumulative), tiebreak form score then earliest. Leaderboard SQL surfaces `lr.report->>'total_reps' AS reps`; metric selection maps declared `{"Pushup"}` → `reps` (plus all-Pushup inference). No new storage — `total_reps` was always in `LiftingResult.report`.
- **Result page is set-oriented, not rep-oriented.** Pushups render ONE "Set Breakdown" card — `lib/setSummary.ts` (`summarizeSet`, pure + fixture-tested) averages each metric across reps and counts how many passed; aggregate status is `pass` only if every rep passed, `warn` at ≥half, else `fail` (it never invents a numeric threshold the engine didn't supply). The separate "Rep-by-Rep Details" table is hidden. Other lifts keep per-rep cards — this is **scoped to pushups on purpose**, not a global change.
- **Copy is overridden frontend-side, deliberately.** The engine bakes `label`/`description` into every report from its bicep_curl `METRIC_TARGETS`, so a pushup report literally read "how much of the full curl range you used". `METRIC_COPY_OVERRIDES` in `lib/liftCoaching.ts` remaps them (rom→**Depth**, elbow_stability→**Elbow Flare**, shoulder_swing→**Body Line**) plus a `pushup` coaching block. Doing it here rather than in the engine fixes **already-analyzed** reports with no re-analysis. If you later add a `PUSHUP_METRIC_TARGETS` engine block, delete these overrides or they'll mask it.
- **Weight is hidden for bodyweight lifts** (`isBodyweightLift` = plank | pushup) on the result header AND the share-card blurb — the old checks were `!== 'plank'` in both places.
- **Frontend:** `ChallengeMetric` gained `"reps"`; `metric.ts` returns `REPS`/`reps`/"Upload your pushups". `AttemptHistory` has a third render branch ("N reps" + grade pill). `isBodyweightLift()` (module-level in both `ChallengeDetail` and `UploadVideo`, deliberately NOT block-scoped — see the plank-nickname scope-bug gotcha) hides the weight field for Plank+Pushup. `UploadVideo` posts weight `0` for pushups; its `parseFloat("")` guard would otherwise have blocked the upload.
- **Known real-world risk (found via synthetic testing, not yet seen on real footage):** `_add_boundary_peaks` in `rep_segmenter.py` deliberately drops a final boundary peak when the signal tail is still rising >30°/s, treating it as a video cut off mid-movement. A pushup video where **recording stops the instant the last rep tops out will under-count by one.** Real sets usually end held at lockout, so this may never bite — but check it on the first real clip before touching the guard.
- **Gotcha found in review:** adding a column to the leaderboard SQL broke 5 route tests because `_prow` in `test_competition_routes.py` models the query result — fixture and query must be updated together.
- **Analyzer venv gotcha:** the engine's venv is **`.venv/`**. `bowlingenv/` also exists but lacks mediapipe, and running the suite under it produces 3-4 spurious `test_estimator` failures that look like pre-existing breakage but are not. `venv/` (per older docs) doesn't exist at all.
- Suite at ship: backend gate **172 passed**; frontend **357 passed**, tsc clean; analyzer branch **202 passed, 2 skipped, 0 failed** (baseline was 197 passed).

## Bowling Score Sheets (shipped 2026-08-28)

Photograph the lane monitor — the end-of-night **RESULTS** screen (Player · Game 1-3 · Scratch · Hdcp · Total) or a per-game **End of game** frame strip — and the app parses, stores and mines it for "things to work on". Spec: `docs/superpowers/specs/2026-08-28-bowling-scoresheet-design.md`; plan: `docs/superpowers/plans/2026-08-28-bowling-scoresheet.md`. Same path as golf: Vision OCR → deterministic DB-free parser → checksum validation → review page. (Gemini on Vertex was probed and works but is deliberately not used — no IAM/secret, and the parser is testable offline.)

- **Tables (migration 017):** `BowlingScoreSheet` (uploader, `sheet_type` night|game, `played_on`, `image_url`, `raw_parse` JSONB, `processing_status` parsed|failed|confirmed, `team_name`) and `BowlingGame` (one row per player × game: `player_name`, `game_number`, `total_score`, `hdcp` per game, `frames` JSONB `[[roll symbols]]` for game screens, `computed_total`, `flagged`/`flag_reason`, `confidence`). `user_id` on a game is NULL until the uploader claims that player's row on the review page — league-mates are never turned into users (unlike golf guests).
- **Routes** (`routes/bowling_sheet_routes.py`, prefix `/bowling`): `POST /scoresheet/upload` (multipart `image`, `user_id`|`email`, `sheet_type`, `played_on?`; retries OCR at 0/180/90/270° and keeps the parse with the most clean rows — **Vision returns nothing usable on a 180° screen**, so the retry is load-bearing), `GET /scoresheet/<id>`, `PUT /scoresheet/<id>/confirm` (`{claim_player, players:[{name, games:[{game_number,total_score,hdcp?,frames?}]}]}`), `DELETE /scoresheet/<id>`, `GET /games?user_id=`, `GET /insights/<user_id>`.
- **Pure services:** `services/bowling_score.py` (ten-pin rules incl. 10th frame; `score_frames`, `validate_night_row`, `infer_night_row`), `services/bowling_sheet_parser.py` (`parse_sheet`, `shape_games`), `services/bowling_insights.py` (`compute_insights` → averages, trend, G1/G2/G3 slot averages, stdev; strike/spare/open %, first-ball avg, per-frame strike heatmap when frames exist; rule-based `tips`), `services/vision_ocr.py` (shared word+symbol extraction).
- **Parser gotchas learned on real photos:** night sheets — numbers sit ~⅓ row below their name and perspective skews rows *unevenly* across columns, so a full column is assigned to players by rank order, not nearest-y (de-skewed nearest-y is only the fallback for a missing cell); the Team block's `Game 1/2/3` header digits must be excluded or they land in the player columns; one glare-hidden cell is inferred from the two checksums (`sum(games)==scratch`, `scratch+hdcp==total`) and marked `inferred`, any other mismatch flags. Game screens — Vision drops `-` glyphs and merges `9/9/9` across cells, and reads `10` as `IO`; roll glyphs are binned at **symbol** level into frame cells fitted from the `1..10` header, then a constraint solver reconstructs legal frames matching the **printed running score** (which Vision reads cleanly); a glyph that contradicts the printed score flags the row. The highlighted "current bowler" row draws its rolls *above* the name, so bands are cut between running-score lines, not around names.
- **Fixtures:** `backend/tests/fixtures/bowling/<stem>.jpg` + `<stem>_ocr.json` (cached Vision dump) + `<stem>_truth.json` (hand-checked, checksum-verified). `tests/test_bowling_sheet_parser.py` must match truth exactly (128/128 cells at ship: night_01, night_03, game_01; night_02/night_04 truth exists but photos were never saved to disk). Refresh/extend with `GOOGLE_APPLICATION_CREDENTIALS=credentials.json venv/bin/python tools/bowling_sheet_debug.py [--refresh] [--rotate 180] [stem]` — prints a per-photo cell hit-rate.
- **Frontend:** `/bowling/snap` (camera-first, `BowlingSheetUpload autoCamera`) and `/bowling/scoresheet/upload`; `/bowling/scoresheet/:id` review (`BowlingSheetReview` — editable totals or a `FrameStrip` with live `lib/bowlingScore.ts` running score, flagged rows amber, "This is me" claim); `/bowling/insights/:userId` (`me` resolves from localStorage). BowlHub primary is now the snap flow; Profile Bowl tab shows recent sheet games + Insights link.

## Delight Loop (started 2026-08-29)

Recurring product-quality loop, one folder per tick under `docs/delight/<date>-iteration-NN/`:
personas (P1 Priya first-timer · P2 Marcus bowler · P3 Dana golfer · P4 Tom regular · P5 Sam
lost-session) → Playwright walk of production at 390×844 with per-route metrics (height, CTA
count, horizontal overflow, console errors) → idea list → critical review with an explicit
**clutter / duplicate-information** lens → top 3 shipped → verified in prod → bug log (every
bug seen, fixed or not) + retro. Iteration 01 shipped the profile Lift-tab de-clutter
(6941→2012px), the "See your result" deep-link from `/lift/status` (backend `/lifting/result`
now returns `user_id`/`competition_id`), the returning-user home (no pitch/demo when
`localStorage.userId` exists) and the `/challenges` pill-wrap fix. Start the next tick from the
previous doc's bug log. **Rule since iteration 02: each top-3 pick must create a moment
(recognition / progress / surprise) at an emotional peak — friction fixes go to the bug log.**
Iteration 02 shipped the result-page **ladder** (`lib/standing.ts` extended with `below`,
`podiumGap`, `personalBest`, `attemptScore`, `metricForLift`; `components/challenge/ResultLadder.tsx`
— rank, the athlete above/below with gaps, new-best pill, Beat-this for visitors), the waiting-screen
target (`/lift/status/:id?challenge=<id>`), and the completion reveal (number → grade → ladder).
`deriveStanding` also feeds the older challenge-page `StandingCard` — extend it, don't fork it. Gotchas: `tools/run_ci_tests.sh` needs `PYTHON=venv/bin/python`; get
jest results via `node node_modules/jest/bin/jest.js --json --outputFile=…` (the shell hook
rewrites jest stdout); `jest.setup.js` stubs `localStorage` with `jest.fn()` — mock
`getItem`'s return value, `setItem` is a no-op.

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
| `/golf/upload` | POST | Multipart form: scorecard image + `user_id` OR `email` — everything else optional (photo-only since migration 011). The grid parser extracts players/pars/tees; `course_name` (optional) links via `match_or_create_course`; card-printed tee rating/slopes auto-create `Tee` rows when the course is known. Returns `round_id`, `hole_scores`, `detected_players` (holes carry `flagged`), `detected_tees`, `needs_tee`, `needs_course`, `parser` (`grid`\|`legacy`), and `guest_rounds` (see "Multi-player auto-save"). |
| `/golf/round/<id>` | GET | Fetch round with nested `course` (nullable) and `tee` objects + `hole_scores`, `detected_players`, `detected_tees`, `needs_tee`, `needs_course` for the review UI. |
| `/golf/round/<id>/scores` | PUT | Confirm/correct holes; also accepts review-page overrides: `course_id` or `course_name`, `tee_id` or `rating`+`slope` (+`tee_name`), and `played_on` (YYYY-MM-DD). Computes `score_differential`, recalculates WHS index, writes a new `HandicapSnapshot`. |
| `/golf/round/<id>` | DELETE | Delete a round and write a recalculated `HandicapSnapshot`. |
| `/golf/rounds?user_id=` | GET | List a user's rounds; each entry carries nested `course` and `tee`. |
| `/golf/handicap/<user_id>` | GET | Current handicap index + differentials used (reads latest `HandicapSnapshot`). |
| `/golf/handicap/<user_id>/recompute` | POST | Force a fresh `HandicapSnapshot` for a user from their stored rounds. Used when engine rules change (e.g. the 1-round minimum below) and existing users need to refresh their index without re-confirming rounds. |
| `/golf/leaderboard` | GET | Global leaderboard sourced from latest `HandicapSnapshot` per user; each row includes `monthly_delta` (30-day handicap change). The frontend renders a signed ▲/▼ pill on `GolfLeaderboard` rows (lower-is-better: negative delta = green improvement); zero/null deltas render nothing. |
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
- **Snapshot poison-lows.** `HandicapSnapshot` is append-only and the cap MINs over it — so a garbage low from a since-deleted bug-era round silently clamps every future index (Paul sat at 9.0 with a real 25.0 until his orphaned 4.0 snapshot was purged, 2026-07-02). Deleting a round does NOT remove the snapshots it produced, and there is no API for snapshot deletion — cleanup is direct SQL + `POST /golf/handicap/<id>/recompute`. If an index looks impossibly low or won't rise after good rounds, check snapshot history before suspecting the engine.
- **9-hole rounds.** Weighted at **0.5** toward the "last 20" pool. `_effective_round_count` = full 18-hole rounds + (nine-hole rounds // 2).
- **Reference fixtures.** `backend/tests/fixtures/whs_reference_cases.json` + `backend/tests/test_handicap.py` exercise every adjustment-table row plus NDB cap, establishing, 12-month cap, and 9-hole weighting. Any handicap change must re-pass this fixture bit-for-bit.

### Grid parser (primary since 2026-07-02)

`services/scorecard_grid.py` — pure, DB-free. Pipeline: card-quad detection →
vanishing-point metric rectification from the table's own Hough line families
(the quad alone is unreliable: clips/pavement pollute it) → morphological
h/v line profiles → cell matrix → Vision OCR symbols (from ONE pass on the
original image) mapped through the composed homography into cells → semantic
labeling (PAR row anchors the 18 hole columns; multi-digit par-row cells are
OUT/IN/TOT) → per-cell scores with confidence → checksum validation against
handwritten OUT/IN/TOT (mismatch flags the lowest-confidence hole, never
silently accepts) → tee rating/slopes from y-banded `NN.N/NNN` text lines
(grid rows merge under clips; y-banding after rectification doesn't).

Measured on `tests/fixtures/scorecards/`: 55/55 score cells, 36/36 pars,
10/10 tees (baseline with the legacy parser: 18/55). Tests:
`venv/bin/python -m pytest tests/test_scorecard_grid.py --noconftest`;
debug overlays + hit-rate report: `venv/bin/python tools/grid_debug.py`.
Gotchas learned on real cards: Vision double-emits glyphs (dedupe at <12px
— wider merges legit repeated digits like slope "116"); handwritten names
straddle printed row lines (nameless digit rows adopt an adjacent name row);
tee rows are half the height of header rows so grid rows can merge them.

Falls back to the legacy symbol parser below (`GridParseError`, zero players,
or any crash), which remains fully functional.

### Legacy OCR Parser (multi-player fallback)
`_parse_scorecard_symbols(symbols, page_width, page_height)` in `golf_routes.py` operates on **symbol-level** Vision output (not words — Vision tends to concatenate handwritten digits into garbage tokens like `"7864856T65854494444"`).

Pipeline:
1. Group symbols into rows by y-proximity (~2% of page height).
2. Run `_extract_pars` (see below) on all symbols to recover the per-hole par sequence. This happens once per scorecard and is shared across every detected player.
3. For each row, skip if it has too many letters (label/tee row) or too few digits (hole-number or blank row).
4. Extract the leftmost contiguous letter cluster as the player's name; reject known labels (`PAR`, `HANDICAP`, `BLACK`, `GOLD`, `GREEN`, `WHITE`, …) and label prefixes.
5. Cluster the row's digits by x-gap: single-digit clusters are hole scores; multi-digit clusters (`"56"`, `"105"`) are subtotals (OUT/IN/TOT) and used as column separators.
6. First 9 singles before the OUT subtotal = front 9; first 9 singles between OUT and IN = back 9.
7. Return `{players: [{name, holes: [{hole_number, par, strokes, ocr_confidence}] x18}, ...]}` with each hole's `par` pulled from the extracted sequence (falls back to `4` only when extraction fails).

Image rotation: `_auto_orient_image` only applies EXIF transpose. If the parser detects no players, the upload route retries OCR on a 90°-rotated copy and keeps whichever pass produced more players. It does **not** force portrait orientation (that was a previous bug that broke valid landscape scorecards).

### Par-row extraction (`_extract_pars`)

Per-hole pars come from the scorecard itself (not a hardcoded 4). The extractor lives next to the player parser in `golf_routes.py` and is driven by three helpers:

1. **`_find_par_label(symbols)`** — locates the `PAR` anchor. Requires three letters `P`–`A`–`R` consecutive in x with consistent y (within 20 px), and rejects any match where a fourth letter follows within 100 px (so `PARTICIPANT` / `PART` / `PARK` can't masquerade as the PAR row).
2. **`_fit_row_slope(symbols, anchor_y, anchor_x)`** — scorecard photos are tilted a few degrees from the camera, so the PAR row's y drifts by ~150 px across 3500 px of x (typical slope ≈ -0.04). The helper iteratively fits OLS (y vs. x) across 3 passes — wide y-band (±180 px), then tighten (±90), then tighten again (±55) — so noise from adjacent rows (HANDICAP, tee yardages) gets squeezed out.
3. **`_extract_pars(...)`** — projects the slope-adjusted y-line from the PAR anchor, keeps digits within ±tolerance (≈1.5% of page height), clusters them by x-gap, treats multi-digit clusters as OUT/IN/TOT subtotals (separator between the two nines), and keeps only single-digit values in the legal 3–6 range. Returns a list of 18 pars, or `None` if fewer than 14 could be recovered (in which case the caller falls back to par-4).

The fixture scorecard (`tests/fixtures/golf_scorecard_ocr.json`) recovers `[4,4,3,5,5,4,4,3,4, 4,4,4,5,3,4,5,3,4]` — front 36 / back 36 / total 72. `tools/run_golf_parser_tests.py` covers the happy path, the `None`-when-absent path, and the end-to-end wiring into player holes.

### Multi-player auto-save (`_save_guest_player_round`)

When OCR returns two or more players on the same scorecard (e.g. TOM and CHRIS), the upload route auto-creates a guest `User` for each detected name and saves a fully-confirmed `Round` + `HoleScore` rows under that guest, in addition to the uploader's own primary round. Each guest then appears on the leaderboard with their own handicap.

Keys:
- **Deterministic email.** A detected name maps to `<slug>@guest.tomsgym.local` (slug = lowercased alphanumeric). Same name across uploads → same guest user → handicap accumulates instead of duplicating.
- **Auto-confirm.** Differential is computed at upload with the flat NDB-10 cap (`min(strokes, 10)` per hole), the round is stored with `processing_status='confirmed'`, and a `HandicapSnapshot` is written via `_recalculate_handicap`. No human review step required.
- **Partial rounds** (`_classify_guest_round`): <6 captured holes → not saved; exactly 9 in one nine → saved as a 9-hole round whose differential is scored against half the 18-hole rating then **doubled** to an 18-hole equivalent (raw 9-hole diffs are ~half scale and would always win the lowest-N pool — a back-nine-only card once hit the leaderboard at -42.0); exactly 18 → scored normally; anything else → saved for display, `score_differential` NULL (invisible to the handicap engine).
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
| `/golf/profile/:userId?` | `GolfProfile` | User's golf stats and rounds. Consumes `GET /golf/users/:id/handicap/history` for the handicap trend (Phase D dashboard surface). Each expanded round renders a compact 9-up hole grid showing `#` / `Par N` / strokes with color-coded cells (birdie / par / bogey+). The scorecard thumbnail is clickable and opens a fullscreen lightbox (Escape or click-outside to close, body scroll locked) so the user can verify OCR scores against the physical card. Reads the user name from `GET /users/:id/profile` via `profileRes.data.user.name` — note the `.user` nesting; the endpoint wraps user fields (`{user: {name, email, ...}, competitions: [...], ...}`) and early code that read `profileRes.data.name` silently fell through to the avatar's fallback seed. |

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
