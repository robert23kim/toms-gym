import React from "react";
import "@testing-library/jest-dom";
import { render, screen, fireEvent, waitFor, within } from "@testing-library/react";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import axios from "axios";
import BowlingSheetReview from "../BowlingSheetReview";
import {
  fetchBowlingSheet,
  confirmBowlingSheet,
  deleteBowlingSheet,
  BowlingSheet,
  BowlingSheetGame,
} from "../../lib/api";

jest.mock("../../config", () => ({ API_URL: "https://test-api.example" }));

jest.mock("../../components/Layout", () => ({
  __esModule: true,
  default: ({ children }: { children: React.ReactNode }) => <div>{children}</div>,
}));

jest.mock("../../lib/api", () => ({
  fetchBowlingSheet: jest.fn(),
  confirmBowlingSheet: jest.fn(),
  deleteBowlingSheet: jest.fn(),
}));

jest.mock("axios");

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

const mockedFetch = fetchBowlingSheet as jest.MockedFunction<typeof fetchBowlingSheet>;
const mockedConfirm = confirmBowlingSheet as jest.MockedFunction<typeof confirmBowlingSheet>;
const mockedDelete = deleteBowlingSheet as jest.MockedFunction<typeof deleteBowlingSheet>;
const mockedAxios = axios as jest.Mocked<typeof axios>;

const game = (
  gameNumber: number,
  total: number | null,
  overrides: Partial<BowlingSheetGame> = {},
): BowlingSheetGame => ({
  game_number: gameNumber,
  total_score: total,
  hdcp: 37,
  frames: null,
  computed_total: null,
  flagged: false,
  flag_reason: null,
  confidence: 0.95,
  ...overrides,
});

const nightSheet: BowlingSheet = {
  sheet_id: "sheet-1",
  sheet_type: "night",
  played_on: "2026-08-28",
  image_url: "https://cdn.example/night.jpg",
  team_name: "Gutter Gang",
  processing_status: "parsed",
  flagged_count: 1,
  players: [
    { name: "TOM", games: [game(1, 164), game(2, 236), game(3, 196)] },
    { name: "CHRIS", games: [game(1, 178), game(2, 145), game(3, 201)] },
    { name: "PAT", games: [game(1, 120), game(2, 133), game(3, 99)] },
    {
      name: "ANDREW",
      games: [
        game(1, 225),
        game(2, 205, { flagged: true, flag_reason: "glare on the totals column" }),
        game(3, 176),
      ],
    },
  ],
};

const gameSheet: BowlingSheet = {
  sheet_id: "sheet-2",
  sheet_type: "game",
  played_on: "2026-08-28",
  image_url: null,
  team_name: null,
  processing_status: "parsed",
  flagged_count: 0,
  players: [
    {
      name: "TOM",
      games: [
        game(1, 163, {
          frames: [
            ["X"], ["8", "1"], ["X"], ["9", "/"], ["X"],
            ["6", "3"], ["8", "/"], ["X"], ["9", "-"], ["7", "/", "9"],
          ],
          computed_total: 163,
        }),
      ],
    },
  ],
};

const renderReview = () =>
  render(
    <MemoryRouter initialEntries={["/bowling/scoresheet/sheet-1"]}>
      <Routes>
        <Route path="/bowling/scoresheet/:id" element={<BowlingSheetReview />} />
      </Routes>
    </MemoryRouter>,
  );

const playerCard = (name: string) => screen.getByTestId(`player-${name}`);

beforeEach(() => {
  jest.clearAllMocks();
  localStorage.clear();
  localStorage.setItem("userId", "user-1");
  mockedAxios.get.mockResolvedValue({ data: { user: { name: "Tom Oka" } } });
  mockedFetch.mockResolvedValue(nightSheet);
  mockedConfirm.mockImplementation(async () => ({
    ...nightSheet,
    processing_status: "confirmed",
  }));
  mockedDelete.mockResolvedValue(undefined);
});

describe("BowlingSheetReview — night sheet", () => {
  it("renders every parsed player with their series scratch and total", async () => {
    renderReview();
    await screen.findByTestId("player-TOM");
    ["TOM", "CHRIS", "PAT", "ANDREW"].forEach((name) => {
      expect(playerCard(name)).toBeInTheDocument();
    });
    expect(within(playerCard("TOM")).getByTestId("scratch")).toHaveTextContent("596");
    expect(within(playerCard("TOM")).getByTestId("total")).toHaveTextContent("707");
  });

  it("recomputes scratch and total when a game is edited", async () => {
    renderReview();
    await screen.findByTestId("player-TOM");
    fireEvent.change(screen.getByLabelText("TOM game 2"), { target: { value: "200" } });
    expect(within(playerCard("TOM")).getByTestId("scratch")).toHaveTextContent("560");
    expect(within(playerCard("TOM")).getByTestId("total")).toHaveTextContent("671");
  });

  it("shows the flag reason on a flagged row", async () => {
    renderReview();
    await screen.findByTestId("player-ANDREW");
    expect(
      within(playerCard("ANDREW")).getByText(/glare on the totals column/i),
    ).toBeInTheDocument();
  });

  it("preselects the player matching the signed-in profile name", async () => {
    renderReview();
    await screen.findByTestId("player-TOM");
    await waitFor(() =>
      expect(screen.getByLabelText("Claim TOM")).toBeChecked(),
    );
  });

  it("confirms with the claimed player and lands on insights", async () => {
    renderReview();
    await screen.findByTestId("player-TOM");
    fireEvent.click(screen.getByLabelText("Claim CHRIS"));
    fireEvent.click(screen.getByRole("button", { name: /save these scores/i }));

    await waitFor(() => expect(mockedConfirm).toHaveBeenCalled());
    const [sheetId, body] = mockedConfirm.mock.calls[0];
    expect(sheetId).toBe("sheet-1");
    expect(body.claim_player).toBe("CHRIS");
    expect(body.players).toHaveLength(4);
    expect(body.players[0].games[0]).toEqual({
      game_number: 1,
      total_score: 164,
      hdcp: 37,
      frames: null,
    });
    expect(mockNavigate).toHaveBeenCalledWith("/bowling/insights/user-1?sheet=sheet-1");
  });

  it("returns to the hub when nothing is claimed", async () => {
    renderReview();
    await screen.findByTestId("player-TOM");
    fireEvent.click(screen.getByLabelText("Claim nobody"));
    fireEvent.click(screen.getByRole("button", { name: /save these scores/i }));
    await waitFor(() => expect(mockedConfirm).toHaveBeenCalled());
    expect(mockedConfirm.mock.calls[0][1].claim_player).toBeNull();
    expect(mockNavigate).toHaveBeenCalledWith("/bowl");
  });

  it("adds a blank player row", async () => {
    renderReview();
    await screen.findByTestId("player-TOM");
    fireEvent.click(screen.getByRole("button", { name: /add player/i }));
    expect(screen.getAllByLabelText(/player name/i)).toHaveLength(5);
  });

  it("deletes only after an inline second confirmation", async () => {
    renderReview();
    await screen.findByTestId("player-TOM");
    fireEvent.click(screen.getByRole("button", { name: /^delete sheet$/i }));
    expect(mockedDelete).not.toHaveBeenCalled();
    fireEvent.click(screen.getByRole("button", { name: /really delete/i }));
    await waitFor(() => expect(mockedDelete).toHaveBeenCalledWith("sheet-1"));
    expect(mockNavigate).toHaveBeenCalledWith("/bowl");
  });

  it("opens the photo in a lightbox and closes it on Escape", async () => {
    renderReview();
    await screen.findByTestId("player-TOM");
    fireEvent.click(screen.getByRole("button", { name: /view the score sheet photo/i }));
    expect(screen.getByRole("dialog")).toBeInTheDocument();
    fireEvent.keyDown(window, { key: "Escape" });
    await waitFor(() => expect(screen.queryByRole("dialog")).toBeNull());
  });
});

describe("BowlingSheetReview — failed sheet", () => {
  it("renders one blank player row", async () => {
    mockedFetch.mockResolvedValue({
      ...nightSheet,
      processing_status: "failed",
      players: [],
      flagged_count: 0,
      error_message: "no players found",
    });
    renderReview();
    expect(await screen.findByText(/couldn't read/i)).toBeInTheDocument();
    expect(screen.getAllByLabelText(/player name/i)).toHaveLength(1);
  });
});

describe("BowlingSheetReview — single game sheet", () => {
  beforeEach(() => {
    mockedFetch.mockResolvedValue(gameSheet);
    mockedConfirm.mockImplementation(async () => ({
      ...gameSheet,
      processing_status: "confirmed",
    }));
  });

  it("renders ten frame cells with the running score", async () => {
    renderReview();
    await screen.findByTestId("player-TOM");
    expect(screen.getAllByLabelText(/^TOM frame \d+$/)).toHaveLength(10);
    expect(screen.getByLabelText("TOM frame 1")).toHaveValue("X");
    expect(screen.getByTestId("cumulative-0")).toHaveTextContent("19");
    expect(screen.getByTestId("cumulative-9")).toHaveTextContent("163");
  });

  it("rescores the strip as frames are edited", async () => {
    renderReview();
    await screen.findByTestId("player-TOM");
    fireEvent.change(screen.getByLabelText("TOM frame 2"), { target: { value: "9/" } });
    expect(screen.getByTestId("cumulative-0")).toHaveTextContent("20");
    expect(screen.getByTestId("cumulative-1")).toHaveTextContent("40");
  });

  it("flags an impossible frame and blocks saving", async () => {
    renderReview();
    await screen.findByTestId("player-TOM");
    fireEvent.change(screen.getByLabelText("TOM frame 2"), { target: { value: "99" } });
    // Shown twice on purpose: under the strip and in the save-blocked banner.
    expect(screen.getAllByText(/exceeds 10/i)).toHaveLength(2);
    expect(screen.getByRole("button", { name: /save these scores/i })).toBeDisabled();
  });

  it("posts the edited frames on confirm", async () => {
    renderReview();
    await screen.findByTestId("player-TOM");
    fireEvent.change(screen.getByLabelText("TOM frame 2"), { target: { value: "9/" } });
    fireEvent.click(screen.getByRole("button", { name: /save these scores/i }));
    await waitFor(() => expect(mockedConfirm).toHaveBeenCalled());
    const posted = mockedConfirm.mock.calls[0][1].players[0].games[0];
    expect(posted.frames?.[1]).toEqual(["9", "/"]);
    expect(posted.total_score).toBe(175);
  });
});
