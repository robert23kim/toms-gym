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

jest.mock("../../lib/api", () => ({
  ...jest.requireActual("../../lib/api"),
  getCompetitions: jest.fn(),
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
    expect(screen.getByRole("link", { name: /lift/i })).toHaveAttribute("href", "/lift/upload");
    expect(screen.getByRole("link", { name: /bowl/i })).toHaveAttribute("href", "/bowling/upload");
    expect(screen.getByRole("link", { name: /golf/i })).toHaveAttribute("href", "/golf/snap");
    await waitFor(() => expect(api.getCompetitions).toHaveBeenCalled());
  });

  it("shows only ongoing challenges as row cards linking to their pages", async () => {
    (api.getCompetitions as jest.Mock).mockResolvedValue([ongoing, completed]);
    renderHome();
    await waitFor(() =>
      expect(screen.getByText("Summer Plank Challenge")).toBeInTheDocument()
    );
    expect(screen.getByText("Summer Plank Challenge").closest("a")).toHaveAttribute("href", "/challenges/c1");
    expect(screen.getByText("Plank")).toBeInTheDocument();
    expect(screen.queryByText("Old Squat-Off")).toBeNull();
    expect(screen.getByText(/open challenges/i)).toBeInTheDocument();
  });

  it("hides the strip label entirely when nothing is ongoing but keeps an All challenges link", async () => {
    (api.getCompetitions as jest.Mock).mockResolvedValue([completed]);
    renderHome();
    await waitFor(() => expect(api.getCompetitions).toHaveBeenCalled());
    expect(screen.queryByText(/open challenges/i)).toBeNull();
    expect(screen.getByRole("link", { name: /all challenges/i })).toHaveAttribute("href", "/challenges");
  });

  it("renders the demo loop", async () => {
    (api.getCompetitions as jest.Mock).mockResolvedValue([]);
    renderHome();
    expect(screen.getByText(/plank · hold \+ form/i)).toBeInTheDocument();
    await waitFor(() => expect(api.getCompetitions).toHaveBeenCalled());
  });
});
