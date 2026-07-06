import React from "react";
import "@testing-library/jest-dom";
import { render, screen } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import HandicapResultCard from "../HandicapResultCard";

const base = {
  handicapIndex: 21.0,
  prevIndex: 21.3,
  totalScore: 93,
  differential: 20.5,
  profileTo: "/golf/profile/u1",
  roundTo: "/golf/round/r1",
};

const renderCard = (props = {}) =>
  render(
    <MemoryRouter>
      <HandicapResultCard {...base} {...props} />
    </MemoryRouter>
  );

describe("HandicapResultCard", () => {
  it("leads with the handicap index as the hero number", () => {
    renderCard();
    expect(screen.getByText("21.0")).toBeInTheDocument();
    expect(screen.getByText(/handicap index/i)).toBeInTheDocument();
  });

  it("shows an improvement delta (down = green ▼)", () => {
    renderCard(); // 21.3 -> 21.0 improved by 0.3
    expect(screen.getByText(/▼\s*0\.3/)).toBeInTheDocument();
  });

  it("shows a worsening delta (up = ▲)", () => {
    renderCard({ handicapIndex: 22.0, prevIndex: 21.3 });
    expect(screen.getByText(/▲\s*0\.7/)).toBeInTheDocument();
  });

  it("shows no delta pill when prevIndex is null or unchanged", () => {
    renderCard({ prevIndex: null });
    expect(screen.queryByText(/[▲▼]/)).toBeNull();
    renderCard({ prevIndex: 21.0 });
    expect(screen.queryByText(/[▲▼]/)).toBeNull();
  });

  it("shows provisional copy when handicapIndex is null", () => {
    renderCard({ handicapIndex: null });
    expect(screen.getByText(/provisional index pending/i)).toBeInTheDocument();
  });

  it("renders score, differential, and both links", () => {
    renderCard();
    expect(screen.getByText("93")).toBeInTheDocument();
    expect(screen.getByText(/leaderboard/i)).toHaveAttribute("href", "/golf/leaderboard");
    expect(screen.getByText(/my rounds/i)).toHaveAttribute("href", "/golf/profile/u1");
  });
});
