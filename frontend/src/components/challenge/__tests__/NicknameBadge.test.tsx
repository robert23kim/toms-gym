import React from "react";
import "@testing-library/jest-dom";
import { render, screen } from "@testing-library/react";
import NicknameBadge from "../NicknameBadge";

describe("NicknameBadge", () => {
  it("renders the emoji and name", () => {
    render(<NicknameBadge nickname={{ name: "Statue", emoji: "🗿" }} />);
    expect(screen.getByText(/Statue/)).toBeInTheDocument();
    expect(screen.getByText(/🗿/)).toBeInTheDocument();
  });

  it("renders nothing when nickname is null", () => {
    const { container } = render(<NicknameBadge nickname={null} />);
    expect(container.firstChild).toBeNull();
  });
});
