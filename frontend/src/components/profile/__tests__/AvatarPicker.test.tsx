import React from "react";
import "@testing-library/jest-dom";
import { render, screen, waitFor, fireEvent } from "@testing-library/react";

const mockFetchAchievements = jest.fn();
const mockSetAvatar = jest.fn();

jest.mock("../../../lib/api", () => ({
  fetchAchievements: (...args: unknown[]) => mockFetchAchievements(...args),
  setAvatar: (...args: unknown[]) => mockSetAvatar(...args),
}));

import AvatarPicker from "../AvatarPicker";

const achievements = {
  ladder: [
    { key: "first_steps", tier: 1, title: "First Steps", emoji: "🌱" },
    { key: "half_minute", tier: 2, title: "Half Minute", emoji: "⏱️" },
  ],
  earned: ["first_steps"],
  next: { key: "half_minute", title: "Half Minute", emoji: "⏱️", tier: 2 },
  avatar: "avataaars-ace",
  avatars: [
    { key: "avataaars-ace", url: "https://dicebear/ace" },
    { key: "avataaars-blaze", url: "https://dicebear/blaze" },
  ],
  locked_packs: [
    { key: "half_minute", title: "Half Minute", emoji: "⏱️", hint: "Hold a plank for 30s" },
    { key: "champion", title: "Champion", emoji: "👑", hint: "Win a challenge" },
  ],
};

describe("AvatarPicker", () => {
  beforeEach(() => {
    mockFetchAchievements.mockReset().mockResolvedValue(achievements);
    mockSetAvatar.mockReset().mockResolvedValue({
      avatar: "avataaars-blaze",
      avatar_url: "https://dicebear/blaze",
    });
  });

  it("shows unlocked avatars as selectable", async () => {
    render(<AvatarPicker userId="u1" onSelected={jest.fn()} />);
    await waitFor(() =>
      expect(screen.getByLabelText("Choose avatar avataaars-blaze")).toBeInTheDocument(),
    );
  });

  it("lists locked packs with their milestone hints", async () => {
    render(<AvatarPicker userId="u1" onSelected={jest.fn()} />);
    await waitFor(() =>
      expect(screen.getByTestId("locked-pack-half_minute")).toBeInTheDocument(),
    );
    expect(screen.getByText(/Hold a plank for 30s/)).toBeInTheDocument();
    expect(screen.getByTestId("locked-pack-champion")).toBeInTheDocument();
    expect(screen.getByText(/Win a challenge/)).toBeInTheDocument();
  });

  it("saves the picked avatar and reports it upward", async () => {
    const onSelected = jest.fn();
    render(<AvatarPicker userId="u1" onSelected={onSelected} />);
    await waitFor(() =>
      expect(screen.getByLabelText("Choose avatar avataaars-blaze")).toBeInTheDocument(),
    );
    fireEvent.click(screen.getByLabelText("Choose avatar avataaars-blaze"));
    await waitFor(() =>
      expect(mockSetAvatar).toHaveBeenCalledWith("u1", "avataaars-blaze"),
    );
    expect(onSelected).toHaveBeenCalledWith("https://dicebear/blaze");
  });

  it("keeps the prior selection when the save is rejected", async () => {
    mockSetAvatar.mockRejectedValue(new Error("locked"));
    const onSelected = jest.fn();
    render(<AvatarPicker userId="u1" onSelected={onSelected} />);
    await waitFor(() =>
      expect(screen.getByLabelText("Choose avatar avataaars-blaze")).toBeInTheDocument(),
    );
    fireEvent.click(screen.getByLabelText("Choose avatar avataaars-blaze"));
    await waitFor(() =>
      expect(screen.getByText(/Could not save that avatar/)).toBeInTheDocument(),
    );
    expect(onSelected).not.toHaveBeenCalled();
  });
});
