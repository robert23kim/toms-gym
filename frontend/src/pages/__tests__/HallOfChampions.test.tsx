import React from "react";
import "@testing-library/jest-dom";
import { render, screen, waitFor } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import HallOfChampions from "../HallOfChampions";
import * as api from "../../lib/api";

jest.mock("../../config", () => ({ API_URL: "https://test-api.example" }));
jest.mock("../../components/Layout", () => ({
  __esModule: true,
  default: ({ children }: { children: React.ReactNode }) => <div>{children}</div>,
}));
jest.mock("../../lib/api", () => ({
  ...jest.requireActual("../../lib/api"),
  fetchChampions: jest.fn(),
  getCompetitions: jest.fn(),
  getChallengeLeaderboard: jest.fn(),
}));

const champ = (over: Partial<api.Champion>): api.Champion => ({
  user_id: "u1",
  name: "wonder725",
  competition_id: "c1",
  competition_name: "Summer plank challenge",
  metric: "time",
  score: 275.4,
  ended_on: "2026-07-31",
  attempt_id: "a1",
  runners_up: [{ name: "victoria", user_id: "u2", score: 244.9 }],
  field_size: 6,
  margin: 30.5,
  winner_attempts: 3,
  won_on: "2026-07-20",
  ...over,
});

const renderHall = () =>
  render(
    <MemoryRouter>
      <HallOfChampions />
    </MemoryRouter>
  );

describe("HallOfChampions", () => {
  beforeEach(() => {
    jest.clearAllMocks();
    (localStorage.getItem as jest.Mock).mockReturnValue(null);
    (api.getCompetitions as jest.Mock).mockResolvedValue([]);
  });

  it("crowns the newest champion in the hero with margin and watch link", async () => {
    (api.fetchChampions as jest.Mock).mockResolvedValue([champ({})]);
    renderHall();
    const hero = await screen.findByRole("region", { name: /reigning champion/i });
    expect(hero).toHaveTextContent("wonder725");
    expect(hero).toHaveTextContent("4:35");
    expect(hero).toHaveTextContent("Won by 0:30 over victoria");
    expect(screen.getByRole("link", { name: /watch the win/i })).toHaveAttribute(
      "href",
      "/challenges/c1/participants/u1/video/a1"
    );
  });

  it("shows dynasties and numbered titles for repeat winners", async () => {
    (api.fetchChampions as jest.Mock).mockResolvedValue([
      champ({}),
      champ({ user_id: "u9", name: "Toka", competition_id: "c2", competition_name: "Biceps and Bench", metric: "weight", score: 115, ended_on: "2026-04-04" }),
      champ({ user_id: "u9", name: "Toka", competition_id: "c3", competition_name: "New Powerlifting", metric: "weight", score: 320, ended_on: "2026-02-04" }),
    ]);
    renderHall();
    const dyn = await screen.findByRole("region", { name: /dynasties/i });
    expect(dyn).toHaveTextContent("Toka");
    expect(dyn).toHaveTextContent("Back-to-back champion");
    expect(screen.getByText("2nd title")).toBeInTheDocument();
  });

  it("flags the viewer's own wins", async () => {
    (localStorage.getItem as jest.Mock).mockImplementation((k: string) =>
      k === "userId" ? "u1" : null
    );
    (api.fetchChampions as jest.Mock).mockResolvedValue([champ({})]);
    renderHall();
    expect(await screen.findByText(/your reign/i)).toBeInTheDocument();
    expect(screen.getByText("You")).toBeInTheDocument();
  });

  it("renders the empty throne when nobody has won yet", async () => {
    (api.fetchChampions as jest.Mock).mockResolvedValue([]);
    renderHall();
    expect(await screen.findByText(/the throne is empty/i)).toBeInTheDocument();
  });

  it("lists ongoing challenges with their current leader", async () => {
    (api.fetchChampions as jest.Mock).mockResolvedValue([]);
    (api.getCompetitions as jest.Mock).mockResolvedValue([
      { id: "live", title: "Pushup August", status: "ongoing", registrationDeadline: new Date(Date.now() + 3 * 86_400_000).toISOString() },
    ]);
    (api.getChallengeLeaderboard as jest.Mock).mockResolvedValue({
      metric: "reps",
      rows: [{ rank: 1, name: "Sam", score: 40 }],
    });
    renderHall();
    await waitFor(() => expect(screen.getByText(/Sam leads at 40 reps/)).toBeInTheDocument());
  });
});
