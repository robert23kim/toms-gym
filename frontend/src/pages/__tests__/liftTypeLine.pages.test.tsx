import React from "react";
import "@testing-library/jest-dom";
import { fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import axios from "axios";
import VideoPlayer from "../VideoPlayer";
import AnalysisStatus from "../AnalysisStatus";
import * as api from "../../lib/api";
import { CONSISTENCY_COMPETITION_ID, consistencyLeaderboard } from "../../__fixtures__/consistencyLeaderboard";

jest.mock("../../config", () => ({ API_URL: "https://test-api.example", PROD_API_URL: "https://test-api.example" }));
jest.mock("../../components/Layout", () => ({
  __esModule: true,
  default: ({ children }: { children: React.ReactNode }) => <div>{children}</div>,
}));
jest.mock("axios", () => ({
  __esModule: true,
  default: { get: jest.fn(), post: jest.fn(), isAxiosError: () => false },
}));
jest.mock("../../lib/api", () => ({
  ...jest.requireActual("../../lib/api"),
  getChallengeLeaderboard: jest.fn(),
  getLiftingResult: jest.fn(),
  triggerLiftingAnalysis: jest.fn(),
  changeLiftType: jest.fn(),
}));
jest.mock("../../lib/share", () => ({ shareResult: jest.fn() }));

const ID = CONSISTENCY_COMPETITION_ID;
const OWNER = "b1";

const result = (over: object = {}) => ({
  id: "lr-1",
  attempt_id: "v1",
  user_id: OWNER,
  competition_id: ID,
  processing_status: "completed",
  lift_type: "Pushup",
  lift_type_source: "auto",
  lift_type_confidence: 0.91,
  needs_lift_type: false,
  report: { lift_type: "pushup", total_reps: 12, overall_grade: "B", rep_metrics: [], insights: [] },
  ...over,
});

const routeGets = (res: object, attempt: object = {}) => {
  (api.getChallengeLeaderboard as jest.Mock).mockResolvedValue(consistencyLeaderboard);
  (api.getLiftingResult as jest.Mock).mockResolvedValue(res);
  (axios.get as jest.Mock).mockImplementation((url: string) => {
    if (url.endsWith(`/competitions/${ID}`))
      return Promise.resolve({ data: { competition: { id: ID, name: "The 100 Club", start_date: "2026-01-01", end_date: "2099-12-27" } } });
    if (url.includes("/attempts/v1"))
      return Promise.resolve({ data: { id: "v1", lift_type: "Pushup", weight: 0, participant_name: "Ben", status: "completed", ...attempt } });
    if (url.includes("/lifting/result/v1")) return Promise.resolve({ data: res });
    return Promise.resolve({ data: { lifts: [] } });
  });
};

const viewer = (id: string | null) =>
  (localStorage.getItem as jest.Mock).mockImplementation((k: string) => (k === "userId" ? id : null));

const openVideo = () =>
  render(
    <MemoryRouter initialEntries={[`/challenges/${ID}/participants/${OWNER}/video/v1`]}>
      <Routes>
        <Route path="/challenges/:id/participants/:participantId/video/:videoId" element={<VideoPlayer />} />
      </Routes>
    </MemoryRouter>,
  );

const openStatus = () =>
  render(
    <MemoryRouter initialEntries={[`/status/v1?challenge=${ID}`]}>
      <Routes>
        <Route path="/status/:attemptId" element={<AnalysisStatus kind="lifting" />} />
      </Routes>
    </MemoryRouter>,
  );

describe("result line on the challenge video page", () => {
  beforeEach(() => jest.clearAllMocks());

  test.each([
    ["automatic", {}, /^Counted as Pushups · Automatic\s*Change$/],
    ["manual", { lift_type_source: "user", lift_type_confidence: null }, /^Counted as Pushups\s*Change$/],
    ["confirm", { lift_type_confidence: 0.4 }, /^Is this a pushup\?\s*Yes\s*Change$/],
  ])("%s state for the owner", async (state, over, text) => {
    viewer(OWNER);
    routeGets(result(over));
    openVideo();
    const line = await screen.findByTestId("lift-type-line");
    expect(line).toHaveAttribute("data-state", state);
    expect(line).toHaveTextContent(text);
  });

  test("Change is owner-only", async () => {
    viewer("a1");
    routeGets(result());
    openVideo();
    const line = await screen.findByTestId("lift-type-line");
    expect(within(line).queryByRole("button")).toBeNull();
  });

  test("no line while the backend does not report the source", async () => {
    viewer(OWNER);
    routeGets(result({ lift_type_source: undefined, lift_type_confidence: undefined, needs_lift_type: undefined }));
    openVideo();
    await screen.findByTestId("consistency-result");
    expect(screen.queryByTestId("lift-type-line")).toBeNull();
  });

  test("an unknown type reads as a lift in the title and the line asks which", async () => {
    viewer(OWNER);
    routeGets(
      result({ lift_type: "Auto", needs_lift_type: true, lift_type_confidence: 0, report: { lift_type: "auto" } }),
      { lift_type: "Auto" },
    );
    openVideo();
    expect(await screen.findByTestId("lift-type-line")).toHaveTextContent("Which lift is this?");
    expect(screen.getByRole("heading", { level: 1 })).toHaveTextContent(/Ben's lift$/);
  });

  test("a confirmed change drops the page back into analysing", async () => {
    viewer(OWNER);
    routeGets(result());
    (api.changeLiftType as jest.Mock).mockResolvedValue({ attempt_id: "v1", lift_type: "Situp", status: "queued" });
    openVideo();
    fireEvent.click(within(await screen.findByTestId("lift-type-line")).getByRole("button", { name: "Change" }));
    fireEvent.click(screen.getByRole("radio", { name: "Situps" }));
    fireEvent.click(screen.getByRole("button", { name: "Re-analyse" }));
    expect(await screen.findByText("Analyzing your form...")).toBeInTheDocument();
    expect(api.changeLiftType).toHaveBeenCalledWith("v1", "Situp", OWNER);
    expect(screen.getByRole("heading", { level: 1 })).toHaveTextContent(/Ben's Situp$/);
    expect(screen.queryByTestId("consistency-result")).toBeNull();
  });
});

describe("result line on the status page", () => {
  beforeEach(() => jest.clearAllMocks());

  test("automatic state under the title, owner gets Change", async () => {
    viewer(OWNER);
    routeGets(result());
    openStatus();
    const line = await screen.findByTestId("lift-type-line");
    expect(line).toHaveAttribute("data-state", "automatic");
    expect(within(line).getByRole("button", { name: "Change" })).toBeInTheDocument();
  });

  test("a visitor with no stored id gets no Change", async () => {
    viewer(null);
    routeGets(result());
    openStatus();
    const line = await screen.findByTestId("lift-type-line");
    expect(within(line).queryByRole("button")).toBeNull();
  });

  test("an undetected type asks which lift even with no score to reveal", async () => {
    viewer(OWNER);
    routeGets(result({ lift_type: "Auto", needs_lift_type: true, lift_type_confidence: 0, report: { lift_type: "auto" } }));
    openStatus();
    expect(await screen.findByTestId("lift-type-line")).toHaveTextContent("Which lift is this?");
  });

  test("a confirmed change returns to the queued state", async () => {
    viewer(OWNER);
    routeGets(result());
    (api.changeLiftType as jest.Mock).mockResolvedValue({ attempt_id: "v1", lift_type: "Squat", status: "queued" });
    openStatus();
    fireEvent.click(within(await screen.findByTestId("lift-type-line")).getByRole("button", { name: "Change" }));
    fireEvent.click(screen.getByRole("radio", { name: "Squats" }));
    fireEvent.click(screen.getByRole("button", { name: "Re-analyse" }));
    expect(await screen.findByText("Queued for analysis")).toBeInTheDocument();
    await waitFor(() => expect(screen.queryByTestId("lift-type-line")).toBeNull());
  });
});
