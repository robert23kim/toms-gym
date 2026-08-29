import React from "react";
import "@testing-library/jest-dom";
import { render, screen } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import ResultLadder from "../challenge/ResultLadder";
import { PersonalBest, Standing } from "../../lib/standing";
import type { ChallengeLeaderboardRow } from "../../lib/types";

const row: ChallengeLeaderboardRow = {
  rank: 2,
  user_id: "toka",
  name: "Toka",
  score: 35,
  best_by_lift: { Pushup: 35 },
  form_score: null,
  steadiness: null,
  attempt_id: "a2",
  clip_url: null,
  thumbnail_url: null,
  date: "2026-08-28",
  weight_class: null,
  gender: null,
  attempt_count: 2,
  history: [
    { score: 28, date: "2026-08-01" },
    { score: 35, date: "2026-08-28" },
  ],
};

const second: Standing = {
  row,
  rank: 2,
  participantCount: 7,
  best: 35,
  history: row.history,
  tries: 2,
  delta: 7,
  isLeader: false,
  gap: 4,
  progress: 35 / 39,
  nextName: "rob",
  nextRank: 1,
  ctaLabel: "Beat your best — 35reps",
  goalSubtitle: "4reps to reach #1",
  below: { name: "caleb smith", rank: 3, score: 20, gap: 15 },
  podiumGap: null,
};

const newBest: PersonalBest = { isPersonalBest: true, previousBest: 28, belowBest: false };
const noBest: PersonalBest = { isPersonalBest: false, previousBest: null, belowBest: false };

const renderLadder = (props: Partial<React.ComponentProps<typeof ResultLadder>> = {}) =>
  render(
    <MemoryRouter>
      <ResultLadder
        standing={second}
        personalBest={newBest}
        metric="reps"
        athleteName="Toka"
        isOwner
        challengeId="c1"
        challengeOpen
        {...props}
      />
    </MemoryRouter>,
  );

describe("ResultLadder", () => {
  it("shows rank, both neighbours with their gaps, and the new-best pill for the owner", () => {
    renderLadder();
    expect(screen.getByText("#2")).toBeInTheDocument();
    expect(screen.getByText("of 7")).toBeInTheDocument();
    expect(screen.getByText("4 reps to pass rob")).toBeInTheDocument();
    expect(screen.getByText("rob")).toBeInTheDocument();
    expect(screen.getByText("39 reps")).toBeInTheDocument();
    expect(screen.getByText("You")).toBeInTheDocument();
    expect(screen.getByText("15 reps clear")).toBeInTheDocument();
    expect(screen.getByText("caleb")).toBeInTheDocument();
    expect(screen.getByText("20 reps")).toBeInTheDocument();
    expect(screen.getByText(/New best · up from 28 reps/)).toBeInTheDocument();
    expect(screen.queryByRole("link", { name: /Beat this/ })).toBeNull();
  });

  it("speaks about a visitor's athlete in the third person and offers Beat this while open", () => {
    renderLadder({ isOwner: false });
    expect(screen.getByText("Where Toka stands")).toBeInTheDocument();
    expect(screen.getByRole("link", { name: /Beat this/ })).toHaveAttribute("href", "/challenges/c1/upload");
  });

  it("drops Beat this once the challenge has ended", () => {
    renderLadder({ isOwner: false, challengeOpen: false });
    expect(screen.queryByRole("link", { name: /Beat this/ })).toBeNull();
  });

  it("tells the leader they lead, and shows podium distance to someone off it", () => {
    renderLadder({
      personalBest: noBest,
      standing: { ...second, rank: 1, isLeader: true, gap: null, nextName: null, nextRank: null },
    });
    expect(screen.getByText("You lead the field")).toBeInTheDocument();

    renderLadder({
      personalBest: noBest,
      metric: "time",
      standing: { ...second, rank: 5, best: 100, gap: 20, nextName: "dee", nextRank: 4, below: null, podiumGap: 30 },
    });
    expect(screen.getByText("30.0s from the podium")).toBeInTheDocument();
    expect(screen.getByText("20.0s to pass dee")).toBeInTheDocument();
  });

  it("shows the athlete's best when the viewed attempt is weaker than it", () => {
    renderLadder({ personalBest: { isPersonalBest: false, previousBest: 35, belowBest: true } });
    expect(screen.getByText("Best: 35 reps")).toBeInTheDocument();
    expect(screen.queryByText(/New best/)).toBeNull();
  });

  it("treats a solo board as an invitation", () => {
    renderLadder({
      personalBest: noBest,
      standing: { ...second, rank: 1, participantCount: 1, isLeader: true, gap: null, nextName: null, nextRank: null, below: null },
    });
    expect(screen.getByText("First on the board")).toBeInTheDocument();
    expect(screen.queryByText("You")).toBeNull();
  });

  it("can carry a second recognition pill", () => {
    renderLadder({ extraPill: "Steadiest plank yet" });
    expect(screen.getByText(/Steadiest plank yet/)).toBeInTheDocument();
    expect(screen.getByText(/New best · up from 28 reps/)).toBeInTheDocument();
  });
});
