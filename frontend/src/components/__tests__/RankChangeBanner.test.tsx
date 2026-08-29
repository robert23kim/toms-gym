import React from "react";
import "@testing-library/jest-dom";
import { render, screen } from "@testing-library/react";
import RankChangeBanner from "../challenge/RankChangeBanner";
import type { Standing } from "../../lib/standing";
import type { ChallengeLeaderboardRow } from "../../lib/types";

const row: ChallengeLeaderboardRow = {
  rank: 3, user_id: "me", name: "Toka", score: 35, best_by_lift: {}, form_score: null, steadiness: null,
  attempt_id: null, clip_url: null, thumbnail_url: null, date: null, weight_class: null, gender: null,
  attempt_count: 2, history: [],
};

const standing: Standing = {
  row, rank: 3, participantCount: 6, best: 35, history: [], tries: 2, delta: null, isLeader: false,
  gap: 4, progress: 0.9, nextName: "rob kim", nextRank: 2, ctaLabel: "", goalSubtitle: null,
  below: null, podiumGap: null,
};

describe("RankChangeBanner", () => {
  it("celebrates a move up", () => {
    render(<RankChangeBanner shift={{ kind: "up", from: 5, to: 3 }} standing={standing} metric="reps" />);
    expect(screen.getByRole("status")).toHaveTextContent("▲ You moved up — #5 → #3 since your last visit");
    expect(screen.queryByText(/take it back/)).toBeNull();
  });

  it("names the person to pass after a slip", () => {
    render(<RankChangeBanner shift={{ kind: "down", from: 2, to: 3 }} standing={standing} metric="reps" />);
    expect(screen.getByRole("status")).toHaveTextContent(
      "▼ You slipped — #2 → #3 since your last visit · 4 reps to pass rob and take it back",
    );
  });
});
