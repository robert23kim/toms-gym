# Fairway Phase A — Visual + UX Polish Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Reskin the existing `/golf/*` pages to the Fairway visual idiom and add the review-page UX wins (color-coded cells, amber confidence glow, live differential, "N holes need review" banner, staged parse progress). Pure frontend — no schema, no backend contract changes.

**Architecture:** Scope Fairway design tokens to golf pages only via a `FairwayScope` wrapper and a dedicated `fairway.css`. Keep Tailwind for layout/utilities; use plain CSS classes (prefixed `fw-`) for the token-driven visuals (0.5px borders, palette, typography, confidence glow). Extract a handful of focused components (`StagedParseProgress`, `HighlightsGrid`, `HoleBarChart`, `ReviewBanner`) from the existing page files so each file stays focused. Playwright E2E tests go into a new `golf-fairway-phase-a.spec.ts` and seed a real round via the existing `/golf/upload` endpoint.

**Tech Stack:** React 18 + TypeScript + Vite; Tailwind 3.4 already in use; Framer Motion for existing animations (leave intact). Playwright 1.58 for e2e (pattern: seed round via API, assert DOM in browser). Targets the deployed prod backend by default.

**Spec reference:** `docs/superpowers/specs/2026-04-18-fairway-incremental-migration-design.md` §Phase A.

**Phase B and D:** tracked separately. After this plan ships, write:
- `docs/superpowers/plans/YYYY-MM-DD-fairway-phase-b.md` (Course/Tee model + WHS engine rewrite).
- `docs/superpowers/plans/YYYY-MM-DD-fairway-phase-d.md` (dashboard landing page).

---

## File structure

**Create:**
- `frontend/src/styles/fairway.css` — design tokens (palette, typography, radii, border rules, confidence glow keyframes). Scoped under `.fw-scope`.
- `frontend/src/components/FairwayScope.tsx` — wrapper that imports `fairway.css`, applies the `fw-scope` class, and sets a light/dark data attribute.
- `frontend/src/components/golf/StagedParseProgress.tsx` — 5-stage pulsing progress list used during upload.
- `frontend/src/components/golf/HighlightsGrid.tsx` — 4-cell birdies/pars/bogeys/doubles summary.
- `frontend/src/components/golf/HoleBarChart.tsx` — 18-column SVG bar chart of strokes vs par.
- `frontend/src/components/golf/ReviewBanner.tsx` — amber "N holes need review" banner for the review page.
- `frontend/e2e/golf-fairway-phase-a.spec.ts` — Playwright E2E covering the five reskinned pages.

**Modify:**
- `frontend/src/pages/GolfUpload.tsx` — wrap in `FairwayScope`, apply tokens, add `StagedParseProgress` overlay during upload, re-word file picker CTAs.
- `frontend/src/pages/GolfReview.tsx` — wrap in `FairwayScope`, adjust `getHoleBgClass` to Fairway palette, lift confidence threshold from 0.7 → 0.85, swap `AlertTriangle` icon for CSS glow ring, add `ReviewBanner` + live differential footer.
- `frontend/src/pages/GolfRound.tsx` — wrap in `FairwayScope`, replace inline stat pills with `HighlightsGrid`, add `HoleBarChart`, add standout-holes list.
- `frontend/src/pages/GolfProfile.tsx` — wrap in `FairwayScope`, convert header into Fairway stat cards, re-style expandable round rows.
- `frontend/src/pages/GolfLeaderboard.tsx` — wrap in `FairwayScope`, reformat rows to Fairway style (avatar, name, handicap, monthly delta).

**No changes:**
- Backend code.
- `frontend/src/index.css`, `frontend/tailwind.config.ts` (leave global styles alone; scope is golf-only).
- Other pages (lifting, bowling, nav, auth).

---

## Task 0: Branch setup

**Files:** none (git only).

- [ ] **Step 1: Create and switch to the phase branch**

```bash
git checkout main
git pull --ff-only
git checkout -b golf/fairway-phase-a
```

- [ ] **Step 2: Confirm clean baseline**

Run: `git status`
Expected: `On branch golf/fairway-phase-a; nothing to commit, working tree clean`

---

## Task 1: Create Fairway design tokens stylesheet

**Files:**
- Create: `frontend/src/styles/fairway.css`

- [ ] **Step 1: Write the tokens file**

```css
/* Fairway design tokens — scoped to .fw-scope so they don't leak into
 * lifting / bowling / nav. Follows the Fairway spec visual reference:
 * 0.5px borders on most surfaces, 2px info borders only on selected items,
 * palette from fairway_spec_bundle/designs/_base.css. */

.fw-scope {
  /* Palette — Fairway spec §13 */
  --fw-bg-primary: #FFFFFF;
  --fw-bg-secondary: #F7F5EF;
  --fw-bg-tertiary: #EFEDE6;
  --fw-bg-info: #E6F1FB;
  --fw-bg-success: #EAF3DE;
  --fw-bg-warning: #FAEEDA;
  --fw-bg-danger: #FCEBEB;

  --fw-text-primary: #2C2C2A;
  --fw-text-secondary: #5F5E5A;
  --fw-text-tertiary: #888780;
  --fw-text-info: #185FA5;
  --fw-text-success: #3B6D11;
  --fw-text-warning: #854F0B;
  --fw-text-danger: #A32D2D;

  --fw-border-tertiary: rgba(0,0,0,0.12);
  --fw-border-secondary: rgba(0,0,0,0.22);
  --fw-border-primary: rgba(0,0,0,0.35);
  --fw-border-info: #378ADD;
  --fw-border-success: #97C459;
  --fw-border-warning: #EF9F27;

  --fw-success: #1D9E75;
  --fw-warning: #EF9F27;
  --fw-danger:  #D85A30;
  --fw-info:    #185FA5;

  --fw-radius-sm: 4px;
  --fw-radius-md: 8px;
  --fw-radius-lg: 12px;

  --fw-font-sans: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
  --fw-font-size-body: 14px;
  --fw-font-size-h3: 16px;
  --fw-font-size-h2: 18px;
  --fw-font-size-h1: 22px;

  font-family: var(--fw-font-sans);
  color: var(--fw-text-primary);
  background: #FAFAF7;
}

/* Dark-mode overrides — used when the root html has the `dark` class
 * (next-themes contract already used elsewhere in the app). */
html.dark .fw-scope {
  --fw-bg-primary: #17181A;
  --fw-bg-secondary: #1F2022;
  --fw-bg-tertiary: #26272A;
  --fw-text-primary: #F2F2F0;
  --fw-text-secondary: #B8B8B4;
  --fw-text-tertiary: #7A7A76;
  --fw-border-tertiary: rgba(255,255,255,0.12);
  --fw-border-secondary: rgba(255,255,255,0.22);
  --fw-border-primary: rgba(255,255,255,0.35);
  background: #0F1012;
}

/* Surface + typography primitives */
.fw-scope .fw-surface {
  background: var(--fw-bg-primary);
  border: 0.5px solid var(--fw-border-tertiary);
  border-radius: var(--fw-radius-lg);
}

.fw-scope .fw-h1 { font-size: var(--fw-font-size-h1); font-weight: 500; margin: 0; }
.fw-scope .fw-h2 { font-size: var(--fw-font-size-h2); font-weight: 500; margin: 0; }
.fw-scope .fw-h3 { font-size: var(--fw-font-size-h3); font-weight: 500; margin: 0; }
.fw-scope .fw-text-secondary { color: var(--fw-text-secondary); }

/* Selected / featured — the ONE place where 2px borders are allowed. */
.fw-scope .fw-selected {
  border: 2px solid var(--fw-border-info) !important;
}

/* Scorecard cell score-vs-par semantics (Fairway spec §5.2 Step 3). */
.fw-scope .fw-cell {
  background: var(--fw-bg-primary);
  border: 0.5px solid var(--fw-border-tertiary);
  border-radius: var(--fw-radius-md);
  color: var(--fw-text-primary);
}
.fw-scope .fw-cell-birdie {
  background: var(--fw-bg-success);
  border-color: var(--fw-border-success);
  color: var(--fw-text-success);
}
.fw-scope .fw-cell-par {
  background: var(--fw-bg-primary);
  border-color: var(--fw-border-tertiary);
}
.fw-scope .fw-cell-bogey-plus {
  background: var(--fw-bg-danger);
  border-color: var(--fw-border-warning);
  color: var(--fw-text-danger);
}

/* Low-confidence glow (Fairway spec §5.2 Step 3, threshold 0.85). */
.fw-scope .fw-cell-needs-review {
  box-shadow: 0 0 0 2px var(--fw-border-warning),
              0 0 12px 2px rgba(239, 159, 39, 0.5);
  animation: fw-glow-pulse 1.6s ease-in-out infinite;
}

@keyframes fw-glow-pulse {
  0%, 100% { box-shadow: 0 0 0 2px var(--fw-border-warning),
                         0 0 8px  2px rgba(239, 159, 39, 0.35); }
  50%      { box-shadow: 0 0 0 2px var(--fw-border-warning),
                         0 0 16px 4px rgba(239, 159, 39, 0.65); }
}

/* Staged-parse progress pulsing dot (Fairway spec §5.2 Step 2). */
.fw-scope .fw-parse-dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  background: var(--fw-border-tertiary);
  display: inline-block;
  margin-right: 10px;
}
.fw-scope .fw-parse-dot-active {
  background: var(--fw-info);
  animation: fw-parse-pulse 1s ease-in-out infinite;
}
.fw-scope .fw-parse-dot-done {
  background: var(--fw-success);
}
@keyframes fw-parse-pulse {
  0%, 100% { opacity: 1;   transform: scale(1); }
  50%      { opacity: 0.5; transform: scale(0.85); }
}

/* Camera viewport corner guides on GolfUpload (Fairway spec §5.2 Step 1). */
.fw-scope .fw-corner-guides {
  position: relative;
}
.fw-scope .fw-corner-guides::before,
.fw-scope .fw-corner-guides::after {
  content: "";
  position: absolute;
  width: 24px;
  height: 24px;
  border: 2px solid var(--fw-info);
  pointer-events: none;
}
.fw-scope .fw-corner-guides::before {
  top: 8px; left: 8px;
  border-right: none; border-bottom: none;
  border-top-left-radius: 4px;
}
.fw-scope .fw-corner-guides::after {
  bottom: 8px; right: 8px;
  border-left: none; border-top: none;
  border-bottom-right-radius: 4px;
}
```

- [ ] **Step 2: Verify the file exists and imports cleanly**

Run: `ls -la frontend/src/styles/fairway.css && head -3 frontend/src/styles/fairway.css`
Expected: file exists, first lines begin with `/* Fairway design tokens`.

- [ ] **Step 3: Commit**

```bash
git add frontend/src/styles/fairway.css
git commit -m "feat(golf): add Fairway design tokens stylesheet

Scoped under .fw-scope so it cannot leak into lifting/bowling/nav.
No pages wired up yet — Task 2 adds the wrapper component."
```

---

## Task 2: Create FairwayScope wrapper component

**Files:**
- Create: `frontend/src/components/FairwayScope.tsx`
- Test:   `frontend/e2e/golf-fairway-phase-a.spec.ts`

- [ ] **Step 1: Write the failing Playwright test**

Create `frontend/e2e/golf-fairway-phase-a.spec.ts`:

```ts
import { test, expect, request } from "@playwright/test";

/**
 * Fairway Phase A — visual + UX polish smoke test.
 *
 * Strategy: seed a golf round via the real backend so we have a deterministic
 * round ID to hit, then drive the UI and assert Fairway markers.
 */

const API_URL =
  process.env.API_URL ||
  "https://my-python-backend-quyiiugyoq-ue.a.run.app";

test.describe.configure({ mode: "serial" });

test("golf upload page is wrapped in fw-scope", async ({ page }) => {
  await page.goto("/golf/upload");
  const scope = page.locator(".fw-scope").first();
  await expect(scope).toBeVisible();
});
```

- [ ] **Step 2: Run test to verify it fails**

Run:
```bash
cd frontend && npx playwright test e2e/golf-fairway-phase-a.spec.ts --reporter=list
```
Expected: FAIL with `Locator expected to be visible` (no `.fw-scope` exists yet).

- [ ] **Step 3: Create the wrapper component**

Create `frontend/src/components/FairwayScope.tsx`:

```tsx
import React from "react";
import "../styles/fairway.css";

interface FairwayScopeProps {
  children: React.ReactNode;
  className?: string;
}

/**
 * Applies the Fairway design tokens (palette, typography, 0.5px borders)
 * to its subtree. Tokens live in frontend/src/styles/fairway.css under
 * the .fw-scope selector so they can't leak into other features.
 */
const FairwayScope: React.FC<FairwayScopeProps> = ({ children, className = "" }) => (
  <div className={`fw-scope ${className}`.trim()}>{children}</div>
);

export default FairwayScope;
```

- [ ] **Step 4: Wrap GolfUpload's outer container in FairwayScope**

Modify `frontend/src/pages/GolfUpload.tsx:9` add import, then at line 134 wrap the `<motion.div>` in `<FairwayScope>`:

```tsx
// near existing imports
import FairwayScope from "../components/FairwayScope";
```

Change (around current lines 134–293):
```tsx
  return (
    <Layout>
      <FairwayScope>
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          className="min-h-screen bg-background py-12 px-4 sm:px-6 lg:px-8"
        >
          {/* ... existing markup unchanged for now ... */}
        </motion.div>
      </FairwayScope>
    </Layout>
  );
```

- [ ] **Step 5: Run the dev build to confirm no compile errors**

Run:
```bash
cd frontend && npx tsc --noEmit
```
Expected: exits 0.

- [ ] **Step 6: Re-run Playwright to verify it now passes against a local preview**

Run the preview server first (if not already running):
```bash
cd frontend && npm run build && npm run preview -- --port 4173 &
```
Then run:
```bash
cd frontend && FRONTEND_URL=http://localhost:4173 npx playwright test e2e/golf-fairway-phase-a.spec.ts --reporter=list
```
Expected: PASS.

(Production deploy is a separate gate at the end of the phase; local preview is fine for iteration.)

- [ ] **Step 7: Commit**

```bash
git add frontend/src/components/FairwayScope.tsx frontend/src/pages/GolfUpload.tsx frontend/e2e/golf-fairway-phase-a.spec.ts
git commit -m "feat(golf): wrap GolfUpload in FairwayScope + first e2e assertion"
```

---

## Task 3: Reskin GolfUpload — header, CTAs, drop zone

**Files:**
- Modify: `frontend/src/pages/GolfUpload.tsx`
- Modify: `frontend/e2e/golf-fairway-phase-a.spec.ts`

- [ ] **Step 1: Write the failing test**

Append to `golf-fairway-phase-a.spec.ts`:

```ts
test("golf upload shows Fairway header, alignment guides, and two CTAs", async ({ page }) => {
  await page.goto("/golf/upload");

  // Fairway header with wordmark-style title (fw-h1 class)
  await expect(page.locator(".fw-h1", { hasText: "Log round" })).toBeVisible();

  // Alignment-guide corners on the capture area
  await expect(page.locator(".fw-corner-guides")).toBeVisible();

  // Two CTAs: Capture photo + Upload from library
  await expect(page.getByRole("button", { name: /capture photo/i })).toBeVisible();
  await expect(page.getByRole("button", { name: /upload from library/i })).toBeVisible();

  // Hint text
  await expect(page.getByText(/lay flat, fill frame, avoid glare/i)).toBeVisible();
});
```

- [ ] **Step 2: Run the test to verify it fails**

Run: `cd frontend && FRONTEND_URL=http://localhost:4173 npx playwright test e2e/golf-fairway-phase-a.spec.ts -g "Fairway header" --reporter=list`
Expected: FAIL (no `.fw-corner-guides`, no "Capture photo" button).

- [ ] **Step 3: Reskin the JSX**

In `GolfUpload.tsx`, replace the header + drop zone sections. The full updated return block (replace from `return (` to the final `);` of the component):

```tsx
  return (
    <Layout>
      <FairwayScope>
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          className="min-h-screen py-10 px-4 sm:px-6 lg:px-8"
        >
          <div className="max-w-2xl mx-auto">
            <Link
              to="/golf/leaderboard"
              className="inline-flex items-center fw-text-secondary hover:opacity-80 mb-6 text-sm"
            >
              <ArrowLeft className="mr-2" size={16} />
              Back to Golf
            </Link>

            <div className="fw-surface p-6 sm:p-8 space-y-6">
              <div>
                <h1 className="fw-h1">Log round</h1>
                <p className="fw-text-secondary text-sm mt-1">
                  Snap your scorecard — we'll read it and do the math.
                </p>
              </div>

              <form onSubmit={handleSubmit} className="space-y-5">
                {!localStorage.getItem("userId") && (
                  <div>
                    <label className="block text-sm font-medium mb-1.5">Email</label>
                    <input
                      type="email"
                      value={email}
                      onChange={(e) => setEmail(e.target.value)}
                      placeholder="you@example.com"
                      className="w-full px-3 h-9 rounded-md border border-[var(--fw-border-tertiary)] bg-[var(--fw-bg-primary)] text-sm focus:outline-none focus:border-[var(--fw-info)]"
                    />
                    <p className="text-xs fw-text-secondary mt-1">
                      No account needed — your round is linked to this email.
                    </p>
                  </div>
                )}

                <div>
                  <label className="block text-sm font-medium mb-1.5">Course</label>
                  <input
                    type="text"
                    value={courseName}
                    onChange={(e) => setCourseName(e.target.value)}
                    placeholder="e.g. Pebble Beach Golf Links"
                    className="w-full px-3 h-9 rounded-md border border-[var(--fw-border-tertiary)] bg-[var(--fw-bg-primary)] text-sm focus:outline-none focus:border-[var(--fw-info)]"
                  />
                </div>

                <div className="grid grid-cols-2 gap-4">
                  <div>
                    <label className="block text-sm font-medium mb-1.5">Slope</label>
                    <input
                      type="number"
                      value={slopeRating}
                      onChange={(e) => setSlopeRating(e.target.value)}
                      min="55" max="155" step="1"
                      className="w-full px-3 h-9 rounded-md border border-[var(--fw-border-tertiary)] bg-[var(--fw-bg-primary)] text-sm"
                    />
                  </div>
                  <div>
                    <label className="block text-sm font-medium mb-1.5">Course rating</label>
                    <input
                      type="number"
                      value={courseRating}
                      onChange={(e) => setCourseRating(e.target.value)}
                      min="55" max="85" step="0.1"
                      className="w-full px-3 h-9 rounded-md border border-[var(--fw-border-tertiary)] bg-[var(--fw-bg-primary)] text-sm"
                    />
                  </div>
                </div>

                <div>
                  <label className="block text-sm font-medium mb-1.5">Date</label>
                  <input
                    type="date"
                    value={playedAt}
                    onChange={(e) => setPlayedAt(e.target.value)}
                    className="w-full px-3 h-9 rounded-md border border-[var(--fw-border-tertiary)] bg-[var(--fw-bg-primary)] text-sm"
                  />
                </div>

                <div>
                  <label className="block text-sm font-medium mb-1.5">Scorecard photo</label>
                  <div
                    onDrop={handleDrop}
                    onDragOver={handleDragOver}
                    onDragLeave={handleDragLeave}
                    className={`fw-corner-guides rounded-lg p-10 text-center transition-colors ${
                      isDragging
                        ? "border-[var(--fw-info)] bg-[var(--fw-bg-info)]"
                        : "border-[var(--fw-border-tertiary)] bg-[var(--fw-bg-secondary)]"
                    } border-[0.5px] border-dashed`}
                  >
                    <input
                      type="file"
                      accept="image/*"
                      onChange={handleFileSelect}
                      className="hidden"
                      id="golf-scorecard-upload"
                    />

                    {previewUrl ? (
                      <img
                        src={previewUrl}
                        alt="Scorecard preview"
                        className="max-h-56 rounded-md mb-3 object-contain mx-auto"
                      />
                    ) : (
                      <p className="fw-text-secondary text-sm mb-4">
                        Lay flat, fill frame, avoid glare.
                      </p>
                    )}

                    <div className="flex gap-3 justify-center flex-wrap">
                      <label
                        htmlFor="golf-scorecard-upload"
                        className="inline-flex items-center gap-2 h-9 px-4 rounded-md border border-[var(--fw-border-secondary)] bg-[var(--fw-bg-primary)] text-sm cursor-pointer hover:bg-[var(--fw-bg-tertiary)]"
                      >
                        Upload from library
                      </label>
                      <button
                        type="button"
                        onClick={() => document.getElementById("golf-scorecard-upload")?.click()}
                        className="inline-flex items-center gap-2 h-9 px-4 rounded-md bg-[var(--fw-info)] text-white text-sm hover:opacity-90"
                      >
                        Capture photo
                      </button>
                    </div>

                    {selectedFile && (
                      <p className="text-xs fw-text-secondary mt-3">{selectedFile.name}</p>
                    )}
                  </div>
                </div>

                {error && (
                  <div className="text-sm text-[var(--fw-text-danger)] bg-[var(--fw-bg-danger)] border border-[var(--fw-border-warning)] rounded-md px-3 py-2">
                    {error}
                  </div>
                )}

                <button
                  type="submit"
                  disabled={isUploading || !selectedFile}
                  className="w-full h-10 rounded-md bg-[var(--fw-info)] text-white font-medium text-sm hover:opacity-90 disabled:opacity-50 disabled:cursor-not-allowed"
                >
                  {isUploading ? "Analysing..." : "Analyse scorecard"}
                </button>
              </form>
            </div>
          </div>
        </motion.div>
      </FairwayScope>
    </Layout>
  );
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd frontend && FRONTEND_URL=http://localhost:4173 npm run build && npm run preview -- --port 4173 & sleep 2 && npx playwright test e2e/golf-fairway-phase-a.spec.ts -g "Fairway header" --reporter=list`
Expected: PASS.

(Kill the preview server with `kill %1` or `pkill -f "vite preview"` between tasks if it gets stuck.)

- [ ] **Step 5: Commit**

```bash
git add frontend/src/pages/GolfUpload.tsx frontend/e2e/golf-fairway-phase-a.spec.ts
git commit -m "feat(golf): reskin GolfUpload with Fairway tokens and capture guides"
```

---

## Task 4: Add staged parse progress overlay

**Files:**
- Create: `frontend/src/components/golf/StagedParseProgress.tsx`
- Modify: `frontend/src/pages/GolfUpload.tsx`
- Modify: `frontend/e2e/golf-fairway-phase-a.spec.ts`

- [ ] **Step 1: Write the failing test**

Append to `golf-fairway-phase-a.spec.ts`:

```ts
test("staged parse progress shows 5 tasks during upload", async ({ page }) => {
  await page.goto("/golf/upload");

  // Intercept the upload POST and stall it ~3s so the staged UI has time to animate.
  await page.route("**/golf/upload", async (route) => {
    await new Promise((r) => setTimeout(r, 3000));
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({ round_id: "stub-round-id", user_id: "stub-user-id" }),
    });
  });

  // Fill required fields so the submit goes through.
  await page.fill('input[type="email"]', "fairway-smoke@test.com").catch(() => {});
  await page.fill('input[placeholder*="Pebble Beach" i]', "Smoke Course");
  // Trigger file select via hidden input.
  const filePath = "e2e/fixtures/scorecard-test.jpg";
  // Tiny placeholder image — any small JPG works. Create if missing in test setup.
  await page.setInputFiles("#golf-scorecard-upload", filePath);
  await page.getByRole("button", { name: /analyse scorecard/i }).click();

  // All five stages should render while the upload is in flight.
  for (const label of [
    "Detecting layout",
    "Identifying course",
    "Reading par and yardage",
    "Extracting player scores",
    "Flagging low-confidence holes",
  ]) {
    await expect(page.getByText(label)).toBeVisible({ timeout: 3500 });
  }
});
```

Also ensure the fixture exists:

```bash
mkdir -p frontend/e2e/fixtures
# Create a tiny valid JPEG (1x1 pixel). The backend isn't called because of
# the route override, but setInputFiles still requires a real file.
printf '\xff\xd8\xff\xdb\x00\x43\x00\x08\x06\x06\x07\x06\x05\x08\x07\x07\x07\x09\x09\x08\x0a\x0c\x14\x0d\x0c\x0b\x0b\x0c\x19\x12\x13\x0f\x14\x1d\x1a\x1f\x1e\x1d\x1a\x1c\x1c\x20\x24\x2e\x27\x20\x22\x2c\x23\x1c\x1c\x28\x37\x29\x2c\x30\x31\x34\x34\x34\x1f\x27\x39\x3d\x38\x32\x3c\x2e\x33\x34\x32\xff\xc0\x00\x0b\x08\x00\x01\x00\x01\x01\x01\x11\x00\xff\xc4\x00\x1f\x00\x00\x01\x05\x01\x01\x01\x01\x01\x01\x00\x00\x00\x00\x00\x00\x00\x00\x01\x02\x03\x04\x05\x06\x07\x08\x09\x0a\x0b\xff\xc4\x00\xb5\x10\x00\x02\x01\x03\x03\x02\x04\x03\x05\x05\x04\x04\x00\x00\x01\x7d\x01\x02\x03\x00\x04\x11\x05\x12\x21\x31\x41\x06\x13\x51\x61\x07\x22\x71\x14\x32\x81\x91\xa1\x08\x23\x42\xb1\xc1\x15\x52\xd1\xf0\x24\x33\x62\x72\x82\xff\xda\x00\x08\x01\x01\x00\x00\x3f\x00\xfb\xd0\xff\xd9' > frontend/e2e/fixtures/scorecard-test.jpg
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd frontend && FRONTEND_URL=http://localhost:4173 npx playwright test e2e/golf-fairway-phase-a.spec.ts -g "staged parse" --reporter=list`
Expected: FAIL (`Detecting layout` text not found).

- [ ] **Step 3: Implement the component**

Create `frontend/src/components/golf/StagedParseProgress.tsx`:

```tsx
import React, { useEffect, useState } from "react";

const STAGES = [
  "Detecting layout",
  "Identifying course",
  "Reading par and yardage",
  "Extracting player scores",
  "Flagging low-confidence holes",
] as const;

/**
 * Shows a 5-stage fake-progression list while the real /golf/upload call
 * is in flight. Each stage becomes "active" (pulsing info dot) after a
 * short delay, then "done" (green dot) when the next stage starts. The
 * last stage stays active until the parent unmounts the component.
 *
 * Why fake-stage: the real backend does a single OCR call that takes
 * 2–6s with no intermediate signal. A staged UI makes the wait feel
 * intentional (Fairway spec §5.2 Step 2).
 */
const StagedParseProgress: React.FC = () => {
  const [activeIndex, setActiveIndex] = useState(0);

  useEffect(() => {
    const timers: ReturnType<typeof setTimeout>[] = [];
    STAGES.forEach((_, i) => {
      if (i === 0) return;
      timers.push(setTimeout(() => setActiveIndex(i), i * 700));
    });
    return () => timers.forEach(clearTimeout);
  }, []);

  return (
    <div className="fw-surface p-5">
      <h3 className="fw-h3 mb-3">Reading your scorecard</h3>
      <ul className="space-y-2 text-sm">
        {STAGES.map((label, i) => {
          const state =
            i < activeIndex ? "fw-parse-dot-done" :
            i === activeIndex ? "fw-parse-dot-active" : "";
          return (
            <li key={label} className="flex items-center">
              <span className={`fw-parse-dot ${state}`} />
              <span className={i <= activeIndex ? "" : "fw-text-secondary"}>{label}</span>
            </li>
          );
        })}
      </ul>
    </div>
  );
};

export default StagedParseProgress;
```

- [ ] **Step 4: Mount the overlay during upload in GolfUpload.tsx**

At the top of `GolfUpload.tsx` imports:
```tsx
import StagedParseProgress from "../components/golf/StagedParseProgress";
```

Inside the form, replace the final submit button block with a conditional: show the staged progress instead of the form footer while uploading. Change the bottom of the form (just before the closing `</form>`):

```tsx
                {isUploading ? (
                  <StagedParseProgress />
                ) : (
                  <button
                    type="submit"
                    disabled={!selectedFile}
                    className="w-full h-10 rounded-md bg-[var(--fw-info)] text-white font-medium text-sm hover:opacity-90 disabled:opacity-50 disabled:cursor-not-allowed"
                  >
                    Analyse scorecard
                  </button>
                )}
```

(Remove the older `{isUploading ? "Analysing..." : "Analyse scorecard"}` branch from Task 3 — the new block replaces it.)

- [ ] **Step 5: Run test to verify it passes**

Run: `cd frontend && npm run build && kill %1 2>/dev/null; npm run preview -- --port 4173 & sleep 2 && FRONTEND_URL=http://localhost:4173 npx playwright test e2e/golf-fairway-phase-a.spec.ts -g "staged parse" --reporter=list`
Expected: PASS.

- [ ] **Step 6: Commit**

```bash
git add frontend/src/components/golf/StagedParseProgress.tsx frontend/src/pages/GolfUpload.tsx frontend/e2e/golf-fairway-phase-a.spec.ts frontend/e2e/fixtures/scorecard-test.jpg
git commit -m "feat(golf): staged parse progress overlay during upload"
```

---

## Task 5: Seed a golf round for downstream tests

**Files:**
- Modify: `frontend/e2e/golf-fairway-phase-a.spec.ts`

Tasks 6–11 need a real round with known low-confidence holes. Seed once with `test.beforeAll` and share the round ID.

- [ ] **Step 1: Add a `beforeAll` block that seeds a round via the API**

Replace the top of `golf-fairway-phase-a.spec.ts` with:

```ts
import { test, expect, request, APIRequestContext } from "@playwright/test";
import fs from "fs";
import path from "path";

const API_URL =
  process.env.API_URL ||
  "https://my-python-backend-quyiiugyoq-ue.a.run.app";

test.describe.configure({ mode: "serial" });

// These module-level let bindings are populated by beforeAll and then read
// by every subsequent test in the file (Tasks 6–15).
let seededRoundId = "";
let seededUserId = "";

test.beforeAll(async () => {
  const ctx: APIRequestContext = await request.newContext();

  // Register a throwaway user so we have a user_id to attach the round to.
  const uniq = Date.now().toString(36);
  const email = `fairway-phase-a-${uniq}@test.com`;
  const register = await ctx.post(`${API_URL}/auth/register`, {
    data: { email, password: "TestPassword123!", name: `Phase A ${uniq}` },
  });
  if (!register.ok()) {
    throw new Error(`Failed to register test user: ${register.status()} ${await register.text()}`);
  }

  // Upload a scorecard — we only need a round_id. Use the fixture from Task 4
  // and provide course/slope/rating inline.
  const fixturePath = path.resolve(__dirname, "fixtures/scorecard-test.jpg");
  const imageBuffer = fs.readFileSync(fixturePath);
  const upload = await ctx.post(`${API_URL}/golf/upload`, {
    multipart: {
      image: {
        name: "scorecard-test.jpg",
        mimeType: "image/jpeg",
        buffer: imageBuffer,
      },
      email,
      course_name: `Phase A Test Course ${uniq}`,
      slope_rating: "128",
      course_rating: "71.2",
      played_at: new Date().toISOString().split("T")[0],
    },
  });
  if (!upload.ok()) {
    throw new Error(`Failed to seed round: ${upload.status()} ${await upload.text()}`);
  }
  const body = await upload.json();
  seededRoundId = body.round_id;
  seededUserId = body.user_id;
  expect(seededRoundId).toMatch(/^[0-9a-f-]{36}$/);
  expect(seededUserId).toMatch(/^[0-9a-f-]{36}$/);
});
```

Keep the existing `test(...)` blocks below this.

- [ ] **Step 2: Run the existing tests to confirm the seed works**

Run: `cd frontend && FRONTEND_URL=http://localhost:4173 npx playwright test e2e/golf-fairway-phase-a.spec.ts --reporter=list`
Expected: previous tests still PASS; new `beforeAll` runs without error.

- [ ] **Step 3: Commit**

```bash
git add frontend/e2e/golf-fairway-phase-a.spec.ts
git commit -m "test(golf): seed round fixture via API for Phase A e2e"
```

---

## Task 6: GolfReview — Fairway palette on score cells

**Files:**
- Modify: `frontend/src/pages/GolfReview.tsx`
- Modify: `frontend/e2e/golf-fairway-phase-a.spec.ts`

Swap `getHoleBgClass` from Tailwind ad-hoc colors to the Fairway `fw-cell-*` classes. Keep Tailwind for layout only.

- [ ] **Step 1: Write the failing test**

Append to `golf-fairway-phase-a.spec.ts`:

```ts
test("review cells use Fairway color semantics vs par", async ({ page }) => {
  await page.goto(`/golf/review/${seededRoundId}`);

  // Find at least one hole input. Because the seeded round is from a tiny
  // test image the OCR will produce no scores, so we'll type a known value
  // and assert the class changes accordingly.
  const firstCell = page.locator('[data-testid="scorecard-cell-1"]');
  await expect(firstCell).toBeVisible();

  // Click to edit, enter a birdie (par 4 → stroke 3)
  await firstCell.click();
  await page.keyboard.type("3");
  await page.keyboard.press("Enter");
  await expect(firstCell).toHaveClass(/fw-cell-birdie/);

  // Enter a par
  await firstCell.click();
  await page.keyboard.press("Control+a");
  await page.keyboard.type("4");
  await page.keyboard.press("Enter");
  await expect(firstCell).toHaveClass(/fw-cell-par/);

  // Enter a bogey
  await firstCell.click();
  await page.keyboard.press("Control+a");
  await page.keyboard.type("5");
  await page.keyboard.press("Enter");
  await expect(firstCell).toHaveClass(/fw-cell-bogey-plus/);
});
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd frontend && FRONTEND_URL=http://localhost:4173 npx playwright test e2e/golf-fairway-phase-a.spec.ts -g "Fairway color semantics" --reporter=list`
Expected: FAIL (no `fw-cell-birdie` class; also no `data-testid="scorecard-cell-1"`).

- [ ] **Step 3: Update `getHoleBgClass` and cell markup in GolfReview.tsx**

Replace the function (currently ~line 107):

```tsx
  const getHoleBgClass = (hole: GolfHoleScore) => {
    if (hole.strokes === null) return "fw-cell";
    const diff = hole.strokes - hole.par;
    if (diff <= -1) return "fw-cell fw-cell-birdie";
    if (diff === 0)  return "fw-cell fw-cell-par";
    return "fw-cell fw-cell-bogey-plus";
  };
```

And wrap the per-cell `<div>` inside `renderHoleGrid` with a `data-testid`:

```tsx
          <div
            key={hole.hole_number}
            data-testid={`scorecard-cell-${hole.hole_number}`}
            onClick={() => setEditingHole(hole.hole_number)}
            className={`relative p-2 cursor-pointer transition-colors ${getHoleBgClass(
              hole
            )} ${editingHole === hole.hole_number ? "fw-selected" : ""}`}
          >
```

Also wrap the page root in `<FairwayScope>`. Add the import:

```tsx
import FairwayScope from "../components/FairwayScope";
```

Wrap **each** of the three return branches (loading, error, and the main render) in `<FairwayScope>`. For the loading branch the full JSX becomes:

```tsx
  if (loading) {
    return (
      <Layout>
        <FairwayScope>
          <div className="min-h-screen py-12 px-4 sm:px-6 lg:px-8">
            <div className="max-w-4xl mx-auto">
              <div className="flex items-center justify-center h-64">
                <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-[var(--fw-info)]"></div>
              </div>
            </div>
          </div>
        </FairwayScope>
      </Layout>
    );
  }
```

Use the same pattern for the error branch (keep its body, swap the outer `<Layout>` contents into `<FairwayScope>`) and for the main render return.

- [ ] **Step 4: Run test to verify it passes**

Run: `cd frontend && npm run build && npm run preview -- --port 4173 & sleep 2 && FRONTEND_URL=http://localhost:4173 npx playwright test e2e/golf-fairway-phase-a.spec.ts -g "Fairway color semantics" --reporter=list`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add frontend/src/pages/GolfReview.tsx frontend/e2e/golf-fairway-phase-a.spec.ts
git commit -m "feat(golf): Fairway color semantics on review cells"
```

---

## Task 7: GolfReview — confidence glow at 0.85 threshold

Replace the `AlertTriangle` icon (currently fires at `< 0.7`) with the CSS glow ring at `< 0.85` (Fairway spec §5.2 Step 3).

**Files:**
- Modify: `frontend/src/pages/GolfReview.tsx`
- Modify: `frontend/e2e/golf-fairway-phase-a.spec.ts`

- [ ] **Step 1: Write the failing test**

Because we can't easily seed a low-confidence cell from the API (OCR of the 1x1 fixture returns nothing), use `page.evaluate` to patch React state directly is overkill. Instead, assert the CSS class gets applied based on the `ocr_confidence` prop by stubbing the round fetch:

```ts
test("low-confidence cells get the fw-cell-needs-review glow", async ({ page }) => {
  // Stub the round fetch so hole 3 is low-confidence and holes 1-2 are not.
  await page.route(`**/golf/round/${seededRoundId}`, async (route) => {
    const body = {
      id: seededRoundId,
      user_id: "stub-user",
      course_name: "Stub Course",
      slope_rating: 128,
      course_rating: 71.2,
      adjusted_gross_score: null,
      differential: null,
      scorecard_image_url: null,
      ocr_confidence: 0.5,
      processing_status: "ocr_complete",
      played_at: "2026-04-18",
      holes: Array.from({ length: 18 }, (_, i) => ({
        hole_number: i + 1,
        par: 4,
        strokes: i === 2 ? 4 : null,
        ocr_confidence: i === 2 ? 0.5 : 0.99,
      })),
      detected_players: [],
    };
    await route.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify(body) });
  });

  await page.goto(`/golf/review/${seededRoundId}`);
  await expect(page.locator('[data-testid="scorecard-cell-3"]')).toHaveClass(/fw-cell-needs-review/);
  await expect(page.locator('[data-testid="scorecard-cell-1"]')).not.toHaveClass(/fw-cell-needs-review/);

  // The old AlertTriangle icon should be gone.
  await expect(page.locator('[data-testid="scorecard-cell-3"] svg')).toHaveCount(0);
});
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd frontend && FRONTEND_URL=http://localhost:4173 npx playwright test e2e/golf-fairway-phase-a.spec.ts -g "needs-review glow" --reporter=list`
Expected: FAIL.

- [ ] **Step 3: Update the cell markup in GolfReview.tsx**

Remove the `AlertTriangle` import if it's unused elsewhere (it still appears in the banner; keep it). Remove the JSX block that renders `<AlertTriangle …/>` inside each cell (currently lines ~325–331). Replace the cell's wrapper className with:

```tsx
          <div
            key={hole.hole_number}
            data-testid={`scorecard-cell-${hole.hole_number}`}
            onClick={() => setEditingHole(hole.hole_number)}
            className={`relative p-2 cursor-pointer transition-colors ${getHoleBgClass(
              hole
            )} ${editingHole === hole.hole_number ? "fw-selected" : ""} ${
              hole.ocr_confidence !== undefined &&
              hole.ocr_confidence < 0.85 &&
              hole.strokes !== null
                ? "fw-cell-needs-review"
                : ""
            }`}
          >
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd frontend && npm run build && npm run preview -- --port 4173 & sleep 2 && FRONTEND_URL=http://localhost:4173 npx playwright test e2e/golf-fairway-phase-a.spec.ts -g "needs-review glow" --reporter=list`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add frontend/src/pages/GolfReview.tsx frontend/e2e/golf-fairway-phase-a.spec.ts
git commit -m "feat(golf): amber confidence glow at 0.85 threshold on review"
```

---

## Task 8: GolfReview — "N holes need review" banner

**Files:**
- Create: `frontend/src/components/golf/ReviewBanner.tsx`
- Modify: `frontend/src/pages/GolfReview.tsx`
- Modify: `frontend/e2e/golf-fairway-phase-a.spec.ts`

- [ ] **Step 1: Write the failing test**

Append to `golf-fairway-phase-a.spec.ts`:

```ts
test("N holes need review banner appears when any cell < 0.85", async ({ page }) => {
  await page.route(`**/golf/round/${seededRoundId}`, async (route) => {
    const body = {
      id: seededRoundId,
      user_id: "stub",
      course_name: "Stub",
      slope_rating: 128,
      course_rating: 71.2,
      adjusted_gross_score: null,
      differential: null,
      scorecard_image_url: null,
      ocr_confidence: 0.6,
      processing_status: "ocr_complete",
      played_at: "2026-04-18",
      holes: Array.from({ length: 18 }, (_, i) => ({
        hole_number: i + 1,
        par: 4,
        strokes: 4,
        ocr_confidence: i < 3 ? 0.5 : 0.95, // 3 low-confidence holes
      })),
      detected_players: [],
    };
    await route.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify(body) });
  });

  await page.goto(`/golf/review/${seededRoundId}`);
  await expect(page.locator('[data-testid="review-banner"]')).toHaveText(/3 holes? need review/i);
});
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd frontend && FRONTEND_URL=http://localhost:4173 npx playwright test e2e/golf-fairway-phase-a.spec.ts -g "need review banner" --reporter=list`
Expected: FAIL.

- [ ] **Step 3: Create the component**

Create `frontend/src/components/golf/ReviewBanner.tsx`:

```tsx
import React from "react";
import { AlertTriangle } from "lucide-react";

interface ReviewBannerProps {
  needsReviewCount: number;
}

/**
 * Amber banner shown at the top of the review grid when any score cell
 * has ocr_confidence < 0.85 (Fairway spec §5.2 Step 3).
 * Hidden when the count is 0.
 */
const ReviewBanner: React.FC<ReviewBannerProps> = ({ needsReviewCount }) => {
  if (needsReviewCount <= 0) return null;
  const wording =
    needsReviewCount >= 10
      ? "Many holes need review"
      : `${needsReviewCount} hole${needsReviewCount === 1 ? "" : "s"} need review`;
  return (
    <div
      data-testid="review-banner"
      className="flex items-center gap-2 rounded-md border-[0.5px] border-[var(--fw-border-warning)] bg-[var(--fw-bg-warning)] text-[var(--fw-text-warning)] px-3 py-2 text-sm"
    >
      <AlertTriangle className="w-4 h-4" />
      <span>{wording}</span>
    </div>
  );
};

export default ReviewBanner;
```

- [ ] **Step 4: Wire it into GolfReview.tsx**

Import at top of file:
```tsx
import ReviewBanner from "../components/golf/ReviewBanner";
```

Compute the count just before the render (next to the existing `allHolesComplete` derivation):
```tsx
  const needsReviewCount = holes.filter(
    (h) => h.ocr_confidence !== undefined && h.ocr_confidence < 0.85 && h.strokes !== null
  ).length;
```

Insert `<ReviewBanner needsReviewCount={needsReviewCount} />` just below the course header `<div>`, above the scorecard image block.

- [ ] **Step 5: Run test to verify it passes**

Run: `cd frontend && npm run build && npm run preview -- --port 4173 & sleep 2 && FRONTEND_URL=http://localhost:4173 npx playwright test e2e/golf-fairway-phase-a.spec.ts -g "need review banner" --reporter=list`
Expected: PASS.

- [ ] **Step 6: Commit**

```bash
git add frontend/src/components/golf/ReviewBanner.tsx frontend/src/pages/GolfReview.tsx frontend/e2e/golf-fairway-phase-a.spec.ts
git commit -m "feat(golf): N holes need review banner on review page"
```

---

## Task 9: GolfReview — live differential footer

**Files:**
- Modify: `frontend/src/pages/GolfReview.tsx`
- Modify: `frontend/e2e/golf-fairway-phase-a.spec.ts`

- [ ] **Step 1: Write the failing test**

Append to `golf-fairway-phase-a.spec.ts`:

```ts
test("live differential footer updates as scores change", async ({ page }) => {
  await page.route(`**/golf/round/${seededRoundId}`, async (route) => {
    const body = {
      id: seededRoundId,
      user_id: "stub",
      course_name: "Stub",
      slope_rating: 128,
      course_rating: 71.2,
      adjusted_gross_score: null,
      differential: null,
      scorecard_image_url: null,
      ocr_confidence: 0.95,
      processing_status: "ocr_complete",
      played_at: "2026-04-18",
      holes: Array.from({ length: 18 }, (_, i) => ({
        hole_number: i + 1,
        par: 4,
        strokes: 4, // total 72, = course rating → differential 0.0
        ocr_confidence: 0.95,
      })),
      detected_players: [],
    };
    await route.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify(body) });
  });

  await page.goto(`/golf/review/${seededRoundId}`);
  const footer = page.locator('[data-testid="review-differential"]');
  await expect(footer).toContainText("0.7");
  // ((72 - 71.2) × 113) / 128 = 0.70625 → "0.7"

  // Change hole 1 from 4 → 5. New total 73. Differential: ((73-71.2)*113)/128 = 1.5890625 → "1.6"
  await page.locator('[data-testid="scorecard-cell-1"]').click();
  await page.keyboard.press("Control+a");
  await page.keyboard.type("5");
  await page.keyboard.press("Enter");
  await expect(footer).toContainText("1.6");
});
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd frontend && FRONTEND_URL=http://localhost:4173 npx playwright test e2e/golf-fairway-phase-a.spec.ts -g "live differential" --reporter=list`
Expected: FAIL.

- [ ] **Step 3: Add the footer to GolfReview.tsx**

Compute near the other totals (after `totalPar`):

```tsx
  const liveDifferential =
    round && allHolesComplete
      ? ((grandTotal - Number(round.course_rating)) * 113) /
        Number(round.slope_rating)
      : null;
```

Insert the footer between the 3-cell totals row and the confirm button:

```tsx
              {/* Live differential (Fairway spec §5.2 Step 3). */}
              <div
                data-testid="review-differential"
                className="fw-surface p-3 text-sm flex items-center justify-between"
              >
                <span className="fw-text-secondary">
                  Front {front9Total} · Back {back9Total} · Total {grandTotal}
                </span>
                <span className="font-medium">
                  Score differential:{" "}
                  <span className="text-[var(--fw-text-info)]">
                    {liveDifferential !== null
                      ? liveDifferential.toFixed(1)
                      : "—"}
                  </span>
                </span>
              </div>
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd frontend && npm run build && npm run preview -- --port 4173 & sleep 2 && FRONTEND_URL=http://localhost:4173 npx playwright test e2e/golf-fairway-phase-a.spec.ts -g "live differential" --reporter=list`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add frontend/src/pages/GolfReview.tsx frontend/e2e/golf-fairway-phase-a.spec.ts
git commit -m "feat(golf): live score differential footer on review"
```

---

## Task 10: GolfReview — shell reskin + success screen

Wraps up remaining visual-only changes on review (player picker pills, confirm button, success screen) to use Fairway tokens.

**Files:**
- Modify: `frontend/src/pages/GolfReview.tsx`
- Modify: `frontend/e2e/golf-fairway-phase-a.spec.ts`

- [ ] **Step 1: Write the failing test**

```ts
test("review page uses Fairway typography and surface styles", async ({ page }) => {
  await page.goto(`/golf/review/${seededRoundId}`);
  await expect(page.locator(".fw-scope .fw-h1", { hasText: /review/i })).toBeVisible();
  await expect(page.locator(".fw-surface").first()).toBeVisible();
});
```

- [ ] **Step 2: Run test to verify it fails** (only if prior tasks haven't already added these markers)

Run: `cd frontend && FRONTEND_URL=http://localhost:4173 npx playwright test e2e/golf-fairway-phase-a.spec.ts -g "Fairway typography" --reporter=list`
Expected: FAIL if header is still `<h1 className="text-2xl font-bold">`.

- [ ] **Step 3: Apply shell reskin to GolfReview.tsx**

Replace the outer card's surrounding markup (`<div className="bg-card rounded-lg shadow-lg overflow-hidden">` and its inner title/subtitle) with:

```tsx
            <div className="fw-surface p-6 sm:p-8 space-y-5">
              <div>
                <h1 className="fw-h1">Review scores</h1>
                <p className="fw-text-secondary text-sm mt-1">
                  {round?.course_name} — {round?.played_at}
                </p>
                {round?.ocr_confidence !== null && round?.ocr_confidence !== undefined && (
                  <p className="text-xs fw-text-secondary mt-1">
                    OCR confidence {(round.ocr_confidence * 100).toFixed(0)}% ·
                    tap any cell to edit.
                  </p>
                )}
              </div>
              {/* rest of body unchanged */}
            </div>
```

Replace the detected-players pill container class:
```tsx
                <div
                  data-testid="detected-players"
                  className="rounded-md border-[0.5px] border-[var(--fw-border-info)] bg-[var(--fw-bg-info)] p-3"
                >
```

Replace the confirm button:
```tsx
              <button
                onClick={handleConfirm}
                disabled={!allHolesComplete || confirming}
                className="w-full h-11 rounded-md bg-[var(--fw-info)] text-white font-medium text-sm hover:opacity-90 disabled:opacity-50 disabled:cursor-not-allowed"
              >
                {confirming ? "Confirming..." : "Confirm and save"}
              </button>
```

Success screen (`confirmed && resultData` block): change outer container to `<FairwayScope>`, swap the Trophy/icon circle and stat cards to use `fw-surface` + `fw-text-*` tokens. The specific change:

```tsx
  if (confirmed && resultData) {
    const userId = round?.user_id || localStorage.getItem("userId");
    return (
      <Layout>
        <FairwayScope>
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            className="min-h-screen py-10 px-4 sm:px-6 lg:px-8"
          >
            <div className="max-w-2xl mx-auto text-center">
              <div className="w-16 h-16 rounded-full bg-[var(--fw-bg-success)] border-[0.5px] border-[var(--fw-border-success)] flex items-center justify-center mx-auto mb-4">
                <Check className="w-8 h-8 text-[var(--fw-text-success)]" />
              </div>
              <h1 className="fw-h1 mb-1">Round saved</h1>
              <p className="fw-text-secondary mb-6">
                {round?.course_name} — {round?.played_at}
              </p>
              <div className="grid grid-cols-2 gap-3 mb-6 text-left">
                <div className="fw-surface p-4">
                  <div className="text-2xl font-medium">{resultData.adjusted_gross_score}</div>
                  <div className="text-xs fw-text-secondary">Total score</div>
                </div>
                <div className="fw-surface p-4">
                  <div className="text-2xl font-medium text-[var(--fw-text-success)]">
                    {resultData.differential !== null ? resultData.differential.toFixed(1) : "N/A"}
                  </div>
                  <div className="text-xs fw-text-secondary">Differential</div>
                </div>
              </div>
              {resultData.handicap_index !== null && (
                <div className="fw-surface p-4 mb-6 text-left">
                  <div className="text-xs fw-text-secondary">Handicap index</div>
                  <div className="text-3xl font-medium text-[var(--fw-text-success)]">
                    {resultData.handicap_index.toFixed(1)}
                  </div>
                </div>
              )}
              <div className="flex gap-3 justify-center">
                <Link
                  to={userId ? `/golf/profile/${userId}` : "/golf/profile"}
                  className="h-9 px-4 rounded-md bg-[var(--fw-info)] text-white text-sm inline-flex items-center"
                >
                  View profile
                </Link>
                <Link
                  to={`/golf/round/${roundId}`}
                  className="h-9 px-4 rounded-md border-[0.5px] border-[var(--fw-border-secondary)] text-sm inline-flex items-center"
                >
                  View round
                </Link>
              </div>
            </div>
          </motion.div>
        </FairwayScope>
      </Layout>
    );
  }
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd frontend && npm run build && npm run preview -- --port 4173 & sleep 2 && FRONTEND_URL=http://localhost:4173 npx playwright test e2e/golf-fairway-phase-a.spec.ts -g "Fairway typography" --reporter=list`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add frontend/src/pages/GolfReview.tsx frontend/e2e/golf-fairway-phase-a.spec.ts
git commit -m "feat(golf): reskin review shell + success screen with Fairway tokens"
```

---

## Task 11: GolfRound — highlights grid + hole bar chart

**Files:**
- Create: `frontend/src/components/golf/HighlightsGrid.tsx`
- Create: `frontend/src/components/golf/HoleBarChart.tsx`
- Modify: `frontend/src/pages/GolfRound.tsx`
- Modify: `frontend/e2e/golf-fairway-phase-a.spec.ts`

- [ ] **Step 1: Write the failing test**

The seeded round starts with `processing_status: "ocr_complete"` and no confirmed scores, so stub the fetch to return a fully-scored round:

```ts
test("round page shows highlights grid and hole bar chart", async ({ page }) => {
  await page.route(`**/golf/round/${seededRoundId}`, async (route) => {
    const body = {
      id: seededRoundId,
      user_id: "stub",
      course_name: "Stub Course",
      slope_rating: 128,
      course_rating: 71.2,
      adjusted_gross_score: 80,
      differential: 7.8,
      scorecard_image_url: null,
      ocr_confidence: 0.95,
      processing_status: "confirmed",
      played_at: "2026-04-18",
      holes: Array.from({ length: 18 }, (_, i) => ({
        hole_number: i + 1,
        par: 4,
        strokes: 4 + (i % 3 === 0 ? 1 : 0),
        ocr_confidence: 0.95,
      })),
    };
    await route.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify(body) });
  });

  await page.goto(`/golf/round/${seededRoundId}`);
  await expect(page.locator('[data-testid="highlights-grid"]')).toBeVisible();
  await expect(page.locator('[data-testid="hole-bar-chart"] rect')).toHaveCount(18);
});
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd frontend && FRONTEND_URL=http://localhost:4173 npx playwright test e2e/golf-fairway-phase-a.spec.ts -g "highlights grid and hole bar" --reporter=list`
Expected: FAIL.

- [ ] **Step 3: Implement HighlightsGrid**

Create `frontend/src/components/golf/HighlightsGrid.tsx`:

```tsx
import React from "react";

interface HighlightsGridProps {
  birdies: number;
  pars: number;
  bogeys: number;
  doublesOrWorse: number;
}

const cellClass = "fw-surface p-3 text-center";

const HighlightsGrid: React.FC<HighlightsGridProps> = ({
  birdies, pars, bogeys, doublesOrWorse,
}) => (
  <div
    data-testid="highlights-grid"
    className="grid grid-cols-4 gap-2"
  >
    <div className={cellClass}>
      <div className="text-xl font-medium text-[var(--fw-text-success)]">{birdies}</div>
      <div className="text-xs fw-text-secondary">Birdies</div>
    </div>
    <div className={cellClass}>
      <div className="text-xl font-medium">{pars}</div>
      <div className="text-xs fw-text-secondary">Pars</div>
    </div>
    <div className={cellClass}>
      <div className="text-xl font-medium text-[var(--fw-text-warning)]">{bogeys}</div>
      <div className="text-xs fw-text-secondary">Bogeys</div>
    </div>
    <div className={cellClass}>
      <div className="text-xl font-medium text-[var(--fw-text-danger)]">{doublesOrWorse}</div>
      <div className="text-xs fw-text-secondary">Doubles+</div>
    </div>
  </div>
);

export default HighlightsGrid;
```

- [ ] **Step 4: Implement HoleBarChart**

Create `frontend/src/components/golf/HoleBarChart.tsx`:

```tsx
import React from "react";

interface HoleBarChartProps {
  holes: { hole_number: number; par: number; strokes: number | null }[];
}

/**
 * 18-column bar chart: each bar shows strokes relative to par. Positive
 * bars (above the par baseline) represent over-par; negative bars (below)
 * represent under-par. Colors follow the Fairway semantics.
 *
 * SVG-only, no chart library, so the page stays lightweight.
 */
const HoleBarChart: React.FC<HoleBarChartProps> = ({ holes }) => {
  const width = 360;
  const height = 100;
  const padding = 12;
  const barW = (width - padding * 2) / 18;
  const maxDelta = 4; // cap visualization to ±4 for sensible scaling

  const sorted = [...holes].sort((a, b) => a.hole_number - b.hole_number);

  return (
    <div className="fw-surface p-4">
      <h3 className="fw-h3 mb-2">Hole by hole vs par</h3>
      <svg
        data-testid="hole-bar-chart"
        viewBox={`0 0 ${width} ${height}`}
        className="w-full h-auto"
        role="img"
        aria-label="Hole-by-hole strokes vs par"
      >
        {/* baseline (par) */}
        <line
          x1={padding} x2={width - padding}
          y1={height / 2} y2={height / 2}
          stroke="var(--fw-border-secondary)" strokeWidth="0.5" strokeDasharray="2 3"
        />
        {sorted.map((h, i) => {
          const delta = h.strokes === null ? 0 : h.strokes - h.par;
          const clamped = Math.max(-maxDelta, Math.min(maxDelta, delta));
          const h2 = (height / 2) - padding;
          const barH = (Math.abs(clamped) / maxDelta) * h2;
          const y = clamped >= 0 ? height / 2 : (height / 2) - barH;
          const color =
            delta < 0 ? "var(--fw-success)" :
            delta === 0 ? "var(--fw-border-secondary)" :
            delta === 1 ? "var(--fw-warning)" :
            "var(--fw-danger)";
          return (
            <rect
              key={h.hole_number}
              x={padding + i * barW + 1}
              y={y}
              width={barW - 2}
              height={barH || 1}
              fill={color}
              rx="1"
            />
          );
        })}
      </svg>
    </div>
  );
};

export default HoleBarChart;
```

- [ ] **Step 5: Wire into GolfRound.tsx**

Wrap the outer return in `<FairwayScope>` (import + wrap as earlier pages). Replace the existing "Summary stats" grid (birdies/pars/bogeys/doubles block) with `<HighlightsGrid>`, and add `<HoleBarChart holes={holes} />` right below the two 9-hole grids.

Top imports:
```tsx
import FairwayScope from "../components/FairwayScope";
import HighlightsGrid from "../components/golf/HighlightsGrid";
import HoleBarChart from "../components/golf/HoleBarChart";
```

Replace the existing stat pills block with:
```tsx
              <HighlightsGrid
                birdies={birdies}
                pars={pars}
                bogeys={bogeys}
                doublesOrWorse={doubles}
              />
```

Add below the two `renderHoleGrid` calls:
```tsx
              <HoleBarChart holes={holes} />
```

- [ ] **Step 6: Run test to verify it passes**

Run: `cd frontend && npm run build && npm run preview -- --port 4173 & sleep 2 && FRONTEND_URL=http://localhost:4173 npx playwright test e2e/golf-fairway-phase-a.spec.ts -g "highlights grid and hole bar" --reporter=list`
Expected: PASS.

- [ ] **Step 7: Commit**

```bash
git add frontend/src/components/golf/HighlightsGrid.tsx frontend/src/components/golf/HoleBarChart.tsx frontend/src/pages/GolfRound.tsx frontend/e2e/golf-fairway-phase-a.spec.ts
git commit -m "feat(golf): Fairway highlights grid + hole-by-hole bar chart on round"
```

---

## Task 12: GolfRound — shell reskin

Wrap the remaining parts of `GolfRound.tsx` in Fairway tokens (header, stat pills, scorecard image block). No new tests — covered by the smoke in Task 14.

**Files:**
- Modify: `frontend/src/pages/GolfRound.tsx`

- [ ] **Step 1: Replace header block**

Replace the header region (currently the flex container with `MapPin`, calendar, slope/rating badges, Score/Differential stat cards):

```tsx
              <div className="flex flex-col sm:flex-row sm:items-start sm:justify-between gap-4">
                <div>
                  <h1 className="fw-h1 flex items-center gap-2">
                    <MapPin className="w-5 h-5 text-[var(--fw-text-success)]" />
                    {round.course_name}
                  </h1>
                  <div className="flex items-center gap-4 mt-2 text-sm fw-text-secondary">
                    <span className="inline-flex items-center gap-1">
                      <Calendar className="w-3.5 h-3.5" />
                      {round.played_at}
                    </span>
                    <span>Slope {round.slope_rating}</span>
                    <span>Rating {round.course_rating}</span>
                  </div>
                </div>
                <div className="flex gap-2">
                  <div className="fw-surface px-4 py-2 text-center">
                    <div className="text-2xl font-medium">
                      {round.adjusted_gross_score || sumStrokes(holes)}
                    </div>
                    <div className="text-xs fw-text-secondary">Score</div>
                  </div>
                  {round.differential !== null && (
                    <div className="fw-surface px-4 py-2 text-center">
                      <div className="text-2xl font-medium text-[var(--fw-text-success)] inline-flex items-center gap-1">
                        <TrendingDown className="w-4 h-4" />
                        {round.differential.toFixed(1)}
                      </div>
                      <div className="text-xs fw-text-secondary">Differential</div>
                    </div>
                  )}
                </div>
              </div>
```

- [ ] **Step 2: Replace totals block**

Replace the 3-cell totals grid with:

```tsx
              <div className="grid grid-cols-3 gap-2">
                <div className="fw-surface p-3 text-center">
                  <div className="text-xl font-medium">{sumStrokes(front9)}</div>
                  <div className="text-xs fw-text-secondary">Front 9 (Par {sumPar(front9)})</div>
                </div>
                <div className="fw-surface p-3 text-center">
                  <div className="text-xl font-medium">{sumStrokes(back9)}</div>
                  <div className="text-xs fw-text-secondary">Back 9 (Par {sumPar(back9)})</div>
                </div>
                <div className="fw-surface p-3 text-center">
                  <div className="text-xl font-medium">{sumStrokes(holes)}</div>
                  <div className="text-xs fw-text-secondary">Total (Par {sumPar(holes)})</div>
                </div>
              </div>
```

- [ ] **Step 3: Replace `getHoleBgClass` to match review-page Fairway semantics**

```tsx
  const getHoleBgClass = (hole: GolfHoleScore) => {
    if (hole.strokes === null) return "fw-cell";
    const diff = hole.strokes - hole.par;
    if (diff <= -1) return "fw-cell fw-cell-birdie";
    if (diff === 0)  return "fw-cell fw-cell-par";
    return "fw-cell fw-cell-bogey-plus";
  };
```

- [ ] **Step 4: Verify no TS errors**

Run: `cd frontend && npx tsc --noEmit`
Expected: exits 0.

- [ ] **Step 5: Commit**

```bash
git add frontend/src/pages/GolfRound.tsx
git commit -m "feat(golf): reskin GolfRound header and totals with Fairway tokens"
```

---

## Task 13: GolfProfile reskin

**Files:**
- Modify: `frontend/src/pages/GolfProfile.tsx`
- Modify: `frontend/e2e/golf-fairway-phase-a.spec.ts`

- [ ] **Step 1: Write the failing test**

(`seededUserId` is already populated by the `beforeAll` in Task 5.)

```ts
test("profile page uses Fairway stat tiles for rounds played", async ({ page }) => {
  await page.goto(`/golf/profile/${seededUserId}`);
  await expect(page.locator(".fw-scope .fw-h1")).toBeVisible();
  await expect(page.locator('[data-testid="profile-stats"]')).toBeVisible();
});
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd frontend && FRONTEND_URL=http://localhost:4173 npx playwright test e2e/golf-fairway-phase-a.spec.ts -g "Fairway stat tiles" --reporter=list`
Expected: FAIL.

- [ ] **Step 3: Reskin GolfProfile.tsx**

Wrap in `<FairwayScope>`, replace the circular handicap badge + "rounds played" line with a Fairway stat-tile grid:

Add import:
```tsx
import FairwayScope from "../components/FairwayScope";
```

Replace the profile header block (from `<div className="text-center mb-8">` to just before `{/* Upload button */}`) with:

```tsx
          <div className="flex items-center gap-4 mb-6">
            <img
              src={getGhibliAvatar(userId)}
              alt="Avatar"
              className="w-14 h-14 rounded-full bg-[var(--fw-bg-secondary)] border-[0.5px] border-[var(--fw-border-tertiary)]"
            />
            <div>
              <h1 className="fw-h1">{userName || "Golfer"}</h1>
              <p className="fw-text-secondary text-sm">
                {rounds.length} round{rounds.length !== 1 ? "s" : ""}
              </p>
            </div>
          </div>

          <div
            data-testid="profile-stats"
            className="grid grid-cols-2 sm:grid-cols-3 gap-2 mb-6"
          >
            <div className="fw-surface p-4">
              <div className="text-xs fw-text-secondary">Handicap</div>
              <div className="text-2xl font-medium text-[var(--fw-text-success)]">
                {handicapIndex !== null ? handicapIndex.toFixed(1) : "—"}
              </div>
              {handicapIndex === null && (
                <div className="text-xs fw-text-secondary mt-1">
                  Play 3+ rounds
                </div>
              )}
            </div>
            <div className="fw-surface p-4">
              <div className="text-xs fw-text-secondary">Best differential</div>
              <div className="text-2xl font-medium">
                {(() => {
                  const diffs = rounds
                    .map((r) => r.differential)
                    .filter((d): d is number => d !== null);
                  return diffs.length ? Math.min(...diffs).toFixed(1) : "—";
                })()}
              </div>
            </div>
            <div className="fw-surface p-4 col-span-2 sm:col-span-1">
              <div className="text-xs fw-text-secondary">Last round</div>
              <div className="text-2xl font-medium">
                {rounds[0]?.adjusted_gross_score ?? "—"}
              </div>
              {rounds[0] && (
                <div className="text-xs fw-text-secondary mt-1 truncate">
                  {rounds[0].course_name} · {rounds[0].played_at}
                </div>
              )}
            </div>
          </div>
```

And restyle the expandable rounds list rows. Replace the round card:

```tsx
              {rounds.map((round) => {
                const stats = getRoundStats(round);
                const isExpanded = expandedRound === round.id;
                return (
                  <div key={round.id} className="fw-surface overflow-hidden">
                    <button
                      onClick={() => setExpandedRound(isExpanded ? null : round.id)}
                      className="w-full p-4 text-left"
                    >
                      {/* ...existing JSX, but with fw-text-secondary instead of text-muted-foreground... */}
                    </button>
                    {/* rest unchanged */}
                  </div>
                );
              })}
```

Update `getHoleBgClass` in this file to match Fairway cell classes like in Tasks 6 + 12.

- [ ] **Step 4: Run test to verify it passes**

Run: `cd frontend && npm run build && npm run preview -- --port 4173 & sleep 2 && FRONTEND_URL=http://localhost:4173 npx playwright test e2e/golf-fairway-phase-a.spec.ts -g "Fairway stat tiles" --reporter=list`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add frontend/src/pages/GolfProfile.tsx frontend/e2e/golf-fairway-phase-a.spec.ts
git commit -m "feat(golf): reskin GolfProfile with Fairway stat tiles"
```

---

## Task 14: GolfLeaderboard reskin

**Files:**
- Modify: `frontend/src/pages/GolfLeaderboard.tsx`
- Modify: `frontend/e2e/golf-fairway-phase-a.spec.ts`

- [ ] **Step 1: Write the failing test**

```ts
test("leaderboard uses Fairway row style", async ({ page }) => {
  await page.goto("/golf/leaderboard");
  await expect(page.locator(".fw-scope .fw-h1", { hasText: /leaderboard/i })).toBeVisible();
  // Verify fw-surface wrapper is used
  await expect(page.locator('[data-testid="leaderboard-list"]')).toHaveClass(/fw-surface/);
});
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd frontend && FRONTEND_URL=http://localhost:4173 npx playwright test e2e/golf-fairway-phase-a.spec.ts -g "Fairway row style" --reporter=list`
Expected: FAIL.

- [ ] **Step 3: Reskin GolfLeaderboard.tsx**

Add:
```tsx
import FairwayScope from "../components/FairwayScope";
```

Wrap outer return in `<FairwayScope>`. Change header:

```tsx
          <div className="flex items-center justify-between mb-6">
            <div>
              <h1 className="fw-h1">Handicap leaderboard</h1>
              <p className="fw-text-secondary text-sm">Lowest handicap index first.</p>
            </div>
            <Link
              to="/golf/upload"
              className="h-9 px-4 rounded-md bg-[var(--fw-info)] text-white text-sm inline-flex items-center gap-2"
            >
              <Upload className="w-4 h-4" />
              Log round
            </Link>
          </div>
```

Change the entries container to have `data-testid="leaderboard-list"` and use fw-surface:

```tsx
            <div
              data-testid="leaderboard-list"
              className="fw-surface overflow-hidden"
            >
              {entries.map((entry, index) => (
                <Link
                  key={entry.user_id}
                  to={`/golf/profile/${entry.user_id}`}
                  className={`flex items-center gap-4 p-3 hover:bg-[var(--fw-bg-secondary)] transition-colors ${
                    index !== entries.length - 1
                      ? "border-b-[0.5px] border-[var(--fw-border-tertiary)]"
                      : ""
                  }`}
                >
                  <div className="w-6 text-center font-medium text-sm fw-text-secondary">
                    {entry.rank}
                  </div>
                  <img
                    src={getGhibliAvatar(entry.user_id)}
                    alt={entry.user_name}
                    className="w-10 h-10 rounded-full bg-[var(--fw-bg-secondary)]"
                  />
                  <div className="flex-1 min-w-0">
                    <div className="font-medium truncate">{entry.user_name}</div>
                    <div className="text-xs fw-text-secondary">
                      {entry.rounds_played} round{entry.rounds_played !== 1 ? "s" : ""}
                    </div>
                  </div>
                  <div className="text-right">
                    <div className="text-lg font-medium text-[var(--fw-text-success)]">
                      {entry.handicap_index.toFixed(1)}
                    </div>
                    <div className="text-xs fw-text-secondary">
                      Best {entry.best_differential !== null ? entry.best_differential.toFixed(1) : "—"}
                    </div>
                  </div>
                </Link>
              ))}
            </div>
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd frontend && npm run build && npm run preview -- --port 4173 & sleep 2 && FRONTEND_URL=http://localhost:4173 npx playwright test e2e/golf-fairway-phase-a.spec.ts -g "Fairway row style" --reporter=list`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add frontend/src/pages/GolfLeaderboard.tsx frontend/e2e/golf-fairway-phase-a.spec.ts
git commit -m "feat(golf): reskin GolfLeaderboard with Fairway rows"
```

---

## Task 15: End-to-end Phase-A smoke test

**Files:**
- Modify: `frontend/e2e/golf-fairway-phase-a.spec.ts`

- [ ] **Step 1: Add a single happy-path smoke test that touches all five pages**

Append:

```ts
test("full Phase A surface is Fairway-skinned", async ({ page }) => {
  // Upload
  await page.goto("/golf/upload");
  await expect(page.locator(".fw-scope .fw-h1", { hasText: /log round/i })).toBeVisible();

  // Review
  await page.goto(`/golf/review/${seededRoundId}`);
  await expect(page.locator(".fw-scope .fw-h1", { hasText: /review/i })).toBeVisible();

  // Round
  await page.goto(`/golf/round/${seededRoundId}`);
  await expect(page.locator(".fw-scope")).toBeVisible();

  // Profile
  await page.goto(`/golf/profile/${seededUserId}`);
  await expect(page.locator('[data-testid="profile-stats"]')).toBeVisible();

  // Leaderboard
  await page.goto("/golf/leaderboard");
  await expect(page.locator('[data-testid="leaderboard-list"]')).toBeVisible();
});
```

- [ ] **Step 2: Run the full test file**

Run: `cd frontend && FRONTEND_URL=http://localhost:4173 npx playwright test e2e/golf-fairway-phase-a.spec.ts --reporter=list`
Expected: all tests PASS.

- [ ] **Step 3: Run the type checker and lifting/bowling-related tests to confirm no regression**

Run: `cd frontend && npx tsc --noEmit`
Expected: exits 0.

Run the pre-existing e2e suites to confirm they still pass unchanged:
```bash
cd frontend && FRONTEND_URL=http://localhost:4173 npx playwright test e2e/bowling-lifecycle.spec.ts e2e/user-workflows.spec.ts --reporter=list
```
Expected: PASS (unchanged behavior).

- [ ] **Step 4: Commit**

```bash
git add frontend/e2e/golf-fairway-phase-a.spec.ts
git commit -m "test(golf): Phase A full-surface Fairway smoke"
```

---

## Task 16: Deploy to production and verify

**Files:** none (deploy only).

- [ ] **Step 1: Push the branch**

```bash
git push -u origin golf/fairway-phase-a
```

- [ ] **Step 2: Open a PR for review**

```bash
gh pr create --title "feat(golf): Fairway Phase A — visual + UX polish" --body "$(cat <<'EOF'
## Summary
- Introduce Fairway design tokens scoped to /golf/* pages via `FairwayScope` + `frontend/src/styles/fairway.css`.
- Reskin all five golf pages (upload, review, round, profile, leaderboard) to Fairway visual idiom: 0.5px borders, semantic palette, typography weights 400/500.
- Review page UX wins: Fairway color semantics on cells, amber confidence glow at 0.85 threshold, "N holes need review" banner, live score differential footer.
- Staged parse progress overlay during upload.

Spec: docs/superpowers/specs/2026-04-18-fairway-incremental-migration-design.md §Phase A
Plan: docs/superpowers/plans/2026-04-18-fairway-phase-a.md

## Test plan
- [x] `cd frontend && npx tsc --noEmit`
- [x] `cd frontend && npx playwright test e2e/golf-fairway-phase-a.spec.ts`
- [x] `cd frontend && npx playwright test e2e/bowling-lifecycle.spec.ts e2e/user-workflows.spec.ts` (regression)
- [ ] Deploy: `python3 deploy.py --frontend-only --skip-iam`
- [ ] Smoke: hit production /golf/upload, /golf/review/<id>, /golf/round/<id>, /golf/profile/<id>, /golf/leaderboard; verify Fairway styling and no layout regressions.

🤖 Generated with [Claude Code](https://claude.com/claude-code)
EOF
)"
```

- [ ] **Step 3: After PR is merged, deploy frontend**

(User action, not agent action.)
```bash
python3 deploy.py --frontend-only --skip-iam
```
Expected: Cloud Run revision updates; `https://toms-gym-web-quyiiugyoq-ue.a.run.app/golf/upload` renders the Fairway-skinned page.

- [ ] **Step 4: Post-deploy verification**

Run the same Playwright suite against production:
```bash
cd frontend && npx playwright test e2e/golf-fairway-phase-a.spec.ts --reporter=list
```
Expected: PASS against production URL.

---

## Phase A exit criteria

- All 16 tasks' commits landed on `main`.
- Playwright `golf-fairway-phase-a.spec.ts` passes against production.
- Manual eyeball check: upload, review, round, profile, leaderboard all look like the Fairway mockups (tones, borders, typography) — see `fairway_spec_bundle/designs/*.png` for reference.
- No regression on `bowling-lifecycle`, `user-workflows`, `annotation-workspace`, `lane-edge-editor` e2e tests.

Next: write `docs/superpowers/plans/<date>-fairway-phase-b.md` per spec §Phase B.
