import React from "react";
import "@testing-library/jest-dom";
import { render, screen } from "@testing-library/react";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import axios from "axios";
import VideoPlayer from "../VideoPlayer";
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
}));

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

it("shows the club result block instead of the rank ladder on a 100 Club board", async () => {
  const board = {
    ...consistencyLeaderboard,
    rows: consistencyLeaderboard.rows.map((r) => ({ ...r, history: [{ score: r.score, date: "2026-11-02" }] })),
  };
  (localStorage.getItem as jest.Mock).mockImplementation((key: string) => (key === "userId" ? "b1" : null));
  (api.getChallengeLeaderboard as jest.Mock).mockResolvedValue(board);
  (api.getLiftingResult as jest.Mock).mockResolvedValue(liftingResult);
  (axios.get as jest.Mock).mockImplementation((url: string) => {
    if (url.endsWith(`/competitions/${ID}`))
      return Promise.resolve({ data: { competition: { id: ID, name: "The 100 Club", start_date: "2026-01-01", end_date: "2099-12-27" } } });
    if (url.includes("/attempts/v1"))
      return Promise.resolve({
        data: { id: "v1", lift_type: "Situp", weight: 0, participant_name: "Ben", status: "completed", created_at: "2026-11-04T12:00:00Z" },
      });
    return Promise.resolve({ data: { lifts: [] } });
  });

  render(
    <MemoryRouter initialEntries={[`/challenges/${ID}/participants/b1/video/v1`]}>
      <Routes>
        <Route path="/challenges/:id/participants/:participantId/video/:videoId" element={<VideoPlayer />} />
      </Routes>
    </MemoryRouter>,
  );

  const result = await screen.findByTestId("consistency-result");
  expect(result).toHaveTextContent("+3 lifts banked");
  expect(result).toHaveTextContent("10 / 125 this week · 4 days left");
  expect(screen.queryByText(/to pass/)).toBeNull();
  expect(screen.queryByText(/Where you stand/i)).toBeNull();
});
