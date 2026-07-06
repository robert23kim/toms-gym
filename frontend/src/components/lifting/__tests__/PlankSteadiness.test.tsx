import React from "react";
import "@testing-library/jest-dom";
import { render, screen, fireEvent } from "@testing-library/react";
import PlankSteadiness from "../PlankSteadiness";
import { LiftingReport, PlankPerSecond } from "../../../lib/types";

const sec = (t: number, state: string, deg: number, form: number): PlankPerSecond => ({
  t,
  state,
  body_line_deg: deg,
  elbow_deg: 90,
  form_score: form,
});

const perSecond: PlankPerSecond[] = [
  ...Array.from({ length: 5 }, (_, i) => sec(i, "settling", 170, 0.3)),
  ...Array.from({ length: 40 }, (_, i) => sec(5 + i, "in_plank", 175, 0.9)),
];

const report: LiftingReport = {
  camera_view: "side",
  active_arm: "left",
  total_reps: 0,
  overall_grade: "",
  overall_score: 0,
  rep_metrics: [],
  insights: [],
  lift_type: "plank",
  total_in_plank_s: 40,
  longest_run_s: 40,
  overall_form_score: 0.9,
  plank_type: "forearm",
  pose_detection_rate: 0.98,
  body_line_median_deg: 175,
  body_line_stdev_deg: 1.2,
  per_second: perSecond,
};

describe("PlankSteadiness", () => {
  it("renders the steadiness score pill and personality badge", () => {
    render(<PlankSteadiness report={report} onSeek={() => {}} />);
    expect(screen.getByText("88")).toBeInTheDocument(); // 100 - 1.2*10 = 88
    expect(screen.getByText(/rock solid/i)).toBeInTheDocument();
    expect(screen.getByText(/statue/i)).toBeInTheDocument(); // stdev 1.2, no wobbles
  });

  it("renders milestone ticks and the hold segments strip", () => {
    render(<PlankSteadiness report={report} onSeek={() => {}} />);
    expect(screen.getByText("0:30")).toBeInTheDocument(); // reached at 40s hold
    expect(screen.getByTestId("hold-segments")).toBeInTheDocument();
  });

  it("calls onSeek with a time within the video when the chart is clicked", () => {
    const onSeek = jest.fn();
    render(<PlankSteadiness report={report} onSeek={onSeek} />);
    const chart = screen.getByTestId("steadiness-chart");
    // jsdom has no layout; getBoundingClientRect is stubbed below
    chart.getBoundingClientRect = () =>
      ({ left: 0, top: 0, width: 560, height: 160, right: 560, bottom: 160, x: 0, y: 0, toJSON: () => ({}) } as DOMRect);
    // jsdom lacks PointerEvent; a MouseEvent typed "pointerdown" carries
    // clientX and still triggers React's onPointerDown.
    fireEvent(chart, new MouseEvent("pointerdown", { bubbles: true, clientX: 280 }));
    expect(onSeek).toHaveBeenCalledTimes(1);
    const t = onSeek.mock.calls[0][0];
    expect(t).toBeGreaterThanOrEqual(0);
    expect(t).toBeLessThanOrEqual(45);
  });

  it("renders nothing when per_second is empty", () => {
    const { container } = render(
      <PlankSteadiness report={{ ...report, per_second: [] }} onSeek={() => {}} />
    );
    expect(container.firstChild).toBeNull();
  });
});
