import React from "react";
import "@testing-library/jest-dom";
import { render, screen } from "@testing-library/react";
import VideoCaptureInput from "../VideoCaptureInput";

describe("VideoCaptureInput", () => {
  const noop = () => {};

  it("renders a camera input with capture and a library input without", () => {
    render(<VideoCaptureInput selectedFileName={null} onFileSelect={noop} />);
    const camera = document.getElementById("challenge-video-camera");
    const library = document.getElementById("challenge-video-upload");
    expect(camera!.getAttribute("capture")).toBe("environment");
    expect(camera!.getAttribute("accept")).toBe("video/*");
    expect(library!.hasAttribute("capture")).toBe(false);
    expect(library!.getAttribute("accept")).toBe("video/*");
  });

  it("shows both affordances and the selected file name", () => {
    render(<VideoCaptureInput selectedFileName="plank.mp4" onFileSelect={noop} />);
    expect(screen.getByText(/record now/i)).toBeInTheDocument();
    expect(screen.getByText(/choose existing video/i)).toBeInTheDocument();
    expect(screen.getByText("plank.mp4")).toBeInTheDocument();
  });
});
