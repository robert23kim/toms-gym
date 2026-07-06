import React from "react";
import "@testing-library/jest-dom";
import { render, screen } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import IconTile from "../IconTile";

describe("IconTile", () => {
  it("renders an accessible link tile with title and description", () => {
    render(
      <MemoryRouter>
        <IconTile to="/lift/upload" icon={<span data-testid="ic" />} title="Lift" description="Per-rep grades." />
      </MemoryRouter>
    );
    const link = screen.getByRole("link", { name: /lift/i });
    expect(link).toHaveAttribute("href", "/lift/upload");
    expect(screen.getByText("Per-rep grades.")).toBeInTheDocument();
    expect(screen.getByTestId("ic")).toBeInTheDocument();
  });
});
