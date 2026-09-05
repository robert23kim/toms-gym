import React from "react";
import { render, screen } from "@testing-library/react";
import "@testing-library/jest-dom";
import FrameStrip from "../FrameStrip";

const frames = [
  ["X"], ["7", "-"], ["X"], ["9", "/"], ["7", "/"],
  ["9", "/"], ["8", "/"], ["7", "/"], ["8", "1"], ["9", "/", "X"],
];

describe("FrameStrip inferred frames", () => {
  it("marks guessed frames and says which ones to check", () => {
    render(<FrameStrip playerName="Tom" frames={frames} inferred={[2, 9]} onChange={() => {}} />);
    expect(screen.getByText("Frames 2, 9 read from the score — check the rolls")).toBeInTheDocument();
    const guessed = screen.getByLabelText("Tom frame 2");
    expect(guessed.className).toContain("border-amber-500");
    expect(guessed).toHaveAttribute("title", expect.stringContaining("guessed"));
    expect(screen.getByLabelText("Tom frame 1").className).not.toContain("border-amber-500");
  });

  it("shows the normal complete-game line when nothing was guessed", () => {
    render(<FrameStrip playerName="Tom" frames={frames} onChange={() => {}} />);
    expect(screen.getByText("Complete game")).toBeInTheDocument();
    expect(screen.getByText("Total 162")).toBeInTheDocument();
  });
});
