import React from "react";
import "@testing-library/jest-dom";
import { render, screen } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import BowlHub from "../BowlHub";

jest.mock("../../config", () => ({ API_URL: "https://test-api.example" }));

jest.mock("../../components/Layout", () => ({
  __esModule: true,
  default: ({ children }: { children: React.ReactNode }) => <div>{children}</div>,
}));

describe("BowlHub", () => {
  it("leads with the camera-first score-sheet CTA", () => {
    render(<MemoryRouter><BowlHub /></MemoryRouter>);
    expect(screen.getByText(/snap a score sheet/i).closest("a")).toHaveAttribute(
      "href",
      "/bowling/snap",
    );
  });

  it("keeps video analysis, insights, and challenges as secondary rows", () => {
    render(<MemoryRouter><BowlHub /></MemoryRouter>);
    expect(screen.getByText(/analyze a video/i).closest("a")).toHaveAttribute(
      "href",
      "/bowling/upload",
    );
    expect(screen.getByText(/my insights/i).closest("a")).toHaveAttribute(
      "href",
      "/bowling/insights/me",
    );
    expect(screen.getByText(/challenges/i).closest("a")).toHaveAttribute(
      "href",
      "/challenges",
    );
  });
});
