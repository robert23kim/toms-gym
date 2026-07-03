# Frontend Consolidation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make the SPA resilient and coherent: a top-level ErrorBoundary, lazy-loaded routes, one API base URL, react-query as the data-fetching pattern (with one exemplary page converted), a shared media-upload hook replacing copy-pasted upload state, and repo hygiene (screenshots, tracked mp4, uncommitted Android wrapper).

**Architecture:** All work is in `/Users/toka/code/toms_gym/frontend` (React 18 + TypeScript + Vite + Tailwind/shadcn, Jest + RTL) except the final hygiene task, which touches the repo root. react-query's `QueryClientProvider` already wraps the app (`App.tsx:35`) — we start actually using it via a thin `src/lib/queries.ts` hooks module. Upload state (file select / drag-drop / preview / validation) is extracted into `src/hooks/useMediaUpload.ts` and adopted by GolfUpload and BowlingUpload.

**Tech Stack:** React 18, TypeScript, Vite, @tanstack/react-query (already installed), Jest + ts-jest + React Testing Library.

## Global Constraints

- **Prerequisite:** commit/land the currently-uncommitted work on branch `plank/poller-timeouts` first (GolfProfile/GolfReview/GolfRound and `.env.production` are dirty). Each task assumes a clean tree.
- Working dir for all commands unless noted: `/Users/toka/code/toms_gym/frontend`.
- Validation trio before any task is "done": `npx tsc --noEmit` (typecheck), `npm test -- <changed test files>` (Jest), `npm run build` (Vite). Run the full `npm test` suite in each task's final verify step.
- No `any`, `as any`, or `{} as Type` in new/changed code. New code uses proper types from `src/lib/types.ts`.
- Do not change any user-visible copy, class names, or `data-testid` attributes except where a task explicitly says so (Playwright e2e specs in `e2e/` select on them).
- Conventional commits: `feat(scope):`, `fix(scope):`, `refactor(scope):`, `chore(scope):`, `test(scope):`.
- Deploy at the end of the whole plan (not per task): `cd /Users/toka/code/toms_gym && python3 deploy.py --frontend-only --skip-iam`, then smoke-check https://my-frontend-quyiiugyoq-ue.a.run.app.

---

### Task 1: Top-level ErrorBoundary

Any render throw currently white-screens the whole SPA (no boundary exists anywhere in `src/`).

**Files:**
- Create: `src/components/ErrorBoundary.tsx`
- Create: `src/components/__tests__/ErrorBoundary.test.tsx`
- Modify: `src/App.tsx` (wrap the tree)

**Interfaces:**
- Produces: `default export class ErrorBoundary extends React.Component<{children: React.ReactNode}, {error: Error | null}>`. Task 2 nests `Suspense` inside it.

- [x] **Step 1: Write the failing test**

```tsx
// src/components/__tests__/ErrorBoundary.test.tsx
import { render, screen } from "@testing-library/react";
import ErrorBoundary from "../ErrorBoundary";

const Boom = () => {
  throw new Error("kaboom");
};

describe("ErrorBoundary", () => {
  it("renders the fallback when a child throws", () => {
    const spy = jest.spyOn(console, "error").mockImplementation(() => {});
    render(
      <ErrorBoundary>
        <Boom />
      </ErrorBoundary>
    );
    expect(screen.getByText("Something went wrong")).toBeInTheDocument();
    expect(screen.getByText("kaboom")).toBeInTheDocument();
    spy.mockRestore();
  });

  it("renders children when nothing throws", () => {
    render(
      <ErrorBoundary>
        <div>all good</div>
      </ErrorBoundary>
    );
    expect(screen.getByText("all good")).toBeInTheDocument();
  });
});
```

- [x] **Step 2: Run test to verify it fails**

Run: `npm test -- src/components/__tests__/ErrorBoundary.test.tsx`
Expected: FAIL — `Cannot find module '../ErrorBoundary'`

- [x] **Step 3: Implement the component**

```tsx
// src/components/ErrorBoundary.tsx
import React from "react";

interface ErrorBoundaryProps {
  children: React.ReactNode;
}

interface ErrorBoundaryState {
  error: Error | null;
}

// Class component: React only exposes render-error catching via
// componentDidCatch/getDerivedStateFromError.
export default class ErrorBoundary extends React.Component<
  ErrorBoundaryProps,
  ErrorBoundaryState
> {
  state: ErrorBoundaryState = { error: null };

  static getDerivedStateFromError(error: Error): ErrorBoundaryState {
    return { error };
  }

  componentDidCatch(error: Error, info: React.ErrorInfo) {
    console.error("Unhandled render error:", error, info.componentStack);
  }

  render() {
    if (this.state.error) {
      return (
        <div className="min-h-screen flex flex-col items-center justify-center gap-4 p-8 text-center">
          <h1 className="text-2xl font-semibold">Something went wrong</h1>
          <p className="text-muted-foreground">{this.state.error.message}</p>
          <button
            className="px-4 py-2 rounded-md bg-primary text-primary-foreground"
            onClick={() => {
              this.setState({ error: null });
              window.location.assign("/");
            }}
          >
            Back to home
          </button>
        </div>
      );
    }
    return this.props.children;
  }
}
```

- [x] **Step 4: Run test to verify it passes**

Run: `npm test -- src/components/__tests__/ErrorBoundary.test.tsx`
Expected: 2 PASSED

- [x] **Step 5: Wire into App.tsx**

In `src/App.tsx`, add `import ErrorBoundary from "./components/ErrorBoundary";` and wrap everything inside `QueryClientProvider`:

```tsx
const App = () => {
  return (
    <QueryClientProvider client={queryClient}>
      <ErrorBoundary>
        <BrowserRouter>
          <AuthProvider>
            <TitleUpdater />
            <TooltipProvider>
              <Routes>
                {routes.map((route, index) => (
                  <Route key={index} path={route.path} element={route.element} />
                ))}
              </Routes>
              <Toaster />
              <Sonner />
            </TooltipProvider>
          </AuthProvider>
        </BrowserRouter>
      </ErrorBoundary>
    </QueryClientProvider>
  );
};
```

- [x] **Step 6: Validate and commit**

Run: `npx tsc --noEmit && npm test && npm run build`
Expected: all green.

```bash
git add src/components/ErrorBoundary.tsx src/components/__tests__/ErrorBoundary.test.tsx src/App.tsx
git commit -m "feat(frontend): top-level ErrorBoundary so render throws don't white-screen"
```

---

### Task 2: Lazy-load all routes

All ~27 page components are eagerly imported in `src/routes/index.tsx`, so the initial bundle carries every feature.

**Files:**
- Modify: `src/routes/index.tsx` (full rewrite below)
- Modify: `src/App.tsx` (Suspense around `<Routes>`)

**Interfaces:**
- Consumes: `ErrorBoundary` from Task 1 (already wired outside — Suspense goes inside it).
- Produces: same `routes: RouteObject[]` export; same paths; page components become `React.lazy`.

- [x] **Step 1: Rewrite `src/routes/index.tsx`**

Replace the entire file with (route paths are IDENTICAL to the current file — only the import mechanism changes; `ShortLinkRedirect` and the inline `VideoPlayerRedirect` stay eager because redirects should not flash a spinner):

```tsx
import { lazy } from "react";
import { RouteObject } from "react-router-dom";
import { Navigate, useParams } from "react-router-dom";
import ShortLinkRedirect from "../pages/ShortLinkRedirect";

const Index = lazy(() => import("../pages/Index"));
const Challenges = lazy(() => import("../pages/Challenges"));
const Athletes = lazy(() => import("../pages/Athletes"));
const About = lazy(() => import("../pages/About"));
const ChallengeDetail = lazy(() => import("../pages/ChallengeDetail"));
const ChallengeVideos = lazy(() => import("../pages/ChallengeVideos"));
const VideoPlayer = lazy(() => import("../pages/VideoPlayer"));
const UploadVideo = lazy(() => import("../pages/UploadVideo"));
const NotFound = lazy(() => import("../pages/NotFound"));
const Leaderboard = lazy(() => import("../pages/Leaderboard"));
const Store = lazy(() => import("../pages/Store"));
const Profile = lazy(() => import("../pages/Profile"));
const WeeklyLifts = lazy(() => import("../pages/WeeklyLifts"));
const AuthCallback = lazy(() => import("../pages/AuthCallback"));
const AuthError = lazy(() => import("../pages/AuthError"));
const BowlingUpload = lazy(() => import("../pages/BowlingUpload"));
const BowlingResult = lazy(() => import("../pages/BowlingResult"));
const BowlingChallenge = lazy(() => import("../pages/BowlingChallenge"));
const AnnotationWorkspace = lazy(() => import("../pages/AnnotationWorkspace"));
const GolfUpload = lazy(() => import("../pages/GolfUpload"));
const GolfReview = lazy(() => import("../pages/GolfReview"));
const GolfRound = lazy(() => import("../pages/GolfRound"));
const GolfProfile = lazy(() => import("../pages/GolfProfile"));
const GolfLeaderboard = lazy(() => import("../pages/GolfLeaderboard"));

// Redirect component for backward compatibility
const VideoPlayerRedirect = () => {
  const { id, participantId, videoId } = useParams();
  return <Navigate to={`/challenges/${id}/participants/${participantId}/video/${videoId}`} replace />;
};

export const routes: RouteObject[] = [
  { path: "/", element: <Index /> },
  { path: "/challenges", element: <Challenges /> },
  { path: "/challenges/:id", element: <ChallengeDetail /> },
  { path: "/challenges/:id/videos", element: <ChallengeVideos /> },
  { path: "/challenges/:id/upload", element: <UploadVideo /> },
  { path: "/upload", element: <UploadVideo /> },
  {
    path: "/challenges/:id/participants/:participantId/video/:videoId",
    element: <VideoPlayer />,
  },
  { path: "/video-player/:id/:participantId/:videoId", element: <VideoPlayerRedirect /> },
  { path: "/s/:code", element: <ShortLinkRedirect /> },
  { path: "/athletes", element: <Athletes /> },
  { path: "/about", element: <About /> },
  { path: "/leaderboard", element: <Leaderboard /> },
  { path: "/store", element: <Store /> },
  { path: "/profile", element: <Profile /> },
  { path: "/profile/:id", element: <Profile /> },
  { path: "/profile/:id/weekly-lifts", element: <WeeklyLifts /> },
  { path: "/auth/callback", element: <AuthCallback /> },
  { path: "/auth/error", element: <AuthError /> },
  { path: "/bowling/upload", element: <BowlingUpload /> },
  { path: "/bowling/upload/:competitionId", element: <BowlingUpload /> },
  { path: "/bowling/result/:attemptId", element: <BowlingResult /> },
  { path: "/bowling/result/:attemptId/annotate", element: <AnnotationWorkspace /> },
  { path: "/bowling/challenge/:id", element: <BowlingChallenge /> },
  { path: "/golf/upload", element: <GolfUpload /> },
  { path: "/golf/review/:roundId", element: <GolfReview /> },
  { path: "/golf/round/:roundId", element: <GolfRound /> },
  { path: "/golf/profile", element: <GolfProfile /> },
  { path: "/golf/profile/:userId", element: <GolfProfile /> },
  { path: "/golf/leaderboard", element: <GolfLeaderboard /> },
  { path: "*", element: <NotFound /> },
];
```

Note: this requires every page to have a `default export` — all current pages do (they're imported as default today).

- [x] **Step 2: Add Suspense in App.tsx**

Add `Suspense` to the react import in `src/App.tsx` (`import { useEffect, Suspense } from "react";`) and wrap the `<Routes>` block:

```tsx
            <Suspense
              fallback={
                <div className="min-h-screen flex items-center justify-center">
                  <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-primary" />
                </div>
              }
            >
              <Routes>
                {routes.map((route, index) => (
                  <Route key={index} path={route.path} element={route.element} />
                ))}
              </Routes>
            </Suspense>
```

- [x] **Step 3: Verify chunk splitting**

Run: `npx tsc --noEmit && npm test && npm run build`
Expected: all green, and the build output lists many small `dist/assets/*.js` chunks (one per page) instead of one large bundle. Note the main chunk size before/after in the commit message body.

- [x] **Step 4: Manual smoke**

Run: `npm run dev` and load `/`, `/golf/leaderboard`, `/upload` — each renders (spinner may flash on first navigation).

- [x] **Step 5: Commit**

```bash
git add src/routes/index.tsx src/App.tsx
git commit -m "feat(frontend): lazy-load route components to split the bundle"
```

---

### Task 3: Clean up `config.ts` (kill the UA override and prod console noise)

`src/config.ts` force-routes "mobile or Linux" user agents to the hardcoded prod URL regardless of `VITE_API_URL`, and logs ~8 lines (including the full user agent) on every page load in production.

**Files:**
- Modify: `src/config.ts` (full rewrite below)
- Verify: `frontend/.env.production` contains `VITE_API_URL`

- [x] **Step 1: Check for test/code dependencies**

Run: `grep -rn "isMobileDevice\|shouldUseProductionUrl\|isLinux" src/ e2e/ --include="*.ts" --include="*.tsx"`
Expected: hits only inside `src/config.ts`. If anything else consumes these exports, stop and report — do not delete used exports.

- [x] **Step 2: Rewrite `src/config.ts`**

```ts
/// <reference types="vite/client" />

// Hardcoded production URL as the fallback when VITE_API_URL is unset
// (e.g. a local build without env). Deploys set VITE_API_URL explicitly.
const PRODUCTION_API_URL = "https://my-python-backend-quyiiugyoq-ue.a.run.app";

export const API_URL = import.meta.env.VITE_API_URL || PRODUCTION_API_URL;
export const PROD_API_URL = PRODUCTION_API_URL;
export const COMPETITIONS_API_URL = API_URL;

// App build/version stamp — set at deploy time by deploy.py via
// VITE_BUILD_TIMESTAMP (unix seconds). Surfaced in the footer so you can
// confirm at a glance which frontend build is actually live.
const buildTimestamp = Number(import.meta.env.VITE_BUILD_TIMESTAMP) || 0;
export const APP_VERSION = buildTimestamp
  ? `${new Date(buildTimestamp * 1000).toISOString().slice(0, 16).replace("T", " ")} UTC`
  : "dev";
export const APP_BUILD = buildTimestamp;
```

- [x] **Step 3: Confirm production env sets the URL**

Run: `grep VITE_API_URL .env.production`
Expected: `VITE_API_URL=https://my-python-backend-quyiiugyoq-ue.a.run.app` (or equivalent). If missing, add that line — with the UA override gone, this is what keeps production builds pointed at the backend.

Behavior note for the commit body: the old UA sniffing existed to force mobile devices onto prod; since production builds get `VITE_API_URL` at build time, the override only ever mattered for `npm run dev` on a phone — if that workflow comes back, use `VITE_API_URL=... npm run dev`, not UA sniffing.

- [x] **Step 4: Validate and commit**

Run: `npx tsc --noEmit && npm test && npm run build`
Expected: green. Then load `npm run dev` and confirm the console shows zero config logs.

```bash
git add src/config.ts .env.production
git commit -m "fix(frontend): single API_URL source; drop UA sniffing and prod console logging"
```

---

### Task 4: Delete the dead axios instance and stale base URL

`src/lib/api.ts:19` hardcodes `API_BASE_URL = "https://my-app-834341357827.us-east1.run.app"` — a dead service URL — and exports an `api` axios instance plus an `endpoints` map with **zero** consumers outside the file.

**Files:**
- Modify: `src/lib/api.ts` (remove lines 19 and 76–99: `API_BASE_URL`, `export const api = axios.create(...)`, `export const endpoints = {...}`)
- Check: `src/lib/__tests__/` for tests referencing the removed exports

- [x] **Step 1: Re-verify the exports are unused**

Run: `grep -rn "endpoints\b" src --include="*.tsx" --include="*.ts" | grep -v "lib/api.ts"` and `grep -rn "import { api" src --include="*.tsx" --include="*.ts"` and `grep -rn "API_BASE_URL" src`
Expected: no hits outside `src/lib/api.ts` (and possibly `src/lib/__tests__/api.test.ts` — note any test hits for Step 3).

- [x] **Step 2: Delete**

In `src/lib/api.ts` remove:
- Line 19: `const API_BASE_URL = "https://my-app-834341357827.us-east1.run.app";`
- The `export const api = axios.create({...});` block (lines 76–81)
- The `export const endpoints = { challenges: {...}, participants: {...}, videos: {...} } as const;` block (lines 83–99)

Keep the top-level `import axios from "axios";` — the rest of the file still uses axios for its exported functions.

- [x] **Step 3: Fix any tests that asserted on the removed exports**

If Step 1 found hits in `src/lib/__tests__/`, delete only those test cases (they test dead code), keeping the rest of the file intact.

- [x] **Step 4: Validate and commit**

Run: `npx tsc --noEmit && npm test && npm run build`
Expected: green.

```bash
git add src/lib/api.ts src/lib/__tests__/
git commit -m "chore(frontend): remove dead axios instance and stale my-app base URL"
```

---

### Task 5: Adopt react-query — `queries.ts` + GolfLeaderboard conversion

react-query is installed and `QueryClientProvider` wraps the app, but there are zero `useQuery` calls. Establish the pattern with a hooks module and convert `GolfLeaderboard` (small, read-only, representative).

**Files:**
- Create: `src/lib/queries.ts`
- Create: `src/lib/__tests__/queries.test.tsx`
- Modify: `src/pages/GolfLeaderboard.tsx` (lines 1–54: imports, state, effect, loading block)

**Interfaces:**
- Consumes: `API_URL` from `src/config.ts`; `GolfLeaderboardEntry` from `src/lib/types.ts`.
- Produces: `useGolfLeaderboard(limit?: number)` returning `UseQueryResult<GolfLeaderboardEntry[]>`, and `apiErrorMessage(error: unknown, fallback: string): string`. Future page conversions follow this module's pattern.

- [x] **Step 1: Write the failing test**

```tsx
// src/lib/__tests__/queries.test.tsx
import { renderHook, waitFor } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import React from "react";
import axios from "axios";
import { useGolfLeaderboard, apiErrorMessage } from "../queries";

jest.mock("axios", () => {
  const actual = jest.requireActual("axios");
  return { ...actual, get: jest.fn(), isAxiosError: actual.isAxiosError };
});

const wrapper = ({ children }: { children: React.ReactNode }) => (
  <QueryClientProvider
    client={new QueryClient({ defaultOptions: { queries: { retry: false } } })}
  >
    {children}
  </QueryClientProvider>
);

describe("useGolfLeaderboard", () => {
  it("returns leaderboard entries", async () => {
    (axios.get as jest.Mock).mockResolvedValue({
      data: {
        leaderboard: [
          {
            user_id: "u1",
            user_name: "Tom",
            rank: 1,
            handicap_index: 12.3,
            rounds_played: 4,
            best_differential: 10.1,
          },
        ],
      },
    });
    const { result } = renderHook(() => useGolfLeaderboard(), { wrapper });
    await waitFor(() => expect(result.current.isSuccess).toBe(true));
    expect(result.current.data).toHaveLength(1);
    expect(result.current.data?.[0].user_name).toBe("Tom");
    expect((axios.get as jest.Mock).mock.calls[0][0]).toContain(
      "/golf/leaderboard?limit=50"
    );
  });

  it("surfaces request errors", async () => {
    (axios.get as jest.Mock).mockRejectedValue(new Error("network down"));
    const { result } = renderHook(() => useGolfLeaderboard(), { wrapper });
    await waitFor(() => expect(result.current.isError).toBe(true));
  });
});

describe("apiErrorMessage", () => {
  it("unwraps Error messages", () => {
    expect(apiErrorMessage(new Error("boom"), "fallback")).toBe("boom");
  });

  it("falls back for unknown values", () => {
    expect(apiErrorMessage("weird", "fallback")).toBe("fallback");
  });
});
```

- [x] **Step 2: Run test to verify it fails**

Run: `npm test -- src/lib/__tests__/queries.test.tsx`
Expected: FAIL — `Cannot find module '../queries'`

- [x] **Step 3: Implement `src/lib/queries.ts`**

```ts
// react-query hooks for server data. New pages should fetch through hooks in
// this module instead of ad-hoc axios calls inside useEffect.
import { useQuery } from "@tanstack/react-query";
import axios from "axios";
import { API_URL } from "../config";
import { GolfLeaderboardEntry } from "./types";

export function apiErrorMessage(error: unknown, fallback: string): string {
  if (axios.isAxiosError(error)) {
    const body = error.response?.data as { error?: string } | undefined;
    return body?.error ?? error.message;
  }
  return error instanceof Error ? error.message : fallback;
}

export function useGolfLeaderboard(limit = 50) {
  return useQuery({
    queryKey: ["golf", "leaderboard", limit],
    queryFn: async (): Promise<GolfLeaderboardEntry[]> => {
      const res = await axios.get(`${API_URL}/golf/leaderboard?limit=${limit}`);
      return res.data.leaderboard ?? [];
    },
    staleTime: 30_000,
  });
}
```

- [x] **Step 4: Run test to verify it passes**

Run: `npm test -- src/lib/__tests__/queries.test.tsx`
Expected: 4 PASSED

- [x] **Step 5: Convert GolfLeaderboard**

In `src/pages/GolfLeaderboard.tsx`:

1. Replace the imports of `useState`/`useEffect`/`axios` usage — new import block at the top:

```tsx
import React from "react";
import { Link } from "react-router-dom";
import { motion } from "framer-motion";
import { Trophy, Upload } from "lucide-react";
import Layout from "../components/Layout";
import FairwayScope from "../components/FairwayScope";
import { getGolfAvatar } from "../lib/api";
import { apiErrorMessage, useGolfLeaderboard } from "../lib/queries";
```

2. Replace the state + effect block (current lines 13–38) with:

```tsx
const GolfLeaderboard: React.FC = () => {
  const { data: entries = [], isLoading, error } = useGolfLeaderboard();
```

3. In the loading guard, change `if (loading) {` to `if (isLoading) {` (JSX unchanged).

4. In the error banner, replace `{error}` with:

```tsx
                {apiErrorMessage(error, "Failed to load leaderboard")}
```

and change the condition from `{error && (` to `{error != null && (`.

Everything else in the file (all JSX, `data-testid="leaderboard-list"`, styling) stays byte-identical.

- [x] **Step 6: Validate and commit**

Run: `npx tsc --noEmit && npm test && npm run build`
Expected: green (existing golf component tests unaffected).

```bash
git add src/lib/queries.ts src/lib/__tests__/queries.test.tsx src/pages/GolfLeaderboard.tsx
git commit -m "feat(frontend): adopt react-query via lib/queries; convert GolfLeaderboard"
```

Follow-up (out of scope, note in report): convert `GolfProfile`, `Leaderboard`, and `Challenges` to hooks in this module using the same pattern.

---

### Task 6: Shared `useMediaUpload` hook + GolfUpload adoption

GolfUpload, BowlingUpload, and UploadVideo each hand-roll identical file-select / drag-drop / preview / size-validation state (~50 lines each).

**Files:**
- Create: `src/hooks/useMediaUpload.ts`
- Create: `src/hooks/__tests__/useMediaUpload.test.ts`
- Modify: `src/pages/GolfUpload.tsx` (lines 12–65: state + four handlers)

**Interfaces:**
- Produces:

```ts
useMediaUpload({ accept: "image" | "video", maxBytes: number }): {
  file: File | null;
  previewUrl: string | null;
  isDragging: boolean;
  error: string | null;
  setError: (e: string | null) => void;
  onInputChange: (e: ChangeEvent<HTMLInputElement>) => void;
  onDrop: (e: DragEvent) => void;
  onDragOver: (e: DragEvent) => void;
  onDragLeave: () => void;
}
```

Task 7 consumes the same hook for BowlingUpload.

- [x] **Step 1: Write the failing test**

```ts
// src/hooks/__tests__/useMediaUpload.test.ts
import { renderHook, act } from "@testing-library/react";
import type { ChangeEvent } from "react";
import { useMediaUpload } from "../useMediaUpload";

beforeAll(() => {
  global.URL.createObjectURL = jest.fn(() => "blob:preview");
  global.URL.revokeObjectURL = jest.fn();
});

function changeEventWith(file: File) {
  return { target: { files: [file] } } as unknown as ChangeEvent<HTMLInputElement>;
}

describe("useMediaUpload", () => {
  it("accepts a valid file and builds a preview", () => {
    const { result } = renderHook(() =>
      useMediaUpload({ accept: "image", maxBytes: 1024 })
    );
    const file = new File(["x"], "card.jpg", { type: "image/jpeg" });
    act(() => result.current.onInputChange(changeEventWith(file)));
    expect(result.current.file).toBe(file);
    expect(result.current.previewUrl).toBe("blob:preview");
    expect(result.current.error).toBeNull();
  });

  it("rejects the wrong media type", () => {
    const { result } = renderHook(() =>
      useMediaUpload({ accept: "image", maxBytes: 1024 })
    );
    const file = new File(["x"], "clip.mp4", { type: "video/mp4" });
    act(() => result.current.onInputChange(changeEventWith(file)));
    expect(result.current.file).toBeNull();
    expect(result.current.error).toBe("Please choose an image file");
  });

  it("rejects oversized files with a MB message", () => {
    const { result } = renderHook(() =>
      useMediaUpload({ accept: "image", maxBytes: 20 * 1024 * 1024 })
    );
    const big = new File([new ArrayBuffer(21 * 1024 * 1024)], "big.jpg", {
      type: "image/jpeg",
    });
    act(() => result.current.onInputChange(changeEventWith(big)));
    expect(result.current.file).toBeNull();
    expect(result.current.error).toBe("Image must be under 20MB");
  });
});
```

- [x] **Step 2: Run test to verify it fails**

Run: `npm test -- src/hooks/__tests__/useMediaUpload.test.ts`
Expected: FAIL — `Cannot find module '../useMediaUpload'`

- [x] **Step 3: Implement the hook**

```ts
// src/hooks/useMediaUpload.ts
// Shared file-selection state for the upload pages (golf scorecards, bowling
// and lifting videos): input + drag-drop handlers, type/size validation, and
// object-URL preview lifecycle.
import { useState } from "react";
import type { ChangeEvent, DragEvent } from "react";

interface UseMediaUploadOptions {
  accept: "image" | "video";
  maxBytes: number;
}

export function useMediaUpload({ accept, maxBytes }: UseMediaUploadOptions) {
  const [file, setFile] = useState<File | null>(null);
  const [previewUrl, setPreviewUrl] = useState<string | null>(null);
  const [isDragging, setIsDragging] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const label = accept === "image" ? "Image" : "Video";

  const takeFile = (candidate: File | null | undefined) => {
    if (!candidate) return;
    if (!candidate.type.startsWith(`${accept}/`)) {
      setError(`Please choose ${accept === "image" ? "an image" : "a video"} file`);
      return;
    }
    if (candidate.size > maxBytes) {
      setError(`${label} must be under ${Math.round(maxBytes / (1024 * 1024))}MB`);
      return;
    }
    setFile(candidate);
    setPreviewUrl((old) => {
      if (old) URL.revokeObjectURL(old);
      return URL.createObjectURL(candidate);
    });
    setError(null);
  };

  const onInputChange = (e: ChangeEvent<HTMLInputElement>) => takeFile(e.target.files?.[0]);

  const onDrop = (e: DragEvent) => {
    e.preventDefault();
    setIsDragging(false);
    takeFile(e.dataTransfer.files?.[0]);
  };

  const onDragOver = (e: DragEvent) => {
    e.preventDefault();
    setIsDragging(true);
  };

  const onDragLeave = () => setIsDragging(false);

  return {
    file,
    previewUrl,
    isDragging,
    error,
    setError,
    onInputChange,
    onDrop,
    onDragOver,
    onDragLeave,
  };
}
```

- [x] **Step 4: Run test to verify it passes**

Run: `npm test -- src/hooks/__tests__/useMediaUpload.test.ts`
Expected: 3 PASSED

- [x] **Step 5: Adopt in GolfUpload**

In `src/pages/GolfUpload.tsx`:

1. Add `import { useMediaUpload } from "../hooks/useMediaUpload";`.
2. Delete the four state hooks `selectedFile`, `previewUrl`, `error`, `isDragging` (keep `email`, `courseName`, `slopeRating`, `courseRating`, `playedAt`, `isUploading`) and delete the `handleFileSelect`, `handleDrop`, `handleDragOver`, `handleDragLeave` functions (lines 26–65). Replace with:

```tsx
  const {
    file: selectedFile,
    previewUrl,
    isDragging,
    error,
    setError,
    onInputChange: handleFileSelect,
    onDrop: handleDrop,
    onDragOver: handleDragOver,
    onDragLeave: handleDragLeave,
  } = useMediaUpload({ accept: "image", maxBytes: 20 * 1024 * 1024 });
```

Aliasing to the old names means the JSX below (input `onChange={handleFileSelect}`, the drop-zone handlers, `error` banner, `previewUrl` img, `selectedFile` checks) needs **zero** changes. `handleSubmit` keeps using `setError` exactly as before.

Behavior note: the drop-path error message changes from "Please drop an image file" to "Please choose an image file" — acceptable copy unification; confirm no e2e spec asserts the old string (`grep -rn "Please drop" e2e/ src/`).

- [x] **Step 6: Validate and commit**

Run: `npx tsc --noEmit && npm test && npm run build`, then `npm run dev` → `/golf/upload`: select a file (preview appears), drag-drop a file, try a >20MB file (error shows).

```bash
git add src/hooks/useMediaUpload.ts src/hooks/__tests__/useMediaUpload.test.ts src/pages/GolfUpload.tsx
git commit -m "refactor(frontend): shared useMediaUpload hook; adopt in GolfUpload"
```

---

### Task 7: Adopt `useMediaUpload` in BowlingUpload

**Files:**
- Modify: `src/pages/BowlingUpload.tsx`

**Interfaces:**
- Consumes: `useMediaUpload` from Task 6 with `{ accept: "video", maxBytes: <the page's current limit> }`.

- [x] **Step 1: Map the page's current upload state**

Run: `grep -n "useState\|const handle\|size >" src/pages/BowlingUpload.tsx`
Expected: the same quartet as GolfUpload (file/preview/error/isDragging state + select/drop/dragover/dragleave handlers) plus a size check. Note the exact max-size constant the page uses (if it has none, use `500 * 1024 * 1024` and say so in the commit body).

- [x] **Step 2: Replace state + handlers with the hook**

Apply the same mechanical replacement as Task 6 Step 5: delete the four state hooks and four handlers, insert

```tsx
  const {
    file: selectedFile,
    previewUrl,
    isDragging,
    error,
    setError,
    onInputChange: handleFileSelect,
    onDrop: handleDrop,
    onDragOver: handleDragOver,
    onDragLeave: handleDragLeave,
  } = useMediaUpload({ accept: "video", maxBytes: /* value from Step 1 */ });
```

aliasing to whatever names this page's JSX actually uses (adjust the aliases to match — do not rename anything in the JSX). Keep the page's submit function and its `setError` calls unchanged.

- [x] **Step 3: Validate and commit**

Run: `npx tsc --noEmit && npm test && npm run build`, then `npm run dev` → `/bowling/upload`: file select + drop + oversize rejection all behave.

```bash
git add src/pages/BowlingUpload.tsx
git commit -m "refactor(frontend): BowlingUpload uses shared useMediaUpload hook"
```

Follow-up (out of scope, note in report): `UploadVideo.tsx` should adopt the same hook, but its flow is entangled with WebCodecs compression + signed-URL upload (`lib/resumableUpload.ts`) — convert it in its own change after this pattern has soaked.

---

### Task 8: Repo hygiene — screenshots, tracked mp4, Android wrapper

Working dir: `/Users/toka/code/toms_gym` (repo root).

**Decision baked into this task:** `frontend/android/` (an uncommitted Capacitor Android wrapper with no `capacitor.config.*` checked in and no CI wiring) is treated as a local experiment → gitignored, kept on disk. If Tom wants Android as a real target, revert the `.gitignore` line and commit it with a config instead.

**Files:**
- Modify: `.gitignore` (repo root)
- Delete: ~23 stray screenshots + `golf_scorecard.jpg` at repo root
- Untrack: `output_deadlift.mp4` (tracked, 14MB)

- [ ] **Step 1: Confirm the strays are not referenced**

Run: `grep -rln "golf_scorecard.jpg\|output_deadlift.mp4\|leaderboard-final.png" backend/ frontend/ docs/ --include="*.py" --include="*.ts" --include="*.tsx" --include="*.md" | grep -v node_modules`
Expected: no hits (they're one-off verification artifacts). If a doc references one, move that file into `docs/images/` instead of deleting it and note it.

- [ ] **Step 2: Extend `.gitignore`**

Append to the repo-root `.gitignore`:

```
# One-off verification screenshots and local artifacts
/*.png
/*.jpg
/*.mp4
.playwright-mcp/

# Local Capacitor experiment — commit deliberately if Android becomes a real target
frontend/android/
```

- [ ] **Step 3: Delete strays and untrack the video**

```bash
cd /Users/toka/code/toms_gym
rm -f *.png golf_scorecard.jpg
git rm --cached output_deadlift.mp4
```

Then confirm: `git status --short` no longer lists any root `*.png`, `golf_scorecard.jpg`, `.playwright-mcp/`, or `frontend/android/`; `git ls-files | grep -c "\.mp4$"` counts only the intentional test fixtures under `backend/tests/` (leave those — the backend suite loads them).

- [ ] **Step 4: Verify nothing broke**

Run: `cd frontend && npm test && npm run build` and `cd ../backend && venv/bin/python tools/run_golf_parser_tests.py`
Expected: green — the deleted files were never inputs to code or tests.

- [ ] **Step 5: Commit**

```bash
cd /Users/toka/code/toms_gym
git add .gitignore
git commit -m "chore(repo): gitignore local artifacts; drop stray screenshots and tracked mp4"
```

---

## Final deploy + smoke (after all tasks)

- [ ] `cd /Users/toka/code/toms_gym && python3 deploy.py --frontend-only --skip-iam`
- [ ] Load https://my-frontend-quyiiugyoq-ue.a.run.app — home, `/golf/leaderboard`, `/golf/upload`, `/bowling/upload`, `/upload` all render; browser console is free of the old config.ts log spam; network tab shows per-page JS chunks.
