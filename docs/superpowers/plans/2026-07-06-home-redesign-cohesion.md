# Home Redesign + Quiet-Gym Cohesion Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Rebuild the home page as a minimal centered experience (Top Lifts gone, demo loop, icon tiles, open-challenges strip) and extend the same visual language across Layout, hubs, UploadChooser, Challenges, and Leaderboard — per spec `docs/superpowers/specs/2026-07-06-home-redesign-cohesion-design.md`.

**Architecture:** Frontend-only. Four new shared components (`AmbientBackground`, `IconTile`, `RowCard`, `DemoLoop`); `Layout` mounts the background and gets the new footer, so every page inherits both; five pages restyled on top of the primitives. All animation CSS lives in `src/index.css`; the reviewed mockup (`docs/superpowers/specs/assets/2026-07-06-home-redesign-mockup.html`) is the visual reference.

**Tech Stack:** React 18 + TypeScript, react-router, framer-motion (already a dep), Tailwind with shadcn-style HSL tokens (`bg-accent/10` alpha modifiers work), jest + RTL, vite.

## Global Constraints

- No backend changes; only existing `getCompetitions()` is consumed (shape: `{ id, title, status: 'upcoming'|'ongoing'|'completed', categories: string[] }`).
- Golf `fw-*` page internals untouched. VideoPlayer, BowlingResult, AnnotationWorkspace, Profile, SignIn untouched.
- All new fetches non-fatal (`catch` → empty); home never shows a fetch error.
- Every animation must be disabled or static under `@media (prefers-reduced-motion: reduce)`; background layers are `aria-hidden` + `pointer-events-none`.
- Page-level jest tests must mock `../../config` (Vite `import.meta`) and stub `Layout` where the navbar tree isn't under test — follow `src/pages/__tests__/GolfUpload.test.tsx`.
- `TopLifts` component file is NOT deleted (follow-up cleanup); only its Index usage goes.
- LiftHub's plank quick link test (`src/pages/__tests__/LiftHub.test.tsx`) must stay green through the HubPage restyle.
- Validation gate per task: `cd frontend && npx jest <targeted tests> && npx vite build`. Final task: full `npx jest && npx vite build && npx tsc --noEmit`, deploy, prod verify.

---

### Task 1: IconTile + RowCard primitives (TDD)

**Files:**
- Create: `frontend/src/components/IconTile.tsx`
- Create: `frontend/src/components/RowCard.tsx`
- Test: `frontend/src/components/__tests__/IconTile.test.tsx` (new)
- Test: `frontend/src/components/__tests__/RowCard.test.tsx` (new)

**Interfaces:**
- Produces: `IconTile` props `{ to: string; icon: React.ReactNode; title: string; description: string }`; `RowCard` props `{ to: string; icon?: React.ReactNode; title: string; pill?: string; trailing?: string }` (trailing defaults `"Open"`). Consumed by Tasks 5–8.

- [ ] **Step 1: Write the failing tests**

```tsx
// frontend/src/components/__tests__/IconTile.test.tsx
import React from "react";
import "@testing-library/jest-dom";
import { render, screen } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import IconTile from "../IconTile";

describe("IconTile", () => {
  it("renders an accessible link tile with title and description", () => {
    render(
      <MemoryRouter>
        <IconTile to="/lift/upload" icon={<span data-testid="ic" />} title="Lift" description="Per-rep grades." />
      </MemoryRouter>
    );
    const link = screen.getByRole("link", { name: /lift/i });
    expect(link).toHaveAttribute("href", "/lift/upload");
    expect(screen.getByText("Per-rep grades.")).toBeInTheDocument();
    expect(screen.getByTestId("ic")).toBeInTheDocument();
  });
});
```

```tsx
// frontend/src/components/__tests__/RowCard.test.tsx
import React from "react";
import "@testing-library/jest-dom";
import { render, screen } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import RowCard from "../RowCard";

describe("RowCard", () => {
  it("renders link, title, pill, and default trailing label", () => {
    render(
      <MemoryRouter>
        <RowCard to="/challenges/c1" title="Summer Plank Challenge" pill="Plank" />
      </MemoryRouter>
    );
    const link = screen.getByRole("link", { name: /summer plank challenge/i });
    expect(link).toHaveAttribute("href", "/challenges/c1");
    expect(screen.getByText("Plank")).toBeInTheDocument();
    expect(screen.getByText("Open")).toBeInTheDocument();
  });

  it("omits the pill when not given and honors custom trailing", () => {
    render(
      <MemoryRouter>
        <RowCard to="/leaderboard" title="Leaderboard" trailing="View" />
      </MemoryRouter>
    );
    expect(screen.getByText("View")).toBeInTheDocument();
    expect(screen.queryByText("Open")).toBeNull();
  });
});
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd frontend && npx jest src/components/__tests__/IconTile.test.tsx src/components/__tests__/RowCard.test.tsx`
Expected: FAIL — Cannot find module '../IconTile' / '../RowCard'.

- [ ] **Step 3: Implement both components**

```tsx
// frontend/src/components/IconTile.tsx
import React from "react";
import { Link } from "react-router-dom";

interface Props {
  to: string;
  icon: React.ReactNode;
  title: string;
  description: string;
}

/**
 * Quiet-gym primitive: centered icon-chip tile, whole tile is the link.
 * Used by the home page verticals and the upload chooser.
 */
const IconTile: React.FC<Props> = ({ to, icon, title, description }) => (
  <Link
    to={to}
    className="group flex flex-col items-center gap-2.5 glass rounded-2xl px-4 py-6 text-center transition-all hover:bg-secondary/40 hover:-translate-y-0.5"
  >
    <span className="w-11 h-11 rounded-xl bg-accent/10 text-accent grid place-items-center">
      {icon}
    </span>
    <span className="font-semibold">{title}</span>
    <span className="text-sm text-muted-foreground leading-snug">{description}</span>
  </Link>
);

export default IconTile;
```

```tsx
// frontend/src/components/RowCard.tsx
import React from "react";
import { Link } from "react-router-dom";
import { ArrowRight } from "lucide-react";

interface Props {
  to: string;
  icon?: React.ReactNode;
  title: string;
  pill?: string;
  trailing?: string;
}

/**
 * Quiet-gym primitive: slim horizontal link row — icon · title · pill · "Open →".
 * Used by the home open-challenges strip, hub secondary links, and Challenges.
 */
const RowCard: React.FC<Props> = ({ to, icon, title, pill, trailing = "Open" }) => (
  <Link
    to={to}
    className="group flex items-center gap-3 glass rounded-xl px-4 py-3.5 text-left transition-colors hover:bg-secondary/40"
  >
    {icon && <span className="text-accent shrink-0">{icon}</span>}
    <span className="flex-1 min-w-0 font-medium truncate">{title}</span>
    {pill && (
      <span className="shrink-0 text-[11px] font-semibold px-2.5 py-0.5 rounded-full bg-accent/10 text-accent">
        {pill}
      </span>
    )}
    <span className="shrink-0 inline-flex items-center gap-1 text-sm text-muted-foreground group-hover:text-foreground transition-colors">
      {trailing}
      <ArrowRight className="w-3.5 h-3.5" />
    </span>
  </Link>
);

export default RowCard;
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd frontend && npx jest src/components/__tests__/IconTile.test.tsx src/components/__tests__/RowCard.test.tsx`
Expected: PASS (3 tests).

- [ ] **Step 5: Commit**

```bash
git add frontend/src/components/IconTile.tsx frontend/src/components/RowCard.tsx frontend/src/components/__tests__/IconTile.test.tsx frontend/src/components/__tests__/RowCard.test.tsx
git commit -m "feat(ui): IconTile + RowCard quiet-gym primitives"
```

---

### Task 2: AmbientBackground + Layout mount

**Files:**
- Create: `frontend/src/components/AmbientBackground.tsx`
- Modify: `frontend/src/index.css` (append keyframes block)
- Modify: `frontend/src/components/Layout.tsx` (mount before `<main>`)
- Test: `frontend/src/components/__tests__/AmbientBackground.test.tsx` (new)

**Interfaces:**
- Produces: `<AmbientBackground />` (no props), mounted once in `Layout`.

- [ ] **Step 1: Write the failing test**

```tsx
// frontend/src/components/__tests__/AmbientBackground.test.tsx
import React from "react";
import "@testing-library/jest-dom";
import { render } from "@testing-library/react";
import AmbientBackground from "../AmbientBackground";

describe("AmbientBackground", () => {
  it("renders doodle + three glow layers, all aria-hidden and pointer-transparent", () => {
    const { container } = render(<AmbientBackground />);
    const layers = container.querySelectorAll("[aria-hidden='true']");
    expect(layers.length).toBe(4); // 1 doodle + 3 glows
    layers.forEach((el) => {
      expect(el.className).toContain("pointer-events-none");
      expect(el.className).toContain("fixed");
    });
  });
});
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd frontend && npx jest src/components/__tests__/AmbientBackground.test.tsx`
Expected: FAIL — Cannot find module '../AmbientBackground'.

- [ ] **Step 3: Implement**

Append to `frontend/src/index.css` (bottom of file):

```css
/* Quiet-gym ambient background (AmbientBackground.tsx) */
@keyframes ambient-drift-1 {
  from { transform: translate(0, 0); }
  to { transform: translate(70px, 40px); }
}
@keyframes ambient-drift-2 {
  from { transform: translate(0, 0); }
  to { transform: translate(-60px, 50px); }
}
.ambient-glow { border-radius: 9999px; filter: blur(90px); }
.ambient-glow-1 { animation: ambient-drift-1 26s ease-in-out infinite alternate; }
.ambient-glow-2 { animation: ambient-drift-2 32s ease-in-out infinite alternate; }
.ambient-glow-3 { animation: ambient-drift-1 38s ease-in-out infinite alternate-reverse; }
@media (prefers-reduced-motion: reduce) {
  .ambient-glow-1, .ambient-glow-2, .ambient-glow-3 { animation: none; }
}
```

```tsx
// frontend/src/components/AmbientBackground.tsx
import React from "react";

// Repeating 320px line-art tile: dumbbell, bowling ball, golf flag + green,
// stopwatch, swoosh — white strokes; the layer's opacity keeps it a whisper.
const DOODLE_TILE = `url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='320' height='320' viewBox='0 0 320 320'%3E%3Cg fill='none' stroke='%23ffffff' stroke-width='1.6' stroke-linecap='round' stroke-linejoin='round'%3E%3Cg transform='translate(38 44) rotate(-18)'%3E%3Crect x='0' y='6' width='7' height='16' rx='2'/%3E%3Crect x='33' y='6' width='7' height='16' rx='2'/%3E%3Cline x1='7' y1='14' x2='33' y2='14'/%3E%3C/g%3E%3Cg transform='translate(220 60) rotate(12)'%3E%3Ccircle cx='14' cy='14' r='14'/%3E%3Ccircle cx='9' cy='9' r='1.4'/%3E%3Ccircle cx='16' cy='7' r='1.4'/%3E%3Ccircle cx='15' cy='14' r='1.4'/%3E%3C/g%3E%3Cg transform='translate(150 150) rotate(-8)'%3E%3Cline x1='4' y1='34' x2='4' y2='0'/%3E%3Cpath d='M4 2 L26 8 L4 15'/%3E%3Cellipse cx='9' cy='36' rx='9' ry='2.4'/%3E%3C/g%3E%3Cg transform='translate(48 218) rotate(14)'%3E%3Ccircle cx='12' cy='16' r='11'/%3E%3Cline x1='9' y1='2' x2='15' y2='2'/%3E%3Cline x1='12' y1='2' x2='12' y2='5'/%3E%3Cline x1='12' y1='16' x2='17' y2='11'/%3E%3C/g%3E%3Cg transform='translate(238 220) rotate(-10)'%3E%3Cpath d='M8 0 C4 6 12 10 8 16 C4 22 12 26 8 32'/%3E%3Cpath d='M8 0 C12 6 4 10 8 16 C12 22 4 26 8 32' transform='translate(6 0)'/%3E%3C/g%3E%3C/g%3E%3C/svg%3E")`;

/**
 * App-wide ambient backdrop: faint sports-doodle wallpaper + three slow
 * drifting color glows. Mounted once in Layout; purely decorative.
 */
const AmbientBackground: React.FC = () => (
  <>
    <div
      aria-hidden="true"
      className="fixed inset-0 -z-20 pointer-events-none opacity-[0.05]"
      style={{ backgroundImage: DOODLE_TILE, backgroundSize: "320px 320px" }}
    />
    <div
      aria-hidden="true"
      className="ambient-glow ambient-glow-1 fixed -z-10 pointer-events-none w-[480px] h-[480px] -left-36 top-16"
      style={{ background: "hsl(220 90% 56% / 0.16)" }}
    />
    <div
      aria-hidden="true"
      className="ambient-glow ambient-glow-2 fixed -z-10 pointer-events-none w-[420px] h-[420px] -right-40 top-[340px]"
      style={{ background: "hsl(160 70% 45% / 0.10)" }}
    />
    <div
      aria-hidden="true"
      className="ambient-glow ambient-glow-3 fixed -z-10 pointer-events-none w-[380px] h-[380px] left-[30%] -bottom-44"
      style={{ background: "hsl(30 90% 55% / 0.08)" }}
    />
  </>
);

export default AmbientBackground;
```

In `frontend/src/components/Layout.tsx`, add the import and mount as the first child of the root div:

```tsx
import AmbientBackground from "./AmbientBackground";
```

```tsx
    <div className="min-h-screen flex flex-col bg-background">
      <AmbientBackground />
      <Navbar />
```

- [ ] **Step 4: Run test + build**

Run: `cd frontend && npx jest src/components/__tests__/AmbientBackground.test.tsx && npx vite build`
Expected: PASS (1 test); clean build.

- [ ] **Step 5: Commit**

```bash
git add frontend/src/components/AmbientBackground.tsx frontend/src/components/__tests__/AmbientBackground.test.tsx frontend/src/components/Layout.tsx frontend/src/index.css
git commit -m "feat(ui): ambient glows + sports-doodle backdrop app-wide"
```

---

### Task 3: Layout footer refresh

**Files:**
- Modify: `frontend/src/components/Layout.tsx` (footer block)
- Test: `frontend/src/components/__tests__/LayoutFooter.test.tsx` (new)

**Interfaces:**
- Consumes: existing `/feedback`, `/terms`, `/privacy` routes; `APP_VERSION` from `../config`.

- [ ] **Step 1: Write the failing test**

```tsx
// frontend/src/components/__tests__/LayoutFooter.test.tsx
import React from "react";
import "@testing-library/jest-dom";
import { render, screen } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import Layout from "../Layout";

// config.ts uses import.meta (Vite), which jest can't parse; mock it as the
// repo's other tests do.
jest.mock("../../config", () => ({ API_URL: "https://test-api.example", APP_VERSION: "test" }));

// Navbar pulls in the auth tree; stub it so the test stays on the footer.
jest.mock("../Navbar", () => ({
  __esModule: true,
  default: () => <nav />,
}));

describe("Layout footer", () => {
  it("links Report a bug and Request a feature to /feedback", () => {
    render(
      <MemoryRouter>
        <Layout>content</Layout>
      </MemoryRouter>
    );
    expect(screen.getByRole("link", { name: /report a bug/i })).toHaveAttribute("href", "/feedback");
    expect(screen.getByRole("link", { name: /request a feature/i })).toHaveAttribute("href", "/feedback");
    expect(screen.getByRole("link", { name: /terms/i })).toHaveAttribute("href", "/terms");
    expect(screen.getByRole("link", { name: /privacy/i })).toHaveAttribute("href", "/privacy");
  });
});
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd frontend && npx jest src/components/__tests__/LayoutFooter.test.tsx`
Expected: FAIL — no "report a bug" link (current footer says "Feedback").

- [ ] **Step 3: Replace the footer block**

In `Layout.tsx`, add `Bug` to imports (`import { Bug } from "lucide-react";`) and replace the entire existing `<footer>...</footer>` with:

```tsx
      <footer className="py-6 px-4 border-t border-border/40 mt-auto">
        <div className="max-w-7xl mx-auto flex flex-wrap items-center justify-center gap-x-3 gap-y-2 text-sm text-muted-foreground">
          <Link to="/feedback" className="inline-flex items-center gap-1.5 hover:text-foreground transition-colors">
            <Bug className="w-3.5 h-3.5" />
            Report a bug
          </Link>
          <span aria-hidden="true">·</span>
          <Link to="/feedback" className="hover:text-foreground transition-colors">
            Request a feature
          </Link>
          <span aria-hidden="true">·</span>
          <Link to="/terms" className="hover:text-foreground transition-colors">
            Terms
          </Link>
          <span aria-hidden="true">·</span>
          <Link to="/privacy" className="hover:text-foreground transition-colors">
            Privacy
          </Link>
          <span className="text-xs text-muted-foreground/60" title="Frontend build">
            v{APP_VERSION}
          </span>
        </div>
      </footer>
```

- [ ] **Step 4: Run test + build**

Run: `cd frontend && npx jest src/components/__tests__/LayoutFooter.test.tsx && npx vite build`
Expected: PASS; clean build.

- [ ] **Step 5: Commit**

```bash
git add frontend/src/components/Layout.tsx frontend/src/components/__tests__/LayoutFooter.test.tsx
git commit -m "feat(ui): centered minimal footer with report-a-bug link"
```

---

### Task 4: DemoLoop component (TDD)

**Files:**
- Create: `frontend/src/components/DemoLoop.tsx`
- Modify: `frontend/src/index.css` (append demo keyframes)
- Test: `frontend/src/components/__tests__/DemoLoop.test.tsx` (new)

**Interfaces:**
- Produces: `<DemoLoop />` (no props). Consumed by Task 5 (Index).

- [ ] **Step 1: Write the failing test**

```tsx
// frontend/src/components/__tests__/DemoLoop.test.tsx
import React from "react";
import "@testing-library/jest-dom";
import { render, screen } from "@testing-library/react";
import DemoLoop from "../DemoLoop";

describe("DemoLoop", () => {
  it("renders the three scenes and progress dots", () => {
    const { container } = render(<DemoLoop />);
    expect(screen.getByText(/plank · hold \+ form/i)).toBeInTheDocument();
    expect(screen.getByText(/bowl · ball tracking/i)).toBeInTheDocument();
    expect(screen.getByText(/golf · scorecard → handicap/i)).toBeInTheDocument();
    expect(container.querySelectorAll(".demo-dot").length).toBe(3);
    // payoff pills
    expect(screen.getByText("Hips level ✓")).toBeInTheDocument();
    expect(screen.getByText("Board 17 · Pocket ✓")).toBeInTheDocument();
    expect(screen.getByText("HCP 21.0")).toBeInTheDocument();
  });
});
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd frontend && npx jest src/components/__tests__/DemoLoop.test.tsx`
Expected: FAIL — Cannot find module '../DemoLoop'.

- [ ] **Step 3: Append demo CSS to `frontend/src/index.css`**

```css
/* Quiet-gym demo loop (DemoLoop.tsx) — 12s cycle: plank 0-4s, bowl 4-8s, golf 8-12s */
.demo-scene { opacity: 0; animation: demo-scene-cycle 12s infinite; }
.demo-scene-bowl { animation-delay: 4s; }
.demo-scene-golf { animation-delay: 8s; }
@keyframes demo-scene-cycle {
  0% { opacity: 0; } 4% { opacity: 1; } 32% { opacity: 1; } 36% { opacity: 0; } 100% { opacity: 0; }
}
.demo-plank-bob { animation: demo-plank-bob 3s ease-in-out infinite; }
@keyframes demo-plank-bob {
  0%, 100% { transform: translateY(0); } 50% { transform: translateY(2px); }
}
.demo-timer { opacity: 0; animation: 12s infinite; }
.demo-timer-1 { animation-name: demo-timer-1; }
.demo-timer-2 { animation-name: demo-timer-2; }
.demo-timer-3 { animation-name: demo-timer-3; }
@keyframes demo-timer-1 { 0% { opacity: 1; } 11% { opacity: 1; } 12%, 100% { opacity: 0; } }
@keyframes demo-timer-2 { 0%, 11% { opacity: 0; } 12%, 22% { opacity: 1; } 23%, 100% { opacity: 0; } }
@keyframes demo-timer-3 { 0%, 22% { opacity: 0; } 23%, 32% { opacity: 1; } 36%, 100% { opacity: 0; } }
.demo-pill-plank { opacity: 0; animation: demo-pill-plank 12s infinite; }
@keyframes demo-pill-plank {
  0%, 14% { opacity: 0; transform: translateY(4px); }
  17%, 32% { opacity: 1; transform: translateY(0); }
  36%, 100% { opacity: 0; }
}
.demo-trace { stroke-dasharray: 150; stroke-dashoffset: 150; animation: demo-trace 12s infinite; }
@keyframes demo-trace {
  0%, 38% { stroke-dashoffset: 150; }
  56% { stroke-dashoffset: 0; }
  66%, 100% { stroke-dashoffset: 0; }
}
.demo-pill-bowl { opacity: 0; animation: demo-pill-bowl 12s infinite; }
@keyframes demo-pill-bowl {
  0%, 57% { opacity: 0; transform: translateY(4px); }
  60%, 65% { opacity: 1; transform: translateY(0); }
  69%, 100% { opacity: 0; }
}
.demo-scanline { animation: demo-scan 12s infinite; }
@keyframes demo-scan {
  0%, 69% { transform: translateX(0); }
  86%, 100% { transform: translateX(380px); }
}
.demo-pill-golf { opacity: 0; animation: demo-pill-golf 12s infinite; }
@keyframes demo-pill-golf {
  0%, 87% { opacity: 0; transform: translateY(4px); }
  90%, 98% { opacity: 1; transform: translateY(0); }
  100% { opacity: 0; }
}
.demo-dot { animation: demo-dot-cycle 12s infinite; }
.demo-dot:nth-child(2) { animation-delay: 4s; }
.demo-dot:nth-child(3) { animation-delay: 8s; }
@keyframes demo-dot-cycle {
  0%, 4% { background: hsl(var(--accent)); } 32% { background: hsl(var(--accent)); }
  36%, 100% { background: hsl(var(--secondary)); }
}
@media (prefers-reduced-motion: reduce) {
  .demo-scene, .demo-plank-bob, .demo-timer, .demo-pill-plank, .demo-trace,
  .demo-pill-bowl, .demo-scanline, .demo-pill-golf, .demo-dot { animation: none; }
  .demo-scene-plank { opacity: 1; }
  .demo-pill-plank, .demo-timer-3 { opacity: 1; }
}
```

- [ ] **Step 4: Implement the component**

```tsx
// frontend/src/components/DemoLoop.tsx
import React from "react";

/**
 * Home-page demo loop: a 12s CSS/SVG animation cycling three scenes of what
 * the app actually does — a plank hold with timer + form check, a bowling
 * ball tracked down the lane, and a scorecard scanned into a handicap.
 * Pure presentation; all timing lives in index.css (demo-* keyframes).
 * Reference: docs/superpowers/specs/assets/2026-07-06-home-redesign-mockup.html
 */
const DemoLoop: React.FC = () => (
  <div>
    <div className="relative glass rounded-2xl overflow-hidden h-[190px]">
      {/* Scene 1: Plank — figure holds, timer counts up, form check pops */}
      <div className="demo-scene demo-scene-plank absolute inset-0">
        <span className="absolute top-3 left-4 text-xs uppercase tracking-wider text-muted-foreground">
          Plank · hold + form
        </span>
        <svg viewBox="0 0 560 190" className="w-full h-full" aria-hidden="true">
          <line x1="80" y1="160" x2="480" y2="160" stroke="hsl(240 4% 22%)" strokeWidth="2" />
          <g className="demo-plank-bob" stroke="hsl(0 0% 80%)" strokeWidth="5" strokeLinecap="round" fill="none">
            <circle cx="176" cy="116" r="11" fill="hsl(0 0% 80%)" stroke="none" />
            <line x1="196" y1="124" x2="352" y2="142" />
            <line x1="200" y1="126" x2="192" y2="156" />
            <line x1="178" y1="157" x2="212" y2="157" />
            <line x1="352" y1="142" x2="362" y2="158" />
          </g>
          <g fontSize="26" fontWeight="700" fill="hsl(0 0% 92%)" textAnchor="middle" fontFamily="ui-monospace, SFMono-Regular, Menlo, monospace">
            <text className="demo-timer demo-timer-1" x="440" y="90">0:15</text>
            <text className="demo-timer demo-timer-2" x="440" y="90">0:32</text>
            <text className="demo-timer demo-timer-3" x="440" y="90">0:47</text>
          </g>
          <text x="440" y="108" textAnchor="middle" fontSize="11" fill="hsl(240 5% 55%)" letterSpacing="1">HOLD</text>
          <g className="demo-pill-plank">
            <rect x="386" y="122" width="108" height="26" rx="13" fill="hsl(160 70% 45% / 0.15)" />
            <text x="440" y="139" textAnchor="middle" fontSize="13" fontWeight="600" fill="hsl(160 70% 55%)">Hips level ✓</text>
          </g>
        </svg>
      </div>

      {/* Scene 2: Bowl — ball hooks down the lane, trace draws */}
      <div className="demo-scene demo-scene-bowl absolute inset-0">
        <span className="absolute top-3 left-4 text-xs uppercase tracking-wider text-muted-foreground">
          Bowl · ball tracking
        </span>
        <svg viewBox="0 0 560 190" className="w-full h-full" aria-hidden="true">
          <path d="M 240 28 L 320 28 L 400 168 L 160 168 Z" fill="hsl(240 4% 14%)" stroke="hsl(240 4% 22%)" />
          <g fill="hsl(0 0% 85%)">
            <circle cx="262" cy="24" r="5" /><circle cx="280" cy="20" r="5" /><circle cx="298" cy="24" r="5" />
            <circle cx="271" cy="30" r="5" /><circle cx="289" cy="30" r="5" />
          </g>
          <path
            className="demo-trace"
            d="M 285 158 C 320 120 322 70 284 32"
            fill="none"
            stroke="hsl(220 90% 56%)"
            strokeWidth="2.5"
            strokeDasharray="4 5"
            strokeLinecap="round"
          />
          <circle r="9" fill="hsl(220 90% 56%)">
            <animateMotion
              dur="12s"
              repeatCount="indefinite"
              calcMode="linear"
              keyPoints="0;0;1;1"
              keyTimes="0;0.38;0.56;1"
              path="M 285 158 C 320 120 322 70 284 32"
            />
          </circle>
          <g className="demo-pill-bowl">
            <rect x="398" y="70" width="128" height="26" rx="13" fill="hsl(220 90% 56% / 0.15)" />
            <text x="462" y="87" textAnchor="middle" fontSize="13" fontWeight="600" fill="hsl(220 90% 66%)">Board 17 · Pocket ✓</text>
          </g>
        </svg>
      </div>

      {/* Scene 3: Golf — scan line reads the scorecard, handicap pops */}
      <div className="demo-scene demo-scene-golf absolute inset-0">
        <span className="absolute top-3 left-4 text-xs uppercase tracking-wider text-muted-foreground">
          Golf · scorecard → handicap
        </span>
        <svg viewBox="0 0 560 190" className="w-full h-full" aria-hidden="true">
          <g stroke="hsl(240 4% 24%)" fill="none">
            <rect x="90" y="60" width="380" height="70" rx="6" />
            <line x1="90" y1="95" x2="470" y2="95" />
            <line x1="132" y1="60" x2="132" y2="130" /><line x1="174" y1="60" x2="174" y2="130" />
            <line x1="216" y1="60" x2="216" y2="130" /><line x1="258" y1="60" x2="258" y2="130" />
            <line x1="300" y1="60" x2="300" y2="130" /><line x1="342" y1="60" x2="342" y2="130" />
            <line x1="384" y1="60" x2="384" y2="130" /><line x1="426" y1="60" x2="426" y2="130" />
          </g>
          <g fontSize="12" fill="hsl(240 5% 55%)" textAnchor="middle">
            <text x="111" y="82">1</text><text x="153" y="82">2</text><text x="195" y="82">3</text>
            <text x="237" y="82">4</text><text x="279" y="82">5</text><text x="321" y="82">6</text>
            <text x="363" y="82">7</text><text x="405" y="82">8</text><text x="448" y="82">9</text>
          </g>
          <g fontSize="13" fontWeight="600" fill="hsl(0 0% 88%)" textAnchor="middle">
            <text x="111" y="118">5</text><text x="153" y="118">4</text><text x="195" y="118">4</text>
            <text x="237" y="118">6</text><text x="279" y="118">3</text><text x="321" y="118">5</text>
            <text x="363" y="118">4</text><text x="405" y="118">5</text><text x="448" y="118">4</text>
          </g>
          <line className="demo-scanline" x1="90" y1="52" x2="90" y2="138" stroke="hsl(220 90% 56%)" strokeWidth="2" />
          <g className="demo-pill-golf">
            <rect x="238" y="146" width="90" height="28" rx="14" fill="hsl(160 70% 45% / 0.15)" />
            <text x="283" y="165" textAnchor="middle" fontSize="14" fontWeight="700" fill="hsl(160 70% 55%)">HCP 21.0</text>
          </g>
        </svg>
      </div>
    </div>
    <div className="flex gap-1.5 justify-center mt-3" aria-hidden="true">
      <span className="demo-dot w-1.5 h-1.5 rounded-full bg-secondary" />
      <span className="demo-dot w-1.5 h-1.5 rounded-full bg-secondary" />
      <span className="demo-dot w-1.5 h-1.5 rounded-full bg-secondary" />
    </div>
  </div>
);

export default DemoLoop;
```

- [ ] **Step 5: Run test + build**

Run: `cd frontend && npx jest src/components/__tests__/DemoLoop.test.tsx && npx vite build`
Expected: PASS (1 test); clean build.

- [ ] **Step 6: Commit**

```bash
git add frontend/src/components/DemoLoop.tsx frontend/src/components/__tests__/DemoLoop.test.tsx frontend/src/index.css
git commit -m "feat(home): animated plank/bowl/golf demo loop"
```

---

### Task 5: Index rebuild (TDD)

**Files:**
- Rewrite: `frontend/src/pages/Index.tsx`
- Test: `frontend/src/pages/__tests__/Index.test.tsx` (new)

**Interfaces:**
- Consumes: `IconTile`, `RowCard` (Task 1), `DemoLoop` (Task 4), `getCompetitions()` from `../lib/api`.

- [ ] **Step 1: Write the failing test**

```tsx
// frontend/src/pages/__tests__/Index.test.tsx
import React from "react";
import "@testing-library/jest-dom";
import { render, screen, waitFor } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import Index from "../Index";
import * as api from "../../lib/api";

// config.ts uses import.meta (Vite), which jest can't parse; mock it as the
// repo's other tests do.
jest.mock("../../config", () => ({ API_URL: "https://test-api.example" }));

// Layout pulls in the Navbar/auth tree; stub it so the test stays on the page.
jest.mock("../../components/Layout", () => ({
  __esModule: true,
  default: ({ children }: { children: React.ReactNode }) => <div>{children}</div>,
}));

jest.mock("../../lib/api", () => ({
  ...jest.requireActual("../../lib/api"),
  getCompetitions: jest.fn(),
}));

const ongoing = { id: "c1", title: "Summer Plank Challenge", status: "ongoing", categories: ["Plank"] };
const completed = { id: "c2", title: "Old Squat-Off", status: "completed", categories: ["Squat"] };

const renderHome = () =>
  render(
    <MemoryRouter>
      <Index />
    </MemoryRouter>
  );

describe("Index (quiet-gym home)", () => {
  beforeEach(() => jest.clearAllMocks());

  it("renders the three vertical tiles with the right upload targets", async () => {
    (api.getCompetitions as jest.Mock).mockResolvedValue([]);
    renderHome();
    expect(screen.getByRole("link", { name: /lift/i })).toHaveAttribute("href", "/lift/upload");
    expect(screen.getByRole("link", { name: /bowl/i })).toHaveAttribute("href", "/bowling/upload");
    expect(screen.getByRole("link", { name: /golf/i })).toHaveAttribute("href", "/golf/snap");
    await waitFor(() => expect(api.getCompetitions).toHaveBeenCalled());
  });

  it("shows only ongoing challenges as row cards linking to their pages", async () => {
    (api.getCompetitions as jest.Mock).mockResolvedValue([ongoing, completed]);
    renderHome();
    await waitFor(() =>
      expect(screen.getByText("Summer Plank Challenge")).toBeInTheDocument()
    );
    expect(screen.getByText("Summer Plank Challenge").closest("a")).toHaveAttribute("href", "/challenges/c1");
    expect(screen.getByText("Plank")).toBeInTheDocument();
    expect(screen.queryByText("Old Squat-Off")).toBeNull();
    expect(screen.getByText(/open challenges/i)).toBeInTheDocument();
  });

  it("hides the strip label entirely when nothing is ongoing but keeps an All challenges link", async () => {
    (api.getCompetitions as jest.Mock).mockResolvedValue([completed]);
    renderHome();
    await waitFor(() => expect(api.getCompetitions).toHaveBeenCalled());
    expect(screen.queryByText(/open challenges/i)).toBeNull();
    expect(screen.getByRole("link", { name: /all challenges/i })).toHaveAttribute("href", "/challenges");
  });

  it("renders the demo loop", async () => {
    (api.getCompetitions as jest.Mock).mockResolvedValue([]);
    renderHome();
    expect(screen.getByText(/plank · hold \+ form/i)).toBeInTheDocument();
    await waitFor(() => expect(api.getCompetitions).toHaveBeenCalled());
  });
});
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd frontend && npx jest src/pages/__tests__/Index.test.tsx`
Expected: FAIL — current page renders TopLifts/photo cards; tile hrefs point at old targets; no row cards.

- [ ] **Step 3: Rewrite `Index.tsx`**

Replace the whole file with:

```tsx
import React, { useEffect, useState } from "react";
import { motion } from "framer-motion";
import { Link } from "react-router-dom";
import { Dumbbell, Target, Flag, Timer } from "lucide-react";
import Layout from "../components/Layout";
import IconTile from "../components/IconTile";
import RowCard from "../components/RowCard";
import DemoLoop from "../components/DemoLoop";
import { getCompetitions } from "../lib/api";
import { Competition } from "../lib/types";

// The three analysis verticals — each tile IS the upload entry point.
const VERTICALS = [
  {
    to: "/lift/upload",
    icon: <Dumbbell className="w-5 h-5" />,
    title: "Lift",
    description: "Per-rep grades on squat, bench, deadlift & curls.",
  },
  {
    to: "/bowling/upload",
    icon: <Target className="w-5 h-5" />,
    title: "Bowl",
    description: "Ball trajectory, entry board & pocket impact.",
  },
  {
    to: "/golf/snap",
    icon: <Flag className="w-5 h-5" />,
    title: "Golf",
    description: "Snap a scorecard, get your handicap.",
  },
];

const Index = () => {
  const [open, setOpen] = useState<Competition[]>([]);

  useEffect(() => {
    let cancelled = false;
    getCompetitions()
      .then((comps) => {
        if (cancelled) return;
        setOpen(comps.filter((c) => c.status === "ongoing"));
      })
      .catch(() => {}); // non-fatal: strip simply stays hidden
    return () => {
      cancelled = true;
    };
  }, []);

  return (
    <Layout>
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.5, ease: "easeOut" }}
        className="max-w-2xl mx-auto text-center flex flex-col gap-14 py-10"
      >
        {/* Hero */}
        <section>
          <h1 className="text-3xl md:text-4xl font-bold leading-tight mb-3 text-balance">
            AI analysis of your lift, bowl, or round — in minutes.
          </h1>
          <p className="text-muted-foreground max-w-md mx-auto">
            Upload a video or snap a photo and get annotated feedback. No signup — just your email.
          </p>
        </section>

        {/* Animated demo of what the analysis produces */}
        <section aria-label="Analysis demo">
          <DemoLoop />
        </section>

        {/* The three verticals */}
        <section className="grid grid-cols-1 sm:grid-cols-3 gap-3.5">
          {VERTICALS.map((v) => (
            <IconTile key={v.to} {...v} />
          ))}
        </section>

        {/* Open challenges — hidden entirely when nothing is ongoing */}
        <section className="flex flex-col gap-2.5">
          {open.length > 0 && (
            <>
              <div className="flex items-center gap-3.5 text-xs uppercase tracking-widest text-muted-foreground mb-1">
                <span className="flex-1 h-px bg-border" aria-hidden="true" />
                Open challenges
                <span className="flex-1 h-px bg-border" aria-hidden="true" />
              </div>
              {open.map((c) => (
                <RowCard
                  key={c.id}
                  to={`/challenges/${c.id}`}
                  icon={<Timer className="w-[18px] h-[18px]" />}
                  title={c.title}
                  pill={c.categories?.[0]}
                />
              ))}
            </>
          )}
          <Link
            to="/challenges"
            className="text-sm text-muted-foreground hover:text-foreground transition-colors mt-1"
          >
            All challenges →
          </Link>
        </section>
      </motion.div>
    </Layout>
  );
};

export default Index;
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd frontend && npx jest src/pages/__tests__/Index.test.tsx`
Expected: PASS (4 tests).

- [ ] **Step 5: Full-suite sanity + build**

Run: `cd frontend && npx jest && npx vite build`
Expected: all suites pass (nothing else imports Index; TopLifts/getFeaturedChallenges now unused by Index but still exported — fine); clean build.

- [ ] **Step 6: Commit**

```bash
git add frontend/src/pages/Index.tsx frontend/src/pages/__tests__/Index.test.tsx
git commit -m "feat(home): minimal centered home — demo loop, icon tiles, open challenges"
```

---

### Task 6: HubPage restyle

**Files:**
- Modify: `frontend/src/components/HubPage.tsx`

**Interfaces:**
- Consumes: `RowCard` (Task 1). `HubPageProps` / `HubLink` types unchanged (LiftHub/BowlHub/GolfHub compile as-is; `description` on secondary links is accepted but no longer rendered).

- [ ] **Step 1: Restyle**

Replace the component body's JSX (keep the interfaces and imports, add `import RowCard from "./RowCard";`, drop the now-unused `ArrowRight` import ONLY if unused after the edit — the primary CTA still uses it, so keep it):

```tsx
const HubPage: React.FC<HubPageProps> = ({ title, subtitle, icon, primary, secondary }) => {
  return (
    <Layout>
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.5 }}
        className="max-w-2xl mx-auto text-center py-6"
      >
        <div className="flex flex-col items-center gap-2 mb-2">
          <span className="w-14 h-14 rounded-2xl bg-accent/10 text-accent grid place-items-center">
            {icon}
          </span>
          <h1 className="text-3xl font-semibold">{title}</h1>
        </div>
        <p className="text-muted-foreground mb-8 max-w-md mx-auto">{subtitle}</p>

        {/* Primary CTA — Upload */}
        <Link
          to={primary.to}
          className="group flex items-center justify-between w-full p-6 mb-8 rounded-2xl bg-accent text-accent-foreground shadow-sm hover:bg-accent/90 transition-colors text-left"
        >
          <div className="flex items-center gap-4">
            <span>{primary.icon}</span>
            <div>
              <p className="text-lg font-semibold">{primary.label}</p>
              {primary.description && (
                <p className="text-sm text-accent-foreground/80">{primary.description}</p>
              )}
            </div>
          </div>
          <ArrowRight className="w-6 h-6 transition-transform group-hover:translate-x-1" />
        </Link>

        {/* Secondary surfaces — quiet-gym rows */}
        <div className="flex flex-col gap-2.5">
          {secondary.map((item) => (
            <RowCard
              key={item.to + item.label}
              to={item.to}
              icon={item.icon}
              title={item.label}
            />
          ))}
        </div>
      </motion.div>
    </Layout>
  );
};
```

- [ ] **Step 2: Verify LiftHub test still green + build**

Run: `cd frontend && npx jest src/pages/__tests__/LiftHub.test.tsx && npx vite build`
Expected: PASS (the plank quick link renders its `label` through RowCard's `title`); clean build.

- [ ] **Step 3: Commit**

```bash
git add frontend/src/components/HubPage.tsx
git commit -m "feat(hubs): centered quiet-gym hub layout with row-card links"
```

---

### Task 7: UploadChooser restyle

**Files:**
- Modify: `frontend/src/pages/UploadChooser.tsx`

**Interfaces:**
- Consumes: `IconTile` (Task 1).

- [ ] **Step 1: Restyle**

Replace the whole file with:

```tsx
import React from "react";
import { motion } from "framer-motion";
import { Dumbbell, Target, Flag } from "lucide-react";
import Layout from "../components/Layout";
import IconTile from "../components/IconTile";

/**
 * Unified upload entry (T7). Asks "What are you analyzing?" and routes to
 * one of the three existing, separate upload flows — same tiles as home.
 */
const OPTIONS = [
  {
    to: "/lift/upload",
    title: "Lift",
    description: "Per-rep grades on squat, bench, deadlift & curls.",
    icon: <Dumbbell className="w-5 h-5" />,
  },
  {
    to: "/bowling/upload",
    title: "Bowl",
    description: "Ball trajectory, entry board & pocket impact.",
    icon: <Target className="w-5 h-5" />,
  },
  {
    to: "/golf/snap",
    title: "Golf",
    description: "Snap a scorecard, get your handicap.",
    icon: <Flag className="w-5 h-5" />,
  },
];

const UploadChooser: React.FC = () => {
  return (
    <Layout>
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.5 }}
        className="max-w-2xl mx-auto text-center py-10"
      >
        <h1 className="text-3xl font-semibold mb-2">What are you analyzing?</h1>
        <p className="text-muted-foreground mb-8">
          Pick a sport to start — each upload gives you analysis you can't get anywhere else.
        </p>

        <div className="grid grid-cols-1 sm:grid-cols-3 gap-3.5">
          {OPTIONS.map((opt) => (
            <IconTile key={opt.to} {...opt} />
          ))}
        </div>
      </motion.div>
    </Layout>
  );
};

export default UploadChooser;
```

Note: golf now routes to `/golf/snap` (camera-first), consistent with home.

- [ ] **Step 2: Verify build**

Run: `cd frontend && npx vite build`
Expected: clean build.

- [ ] **Step 3: Commit**

```bash
git add frontend/src/pages/UploadChooser.tsx
git commit -m "feat(upload): chooser uses home icon tiles, golf snap route"
```

---

### Task 8: Challenges page pass

**Files:**
- Modify: `frontend/src/pages/Challenges.tsx`

**Interfaces:**
- Consumes: `RowCard` (Task 1); the page's existing `challenges` state (transformed `Challenge` objects with `id`, `title`, `status`, `categories`).

- [ ] **Step 1: Restyle header + add Open-now strip**

In `Challenges.tsx`:

(a) Add imports:

```tsx
import RowCard from "../components/RowCard";
import { Timer } from "lucide-react";
```

(b) Replace the header block (the `motion.div` containing the h1 + Create button, currently a left/right flex) with a centered version:

```tsx
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.5 }}
        className="mb-8 text-center"
      >
        <h1 className="text-3xl font-semibold mb-2">Challenges</h1>
        <p className="text-muted-foreground mb-4">
          Browse all available lifting challenges and find the perfect one for you.
        </p>
        <button
          onClick={() => setIsCreateModalOpen(true)}
          className="inline-flex items-center gap-2 px-4 py-2 bg-accent text-white rounded-md hover:bg-accent/90 transition-colors"
        >
          <Plus size={20} />
          <span>Create Challenge</span>
        </button>
      </motion.div>
```

(c) Immediately after the error block, before the "All Challenges" section, insert the Open-now strip (mirrors home):

```tsx
      {challenges.some((c) => c.status === "ongoing") && (
        <div className="max-w-2xl mx-auto mb-10 flex flex-col gap-2.5">
          <div className="flex items-center gap-3.5 text-xs uppercase tracking-widest text-muted-foreground mb-1">
            <span className="flex-1 h-px bg-border" aria-hidden="true" />
            Open now
            <span className="flex-1 h-px bg-border" aria-hidden="true" />
          </div>
          {challenges
            .filter((c) => c.status === "ongoing")
            .map((c) => (
              <RowCard
                key={c.id}
                to={`/challenges/${c.id}`}
                icon={<Timer className="w-[18px] h-[18px]" />}
                title={c.title}
                pill={c.categories?.[0]}
              />
            ))}
        </div>
      )}
```

(d) Restyle the filter buttons to the pill language — replace the button `className` template with:

```tsx
                className={`px-3 py-1 text-sm rounded-full transition-all ${
                  activeFilter === filter
                    ? "bg-accent/15 text-accent border border-accent/30"
                    : "bg-secondary/50 text-muted-foreground hover:text-foreground border border-transparent"
                }`}
```

- [ ] **Step 2: Verify build + full jest**

Run: `cd frontend && npx jest && npx vite build`
Expected: all suites pass; clean build.

- [ ] **Step 3: Commit**

```bash
git add frontend/src/pages/Challenges.tsx
git commit -m "feat(challenges): centered header, open-now strip, pill filters"
```

---

### Task 9: Leaderboard light touch

**Files:**
- Modify: `frontend/src/pages/Leaderboard.tsx` (filter buttons only, ~lines 103-115)

- [ ] **Step 1: Restyle the category filter buttons**

Replace the button `className` template (in the `['total','squat','bench','deadlift']` map) with:

```tsx
                className={`px-4 py-2 rounded-full transition-all ${
                  activeCategory === category
                    ? "bg-accent/15 text-accent border border-accent/30"
                    : "bg-secondary/50 text-muted-foreground hover:text-foreground border border-transparent"
                }`}
```

(Header is already centered; selects and table untouched.)

- [ ] **Step 2: Verify build**

Run: `cd frontend && npx vite build`
Expected: clean build.

- [ ] **Step 3: Commit**

```bash
git add frontend/src/pages/Leaderboard.tsx
git commit -m "feat(leaderboard): pill-language filter styling"
```

---

### Task 10: Full gate + deploy + prod verify + docs

**Files:**
- Modify: `CLAUDE.md` (add shipped section)

- [ ] **Step 1: Full validation gate**

Run: `cd frontend && npx jest && npx vite build && npx tsc --noEmit`
Expected: all suites pass (existing + 6 new), clean build, 0 type errors.

- [ ] **Step 2: Spec-coverage check**

Confirm against `docs/superpowers/specs/2026-07-06-home-redesign-cohesion-design.md`: AmbientBackground (Task 2), IconTile/RowCard (Task 1), DemoLoop (Task 4), Index rebuild (Task 5), Layout footer (Task 3), HubPage (Task 6), UploadChooser (Task 7), Challenges (Task 8), Leaderboard (Task 9). Golf fw-* internals: verify `git diff --stat` shows no `Golf*.tsx` page changes.

- [ ] **Step 3: Deploy + prod verification (project convention)**

Run: `python3 deploy.py --frontend-only --skip-iam`
Then verify on the prod URL: home shows hero + demo loop + tiles + strip (or no strip if nothing ongoing); footer shows "Report a bug"; hubs/chooser/challenges/leaderboard render the new styling; a golf fw-* page still renders correctly over the ambient background. Check the served page chunks contain marker strings (e.g. `Plank · hold + form`, `Report a bug`).

- [ ] **Step 4: Update CLAUDE.md + mark plan complete, commit**

Add a "Home Redesign + Quiet-Gym Cohesion (shipped 2026-07-06)" section to `CLAUDE.md` summarizing: new components (AmbientBackground/IconTile/RowCard/DemoLoop), Layout footer, Index rebuild (TopLifts removed from page, component file retained), page passes, and test suites added. Mark all checkboxes in this plan.

```bash
git add CLAUDE.md docs/superpowers/plans/2026-07-06-home-redesign-cohesion.md
git commit -m "docs: record home redesign + quiet-gym cohesion pass"
```
