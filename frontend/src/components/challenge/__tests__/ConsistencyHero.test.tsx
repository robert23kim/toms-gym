import React from "react";
import "@testing-library/jest-dom";
import { fireEvent, render, screen, within } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import ConsistencyHero, { finalDayLabel, startDayLabel } from "../ConsistencyHero";
import type { ClubUpload } from "../clubBreakdown";
import type { ChallengeLeaderboard } from "../../../lib/types";
import {
  consistencyLeaderboard,
  endedConsistencyLeaderboard,
  upcomingConsistencyLeaderboard,
} from "../../../__fixtures__/consistencyLeaderboard";

const rowOf = (board: ChallengeLeaderboard, userId: string) =>
  board.rows.find((r) => r.user_id === userId) ?? null;

const renderHero = (board: ChallengeLeaderboard, viewer: string | null, uploads?: ClubUpload[]) =>
  render(
    <MemoryRouter>
      <ConsistencyHero
        block={board.consistency!}
        liftTypes={board.lift_types}
        viewerRow={viewer ? rowOf(board, viewer) : null}
        uploads={uploads}
      />
    </MemoryRouter>,
  );

const renderWith = (board: ChallengeLeaderboard, viewerRow: ChallengeLeaderboard["rows"][number]) =>
  render(
    <MemoryRouter>
      <ConsistencyHero block={board.consistency!} liftTypes={board.lift_types} viewerRow={viewerRow} />
    </MemoryRouter>,
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
    const seg = screen.getByTestId("consistency-ring-seg-Situp");
    expect(Number(seg.getAttribute("data-fraction"))).toBeCloseTo(42 / 150, 3);
    expect(screen.queryByTestId("consistency-ring-seg-Pushup")).toBeNull();
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
    renderWith({ ...consistencyLeaderboard, consistency: block }, viewer);
    expect(screen.getByTestId("consistency-caption")).toHaveTextContent(/^Quota met\.$/);
  });

  it("fills the ring exactly once above quota, never past it", () => {
    const base = rowOf(consistencyLeaderboard, "a1")!;
    const viewer = {
      ...base,
      this_week: { ...base.this_week!, lifts: 240, quota: 125, met: true, by_type: { Situp: 200, Pushup: 40, Squat: 0, Plank: 0 } },
    };
    renderWith(consistencyLeaderboard, viewer);
    const fractions = ["Situp", "Pushup"].map((t) => Number(screen.getByTestId(`consistency-ring-seg-${t}`).getAttribute("data-fraction")));
    expect(fractions[0] + fractions[1]).toBeCloseTo(1, 6);
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

  it("says each led type is an extra +25 that locks when the week ends", () => {
    renderHero(consistencyLeaderboard, null);
    expect(screen.getByTestId("consistency-bonus-note")).toHaveTextContent(
      /^\+25 extra for each lift type you log that week where nobody logs more, locked in when the week ends on Sunday\.$/,
    );
  });

  it("has no bonus note outside a live week", () => {
    renderHero(endedConsistencyLeaderboard, "a1");
    expect(screen.queryByTestId("consistency-bonus-note")).toBeNull();
  });
  it("names the last Sunday of the challenge from week_start and weeks", () => {
    expect(finalDayLabel({ week_start: "2026-11-02", weeks: 8 })).toBe("Sun 27 Dec");
    expect(finalDayLabel({ week_start: "2026-03-02", weeks: 1 })).toBe("Sun 8 Mar");
  });

  it("legends every lift type under the ring with the lead badge on the type the viewer leads", () => {
    renderHero(consistencyLeaderboard, "a1");
    const legend = screen.getByTestId("consistency-legend");
    const rows = within(legend).getAllByTestId(/^consistency-legend-/);
    expect(rows.map((r) => r.getAttribute("data-testid"))).toEqual([
      "consistency-legend-Situp",
      "consistency-legend-Pushup",
      "consistency-legend-Squat",
      "consistency-legend-Plank",
    ]);
    expect(screen.getByTestId("consistency-legend-Situp")).toHaveTextContent(/^Situp42lead$/i);
    expect(screen.getByTestId("consistency-legend-Pushup")).toHaveTextContent(/^Pushup0$/);
    expect(screen.queryByText(/You lead Situp this week/)).toBeNull();
  });

  it("shows plank seconds beside plank lifts in the legend", () => {
    const base = rowOf(consistencyLeaderboard, "a1")!;
    const viewer = { ...base, this_week: { ...base.this_week!, by_type: { Situp: 42, Plank: 8 }, plank_seconds: 82.79 } };
    renderWith(consistencyLeaderboard, viewer);
    expect(screen.getByTestId("consistency-legend-Plank")).toHaveTextContent("Plank8· 82.8 s");
  });

  it("itemises this week's points: banked lifts, the open quota bonus and the pending lead", () => {
    renderHero(consistencyLeaderboard, "a1");
    const receipt = screen.getByTestId("consistency-receipt");
    expect(within(receipt).getByTestId("receipt-banked")).toHaveTextContent("Lifts banked42 of 150+42");
    expect(within(receipt).getByTestId("receipt-quota")).toHaveTextContent("Quota met108 to go+50");
    expect(within(receipt).getByTestId("receipt-quota")).toHaveAttribute("data-earned", "false");
    expect(within(receipt).getByTestId("receipt-lead-Situp")).toHaveTextContent("Situp lead· locks Sun+25");
    expect(within(receipt).getByTestId("receipt-total")).toHaveTextContent("42 pts this week");
    expect(within(receipt).getByTestId("receipt-total")).toHaveTextContent("67 if the lead holds");
    expect(within(receipt).getByTestId("receipt-total")).toHaveTextContent("467 overall");
  });

  it("marks the quota bonus earned once the quota is met and drops the overall when it equals the week", () => {
    const base = rowOf(consistencyLeaderboard, "a1")!;
    const viewer = { ...base, score: 200, this_week: { ...base.this_week!, lifts: 150, met: true, leading: ["Situp", "Plank"] } };
    renderWith(consistencyLeaderboard, viewer);
    const receipt = screen.getByTestId("consistency-receipt");
    expect(within(receipt).getByTestId("receipt-quota")).toHaveTextContent(/^Quota met\+50$/);
    expect(within(receipt).getByTestId("receipt-quota")).toHaveAttribute("data-earned", "true");
    expect(within(receipt).getByTestId("receipt-total")).toHaveTextContent("200 pts this week");
    expect(within(receipt).getByTestId("receipt-total")).toHaveTextContent("250 if the leads hold");
    expect(within(receipt).getByTestId("receipt-total")).not.toHaveTextContent("overall");
  });

  it("has no receipt before the start, after the end or for anonymous visitors", () => {
    const { unmount } = renderHero(upcomingConsistencyLeaderboard, "a1");
    expect(screen.queryByTestId("consistency-receipt")).toBeNull();
    unmount();
    const ended = renderHero(endedConsistencyLeaderboard, "a1");
    expect(screen.queryByTestId("consistency-receipt")).toBeNull();
    ended.unmount();
    renderHero(consistencyLeaderboard, null);
    expect(screen.queryByTestId("consistency-receipt")).toBeNull();
    expect(screen.queryByTestId("consistency-legend")).toBeNull();
  });

  const uploads: ClubUpload[] = [
    { id: "u2", liftType: "Plank", at: "2026-11-17T18:21:00+00:00", lifts: 8, seconds: 82.79, failed: false, href: "/v/u2" },
    { id: "u3", liftType: "Pushup", at: "2026-11-17T18:22:00+00:00", lifts: null, seconds: null, failed: false, href: "/v/u3" },
    { id: "u1", liftType: "Situp", at: "2026-11-16T12:38:00+00:00", lifts: 22, seconds: null, failed: false, href: "/v/u1" },
    { id: "u0", liftType: "Situp", at: "2026-11-16T11:00:00+00:00", lifts: 0, seconds: null, failed: true, href: "/v/u0" },
  ];

  it("keeps this week's uploads behind one tap and lists them by day, newest first", () => {
    renderHero(consistencyLeaderboard, "a1", uploads);
    const toggle = screen.getByTestId("consistency-uploads-toggle");
    expect(toggle).toHaveTextContent("This week's uploads · 4");
    expect(toggle).toHaveAttribute("aria-expanded", "false");
    expect(screen.queryByTestId("consistency-uploads")).toBeNull();
    fireEvent.click(toggle);
    expect(toggle).toHaveAttribute("aria-expanded", "true");
    const list = screen.getByTestId("consistency-uploads");
    expect(within(list).getAllByTestId("consistency-upload-day").map((d) => d.textContent)).toEqual(["Tue 17 Nov", "Mon 16 Nov"]);
    const rows = within(list).getAllByTestId(/^consistency-upload-u/);
    expect(rows.map((r) => r.getAttribute("data-testid"))).toEqual([
      "consistency-upload-u3",
      "consistency-upload-u2",
      "consistency-upload-u1",
      "consistency-upload-u0",
    ]);
    expect(screen.getByTestId("consistency-upload-u2")).toHaveTextContent("Plank82.8 s1:21 pm+8");
    expect(screen.getByTestId("consistency-upload-u3")).toHaveTextContent("Pushup1:22 pmanalysing");
    expect(screen.getByTestId("consistency-upload-u1")).toHaveTextContent("Situp7:38 am+22");
    expect(screen.getByTestId("consistency-upload-u0")).toHaveTextContent("Situp6:00 amfailed");
    expect(screen.getByTestId("consistency-upload-u2").closest("a")).toHaveAttribute("href", "/v/u2");
  });

  it("offers no uploads toggle when there is nothing this week", () => {
    renderHero(consistencyLeaderboard, "a1", []);
    expect(screen.queryByTestId("consistency-uploads-toggle")).toBeNull();
  });
});
