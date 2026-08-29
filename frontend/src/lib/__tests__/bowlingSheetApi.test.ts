import axios from "axios";
import {
  uploadBowlingSheet,
  fetchBowlingSheet,
  confirmBowlingSheet,
  deleteBowlingSheet,
  fetchBowlingGames,
  fetchBowlingInsights,
  BowlingSheet,
} from "../api";

jest.mock("../../config", () => ({ API_URL: "https://test-api.example" }));
jest.mock("axios");

const mockedAxios = axios as jest.Mocked<typeof axios>;

const sheet: BowlingSheet = {
  sheet_id: "sheet-1",
  sheet_type: "night",
  played_on: "2026-08-28",
  image_url: "https://cdn.example/sheet.jpg",
  team_name: "Gutter Gang",
  processing_status: "parsed",
  players: [
    {
      name: "TOM",
      games: [
        {
          game_number: 1,
          total_score: 163,
          hdcp: 37,
          frames: null,
          computed_total: null,
          flagged: false,
          flag_reason: null,
          confidence: 0.94,
        },
      ],
    },
  ],
  flagged_count: 0,
};

beforeEach(() => jest.clearAllMocks());

describe("bowling score-sheet api", () => {
  it("posts an upload as multipart and returns the sheet", async () => {
    mockedAxios.post.mockResolvedValue({ data: sheet });
    const form = new FormData();
    form.append("sheet_type", "night");
    await expect(uploadBowlingSheet(form)).resolves.toEqual(sheet);
    expect(mockedAxios.post).toHaveBeenCalledWith(
      "https://test-api.example/bowling/scoresheet/upload",
      form,
      { headers: { "Content-Type": "multipart/form-data" } },
    );
  });

  it("fetches a sheet by id", async () => {
    mockedAxios.get.mockResolvedValue({ data: sheet });
    await expect(fetchBowlingSheet("sheet-1")).resolves.toEqual(sheet);
    expect(mockedAxios.get).toHaveBeenCalledWith(
      "https://test-api.example/bowling/scoresheet/sheet-1",
    );
  });

  it("puts the confirm body with the claimed player", async () => {
    mockedAxios.put.mockResolvedValue({ data: { ...sheet, processing_status: "confirmed" } });
    const body = {
      claim_player: "TOM",
      players: [{ name: "TOM", games: [{ game_number: 1, total_score: 163, hdcp: 37 }] }],
    };
    const result = await confirmBowlingSheet("sheet-1", body);
    expect(result.processing_status).toBe("confirmed");
    expect(mockedAxios.put).toHaveBeenCalledWith(
      "https://test-api.example/bowling/scoresheet/sheet-1/confirm",
      body,
    );
  });

  it("deletes a sheet", async () => {
    mockedAxios.delete.mockResolvedValue({ data: null });
    await deleteBowlingSheet("sheet-1");
    expect(mockedAxios.delete).toHaveBeenCalledWith(
      "https://test-api.example/bowling/scoresheet/sheet-1",
    );
  });

  it("passes pagination through to the games list", async () => {
    mockedAxios.get.mockResolvedValue({
      data: { games: [], total: 0, limit: 5, offset: 10 },
    });
    await fetchBowlingGames("user-1", 5, 10);
    expect(mockedAxios.get).toHaveBeenCalledWith(
      "https://test-api.example/bowling/games?user_id=user-1&limit=5&offset=10",
    );
  });

  it("defaults the games page size to 20", async () => {
    mockedAxios.get.mockResolvedValue({
      data: { games: [], total: 0, limit: 20, offset: 0 },
    });
    await fetchBowlingGames("user-1");
    expect(mockedAxios.get).toHaveBeenCalledWith(
      "https://test-api.example/bowling/games?user_id=user-1&limit=20&offset=0",
    );
  });

  it("fetches insights for a user", async () => {
    mockedAxios.get.mockResolvedValue({ data: { games: 0, tips: [], recent: [] } });
    await fetchBowlingInsights("user-1");
    expect(mockedAxios.get).toHaveBeenCalledWith(
      "https://test-api.example/bowling/insights/user-1",
    );
  });
});
