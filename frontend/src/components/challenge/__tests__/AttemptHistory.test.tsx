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

const plankAttempt = (id: string, iso: string, hold: number, steadiness: number | null = null) => ({
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
  steadiness,
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

const pushupAttempt = (id: string, iso: string, reps: number | null, grade: string | null) => ({
  attempt_id: id,
  competition_id: "comp3",
  competition_name: "Pushup Challenge",
  lift_type: "pushup",
  weight: null,
  created_at: iso,
  status: "completed",
  analysis_status: reps === null ? "processing" : "completed",
  grade,
  total_reps: reps,
  hold_s: null,
});

const renderPanel = (metric: "time" | "weight" | "reps", competitionId: string) =>
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

  it("shows a steadiness nickname on a plank attempt", async () => {
    (axios.get as jest.Mock).mockResolvedValue({
      data: { lifts: [plankAttempt("a1", "2026-07-06T09:00:00+00:00", 40, 1)], total: 1 },
    });
    renderPanel("time", "comp1");
    await waitFor(() => expect(screen.getByText(/Statue/)).toBeInTheDocument());
  });

  it("shows no nickname when steadiness is absent", async () => {
    (axios.get as jest.Mock).mockResolvedValue({
      data: { lifts: [plankAttempt("a1", "2026-07-06T09:00:00+00:00", 40, null)], total: 1 },
    });
    renderPanel("time", "comp1");
    await waitFor(() => expect(screen.getByText("0:40")).toBeInTheDocument());
    expect(screen.queryByText(/Statue|Wobbler|Jellyfish|Steady Eddie/)).toBeNull();
  });

  it("shows the error copy on fetch failure", async () => {
    (axios.get as jest.Mock).mockRejectedValue(new Error("boom"));
    renderPanel("time", "comp1");
    await waitFor(() =>
      expect(screen.getByText(/couldn't load attempts/i)).toBeInTheDocument()
    );
  });

  it("reps metric: renders rep counts + grade pill and crowns the best", async () => {
    (axios.get as jest.Mock).mockResolvedValue({
      data: {
        lifts: [
          pushupAttempt("p1", "2026-08-02T09:00:00+00:00", 30, "A"),
          pushupAttempt("p2", "2026-08-01T09:00:00+00:00", 12, "C"),
        ],
        total: 2,
      },
    });
    renderPanel("reps", "comp3");
    await waitFor(() => expect(screen.getByText("30 reps")).toBeInTheDocument());
    expect(screen.getByText("12 reps")).toBeInTheDocument();
    expect(screen.getByText("A")).toBeInTheDocument();
    expect(screen.getByText("🏆").closest("a")).toHaveAttribute(
      "href",
      "/challenges/comp3/participants/u1/video/p1"
    );
  });

  it("reps metric: shows analyzing… while a pushup attempt has no rep count yet", async () => {
    (axios.get as jest.Mock).mockResolvedValue({
      data: { lifts: [pushupAttempt("p9", "2026-08-03T09:00:00+00:00", null, null)], total: 1 },
    });
    renderPanel("reps", "comp3");
    await waitFor(() => expect(screen.getByText("analyzing…")).toBeInTheDocument());
  });
});
