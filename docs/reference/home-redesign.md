<!-- Moved verbatim from CLAUDE.md on 2026-09-19; CLAUDE.md keeps a pointer. -->
# Home Redesign + Quiet-Gym Cohesion (shipped 2026-07-06)

Minimal, centered home page + app-wide visual language. Spec: `docs/superpowers/specs/2026-07-06-home-redesign-cohesion-design.md` (mockup asset committed alongside); plan: `docs/superpowers/plans/2026-07-06-home-redesign-cohesion.md`. Frontend-only.

- **Shared primitives** (`frontend/src/components/`): `AmbientBackground` (fixed doodle-wallpaper + 3 drifting glow layers, mounted once in `Layout` → every page), `IconTile` (centered icon-chip link tile), `RowCard` (slim row: icon · title · pill · "Open →"), `DemoLoop` (home-only 12s CSS/SVG loop: plank hold + timer → bowling trace → scorecard scan; keyframes in `index.css` as `demo-*`/`ambient-*`; all reduced-motion aware).
- **Index rebuilt**: hero → DemoLoop → 3 IconTiles (`/lift/upload`, `/bowling/upload`, `/golf/snap`) → "Open challenges" strip (`getCompetitions()` filtered to `status==='ongoing'`, RowCards → `/challenges/:id`; whole strip hidden when none). Removed: TopLifts sidebar (component file retained, now unused), photo cards, How It Works, featured-challenge cards/filters.
- **Layout footer**: centered "Report a bug · Request a feature · Terms · Privacy · v{APP_VERSION}" (bug/feature → `/feedback`); copyright line dropped.
- **Page passes**: `HubPage` centered w/ RowCard secondary links (descriptions no longer rendered on hubs); `UploadChooser` = same IconTiles as home (golf → `/golf/snap`); `Challenges` centered header + "Open now" RowCard strip + pill filters; `Leaderboard` pill filters. Golf `fw-*` internals untouched.
- **Tests**: `Index`, `IconTile`, `RowCard`, `AmbientBackground`, `DemoLoop`, `LayoutFooter` suites (page tests mock `../../config` + stub Navbar/Layout). Suite at ship: 46 suites / 282 tests.
