import React from "react";
import { render } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import GolfUpload from "../GolfUpload";

// config.ts uses import.meta (Vite), which jest can't parse; mock it as the
// repo's other tests do.
jest.mock("../../config", () => ({ API_URL: "https://test-api.example" }));

// Layout pulls in the Navbar/auth tree; stub it so the test stays focused on
// the capture inputs.
jest.mock("../../components/Layout", () => ({
  __esModule: true,
  default: ({ children }: { children: React.ReactNode }) => <div>{children}</div>,
}));

// FairwayScope imports a raw .css file jest can't parse; stub to a passthrough.
jest.mock("../../components/FairwayScope", () => ({
  __esModule: true,
  default: ({ children }: { children: React.ReactNode }) => <div>{children}</div>,
}));

jest.mock("axios");

const renderPage = (props = {}) =>
  render(
    <MemoryRouter>
      <GolfUpload {...props} />
    </MemoryRouter>
  );

describe("GolfUpload capture inputs", () => {
  it("has a camera input with capture=environment and a library input without capture", () => {
    renderPage();
    const camera = document.getElementById("golf-scorecard-camera");
    const library = document.getElementById("golf-scorecard-upload");
    expect(camera).not.toBeNull();
    expect(camera!.getAttribute("capture")).toBe("environment");
    expect(camera!.getAttribute("accept")).toBe("image/*");
    expect(library).not.toBeNull();
    expect(library!.hasAttribute("capture")).toBe(false);
  });

  it("auto-clicks the camera input when autoCamera is set", () => {
    const clickSpy = jest
      .spyOn(HTMLInputElement.prototype, "click")
      .mockImplementation(() => {});
    renderPage({ autoCamera: true });
    expect(clickSpy).toHaveBeenCalled();
    clickSpy.mockRestore();
  });
});
