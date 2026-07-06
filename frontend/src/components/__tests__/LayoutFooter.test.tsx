import React from "react";
import "@testing-library/jest-dom";
import { render, screen } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import Layout from "../Layout";

// config.ts uses import.meta (Vite), which jest can't parse; mock it as the
// repo's other tests do.
jest.mock("../../config", () => ({ API_URL: "https://test-api.example", APP_VERSION: "test" }));

// Navbar pulls in the auth tree; stub it so the test stays on the footer.
jest.mock("../Navbar", () => ({
  __esModule: true,
  default: () => <nav />,
}));

describe("Layout footer", () => {
  it("links Report a bug and Request a feature to /feedback", () => {
    render(
      <MemoryRouter>
        <Layout>content</Layout>
      </MemoryRouter>
    );
    expect(screen.getByRole("link", { name: /report a bug/i })).toHaveAttribute("href", "/feedback");
    expect(screen.getByRole("link", { name: /request a feature/i })).toHaveAttribute("href", "/feedback");
    expect(screen.getByRole("link", { name: /terms/i })).toHaveAttribute("href", "/terms");
    expect(screen.getByRole("link", { name: /privacy/i })).toHaveAttribute("href", "/privacy");
  });
});
