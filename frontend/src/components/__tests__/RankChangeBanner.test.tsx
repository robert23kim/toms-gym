import React from "react";
import "@testing-library/jest-dom";
import { render, screen } from "@testing-library/react";
import RankChangeBanner from "../challenge/RankChangeBanner";

describe("RankChangeBanner", () => {
  it("celebrates a move up", () => {
    render(<RankChangeBanner shift={{ kind: "up", from: 5, to: 3 }} />);
    expect(screen.getByRole("status")).toHaveTextContent("▲ You moved up — #5 → #3 since your last visit");
  });

  it("states a slip plainly — the standing card beneath already shows the way back", () => {
    render(<RankChangeBanner shift={{ kind: "down", from: 2, to: 3 }} />);
    expect(screen.getByRole("status")).toHaveTextContent("▼ You slipped — #2 → #3 since your last visit");
    expect(screen.queryByText(/take it back/)).toBeNull();
  });
});
