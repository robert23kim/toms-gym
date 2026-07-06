import React from "react";
import "@testing-library/jest-dom";
import { render, screen, waitFor, fireEvent } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import axios from "axios";
import LiftHistoryList from "../LiftHistoryList";

// config.ts uses import.meta (Vite), which jest can't parse; mock it as the
// repo's other tests do.
jest.mock("../../../config", () => ({ API_URL: "https://test-api.example" }));

jest.mock("axios", () => {
  const actual = jest.requireActual("axios");
  const mocked = { ...actual, get: jest.fn() };
  return { ...mocked, default: mocked };
});

const squat = {
  attempt_id: "a1",
  competition_id: "c1",
  competition_name: "Squat-Off",
  lift_type: "squat",
  weight: 100,
  created_at: "2026-07-04T12:00:00+00:00",
  status: "completed",
  analysis_status: "completed",
  grade: "A",
  total_reps: 5,
  hold_s: null,
};

const plank = {
  attempt_id: "a2",
  competition_id: "c2",
  competition_name: "Plank Challenge",
  lift_type: "plank",
  weight: 0,
  created_at: "2026-07-06T09:00:00+00:00",
  status: "completed",
  analysis_status: "completed",
  grade: null,
  total_reps: null,
  hold_s: 244.2,
};

const queued = {
  ...squat,
  attempt_id: "a3",
  grade: null,
  analysis_status: "queued",
};

const renderList = () =>
  render(
    <MemoryRouter>
      <LiftHistoryList userId="u1" />
    </MemoryRouter>
  );

describe("LiftHistoryList", () => {
  beforeEach(() => jest.clearAllMocks());

  it("renders grade pill, plank hold time, and analyzing state with correct links", async () => {
    (axios.get as jest.Mock).mockResolvedValue({
      data: { lifts: [plank, squat, queued], total: 3, limit: 20, offset: 0 },
    });
    renderList();
    await waitFor(() => expect(screen.getByText("A")).toBeInTheDocument());
    expect(screen.getByText("4:04")).toBeInTheDocument(); // 244.2s hold
    expect(screen.getByText(/analyzing/i)).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: /my lifts \(3\)/i })).toBeInTheDocument();
    const plankLink = screen.getByText("4:04").closest("a");
    expect(plankLink).toHaveAttribute("href", "/challenges/c2/participants/u1/video/a2");
  });

  it("loads the next page and appends", async () => {
    (axios.get as jest.Mock)
      .mockResolvedValueOnce({ data: { lifts: [squat], total: 2, limit: 1, offset: 0 } })
      .mockResolvedValueOnce({
        data: { lifts: [plank], total: 2, limit: 1, offset: 1 },
      });
    renderList();
    await waitFor(() => expect(screen.getByText("A")).toBeInTheDocument());
    fireEvent.click(screen.getByRole("button", { name: /load more/i }));
    await waitFor(() => expect(screen.getByText("4:04")).toBeInTheDocument());
    expect(screen.getByText("A")).toBeInTheDocument(); // first page still there
    const secondCall = (axios.get as jest.Mock).mock.calls[1][0] as string;
    expect(secondCall).toContain("offset=1");
  });

  it("renders nothing on empty or error", async () => {
    (axios.get as jest.Mock).mockResolvedValue({
      data: { lifts: [], total: 0, limit: 20, offset: 0 },
    });
    const { container } = renderList();
    await waitFor(() => expect(axios.get).toHaveBeenCalled());
    expect(container.firstChild).toBeNull();

    (axios.get as jest.Mock).mockRejectedValue(new Error("boom"));
    const { container: c2 } = renderList();
    await waitFor(() => expect(axios.get).toHaveBeenCalledTimes(2));
    expect(c2.firstChild).toBeNull();
  });
});
