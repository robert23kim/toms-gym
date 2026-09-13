import React from "react";
import "@testing-library/jest-dom";
import { render, screen } from "@testing-library/react";
import SetStats from "../SetStats";

const rep = (start: number, peak: number, end: number, form: number) => ({
  start_s: start,
  peak_s: peak,
  end_s: end,
  form_score: form,
});

describe("SetStats", () => {
  it("renders pace, streak, slowest rep and the three thirds", () => {
    render(
      <SetStats
        repMetrics={[rep(0, 1, 2, 90), rep(2, 3, 4, 80), rep(4, 5, 7, 60), rep(10, 11, 12, 40)]}
      />
    );
    expect(screen.getByTestId("set-stats")).toHaveTextContent("Set Stats");
    expect(screen.getByTestId("set-stats-pace")).toHaveTextContent("20");
    expect(screen.getByTestId("set-stats-streak")).toHaveTextContent("2");
    expect(screen.getByTestId("set-stats-slowest")).toHaveTextContent("3s");
    expect(screen.getByTestId("set-stats")).toHaveTextContent("fastest rep 2s");
    const thirds = screen.getByTestId("set-stats-thirds");
    expect(thirds).toHaveTextContent("Start");
    expect(thirds).toHaveTextContent("form 85");
    expect(thirds).toHaveTextContent("Middle");
    expect(thirds).toHaveTextContent("form 60");
    expect(thirds).toHaveTextContent("End");
    expect(thirds).toHaveTextContent("form 40");
  });

  it("renders nothing without per-rep timing", () => {
    const { container } = render(
      <SetStats repMetrics={[{ form_score: 90 }, { form_score: 80 }, { form_score: 70 }]} />
    );
    expect(container).toBeEmptyDOMElement();
    expect(screen.queryByTestId("set-stats")).toBeNull();
  });

  it("renders nothing for fewer than three timed reps", () => {
    const { container } = render(<SetStats repMetrics={[rep(0, 1, 2, 90), rep(2, 3, 4, 90)]} />);
    expect(container).toBeEmptyDOMElement();
  });
});
