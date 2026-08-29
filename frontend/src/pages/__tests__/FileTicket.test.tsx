import React from "react";
import "@testing-library/jest-dom";
import { render, screen } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import FileTicket from "../FileTicket";

jest.mock("../../config", () => ({ API_URL: "http://test" }));
jest.mock("../../components/Layout", () => ({
  __esModule: true,
  default: ({ children }: { children: React.ReactNode }) => <div>{children}</div>,
}));
jest.mock("../../lib/api", () => ({
  createTicket: jest.fn(),
}));

const renderAt = (path: string) =>
  render(
    <MemoryRouter initialEntries={[path]}>
      <FileTicket />
    </MemoryRouter>,
  );

describe("FileTicket default type", () => {
  it("defaults to bug", () => {
    renderAt("/feedback");
    expect(screen.getByRole("button", { name: /report a bug/i })).toHaveAttribute("aria-pressed", "true");
  });

  it("preselects feature when ?type=feature", () => {
    renderAt("/feedback?type=feature");
    expect(screen.getByRole("button", { name: /request a feature/i })).toHaveAttribute("aria-pressed", "true");
  });

  it("falls back to bug on an unknown type", () => {
    renderAt("/feedback?type=bogus");
    expect(screen.getByRole("button", { name: /report a bug/i })).toHaveAttribute("aria-pressed", "true");
  });
});
