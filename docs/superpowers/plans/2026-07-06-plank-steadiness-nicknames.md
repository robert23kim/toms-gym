# Plank Steadiness Nicknames Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Show funny steadiness-based nicknames on the plank challenge (leaderboard rows, podium chips, attempt history), blending steadiness with attempt count and upload cadence.

**Architecture:** Two pure frontend helpers in `lib/plankStats.ts` — `steadinessNickname(stdev)` (per-attempt base name) and `athleteNickname({stdevDeg, attemptCount, uploadDates})` (base + behavior modifier). One new backend field (`body_line_stdev_deg`) surfaced through the leaderboard and lift-history queries; attempt count + upload dates are already on the leaderboard row. Video-page `personality()` is untouched.

**Tech Stack:** TypeScript/React (Vite, Jest + RTL), Python/Flask (SQLAlchemy raw SQL, pytest).

## Global Constraints

- Nickname vocabulary (exact strings + emoji): `🗿 Statue`, `💪 Steady Eddie`, `🌊 The Wobbler`, `🪼 Human Jellyfish`. Modifiers: `One-Shot`, `Relentless`, `The Elusive`.
- Steadiness band boundaries come from existing `steadinessScore()`: ≥85 Rock Solid, ≥70 Steady, ≥50 Wobbly, else Jelly Mode.
- Missing/NaN steadiness → helper returns `null` → no badge renders (no layout shift, no "—").
- Nicknames render on **time-metric (plank)** challenges only; weight boards render nothing.
- Backend adds exactly one new field: `body_line_stdev_deg` as `steadiness`. No new endpoints. No `per_second` on list rows.
- Video-page `personality()` and `steadinessScore()` are unchanged.
- Follow existing patterns: raw SQL `lr.report->>'...'` extraction, `_to_float` null-safety, `rounded-full border border-white/10 bg-white/5` chip styling.

---

### Task 1: `steadinessNickname` helper (per-attempt base)

**Files:**
- Modify: `frontend/src/lib/plankStats.ts`
- Test: `frontend/src/lib/__tests__/plankStats.test.ts`

**Interfaces:**
- Consumes: existing `steadinessScore(stdevDeg?: number|null)` (same file).
- Produces: `steadinessNickname(stdevDeg?: number | null): { name: string; emoji: string } | null`

- [ ] **Step 1: Write the failing tests**

Add to `plankStats.test.ts`:

```ts
import { steadinessNickname } from "../plankStats";

describe("steadinessNickname", () => {
  // steadinessScore = clamp(100 - stdev*10). stdev 1 -> 90 (Statue),
  // stdev 2.5 -> 75 (Steady Eddie), stdev 4.5 -> 55 (Wobbler), stdev 6 -> 40 (Jelly).
  it("returns Statue for rock-solid steadiness (score >= 85)", () => {
    expect(steadinessNickname(1)).toEqual({ name: "Statue", emoji: "🗿" });
  });
  it("returns Steady Eddie for steady (score >= 70)", () => {
    expect(steadinessNickname(2.5)).toEqual({ name: "Steady Eddie", emoji: "💪" });
  });
  it("returns The Wobbler for wobbly (score >= 50)", () => {
    expect(steadinessNickname(4.5)).toEqual({ name: "The Wobbler", emoji: "🌊" });
  });
  it("returns Human Jellyfish for jelly (score < 50)", () => {
    expect(steadinessNickname(6)).toEqual({ name: "Human Jellyfish", emoji: "🪼" });
  });
  it("pins band boundaries at 85 and 70 and 50", () => {
    expect(steadinessNickname(1.5)).toEqual({ name: "Statue", emoji: "🗿" }); // score 85
    expect(steadinessNickname(3)).toEqual({ name: "Steady Eddie", emoji: "💪" }); // score 70
    expect(steadinessNickname(5)).toEqual({ name: "The Wobbler", emoji: "🌊" }); // score 50
  });
  it("returns null for missing/NaN stdev", () => {
    expect(steadinessNickname(null)).toBeNull();
    expect(steadinessNickname(undefined)).toBeNull();
    expect(steadinessNickname(NaN)).toBeNull();
  });
});
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd frontend && npx jest src/lib/__tests__/plankStats.test.ts -t steadinessNickname`
Expected: FAIL — `steadinessNickname is not a function`.

- [ ] **Step 3: Write minimal implementation**

Add to `plankStats.ts` (after `steadinessScore`), plus the interface near the top:

```ts
export interface Nickname {
  name: string;
  emoji: string;
}

const STEADINESS_NICKNAMES: Record<string, Nickname> = {
  "Rock Solid": { name: "Statue", emoji: "🗿" },
  Steady: { name: "Steady Eddie", emoji: "💪" },
  Wobbly: { name: "The Wobbler", emoji: "🌊" },
  "Jelly Mode": { name: "Human Jellyfish", emoji: "🪼" },
};

/** Funny nickname from a single steadiness stdev; null when no steadiness. */
export function steadinessNickname(stdevDeg?: number | null): Nickname | null {
  const score = steadinessScore(stdevDeg);
  return score ? STEADINESS_NICKNAMES[score.label] : null;
}
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd frontend && npx jest src/lib/__tests__/plankStats.test.ts -t steadinessNickname`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add frontend/src/lib/plankStats.ts frontend/src/lib/__tests__/plankStats.test.ts
git commit -m "feat(plank): steadinessNickname helper (per-attempt base name)"
```

---

### Task 2: `athleteNickname` helper (base + behavior modifier)

**Files:**
- Modify: `frontend/src/lib/plankStats.ts`
- Test: `frontend/src/lib/__tests__/plankStats.test.ts`

**Interfaces:**
- Consumes: `steadinessNickname` (Task 1), `Nickname` type.
- Produces: `athleteNickname(input: { stdevDeg?: number | null; attemptCount: number; uploadDates: (string | null)[] }): Nickname | null`

- [ ] **Step 1: Write the failing tests**

Add to `plankStats.test.ts`:

```ts
import { athleteNickname } from "../plankStats";

describe("athleteNickname", () => {
  const solid = 1; // -> Statue base
  const jelly = 6; // -> Human Jellyfish base

  it("returns null when there is no steadiness base", () => {
    expect(
      athleteNickname({ stdevDeg: null, attemptCount: 3, uploadDates: [] })
    ).toBeNull();
  });

  it("no modifier for normal cadence", () => {
    expect(
      athleteNickname({
        stdevDeg: solid,
        attemptCount: 3,
        uploadDates: ["2026-07-01", "2026-07-04", "2026-07-08"],
      })
    ).toEqual({ name: "Statue", emoji: "🗿" });
  });

  it("One-Shot for a single attempt", () => {
    expect(
      athleteNickname({ stdevDeg: solid, attemptCount: 1, uploadDates: ["2026-07-01"] })
    ).toEqual({ name: "One-Shot Statue", emoji: "🗿" });
  });

  it("Relentless for >=4 attempts with median gap <= 1 day", () => {
    expect(
      athleteNickname({
        stdevDeg: jelly,
        attemptCount: 4,
        uploadDates: ["2026-07-01", "2026-07-01", "2026-07-02", "2026-07-02"],
      })
    ).toEqual({ name: "Relentless Human Jellyfish", emoji: "🪼" });
  });

  it("The Elusive for >=2 attempts with a >=14 day gap", () => {
    expect(
      athleteNickname({
        stdevDeg: solid,
        attemptCount: 2,
        uploadDates: ["2026-06-01", "2026-07-01"],
      })
    ).toEqual({ name: "The Elusive Statue", emoji: "🗿" });
  });

  it("One-Shot wins over other rules for a single attempt", () => {
    expect(
      athleteNickname({ stdevDeg: jelly, attemptCount: 1, uploadDates: ["2026-07-01"] })
    ).toEqual({ name: "One-Shot Human Jellyfish", emoji: "🪼" });
  });

  it("ignores null dates and unordered input; <2 valid dates -> no gap rules", () => {
    expect(
      athleteNickname({
        stdevDeg: solid,
        attemptCount: 5,
        uploadDates: [null, "2026-07-01", null],
      })
    ).toEqual({ name: "Statue", emoji: "🗿" }); // only 1 valid date -> no cadence modifier
  });
});
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd frontend && npx jest src/lib/__tests__/plankStats.test.ts -t athleteNickname`
Expected: FAIL — `athleteNickname is not a function`.

- [ ] **Step 3: Write minimal implementation**

Add to `plankStats.ts`:

```ts
/** Consecutive-day gaps (days) from ISO dates; nulls dropped, sorted internally. */
function uploadGaps(uploadDates: (string | null)[]): number[] {
  const days = uploadDates
    .filter((d): d is string => !!d)
    .map((d) => Date.parse(`${d}T00:00:00`))
    .filter((ms) => !Number.isNaN(ms))
    .sort((a, b) => a - b)
    .map((ms) => ms / 86_400_000);
  const gaps: number[] = [];
  for (let i = 1; i < days.length; i++) gaps.push(days[i] - days[i - 1]);
  return gaps;
}

function median(xs: number[]): number {
  const s = [...xs].sort((a, b) => a - b);
  const mid = Math.floor(s.length / 2);
  return s.length % 2 ? s[mid] : (s[mid - 1] + s[mid]) / 2;
}

/** Athlete-level nickname: steadiness base + volume/cadence modifier. */
export function athleteNickname(input: {
  stdevDeg?: number | null;
  attemptCount: number;
  uploadDates: (string | null)[];
}): Nickname | null {
  const base = steadinessNickname(input.stdevDeg);
  if (!base) return null;

  const gaps = uploadGaps(input.uploadDates);
  let modifier: string | null = null;
  if (input.attemptCount === 1) {
    modifier = "One-Shot";
  } else if (input.attemptCount >= 4 && gaps.length > 0 && median(gaps) <= 1) {
    modifier = "Relentless";
  } else if (input.attemptCount >= 2 && gaps.length > 0 && Math.max(...gaps) >= 14) {
    modifier = "The Elusive";
  }

  return modifier ? { name: `${modifier} ${base.name}`, emoji: base.emoji } : base;
}
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd frontend && npx jest src/lib/__tests__/plankStats.test.ts -t athleteNickname`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add frontend/src/lib/plankStats.ts frontend/src/lib/__tests__/plankStats.test.ts
git commit -m "feat(plank): athleteNickname helper (base + behavior modifier)"
```

---

### Task 3: Backend surfaces `steadiness` on lift history

**Files:**
- Modify: `backend/toms_gym/routes/user_routes.py:128-131` (lifts query)
- Modify: `backend/toms_gym/services/lift_history.py` (`shape_lift_row`)
- Test: `backend/tests/test_lift_history.py`

**Interfaces:**
- Produces: `/users/<id>/lifts` rows and `shape_lift_row(row)` gain `steadiness: float | None`.

- [ ] **Step 1: Write the failing test**

Add to `test_lift_history.py`:

```python
def test_shape_lift_row_includes_steadiness():
    row = {
        "attempt_id": "a1", "competition_id": "c1", "competition_name": "Plank",
        "lift_type": "Plank", "report_lift_type": "plank", "weight": None,
        "created_at": None, "status": "completed", "analysis_status": "completed",
        "grade": None, "total_reps": None, "hold_s": "42.0",
        "steadiness": "1.8",
    }
    assert shape_lift_row(row)["steadiness"] == 1.8

def test_shape_lift_row_steadiness_null_safe():
    row = {"attempt_id": "a1", "steadiness": None}
    assert shape_lift_row(row)["steadiness"] is None
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd backend && venv/bin/python -m pytest tests/test_lift_history.py -k steadiness --noconftest`
Expected: FAIL — `KeyError: 'steadiness'` / key missing.

- [ ] **Step 3: Implement**

In `services/lift_history.py`, add to the returned dict in `shape_lift_row`:

```python
        "hold_s": _to_float(get("hold_s")),
        "steadiness": _to_float(get("steadiness")),
```

In `routes/user_routes.py`, add the column to the SELECT (after `hold_s`):

```sql
                       lr.report->>'total_in_plank_s' AS hold_s,
                       lr.report->>'body_line_stdev_deg' AS steadiness
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd backend && venv/bin/python -m pytest tests/test_lift_history.py -k steadiness --noconftest`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add backend/toms_gym/routes/user_routes.py backend/toms_gym/services/lift_history.py backend/tests/test_lift_history.py
git commit -m "feat(challenges): surface body_line_stdev_deg on lift history"
```

---

### Task 4: Backend carries best-attempt `steadiness` onto time leaderboard rows

**Files:**
- Modify: `backend/toms_gym/routes/competition_routes.py:415-464` (leaderboard query + attempt dict)
- Modify: `backend/toms_gym/services/challenge_leaderboard.py` (`_rank_time`)
- Test: `backend/tests/test_challenge_leaderboard.py`

**Interfaces:**
- Produces: ranked time rows gain `steadiness: float | None` (best attempt's). Weight rows omit it.

- [ ] **Step 1: Write the failing test**

Add to `test_challenge_leaderboard.py` (match the module's existing import of `rank_challenge`):

```python
def test_time_row_carries_best_attempt_steadiness():
    participants = [{
        "user_id": "u1", "name": "Ann", "weight_class": None, "gender": None,
        "attempts": [
            {"attempt_id": "a1", "lift_type": "Plank", "weight_kg": None,
             "status": "completed", "created_at": "2026-07-01",
             "video_url": "v", "annotated_video_url": None,
             "held_s": 30.0, "form_score": 0.9, "steadiness": 1.5},
            {"attempt_id": "a2", "lift_type": "Plank", "weight_kg": None,
             "status": "completed", "created_at": "2026-07-02",
             "video_url": "v", "annotated_video_url": None,
             "held_s": 60.0, "form_score": 0.8, "steadiness": 3.2},
        ],
    }]
    rows = rank_challenge(participants, metric="time")
    # best attempt is a2 (longer hold) -> its steadiness carries through
    assert rows[0]["steadiness"] == 3.2
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd backend && venv/bin/python -m pytest tests/test_challenge_leaderboard.py -k steadiness --noconftest`
Expected: FAIL — `KeyError: 'steadiness'`.

- [ ] **Step 3: Implement**

In `routes/competition_routes.py` leaderboard SELECT (after `form_score`):

```sql
                       lr.report->>'overall_form_score' AS form_score,
                       lr.report->>'body_line_stdev_deg' AS steadiness
```

And in the attempt dict appended to `participants[uid]["attempts"]`:

```python
                    "form_score": _to_float(row['form_score']),
                    "steadiness": _to_float(row['steadiness']),
```

In `services/challenge_leaderboard.py` `_rank_time`, add `steadiness` to both the
qualifying `row` dict and the zero-score `row` dict:

```python
            row = {
                "score": score,
                "best_by_lift": {"Plank": score},
                "form_score": best["form_score"],
                "steadiness": best.get("steadiness"),
                ...
            }
```
```python
            row = {
                "score": 0,
                "best_by_lift": {},
                "form_score": None,
                "steadiness": None,
                ...
            }
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd backend && venv/bin/python -m pytest tests/test_challenge_leaderboard.py -k steadiness --noconftest`
Expected: PASS. Also run the full file to confirm no regression:
`cd backend && venv/bin/python -m pytest tests/test_challenge_leaderboard.py --noconftest`

- [ ] **Step 5: Commit**

```bash
git add backend/toms_gym/routes/competition_routes.py backend/toms_gym/services/challenge_leaderboard.py backend/tests/test_challenge_leaderboard.py
git commit -m "feat(challenges): carry best-attempt steadiness onto time leaderboard rows"
```

---

### Task 5: Frontend types gain `steadiness`

**Files:**
- Modify: `frontend/src/lib/types.ts:405-426` (`ChallengeLeaderboardRow`)
- Modify: `frontend/src/components/challenge/AttemptHistory.tsx:8-16` (`AttemptRow`)

**Interfaces:**
- Produces: `ChallengeLeaderboardRow.steadiness: number | null`; `AttemptRow.steadiness: number | null`.

- [ ] **Step 1: Add the fields (type-only, verified by tsc)**

In `types.ts`, inside `ChallengeLeaderboardRow` (after `form_score`):

```ts
  /** time only; best attempt's body_line_stdev_deg. null otherwise. */
  steadiness: number | null;
```

In `AttemptHistory.tsx` `AttemptRow`:

```ts
  hold_s: number | null;
  steadiness: number | null;
```

- [ ] **Step 2: Verify typecheck passes**

Run: `cd frontend && npx tsc --noEmit`
Expected: PASS (no new errors).

- [ ] **Step 3: Commit**

```bash
git add frontend/src/lib/types.ts frontend/src/components/challenge/AttemptHistory.tsx
git commit -m "feat(challenges): steadiness field on leaderboard + attempt row types"
```

---

### Task 6: Shared `NicknameBadge` component

**Files:**
- Create: `frontend/src/components/challenge/NicknameBadge.tsx`
- Test: `frontend/src/components/challenge/__tests__/NicknameBadge.test.tsx`

**Interfaces:**
- Consumes: `Nickname` from `lib/plankStats`.
- Produces: `NicknameBadge({ nickname }: { nickname: Nickname | null })` — renders a pill or nothing.

- [ ] **Step 1: Write the failing test**

```tsx
import { render, screen } from "@testing-library/react";
import NicknameBadge from "../NicknameBadge";

describe("NicknameBadge", () => {
  it("renders the emoji and name", () => {
    render(<NicknameBadge nickname={{ name: "Statue", emoji: "🗿" }} />);
    expect(screen.getByText(/Statue/)).toBeInTheDocument();
    expect(screen.getByText(/🗿/)).toBeInTheDocument();
  });
  it("renders nothing when nickname is null", () => {
    const { container } = render(<NicknameBadge nickname={null} />);
    expect(container.firstChild).toBeNull();
  });
});
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd frontend && npx jest src/components/challenge/__tests__/NicknameBadge.test.tsx`
Expected: FAIL — cannot find module.

- [ ] **Step 3: Implement**

```tsx
import React from "react";
import type { Nickname } from "../../lib/plankStats";

/** Muted pill for a plank steadiness nickname. Renders nothing when null. */
const NicknameBadge: React.FC<{ nickname: Nickname | null; className?: string }> = ({
  nickname,
  className = "",
}) => {
  if (!nickname) return null;
  return (
    <span
      className={`inline-flex items-center gap-1 rounded-full border border-white/10 bg-white/5 px-2 py-0.5 text-[11px] text-white/60 ${className}`}
    >
      <span aria-hidden>{nickname.emoji}</span>
      {nickname.name}
    </span>
  );
};

export default NicknameBadge;
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd frontend && npx jest src/components/challenge/__tests__/NicknameBadge.test.tsx`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add frontend/src/components/challenge/NicknameBadge.tsx frontend/src/components/challenge/__tests__/NicknameBadge.test.tsx
git commit -m "feat(challenges): NicknameBadge pill component"
```

---

### Task 7: Render per-attempt nickname in AttemptHistory

**Files:**
- Modify: `frontend/src/components/challenge/AttemptHistory.tsx`
- Test: `frontend/src/components/challenge/__tests__/AttemptHistory.test.tsx` (create if absent)

**Interfaces:**
- Consumes: `steadinessNickname` (Task 1), `NicknameBadge` (Task 6), `AttemptRow.steadiness` (Task 5).

- [ ] **Step 1: Write the failing test**

Create/extend `__tests__/AttemptHistory.test.tsx`. Mock axios to return a plank attempt with steadiness and assert the badge appears:

```tsx
jest.mock("axios");
import axios from "axios";
import { render, screen, waitFor } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import AttemptHistory from "../AttemptHistory";

it("shows a steadiness nickname on a plank attempt", async () => {
  (axios.get as jest.Mock).mockResolvedValue({
    data: { lifts: [{ attempt_id: "a1", lift_type: "Plank", weight: null,
      created_at: "2026-07-01", analysis_status: "completed", grade: null,
      hold_s: 40, steadiness: 1 }] },
  });
  render(
    <MemoryRouter>
      <AttemptHistory userId="u1" competitionId="c1" metric="time" />
    </MemoryRouter>
  );
  await waitFor(() => expect(screen.getByText(/Statue/)).toBeInTheDocument());
});
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd frontend && npx jest src/components/challenge/__tests__/AttemptHistory.test.tsx`
Expected: FAIL — no "Statue" text.

- [ ] **Step 3: Implement**

In `AttemptHistory.tsx`: import the helpers, and inside the time-metric branch (the `metric === "time"` block, near the hold span) append a badge:

```tsx
import { steadinessNickname } from "../../lib/plankStats";
import NicknameBadge from "./NicknameBadge";
```
```tsx
              {metric === "time" ? (
                <span className="flex items-center gap-2">
                  <span className="font-medium tabular-nums">
                    {row.hold_s != null ? fmtHold(row.hold_s) : analyzing ? "analyzing…" : "—"}
                  </span>
                  <NicknameBadge nickname={steadinessNickname(row.steadiness)} />
                </span>
              ) : (
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd frontend && npx jest src/components/challenge/__tests__/AttemptHistory.test.tsx`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add frontend/src/components/challenge/AttemptHistory.tsx frontend/src/components/challenge/__tests__/AttemptHistory.test.tsx
git commit -m "feat(challenges): per-attempt steadiness nickname in AttemptHistory"
```

---

### Task 8: Render athlete nickname on leaderboard rows (LeaderboardRow + YouRow)

**Files:**
- Modify: `frontend/src/components/challenge/LeaderboardRow.tsx`
- Modify: `frontend/src/components/challenge/YouRow.tsx`
- Test: `frontend/src/components/challenge/__tests__/LeaderboardRow.test.tsx` (create if absent)

**Interfaces:**
- Consumes: `athleteNickname` (Task 2), `NicknameBadge` (Task 6), `ChallengeLeaderboardRow.steadiness` (Task 5).

- [ ] **Step 1: Write the failing test**

```tsx
import { render, screen } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import LeaderboardRow from "../LeaderboardRow";

const baseRow = {
  rank: 4, user_id: "u1", name: "Ann", score: 60, best_by_lift: { Plank: 60 },
  form_score: 0.8, steadiness: 1, attempt_id: "a1", clip_url: null,
  thumbnail_url: null, date: "2026-07-02", weight_class: null, gender: null,
  attempt_count: 1, history: [{ score: 60, date: "2026-07-02" }],
};

it("shows athlete nickname on a time-metric row", () => {
  render(
    <MemoryRouter>
      <LeaderboardRow row={baseRow as never} metric="time" clipHref={null} />
    </MemoryRouter>
  );
  expect(screen.getByText(/One-Shot Statue/)).toBeInTheDocument();
});

it("shows no nickname on a weight-metric row", () => {
  render(
    <MemoryRouter>
      <LeaderboardRow row={{ ...baseRow, steadiness: null } as never} metric="weight" clipHref={null} />
    </MemoryRouter>
  );
  expect(screen.queryByText(/Statue/)).not.toBeInTheDocument();
});
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd frontend && npx jest src/components/challenge/__tests__/LeaderboardRow.test.tsx`
Expected: FAIL — no "One-Shot Statue".

- [ ] **Step 3: Implement**

In `LeaderboardRow.tsx` and `YouRow.tsx`, import helpers and render a badge next
to the athlete name **only when `metric === "time"`**:

```tsx
import { athleteNickname } from "../../lib/plankStats";
import NicknameBadge from "./NicknameBadge";
```

Compute once inside the component body:

```tsx
  const nickname =
    metric === "time"
      ? athleteNickname({
          stdevDeg: row.steadiness,
          attemptCount: row.attempt_count,
          uploadDates: row.history.map((h) => h.date),
        })
      : null;
```

Render `<NicknameBadge nickname={nickname} />` adjacent to the name element in
each component (below the name line on mobile, inline on desktop — place it in
the existing name column container). In `YouRow`, guard on `entered` (only the
entered variant has a `row`).

- [ ] **Step 4: Run test to verify it passes**

Run: `cd frontend && npx jest src/components/challenge/__tests__/LeaderboardRow.test.tsx`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add frontend/src/components/challenge/LeaderboardRow.tsx frontend/src/components/challenge/YouRow.tsx frontend/src/components/challenge/__tests__/LeaderboardRow.test.tsx
git commit -m "feat(challenges): athlete steadiness nickname on leaderboard rows"
```

---

### Task 9: Render athlete nickname on podium chips

**Files:**
- Modify: `frontend/src/pages/ChallengeDetail.tsx:756-793` (podium chips strip)

**Interfaces:**
- Consumes: `athleteNickname` (Task 2), `NicknameBadge` (Task 6).

- [ ] **Step 1: Implement (podium chips show nickname for time metric)**

The podium chips strip currently only renders when a podium member has
`attempt_count > 1`. Broaden it so top-3 plank athletes with a nickname also get
a chip. Import helpers at top of `ChallengeDetail.tsx`:

```tsx
import { athleteNickname } from "../lib/plankStats";
import NicknameBadge from "../components/challenge/NicknameBadge";
```

Add a helper near `resolveClipHref`:

```tsx
  const rowNickname = (r: ChallengeLeaderboardRow) =>
    metric === "time"
      ? athleteNickname({
          stdevDeg: r.steadiness,
          attemptCount: r.attempt_count,
          uploadDates: r.history.map((h) => h.date),
        })
      : null;
```

In the podium chips block, render the badge beside each athlete's attempts chip.
Change the render guard so the strip appears when any podium row has either
`attempt_count > 1` **or** a nickname:

```tsx
                {podiumRows.some((r) => r.attempt_count > 1 || rowNickname(r)) && (
```

And inside the mapped chip button (or beside it), add:

```tsx
                          <NicknameBadge nickname={rowNickname(r)} className="ml-1" />
```

Place the badge so it renders next to the athlete's name in the chip. Keep the
existing `attempt_count > 1` filter for the expandable attempts button, but
render the nickname for all podium rows that have one.

- [ ] **Step 2: Verify typecheck + existing ChallengeDetail-adjacent tests**

Run: `cd frontend && npx tsc --noEmit && npx jest src/pages/__tests__ -t Challenge 2>/dev/null || true`
Expected: tsc PASS.

- [ ] **Step 3: Commit**

```bash
git add frontend/src/pages/ChallengeDetail.tsx
git commit -m "feat(challenges): athlete steadiness nickname on podium chips"
```

---

### Task 10: Full test suites + typecheck gate

**Files:** none (verification only).

- [ ] **Step 1: Backend CI gate**

Run: `cd backend && bash tools/run_ci_tests.sh`
Expected: all suites pass (includes `test_lift_history.py`, `test_challenge_leaderboard.py`).

- [ ] **Step 2: Frontend suite + typecheck**

Run: `cd frontend && npx tsc --noEmit && npx jest`
Expected: all suites green (new: `NicknameBadge`, `AttemptHistory`, `LeaderboardRow`, extended `plankStats`).

- [ ] **Step 3: Commit any snapshot/fixups if needed**

```bash
git add -A && git commit -m "test(challenges): plank steadiness nickname suites green" || true
```

---

### Task 11: Deploy + verify in production

**Files:** none (deploy + manual verification).

- [ ] **Step 1: Full deploy**

Run: `python3 deploy.py --skip-iam`
Expected: backend + frontend revisions deploy successfully.

- [ ] **Step 2: Verify backend field is live**

Find an ongoing plank challenge id, then:
`curl -s "https://my-python-backend-quyiiugyoq-ue.a.run.app/competitions/<id>/leaderboard" | python3 -m json.tool | grep -i steadiness`
Expected: `steadiness` present on time-metric rows (value or null).

- [ ] **Step 3: Verify frontend renders nicknames**

Open `https://my-frontend-quyiiugyoq-ue.a.run.app`, navigate to an ongoing plank
challenge. Confirm: podium chips / leaderboard rows show a nickname pill (e.g.
🗿 Statue), expanding an athlete shows per-attempt nicknames, and a weight
challenge shows none. Use Playwright MCP or a screenshot to capture evidence.

- [ ] **Step 4: Final commit (docs/notes if any)**

```bash
git add -A && git commit -m "docs(challenges): note plank steadiness nicknames shipped" || true
```

---

## Self-Review

**Spec coverage:**
- steadinessNickname (base) → Task 1 ✓
- athleteNickname (base+modifier, cadence rules) → Task 2 ✓
- Backend `body_line_stdev_deg` on lift history → Task 3 ✓
- Backend best-attempt steadiness on leaderboard → Task 4 ✓
- Types → Task 5 ✓
- Badge component → Task 6 ✓
- Attempt-history render (per-attempt) → Task 7 ✓
- Leaderboard + YouRow render (athlete-level) → Task 8 ✓
- Podium chips render → Task 9 ✓
- Tests → Tasks 1–8 inline + Task 10 gate ✓
- Deploy + verify → Task 11 ✓

**Placeholder scan:** No TBD/TODO; all code shown.

**Type consistency:** `Nickname` type defined in Task 1, consumed in 2/6/7/8/9. `steadiness` field spelled identically across backend (`steadiness`) and frontend (`row.steadiness`). `athleteNickname` signature identical in Tasks 2, 8, 9.
