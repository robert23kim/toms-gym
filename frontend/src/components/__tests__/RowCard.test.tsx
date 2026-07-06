import React from "react";
import "@testing-library/jest-dom";
import { render, screen } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import RowCard from "../RowCard";

describe("RowCard", () => {
  it("renders link, title, pill, and default trailing label", () => {
    render(
      <MemoryRouter>
        <RowCard to="/challenges/c1" title="Summer Plank Challenge" pill="Plank" />
      </MemoryRouter>
    );
    const link = screen.getByRole("link", { name: /summer plank challenge/i });
    expect(link).toHaveAttribute("href", "/challenges/c1");
    expect(screen.getByText("Plank")).toBeInTheDocument();
    expect(screen.getByText("Open")).toBeInTheDocument();
  });

  it("omits the pill when not given and honors custom trailing", () => {
    render(
      <MemoryRouter>
        <RowCard to="/leaderboard" title="Leaderboard" trailing="View" />
      </MemoryRouter>
    );
    expect(screen.getByText("View")).toBeInTheDocument();
    expect(screen.queryByText("Open")).toBeNull();
  });
});
