import React from "react";
import "@testing-library/jest-dom";
import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import axios from "axios";
import VideoPlayer from "../VideoPlayer";
import * as api from "../../lib/api";
import * as share from "../../lib/share";
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
}));
jest.mock("../../lib/share", () => ({ shareResult: jest.fn() }));

const ID = CONSISTENCY_COMPETITION_ID;

const liftingResult = {
  id: "lr-1",
  attempt_id: "v1",
  processing_status: "completed",
  report: {
    lift_type: "Situp",
    total_reps: 4,
    overall_grade: "C",
    overall_score: 62,
    camera_view: "side",
    active_arm: "both",
    insights: ["Focus on form for reps 3, 4"],
    rep_metrics: [90, 80, 40, 30].map((form_score, i) => ({
      rep_number: i + 1,
      elbow_angle_range: [60, 150],
      tempo_ratio: 1,
      elbow_drift_pct: 0,
      body_sway_pct: 0,
      form_grade: form_score >= 70 ? "B" : "D",
      form_score,
      metrics: [
        { key: "rom", label: "Range of motion", value: form_score, unit: "%", target: ">= 70%", status: form_score >= 70 ? "pass" : "fail" },
      ],
    })),
  },
};

const clubBoard = {
  ...consistencyLeaderboard,
  rows: consistencyLeaderboard.rows.map((r) => ({ ...r, history: [{ score: r.score, date: "2026-11-02" }] })),
};

function setup({
  viewer,
  board = clubBoard,
  result = liftingResult,
  liftType = "Situp",
  participant = "b1",
  name = "Ben",
  title = "The 100 Club",
}: {
  viewer: string | null;
  board?: object;
  result?: object;
  liftType?: string;
  participant?: string;
  name?: string;
  title?: string;
}) {
  (localStorage.getItem as jest.Mock).mockImplementation((key: string) => (key === "userId" ? viewer : null));
  (api.getChallengeLeaderboard as jest.Mock).mockResolvedValue(board);
  (api.getLiftingResult as jest.Mock).mockResolvedValue(result);
  (axios.get as jest.Mock).mockImplementation((url: string) => {
    if (url.endsWith(`/competitions/${ID}`))
      return Promise.resolve({ data: { competition: { id: ID, name: title, start_date: "2026-01-01", end_date: "2099-12-27" } } });
    if (url.includes("/attempts/v1"))
      return Promise.resolve({
        data: { id: "v1", lift_type: liftType, weight: 0, participant_name: name, status: "completed" },
      });
    return Promise.resolve({ data: { lifts: [] } });
  });

  render(
    <MemoryRouter initialEntries={[`/challenges/${ID}/participants/${participant}/video/v1`]}>
      <Routes>
        <Route path="/challenges/:id/participants/:participantId/video/:videoId" element={<VideoPlayer />} />
      </Routes>
    </MemoryRouter>,
  );
}

it("shows the club result block instead of the rank ladder on a 100 Club board", async () => {
  setup({ viewer: "b1" });

  const result = await screen.findByTestId("consistency-result");
  expect(result).toHaveTextContent("+3 lifts banked");
  expect(result).toHaveTextContent("10 / 125 this week · 4 days left");
  expect(result).not.toHaveTextContent("Ben:");
  expect(screen.queryByText(/to pass/)).toBeNull();
  expect(screen.queryByText(/Where you stand/i)).toBeNull();
});

it("names the athlete when the viewer is watching someone else's club video", async () => {
  setup({ viewer: "a1" });

  const result = await screen.findByTestId("consistency-result");
  expect(result).toHaveTextContent("Ben: 10 / 125 this week · 4 days left");
});

it("places an older club attempt in its own week", async () => {
  setup({ viewer: "b1", result: { ...liftingResult, attempt_created_at: "2026-11-04T17:00:00+00:00" } });

  const result = await screen.findByTestId("consistency-result");
  expect(result).toHaveTextContent("+3 lifts banked in week 1");
  expect(result).not.toHaveTextContent("this week");
});

it("shares club wording, not a rank, from a club video", async () => {
  (share.shareResult as jest.Mock).mockResolvedValue({ url: "https://s/x", method: "share" });
  setup({ viewer: "b1" });
  await screen.findByTestId("consistency-result");
  fireEvent.click(screen.getByTitle("Copy short link to share"));

  await waitFor(() => expect(share.shareResult).toHaveBeenCalled());
  const words = (share.shareResult as jest.Mock).mock.calls.at(-1)[1];
  expect(words).toBe("I banked 3 lifts in The 100 Club — 10 / 125 this week. Join me:");
});

describe("legacy reps board", () => {
  const mkRow = (rank: number, user_id: string, name: string, score: number) => ({
    rank, user_id, name, score, best_by_lift: { Pushup: score }, form_score: null, steadiness: null,
    attempt_id: `${user_id}-best`, clip_url: null, thumbnail_url: null, date: "2026-08-28",
    weight_class: null, gender: null, attempt_count: 1, history: [{ score, date: "2026-08-01" }],
  });
  const legacy = {
    competition_id: ID, metric: "reps", lift_types: ["Pushup"], momentum: { joined: 2, uploaded_today: 0 },
    rows: [mkRow(1, "rob", "rob", 39), mkRow(2, "toka", "Toka", 35)],
  };
  const pushups = { ...liftingResult, report: { ...liftingResult.report, lift_type: "Pushup", total_reps: 35 } };

  it("still renders the rank ladder and no club block", async () => {
    setup({ viewer: "toka", board: legacy, result: pushups, liftType: "Pushup", participant: "toka", name: "Toka", title: "Pushup Party" });

    expect(await screen.findByText("4 reps to pass rob")).toBeInTheDocument();
    expect(screen.queryByTestId("consistency-result")).toBeNull();
  });
});
