import React from "react";
import { render, screen } from "@testing-library/react";
import "@testing-library/jest-dom";
import StatusPill from "../StatusPill";

const daysFromNow = (n: number): string =>
  new Date(Date.now() + n * 86_400_000).toISOString();

describe("StatusPill", () => {
  test("ongoing shows a days-left countdown", () => {
    render(
      <StatusPill status="ongoing" startDate={daysFromNow(-5)} endDate={daysFromNow(23)} />,
    );
    const pill = screen.getByTestId("status-pill");
    expect(pill).toHaveAttribute("data-status", "ongoing");
    expect(pill).toHaveTextContent(/Ongoing · \d+d left/);
  });

  test("upcoming shows a starts-in countdown", () => {
    render(
      <StatusPill status="upcoming" startDate={daysFromNow(4)} endDate={daysFromNow(30)} />,
    );
    const pill = screen.getByTestId("status-pill");
    expect(pill).toHaveAttribute("data-status", "upcoming");
    expect(pill).toHaveTextContent(/starts in \d+d/);
  });

  test("completed shows Ended", () => {
    render(
      <StatusPill status="completed" startDate={daysFromNow(-30)} endDate={daysFromNow(-2)} />,
    );
    expect(screen.getByTestId("status-pill")).toHaveTextContent("Ended");
  });
});
