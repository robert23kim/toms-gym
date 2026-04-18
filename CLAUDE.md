# Project Preferences

## Deployment
- Always deploy changes and test in production after completing frontend/backend modifications
- Use `python3 deploy.py --frontend-only --skip-iam` for frontend-only changes
- Use `python3 deploy.py --backend-only --skip-iam` for backend-only changes
- Use `python3 deploy.py --skip-iam` for full deployment

## Production URLs
- Frontend: https://toms-gym-web-quyiiugyoq-ue.a.run.app
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

### Data Model
- **`GolfRound`** — one per upload: `user_id`, `course_name`, `slope_rating`, `course_rating`, `adjusted_gross_score`, `differential`, `scorecard_image_url`, `ocr_raw` (JSONB: `{text, detected_players}`), `ocr_confidence`, `processing_status`.
- **`GolfHoleScore`** — one per hole (18 per round): `round_id`, `hole_number`, `par`, `strokes`, `ocr_confidence`, `manually_corrected`.
- **`GolfHandicap`** — one per user: `handicap_index`, `rounds_used`, `differentials_used` (USGA WHS formula; needs ≥3 confirmed rounds).

### API Endpoints
| Endpoint | Method | Description |
|----------|--------|-------------|
| `/golf/upload` | POST | Multipart form with scorecard image + course data. Accepts `user_id` OR `email`. Returns `round_id`, `holes` (primary player), `detected_players` (all detected). |
| `/golf/round/<id>` | GET | Fetch round + holes + `detected_players` for the review UI. |
| `/golf/round/<id>/scores` | PUT | Confirm/correct 18 holes; computes differential + recalculates handicap. |
| `/golf/round/<id>` | DELETE | Delete a round and recalculate handicap. |
| `/golf/rounds?user_id=` | GET | List a user's rounds with holes. |
| `/golf/handicap/<user_id>` | GET | Current handicap index + differentials used. |
| `/golf/leaderboard` | GET | Global handicap leaderboard. |

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

### Tests
- `tests/test_golf_parser.py` — pytest suite covering helpers + end-to-end multi-player parsing against a real OCR fixture (`tests/fixtures/golf_scorecard_ocr.json`).
- `tools/run_golf_parser_tests.py` — standalone runner that bypasses the DB-heavy conftest. Use this for quick iteration: `cd backend && venv/bin/python tools/run_golf_parser_tests.py`.
- `tools/ocr_inspect3.py` — debug tool: runs Vision API on a local image and prints symbol-level row/column layout. Requires `GOOGLE_APPLICATION_CREDENTIALS=backend/credentials.json`.

### Frontend Pages
| Route | Component | Description |
|-------|-----------|-------------|
| `/golf/upload` | `GolfUpload` | Scorecard upload + course info form. |
| `/golf/review/:roundId` | `GolfReview` | OCR result review: shows detected players, lets user pick their row, edit scores, confirm. |
| `/golf/round/:roundId` | `GolfRound` | Completed round detail. |
| `/golf/leaderboard` | `GolfLeaderboard` | Handicap leaderboard. |
| `/golf/profile/:userId?` | `GolfProfile` | User's golf stats and rounds. |

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
