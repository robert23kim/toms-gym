import React from "react";
import "@testing-library/jest-dom";
import { render, screen } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import * as api from "../../lib/api";

jest.mock("../../config", () => ({ API_URL: "https://test-api.example" }));
jest.mock("../../lib/api", () => ({
  ...jest.requireActual("../../lib/api"),
  fetchChampions: jest.fn(),
}));

import ChampionSpotlight from "../ChampionSpotlight";

describe("ChampionSpotlight on a 100 Club win", () => {
  it("formats the winning score as points", async () => {
    (api.fetchChampions as jest.Mock).mockResolvedValue([
      {
        user_id: "a1",
        name: "Ana",
        competition_id: "club-100",
        competition_name: "The 100 Club",
        metric: "consistency",
        score: 325,
        ended_on: "2026-12-27",
        attempt_id: null,
      },
    ]);
    render(
      <MemoryRouter>
        <ChampionSpotlight />
      </MemoryRouter>,
    );
    expect(await screen.findByText(/The 100 Club champion — 325 pts/)).toBeInTheDocument();
  });
});
