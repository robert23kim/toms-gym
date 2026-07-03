import React from "react";
import { render, screen } from "@testing-library/react";
import "@testing-library/jest-dom";
import type { ChallengeLeaderboardRow } from "../../../lib/types";

// lib/api transitively imports config.ts (`import.meta.env`), unsupported by
// ts-jest — mock the avatar helper so the module never loads (see Podium.test).
jest.mock("../../../lib/api", () => ({
  getGolfAvatar: (name?: string | null, id?: string | number) =>
    `avatar:${name || id || "x"}`,
}));

import MomentumLine from "../MomentumLine";

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

const rows = [
  makeRow({ rank: 1, user_id: "u1", name: "Ana" }),
  makeRow({ rank: 2, user_id: "u2", name: "Devon" }),
  makeRow({ rank: 3, user_id: "u3", name: "Kim" }),
  makeRow({ rank: 4, user_id: "u4", name: "Sam" }),
];

describe("MomentumLine", () => {
  test("shows uploaded-today and joined counts", () => {
    render(<MomentumLine rows={rows} momentum={{ joined: 12, uploaded_today: 4 }} />);
    expect(screen.getByTestId("momentum-line")).toHaveTextContent(
      "4 uploaded today · 12 joined",
    );
  });

  test("renders at most three overlapping avatars", () => {
    render(<MomentumLine rows={rows} momentum={{ joined: 12, uploaded_today: 4 }} />);
    expect(screen.getAllByRole("img")).toHaveLength(3);
  });

  test("drops the uploaded-today clause when nothing was uploaded today", () => {
    render(<MomentumLine rows={rows} momentum={{ joined: 5, uploaded_today: 0 }} />);
    const line = screen.getByTestId("momentum-line");
    expect(line).toHaveTextContent("5 joined");
    expect(line).not.toHaveTextContent("uploaded today");
  });

  test("renders nothing when there are no faces and no activity", () => {
    const { container } = render(
      <MomentumLine rows={[]} momentum={{ joined: 0, uploaded_today: 0 }} />,
    );
    expect(container.querySelector('[data-testid="momentum-line"]')).toBeNull();
  });
});
