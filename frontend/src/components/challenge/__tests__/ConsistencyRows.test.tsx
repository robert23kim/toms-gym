import React from "react";
import { render, screen, fireEvent, within } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import "@testing-library/jest-dom";

jest.mock("../../../lib/api", () => ({
  getGolfAvatar: (name?: string | null, id?: string | number) => `avatar:${name || id || "x"}`,
}));

import LeaderboardRow from "../LeaderboardRow";
import YouRow from "../YouRow";
import Podium from "../Podium";
import ConsistencyWeekTable from "../ConsistencyWeekTable";
import { StreakFlame } from "../ConsistencyMeta";
import { consistencyLeaderboard } from "../../../__fixtures__/consistencyLeaderboard";

const [ana, ben, cy] = consistencyLeaderboard.rows;

const wrap = (ui: React.ReactElement) => render(<MemoryRouter>{ui}</MemoryRouter>);

describe("100 Club leaderboard rows", () => {
  it("shows points, the streak flame and this week's progress", () => {
    wrap(<LeaderboardRow row={ben} metric="consistency" clipHref={null} />);
    const row = screen.getByTestId("leaderboard-row");
    expect(row).toHaveTextContent("330pts");
    expect(within(row).getByTestId("streak-flame")).toHaveTextContent("🔥1");
    expect(within(row).getByTestId("row-this-week")).toHaveTextContent("10/125 this week");
  });

  it("lists a zero-point row with its week and no flame", () => {
    wrap(<LeaderboardRow row={cy} metric="consistency" clipHref={null} />);
    const row = screen.getByTestId("leaderboard-row");
    expect(within(row).getByTestId("row-this-week")).toHaveTextContent("0/100 this week");
    expect(within(row).queryByTestId("streak-flame")).toBeNull();
    expect(row).not.toHaveTextContent("No entry yet");
  });

  it("notes warm-up lifts on a row with no points yet", () => {
    wrap(<LeaderboardRow row={{ ...cy, warmup_lifts: 1 }} metric="consistency" clipHref={null} />);
    expect(screen.getByTestId("row-this-week")).toHaveTextContent("0/100 this week · 1 warm-up");
  });

  it("offers the week table toggle instead of an attempts count", () => {
    const onToggle = jest.fn();
    wrap(<LeaderboardRow row={ben} metric="consistency" clipHref={null} attemptCount={4} onToggleAttempts={onToggle} />);
    const chip = screen.getByRole("button", { name: /weeks/i });
    expect(chip).not.toHaveTextContent(/attempts/);
    fireEvent.click(chip);
    expect(onToggle).toHaveBeenCalled();
  });

  it("keeps legacy rows on their date subtitle and attempts chip", () => {
    wrap(
      <LeaderboardRow
        row={{ ...ben, this_week: undefined, streak: undefined }}
        metric="reps"
        clipHref={null}
        attemptCount={4}
        onToggleAttempts={() => {}}
      />,
    );
    expect(screen.queryByTestId("row-this-week")).toBeNull();
    expect(screen.getByRole("button", { name: /4 attempts/ })).toBeInTheDocument();
  });

  it("shows the viewer's points, flame and week on the You row", () => {
    wrap(<YouRow entered row={ana} metric="consistency" clipHref={null} />);
    const row = screen.getByTestId("you-row");
    expect(row).toHaveTextContent("467pts");
    expect(within(row).getByTestId("streak-flame")).toHaveTextContent("🔥2");
    expect(within(row).getByTestId("row-this-week")).toHaveTextContent("42/150 this week");
  });

  it("puts points, flame and week under each podium score", () => {
    wrap(<Podium rows={[ana, ben]} metric="consistency" getClipHref={() => null} />);
    expect(screen.getByTestId("podium-score-1")).toHaveTextContent("467pts");
    expect(screen.getByTestId("podium-this-week-1")).toHaveTextContent("🔥242/150 this week");
    expect(screen.getByTestId("podium-score-2")).toHaveTextContent("330pts");
    expect(screen.getByTestId("podium-this-week-2")).toHaveTextContent("10/125 this week");
  });
});

describe("ConsistencyWeekTable", () => {
  it("lists week, quota, lifts, met, bonuses and points oldest first", () => {
    render(<ConsistencyWeekTable weeks={ana.weeks!} liveIndex={3} />);
    const rows = screen.getAllByTestId(/^week-row-/);
    expect(rows.map((r) => r.getAttribute("data-testid"))).toEqual(["week-row-1", "week-row-2", "week-row-3"]);
    const cells = (i: number) => within(rows[i]).getAllByRole("cell").map((c) => c.textContent);
    expect(cells(0)).toEqual(["1", "100", "112", "✓", "Situp, Plank", "200"]);
    expect(cells(1)).toEqual(["2", "125", "130", "✓", "Situp, Pushup", "225"]);
    expect(cells(2)).toEqual(["3now", "150", "42", "…", "—", "42"]);
  });

  it("marks a missed finished week and the quota reset", () => {
    render(<ConsistencyWeekTable weeks={ben.weeks!} liveIndex={3} />);
    const cells = (i: number) =>
      within(screen.getByTestId(`week-row-${i}`)).getAllByRole("cell").map((c) => c.textContent);
    expect(cells(1)).toEqual(["1", "100", "95", "—", "Pushup, Squat", "145"]);
    expect(cells(2)).toEqual(["2", "100", "100", "✓", "Squat", "175"]);
  });

  it("says so when there are no scoring weeks yet", () => {
    render(<ConsistencyWeekTable weeks={[]} />);
    expect(screen.getByTestId("week-table")).toHaveTextContent("No scoring weeks yet.");
  });
});

describe("100 Club accessible names", () => {
  it("names the streak flame as an image", () => {
    render(<StreakFlame streak={2} />);
    expect(screen.getByRole("img", { name: "2-week streak" })).toHaveTextContent("🔥2");
  });

  it("names the met, missed and in-progress marks as images", () => {
    render(<ConsistencyWeekTable weeks={ben.weeks!} liveIndex={3} />);
    expect(screen.getByRole("img", { name: "missed" })).toBeInTheDocument();
    expect(screen.getByRole("img", { name: "met" })).toBeInTheDocument();
    expect(screen.getByRole("img", { name: "in progress" })).toBeInTheDocument();
  });
});
