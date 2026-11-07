import React from "react";
import "@testing-library/jest-dom";
import { render, screen } from "@testing-library/react";
import ConsistencyHero, { startDayLabel } from "../ConsistencyHero";
import type { ChallengeLeaderboard } from "../../../lib/types";
import {
  consistencyLeaderboard,
  endedConsistencyLeaderboard,
  upcomingConsistencyLeaderboard,
} from "../../../__fixtures__/consistencyLeaderboard";

const rowOf = (board: ChallengeLeaderboard, userId: string) =>
  board.rows.find((r) => r.user_id === userId) ?? null;

const renderHero = (board: ChallengeLeaderboard, viewer: string | null) =>
  render(
    <ConsistencyHero
      block={board.consistency!}
      liftTypes={board.lift_types}
      viewerRow={viewer ? rowOf(board, viewer) : null}
    />,
  );

describe("ConsistencyHero", () => {
  it("shows the live week line with days left", () => {
    renderHero(consistencyLeaderboard, "a1");
    expect(screen.getByTestId("consistency-week-line")).toHaveTextContent("Week 3 of 8 · 4 days left");
  });

  it("says one day on Sunday", () => {
    const sunday = { ...consistencyLeaderboard, consistency: { ...consistencyLeaderboard.consistency!, days_left: 1 } };
    renderHero(sunday, "a1");
    expect(screen.getByTestId("consistency-week-line")).toHaveTextContent("Week 3 of 8 · 1 day left");
  });

  it("shows the start day before week 1 and Ended after the last week", () => {
    const { unmount } = renderHero(upcomingConsistencyLeaderboard, "a1");
    expect(screen.getByTestId("consistency-week-line")).toHaveTextContent("Starts Monday 2 Nov");
    unmount();
    renderHero(endedConsistencyLeaderboard, "a1");
    expect(screen.getByTestId("consistency-week-line")).toHaveTextContent(/^Ended$/);
  });

  it("formats the start day from a bare date without a UTC day-shift", () => {
    expect(startDayLabel("2026-11-02")).toBe("Monday 2 Nov");
  });

  it("rings the viewer's lifts against this week's quota with the streak flame", () => {
    renderHero(consistencyLeaderboard, "a1");
    expect(screen.getByTestId("consistency-ring-count")).toHaveTextContent("42 / 150");
    expect(screen.getByTestId("consistency-streak")).toHaveTextContent("2-week streak");
    expect(screen.getByTestId("consistency-streak")).toHaveTextContent("🔥");
    const arc = screen.getByTestId("consistency-ring-arc");
    const dash = Number(arc.getAttribute("stroke-dasharray"));
    const offset = Number(arc.getAttribute("stroke-dashoffset"));
    expect(1 - offset / dash).toBeCloseTo(42 / 150, 3);
    expect(screen.queryByTestId("consistency-pending")).toBeNull();
  });

  it("says a video is still analysing when one is pending", () => {
    renderHero(consistencyLeaderboard, "b1");
    expect(screen.getByTestId("consistency-ring-count")).toHaveTextContent("10 / 125");
    expect(screen.getByTestId("consistency-pending")).toHaveTextContent("1 video still analysing");
  });

  it("has no flame for a zero streak", () => {
    renderHero(consistencyLeaderboard, "c1");
    expect(screen.getByTestId("consistency-ring-count")).toHaveTextContent("0 / 100");
    expect(screen.queryByTestId("consistency-streak")).toBeNull();
  });

  it("marks this week's type leaders as leading, in lift-type order", () => {
    renderHero(consistencyLeaderboard, "a1");
    const situp = screen.getByTestId("consistency-leader-Situp");
    const plank = screen.getByTestId("consistency-leader-Plank");
    expect(situp).toHaveTextContent("Ana 42");
    expect(situp).toHaveTextContent(/leading/i);
    expect(plank).toHaveTextContent("Ben 100 s");
    expect(screen.queryByTestId("consistency-leader-Pushup")).toBeNull();
    expect(screen.queryByTestId("consistency-leader-Squat")).toBeNull();
    expect(situp.compareDocumentPosition(plank) & Node.DOCUMENT_POSITION_FOLLOWING).toBeTruthy();
  });

  it("shows anonymous visitors the week line and leaders, not the ring", () => {
    renderHero(consistencyLeaderboard, null);
    expect(screen.getByTestId("consistency-week-line")).toHaveTextContent("Week 3 of 8");
    expect(screen.getByTestId("consistency-leader-Situp")).toBeInTheDocument();
    expect(screen.queryByTestId("consistency-ring-count")).toBeNull();
    expect(screen.queryByTestId("consistency-streak")).toBeNull();
  });

  it("drops the leading chips once the challenge has ended", () => {
    renderHero(endedConsistencyLeaderboard, "a1");
    expect(screen.queryByTestId("consistency-leader-Situp")).toBeNull();
  });

  it("captions week 1 before the start, never week 0", () => {
    renderHero(upcomingConsistencyLeaderboard, "a1");
    expect(rowOf(upcomingConsistencyLeaderboard, "a1")!.this_week!.index).toBe(0);
    expect(screen.getByTestId("consistency-caption")).toHaveTextContent("Week 1 quota: 100 lifts");
    expect(screen.queryByText(/Week 0/)).toBeNull();
  });

  it("captions a final tally after the end, never week 9", () => {
    renderHero(endedConsistencyLeaderboard, "a1");
    expect(rowOf(endedConsistencyLeaderboard, "a1")!.this_week!.index).toBe(9);
    expect(screen.getByTestId("consistency-caption")).toHaveTextContent("Final: 492 pts · 2 of 8 weeks met");
    expect(screen.queryByText(/Week 9/)).toBeNull();
  });

  it("does not promise a next week once the last week's quota is met", () => {
    const base = rowOf(consistencyLeaderboard, "a1")!;
    const viewer = { ...base, this_week: { ...base.this_week!, index: 8, lifts: 260, met: true } };
    const block = { ...consistencyLeaderboard.consistency!, week_index: 8 };
    render(<ConsistencyHero block={block} liftTypes={consistencyLeaderboard.lift_types} viewerRow={viewer} />);
    expect(screen.getByTestId("consistency-caption")).toHaveTextContent(/^Quota met\.$/);
  });

  it("fills the ring exactly once above quota, never past it", () => {
    const base = rowOf(consistencyLeaderboard, "a1")!;
    const viewer = { ...base, this_week: { ...base.this_week!, lifts: 240, quota: 125, met: true } };
    render(<ConsistencyHero block={consistencyLeaderboard.consistency!} liftTypes={consistencyLeaderboard.lift_types} viewerRow={viewer} />);
    const arc = screen.getByTestId("consistency-ring-arc");
    expect(Number(arc.getAttribute("stroke-dashoffset"))).toBe(0);
    expect(screen.getByTestId("consistency-caption")).toHaveTextContent("Quota met — the bar rises next week.");
  });

  it("notes warm-up lifts before the start", () => {
    renderHero(upcomingConsistencyLeaderboard, "a1");
    expect(screen.getByTestId("consistency-ring-count")).toHaveTextContent("0 / 100");
    expect(screen.getByTestId("consistency-warmup")).toHaveTextContent("20 warm-up lifts");
  });
  it("labels the card as the weekly quota, not the challenge name again", () => {
    renderHero(consistencyLeaderboard, "a1");
    expect(screen.getByTestId("consistency-eyebrow")).toHaveTextContent(/^Weekly quota$/);
    expect(screen.queryByText("The 100 Club")).toBeNull();
  });

  it("says type bonuses are added when the week ends", () => {
    renderHero(consistencyLeaderboard, null);
    expect(screen.getByTestId("consistency-bonus-note")).toHaveTextContent(
      "Type bonuses (+25 each) are added when the week ends on Sunday.",
    );
  });

  it("has no bonus note outside a live week", () => {
    renderHero(endedConsistencyLeaderboard, "a1");
    expect(screen.queryByTestId("consistency-bonus-note")).toBeNull();
  });
});
