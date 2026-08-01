jest.mock("../../../config", () => ({ API_URL: "http://test.local" }));

import React from "react";
import "@testing-library/jest-dom";
import { render, screen } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import TrophyCase, { championTitle } from "../TrophyCase";
import type { Champion } from "../../../lib/api";

const plankWin: Champion = {
  user_id: "u1",
  name: "wonder725",
  competition_id: "c1",
  competition_name: "Summer plank challenge",
  metric: "time",
  score: 275.4,
  ended_on: "2026-07-31",
  attempt_id: "a1",
};

const benchWin: Champion = {
  ...plankWin,
  competition_id: "c2",
  competition_name: "Biceps and Bench",
  metric: "weight",
  score: 120,
  ended_on: "2026-04-04",
};

describe("TrophyCase", () => {
  it("renders a trophy card per championship with score and date", () => {
    render(
      <MemoryRouter>
        <TrophyCase champions={[plankWin, benchWin]} />
      </MemoryRouter>,
    );
    expect(screen.getByText(/Summer plank challenge/)).toBeInTheDocument();
    expect(screen.getByText(/4:35/)).toBeInTheDocument();
    expect(screen.getByText(/Biceps and Bench/)).toBeInTheDocument();
    expect(screen.getByText(/120 kg/)).toBeInTheDocument();
    expect(screen.getAllByText(/🏆/)).toHaveLength(2);
  });

  it("renders nothing when there are no championships", () => {
    const { container } = render(
      <MemoryRouter>
        <TrophyCase champions={[]} />
      </MemoryRouter>,
    );
    expect(container).toBeEmptyDOMElement();
  });
});

describe("championTitle", () => {
  it("formats the crowned flair string with the win year", () => {
    expect(championTitle(plankWin)).toBe(
      "👑 Summer plank challenge Champion 2026",
    );
  });
});
