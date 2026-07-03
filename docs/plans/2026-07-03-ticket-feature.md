# File-a-Ticket Feature (bugs & feature requests)

**Date:** 2026-07-03 · **Status:** in progress (loop-driven)

## Goal
Let any visitor file a bug report or feature request from the app, and let Tom
triage them (view list, flip status). Matches the app's optional-auth model:
no login required, email optional, `user_id` attached when present in
localStorage.

## Data model — `Ticket` (migration 012)
| Column | Type | Notes |
|---|---|---|
| `id` | UUID PK | `gen_random_uuid()` |
| `type` | TEXT | CHECK `('bug','feature')` |
| `title` | TEXT NOT NULL | ≤200 chars (validated in route) |
| `description` | TEXT NOT NULL | ≤5000 chars |
| `page_url` | TEXT | where the issue happened (client-supplied) |
| `contact_email` | TEXT | optional |
| `user_id` | UUID FK → `User` | nullable, `ON DELETE SET NULL` |
| `status` | TEXT | CHECK `('open','in_progress','closed')`, default `'open'` |
| `created_at` / `updated_at` | TIMESTAMPTZ | default `now()` |

Index: `(status, created_at DESC)`.

Migration ships two ways, matching the ShortLink precedent:
`backend/toms_gym/migrations/012_tickets.sql` (record) + idempotent
`CREATE TABLE IF NOT EXISTS` block in `run_startup_migrations()` (applied in
prod on next deploy).

## API — `backend/toms_gym/routes/ticket_routes.py` (`ticket_bp`)
| Endpoint | Method | Notes |
|---|---|---|
| `/tickets` | POST | Public. Body `{type, title, description, page_url?, email?, user_id?}`. Validates type/lengths; 201 → `{ticket_id}`. |
| `/tickets` | GET | List, newest first. Filters `?status=&type=`, `limit` ≤100 default 50. |
| `/tickets/<id>` | GET | Single ticket. 404 if missing. |
| `/tickets/<id>/status` | PUT | Body `{status}`; validates enum; bumps `updated_at`. |

Public like the rest of the app (no admin auth exists yet — known gap from
the 2026-07 strategic review; ticket triage inherits it deliberately).

## Frontend
- `pages/FileTicket.tsx` at **`/feedback`** — Bug/Feature toggle, title,
  description, optional email; sends `user_id` from localStorage and
  `page_url` (referrer) automatically. Success panel with ticket id + link to
  the list.
- `pages/TicketList.tsx` at **`/feedback/list`** — status-tab filter
  (Open / In progress / Closed / All), type badge, relative date, status
  dropdown per row (calls the status endpoint).
- `lib/api.ts`: `createTicket`, `fetchTickets`, `updateTicketStatus` +
  `Ticket` type.
- Entry points: "Feedback" in Navbar `links` (desktop + mobile share the
  array) and footer link in `Layout.tsx`.

## Validation
- Backend: pytest suite `tests/test_ticket_routes.py` following existing
  route-test patterns; must at least run import-safe without the Docker DB.
- Frontend: `vite build` must pass (no `tsc` script; build runs the type
  surface that exists). Jest only if a suitable pattern exists.
- Deploy with `python3 deploy.py --skip-iam`, verify POST + list in prod.
