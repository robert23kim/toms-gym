import React from "react";
import "@testing-library/jest-dom";
import { render, screen } from "@testing-library/react";
import NightCard from "../bowling/NightCard";
import type { Night } from "../../lib/bowlingNight";

const base: Night = {
  playedOn: "2026-08-29",
  count: 3,
  avg: 169,
  high: 202,
  priorAvg: 162,
  delta: 7,
  bestSince: { kind: "since", date: "2026-07-10" },
};

describe("NightCard", () => {
  it("leads with tonight's average, the delta, and when the high game was last beaten", () => {
    render(<NightCard night={base} />);
    expect(screen.getByText("169")).toBeInTheDocument();
    expect(screen.getByText("avg over 3 games")).toBeInTheDocument();
    expect(screen.getByText(/\+7 vs your average/)).toBeInTheDocument();
    expect(screen.getByText("202 high — your best game since Jul 10")).toBeInTheDocument();
  });

  it("handles a first night and a best-ever game without a delta", () => {
    render(<NightCard night={{ ...base, priorAvg: null, delta: null, bestSince: { kind: "first" } }} />);
    expect(screen.getByText("202 high — first night on the books")).toBeInTheDocument();
    expect(screen.queryByText(/vs your average/)).toBeNull();

    render(<NightCard night={{ ...base, delta: -2.5, bestSince: { kind: "best-yet" } }} />);
    expect(screen.getByText("202 high — your best game yet")).toBeInTheDocument();
    expect(screen.getByText(/▼ -2.5 vs your average/)).toBeInTheDocument();
  });
});
