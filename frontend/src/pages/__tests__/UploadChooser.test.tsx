import React from "react";
import "@testing-library/jest-dom";
import { render, screen } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import UploadChooser from "../UploadChooser";
import { useIsOwner } from "../../hooks/useIsOwner";

jest.mock("../../components/Layout", () => ({
  __esModule: true,
  default: ({ children }: { children: React.ReactNode }) => <div>{children}</div>,
}));
jest.mock("../../hooks/useIsOwner", () => ({ useIsOwner: jest.fn(() => false) }));

const hrefs = () => screen.getAllByRole("link").map((a) => a.getAttribute("href"));

describe("UploadChooser", () => {
  afterEach(() => (useIsOwner as jest.Mock).mockReturnValue(false));

  it("offers only the lift upload to anyone but the owner", () => {
    render(
      <MemoryRouter>
        <UploadChooser />
      </MemoryRouter>,
    );
    expect(hrefs()).toEqual(["/lift/upload"]);
  });

  it("offers all three uploads to the owner", () => {
    (useIsOwner as jest.Mock).mockReturnValue(true);
    render(
      <MemoryRouter>
        <UploadChooser />
      </MemoryRouter>,
    );
    expect(hrefs()).toEqual(["/lift/upload", "/bowling/upload", "/golf/snap"]);
  });
});
