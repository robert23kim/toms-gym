# UX Assessment & Roadmap — 2026-07-06

> **Status (2026-07-06): SHIPPED.** All 16 product tasks (T1–T16, Phases 1–4) were implemented, validated, integrated on branch `ux-roadmap`, and deployed to production. T17 (reliability track) is deferred — see `PLANS.md`. Implementation notes live in the "UX Roadmap (shipped 2026-07-06)" section of `CLAUDE.md`. Two flagged follow-ups: (1) T9's emailed short-links use the frontend origin so they don't unfurl — repoint at the backend `/s/<code>`; (2) `frontend/src/components/FindProfile.tsx` dialog is now dead code (recovery moved to `/find-profile`).

Based on the full production walk (`docs/site-map/README.md`, 23 screenshots incl. mobile) plus the 2026-07 strategic review. This is the user-experience companion to the infrastructure priorities already tracked there.

## The high-level diagnosis

**The app's identity and its value are out of sync.** The navigation, landing page, and copy all sell a *competition platform* (challenges, prize pools, judging, "Register → Record → Compete"). But the actual magic — what no other app gives users — is the *analysis*: annotated lift videos with per-rep grades, bowling ball trajectory tracking, and photo-to-handicap golf scoring. Those three features are buried one, two, or three clicks behind competition chrome, and one of them (bowling) isn't in the nav at all.

Everything below follows from realigning around: **"Upload something → get analysis you can't get anywhere else → come back to track progress."**

## Findings (ranked by user impact)

### F1. The analysis features are hidden
- No "Upload" or "Analyze" in the navbar. Lifting upload is only on the home page; bowling upload is only reachable via a home-page challenge card; Golf nav lands on the *leaderboard*, not the camera.
- `/athletes` is orphaned entirely.
- A new user cannot answer "what does this app do for me?" from the nav.

### F2. Demo/test data pollutes first impressions
- "Top Lifts This Month" shows `e2e-lift-1772469238377` and `T30G Upload Bot` next to real users.
- The completed powerlifting challenge says "3 joined" but renders "No entries yet" (podium bug).
- Fake "$1,750 prize pool" on every card; Store has no real checkout; Terms/Privacy are `#` stubs. Together these read as "toy site" and undercut the genuinely serious analysis tech.

### F3. The wait after upload is a dead end
Analysis takes minutes (plank ~9 min worst case). Nothing tells the user "come back in N minutes" or notifies them when done — even though every upload flow already collects an email. Abandonment risk is highest exactly here.

### F4. Results speak engineer, not user
- Bowling result page leads with "Debug Video", frame counts, `conf:1.00`, px/frame. A bowler wants: entry board, pocket hit or miss, ball speed, hook shape — and *what to try next*.
- Lifting rep breakdown shows raw metrics ("Tempo 0.1:1", "Back Position 89.7° / <30°") with no plain-language coaching ("you're pulling too fast; control the descent").
- Low-detection results (1.1%) render without guidance on how to film better.

### F5. Identity is fragmented and fragile
- Three separate profile surfaces (`/profile`, `/golf/profile`, weekly-lifts) with no cross-links; a user who lifts *and* golfs has two disconnected identities on screen.
- Passwordless recovery hinges on the small "Find Profile" dialog; lose localStorage and nothing on the page suggests how to get back.
- Public `/feedback/list` exposes contact emails (known, accepted — but still a UX-trust issue to revisit).

### F6. Copy contradicts the actual (good!) auth model
"How It Works" step 1 says **Register**. The app's best UX property is that you *don't* register — email + upload is everything. The marketing undersells the product's lowest-friction feature.

### What's already good (keep, don't churn)
- Passwordless email-first uploads on all three flows, consistently worded.
- Golf photo-only flow ("Snap your scorecard") is best-in-class simple; camera capture on mobile works.
- Mobile layouts hold up at 390px (hamburger nav, stacked cards).
- Feedback form auto-attaches user + page context.

## Roadmap

Ordered so each phase is shippable alone; sizes are rough (S ≤ ½ day, M ≈ 1–2 days, L ≈ 1 wk).

### Phase 1 — Trust & truth (quick wins, ~1 week)
1. **Purge bot/e2e data from prod surfaces** (S) — filter `*@guest.tomsgym.local`-style bot users + `e2e-lift-*` names from Top Lifts/leaderboards, or flag test users in DB and exclude.
2. **Fix the challenge podium bug** (S–M) — "3 joined" vs "No entries yet" mismatch on `/challenges/:id`.
3. **Honest copy pass** (S) — remove or clearly label fictional prize pools; rewrite "How It Works" to the passwordless reality ("No signup — just your email"); stub pages (Store) get a "coming soon" treatment or leave nav.
4. **Real Terms/Privacy pages** (S) — even one paragraph each; kills the `#` dead links.
5. **Nav restructure** (M) — top-level entries for the three analysis verticals: **Lift**, **Bowl**, **Golf** (each landing on a hub with Upload as primary CTA + leaderboard/recent below); link or delete `/athletes`.

### Phase 2 — First-run & the upload moment (~1–2 weeks)
6. **Landing page repositioned around analysis** (M) — hero = "Get AI analysis of your lift, bowl, or round in minutes," three feature cards with real annotated-output thumbnails (the bowling trajectory shot sells itself), competitions demoted to a section.
7. **Unified upload chooser** (S) — one `/upload` entry that asks "What are you analyzing?" and routes to the three flows (they stay separate underneath; this is only IA glue).
8. **Post-upload status page** (M) — progress state with honest ETA ("usually ~2 min, long videos up to 10"), auto-refresh, and "we'll email you a link when it's ready."
9. **Email-on-complete** (M) — analysis-done email with a short link (`/s/:code` already exists); infra is in place (SMTP secret, email collection). This single feature converts the dead-end wait into a retention loop.

### Phase 3 — Results for humans (~2 weeks)
10. **Bowling result: consumer view first** (M) — headline stats (entry board, est. speed, hook direction, pocket %), debug video/frame data behind an "Advanced" toggle; keep annotate link for corrections.
11. **Lifting rep coaching copy** (M) — map each failed metric to one plain sentence ("Lockout 26% → you didn't finish standing fully upright"); overall grade gets a one-line takeaway.
12. **Filming tips on low confidence** (S) — when detection < threshold, show "Re-record: keep the whole lane/bar in frame, steady phone, landscape" with a retry CTA.
13. **Share cards** (M) — OG-image/short-link share for a graded lift, a trajectory, a round — the organic-growth surface for a hobby app.

### Phase 4 — One identity, reasons to return (~2 weeks)
14. **Unified profile hub** (M–L) — one `/profile/:id` showing lifting, bowling, and golf activity with tabs; golf/lifting profiles link to each other; "Find Profile" gets a full-page route reachable from a clear "Who am I?" nav item.
15. **Magic-link sign-in** (M) — email link that restores the localStorage session on any device; completes the passwordless story without adding passwords.
16. **Golf monthly-delta pill + handicap trend on leaderboard** (S) — backend field already exists (`monthly_delta`, Phase D leftover).

### Phase 5 — Reliability *is* UX (parallel track, from the strategic review)
These aren't cosmetic but they gate everything above: async engine re-architecture (analysis latency + concurrency=1 today), admin route auth + CORS tightening, uptime alerting, branch protection. Plans already written: `docs/superpowers/plans/2026-07-02-*.md` (indexed in `PLANS.md`).

## Suggested next three actions
1. Phase 1 items 1–4 in one sitting (all small, all trust).
2. Nav restructure (item 5) — biggest IA payoff per effort.
3. Email-on-complete (item 9) — the highest-leverage single feature in the list.

---

## Task breakdown (execution-ready)

One task per roadmap item, self-contained enough to pick up cold. Sizes: S ≤ ½ day, M ≈ 1–2 days, L ≈ 1 wk. Dependencies are noted; everything else is parallelizable. Phase 1 (T1–T5) is fully independent — safest first batch for a team on isolated worktrees.

### T1 — Purge bot/e2e test data from public leaderboards and Top Lifts (S)
Production "Top Lifts This Month" shows `e2e-lift-*` users and "T30G Upload Bot" next to real users. Add an `is_test`/bot flag on `User` (or filter by known patterns: name `LIKE 'e2e-lift-%'`, upload-bot account IDs) and exclude flagged users from home Top Lifts, `/leaderboard`, and challenge leaderboards. Do NOT filter golf guest users (`*@guest.tomsgym.local`) — those are real people parsed from scorecards.
**Accept:** prod home shows no bot/e2e entries; a designated test account still sees its own uploads via direct profile URL.

### T2 — Fix challenge podium showing "No entries yet" despite joined participants (M)
Repro: `/challenges/d130cc3c-0021-431e-b5a6-33c3f6a8bd11` shows "3 uploaded today · 3 joined" but the podium renders "No entries yet." Investigate ChallengeDetail's entries query vs the participant-count source (console shows `GET /lifting/result/:videoId` 404s for unanalyzed videos — podium may require analysis results that don't exist, or the entries endpoint filters differently). Use systematic debugging.
**Accept:** completed challenge with submissions shows its podium; regression test added.

### T3 — Honest copy pass: remove fake prizes, fix "Register" messaging (S)
(a) Remove or "Demo"-label the fictional "$1,750 prize pool" on challenge cards (home + `/challenges`). (b) Rewrite "How It Works" on home and `/about`: step 1 says "Register" but the app is passwordless — message "No signup — just your email". (c) Store page gets a "coming soon" treatment. Copy only, no flow changes.
**Accept:** no fabricated prize/judging claims anywhere; messaging matches passwordless reality.

### T4 — Add real Terms and Privacy pages (S)
Footer Terms/Privacy are `href="#"` stubs. Create `/terms` and `/privacy` routes with short honest content (data stored: email, uploaded videos/photos; uploads are publicly viewable; contact for deletion). Wire footer links.
**Accept:** both links navigate to real pages; content mentions public visibility of uploads and email storage.

### T5 — Restructure navbar around Lift / Bowl / Golf verticals (M)
Bowling has no nav entry, Golf lands on the leaderboard, no top-level Upload. Make Lift / Bowl / Golf primary nav items, each landing on a small hub (primary CTA = Upload; below: leaderboard/recent/challenges for that vertical). Decide fate of orphaned `/athletes` (link from a hub or delete). Keep Feedback + Find Profile. Touch `Navbar.tsx`, `routes/index.tsx`, mobile hamburger.
**Accept:** every analysis flow reachable in ≤2 clicks from any page; no orphaned routes.

### T6 — Reposition landing page around analysis output (M) — *after T5*
Hero = "Get AI analysis of your lift, bowl, or round in minutes" with three feature cards using real annotated-output imagery (see `docs/site-map/screenshots/` 04, 08, 14). Demote challenges to a lower section.
**Accept:** first-time visitor can identify all three analysis features and start an upload from the hero without scrolling.

### T7 — Unified /upload chooser (S) — *after T5*
One entry: "What are you analyzing?" → routes to the three existing flows (they stay separate underneath). Note `/upload` currently IS the lifting upload — move lifting to `/lift/upload` (or similar) and keep a redirect strategy for old links.
**Accept:** `/upload` shows the chooser; deep links to the three flows still work.

### T8 — Post-upload status page with honest ETA (M)
Analysis runs minutes (plank worst case ~9 min); today the wait is a dead end. Build a status view (per-attempt page or upgraded success screen): processing state polled from existing status fields, honest ETA copy ("usually ~2 min; long videos up to 10"), auto-refresh, link to the future result, "we'll email you" once T9 lands. Cover lifting + bowling (golf review is synchronous).
**Accept:** after a real prod upload the user sees live status, never a blank/stuck screen; page survives reload via URL.

### T9 — Email-on-analysis-complete with short link (M) — *after T1 (bot flag)*
Highest-leverage single feature. Email is already collected; SMTP creds exist (`EMAIL_PASSWORD` secret); short links exist (`/s/:code`, ShortLink table). On analysis completion (lifting + bowling paths in the jobs pipeline), send "Your analysis is ready" + short link. Include opt-out line. Guards: never block/fail the completion transaction on email failure (log and continue); no email for bot/test users (T1's flag).
**Accept:** prod upload with a test inbox receives the email with a working link; analysis completes normally when SMTP is down.

### T10 — Bowling result: consumer view first, debug behind toggle (M)
`/bowling/result/:attemptId` leads with "Debug Video", frame counts, px/frame, conf values. Restructure: headline stats a bowler cares about (entry board, est. speed, hook direction, pocket hit) + annotated video; internals behind an "Advanced" toggle. Keep the annotate link prominent. Data already exists in the analysis payload — convert or drop units that don't translate.
**Accept:** default view has no debug jargon; advanced view unchanged for dev use.

### T11 — Plain-language coaching on lifting rep breakdown (M)
Rep metrics ("Tempo 0.1:1 vs 1.5-3.0:1", "Back Position 89.7° / <30°") get a one-sentence takeaway per failed metric (e.g. Lockout 26% → "You didn't finish fully upright — stand tall and squeeze at the top") + a one-line overall summary next to the letter grade. Static copy map keyed by (lift type, metric, pass/fail); keep raw numbers visible.
**Accept:** every failable metric has coaching copy for all supported lift types; fixture-driven unit test over the copy map.

### T12 — Filming tips + retry CTA on low-confidence results (S) — *after T10 (same page)*
When detection/confidence is below threshold (e.g. bowling "1.1% detected"), show: "Re-record for better tracking: whole lane in frame, steady phone, landscape from behind the approach" + Upload Again CTA. Same pattern for very-low-confidence lifting results.
**Accept:** low-confidence pages show tips + retry; healthy results don't.

### T13 — Shareable result cards: OG images + short links (M)
For a graded lift, a bowling trajectory, and a golf round: generate an OG-image card (score/grade + annotated still) to GCS; serve `og:image`/`og:title` meta on the `/s/:code` route (needs a server-side meta route on the backend — the SPA can't set OG tags for crawlers).
**Accept:** pasting a result short link into Slack unfurls with the card; Share buttons copy the short link.

### T14 — Unified profile hub across lifting, bowling, golf (L)
One hub at `/profile/:id` with per-sport sections (lifting videos + grades, bowling attempts, golf rounds + handicap), cross-linking existing detail pages. Golf profile keeps its route but links to the hub. Promote "Find Profile" to a full-page route reachable from nav. Backend reads already exist (`/users/:id/profile`, `/golf/rounds?user_id=`, bowling attempts by user).
**Accept:** from a golf profile you can reach the same user's lifts in one click and vice versa.

### T15 — Magic-link sign-in (M) — *after T9 (email plumbing)*
Email → signed one-time link → opening it restores localStorage userId (and JWT if the account has auth). Scope: token table or short-expiry signed JWT, `POST /auth/magic-link` + `GET /auth/magic/:token`, small frontend page. Security: single-use, 15-min expiry, rate-limit by email, don't reveal whether an email exists.
**Accept:** fresh browser recovers a profile via emailed link without a password; link dead after first use/expiry.

### T16 — Golf leaderboard monthly-delta pill (S)
`GET /golf/leaderboard` already returns `monthly_delta` per row — render a ▲/▼ pill on GolfLeaderboard rows, colors consistent with the GolfProfile trend chart.
**Accept:** rows show signed delta pill; zero/no-data rows show nothing rather than "+0.0".

### T17 — Reliability track: engine async + security hygiene (L, parallel)
Plans written 2026-07-02, indexed in `PLANS.md` (`docs/superpowers/plans/2026-07-02-*`): engine re-architecture and security hygiene (admin route auth, CORS tightening, rate limiting), plus branch protection on main and uptime alerting. **Re-verify plan assumptions first** — the Cloud Run Jobs cutover (2026-07-06) already shipped part of the engine plan.

### Execution notes for a team
- Phase 1 (T1–T5) is fully parallel. T3/T4/T5 all touch `routes/index.tsx` and page copy — use isolated worktrees and expect a trivial merge conflict in the route table. T3 should NOT touch `Navbar.tsx` (T5 owns it).
- Validation gate for every task: frontend `npm test` + `vite build`, backend `backend/tools/run_ci_tests.sh`; deploy via `python3 deploy.py --skip-iam` and verify at the prod URL (project convention).
- Golf handicap changes (T16 area) must re-pass `backend/tests/fixtures/whs_reference_cases.json` bit-for-bit.
