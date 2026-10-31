import React from "react";
import "@testing-library/jest-dom";
import { render, screen, waitFor } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import Index from "../Index";
import * as api from "../../lib/api";
import { consistencyLeaderboard } from "../../__fixtures__/consistencyLeaderboard";

jest.mock("../../config", () => ({ API_URL: "https://test-api.example" }));
jest.mock("../../components/Layout", () => ({
  __esModule: true,
  default: ({ children }: { children: React.ReactNode }) => <div>{children}</div>,
}));
jest.mock("../../components/StreakCard", () => ({
  __esModule: true,
  default: () => <div>streak-card</div>,
}));
jest.mock("../../lib/api", () => ({
  ...jest.requireActual("../../lib/api"),
  getCompetitions: jest.fn(),
  getChallengeLeaderboard: jest.fn(),
  uploadBowlingSheet: jest.fn(),
}));

const club = {
  id: "club-100",
  title: "The 100 Club",
  status: "ongoing",
  categories: ["Situp", "Pushup", "Squat", "Plank", "Men", "Women"],
  mode: "consistency",
};
const plank = { id: "c1", title: "Summer Plank Challenge", status: "ongoing", categories: ["Plank"] };

const renderHome = () =>
  render(
    <MemoryRouter>
      <Index />
    </MemoryRouter>,
  );

describe("Index with The 100 Club open", () => {
  beforeEach(() => {
    jest.clearAllMocks();
    (api.getCompetitions as jest.Mock).mockResolvedValue([club, plank]);
    (api.getChallengeLeaderboard as jest.Mock).mockResolvedValue(consistencyLeaderboard);
  });
  afterEach(() => (localStorage.getItem as jest.Mock).mockReset());

  it("gives a saved user a progress pill on a link to the challenge page", async () => {
    (localStorage.getItem as jest.Mock).mockReturnValue("a1");
    renderHome();
    await waitFor(() => expect(screen.getByText("42 / 150 · 4 days left")).toBeInTheDocument());
    expect(screen.getByText("The 100 Club").closest("a")).toHaveAttribute("href", "/challenges/club-100");
    expect(api.getChallengeLeaderboard).toHaveBeenCalledTimes(1);
    expect(api.getChallengeLeaderboard).toHaveBeenCalledWith("club-100");
  });

  it("gives anonymous visitors the plain link row and fetches no board", async () => {
    (localStorage.getItem as jest.Mock).mockReturnValue(null);
    renderHome();
    await waitFor(() => expect(screen.getByText("The 100 Club")).toBeInTheDocument());
    expect(screen.getByText("The 100 Club").closest("a")).toHaveAttribute("href", "/challenges/club-100");
    expect(screen.queryByText(/days left/)).toBeNull();
    expect(api.getChallengeLeaderboard).not.toHaveBeenCalled();
  });

  it("keeps the plain row when the board fetch fails", async () => {
    (localStorage.getItem as jest.Mock).mockReturnValue("a1");
    (api.getChallengeLeaderboard as jest.Mock).mockRejectedValue(new Error("down"));
    renderHome();
    await waitFor(() => expect(api.getChallengeLeaderboard).toHaveBeenCalled());
    expect(screen.getByText("The 100 Club").closest("a")).toHaveAttribute("href", "/challenges/club-100");
    expect(screen.queryByText(/days left/)).toBeNull();
  });
});
