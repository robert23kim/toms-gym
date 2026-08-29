import React from "react";
import "@testing-library/jest-dom";
import { fireEvent, render, screen } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import axios from "axios";
import FindProfilePage from "../FindProfilePage";

jest.mock("../../config", () => ({ API_URL: "https://test-api.example" }));
jest.mock("../../components/Layout", () => ({
  __esModule: true,
  default: ({ children }: { children: React.ReactNode }) => <div>{children}</div>,
}));
jest.mock("../../components/GhibliAvatar", () => ({
  __esModule: true,
  default: ({ name }: { name: string }) => <div>avatar:{name}</div>,
}));
jest.mock("axios", () => {
  const actual = jest.requireActual("axios");
  const mocked = { ...actual, get: jest.fn() };
  return { ...mocked, default: mocked };
});

const lookup = (lifts: object[]) =>
  (axios.get as jest.Mock).mockImplementation((url: string) =>
    url.includes("/by-email/")
      ? Promise.resolve({ data: { id: "u1", name: "Sam Lee", email: "sam@example.com" } })
      : Promise.resolve({ data: { lifts } }),
  );

const submit = () => {
  render(
    <MemoryRouter>
      <FindProfilePage />
    </MemoryRouter>,
  );
  fireEvent.change(screen.getByPlaceholderText("your@email.com"), { target: { value: "sam@example.com" } });
  fireEvent.click(screen.getByRole("button", { name: /Find my profile/i }));
};

describe("FindProfilePage", () => {
  beforeEach(() => (localStorage.setItem as jest.Mock).mockClear());

  it("welcomes the person back by name with their last lift, and remembers them", async () => {
    lookup([{ lift_type: "Bench Press", weight: 80, grade: "D", created_at: "2026-04-12T10:00:00Z" }]);
    submit();

    expect(await screen.findByText("Welcome back, Sam")).toBeInTheDocument();
    expect(screen.getByText(/Last lift · .* ago/)).toBeInTheDocument();
    expect(screen.getByText(/Bench press · 80kg · D/)).toBeInTheDocument();
    expect(screen.getByRole("link", { name: /Open my profile/i })).toHaveAttribute("href", "/profile/u1");
    expect(screen.getByRole("link", { name: /Upload a new lift/i })).toHaveAttribute("href", "/lift/upload");
    expect(localStorage.setItem).toHaveBeenCalledWith("userId", "u1");
    expect(screen.queryByText("Who am I?")).toBeNull();
  });

  it("still welcomes someone with no lifts yet", async () => {
    lookup([]);
    submit();
    expect(await screen.findByText("Your profile is ready.")).toBeInTheDocument();
  });
});
