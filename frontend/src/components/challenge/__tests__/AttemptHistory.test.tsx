import React from "react";
import "@testing-library/jest-dom";
import { render, screen, waitFor } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import axios from "axios";
import AttemptHistory from "../AttemptHistory";

// config.ts uses import.meta (Vite), which jest can't parse; mock it as the
// repo's other tests do.
jest.mock("../../../config", () => ({ API_URL: "https://test-api.example" }));

jest.mock("axios", () => {
  const actual = jest.requireActual("axios");
  const mocked = { ...actual, get: jest.fn() };
  return { ...mocked, default: mocked };
});

const plankAttempt = (id: string, iso: string, hold: number) => ({
  attempt_id: id,
  competition_id: "comp1",
  competition_name: "Plank Challenge",
  lift_type: "plank",
  weight: 60,
  created_at: iso,
  status: "completed",
  analysis_status: "completed",
  grade: null,
  total_reps: null,
  hold_s: hold,
});

const weightAttempt = (id: string, iso: string, weight: number, grade: string | null) => ({
  attempt_id: id,
  competition_id: "comp2",
  competition_name: "Squat-Off",
  lift_type: "squat",
  weight,
  created_at: iso,
  status: "completed",
  analysis_status: "completed",
  grade,
  total_reps: 5,
  hold_s: null,
});

const renderPanel = (metric: "time" | "weight", competitionId: string) =>
  render(
    <MemoryRouter>
      <AttemptHistory userId="u1" competitionId={competitionId} metric={metric} />
    </MemoryRouter>
  );

describe("AttemptHistory", () => {
  beforeEach(() => jest.clearAllMocks());

  it("time metric: renders m:ss holds, crowns the max, links to the video", async () => {
    (axios.get as jest.Mock).mockResolvedValue({
      data: {
        lifts: [
          plankAttempt("a1", "2026-07-06T09:00:00+00:00", 244.2),
          plankAttempt("a2", "2026-07-05T09:00:00+00:00", 215.1),
        ],
        total: 2,
      },
    });
    renderPanel("time", "comp1");
    await waitFor(() => expect(screen.getByText("4:04")).toBeInTheDocument());
    expect(screen.getByText("3:35")).toBeInTheDocument();
    // crown on the best (a1) only
    const crowned = screen.getByText("🏆");
    expect(crowned.closest("a")).toHaveAttribute(
      "href",
      "/challenges/comp1/participants/u1/video/a1"
    );
    const url = (axios.get as jest.Mock).mock.calls[0][0] as string;
    expect(url).toContain("competition_id=comp1");
  });

  it("weight metric: renders kg + grade pill and crowns the heaviest", async () => {
    (axios.get as jest.Mock).mockResolvedValue({
      data: {
        lifts: [
          weightAttempt("b1", "2026-07-04T09:00:00+00:00", 100, "A"),
          weightAttempt("b2", "2026-07-01T09:00:00+00:00", 110, "B"),
        ],
        total: 2,
      },
    });
    renderPanel("weight", "comp2");
    await waitFor(() => expect(screen.getByText(/110kg/)).toBeInTheDocument());
    expect(screen.getByText(/100kg/)).toBeInTheDocument();
    expect(screen.getByText("A")).toBeInTheDocument();
    expect(screen.getByText("🏆").closest("a")).toHaveAttribute(
      "href",
      "/challenges/comp2/participants/u1/video/b2"
    );
  });

  it("shows the error copy on fetch failure", async () => {
    (axios.get as jest.Mock).mockRejectedValue(new Error("boom"));
    renderPanel("time", "comp1");
    await waitFor(() =>
      expect(screen.getByText(/couldn't load attempts/i)).toBeInTheDocument()
    );
  });
});
