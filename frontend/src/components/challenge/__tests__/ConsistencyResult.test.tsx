import React from "react";
import "@testing-library/jest-dom";
import { render, screen } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import ConsistencyResult, { attemptLifts } from "../ConsistencyResult";
import {
  consistencyLeaderboard,
  consistencyRules,
  upcomingConsistencyLeaderboard,
} from "../../../__fixtures__/consistencyLeaderboard";

const situp = {
  lift_type: "Situp",
  total_reps: 4,
  rep_metrics: [{ form_score: 90 }, { form_score: 80 }, { form_score: 40 }, { form_score: 30 }],
};

const renderResult = (board = consistencyLeaderboard, userId: string | null = "a1", report: object = situp) =>
  render(
    <MemoryRouter>
      <ConsistencyResult board={board} userId={userId} report={report} />
    </MemoryRouter>,
  );

describe("attemptLifts", () => {
  it("mirrors the backend: sloppy situps half, plank per 10 s floored, other lifts zero", () => {
    expect(attemptLifts(situp, consistencyRules)).toBe(3);
    expect(attemptLifts({ lift_type: "Pushup", total_reps: 13 }, consistencyRules)).toBe(13);
    expect(attemptLifts({ lift_type: "Squat", total_reps: 20 }, consistencyRules)).toBe(20);
    expect(attemptLifts({ lift_type: "Plank", total_in_plank_s: 119.5 }, consistencyRules)).toBe(11);
    expect(attemptLifts({ lift_type: "Plank", total_in_plank_s: 9.9 }, consistencyRules)).toBe(0);
    expect(attemptLifts({ lift_type: "Bench", total_reps: 5 }, consistencyRules)).toBe(0);
    expect(attemptLifts({ lift_type: "Plank", total_in_plank_s: null }, consistencyRules)).toBeNull();
  });
});

describe("ConsistencyResult", () => {
  it("shows the lifts banked, the week's progress and the days left, never a rank", () => {
    renderResult();
    const block = screen.getByTestId("consistency-result");
    expect(block).toHaveTextContent("+3 lifts banked");
    expect(block).toHaveTextContent("42 / 150 this week · 4 days left");
    expect(block).not.toHaveTextContent(/#\d/);
    expect(screen.getByRole("link", { name: /board/i })).toHaveAttribute(
      "href",
      `/challenges/${consistencyLeaderboard.competition_id}`,
    );
  });

  it("says the quota is met once it is", () => {
    const board = {
      ...consistencyLeaderboard,
      rows: consistencyLeaderboard.rows.map((r) =>
        r.user_id === "a1" ? { ...r, this_week: { ...r.this_week!, lifts: 150, met: true } } : r,
      ),
    };
    renderResult(board);
    expect(screen.getByTestId("consistency-result")).toHaveTextContent("Quota met · 150 / 150 this week · 4 days left");
  });

  it("calls a pre-start upload a warm-up", () => {
    renderResult(upcomingConsistencyLeaderboard);
    expect(screen.getByTestId("consistency-result")).toHaveTextContent("+3 warm-up lifts · scoring starts Monday 2 Nov");
  });

  it("still shows the lifts when the athlete has no row yet", () => {
    renderResult(consistencyLeaderboard, "nobody");
    const block = screen.getByTestId("consistency-result");
    expect(block).toHaveTextContent("+3 lifts banked");
    expect(block).not.toHaveTextContent("this week");
  });
});
