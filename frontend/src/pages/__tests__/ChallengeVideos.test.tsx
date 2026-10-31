import React from "react";
import "@testing-library/jest-dom";
import { render, screen } from "@testing-library/react";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import axios from "axios";
import ChallengeVideos from "../ChallengeVideos";

jest.mock("../../config", () => ({ API_URL: "https://test-api.example", APP_BUILD: "test" }));
jest.mock("../../components/Layout", () => ({
  __esModule: true,
  default: ({ children }: { children: React.ReactNode }) => <div>{children}</div>,
}));
jest.mock("axios", () => ({ __esModule: true, default: { get: jest.fn() } }));

const renderEmpty = (competition: { name: string; lifttypes: string[]; mode?: string }) => {
  (axios.get as jest.Mock).mockImplementation((url: string) =>
    url.endsWith("/lifts")
      ? Promise.resolve({ data: { lifts: [] } })
      : Promise.resolve({ data: { competition: { id: "c9", ...competition } } }),
  );
  render(
    <MemoryRouter initialEntries={["/challenges/c9/videos"]}>
      <Routes>
        <Route path="/challenges/:id/videos" element={<ChallengeVideos />} />
      </Routes>
    </MemoryRouter>,
  );
};

describe("ChallengeVideos empty-state upload link", () => {
  beforeEach(() => jest.clearAllMocks());

  it("sends the 100 Club to the challenge page, never the bare upload route", async () => {
    renderEmpty({ name: "The 100 Club", lifttypes: ["Situp", "Pushup", "Squat", "Plank"], mode: "consistency" });
    expect(await screen.findByRole("link", { name: "Upload Video" })).toHaveAttribute("href", "/challenges/c9");
  });

  it("sends a multi-category challenge to the challenge page", async () => {
    renderEmpty({ name: "Mixed", lifttypes: ["Squat", "Bench Press"] });
    expect(await screen.findByRole("link", { name: "Upload Video" })).toHaveAttribute("href", "/challenges/c9");
  });

  it("keeps the upload route for a single-lift challenge", async () => {
    renderEmpty({ name: "Squat-off", lifttypes: ["Squat"] });
    expect(await screen.findByRole("link", { name: "Upload Video" })).toHaveAttribute("href", "/challenges/c9/upload");
  });
});
