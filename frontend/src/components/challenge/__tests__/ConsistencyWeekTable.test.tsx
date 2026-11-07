import React from "react";
import "@testing-library/jest-dom";
import { render, screen, within } from "@testing-library/react";
import ConsistencyWeekTable from "../ConsistencyWeekTable";
import { consistencyLeaderboard } from "../../../__fixtures__/consistencyLeaderboard";

const ana = consistencyLeaderboard.rows.find((r) => r.user_id === "a1")!;

describe("ConsistencyWeekTable", () => {
  it("shows the live week's provisional leads as locking on Sunday", () => {
    render(<ConsistencyWeekTable weeks={ana.weeks!} liveIndex={3} leading={["Situp"]} />);
    expect(screen.getByTestId("week-bonus-3")).toHaveTextContent("Situp · locks Sun");
    expect(screen.getByTestId("week-bonus-1")).toHaveTextContent(/^Situp, Plank$/);
  });

  it("shows a dash on the live week when the athlete leads nothing", () => {
    render(<ConsistencyWeekTable weeks={ana.weeks!} liveIndex={3} leading={[]} />);
    expect(screen.getByTestId("week-bonus-3")).toHaveTextContent(/^—$/);
  });

  it("breaks each week down by lift type, plank with its seconds", () => {
    render(<ConsistencyWeekTable weeks={ana.weeks!} liveIndex={3} />);
    expect(screen.getByTestId("week-types-1")).toHaveTextContent(/^Situp 45 · Pushup 43 · Plank 24 \(240 s\)$/);
    expect(screen.getByTestId("week-types-3")).toHaveTextContent(/^Situp 42$/);
    const halves = [{ ...ana.weeks![0], by_type: { Situp: 31.5, Pushup: 65, Squat: 0, Plank: 11 }, plank_seconds: 119.5 }];
    render(<ConsistencyWeekTable weeks={halves} />);
    expect(within(screen.getAllByTestId("week-types-1")[1]).getByText(/Situp 31.5 · Pushup 65 · Plank 11 \(119.5 s\)/)).toBeInTheDocument();
  });
});
