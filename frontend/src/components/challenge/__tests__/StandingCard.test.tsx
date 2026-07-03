import React from "react";
import { render, screen } from "@testing-library/react";
import "@testing-library/jest-dom";
import StandingCard from "../StandingCard";
import { deriveStanding, type Standing } from "../../../lib/standing";
import type {
  ChallengeLeaderboard,
  ChallengeLeaderboardRow,
  ChallengeMetric,
} from "../../../lib/types";

const makeRow = (overrides: Partial<ChallengeLeaderboardRow> = {}): ChallengeLeaderboardRow => ({
  rank: 1,
  user_id: "u1",
  name: "Athlete",
  score: 50,
  best_by_lift: { Plank: 50 },
  form_score: 0.9,
  attempt_id: "a1",
  clip_url: null,
  thumbnail_url: null,
  date: "2026-07-01",
  weight_class: null,
  gender: null,
  attempt_count: 1,
  history: [{ score: 50, date: "2026-07-01" }],
  ...overrides,
});

const board = (
  rows: ChallengeLeaderboardRow[],
  metric: ChallengeMetric = "time",
): Pick<ChallengeLeaderboard, "rows" | "metric"> => ({ rows, metric });

const midPackStanding = (): Standing =>
  deriveStanding(
    board([
      makeRow({ rank: 1, user_id: "u1", name: "Ana", score: 30 }),
      makeRow({ rank: 2, user_id: "u2", name: "Devon", score: 22.5 }),
      makeRow({
        rank: 3,
        user_id: "me",
        name: "Toka",
        score: 18.6,
        attempt_count: 3,
        history: [
          { score: 9.2, date: "2026-06-28" },
          { score: 14.1, date: "2026-06-30" },
          { score: 18.6, date: "2026-07-02" },
        ],
      }),
      makeRow({ rank: 4, user_id: "u4", name: "Kim", score: 12 }),
    ]),
    "me",
  )!;

describe("StandingCard", () => {
  test("shows rank, of-N, and the viewer's best", () => {
    render(<StandingCard standing={midPackStanding()} metric="time" />);
    expect(screen.getByTestId("standing-rank")).toHaveTextContent("#3");
    expect(screen.getByTestId("standing-card")).toHaveTextContent("of 4");
    expect(screen.getByTestId("standing-card")).toHaveTextContent("18.6");
  });

  test("renders the sparkline with a delta and raw series from history", () => {
    render(<StandingCard standing={midPackStanding()} metric="time" />);
    expect(screen.getByTestId("sparkline")).toBeInTheDocument();
    expect(screen.getByTestId("sparkline-line")).toBeInTheDocument();
    expect(screen.getByTestId("standing-delta")).toHaveTextContent("+9.4s in 3 tries");
    expect(screen.getByTestId("standing-trend")).toHaveTextContent("9.2s → 14.1s → 18.6s");
  });

  test("shows the gap to the entrant directly above with a progress bar", () => {
    render(<StandingCard standing={midPackStanding()} metric="time" />);
    const gap = screen.getByTestId("standing-gap");
    expect(gap).toHaveTextContent("3.9s");
    expect(gap).toHaveTextContent("Devon");
    expect(gap).toHaveTextContent("#2");
    const bar = screen.getByTestId("standing-progress");
    expect(bar).toHaveStyle({ width: `${Math.round((18.6 / 22.5) * 100)}%` });
  });

  test("#1 viewer sees a defend-your-lead message and no progress bar", () => {
    const leader = deriveStanding(
      board([
        makeRow({ rank: 1, user_id: "me", name: "Toka", score: 40 }),
        makeRow({ rank: 2, user_id: "u2", name: "Ana", score: 30 }),
      ]),
      "me",
    )!;
    render(<StandingCard standing={leader} metric="time" />);
    expect(screen.getByTestId("standing-lead")).toHaveTextContent("defend your lead");
    expect(screen.queryByTestId("standing-gap")).toBeNull();
    expect(screen.queryByTestId("standing-progress")).toBeNull();
  });

  test("single attempt shows the sparkline dot but no delta line", () => {
    const single = deriveStanding(
      board([
        makeRow({ rank: 1, user_id: "u1", name: "Ana", score: 30 }),
        makeRow({
          rank: 2,
          user_id: "me",
          name: "Toka",
          score: 18.6,
          attempt_count: 1,
          history: [{ score: 18.6, date: "2026-07-02" }],
        }),
      ]),
      "me",
    )!;
    render(<StandingCard standing={single} metric="time" />);
    expect(screen.getByTestId("sparkline-dot")).toBeInTheDocument();
    expect(screen.queryByTestId("sparkline-line")).toBeNull();
    expect(screen.queryByTestId("standing-delta")).toBeNull();
  });

  test("weight metric renders the card in lbs", () => {
    const s = deriveStanding(
      board(
        [
          makeRow({ rank: 1, user_id: "u1", name: "Ana", score: 320 }),
          makeRow({ rank: 2, user_id: "me", name: "Toka", score: 300 }),
        ],
        "weight",
      ),
      "me",
    )!;
    render(<StandingCard standing={s} metric="weight" />);
    expect(screen.getByTestId("standing-card")).toHaveTextContent("300");
    expect(screen.getByTestId("standing-gap")).toHaveTextContent("20lbs");
  });
});
