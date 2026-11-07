import React from "react";
import "@testing-library/jest-dom";
import { render, screen } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import Navbar from "../Navbar";
import { useIsOwner } from "../../hooks/useIsOwner";

jest.mock("../../auth/AuthContext", () => ({
  useAuth: () => ({ isAuthenticated: false, user: null, logout: jest.fn() }),
}));
jest.mock("../../hooks/useIsOwner", () => ({ useIsOwner: jest.fn(() => false) }));

const labels = () =>
  screen
    .getAllByRole("link")
    .map((a) => a.getAttribute("href"))
    .filter((h): h is string => Boolean(h));

describe("Navbar verticals", () => {
  beforeEach(() => (localStorage.getItem as jest.Mock).mockReturnValue(null));
  afterEach(() => {
    (localStorage.getItem as jest.Mock).mockReset();
    (useIsOwner as jest.Mock).mockReturnValue(false);
  });

  it("hides Bowl and Golf for anyone but the owner", () => {
    render(
      <MemoryRouter>
        <Navbar />
      </MemoryRouter>,
    );
    const hrefs = labels();
    expect(hrefs).toContain("/lift");
    expect(hrefs).toContain("/challenges");
    expect(hrefs).not.toContain("/bowl");
    expect(hrefs).not.toContain("/golf");
  });

  it("shows Bowl and Golf to the owner", () => {
    (useIsOwner as jest.Mock).mockReturnValue(true);
    render(
      <MemoryRouter>
        <Navbar />
      </MemoryRouter>,
    );
    const hrefs = labels();
    expect(hrefs).toContain("/bowl");
    expect(hrefs).toContain("/golf");
  });
});
