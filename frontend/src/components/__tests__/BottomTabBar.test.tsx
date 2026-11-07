import React from "react";
import "@testing-library/jest-dom";
import { render, screen } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import BottomTabBar from "../BottomTabBar";
import { useIsOwner } from "../../hooks/useIsOwner";

jest.mock("../../hooks/useIsOwner", () => ({ useIsOwner: jest.fn(() => false) }));

const renderAt = (path: string) =>
  render(
    <MemoryRouter initialEntries={[path]}>
      <BottomTabBar />
    </MemoryRouter>,
  );

describe("BottomTabBar", () => {
  afterEach(() => {
    (localStorage.getItem as jest.Mock).mockReset();
    (useIsOwner as jest.Mock).mockReturnValue(false);
  });

  it("renders four tabs for anyone but the owner, with an anonymous Me target", () => {
    renderAt("/terms");
    const hrefs = screen.getAllByRole("link").map((a) => a.getAttribute("href"));
    expect(hrefs).toEqual(["/", "/lift", "/champions", "/find-profile"]);
    expect(screen.queryByRole("link", { current: "page" })).toBeNull();
    expect(screen.getByRole("navigation").firstChild).toHaveClass("grid-cols-4");
  });

  it("adds the Bowl and Golf tabs for the owner", () => {
    (useIsOwner as jest.Mock).mockReturnValue(true);
    renderAt("/terms");
    const hrefs = screen.getAllByRole("link").map((a) => a.getAttribute("href"));
    expect(hrefs).toEqual(["/", "/lift", "/bowl", "/golf", "/champions", "/find-profile"]);
    expect(screen.getByRole("navigation").firstChild).toHaveClass("grid-cols-6");
  });

  it("marks only the Bowl tab current on a bowling route", () => {
    (useIsOwner as jest.Mock).mockReturnValue(true);
    renderAt("/bowling/insights/me");
    const current = screen.getAllByRole("link", { current: "page" });
    expect(current).toHaveLength(1);
    expect(current[0]).toHaveTextContent("Bowl");
  });

  it("marks Champions current in the hall, not Lift", () => {
    renderAt("/champions");
    const current = screen.getAllByRole("link", { current: "page" });
    expect(current).toHaveLength(1);
    expect(current[0]).toHaveTextContent("Champions");
  });

  it("points Me at the saved profile", () => {
    (localStorage.getItem as jest.Mock).mockReturnValue("u1");
    renderAt("/");
    expect(screen.getByRole("link", { name: /^me$/i })).toHaveAttribute("href", "/profile/u1");
    expect(screen.getByRole("link", { name: /home/i })).toHaveAttribute("aria-current", "page");
  });
});
