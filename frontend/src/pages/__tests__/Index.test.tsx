import React from "react";
import "@testing-library/jest-dom";
import { render, screen, waitFor } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import Index from "../Index";
import * as api from "../../lib/api";

// config.ts uses import.meta (Vite), which jest can't parse; mock it as the
// repo's other tests do.
jest.mock("../../config", () => ({ API_URL: "https://test-api.example" }));

// Layout pulls in the Navbar/auth tree; stub it so the test stays on the page.
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
  uploadBowlingSheet: jest.fn(),
}));

const ongoing = { id: "c1", title: "Summer Plank Challenge", status: "ongoing", categories: ["Plank"] };
const completed = { id: "c2", title: "Old Squat-Off", status: "completed", categories: ["Squat"] };

const renderHome = () =>
  render(
    <MemoryRouter>
      <Index />
    </MemoryRouter>
  );

describe("Index (quiet-gym home)", () => {
  beforeEach(() => jest.clearAllMocks());

  it("renders the three vertical tiles with the right upload targets", async () => {
    (api.getCompetitions as jest.Mock).mockResolvedValue([]);
    renderHome();
    expect(screen.getByRole("link", { name: /^lift/i })).toHaveAttribute("href", "/lift");
    expect(screen.getByRole("link", { name: /^bowl/i })).toHaveAttribute("href", "/bowl");
    expect(screen.getByRole("link", { name: /golf/i })).toHaveAttribute("href", "/golf");
    await waitFor(() => expect(api.getCompetitions).toHaveBeenCalled());
  });

  it("lists only ongoing challenges as to-do rows that go straight to upload", async () => {
    (api.getCompetitions as jest.Mock).mockResolvedValue([ongoing, completed]);
    renderHome();
    await waitFor(() =>
      expect(screen.getByText("Summer Plank Challenge")).toBeInTheDocument()
    );
    expect(screen.getByText("Summer Plank Challenge").closest("a")).toHaveAttribute("href", "/challenges/c1");
    expect(screen.getByText("Plank")).toBeInTheDocument();
    expect(screen.queryByText("Old Squat-Off")).toBeNull();
    expect(screen.getByText(/tonight's to-do/i)).toBeInTheDocument();
  });

  it("keeps the standing to-do rows when nothing is ongoing", async () => {
    (api.getCompetitions as jest.Mock).mockResolvedValue([completed]);
    renderHome();
    await waitFor(() => expect(api.getCompetitions).toHaveBeenCalled());
    expect(screen.getByText("Snap tonight's bowling recap").closest("a")).toHaveAttribute("href", "/bowling/snap");
    expect(screen.getByText("Snap a bowling game").closest("a")).toHaveAttribute("href", "/bowling/snap");
    expect(screen.getByText("Snap a scorecard").closest("a")).toHaveAttribute("href", "/golf/snap");
    expect(screen.getByText("Log a lift").closest("a")).toHaveAttribute("href", "/lift/upload");
  });

  it("renders the demo loop", async () => {
    (api.getCompetitions as jest.Mock).mockResolvedValue([]);
    renderHome();
    expect(screen.getByText(/plank · hold \+ form/i)).toBeInTheDocument();
    await waitFor(() => expect(api.getCompetitions).toHaveBeenCalled());
  });

  it("anonymous visitors get the pitch, the demo, then the verticals", async () => {
    (api.getCompetitions as jest.Mock).mockResolvedValue([ongoing]);
    const { container } = renderHome();
    await waitFor(() => expect(screen.getByText("Summer Plank Challenge")).toBeInTheDocument());
    expect(screen.getByText(/AI analysis of your lift/i)).toBeInTheDocument();
    const labels = [...container.querySelectorAll("section[aria-label]")].map((s) => s.getAttribute("aria-label"));
    expect(labels).toEqual(["Pitch", "Your streak", "Analysis demo", "Verticals", "To-do"]);
  });

  describe("for a returning user", () => {
    beforeEach(() => (localStorage.getItem as jest.Mock).mockReturnValue("u1"));
    afterEach(() => (localStorage.getItem as jest.Mock).mockReset());

    it("skips the pitch, demo and tiles and leads with the to-do list above the streak", async () => {
      (api.getCompetitions as jest.Mock).mockResolvedValue([ongoing]);
      const { container } = renderHome();
      await waitFor(() => expect(screen.getByText("Summer Plank Challenge")).toBeInTheDocument());
      expect(screen.queryByText(/AI analysis of your lift/i)).toBeNull();
      expect(screen.queryByText(/plank · hold \+ form/i)).toBeNull();
      expect(screen.getByText("streak-card")).toBeInTheDocument();
      const labels = [...container.querySelectorAll("section[aria-label]")].map((s) => s.getAttribute("aria-label"));
      expect(labels).toEqual(["To-do", "Your streak"]);
      expect(screen.queryByRole("link", { name: /^lift$/i })).toBeNull();
      expect(screen.getByTestId("home-bowl-camera")).toBeInTheDocument();
      expect(screen.getByTestId("home-bowl-library")).toBeInTheDocument();
      expect(screen.getByTestId("home-game-camera")).toBeInTheDocument();
      expect(screen.getByTestId("home-challenge-c1-record")).toBeInTheDocument();
      expect(screen.getByText("Summer Plank Challenge").closest("a")).toBeNull();
    });
  });
});
