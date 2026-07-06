import React from "react";
import "@testing-library/jest-dom";
import { render, screen } from "@testing-library/react";
import DemoLoop from "../DemoLoop";

describe("DemoLoop", () => {
  it("renders the three scenes and progress dots", () => {
    const { container } = render(<DemoLoop />);
    expect(screen.getByText(/plank · hold \+ form/i)).toBeInTheDocument();
    expect(screen.getByText(/bowl · ball tracking/i)).toBeInTheDocument();
    expect(screen.getByText(/golf · scorecard → handicap/i)).toBeInTheDocument();
    expect(container.querySelectorAll(".demo-dot").length).toBe(3);
    // payoff pills
    expect(screen.getByText("Hips level ✓")).toBeInTheDocument();
    expect(screen.getByText("Board 17 · Pocket ✓")).toBeInTheDocument();
    expect(screen.getByText("HCP 21.0")).toBeInTheDocument();
  });
});
