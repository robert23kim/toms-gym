import React from "react";
import "@testing-library/jest-dom";
import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import Navbar from "../Navbar";

const mockRemove = jest.fn(async (_: { key: string }) => undefined);
jest.mock("@capacitor/core", () => ({ Capacitor: { isNativePlatform: () => true } }));
jest.mock("@capacitor/preferences", () => ({
  Preferences: { get: jest.fn(), set: jest.fn(async () => undefined), remove: (a: { key: string }) => mockRemove(a) },
}));
jest.mock("../../auth/AuthContext", () => ({
  useAuth: () => ({ isAuthenticated: false, user: null, logout: jest.fn() }),
}));
jest.mock("../../hooks/useIsOwner", () => ({ useIsOwner: jest.fn(() => false) }));

it("Forget Me clears the remembered identity in localStorage and in the APK's native mirror", async () => {
  (localStorage.getItem as jest.Mock).mockImplementation((k: string) => (k === "userId" ? "u-1" : null));
  render(
    <MemoryRouter>
      <Navbar />
    </MemoryRouter>,
  );
  fireEvent.click(screen.getAllByText("Forget Me")[0]);
  await waitFor(() => expect(mockRemove).toHaveBeenCalledWith({ key: "userId" }));
  expect(mockRemove).toHaveBeenCalledWith({ key: "userEmail" });
  expect(localStorage.removeItem).toHaveBeenCalledWith("userId");
  expect(localStorage.removeItem).toHaveBeenCalledWith("userEmail");
  (localStorage.getItem as jest.Mock).mockReset();
});
