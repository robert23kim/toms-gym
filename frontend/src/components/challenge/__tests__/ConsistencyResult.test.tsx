import React from "react";
import "@testing-library/jest-dom";
import { render, screen } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import ConsistencyResult, { attemptLifts, attemptWeek, consistencyShareText } from "../ConsistencyResult";
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

const renderResult = (
  board = consistencyLeaderboard,
  userId: string | null = "a1",
  report: object = situp,
  extra: { isOwner?: boolean; athleteName?: string | null; attemptAt?: string | null } = {},
) =>
  render(
    <MemoryRouter>
      <ConsistencyResult board={board} userId={userId} report={report} {...extra} />
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

describe("attemptWeek", () => {
  it("reads the upload's local day in the challenge timezone, like backend week_of", () => {
    expect(attemptWeek("2026-11-02T05:00:00Z", consistencyRules)).toBe(1);
    expect(attemptWeek("2026-11-02T04:30:00Z", consistencyRules)).toBe(0);
    expect(attemptWeek("2026-11-08T23:00:00-05:00", consistencyRules)).toBe(1);
    expect(attemptWeek("2026-11-09T12:00:00+00:00", consistencyRules)).toBe(2);
    expect(attemptWeek("2026-11-18T15:00:00.123456+00:00", consistencyRules)).toBe(3);
    expect(attemptWeek(null, consistencyRules)).toBeNull();
    expect(attemptWeek("not a date", consistencyRules)).toBeNull();
  });
});

describe("ConsistencyResult on someone else's video", () => {
  it("names the athlete whose week it is", () => {
    renderResult(consistencyLeaderboard, "b1", situp, { isOwner: false, athleteName: "Ben B" });
    const block = screen.getByTestId("consistency-result");
    expect(block).toHaveTextContent("+3 lifts banked");
    expect(block).toHaveTextContent("Ben: 10 / 125 this week · 4 days left");
  });

  it("keeps the owner's own wording unprefixed", () => {
    renderResult(consistencyLeaderboard, "b1", situp, { isOwner: true, athleteName: "Ben" });
    expect(screen.getByTestId("consistency-result")).not.toHaveTextContent("Ben:");
  });
});

describe("ConsistencyResult for an attempt outside the live week", () => {
  it("uses the attempt's own week and drops the live week's progress", () => {
    renderResult(consistencyLeaderboard, "a1", situp, { attemptAt: "2026-11-04T17:00:00+00:00" });
    const block = screen.getByTestId("consistency-result");
    expect(block).toHaveTextContent("+3 lifts banked in week 1");
    expect(block).not.toHaveTextContent("this week");
  });

  it("calls a pre-start upload a warm-up once the club is live", () => {
    renderResult(consistencyLeaderboard, "a1", situp, { attemptAt: "2026-11-02T04:30:00Z" });
    const block = screen.getByTestId("consistency-result");
    expect(block).toHaveTextContent("+3 warm-up lifts · not scored");
    expect(block).not.toHaveTextContent("banked");
    expect(block).not.toHaveTextContent("this week");
  });

  it("keeps the week's progress when the attempt is from the live week", () => {
    renderResult(consistencyLeaderboard, "a1", situp, { attemptAt: "2026-11-18T15:00:00+00:00" });
    const block = screen.getByTestId("consistency-result");
    expect(block).toHaveTextContent("+3 lifts banked");
    expect(block).not.toHaveTextContent("in week");
    expect(block).toHaveTextContent("42 / 150 this week · 4 days left");
  });
});

describe("consistencyShareText", () => {
  const args = { board: consistencyLeaderboard, report: situp, challengeName: "The 100 Club" };

  it("shares the lifts and the week for the owner, without a rank or a doubled 'the'", () => {
    const text = consistencyShareText({ ...args, userId: "b1", isOwner: true, athleteName: "Ben" });
    expect(text).toBe("I banked 3 lifts in The 100 Club — 10 / 125 this week. Join me:");
  });

  it("names someone else's lifts", () => {
    const text = consistencyShareText({ ...args, userId: "b1", isOwner: false, athleteName: "Ben B" });
    expect(text).toBe("Ben banked 3 lifts in The 100 Club — 10 / 125 this week. Join in:");
  });

  it("leaves the week out for an older attempt and says warm-up before the start", () => {
    expect(
      consistencyShareText({ ...args, userId: "b1", isOwner: true, attemptAt: "2026-11-04T17:00:00Z" }),
    ).toBe("I banked 3 lifts in The 100 Club. Join me:");
    expect(
      consistencyShareText({ ...args, userId: "b1", isOwner: true, attemptAt: "2026-11-01T17:00:00Z" }),
    ).toBe("I logged 3 warm-up lifts in The 100 Club. Join me:");
  });
});

describe("ConsistencyResult while the lift type is still Automatic", () => {
  it("counts nothing and says why instead of banking zero", () => {
    expect(attemptLifts({ lift_type: "auto" }, consistencyRules)).toBeNull();
    renderResult(consistencyLeaderboard, "a1", { lift_type: "auto" });
    const block = screen.getByTestId("consistency-result");
    expect(block).toHaveTextContent("Not banked yet");
    expect(block).not.toHaveTextContent(/\+\d+ lifts? banked/);
  });
});
