import React from "react";
import { render, screen } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import "@testing-library/jest-dom";
import type { ChallengeLeaderboardRow, ChallengeMetric } from "../../../lib/types";

// lib/api transitively imports config.ts (`import.meta.env`), unsupported by
// ts-jest — mock the avatar helper so the module never loads (see Podium.test).
jest.mock("../../../lib/api", () => ({
  getGolfAvatar: (name?: string | null, id?: string | number) =>
    `avatar:${name || id || "x"}`,
}));

import LeaderboardRow from "../LeaderboardRow";

const makeRow = (overrides: Partial<ChallengeLeaderboardRow> = {}): ChallengeLeaderboardRow => ({
  rank: 4,
  user_id: "u4",
  name: "Jade Okafor",
  score: 43.1,
  best_by_lift: { Plank: 43.1 },
  form_score: null,
  attempt_id: "a4",
  clip_url: "https://cdn/clip.mp4",
  thumbnail_url: null,
  date: "2026-07-01",
  weight_class: null,
  gender: null,
  attempt_count: 1,
  history: [],
  ...overrides,
});

const renderRow = (
  row: ChallengeLeaderboardRow,
  metric: ChallengeMetric = "time",
  clipHref: string | null = null,
) =>
  render(
    <MemoryRouter>
      <LeaderboardRow row={row} metric={metric} clipHref={clipHref} />
    </MemoryRouter>,
  );

describe("LeaderboardRow", () => {
  test("renders rank, name, and time score with unit", () => {
    renderRow(makeRow());
    const row = screen.getByTestId("leaderboard-row");
    expect(row).toHaveAttribute("data-rank", "4");
    expect(screen.getByText("Jade Okafor")).toBeInTheDocument();
    expect(row).toHaveTextContent("43.1s");
  });

  test("weight metric switches the score unit to lbs", () => {
    renderRow(makeRow({ score: 300.6, best_by_lift: { Squat: 300.6 } }), "weight");
    expect(screen.getByTestId("leaderboard-row")).toHaveTextContent("301lbs");
  });

  test("zero-score joiners are dimmed with no score", () => {
    renderRow(makeRow({ score: 0, clip_url: null, date: null }));
    const row = screen.getByTestId("leaderboard-row");
    expect(row).toHaveTextContent("No entry yet");
    expect(row).not.toHaveTextContent(/\ds/);
  });

  test("clip thumbnail links to the video route when resolvable", () => {
    renderRow(makeRow(), "time", "/challenges/1/participants/u4/video/9");
    const link = screen.getByRole("link");
    expect(link).toHaveAttribute("href", "/challenges/1/participants/u4/video/9");
  });

  test("no link is rendered when the clip is unresolvable", () => {
    renderRow(makeRow({ clip_url: null }), "time", null);
    expect(screen.queryByRole("link")).toBeNull();
  });

  test("desktop (#1b): row is a 4-column grid with an athlete avatar", () => {
    renderRow(makeRow(), "time", "/challenges/1/participants/u4/video/9");
    const row = screen.getByTestId("leaderboard-row");
    expect(row.className).toContain("lg:grid");
    expect(row.className).toContain("lg:grid-cols-[52px_1fr_120px_90px]");
    // desktop-only 30×30 athlete avatar sits in the ATHLETE column
    expect(row.querySelector('img[aria-hidden="true"]')).not.toBeNull();
  });

  test("desktop (#1b): the single clip link is placed in the CLIP column", () => {
    renderRow(makeRow(), "time", "/challenges/1/participants/u4/video/9");
    const links = screen.getAllByRole("link");
    expect(links).toHaveLength(1); // never two clip elements across breakpoints
    expect(links[0].className).toContain("lg:col-start-4");
  });
});
