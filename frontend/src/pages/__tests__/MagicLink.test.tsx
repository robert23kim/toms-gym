import React from "react";
import "@testing-library/jest-dom";
import { render, screen, waitFor } from "@testing-library/react";
import { MemoryRouter, Routes, Route } from "react-router-dom";
import axios from "axios";
import MagicLink from "../MagicLink";

// config.ts uses import.meta (Vite), which jest can't parse; mock it as the
// repo's other tests do.
jest.mock("../../config", () => ({ API_URL: "https://test-api.example" }));

jest.mock("axios", () => {
  const actual = jest.requireActual("axios");
  const mocked = { ...actual, get: jest.fn(), isAxiosError: actual.isAxiosError };
  return { ...mocked, default: mocked };
});

// jest.setup.js installs a no-op localStorage (getItem always returns
// undefined). Replace it with a working in-memory store, as tokenUtils.test
// does, so setItem/getItem round-trip.
const localStorageMock = (() => {
  let store: Record<string, string> = {};
  return {
    getItem: (key: string) => (key in store ? store[key] : null),
    setItem: (key: string, value: string) => {
      store[key] = String(value);
    },
    removeItem: (key: string) => {
      delete store[key];
    },
    clear: () => {
      store = {};
    },
  };
})();
Object.defineProperty(window, "localStorage", { value: localStorageMock });

const renderAt = (token: string) =>
  render(
    <MemoryRouter initialEntries={[`/auth/magic/${token}`]}>
      <Routes>
        <Route path="/auth/magic/:token" element={<MagicLink />} />
      </Routes>
    </MemoryRouter>
  );

describe("MagicLink", () => {
  const originalLocation = window.location;

  beforeEach(() => {
    (axios.get as jest.Mock).mockReset();
    localStorage.clear();
    // jsdom navigation: make window.location.href assignable + observable.
    delete (window as unknown as { location?: unknown }).location;
    (window as unknown as { location: { href: string } }).location = { href: "" };
  });

  afterAll(() => {
    (window as unknown as { location: Location }).location = originalLocation;
  });

  it("stores userId for a passwordless account and redirects to the profile", async () => {
    (axios.get as jest.Mock).mockResolvedValue({
      data: { user_id: "user-123", access_token: null },
    });
    renderAt("tok-abc");

    await waitFor(() => expect(localStorage.getItem("userId")).toBe("user-123"));
    expect(localStorage.getItem("auth_token")).toBeNull();
    expect(window.location.href).toBe("/profile/user-123");
  });

  it("stores the JWT for an authenticated account", async () => {
    (axios.get as jest.Mock).mockResolvedValue({
      data: { user_id: "user-9", access_token: "jwt-xyz" },
    });
    renderAt("tok-def");

    await waitFor(() => expect(localStorage.getItem("auth_token")).toBe("jwt-xyz"));
    expect(localStorage.getItem("userId")).toBe("user-9");
    expect(window.location.href).toBe("/profile/user-9");
  });

  it("shows an expired/invalid message on a dead link", async () => {
    (axios.get as jest.Mock).mockRejectedValue(new Error("400"));
    renderAt("dead-token");

    await waitFor(() =>
      expect(screen.getByText(/Sign-in link expired/i)).toBeInTheDocument()
    );
    expect(screen.getByText(/Request a new link/i)).toBeInTheDocument();
    expect(localStorage.getItem("userId")).toBeNull();
  });

  it("calls the consume endpoint exactly once (single-use guard)", async () => {
    (axios.get as jest.Mock).mockResolvedValue({
      data: { user_id: "user-1", access_token: null },
    });
    renderAt("tok-once");

    await waitFor(() => expect(localStorage.getItem("userId")).toBe("user-1"));
    expect((axios.get as jest.Mock)).toHaveBeenCalledTimes(1);
  });
});
