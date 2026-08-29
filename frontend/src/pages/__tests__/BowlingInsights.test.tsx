import React from "react";
import "@testing-library/jest-dom";
import { render, screen, waitFor } from "@testing-library/react";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import BowlingInsights from "../BowlingInsights";
import {
  fetchBowlingInsights,
  fetchBowlingGames,
  BowlingInsights as BowlingInsightsPayload,
  BowlingGameRow,
} from "../../lib/api";

jest.mock("../../config", () => ({ API_URL: "https://test-api.example" }));

jest.mock("../../components/Layout", () => ({
  __esModule: true,
  default: ({ children }: { children: React.ReactNode }) => <div>{children}</div>,
}));

jest.mock("../../lib/api", () => ({ fetchBowlingInsights: jest.fn(), fetchBowlingGames: jest.fn() }));

const mockNavigate = jest.fn();
jest.mock("react-router-dom", () => ({
  ...jest.requireActual("react-router-dom"),
  useNavigate: () => mockNavigate,
}));

const localStorageMock = (() => {
  let store: Record<string, string> = {};
  return {
    getItem: (key: string) => (key in store ? store[key] : null),
    setItem: (key: string, value: string) => {
      store[key] = String(value);
    },
    removeItem: (key: string) => {
      delete store[key];
    },
    clear: () => {
      store = {};
    },
  };
})();
Object.defineProperty(window, "localStorage", { value: localStorageMock });

const mockedFetch = fetchBowlingInsights as jest.MockedFunction<typeof fetchBowlingInsights>;

const recent: BowlingGameRow[] = [
  {
    id: "game-1",
    sheet_id: "sheet-1",
    played_on: "2026-08-27",
    game_number: 2,
    total_score: 236,
    hdcp: 37,
    has_frames: true,
    flagged: false,
  },
];

const payload: BowlingInsightsPayload & { recent: BowlingGameRow[] } = {
  games: 9,
  average: 172.4,
  high: 236,
  low: 99,
  stdev: 31.2,
  trend: { last5: 180.2, prior: 165.0, delta: 15.2 },
  slot_averages: { "1": 180.0, "2": 172.0, "3": 165.0 },
  sessions: 3,
  session_series: [
    { played_on: "2026-08-13", average: 160.0, games: 3 },
    { played_on: "2026-08-20", average: 172.0, games: 3 },
    { played_on: "2026-08-27", average: 185.0, games: 3 },
  ],
  over_200: 2,
  hdcp_latest: 37,
  frame_stats: {
    strike_pct: 0.42,
    spare_pct: 0.58,
    open_pct: 0.2,
    first_ball_avg: 8.4,
    single_pin_conversion: 0.71,
    tenth_frame_avg: 15.2,
    strike_by_frame: [1, 0.5, 0.2, 0.4, 0.6, 0.3, 0.1, 0.5, 0.4, 0.7],
    clean_games: 1,
    pins_left: 44,
    frames_analyzed: 90,
  },
  tips: [
    {
      key: "spares",
      title: "Spares are the cheapest pins you can buy",
      body: "Converting spares is worth ~5 pins a game.",
      stat: "58% spare rate",
    },
  ],
  recent,
};

const renderAt = (userId: string) =>
  render(
    <MemoryRouter initialEntries={[`/bowling/insights/${userId}`]}>
      <Routes>
        <Route path="/bowling/insights/:userId" element={<BowlingInsights />} />
      </Routes>
    </MemoryRouter>,
  );

beforeEach(() => {
  jest.clearAllMocks();
  localStorage.clear();
  mockedFetch.mockResolvedValue(payload);
});

describe("BowlingInsights", () => {
  it("renders the headline tiles", async () => {
    renderAt("user-1");
    expect(await screen.findByTestId("tile-average")).toHaveTextContent("172.4");
    expect(screen.getByTestId("tile-high")).toHaveTextContent("236");
    expect(screen.getByTestId("tile-games")).toHaveTextContent("9");
    expect(screen.getByTestId("tile-trend")).toHaveTextContent("▲");
    expect(screen.getByTestId("tile-trend")).toHaveTextContent("15.2");
  });

  it("renders the tips", async () => {
    renderAt("user-1");
    expect(
      await screen.findByText(/spares are the cheapest pins/i),
    ).toBeInTheDocument();
    expect(screen.getByText(/worth ~5 pins a game/i)).toBeInTheDocument();
    expect(screen.getByText("58% spare rate")).toBeInTheDocument();
  });

  it("renders slot averages, frame stats, and the strike heatmap", async () => {
    renderAt("user-1");
    await screen.findByTestId("tile-average");
    expect(screen.getByTestId("slot-1")).toHaveTextContent("180");
    expect(screen.getByTestId("slot-3")).toHaveTextContent("165");
    expect(screen.getByTestId("tile-strike_pct")).toHaveTextContent("42%");
    expect(screen.getByTestId("tile-spare_pct")).toHaveTextContent("58%");
    expect(screen.getByTestId("tile-first_ball_avg")).toHaveTextContent("8.4");
    expect(screen.getAllByTestId(/^strike-frame-/)).toHaveLength(10);
  });

  it("links recent games back to their sheet", async () => {
    renderAt("user-1");
    await screen.findByTestId("tile-average");
    const row = screen.getByTestId("recent-game-game-1");
    expect(row).toHaveAttribute("href", "/bowling/scoresheet/sheet-1");
    expect(row).toHaveTextContent("236");
  });

  it("hides frame stats when the backend has none", async () => {
    mockedFetch.mockResolvedValue({ ...payload, frame_stats: null });
    renderAt("user-1");
    await screen.findByTestId("tile-average");
    expect(screen.queryByTestId("tile-strike_pct")).toBeNull();
  });

  it("shows a snap CTA when there are no games", async () => {
    mockedFetch.mockResolvedValue({
      ...payload,
      games: 0,
      frame_stats: null,
      tips: [{ key: "no_games", title: "No games yet", body: "Snap a sheet.", stat: null }],
      recent: [],
    });
    renderAt("user-1");
    const cta = await screen.findByRole("link", { name: /snap a score sheet/i });
    expect(cta).toHaveAttribute("href", "/bowling/snap");
  });

  it("resolves 'me' from localStorage", async () => {
    localStorage.setItem("userId", "user-42");
    renderAt("me");
    await waitFor(() => expect(mockedFetch).toHaveBeenCalledWith("user-42"));
  });

  it("sends an unknown 'me' to profile recovery", async () => {
    renderAt("me");
    await waitFor(() => expect(mockNavigate).toHaveBeenCalledWith("/find-profile"));
    expect(mockedFetch).not.toHaveBeenCalled();
  });

  it("opens with a Tonight card for the sheet that was just confirmed", async () => {
    mockedFetch.mockResolvedValue(payload);
    (fetchBowlingGames as jest.Mock).mockResolvedValue({
      games: [
        { ...recent[0], id: "g1", sheet_id: "sheet-1", played_on: "2026-08-27", total_score: 205 },
        { ...recent[0], id: "g2", sheet_id: "sheet-9", played_on: "2026-08-29", total_score: 202 },
        { ...recent[0], id: "g3", sheet_id: "sheet-9", played_on: "2026-08-29", total_score: 157 },
        { ...recent[0], id: "g4", sheet_id: "sheet-9", played_on: "2026-08-29", total_score: 148 },
      ],
      total: 4,
    });
    render(
      <MemoryRouter initialEntries={["/bowling/insights/u1?sheet=sheet-9"]}>
        <Routes>
          <Route path="/bowling/insights/:userId" element={<BowlingInsights />} />
        </Routes>
      </MemoryRouter>,
    );
    expect(await screen.findByText("avg over 3 games")).toBeInTheDocument();
    expect(screen.getByText("169")).toBeInTheDocument();
    expect(screen.getByText(/-36 vs your average/)).toBeInTheDocument();
    expect(screen.getByText("202 high — your best game since Aug 27")).toBeInTheDocument();
    expect(fetchBowlingGames).toHaveBeenCalledWith("u1", 100);
  });
});
