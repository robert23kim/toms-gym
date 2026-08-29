import React from "react";
import "@testing-library/jest-dom";
import { render, screen, waitFor } from "@testing-library/react";
import { MemoryRouter, Routes, Route } from "react-router-dom";
import axios from "axios";
import AnalysisStatus from "../AnalysisStatus";

// config.ts uses import.meta (Vite), which jest can't parse; mock it as the
// repo's other tests do (see src/lib/__tests__/queries.test.tsx).
jest.mock("../../config", () => ({ API_URL: "https://test-api.example" }));

// Layout pulls in the Navbar/auth tree; stub it so the test stays focused on
// the status card.
jest.mock("../../components/Layout", () => ({
  __esModule: true,
  default: ({ children }: { children: React.ReactNode }) => <div>{children}</div>,
}));

jest.mock("axios", () => {
  const actual = jest.requireActual("axios");
  const mocked = { ...actual, get: jest.fn(), isAxiosError: actual.isAxiosError };
  return { ...mocked, default: mocked };
});

const mkRow = (rank: number, user_id: string, name: string, score: number, history: number[]) => ({
  rank, user_id, name, score, best_by_lift: { Pushup: score }, form_score: null, steadiness: null,
  attempt_id: `${user_id}-best`, clip_url: null, thumbnail_url: null, date: "2026-08-28",
  weight_class: null, gender: null, attempt_count: history.length,
  history: history.map((s, i) => ({ score: s, date: `2026-08-0${i + 1}` })),
});
const board = {
  competition_id: "c1", metric: "reps", lift_types: ["Pushup"], momentum: { joined: 3, uploaded_today: 1 },
  rows: [mkRow(1, "rob", "rob", 39, [39]), mkRow(2, "toka", "Toka", 35, [28, 35]), mkRow(3, "caleb", "caleb", 20, [20])],
};
const routeGet = (result: object) =>
  (axios.get as jest.Mock).mockImplementation((url: string) =>
    url.includes("/leaderboard") ? Promise.resolve({ data: board }) : Promise.resolve({ data: result }),
  );

const renderAt = (kind: "lifting" | "bowling", id: string, search = "") =>
  render(
    <MemoryRouter initialEntries={[`/status/${id}${search}`]}>
      <Routes>
        <Route path="/status/:attemptId" element={<AnalysisStatus kind={kind} />} />
      </Routes>
    </MemoryRouter>
  );

describe("AnalysisStatus", () => {
  beforeEach(() => {
    (axios.get as jest.Mock).mockReset();
  });

  it("shows honest ETA + email copy while processing", async () => {
    (axios.get as jest.Mock).mockResolvedValue({
      data: { processing_status: "processing" },
    });
    renderAt("lifting", "a1");

    await waitFor(() =>
      expect(screen.getByText(/Analyzing your lift/i)).toBeInTheDocument()
    );
    expect(screen.getByText(/up to 10 minutes/i)).toBeInTheDocument();
    expect(
      screen.getByText(/We'll email you a link when it's ready/i)
    ).toBeInTheDocument();
  });

  it("treats a 404 (result not created yet) as queued, not an error", async () => {
    const notFound = Object.assign(new Error("Not Found"), {
      isAxiosError: true,
      response: { status: 404 },
    });
    (axios.get as jest.Mock).mockRejectedValue(notFound);
    renderAt("lifting", "a2");

    await waitFor(() =>
      expect(screen.getByText(/Queued for analysis/i)).toBeInTheDocument()
    );
  });

  it("links to the full result page when bowling completes", async () => {
    (axios.get as jest.Mock).mockResolvedValue({
      data: { processing_status: "completed" },
    });
    renderAt("bowling", "b1");

    const link = await screen.findByRole("link", { name: /See your result/i });
    expect(link).toHaveAttribute("href", "/bowling/result/b1");
  });

  it("surfaces the error message when analysis fails", async () => {
    (axios.get as jest.Mock).mockResolvedValue({
      data: { processing_status: "failed", error_message: "pose model crashed" },
    });
    renderAt("lifting", "a3");

    await waitFor(() =>
      expect(screen.getByText(/Analysis failed/i)).toBeInTheDocument()
    );
    expect(screen.getByText(/pose model crashed/i)).toBeInTheDocument();
    expect(
      screen.getByRole("link", { name: /Upload Again/i })
    ).toHaveAttribute("href", "/lift/upload");
  });

  it("deep-links a completed lift to its result page when the ids are known", async () => {
    (axios.get as jest.Mock).mockResolvedValue({
      data: { processing_status: "completed", user_id: "u9", competition_id: "c3" },
    });
    renderAt("lifting", "a9");

    const link = await screen.findByRole("link", { name: /See your result/i });
    expect(link).toHaveAttribute("href", "/challenges/c3/participants/u9/video/a9");
    expect(screen.queryByRole("link", { name: /View Your Profile/i })).toBeNull();
  });

  it("falls back to the profile for a completed lift without competition ids", async () => {
    (localStorage.getItem as jest.Mock).mockReturnValue("u1");
    (axios.get as jest.Mock).mockResolvedValue({
      data: { processing_status: "completed" },
    });
    renderAt("lifting", "a8");

    const link = await screen.findByRole("link", { name: /View Your Profile/i });
    expect(link).toHaveAttribute("href", "/profile/u1");
    (localStorage.getItem as jest.Mock).mockReset();
  });

  it("names the leader as a target while a challenge upload is analyzing", async () => {
    routeGet({ processing_status: "processing" });
    renderAt("lifting", "a5", "?challenge=c1");

    expect(await screen.findByText("rob")).toBeInTheDocument();
    expect(screen.getByText("39 reps")).toBeInTheDocument();
    expect(screen.getByText(/3 on the board/)).toBeInTheDocument();
  });

  it("reveals the number, the grade and the ladder when a lift completes", async () => {
    routeGet({
      processing_status: "completed",
      user_id: "toka",
      competition_id: "c1",
      report: { total_reps: 35, overall_grade: "C", lift_type: "pushup" },
    });
    renderAt("lifting", "a6");

    expect(await screen.findByRole("heading", { name: "35 reps" })).toBeInTheDocument();
    expect(screen.getByText("C")).toBeInTheDocument();
    expect(await screen.findByText("#2")).toBeInTheDocument();
    expect(screen.getByText("4 reps to pass rob")).toBeInTheDocument();
    expect(screen.getByText(/New best · up from 28 reps/)).toBeInTheDocument();
    expect(screen.getByRole("link", { name: /See your result/i })).toHaveAttribute(
      "href",
      "/challenges/c1/participants/toka/video/a6",
    );
    expect(screen.queryByText(/Analysis complete!/)).toBeNull();
  });

  it("keeps the plain completion card for bowling", async () => {
    (axios.get as jest.Mock).mockResolvedValue({ data: { processing_status: "completed" } });
    renderAt("bowling", "b7");
    expect(await screen.findByText(/Analysis complete!/)).toBeInTheDocument();
  });
});
