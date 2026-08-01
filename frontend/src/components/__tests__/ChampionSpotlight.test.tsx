import React from "react";
import "@testing-library/jest-dom";
import { render, screen, waitFor } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";

const mockFetchChampions = jest.fn();

jest.mock("../../lib/api", () => ({
  fetchChampions: (...args: unknown[]) => mockFetchChampions(...args),
  formatChampionScore: (metric: string, score: number) =>
    metric === "time" ? "4:35" : `${score} kg`,
  getGolfAvatar: (name?: string | null) => `avatar:${name}`,
}));

import ChampionSpotlight from "../ChampionSpotlight";

const champion = {
  user_id: "u1",
  name: "wonder725",
  competition_id: "c1",
  competition_name: "Summer plank challenge",
  metric: "time" as const,
  score: 275.4,
  ended_on: "2026-07-31",
  attempt_id: "a1",
};

const renderSpotlight = () =>
  render(
    <MemoryRouter>
      <ChampionSpotlight />
    </MemoryRouter>,
  );

describe("ChampionSpotlight", () => {
  beforeEach(() => mockFetchChampions.mockReset());

  it("celebrates the latest champion with score and links", async () => {
    mockFetchChampions.mockResolvedValue([champion]);
    renderSpotlight();
    await waitFor(() => expect(screen.getByText(/wonder725/)).toBeInTheDocument());
    expect(screen.getByText(/Summer plank challenge/)).toBeInTheDocument();
    expect(screen.getByText(/4:35/)).toBeInTheDocument();
    expect(screen.getByRole("link", { name: /View profile/i })).toHaveAttribute(
      "href",
      "/profile/u1",
    );
    expect(screen.getByRole("link", { name: /Watch the win/i })).toHaveAttribute(
      "href",
      "/challenges/c1/participants/u1/video/a1",
    );
  });

  it("omits the video link when the winning attempt is unknown", async () => {
    mockFetchChampions.mockResolvedValue([{ ...champion, attempt_id: null }]);
    renderSpotlight();
    await waitFor(() => expect(screen.getByText(/wonder725/)).toBeInTheDocument());
    expect(screen.queryByRole("link", { name: /Watch the win/i })).not.toBeInTheDocument();
  });

  it("renders nothing when there are no champions", async () => {
    mockFetchChampions.mockResolvedValue([]);
    const { container } = renderSpotlight();
    await waitFor(() => expect(mockFetchChampions).toHaveBeenCalled());
    expect(container).toBeEmptyDOMElement();
  });

  it("renders nothing when the fetch fails", async () => {
    mockFetchChampions.mockRejectedValue(new Error("boom"));
    const { container } = renderSpotlight();
    await waitFor(() => expect(mockFetchChampions).toHaveBeenCalled());
    expect(container).toBeEmptyDOMElement();
  });
});
