import React from "react";
import "@testing-library/jest-dom";
import { render, screen } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import BottomTabBar from "../BottomTabBar";

const renderAt = (path: string) =>
  render(
    <MemoryRouter initialEntries={[path]}>
      <BottomTabBar />
    </MemoryRouter>,
  );

describe("BottomTabBar", () => {
  afterEach(() => (localStorage.getItem as jest.Mock).mockReset());

  it("renders the five tabs with an anonymous Me target", () => {
    renderAt("/terms");
    const hrefs = screen.getAllByRole("link").map((a) => a.getAttribute("href"));
    expect(hrefs).toEqual(["/", "/lift", "/bowl", "/golf", "/find-profile"]);
    expect(screen.queryByRole("link", { current: "page" })).toBeNull();
  });

  it("marks only the Bowl tab current on a bowling route", () => {
    renderAt("/bowling/insights/me");
    const current = screen.getAllByRole("link", { current: "page" });
    expect(current).toHaveLength(1);
    expect(current[0]).toHaveTextContent("Bowl");
  });

  it("points Me at the saved profile", () => {
    (localStorage.getItem as jest.Mock).mockReturnValue("u1");
    renderAt("/");
    expect(screen.getByRole("link", { name: /^me$/i })).toHaveAttribute("href", "/profile/u1");
    expect(screen.getByRole("link", { name: /home/i })).toHaveAttribute("aria-current", "page");
  });
});
