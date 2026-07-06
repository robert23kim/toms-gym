import React from "react";
import "@testing-library/jest-dom";
import { render, screen, waitFor } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import LiftHub from "../LiftHub";
import * as api from "../../lib/api";

// config.ts uses import.meta (Vite), which jest can't parse; the real api
// module (pulled via requireActual) transitively imports it.
jest.mock("../../config", () => ({ API_URL: "https://test-api.example" }));

jest.mock("../../lib/api", () => ({
  ...jest.requireActual("../../lib/api"),
  getCompetitions: jest.fn(),
}));

const plankChallenge = {
  id: "plank-1",
  title: "Summer plank challenge",
  status: "ongoing",
  categories: ["Plank"],
};

describe("LiftHub plank quick link", () => {
  it("links to the ongoing plank challenge when one exists", async () => {
    (api.getCompetitions as jest.Mock).mockResolvedValue([plankChallenge]);
    render(<MemoryRouter><LiftHub /></MemoryRouter>);
    await waitFor(() =>
      expect(screen.getByText(/plank challenge/i)).toBeInTheDocument()
    );
    expect(screen.getByText(/plank challenge/i).closest("a")).toHaveAttribute(
      "href",
      "/challenges/plank-1"
    );
  });

  it("renders no plank link when none is ongoing", async () => {
    (api.getCompetitions as jest.Mock).mockResolvedValue([]);
    render(<MemoryRouter><LiftHub /></MemoryRouter>);
    await waitFor(() => expect(api.getCompetitions).toHaveBeenCalled());
    expect(screen.queryByText(/plank challenge/i)).toBeNull();
  });
});
