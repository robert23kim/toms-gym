import React from "react";
import "@testing-library/jest-dom";
import { render, screen, waitFor } from "@testing-library/react";

const mockFetchUserActivity = jest.fn();
jest.mock("../../lib/api", () => ({
  fetchUserActivity: (...args: unknown[]) => mockFetchUserActivity(...args),
}));
jest.mock("../../lib/share", () => ({ createAndCopyShareLink: jest.fn() }));

import StreakCard from "../StreakCard";

const daysAgo = (n: number) => {
  const d = new Date();
  d.setDate(d.getDate() - n);
  d.setHours(12, 0, 0, 0);
  return d.toISOString();
};

describe("StreakCard", () => {
  beforeEach(() => {
    jest.clearAllMocks();
    (localStorage.getItem as jest.Mock).mockReturnValue(null);
  });

  it("renders nothing without a local userId", () => {
    const { container } = render(<StreakCard />);
    expect(container).toBeEmptyDOMElement();
    expect(mockFetchUserActivity).not.toHaveBeenCalled();
  });

  it("renders nothing when the fetch fails", async () => {
    (localStorage.getItem as jest.Mock).mockImplementation((k: string) => (k === "userId" ? "u1" : "99"));
    mockFetchUserActivity.mockRejectedValue(new Error("boom"));
    const { container } = render(<StreakCard />);
    await waitFor(() => expect(mockFetchUserActivity).toHaveBeenCalledWith("u1"));
    expect(container).toBeEmptyDOMElement();
  });

  it("shows the week strip and streak count", async () => {
    (localStorage.getItem as jest.Mock).mockImplementation((k: string) => (k === "userId" ? "u1" : "99"));
    mockFetchUserActivity.mockResolvedValue([
      { at: daysAgo(0), kind: "lift" },
      { at: daysAgo(7), kind: "golf" },
    ]);
    render(<StreakCard />);
    expect(await screen.findByText("Your streak")).toBeInTheDocument();
    expect(screen.getByLabelText("2 week streak")).toBeInTheDocument();
    expect(screen.getAllByRole("listitem")).toHaveLength(7);
    expect(screen.getAllByTestId("streak-day-active").length).toBeGreaterThanOrEqual(1);
    expect(screen.getByRole("button", { name: /share/i })).toBeInTheDocument();
  });

  it("names the milestone once and remembers it", async () => {
    (localStorage.getItem as jest.Mock).mockImplementation((k: string) => (k === "userId" ? "u1" : null));
    mockFetchUserActivity.mockResolvedValue([
      { at: daysAgo(0), kind: "lift" },
      { at: daysAgo(7), kind: "lift" },
      { at: daysAgo(14), kind: "golf" },
      { at: daysAgo(21), kind: "bowl" },
    ]);
    render(<StreakCard />);
    expect(await screen.findByText(/Four weeks\. A month of showing up\./)).toBeInTheDocument();
    expect(localStorage.setItem).toHaveBeenCalledWith("streak-milestone:u1", "4");
  });

  it("stays quiet once the milestone was celebrated", async () => {
    (localStorage.getItem as jest.Mock).mockImplementation((k: string) => (k === "userId" ? "u1" : "4"));
    mockFetchUserActivity.mockResolvedValue([
      { at: daysAgo(0), kind: "lift" },
      { at: daysAgo(7), kind: "lift" },
      { at: daysAgo(14), kind: "golf" },
      { at: daysAgo(21), kind: "bowl" },
    ]);
    render(<StreakCard />);
    expect(await screen.findByText("Your streak")).toBeInTheDocument();
    expect(screen.queryByText(/Four weeks/)).toBeNull();
  });
});
