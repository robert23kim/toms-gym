import React from "react";
import "@testing-library/jest-dom";
import { fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import axios from "axios";
import ChallengeDetail from "../ChallengeDetail";
import * as api from "../../lib/api";
import { uploadVideo } from "../../lib/resumableUpload";
import type { ChallengeLeaderboard } from "../../lib/types";
import {
  CONSISTENCY_COMPETITION_ID,
  consistencyLeaderboard,
  consistencyRules,
  upcomingConsistencyLeaderboard,
} from "../../__fixtures__/consistencyLeaderboard";
import { liveClubBoard, REPORTER_ID } from "../../__fixtures__/liveClubBoard";

jest.mock("../../config", () => ({ API_URL: "https://test-api.example", APP_BUILD: "test" }));
jest.mock("../../components/Layout", () => ({
  __esModule: true,
  default: ({ children }: { children: React.ReactNode }) => <div>{children}</div>,
}));
jest.mock("../../lib/resumableUpload", () => ({ uploadVideo: jest.fn() }));
jest.mock("../../lib/telemetry", () => ({ reportUploadError: jest.fn() }));
jest.mock("axios", () => ({
  __esModule: true,
  default: { get: jest.fn(), post: jest.fn(), isAxiosError: () => false },
}));
jest.mock("../../lib/api", () => ({
  ...jest.requireActual("../../lib/api"),
  getChallengeLeaderboard: jest.fn(),
  getLiftingResult: jest.fn(),
  triggerLiftingAnalysis: jest.fn(),
  fetchChampions: jest.fn(),
}));

const ID = CONSISTENCY_COMPETITION_ID;
const LIFTS = ["Situp", "Pushup", "Squat", "Plank"];
const description = `100 lifts a week. Situps, pushups, squats or planks. Hit it and the bar rises. - ${JSON.stringify({
  lifttypes: LIFTS,
  weightclasses: [],
  gender: "",
  mode: "consistency",
  rules: consistencyRules,
})}`;

const competition = {
  id: ID,
  name: "The 100 Club",
  start_date: "2026-01-01",
  end_date: "2099-12-27",
  description,
  lifttypes: LIFTS,
  mode: "consistency",
  rules: consistencyRules,
};

const mockGet = axios.get as jest.Mock;

type LiftRow = { id: string; participant_id: string; lift_type: string; created_at: string; video_url: string; status: string };

const setup = (board: ChallengeLeaderboard | null, viewer: string | null, comp: object = competition, lifts: LiftRow[] = []) => {
  (localStorage.getItem as jest.Mock).mockImplementation((key: string) => (key === "userId" ? viewer : null));
  if (board) (api.getChallengeLeaderboard as jest.Mock).mockResolvedValue(board);
  else (api.getChallengeLeaderboard as jest.Mock).mockReturnValue(new Promise(() => {}));
  (api.fetchChampions as jest.Mock).mockResolvedValue([]);
  mockGet.mockImplementation((url: string) => {
    if (url.endsWith(`/competitions/${ID}`)) return Promise.resolve({ data: { competition: comp } });
    if (url.endsWith(`/competitions/${ID}/participants`))
      return Promise.resolve({ data: { participants: [{ id: "a1" }, { id: "b1" }, { id: "c1" }] } });
    if (url.endsWith(`/competitions/${ID}/lifts`)) return Promise.resolve({ data: { lifts } });
    return Promise.reject(new Error(`unexpected GET ${url}`));
  });
  return render(
    <MemoryRouter initialEntries={[`/challenges/${ID}`]}>
      <Routes>
        <Route path="/challenges/:id" element={<ChallengeDetail />} />
      </Routes>
    </MemoryRouter>,
  );
};

describe("ChallengeDetail on a 100 Club board", () => {
  beforeEach(() => jest.clearAllMocks());

  it("renders the hero, the rules line, points rows and the week table", async () => {
    setup(consistencyLeaderboard, "a1");
    const hero = await screen.findByTestId("consistency-hero");
    expect(within(hero).getByTestId("consistency-week-line")).toHaveTextContent("Week 3 of 8 · 4 days left");
    expect(within(hero).getByTestId("consistency-ring-count")).toHaveTextContent("42 / 150");
    expect(within(hero).getByTestId("consistency-streak")).toHaveTextContent("2-week streak");
    expect(within(hero).getByTestId("consistency-leader-Situp")).toHaveTextContent(/leading/i);

    expect(screen.getByTestId("status-pill")).toHaveTextContent(/^Ongoing · ends Sun 27 Dec$/);
    expect(screen.getByTestId("scoring-note")).toHaveTextContent(/10 s of plank/);
    expect(screen.getByTestId("podium-score-1")).toHaveTextContent("467pts");
    expect(screen.getByTestId("podium-score-2")).toHaveTextContent("330pts");
    expect(screen.queryByTestId("standing-card")).toBeNull();

    // Cy has zero points and still lists, with this week's quota.
    const cyRow = screen.getAllByTestId("leaderboard-row").find((r) => r.textContent?.includes("Cy"));
    expect(cyRow).toBeDefined();
    expect(within(cyRow!).getByTestId("row-this-week")).toHaveTextContent("0/100 this week");

    expect(screen.getAllByText("Log this week's lifts").length).toBeGreaterThan(0);

    fireEvent.click(screen.getByRole("button", { name: /Ana.*weeks/ }));
    const table = await screen.findByTestId("week-table");
    expect(within(table).getByTestId("week-row-1")).toHaveTextContent("Situp, Plank");
    expect(within(table).getByTestId("week-row-1")).toHaveTextContent("200");
    expect(within(table).getByTestId("week-row-2")).toHaveTextContent("225");
    expect(within(table).getByTestId("week-row-3")).toHaveTextContent("now");
    expect(within(table).getByTestId("week-bonus-3")).toHaveTextContent("Situp · locks Sun");
    expect(within(table).getByTestId("week-types-1")).toHaveTextContent("Situp 45 · Pushup 43 · Plank 24 (240 s)");
    expect(mockGet).not.toHaveBeenCalledWith(expect.stringContaining("/users/a1/lifts"));
  });

  it("shows anonymous visitors the week line and leaders without a ring", async () => {
    setup(consistencyLeaderboard, null);
    const hero = await screen.findByTestId("consistency-hero");
    expect(within(hero).getByTestId("consistency-week-line")).toHaveTextContent("Week 3 of 8");
    expect(within(hero).getByTestId("consistency-leader-Plank")).toHaveTextContent("Ben 100 s");
    expect(within(hero).queryByTestId("consistency-ring-count")).toBeNull();
    expect(screen.getByTestId("you-row-unknown")).toBeInTheDocument();
    expect(screen.queryByText("Not logged yet")).toBeNull();
  });

  it("on the live board with the reporter's row but no saved userId, asks who he is instead of saying nothing is logged", async () => {
    setup(liveClubBoard, null);
    await screen.findByTestId("podium");
    const unknown = screen.getByTestId("you-row-unknown");
    expect(screen.queryByText("Not logged yet")).toBeNull();
    expect(screen.queryByTestId("you-row")).toBeNull();
    expect(unknown.closest("a")).toHaveAttribute(
      "href",
      `/find-profile?next=${encodeURIComponent(`/challenges/${ID}`)}`,
    );
  });

  it("on the live board with the reporter's userId, shows his week and no empty-state row", async () => {
    setup(liveClubBoard, REPORTER_ID);
    const hero = await screen.findByTestId("consistency-hero");
    expect(within(hero).getByTestId("consistency-ring-count")).toHaveTextContent("147 / 125");
    expect(screen.queryByTestId("you-row-unknown")).toBeNull();
    expect(screen.queryByText("Not logged yet")).toBeNull();
  });

  it("keeps Not logged yet for a known viewer with no row and nothing analysing", async () => {
    setup(liveClubBoard, "someone-new");
    await screen.findByTestId("podium");
    expect(screen.getByTestId("you-row")).toHaveTextContent("Not logged yet");
    expect(screen.queryByTestId("you-row-unknown")).toBeNull();
  });

  it("says the upload is analysing for a known viewer with no row and a processing attempt", async () => {
    (api.getLiftingResult as jest.Mock).mockResolvedValue({ processing_status: "processing" });
    const lifts: LiftRow[] = [
      { id: "new-1", participant_id: "someone-new", lift_type: "Squat", created_at: "2026-11-13T12:00:00+00:00", video_url: "https://storage.example/new-1.mp4", status: "pending" },
    ];
    setup(liveClubBoard, "someone-new", competition, lifts);
    await waitFor(() => expect(screen.getByTestId("you-row")).toHaveTextContent("Analysing your upload…"));
    expect(screen.getByTestId("you-row")).not.toHaveTextContent("Not logged yet");
  });

  it("remembers the uploader from the inline form's response when this browser had no userId", async () => {
    const lifts: LiftRow[] = [];
    (uploadVideo as jest.Mock).mockImplementation(async () => {
      lifts.push({ id: "new-1", participant_id: "u-new", lift_type: "Squat", created_at: "2026-11-13T12:00:00+00:00", video_url: "https://storage.example/new-1.mp4", status: "pending" });
      return { url: "https://storage.example/new-1.mp4", attempt_id: "new-1", user_id: "u-new" };
    });
    (api.triggerLiftingAnalysis as jest.Mock).mockResolvedValue({});
    (api.getLiftingResult as jest.Mock).mockResolvedValue({ processing_status: "processing" });
    setup(liveClubBoard, null, competition, lifts);
    await screen.findByTestId("you-row-unknown");
    fireEvent.click(screen.getAllByText("Log this week's lifts")[0]);
    const form = (await screen.findByText("Lift Type")).closest("form")!;
    fireEvent.change(form.querySelector('input[type="email"]')!, { target: { value: "new@example.com" } });
    fireEvent.change(form.querySelector('input[type="file"]')!, { target: { files: [new File(["x"], "s.mp4", { type: "video/mp4" })] } });
    fireEvent.submit(form);
    await waitFor(() => expect(localStorage.setItem).toHaveBeenCalledWith("userId", "u-new"));
    await waitFor(() => expect(screen.getByTestId("you-row")).toHaveTextContent("Analysing your upload…"));
    expect(screen.queryByTestId("you-row-unknown")).toBeNull();
  });

  it("does not replace a different saved userId with the uploader's", async () => {
    (uploadVideo as jest.Mock).mockResolvedValue({ url: "https://storage.example/new-1.mp4", attempt_id: "new-1", user_id: "u-other" });
    (api.triggerLiftingAnalysis as jest.Mock).mockResolvedValue({});
    (api.getLiftingResult as jest.Mock).mockResolvedValue({ processing_status: "processing" });
    setup(liveClubBoard, "someone-new");
    await screen.findByTestId("podium");
    fireEvent.click(screen.getAllByText("Log this week's lifts")[0]);
    const form = (await screen.findByText("Lift Type")).closest("form")!;
    fireEvent.change(form.querySelector('input[type="email"]')!, { target: { value: "other@example.com" } });
    fireEvent.change(form.querySelector('input[type="file"]')!, { target: { files: [new File(["x"], "s.mp4", { type: "video/mp4" })] } });
    fireEvent.submit(form);
    await waitFor(() => expect(uploadVideo).toHaveBeenCalled());
    await waitFor(() => expect(api.triggerLiftingAnalysis).toHaveBeenCalled());
    expect(localStorage.setItem).not.toHaveBeenCalledWith("userId", expect.anything());
  });

  it("drops the Everyone else header when the podium holds everyone", async () => {
    setup({ ...consistencyLeaderboard, rows: consistencyLeaderboard.rows.slice(0, 2) }, null);
    await screen.findByTestId("consistency-hero");
    expect(await screen.findByTestId("you-row-unknown")).toBeInTheDocument();
    expect(screen.queryByText("Everyone else")).toBeNull();
    expect(screen.queryByTestId("leaderboard-header")).toBeNull();
  });

  it("shows the club's end day in the status pill before the leaderboard arrives", async () => {
    setup(null, null);
    expect(await screen.findByTestId("status-pill")).toHaveTextContent(/^Ongoing · ends Sun 27 Dec$/);
  });

  it("pins the phone upload button above the bottom tab bar", async () => {
    setup(null, null);
    const cta = await screen.findByTestId("mobile-upload-cta");
    expect(cta.className).toMatch(/\bfixed\b/);
    expect(cta.className).not.toMatch(/\bbottom-0\b/);
    expect(cta.className).toMatch(/\babove-tab-bar\b/);
  });

  it("keeps the day countdown on a legacy challenge", async () => {
    const legacyDescription = `Hold it. - ${JSON.stringify({ lifttypes: ["Plank"], weightclasses: [], gender: "" })}`;
    setup(null, null, { id: ID, name: "Plank Off", start_date: "2026-01-01", end_date: "2099-12-27", description: legacyDescription, lifttypes: ["Plank"] });
    expect(await screen.findByTestId("status-pill")).toHaveTextContent(/^Ongoing · \d+d left$/);
  });

  it("drops the Everyone else header on a legacy board whose podium holds everyone", async () => {
    const legacyDescription = `Hold it. - ${JSON.stringify({ lifttypes: ["Plank"], weightclasses: [], gender: "" })}`;
    const legacyBoard: ChallengeLeaderboard = {
      competition_id: ID,
      metric: "time",
      lift_types: ["Plank"],
      momentum: { joined: 1, uploaded_today: 0 },
      rows: [
        {
          rank: 1, user_id: "a1", name: "Ana", score: 61.2, best_by_lift: { Plank: 61.2 }, form_score: 88,
          steadiness: 2.1, attempt_id: "a1-best", clip_url: null, thumbnail_url: null, date: "2026-08-28",
          weight_class: null, gender: null, attempt_count: 1, history: [{ score: 61.2, date: "2026-08-28" }],
        },
      ],
    };
    setup(legacyBoard, null, { id: ID, name: "Plank Off", start_date: "2026-01-01", end_date: "2099-12-27", description: legacyDescription, lifttypes: ["Plank"] });
    await screen.findByTestId("podium");
    expect(await screen.findByTestId("you-row-unknown")).toBeInTheDocument();
    expect(screen.queryByText("Everyone else")).toBeNull();
    expect(screen.queryByTestId("leaderboard-header")).toBeNull();
    expect(screen.queryByTestId("consistency-hero")).toBeNull();
  });

  it("explains a points tie under the podium", async () => {
    const [ana, ben, cy] = consistencyLeaderboard.rows;
    setup({ ...consistencyLeaderboard, rows: [ana, { ...ben, score: ana.score, streak: 2, weeks_met: 2 }, cy] }, null);
    expect(await screen.findByTestId("consistency-tie")).toHaveTextContent(
      "Ana and Ben are tied on points; more lifts this week puts Ana ahead.",
    );
  });

  it("shows no tie line when points differ", async () => {
    setup(consistencyLeaderboard, null);
    await screen.findByTestId("podium");
    expect(screen.queryByTestId("consistency-tie")).toBeNull();
  });

  it("lists warm-up rows before week 1 instead of the empty podium state", async () => {
    setup(upcomingConsistencyLeaderboard, "a1");
    const hero = await screen.findByTestId("consistency-hero");
    expect(within(hero).getByTestId("consistency-week-line")).toHaveTextContent("Starts Monday 2 Nov");
    expect(screen.queryByText(/No entries yet/)).toBeNull();
    const you = screen.getByTestId("you-row");
    expect(within(you).getByTestId("row-this-week")).toHaveTextContent("0/100 this week · 20 warm-up");
    expect(screen.queryByTestId("podium")).toBeNull();
  });

  it("offers exactly the four lifts, hides weight for bodyweight and allows 0 for squats", async () => {
    setup(consistencyLeaderboard, "a1");
    await screen.findByTestId("consistency-hero");
    fireEvent.click(screen.getAllByText("Log this week's lifts")[0]);
    const select = (await screen.findByText("Lift Type")).parentElement!.querySelector("select")!;
    const options = Array.from(select.querySelectorAll("option")).map((o) => o.value);
    expect([...options].sort()).toEqual(["Plank", "Pushup", "Situp", "Squat"]);
    for (const lift of ["Situp", "Pushup", "Plank"]) {
      fireEvent.change(select, { target: { value: lift } });
      expect(screen.queryByText("Weight (lbs)")).toBeNull();
    }
    fireEvent.change(select, { target: { value: "Squat" } });
    const weight = screen.getByPlaceholderText("Enter weight") as HTMLInputElement;
    expect(weight.value).toBe("0");
    expect(weight.min).toBe("0");
    await waitFor(() => expect(api.getChallengeLeaderboard).toHaveBeenCalled());
  });

  it("opens on an air squat at weight 0 and posts 0 for a bodyweight lift", async () => {
    (uploadVideo as jest.Mock).mockRejectedValue(new Error("stop after the post"));
    setup(consistencyLeaderboard, "a1");
    await screen.findByTestId("consistency-hero");
    fireEvent.click(screen.getAllByText("Log this week's lifts")[0]);
    const select = (await screen.findByText("Lift Type")).parentElement!.querySelector("select")!;
    expect(select.value).toBe("Squat");
    expect((screen.getByPlaceholderText("Enter weight") as HTMLInputElement).value).toBe("0");

    fireEvent.change(select, { target: { value: "Situp" } });
    const form = select.closest("form")!;
    fireEvent.change(form.querySelector('input[type="email"]')!, { target: { value: "ana@example.com" } });
    const file = new File(["x"], "situps.mp4", { type: "video/mp4" });
    fireEvent.change(form.querySelector('input[type="file"]')!, { target: { files: [file] } });
    fireEvent.submit(form);
    await waitFor(() => expect(uploadVideo).toHaveBeenCalled());
    expect((uploadVideo as jest.Mock).mock.calls[0][1]).toMatchObject({ lift_type: "Situp", weight: "0" });
  });

  it("lists the viewer's uploads of the live week behind a tap, with lifts from their analysis", async () => {
    const lift = (id: string, created_at: string, lift_type: string, participant_id = "a1"): LiftRow => ({
      id,
      participant_id,
      lift_type,
      created_at,
      video_url: `https://storage.example/${id}.mp4`,
      status: "completed",
    });
    const lifts = [
      lift("w3-situp", "2026-11-17T18:24:00+00:00", "Situp"),
      lift("w3-plank", "2026-11-16T12:21:00+00:00", "Plank"),
      lift("w3-pending", "2026-11-18T12:00:00+00:00", "Pushup"),
      lift("w2-old", "2026-11-10T12:00:00+00:00", "Pushup"),
      lift("w3-ben", "2026-11-17T12:00:00+00:00", "Situp", "b1"),
    ];
    (api.getLiftingResult as jest.Mock).mockImplementation(async (attemptId: string) => {
      if (attemptId === "w3-situp")
        return { processing_status: "completed", report: { lift_type: "Situp", total_reps: 4, rep_metrics: [{ form_score: 90 }, { form_score: 80 }, { form_score: 40 }, { form_score: 30 }] } };
      if (attemptId === "w3-plank") return { processing_status: "completed", report: { lift_type: "Plank", total_in_plank_s: 82.79 } };
      if (attemptId === "w2-old") return { processing_status: "completed", report: { lift_type: "Pushup", total_reps: 30 } };
      return { processing_status: "processing" };
    });
    setup(consistencyLeaderboard, "a1", competition, lifts);
    const toggle = await screen.findByTestId("consistency-uploads-toggle");
    await waitFor(() => expect(toggle).toHaveTextContent("This week's uploads · 3"));
    fireEvent.click(toggle);
    const list = await screen.findByTestId("consistency-uploads");
    await waitFor(() => expect(within(list).getByTestId("consistency-upload-w3-situp")).toHaveTextContent("+3"));
    expect(within(list).getByTestId("consistency-upload-w3-plank")).toHaveTextContent("Plank82.8 s7:21 am+8");
    expect(within(list).getByTestId("consistency-upload-w3-pending")).toHaveTextContent("analysing");
    expect(within(list).queryByTestId("consistency-upload-w2-old")).toBeNull();
    expect(within(list).queryByTestId("consistency-upload-w3-ben")).toBeNull();
    expect(within(list).getByTestId("consistency-upload-w3-situp").closest("a")).toHaveAttribute(
      "href",
      `/challenges/${ID}/participants/a1/video/w3-situp`,
    );
  });
});
