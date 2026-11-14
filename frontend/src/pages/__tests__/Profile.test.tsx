import React from "react";
import "@testing-library/jest-dom";
import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { MemoryRouter, Routes, Route } from "react-router-dom";
import axios from "axios";
import Profile from "../Profile";
import * as api from "../../lib/api";
import { useIsOwner } from "../../hooks/useIsOwner";

jest.mock("../../config", () => ({ API_URL: "https://test-api.example" }));

jest.mock("../../components/Layout", () => ({
  __esModule: true,
  default: ({ children }: { children: React.ReactNode }) => <div>{children}</div>,
}));

const mockLogout = jest.fn();
const mockAuth = { isAuthenticated: false };
jest.mock("../../auth/AuthContext", () => ({
  useAuth: () => ({
    isAuthenticated: mockAuth.isAuthenticated,
    user: null,
    loading: false,
    error: null,
    hasLocalUserId: false,
    handleLoginSuccess: jest.fn(),
    logout: mockLogout,
  }),
}));

jest.mock("../../components/profile/LiftHistoryList", () => ({
  __esModule: true,
  default: () => <div>lift-history</div>,
}));

jest.mock("axios", () => {
  const actual = jest.requireActual("axios");
  const mocked = { ...actual, get: jest.fn(), isAxiosError: actual.isAxiosError };
  return { ...mocked, default: mocked };
});

jest.mock("../../hooks/useIsOwner", () => ({ useIsOwner: jest.fn(() => false) }));
jest.mock("../../lib/api", () => ({
  ...jest.requireActual("../../lib/api"),
  fetchRounds: jest.fn(),
  fetchBowlingResultsByUser: jest.fn(),
  fetchBowlingGames: jest.fn(),
  fetchChampions: jest.fn(),
}));

interface UploadedVideoFixture {
  attempt_id: string;
  lift_type: string;
  weight: number;
  video_url: string;
  created_at: string;
  status: string;
  competition_id: string;
  competition_name: string;
}

const video = (over: Partial<UploadedVideoFixture> = {}): UploadedVideoFixture => ({
  attempt_id: "a1",
  lift_type: "Plank",
  weight: 60,
  video_url: "https://videos.example/a1.mp4",
  created_at: "2026-08-01T12:00:00Z",
  status: "completed",
  competition_id: "c1",
  competition_name: "Summer plank challenge",
  ...over,
});

const profilePayload = (over: { uploaded_videos?: UploadedVideoFixture[] } = {}) => ({
  user: {
    id: "u1",
    name: "wonder725",
    email: "wonder725@example.com",
    username: "wonder725",
    created_at: "2026-01-04T09:30:00Z",
  },
  competitions: [
    {
      id: "c1",
      name: "Summer plank challenge",
      start_date: "2026-06-01T00:00:00Z",
      end_date: "2026-07-31T00:00:00Z",
      description: "Hold the line",
      weight_class: "Open",
      status: "in_progress",
      total_weight: 60,
      successful_lifts: 2,
    },
  ],
  best_lifts: [
    {
      type: "Plank",
      best_weight: 60,
      competition_name: "Summer plank challenge",
      competition_id: "c1",
    },
  ],
  achievements: {
    total_competitions: 1,
    total_successful_lifts: 2,
    heaviest_lift: 60,
    best_snatch: 1,
    best_clean_and_jerk: 0,
  },
  uploaded_videos: over.uploaded_videos ?? [video(), video({ attempt_id: "a2" })],
});

const renderProfile = () =>
  render(
    <MemoryRouter initialEntries={["/profile/u1"]}>
      <Routes>
        <Route path="/profile/:id" element={<Profile />} />
      </Routes>
    </MemoryRouter>
  );

describe("Profile — Lift tab", () => {
  beforeEach(() => {
    (axios.get as jest.Mock).mockReset();
    // jest.setup.js replaces localStorage with jest.fn()s, so reads must be stubbed.
    (localStorage.getItem as jest.Mock).mockReturnValue(null);
    (api.fetchRounds as jest.Mock).mockResolvedValue(null);
    (api.fetchBowlingResultsByUser as jest.Mock).mockResolvedValue([]);
    (api.fetchBowlingGames as jest.Mock).mockResolvedValue(null);
    (api.fetchChampions as jest.Mock).mockResolvedValue([]);
  });

  afterEach(() => {
    (localStorage.getItem as jest.Mock).mockReset();
  });

  it("shows one honest history plus an upload link, and none of the removed blocks", async () => {
    (axios.get as jest.Mock).mockResolvedValue({ data: profilePayload() });
    renderProfile();

    await waitFor(() => expect(screen.getByText("lift-history")).toBeInTheDocument());
    expect(screen.getByRole("link", { name: /upload a lift/i })).toHaveAttribute(
      "href",
      "/lift/upload"
    );
    expect(screen.getByRole("link", { name: /track weekly lifts/i })).toBeInTheDocument();

    expect(screen.queryByText("Competition Stats")).toBeNull();
    expect(screen.queryByText("Personal Bests")).toBeNull();
    expect(screen.queryByText("Achievements")).toBeNull();
    expect(screen.queryByText("Lift Videos")).toBeNull();
    expect(screen.queryByText("Competition History")).toBeNull();
  });

  it("shows the Bowl and Golf tabs only to the app owner", async () => {
    (axios.get as jest.Mock).mockResolvedValue({ data: profilePayload() });
    const { unmount } = renderProfile();
    await waitFor(() => expect(screen.getByText("lift-history")).toBeInTheDocument());
    expect(screen.queryByRole("button", { name: /bowl/i })).toBeNull();
    expect(screen.queryByRole("button", { name: /golf/i })).toBeNull();
    unmount();

    (useIsOwner as jest.Mock).mockReturnValue(true);
    renderProfile();
    await waitFor(() => expect(screen.getByText("lift-history")).toBeInTheDocument());
    expect(screen.getByRole("button", { name: /bowl/i })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /golf/i })).toBeInTheDocument();
    (useIsOwner as jest.Mock).mockReturnValue(false);
  });

  it("owns the empty state when the user has no uploaded lifts", async () => {
    (axios.get as jest.Mock).mockResolvedValue({
      data: profilePayload({ uploaded_videos: [] }),
    });
    renderProfile();

    await waitFor(() => expect(screen.getByText(/no lifts yet/i)).toBeInTheDocument());
    expect(screen.getByRole("link", { name: /upload your first lift/i })).toHaveAttribute(
      "href",
      "/lift/upload"
    );
    expect(screen.queryByText("lift-history")).toBeNull();
  });

  it("hides the email from visitors and shows it to the owner", async () => {
    (axios.get as jest.Mock).mockResolvedValue({ data: profilePayload() });

    (localStorage.getItem as jest.Mock).mockReturnValue("someone-else");
    const visitor = renderProfile();
    await waitFor(() => expect(screen.getByText("wonder725")).toBeInTheDocument());
    expect(screen.queryByText("wonder725@example.com")).toBeNull();
    visitor.unmount();

    (localStorage.getItem as jest.Mock).mockReturnValue("u1");
    renderProfile();
    await waitFor(() =>
      expect(screen.getByText("wonder725@example.com")).toBeInTheDocument()
    );
  });
});

describe("Profile — Forget Me on a phone", () => {
  const remembered = (id: string) => (k: string) => (k === "userId" ? id : k === "userEmail" ? "owner@example.com" : null);

  beforeEach(() => {
    (axios.get as jest.Mock).mockReset();
    (localStorage.removeItem as jest.Mock).mockClear();
    mockLogout.mockClear();
    mockAuth.isAuthenticated = false;
    (api.fetchRounds as jest.Mock).mockResolvedValue(null);
    (api.fetchBowlingResultsByUser as jest.Mock).mockResolvedValue([]);
    (api.fetchBowlingGames as jest.Mock).mockResolvedValue(null);
    (api.fetchChampions as jest.Mock).mockResolvedValue([]);
  });

  afterEach(() => {
    (localStorage.getItem as jest.Mock).mockReset();
  });

  it("gives the owner a phone-only Forget Me that clears the remembered identity", async () => {
    (localStorage.getItem as jest.Mock).mockImplementation(remembered("u1"));
    (axios.get as jest.Mock).mockResolvedValue({ data: profilePayload() });
    renderProfile();

    const button = await screen.findByRole("button", { name: "Forget Me" });
    expect(button).toHaveClass("md:hidden");
    fireEvent.click(button);
    await waitFor(() => expect(localStorage.removeItem).toHaveBeenCalledWith("userId"));
    expect(localStorage.removeItem).toHaveBeenCalledWith("userEmail");
    expect(localStorage.removeItem).toHaveBeenCalledWith("last_attempt_id");
  });

  it("does not offer Forget Me on someone else's profile", async () => {
    (localStorage.getItem as jest.Mock).mockImplementation(remembered("someone-else"));
    (axios.get as jest.Mock).mockResolvedValue({ data: profilePayload() });
    renderProfile();

    await waitFor(() => expect(screen.getByText("wonder725")).toBeInTheDocument());
    expect(screen.queryByRole("button", { name: "Forget Me" })).toBeNull();
  });

  it("still offers Forget Me when the remembered profile fails to load", async () => {
    (localStorage.getItem as jest.Mock).mockImplementation(remembered("u1"));
    (axios.get as jest.Mock).mockRejectedValue(Object.assign(new Error("Not Found"), { response: { status: 404, data: { error: "User not found" } } }));
    jest.spyOn(console, "error").mockImplementation(() => {});
    renderProfile();

    expect(await screen.findByRole("button", { name: "Forget Me" })).toBeInTheDocument();
    (console.error as jest.Mock).mockRestore();
  });

  it("offers Logout instead to a signed-in owner", async () => {
    mockAuth.isAuthenticated = true;
    (localStorage.getItem as jest.Mock).mockImplementation(remembered("u1"));
    (axios.get as jest.Mock).mockResolvedValue({ data: profilePayload() });
    renderProfile();

    fireEvent.click(await screen.findByRole("button", { name: "Logout" }));
    expect(mockLogout).toHaveBeenCalledTimes(1);
    expect(screen.queryByRole("button", { name: "Forget Me" })).toBeNull();
  });
});
