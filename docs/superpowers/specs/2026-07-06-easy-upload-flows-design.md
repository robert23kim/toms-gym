# Easy Upload Flows — Design Spec

**Date:** 2026-07-06
**Status:** Approved direction (user), pending spec review
**Scope:** Make the two anchor workflows fast for an individual user: (1) upload a plank video to the challenge, (2) upload a golf scorecard and see the resulting handicap. Nothing else.

## Background

The customers are a small friend group. The #1 pain is capture-moment friction on a phone. A three-deck design exploration + two-critic adversarial review (see git history of this session) produced a larger group-oriented design; the user explicitly cut it down to: *"easy to upload my plank video and navigate to the challenge, and upload my golf scores and see my handicap."*

**Explicitly out of scope** (evaluated and dropped): email-in upload, group recap pages/emails, Sunday digest, live plank-off session mode, rivalry OG cards, APK push. The adversarial review killed or deferred all of these; do not resurrect them here.

## Design

### A. Golf: snap → review → see your handicap

**A1 — Camera opens directly.**
`frontend/src/pages/GolfUpload.tsx:133` has `accept="image/*"` with no `capture` attribute, so mobile browsers show a chooser sheet (Photo Library / Take Photo / Choose File) before the camera. Add `capture="environment"` to the file input. One attribute; the camera opens immediately on tap. Desktop behavior is unchanged (attribute is ignored).

Keep a secondary "choose from library" affordance: some users photograph the card at the course but upload later. Implementation: two inputs (one with `capture`, one without) behind "Take photo" / "Choose from library" buttons — or equivalent. The primary CTA is the camera.

**A2 — `/golf/snap` fast route + home-screen shortcut.**
A thin route `/golf/snap` that renders GolfUpload with the camera input auto-triggered on mount (one tap fewer than landing on the form). Register it in `frontend/src/routes/index.tsx`. Add a `shortcuts` entry to `frontend/public/manifest.json` (`"Snap scorecard" → /golf/snap`) so long-pressing the installed app icon (Android/PWA) jumps straight to the camera. The GolfHub primary CTA points at `/golf/snap` on mobile.

Note: browsers require a user gesture for file-input activation in some engines; if auto-trigger on mount is blocked, `/golf/snap` renders a single full-screen "Open camera" button — still 2 taps total from home screen. The GolfHub CTA points at `/golf/snap` unconditionally (no mobile detection); on desktop the camera input degrades to the standard file dialog, which is acceptable.

**A3 — Review stays.** No change to the OCR review pass (`GolfReview.tsx`). It is the safety valve that keeps a misread score from writing a permanent `HandicapSnapshot` (append-only; see the poison-low incident in CLAUDE.md). Do not add any auto-confirm path.

**A4 — Post-confirm: lead with the handicap.**
`GolfReview.handleConfirm` already receives `handicap_index` in the `PUT /golf/round/<id>/scores` response (GolfReview.tsx:266) and flips a `confirmed` state. Redesign the confirmed state to lead with:

- **New handicap index** — large display number (this is the payoff moment)
- **Delta vs. previous index** — ▼/▲ with the same lower-is-better color convention as GolfLeaderboard/GolfProfile (green = down). Previous index comes from the latest `HandicapSnapshot` before this confirm; if the confirm response doesn't carry it, fetch `GET /golf/handicap/<user_id>` *before* confirming and diff client-side. No new backend endpoint unless that proves insufficient.
- Below: round total, differential, links to **Leaderboard** and **My rounds** (GolfProfile).
- If `handicap_index` is null (shouldn't happen post-migration — 1 round now yields a provisional index), show the round summary and a "provisional index pending" line instead of a dash.

### B. Plank: challenge → record → done

**B1 — Challenge reachable in ≤2 taps.**
Add the ongoing plank challenge as a quick link on the LiftHub (`frontend/src/pages/LiftHub.tsx`) — e.g. secondary card "Plank challenge" → `/challenges/<id>`. The hub already links generic Challenges; this adds the direct hop. Source the challenge dynamically (ongoing challenge whose lift type is plank / name match from the competitions API) — do not hardcode a competition id.

**B2 — Camera opens directly in video mode.**
`frontend/src/pages/ChallengeDetail.tsx:879` has `accept="video/*"` with no `capture`. Add `capture` (user-facing camera choice left to OS; `capture="environment"` acceptable) so tapping "Record" opens the camera app in record mode — eliminating the record-in-Camera-app-then-hunt-the-file-picker loop. Keep a "choose existing video" secondary input for pre-recorded uploads, same two-input pattern as A1.

**B3 — Lift type pre-set from challenge context.**
`ChallengeDetail.tsx:80` hardcodes `useState<string>("Squat")`. When the challenge is a plank challenge (derive from the challenge's allowed lift types or name), default `liftType` to `"Plank"` and render the selector as a fixed label (locked, not hidden) when the challenge only admits one type. The existing plank-specific compression branch (`compression: liftType === 'Plank' ? 'fast-only' : 'auto'`, line 197) then engages automatically, preserving the iOS-OOM guard.

**B4 — After upload: existing status flow.** The post-upload path stays exactly as shipped in the UX roadmap (T8): navigate to the status page with honest ETA and auto-refresh; the result lands on the challenge leaderboard. No new work.

## Non-goals / guardrails

- No auto-confirm of OCR scores anywhere. Review is mandatory for golf.
- No new backend endpoints expected. A4 uses existing responses/endpoints; B uses existing upload + status flows. If implementation discovers a genuine need (e.g. previous-index in the confirm response), it is a one-field addition to an existing response, not a new route.
- No email, notification, or group features.
- Don't break desktop: `capture` attributes are mobile-only hints; desktop keeps the file dialog.

## Error handling

- Camera permission denied → the input falls back to the standard picker (browser default); no custom handling needed beyond the existing error states.
- `/golf/snap` auto-trigger blocked by gesture policy → full-screen "Open camera" button fallback (A2).
- Oversized plank videos → existing signed-URL direct-to-GCS upload + compression gates already handle this; unchanged.

## Testing

- Unit (jest): lift-type default derives "Plank" on a plank challenge and "Squat" otherwise; GolfReview confirmed-state renders handicap + delta from a mocked confirm response (delta up/down/null cases); LiftHub renders the plank quick link when an ongoing plank challenge exists.
- Build gates: `npm test`, `npx vite build`, `npx tsc --noEmit`.
- Manual/prod verification (project convention): on a real phone — golf: home-screen shortcut → camera → snap → review → confirm → handicap screen; plank: hub → challenge → record → status page. Verify at the production URL after deploy.

## Rough size

Frontend-only. ~1–2 days including tests and prod verification.

| Piece | Size |
|---|---|
| A1/B2 capture attributes + secondary library inputs | S |
| A2 snap route + manifest shortcut + hub CTA | S |
| A4 handicap-first confirm screen | S–M |
| B1 hub quick link, B3 lift-type pre-set/lock | S |
