import React from "react";
import { render, screen } from "@testing-library/react";
import "@testing-library/jest-dom";
import DifficultyMeter from "../DifficultyMeter";

describe("DifficultyMeter", () => {
  test("renders all four slope anchor labels", () => {
    render(<DifficultyMeter slope={113} />);
    expect(screen.getByText(/Forgiving/)).toBeInTheDocument();
    expect(screen.getByText(/^Average$/)).toBeInTheDocument();
    expect(screen.getByText(/Above average/)).toBeInTheDocument();
    expect(screen.getByText(/Brutal/)).toBeInTheDocument();
  });

  test("needle sits at the middle for slope=113", () => {
    render(<DifficultyMeter slope={113} />);
    const needle = screen.getByTestId("difficulty-meter-needle");
    const left = parseFloat(
      (needle.style.left || "0").replace("%", "").trim(),
    );
    expect(left).toBeGreaterThan(57);
    expect(left).toBeLessThan(60);
  });

  test("needle sits near the left edge for slope=100 (below average)", () => {
    render(<DifficultyMeter slope={100} />);
    const needle = screen.getByTestId("difficulty-meter-needle");
    const left = parseFloat(
      (needle.style.left || "0").replace("%", "").trim(),
    );
    expect(left).toBeGreaterThan(40);
    expect(left).toBeLessThan(50);
  });

  test("needle sits near the right edge for slope=145 (brutal)", () => {
    render(<DifficultyMeter slope={145} />);
    const needle = screen.getByTestId("difficulty-meter-needle");
    const left = parseFloat(
      (needle.style.left || "0").replace("%", "").trim(),
    );
    expect(left).toBeGreaterThan(85);
    expect(left).toBeLessThan(95);
  });

  test("needle clamps to edges for out-of-range slope", () => {
    const { rerender } = render(<DifficultyMeter slope={40} />);
    let needle = screen.getByTestId("difficulty-meter-needle");
    expect(
      parseFloat((needle.style.left || "0").replace("%", "").trim()),
    ).toBe(0);

    rerender(<DifficultyMeter slope={200} />);
    needle = screen.getByTestId("difficulty-meter-needle");
    expect(
      parseFloat((needle.style.left || "0").replace("%", "").trim()),
    ).toBe(100);
  });

  test("renders null when slope is null (no tee picked)", () => {
    const { container } = render(<DifficultyMeter slope={null} />);
    expect(container.querySelector('[data-testid="difficulty-meter"]')).toBeNull();
  });
});
