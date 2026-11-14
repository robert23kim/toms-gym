import React from "react";
import "@testing-library/jest-dom";
import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import axios from "axios";
import UploadVideo from "../UploadVideo";
import { uploadVideo } from "../../lib/resumableUpload";

jest.mock("../../config", () => ({ API_URL: "https://test-api.example" }));
jest.mock("../../components/Layout", () => ({
  __esModule: true,
  default: ({ children }: { children: React.ReactNode }) => <div>{children}</div>,
}));
jest.mock("../../lib/resumableUpload", () => ({ uploadVideo: jest.fn() }));
jest.mock("../../lib/telemetry", () => ({ reportUploadError: jest.fn() }));
jest.mock("../../lib/api", () => ({ triggerLiftingAnalysis: jest.fn().mockResolvedValue({}) }));
jest.mock("../../components/ui/use-toast", () => ({ useToast: () => ({ toast: jest.fn() }) }));
jest.mock("axios", () => ({
  __esModule: true,
  default: { get: jest.fn(), post: jest.fn(), isAxiosError: () => false },
}));

const CID = "club-1";
const club = { id: CID, name: "The 100 Club", lifttypes: ["Situp", "Pushup", "Squat", "Plank"], mode: "consistency" };

const setup = (path: string, comp: object | null) => {
  (localStorage.getItem as jest.Mock).mockImplementation((k: string) => (k === "userEmail" ? "sam@example.com" : null));
  (axios.get as jest.Mock).mockImplementation((url: string) => {
    if (comp && url.endsWith(`/competitions/${CID}`)) return Promise.resolve({ data: { competition: comp } });
    return Promise.reject(new Error(`unexpected GET ${url}`));
  });
  return render(
    <MemoryRouter initialEntries={[path]}>
      <Routes>
        <Route path="/challenges/:id/upload" element={<UploadVideo />} />
        <Route path="/lift/upload" element={<UploadVideo />} />
      </Routes>
    </MemoryRouter>,
  );
};

const select = () => screen.getByRole("combobox") as HTMLSelectElement;
const options = () => Array.from(select().options).map((o) => o.textContent);

describe("UploadVideo lift type picker", () => {
  beforeEach(() => jest.clearAllMocks());

  it("opened for the club with the switch on: Automatic first, selected, no weight", async () => {
    setup(`/challenges/${CID}/upload`, { ...club, auto_lift_type_enabled: true });
    await waitFor(() => expect(select().value).toBe("Auto"));
    expect(select().options[0]).toHaveAttribute("data-testid", "lift-type-automatic");
    expect(options()).toEqual(["Automatic", "Squat", "Bench Press", "Deadlift", "Pushup", "Situp"]);
    expect(screen.queryByText(/Weight/)).toBeNull();
    expect(screen.getByText("We'll work out the lift from your video. You can change it after.")).toBeInTheDocument();
    expect((screen.getByPlaceholderText("Enter your email to link this upload") as HTMLInputElement).value).toBe("sam@example.com");
  });

  it("a pick made before the competition loads is kept", async () => {
    let resolve: (v: object) => void = () => {};
    (localStorage.getItem as jest.Mock).mockImplementation(() => null);
    (axios.get as jest.Mock).mockImplementation(() => new Promise((r) => { resolve = r; }));
    render(
      <MemoryRouter initialEntries={[`/challenges/${CID}/upload`]}>
        <Routes>
          <Route path="/challenges/:id/upload" element={<UploadVideo />} />
        </Routes>
      </MemoryRouter>,
    );
    fireEvent.change(select(), { target: { value: "Pushup" } });
    resolve({ data: { competition: { ...club, auto_lift_type_enabled: true } } });
    await waitFor(() => expect(screen.queryByTestId("lift-type-automatic")).not.toBeNull());
    expect(select().value).toBe("Pushup");
  });

  it("posts lift_type Auto with weight 0 after only picking a video", async () => {
    (uploadVideo as jest.Mock).mockResolvedValue({ url: "u", attempt_id: "a-1", user_id: "u-1" });
    const { container } = setup(`/challenges/${CID}/upload`, { ...club, auto_lift_type_enabled: true });
    await waitFor(() => expect(select().value).toBe("Auto"));
    fireEvent.change(container.querySelector('input[type="file"]')!, {
      target: { files: [new File(["x"], "s.mp4", { type: "video/mp4" })] },
    });
    fireEvent.submit(container.querySelector("form")!);
    await waitFor(() => expect(uploadVideo).toHaveBeenCalled());
    expect((uploadVideo as jest.Mock).mock.calls[0][1]).toMatchObject({
      competition_id: CID,
      lift_type: "Auto",
      weight: "0",
      email: "sam@example.com",
    });
  });

  it("with the switch off renders exactly as today", async () => {
    setup(`/challenges/${CID}/upload`, club);
    await waitFor(() => expect(axios.get).toHaveBeenCalledWith(`https://test-api.example/competitions/${CID}`));
    expect(screen.queryByTestId("lift-type-automatic")).toBeNull();
    expect(select().value).toBe("Squat");
    expect(options()).toEqual(["Squat", "Bench Press", "Deadlift", "Pushup", "Situp"]);
    expect(screen.getByText("Weight (kg)")).toBeInTheDocument();
  });

  it("the generic /lift/upload page never asks for a competition and never offers Automatic", async () => {
    setup("/lift/upload", null);
    expect(select().value).toBe("Squat");
    expect(screen.queryByTestId("lift-type-automatic")).toBeNull();
    expect(axios.get).not.toHaveBeenCalled();
  });
});
