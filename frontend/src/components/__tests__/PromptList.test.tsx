import React from "react";
import "@testing-library/jest-dom";
import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import PromptList from "../home/PromptList";
import { buildPrompts } from "../../lib/prompts";
import { todayLocal } from "../../lib/dates";
import * as api from "../../lib/api";

jest.mock("../../config", () => ({ API_URL: "https://test-api.example" }));

const mockNavigate = jest.fn();
jest.mock("react-router-dom", () => ({
  ...jest.requireActual("react-router-dom"),
  useNavigate: () => mockNavigate,
}));

jest.mock("../../lib/api", () => ({
  ...jest.requireActual("../../lib/api"),
  uploadBowlingSheet: jest.fn(),
}));

const prompts = buildPrompts([{ id: "c1", title: "Situps", categories: ["Situp"] }]);
const photo = new File(["jpg"], "screen.jpg", { type: "image/jpeg" });

const renderList = (userId: string | null) =>
  render(
    <MemoryRouter>
      <PromptList prompts={prompts} userId={userId} />
    </MemoryRouter>,
  );

describe("PromptList", () => {
  beforeEach(() => jest.clearAllMocks());

  it("sends anonymous visitors to the snap page instead of the camera", () => {
    renderList(null);
    expect(screen.getByText("Snap tonight's scores").closest("a")).toHaveAttribute("href", "/bowling/snap");
    expect(screen.queryByTestId("home-bowl-camera")).toBeNull();
    expect(screen.getByText("Situps").closest("a")).toHaveAttribute("href", "/challenges/c1/upload");
    expect(screen.getByText("Situp")).toBeInTheDocument();
    expect(screen.getByText("Snap a scorecard").closest("a")).toHaveAttribute("href", "/golf/snap");
    expect(screen.getByText("Log a lift").closest("a")).toHaveAttribute("href", "/lift/upload");
  });

  it("uploads the photo as tonight's night results and opens the review page", async () => {
    (api.uploadBowlingSheet as jest.Mock).mockResolvedValue({ sheet_id: "s1" });
    renderList("u1");
    expect(screen.getByText("Snap tonight's scores").closest("a")).toBeNull();
    fireEvent.change(screen.getByTestId("home-bowl-camera"), { target: { files: [photo] } });
    await waitFor(() => expect(mockNavigate).toHaveBeenCalledWith("/bowling/scoresheet/s1"));
    expect(api.uploadBowlingSheet).toHaveBeenCalledTimes(1);
    const form = (api.uploadBowlingSheet as jest.Mock).mock.calls[0][0] as FormData;
    expect(form.get("image")).toBe(photo);
    expect(form.get("sheet_type")).toBe("night");
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
    expect(screen.getByText("Snap tonight's scores")).toBeInTheDocument();
  });
});
