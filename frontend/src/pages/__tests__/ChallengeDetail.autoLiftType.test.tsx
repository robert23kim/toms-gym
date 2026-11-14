import React from "react";
import "@testing-library/jest-dom";
import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import axios from "axios";
import ChallengeDetail from "../ChallengeDetail";
import * as api from "../../lib/api";
import { uploadVideo } from "../../lib/resumableUpload";
import { CONSISTENCY_COMPETITION_ID, consistencyRules } from "../../__fixtures__/consistencyLeaderboard";
import { liveClubBoard } from "../../__fixtures__/liveClubBoard";

jest.mock("../../config", () => ({ API_URL: "https://test-api.example", APP_BUILD: "test" }));
jest.mock("../../components/Layout", () => ({
  __esModule: true,
  default: ({ children }: { children: React.ReactNode }) => <div>{children}</div>,
}));
jest.mock("../../lib/resumableUpload", () => ({ uploadVideo: jest.fn() }));
jest.mock("../../lib/telemetry", () => ({ reportUploadError: jest.fn() }));
jest.mock("../../components/ui/use-toast", () => ({ useToast: () => ({ toast: jest.fn() }) }));
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

Element.prototype.scrollIntoView = jest.fn();

const ID = CONSISTENCY_COMPETITION_ID;
const club = {
  id: ID,
  name: "The 100 Club",
  start_date: "2026-01-01",
  end_date: "2099-12-27",
  description: "100 lifts a week.",
  lifttypes: ["Situp", "Pushup", "Squat", "Plank"],
  mode: "consistency",
  rules: consistencyRules,
};

const setup = (comp: object, extra: object = {}) => {
  (localStorage.getItem as jest.Mock).mockImplementation((k: string) =>
    k === "userEmail" ? "sam@example.com" : null,
  );
  (api.getChallengeLeaderboard as jest.Mock).mockResolvedValue(liveClubBoard);
  (api.fetchChampions as jest.Mock).mockResolvedValue([]);
  (api.triggerLiftingAnalysis as jest.Mock).mockResolvedValue({});
  (api.getLiftingResult as jest.Mock).mockResolvedValue({ processing_status: "processing" });
  (axios.get as jest.Mock).mockImplementation((url: string) => {
    if (url.endsWith(`/competitions/${ID}`)) return Promise.resolve({ data: { competition: comp, ...extra } });
    if (url.endsWith("/participants")) return Promise.resolve({ data: { participants: [] } });
    if (url.endsWith("/lifts")) return Promise.resolve({ data: { lifts: [] } });
    return Promise.reject(new Error(`unexpected GET ${url}`));
  });
  return render(
    <MemoryRouter initialEntries={[`/challenges/${ID}?upload=1`]}>
      <Routes>
        <Route path="/challenges/:id" element={<ChallengeDetail />} />
      </Routes>
    </MemoryRouter>,
  );
};

const liftSelect = async () => {
  const form = (await screen.findByText("Lift Type")).closest("form")!;
  return { form, select: form.querySelector("select") as HTMLSelectElement };
};

describe("Automatic lift type on the board's upload form", () => {
  beforeEach(() => jest.clearAllMocks());

  it("offers Automatic first and selected, hides weight, and says it once", async () => {
    setup({ ...club, auto_lift_type_enabled: true });
    const { form, select } = await liftSelect();
    await waitFor(() => expect(select.value).toBe("Auto"));
    const first = select.options[0];
    expect(first).toHaveAttribute("data-testid", "lift-type-automatic");
    expect(first.textContent).toBe("Automatic");
    expect(Array.from(select.options).map((o) => o.textContent)).toEqual(["Automatic", "Squat", "Plank", "Pushup", "Situp"]);
    expect(form.querySelector('input[type="number"]')).toBeNull();
    expect(screen.getByText("We'll work out the lift from your video. You can change it after.")).toBeInTheDocument();
  });

  it("uploads with lift_type Auto and weight 0 after only picking a video", async () => {
    (uploadVideo as jest.Mock).mockResolvedValue({ url: "https://storage.example/a.mp4", attempt_id: "a-1", user_id: "u-1" });
    setup({ ...club, auto_lift_type_enabled: true });
    const { form, select } = await liftSelect();
    await waitFor(() => expect(select.value).toBe("Auto"));
    expect((form.querySelector('input[type="email"]') as HTMLInputElement).value).toBe("sam@example.com");
    fireEvent.change(form.querySelector('input[type="file"]')!, {
      target: { files: [new File(["x"], "s.mp4", { type: "video/mp4" })] },
    });
    fireEvent.submit(form);
    await waitFor(() => expect(uploadVideo).toHaveBeenCalled());
    expect((uploadVideo as jest.Mock).mock.calls[0][1]).toMatchObject({ lift_type: "Auto", weight: "0", email: "sam@example.com" });
  });

  it("goes back to Automatic after an upload with a manual pick", async () => {
    (uploadVideo as jest.Mock).mockResolvedValue({ url: "https://storage.example/a.mp4", attempt_id: "a-1", user_id: "u-1" });
    setup({ ...club, auto_lift_type_enabled: true });
    const { form, select } = await liftSelect();
    await waitFor(() => expect(select.value).toBe("Auto"));
    fireEvent.change(select, { target: { value: "Pushup" } });
    expect(screen.queryByText(/work out the lift/)).toBeNull();
    fireEvent.change(form.querySelector('input[type="file"]')!, {
      target: { files: [new File(["x"], "s.mp4", { type: "video/mp4" })] },
    });
    fireEvent.submit(form);
    await waitFor(() => expect(uploadVideo).toHaveBeenCalled());
    expect((uploadVideo as jest.Mock).mock.calls[0][1]).toMatchObject({ lift_type: "Pushup", weight: "0" });
    fireEvent.click(screen.getAllByText("Log this week's lifts")[0]);
    const again = await liftSelect();
    expect(again.select.value).toBe("Auto");
  });

  it("reads the switch at the top level too", async () => {
    setup(club, { auto_lift_type_enabled: true });
    const { select } = await liftSelect();
    await waitFor(() => expect(select.value).toBe("Auto"));
  });

  it("renders the picker exactly as today with the switch off", async () => {
    setup(club);
    const { form, select } = await liftSelect();
    await waitFor(() => expect(select.value).toBe("Squat"));
    expect(screen.queryByTestId("lift-type-automatic")).toBeNull();
    expect(Array.from(select.options).map((o) => o.textContent)).toEqual(["Squat", "Plank", "Pushup", "Situp"]);
    expect(form.querySelector('input[type="number"]')).not.toBeNull();
    expect(screen.queryByText(/work out the lift/)).toBeNull();
  });

  it("never offers Automatic on a challenge with a weighted lift", async () => {
    setup({ ...club, mode: undefined, lifttypes: ["Squat", "Bench Press"], auto_lift_type_enabled: true });
    const { select } = await liftSelect();
    await waitFor(() => expect(select.value).toBe("Squat"));
    expect(screen.queryByTestId("lift-type-automatic")).toBeNull();
  });
});
