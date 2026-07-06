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

const renderAt = (kind: "lifting" | "bowling", id: string) =>
  render(
    <MemoryRouter initialEntries={[`/status/${id}`]}>
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

    const link = await screen.findByRole("link", { name: /View Full Result/i });
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
});
