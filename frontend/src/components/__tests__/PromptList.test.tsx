import React from "react";
import "@testing-library/jest-dom";
import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import PromptList from "../home/PromptList";
import { buildPrompts } from "../../lib/prompts";
import { todayLocal } from "../../lib/dates";
import * as api from "../../lib/api";
import * as resumable from "../../lib/resumableUpload";

jest.mock("../../config", () => ({ API_URL: "https://test-api.example" }));

const mockNavigate = jest.fn();
jest.mock("react-router-dom", () => ({
  ...jest.requireActual("react-router-dom"),
  useNavigate: () => mockNavigate,
}));

jest.mock("../../lib/api", () => ({
  ...jest.requireActual("../../lib/api"),
  uploadBowlingSheet: jest.fn(),
  triggerLiftingAnalysis: jest.fn(),
}));

jest.mock("../../lib/resumableUpload", () => ({ uploadVideo: jest.fn() }));
jest.mock("../../lib/telemetry", () => ({ reportUploadError: jest.fn() }));

const prompts = buildPrompts([
  { id: "c1", title: "Situp challenge", categories: ["Situp"] },
  { id: "c2", title: "Squat-off", categories: ["Squat"] },
]);
const photo = new File(["jpg"], "screen.jpg", { type: "image/jpeg" });
const clip = new File(["mp4"], "situps.mp4", { type: "video/mp4" });

const renderList = (userId: string | null) =>
  render(
    <MemoryRouter>
      <PromptList prompts={prompts} userId={userId} />
    </MemoryRouter>,
  );

describe("PromptList", () => {
  beforeEach(() => jest.clearAllMocks());

  it("sends anonymous visitors to the pages instead of the pickers", () => {
    renderList(null);
    expect(screen.getByText("Snap tonight's bowling recap").closest("a")).toHaveAttribute("href", "/bowling/snap");
    expect(screen.getByText("Snap a bowling game").closest("a")).toHaveAttribute("href", "/bowling/snap");
    expect(screen.queryByTestId("home-bowl-camera")).toBeNull();
    expect(screen.queryByTestId("home-game-camera")).toBeNull();
    expect(screen.getByText("Situp challenge").closest("a")).toHaveAttribute("href", "/challenges/c1");
    expect(screen.getByText("Squat-off").closest("a")).toHaveAttribute("href", "/challenges/c2");
    expect(screen.getByText("Snap a scorecard").closest("a")).toHaveAttribute("href", "/golf/snap");
    expect(screen.getByText("Log a lift").closest("a")).toHaveAttribute("href", "/lift/upload");
  });

  it("offers camera and library pickers on both bowling rows", () => {
    renderList("u1");
    for (const base of ["home-bowl", "home-game"]) {
      expect(screen.getByTestId(`${base}-camera`)).toHaveAttribute("capture", "environment");
      expect(screen.getByTestId(`${base}-library`)).not.toHaveAttribute("capture");
      expect(screen.getByTestId(`${base}-library`)).toHaveAttribute("accept", "image/*");
    }
  });

  it.each([
    ["home-bowl-camera", "night"],
    ["home-bowl-library", "night"],
    ["home-game-camera", "game"],
    ["home-game-library", "game"],
  ])("%s uploads the photo as a %s sheet dated today and opens the review page", async (inputId, sheetType) => {
    (api.uploadBowlingSheet as jest.Mock).mockResolvedValue({ sheet_id: "s1" });
    renderList("u1");
    expect(screen.getByText("Snap tonight's bowling recap").closest("a")).toBeNull();
    expect(screen.getByText("Snap a bowling game").closest("a")).toBeNull();
    fireEvent.change(screen.getByTestId(inputId), { target: { files: [photo] } });
    await waitFor(() => expect(mockNavigate).toHaveBeenCalledWith("/bowling/scoresheet/s1"));
    expect(api.uploadBowlingSheet).toHaveBeenCalledTimes(1);
    const form = (api.uploadBowlingSheet as jest.Mock).mock.calls[0][0] as FormData;
    expect(form.get("image")).toBe(photo);
    expect(form.get("sheet_type")).toBe(sheetType);
    expect(form.get("played_on")).toBe(todayLocal());
    expect(form.get("user_id")).toBe("u1");
  });

  it("shows the upload error on the row and stays put", async () => {
    (api.uploadBowlingSheet as jest.Mock).mockRejectedValue({
      isAxiosError: true,
      response: { status: 400, data: { error: "too blurry" } },
    });
    renderList("u1");
    fireEvent.change(screen.getByTestId("home-bowl-camera"), { target: { files: [photo] } });
    await waitFor(() => expect(screen.getByText(/too blurry/)).toBeInTheDocument());
    expect(mockNavigate).not.toHaveBeenCalled();
    expect(screen.getByText("Snap tonight's bowling recap")).toBeInTheDocument();
  });

  it("gives a bodyweight challenge record and upload pickers, and keeps weighted ones as links", () => {
    renderList("u1");
    expect(screen.getByTestId("home-challenge-c1-record")).toHaveAttribute("capture", "environment");
    expect(screen.getByTestId("home-challenge-c1-upload")).toHaveAttribute("accept", "video/*");
    expect(screen.getByText("Situp challenge").closest("a")).toBeNull();
    expect(screen.getByText("Squat-off").closest("a")).toHaveAttribute("href", "/challenges/c2");
  });

  it.each(["home-challenge-c1-record", "home-challenge-c1-upload"])(
    "%s uploads the clip with the challenge's lift type, starts analysis and opens the status page",
    async (inputId) => {
      (resumable.uploadVideo as jest.Mock).mockResolvedValue({ url: "gs://x", attempt_id: "a9" });
      (api.triggerLiftingAnalysis as jest.Mock).mockResolvedValue({});
      renderList("u1");
      fireEvent.change(screen.getByTestId(inputId), { target: { files: [clip] } });
      await waitFor(() => expect(mockNavigate).toHaveBeenCalledWith("/lift/status/a9?challenge=c1"));
      expect(resumable.uploadVideo).toHaveBeenCalledTimes(1);
      const [file, fields, , options] = (resumable.uploadVideo as jest.Mock).mock.calls[0];
      expect(file).toBe(clip);
      expect(fields).toEqual({ competition_id: "c1", lift_type: "Situp", weight: "0", user_id: "u1" });
      expect(options).toEqual({ compression: "auto" });
      expect(api.triggerLiftingAnalysis).toHaveBeenCalledWith("a9");
    },
  );

  it("shows upload progress on the challenge row while the video is in flight", async () => {
    let resolveUpload: (v: unknown) => void = () => {};
    (resumable.uploadVideo as jest.Mock).mockImplementation((_f, _fields, onProgress) => {
      onProgress(42);
      return new Promise((res) => (resolveUpload = res));
    });
    renderList("u1");
    fireEvent.change(screen.getByTestId("home-challenge-c1-record"), { target: { files: [clip] } });
    await waitFor(() => expect(screen.getByText("Uploading 42%")).toBeInTheDocument());
    resolveUpload({ url: "gs://x", attempt_id: "a1" });
    await waitFor(() => expect(mockNavigate).toHaveBeenCalled());
  });

  it("keeps the challenge row when the video upload fails", async () => {
    (resumable.uploadVideo as jest.Mock).mockRejectedValue({
      isAxiosError: true,
      response: { status: 500, data: { error: "bucket down" } },
    });
    renderList("u1");
    fireEvent.change(screen.getByTestId("home-challenge-c1-upload"), { target: { files: [clip] } });
    await waitFor(() => expect(screen.getByText(/bucket down/)).toBeInTheDocument());
    expect(mockNavigate).not.toHaveBeenCalled();
    expect(api.triggerLiftingAnalysis).not.toHaveBeenCalled();
  });
});
