# Easy Upload Flows Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Camera-first capture for golf scorecards and plank videos, plus a handicap-first confirmation screen — per spec `docs/superpowers/specs/2026-07-06-easy-upload-flows-design.md`.

**Architecture:** Frontend-only. Two `capture` attributes open the phone camera directly; a `/golf/snap` route + PWA shortcut removes navigation taps; a new small `HandicapResultCard` component makes the post-confirm screen lead with the handicap + delta; LiftHub gains a dynamic "Plank challenge" quick link. No backend changes.

**Tech Stack:** React 18 + TypeScript, react-router, jest + React Testing Library, Tailwind-style utility classes with the golf `fw-*` token system (golf pages only).

## Global Constraints

- No auto-confirm of OCR scores anywhere; the GolfReview review pass is untouched except the confirmed-state render.
- No new backend endpoints; use `GET /golf/handicap/<user_id>` (exists) for the previous index.
- Keep the "choose from library" path on both uploads (two-input pattern); `capture` goes ONLY on the camera input.
- Golf pages use `fw-*` CSS tokens (match `GolfReview.tsx` styles); challenge pages use the default token set — do not mix.
- Delta color convention: lower handicap = improvement = `var(--fw-text-success)` (green); rise = `var(--fw-danger)` — matches GolfLeaderboard's monthly-delta pill.
- Validation gate for every task: `cd frontend && npx jest <test file> && npx vite build`. Final task runs the full suite + `npx tsc --noEmit`.
- Discovery already verified: plank lift-type pre-set/lock is ALREADY implemented (`ChallengeDetail.tsx:440-454` + `onlyOne` fixed label at `:840`) — spec item B3 needs no work.

---

### Task 1: Camera-capture input on GolfUpload

**Files:**
- Modify: `frontend/src/pages/GolfUpload.tsx` (input block ~lines 131-168)
- Test: `frontend/src/pages/__tests__/GolfUpload.test.tsx` (new)

**Interfaces:**
- Produces: hidden inputs `#golf-scorecard-upload` (library, no `capture`) and `#golf-scorecard-camera` (`capture="environment"`); a `cameraInputRef` and optional `autoCamera` prop consumed by Task 2.

- [ ] **Step 1: Write the failing test**

```tsx
// frontend/src/pages/__tests__/GolfUpload.test.tsx
import React from "react";
import { render } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import GolfUpload from "../GolfUpload";

jest.mock("axios");

const renderPage = (props = {}) =>
  render(
    <MemoryRouter>
      <GolfUpload {...props} />
    </MemoryRouter>
  );

describe("GolfUpload capture inputs", () => {
  it("has a camera input with capture=environment and a library input without capture", () => {
    renderPage();
    const camera = document.getElementById("golf-scorecard-camera");
    const library = document.getElementById("golf-scorecard-upload");
    expect(camera).not.toBeNull();
    expect(camera!.getAttribute("capture")).toBe("environment");
    expect(camera!.getAttribute("accept")).toBe("image/*");
    expect(library).not.toBeNull();
    expect(library!.hasAttribute("capture")).toBe(false);
  });

  it("auto-clicks the camera input when autoCamera is set", () => {
    const clickSpy = jest
      .spyOn(HTMLInputElement.prototype, "click")
      .mockImplementation(() => {});
    renderPage({ autoCamera: true });
    expect(clickSpy).toHaveBeenCalled();
    clickSpy.mockRestore();
  });
});
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd frontend && npx jest src/pages/__tests__/GolfUpload.test.tsx`
Expected: FAIL — camera element is null (first test); autoCamera prop unknown/no click (second test).

- [ ] **Step 3: Implement**

In `GolfUpload.tsx`:

(a) Change the component signature and add the ref/effect (imports: add `useRef`, `useEffect` if absent):

```tsx
const GolfUpload: React.FC<{ autoCamera?: boolean }> = ({ autoCamera = false }) => {
  const cameraInputRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    // /golf/snap fast path: try to open the camera immediately. Browsers that
    // require a user gesture ignore this; the "Capture photo" button remains.
    if (autoCamera) cameraInputRef.current?.click();
  }, [autoCamera]);
```

(b) Next to the existing hidden input, add the camera input:

```tsx
<input
  type="file"
  accept="image/*"
  capture="environment"
  onChange={handleFileSelect}
  className="hidden"
  id="golf-scorecard-camera"
  ref={cameraInputRef}
/>
```

(c) Point the "Capture photo" button at it (the "Upload from library" button keeps `#golf-scorecard-upload`):

```tsx
onClick={() => cameraInputRef.current?.click()}
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd frontend && npx jest src/pages/__tests__/GolfUpload.test.tsx`
Expected: PASS (2 tests). If render fails on unmocked network calls, add `(axios.get as jest.Mock).mockResolvedValue({ data: {} })` in a `beforeEach`.

- [ ] **Step 5: Commit**

```bash
git add frontend/src/pages/GolfUpload.tsx frontend/src/pages/__tests__/GolfUpload.test.tsx
git commit -m "feat(golf): camera-first capture input on scorecard upload"
```

---

### Task 2: /golf/snap route, PWA shortcut, GolfHub CTA

**Files:**
- Modify: `frontend/src/routes/index.tsx` (route table)
- Modify: `frontend/public/manifest.json`
- Modify: `frontend/src/pages/GolfHub.tsx` (primary CTA target)

**Interfaces:**
- Consumes: `GolfUpload` `autoCamera` prop (Task 1).
- Produces: route `/golf/snap`.

- [ ] **Step 1: Add the route**

In `frontend/src/routes/index.tsx`, after `{ path: "/golf/upload", element: <GolfUpload /> },`:

```tsx
// Easy-upload flows: camera-first scorecard capture (PWA shortcut target)
{ path: "/golf/snap", element: <GolfUpload autoCamera /> },
```

Note: `GolfUpload` is lazy-imported already; reuse that import.

- [ ] **Step 2: Add the manifest shortcut**

In `frontend/public/manifest.json`, add after `"background_color": "#1a1b1e"` (inside the root object):

```json
"shortcuts": [
  {
    "name": "Snap scorecard",
    "short_name": "Snap card",
    "description": "Open the camera to photograph a golf scorecard",
    "url": "/golf/snap",
    "icons": [{ "src": "logo192.png", "sizes": "192x192" }]
  }
]
```

- [ ] **Step 3: Point GolfHub's primary CTA at the snap route**

In `frontend/src/pages/GolfHub.tsx`, change the `primary.to` value from `"/golf/upload"` to `"/golf/snap"` and keep label/description ("Snap a scorecard" wording stays accurate).

- [ ] **Step 4: Verify**

Run: `cd frontend && npx jest src/pages/__tests__/GolfUpload.test.tsx && npx vite build`
Expected: tests PASS; build succeeds; `manifest.json` is valid JSON (build copies it).

- [ ] **Step 5: Commit**

```bash
git add frontend/src/routes/index.tsx frontend/public/manifest.json frontend/src/pages/GolfHub.tsx
git commit -m "feat(golf): /golf/snap fast route + PWA shortcut, hub CTA"
```

---

### Task 3: HandicapResultCard component (TDD)

**Files:**
- Create: `frontend/src/components/golf/HandicapResultCard.tsx`
- Test: `frontend/src/components/golf/__tests__/HandicapResultCard.test.tsx` (new)

**Interfaces:**
- Produces: `HandicapResultCard` React component with props
  `{ handicapIndex: number | null; prevIndex: number | null; totalScore: number; differential: number | null; profileTo: string; roundTo: string }`.
  Consumed by Task 4 (GolfReview confirmed state).

- [ ] **Step 1: Write the failing test**

```tsx
// frontend/src/components/golf/__tests__/HandicapResultCard.test.tsx
import React from "react";
import { render, screen } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import HandicapResultCard from "../HandicapResultCard";

const base = {
  handicapIndex: 21.0,
  prevIndex: 21.3,
  totalScore: 93,
  differential: 21.0,
  profileTo: "/golf/profile/u1",
  roundTo: "/golf/round/r1",
};

const renderCard = (props = {}) =>
  render(
    <MemoryRouter>
      <HandicapResultCard {...base} {...props} />
    </MemoryRouter>
  );

describe("HandicapResultCard", () => {
  it("leads with the handicap index as the hero number", () => {
    renderCard();
    expect(screen.getByText("21.0")).toBeInTheDocument();
    expect(screen.getByText(/handicap index/i)).toBeInTheDocument();
  });

  it("shows an improvement delta (down = green ▼)", () => {
    renderCard(); // 21.3 -> 21.0 improved by 0.3
    expect(screen.getByText(/▼\s*0\.3/)).toBeInTheDocument();
  });

  it("shows a worsening delta (up = ▲)", () => {
    renderCard({ handicapIndex: 22.0, prevIndex: 21.3 });
    expect(screen.getByText(/▲\s*0\.7/)).toBeInTheDocument();
  });

  it("shows no delta pill when prevIndex is null or unchanged", () => {
    renderCard({ prevIndex: null });
    expect(screen.queryByText(/[▲▼]/)).toBeNull();
    renderCard({ prevIndex: 21.0 });
    expect(screen.queryByText(/[▲▼]/)).toBeNull();
  });

  it("shows provisional copy when handicapIndex is null", () => {
    renderCard({ handicapIndex: null });
    expect(screen.getByText(/provisional index pending/i)).toBeInTheDocument();
  });

  it("renders score, differential, and both links", () => {
    renderCard();
    expect(screen.getByText("93")).toBeInTheDocument();
    expect(screen.getByText(/leaderboard/i)).toHaveAttribute("href", "/golf/leaderboard");
    expect(screen.getByText(/my rounds/i)).toHaveAttribute("href", "/golf/profile/u1");
  });
});
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd frontend && npx jest src/components/golf/__tests__/HandicapResultCard.test.tsx`
Expected: FAIL — module not found.

- [ ] **Step 3: Implement**

```tsx
// frontend/src/components/golf/HandicapResultCard.tsx
import React from "react";
import { Link } from "react-router-dom";

interface Props {
  handicapIndex: number | null;
  prevIndex: number | null;
  totalScore: number;
  differential: number | null;
  profileTo: string;
  roundTo: string;
}

/**
 * Post-confirm payoff card: leads with the new handicap index and its delta
 * vs. the previous snapshot. Lower is better — a drop renders green (▼),
 * a rise renders in the danger color (▲), matching GolfLeaderboard's pill.
 */
const HandicapResultCard: React.FC<Props> = ({
  handicapIndex,
  prevIndex,
  totalScore,
  differential,
  profileTo,
  roundTo,
}) => {
  const delta =
    handicapIndex !== null && prevIndex !== null
      ? Math.round((handicapIndex - prevIndex) * 10) / 10
      : null;

  return (
    <div>
      <div className="fw-surface p-6 mb-4 text-center">
        <div className="text-xs fw-text-secondary uppercase tracking-wide mb-1">
          Handicap index
        </div>
        {handicapIndex !== null ? (
          <div className="flex items-baseline justify-center gap-3">
            <span className="text-6xl font-semibold text-[var(--fw-text-success)]">
              {handicapIndex.toFixed(1)}
            </span>
            {delta !== null && delta !== 0 && (
              <span
                className={`text-lg font-medium ${
                  delta < 0
                    ? "text-[var(--fw-text-success)]"
                    : "text-[var(--fw-danger)]"
                }`}
              >
                {delta < 0 ? "▼" : "▲"} {Math.abs(delta).toFixed(1)}
              </span>
            )}
          </div>
        ) : (
          <div className="text-sm fw-text-secondary">
            Provisional index pending — confirm another round to establish it.
          </div>
        )}
      </div>

      <div className="grid grid-cols-2 gap-3 mb-6 text-left">
        <div className="fw-surface p-4">
          <div className="text-2xl font-medium">{totalScore}</div>
          <div className="text-xs fw-text-secondary">Total score</div>
        </div>
        <div className="fw-surface p-4">
          <div className="text-2xl font-medium">
            {differential !== null ? differential.toFixed(1) : "N/A"}
          </div>
          <div className="text-xs fw-text-secondary">Differential</div>
        </div>
      </div>

      <div className="flex gap-3 justify-center flex-wrap">
        <Link
          to="/golf/leaderboard"
          className="h-9 px-4 rounded-md bg-[var(--fw-info)] text-white text-sm inline-flex items-center"
        >
          Leaderboard
        </Link>
        <Link
          to={profileTo}
          className="h-9 px-4 rounded-md border-[0.5px] border-[var(--fw-border-secondary)] text-sm inline-flex items-center"
        >
          My rounds
        </Link>
        <Link
          to={roundTo}
          className="h-9 px-4 rounded-md border-[0.5px] border-[var(--fw-border-secondary)] text-sm inline-flex items-center"
        >
          Round details
        </Link>
      </div>
    </div>
  );
};

export default HandicapResultCard;
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd frontend && npx jest src/components/golf/__tests__/HandicapResultCard.test.tsx`
Expected: PASS (6 tests).

- [ ] **Step 5: Commit**

```bash
git add frontend/src/components/golf/HandicapResultCard.tsx frontend/src/components/golf/__tests__/HandicapResultCard.test.tsx
git commit -m "feat(golf): HandicapResultCard — handicap-first post-confirm payoff"
```

---

### Task 4: Wire HandicapResultCard into GolfReview

**Files:**
- Modify: `frontend/src/pages/GolfReview.tsx` (prev-index fetch + confirmed-state render, ~lines 312-365)

**Interfaces:**
- Consumes: `HandicapResultCard` (Task 3), `GET /golf/handicap/<user_id>` (existing endpoint, response `{ handicap_index: number | null, ... }`).

- [ ] **Step 1: Fetch the previous index before confirm**

In `GolfReview.tsx`, add state and fetch it when the round loads (inside the existing round-fetch effect, after `setRound(...)`, using the fetched round's `user_id`):

```tsx
const [prevIndex, setPrevIndex] = useState<number | null>(null);
```

```tsx
// Previous handicap (pre-confirm) so the confirmed screen can show a delta.
// Snapshot history is untouched by this read; failure is non-fatal.
try {
  const uid = data.user_id || localStorage.getItem("userId");
  if (uid) {
    const h = await axios.get(`${API_URL}/golf/handicap/${uid}`);
    setPrevIndex(h.data?.handicap_index ?? null);
  }
} catch {
  setPrevIndex(null);
}
```

(`data` = the round payload variable already in that effect; match the local name in the file.)

- [ ] **Step 2: Replace the confirmed-state body**

In the `if (confirmed && resultData)` block, replace the two stat cards + handicap card + links markup (keep the surrounding Layout/FairwayScope/motion wrapper, the ✓ badge, the "Round saved" heading, and the course/date line) with:

```tsx
<HandicapResultCard
  handicapIndex={resultData.handicap_index}
  prevIndex={prevIndex}
  totalScore={resultData.adjusted_gross_score}
  differential={resultData.differential}
  profileTo={userId ? `/golf/profile/${userId}` : "/golf/profile"}
  roundTo={`/golf/round/${roundId}`}
/>
```

Add the import: `import HandicapResultCard from "../components/golf/HandicapResultCard";`

- [ ] **Step 3: Verify**

Run: `cd frontend && npx jest src/components/golf/__tests__/HandicapResultCard.test.tsx && npx vite build && npx tsc --noEmit`
Expected: tests PASS, build clean, no type errors (checks the JSX wiring compiles).

- [ ] **Step 4: Commit**

```bash
git add frontend/src/pages/GolfReview.tsx
git commit -m "feat(golf): confirmed screen leads with handicap + delta"
```

---

### Task 5: VideoCaptureInput for the plank/challenge upload (TDD)

**Files:**
- Create: `frontend/src/components/challenge/VideoCaptureInput.tsx`
- Test: `frontend/src/components/challenge/__tests__/VideoCaptureInput.test.tsx` (new)
- Modify: `frontend/src/pages/ChallengeDetail.tsx` (video input block ~lines 874-895)

**Interfaces:**
- Produces: `VideoCaptureInput` component, props `{ selectedFileName: string | null; onFileSelect: (e: React.ChangeEvent<HTMLInputElement>) => void }`. Two inputs: `#challenge-video-camera` (`accept="video/*" capture="environment"`) and `#challenge-video-upload` (library, unchanged id so existing behavior/tests keep working).

- [ ] **Step 1: Write the failing test**

```tsx
// frontend/src/components/challenge/__tests__/VideoCaptureInput.test.tsx
import React from "react";
import { render, screen } from "@testing-library/react";
import VideoCaptureInput from "../VideoCaptureInput";

describe("VideoCaptureInput", () => {
  const noop = () => {};

  it("renders a camera input with capture and a library input without", () => {
    render(<VideoCaptureInput selectedFileName={null} onFileSelect={noop} />);
    const camera = document.getElementById("challenge-video-camera");
    const library = document.getElementById("challenge-video-upload");
    expect(camera!.getAttribute("capture")).toBe("environment");
    expect(camera!.getAttribute("accept")).toBe("video/*");
    expect(library!.hasAttribute("capture")).toBe(false);
    expect(library!.getAttribute("accept")).toBe("video/*");
  });

  it("shows both affordances and the selected file name", () => {
    render(<VideoCaptureInput selectedFileName="plank.mp4" onFileSelect={noop} />);
    expect(screen.getByText(/record now/i)).toBeInTheDocument();
    expect(screen.getByText(/choose existing video/i)).toBeInTheDocument();
    expect(screen.getByText("plank.mp4")).toBeInTheDocument();
  });
});
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd frontend && npx jest src/components/challenge/__tests__/VideoCaptureInput.test.tsx`
Expected: FAIL — module not found.

- [ ] **Step 3: Implement the component**

```tsx
// frontend/src/components/challenge/VideoCaptureInput.tsx
import React from "react";
import { Video, FolderOpen } from "lucide-react";

interface Props {
  selectedFileName: string | null;
  onFileSelect: (e: React.ChangeEvent<HTMLInputElement>) => void;
}

/**
 * Two-affordance video picker: "Record now" opens the phone camera directly
 * (capture attr — no external Camera app + file hunt); "Choose existing"
 * keeps the standard picker. Desktop degrades to a file dialog for both.
 */
const VideoCaptureInput: React.FC<Props> = ({ selectedFileName, onFileSelect }) => (
  <div className="border-2 border-dashed border-input rounded-lg p-4 text-center hover:border-primary/50 transition-colors">
    <input
      type="file"
      accept="video/*"
      capture="environment"
      onChange={onFileSelect}
      className="hidden"
      id="challenge-video-camera"
    />
    <input
      type="file"
      accept="video/*"
      onChange={onFileSelect}
      className="hidden"
      id="challenge-video-upload"
    />
    <div className="flex gap-3 justify-center flex-wrap">
      <label
        htmlFor="challenge-video-camera"
        className="cursor-pointer inline-flex items-center gap-2 px-4 py-2 rounded-lg bg-primary text-primary-foreground text-sm"
      >
        <Video className="w-4 h-4" />
        Record now
      </label>
      <label
        htmlFor="challenge-video-upload"
        className="cursor-pointer inline-flex items-center gap-2 px-4 py-2 rounded-lg border border-input text-sm"
      >
        <FolderOpen className="w-4 h-4" />
        Choose existing video
      </label>
    </div>
    {selectedFileName && (
      <p className="text-sm text-muted-foreground mt-3">{selectedFileName}</p>
    )}
  </div>
);

export default VideoCaptureInput;
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd frontend && npx jest src/components/challenge/__tests__/VideoCaptureInput.test.tsx`
Expected: PASS (2 tests).

- [ ] **Step 5: Wire into ChallengeDetail**

In `ChallengeDetail.tsx` (~line 875), replace the existing `<div className="border-2 border-dashed ...">...</div>` video-input block (the one containing `#challenge-video-upload`) with:

```tsx
<VideoCaptureInput
  selectedFileName={selectedFile ? selectedFile.name : null}
  onFileSelect={handleFileSelect}
/>
```

Add the import: `import VideoCaptureInput from "../components/challenge/VideoCaptureInput";`
The `Dumbbell` icon import stays (used elsewhere in the file).

- [ ] **Step 6: Verify**

Run: `cd frontend && npx jest src/components/challenge/__tests__/VideoCaptureInput.test.tsx && npx vite build && npx tsc --noEmit`
Expected: PASS + clean build.

- [ ] **Step 7: Commit**

```bash
git add frontend/src/components/challenge/VideoCaptureInput.tsx frontend/src/components/challenge/__tests__/VideoCaptureInput.test.tsx frontend/src/pages/ChallengeDetail.tsx
git commit -m "feat(challenges): record-now camera input for challenge video upload"
```

---

### Task 6: LiftHub plank-challenge quick link

**Files:**
- Modify: `frontend/src/pages/LiftHub.tsx`
- Test: `frontend/src/pages/__tests__/LiftHub.test.tsx` (new)

**Interfaces:**
- Consumes: `getCompetitions()` from `frontend/src/lib/api.ts` (existing). VERIFIED mapped shape (`transformCompetitionData`, api.ts:77): `{ id, title, status: 'upcoming'|'ongoing'|'completed', categories: string[], ... }` — note `title` (not `name`) and the pre-computed `status`.

- [ ] **Step 1: Write the failing test**

```tsx
// frontend/src/pages/__tests__/LiftHub.test.tsx
import React from "react";
import { render, screen, waitFor } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import LiftHub from "../LiftHub";
import * as api from "../../lib/api";

jest.mock("../../lib/api", () => ({
  ...jest.requireActual("../../lib/api"),
  getCompetitions: jest.fn(),
}));

const plankChallenge = {
  id: "plank-1",
  title: "Summer plank challenge",
  status: "ongoing",
  categories: ["Plank"],
};

describe("LiftHub plank quick link", () => {
  it("links to the ongoing plank challenge when one exists", async () => {
    (api.getCompetitions as jest.Mock).mockResolvedValue([plankChallenge]);
    render(<MemoryRouter><LiftHub /></MemoryRouter>);
    await waitFor(() =>
      expect(screen.getByText(/plank challenge/i)).toBeInTheDocument()
    );
    expect(screen.getByText(/plank challenge/i).closest("a")).toHaveAttribute(
      "href",
      "/challenges/plank-1"
    );
  });

  it("renders no plank link when none is ongoing", async () => {
    (api.getCompetitions as jest.Mock).mockResolvedValue([]);
    render(<MemoryRouter><LiftHub /></MemoryRouter>);
    await waitFor(() => expect(api.getCompetitions).toHaveBeenCalled());
    expect(screen.queryByText(/plank challenge/i)).toBeNull();
  });
});
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd frontend && npx jest src/pages/__tests__/LiftHub.test.tsx`
Expected: FAIL — no plank link rendered (LiftHub is static today).

- [ ] **Step 3: Implement**

Rework `LiftHub.tsx` to fetch and append the quick link (shape mirrors the existing secondary entries):

```tsx
import React, { useEffect, useState } from "react";
import { Dumbbell, Upload, Trophy, Flame, Timer } from "lucide-react";
import HubPage from "../components/HubPage";
import { getCompetitions } from "../lib/api";

const LiftHub: React.FC = () => {
  const localUserId = localStorage.getItem("userId");
  const [plank, setPlank] = useState<{ id: string; title: string } | null>(null);

  useEffect(() => {
    let cancelled = false;
    getCompetitions()
      .then((comps) => {
        if (cancelled) return;
        const p = comps.find(
          (c) => c.status === "ongoing" && (c.categories || []).includes("Plank")
        );
        setPlank(p ? { id: p.id, title: p.title } : null);
      })
      .catch(() => {});
    return () => {
      cancelled = true;
    };
  }, []);

  return (
    <HubPage
      /* title/subtitle/icon/primary unchanged */
      secondary={[
        ...(plank
          ? [
              {
                to: `/challenges/${plank.id}`,
                label: "Plank challenge",
                description: "Record your plank — straight to the board.",
                icon: <Timer className="w-5 h-5" />,
              },
            ]
          : []),
        /* existing Leaderboard, Challenges, My lifts entries unchanged */
      ]}
    />
  );
};
```

(Keep the existing entries verbatim; the plank link goes first so it's the visible quick action.)

- [ ] **Step 4: Run test to verify it passes**

Run: `cd frontend && npx jest src/pages/__tests__/LiftHub.test.tsx`
Expected: PASS (2 tests).

- [ ] **Step 5: Commit**

```bash
git add frontend/src/pages/LiftHub.tsx frontend/src/pages/__tests__/LiftHub.test.tsx
git commit -m "feat(lift): plank-challenge quick link on the Lift hub"
```

---

### Task 7: Full gate + prod verification

**Files:** none new.

- [ ] **Step 1: Full validation gate**

Run: `cd frontend && npx jest && npx vite build && npx tsc --noEmit`
Expected: all suites pass (existing 36+ suites + 4 new), clean build, 0 type errors.

- [ ] **Step 2: Spec-coverage check**

Confirm against `docs/superpowers/specs/2026-07-06-easy-upload-flows-design.md`: A1 (Task 1), A2 (Task 2), A3 (no change — verify no diff touches the review logic), A4 (Tasks 3-4), B1 (Task 6), B2 (Task 5), B3 (pre-verified, no diff), B4 (no change).

- [ ] **Step 3: Deploy + phone verification (project convention)**

Run: `python3 deploy.py --frontend-only --skip-iam`
Then on a phone (or Playwright mobile viewport for the non-camera parts): `/golf/snap` opens camera or one-tap button; scorecard confirm screen leads with handicap + delta; plank challenge page shows "Record now"; LiftHub shows the plank quick link. Ask the user to confirm the camera behavior on a real device — emulators can't fully verify `capture`.

- [ ] **Step 4: Commit any fixups**

```bash
git add -A && git commit -m "fix(upload-flows): post-verification fixups"
```
