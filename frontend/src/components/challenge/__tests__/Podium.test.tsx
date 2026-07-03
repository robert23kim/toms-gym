import React from "react";
import { render, screen } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import "@testing-library/jest-dom";
import type { ChallengeLeaderboardRow, ChallengeMetric } from "../../../lib/types";

// lib/api transitively imports config.ts, which uses `import.meta.env` (Vite) —
// unsupported by ts-jest. Mock the avatar helper so the module never loads here.
jest.mock("../../../lib/api", () => ({
  getGolfAvatar: (name?: string | null, id?: string | number) =>
    `avatar:${name || id || "x"}`,
}));

import Podium from "../Podium";

const makeRow = (overrides: Partial<ChallengeLeaderboardRow> = {}): ChallengeLeaderboardRow => ({
  rank: 1,
  user_id: "u1",
  name: "Athlete",
  score: 50,
  best_by_lift: { Plank: 50 },
  form_score: 0.9,
  attempt_id: "a1",
  clip_url: "https://cdn/clip.mp4",
  thumbnail_url: null,
  date: "2026-07-01",
  weight_class: "83kg",
  gender: "male",
  attempt_count: 1,
  history: [{ score: 50, date: "2026-07-01" }],
  ...overrides,
});

const renderPodium = (
  rows: ChallengeLeaderboardRow[],
  metric: ChallengeMetric = "time",
  getClipHref: (r: ChallengeLeaderboardRow) => string | null = () => null,
) =>
  render(
    <MemoryRouter>
      <Podium rows={rows} metric={metric} getClipHref={getClipHref} />
    </MemoryRouter>,
  );

const topThree = (): ChallengeLeaderboardRow[] => [
  makeRow({ rank: 1, user_id: "u1", name: "robert23kim", score: 65.8 }),
  makeRow({ rank: 2, user_id: "u2", name: "Priya K", score: 61.2 }),
  makeRow({ rank: 3, user_id: "u3", name: "Marcus A", score: 54.7 }),
];

describe("Podium", () => {
  test("renders columns in 2 · 1 · 3 order", () => {
    const { container } = renderPodium(topThree());
    const places = Array.from(
      container.querySelectorAll('[data-testid^="podium-place-"]'),
    ).map((el) => el.getAttribute("data-testid"));
    expect(places).toEqual(["podium-place-2", "podium-place-1", "podium-place-3"]);
  });

  test("only the champion has a crown", () => {
    renderPodium(topThree());
    expect(screen.getAllByTestId("podium-crown")).toHaveLength(1);
    // The crown sits inside the 1st-place column.
    expect(screen.getByTestId("podium-place-1")).toContainElement(
      screen.getByTestId("podium-crown"),
    );
  });

  test("pedestals carry gold / silver / bronze medal colors", () => {
    renderPodium(topThree());
    expect(screen.getByTestId("podium-pedestal-1")).toHaveAttribute("data-medal", "gold");
    expect(screen.getByTestId("podium-pedestal-2")).toHaveAttribute("data-medal", "silver");
    expect(screen.getByTestId("podium-pedestal-3")).toHaveAttribute("data-medal", "bronze");
  });

  test("time metric renders seconds with an 's' unit", () => {
    renderPodium(topThree(), "time");
    expect(screen.getByTestId("podium-score-1")).toHaveTextContent("65.8s");
  });

  test("weight metric renders a rounded total with an 'lbs' unit", () => {
    const rows = [
      makeRow({ rank: 1, score: 315.4, best_by_lift: { Squat: 315.4 } }),
      makeRow({ rank: 2, user_id: "u2", score: 300, best_by_lift: { Squat: 300 } }),
    ];
    renderPodium(rows, "weight");
    expect(screen.getByTestId("podium-score-1")).toHaveTextContent("315lbs");
  });

  test("thin state (2 entrants) fills only the occupied places", () => {
    const rows = [
      makeRow({ rank: 1, user_id: "u1", score: 40 }),
      makeRow({ rank: 2, user_id: "u2", score: 30 }),
    ];
    renderPodium(rows);
    expect(screen.getByTestId("podium-place-1")).toBeInTheDocument();
    expect(screen.getByTestId("podium-place-2")).toBeInTheDocument();
    expect(screen.queryByTestId("podium-place-3")).toBeNull();
  });

  test("empty state (no scored rows) renders nothing", () => {
    const { container } = renderPodium([
      makeRow({ rank: 1, user_id: "u1", score: 0, clip_url: null }),
    ]);
    expect(container.querySelector('[data-testid="podium"]')).toBeNull();
  });

  test("play badge appears only when a clip href is resolvable", () => {
    renderPodium(topThree(), "time", (r) => (r.rank === 1 ? "/clip/1" : null));
    const badges = screen.getAllByTestId("podium-play-badge");
    expect(badges).toHaveLength(1);
  });

  test("desktop (#1b): champion pedestal and score gain lg: scale-ups", () => {
    renderPodium(topThree());
    expect(screen.getByTestId("podium-pedestal-1").className).toContain("lg:h-[132px]");
    expect(screen.getByTestId("podium-score-1").className).toContain("lg:text-[32px]");
  });
});
