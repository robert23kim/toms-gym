import React from "react";
import "@testing-library/jest-dom";
import { render, screen, waitFor } from "@testing-library/react";
import axios from "axios";
import { useIsOwner } from "../useIsOwner";
import { useAuth } from "../../auth/AuthContext";

jest.mock("axios");
jest.mock("../../config", () => ({ API_URL: "https://test-api.example" }));
jest.mock("../../auth/AuthContext", () => ({ useAuth: jest.fn() }));

const Probe: React.FC<{ label?: string }> = ({ label = "probe" }) => {
  const owner = useIsOwner();
  return <span data-testid={label}>{owner ? "owner" : "guest"}</span>;
};

const profile = (email: string) => ({ data: { user: { id: "u1", name: "x", email } } });

describe("useIsOwner", () => {
  beforeEach(() => {
    (useAuth as jest.Mock).mockReturnValue({ user: null });
    (axios.get as jest.Mock).mockReset();
    (localStorage.getItem as jest.Mock).mockReset();
    (localStorage.setItem as jest.Mock).mockReset();
  });

  it("is false with no saved user and makes no request", async () => {
    (localStorage.getItem as jest.Mock).mockReturnValue(null);
    render(<Probe />);
    expect(screen.getByTestId("probe")).toHaveTextContent("guest");
    await waitFor(() => expect(axios.get).not.toHaveBeenCalled());
  });

  it("resolves a passwordless owner from the public profile and caches it", async () => {
    (localStorage.getItem as jest.Mock).mockImplementation((k: string) => (k === "userId" ? "u1" : null));
    (axios.get as jest.Mock).mockResolvedValue(profile("toka778@gmail.com"));
    render(<Probe />);
    expect(screen.getByTestId("probe")).toHaveTextContent("guest");
    await waitFor(() => expect(screen.getByTestId("probe")).toHaveTextContent("owner"));
    expect(axios.get).toHaveBeenCalledWith("https://test-api.example/users/u1/profile");
    expect(localStorage.setItem).toHaveBeenCalledWith("ownerCheck", JSON.stringify({ userId: "u1", owner: true }));
  });

  it("stays false for another saved user", async () => {
    (localStorage.getItem as jest.Mock).mockImplementation((k: string) => (k === "userId" ? "u9" : null));
    (axios.get as jest.Mock).mockResolvedValue(profile("caleb@example.com"));
    render(<Probe />);
    await waitFor(() => expect(axios.get).toHaveBeenCalled());
    await waitFor(() => expect(localStorage.setItem).toHaveBeenCalled());
    expect(screen.getByTestId("probe")).toHaveTextContent("guest");
  });

  it("stays false when the profile read fails", async () => {
    (localStorage.getItem as jest.Mock).mockImplementation((k: string) => (k === "userId" ? "u8" : null));
    (axios.get as jest.Mock).mockRejectedValue(new Error("boom"));
    render(<Probe />);
    await waitFor(() => expect(axios.get).toHaveBeenCalled());
    expect(screen.getByTestId("probe")).toHaveTextContent("guest");
  });

  it("uses the cached verdict on first render without a request", () => {
    (localStorage.getItem as jest.Mock).mockImplementation((k: string) =>
      k === "userId" ? "u1" : k === "ownerCheck" ? JSON.stringify({ userId: "u1", owner: true }) : null,
    );
    render(<Probe />);
    expect(screen.getByTestId("probe")).toHaveTextContent("owner");
    expect(axios.get).not.toHaveBeenCalled();
  });

  it("ignores a cache left by a different user", async () => {
    (localStorage.getItem as jest.Mock).mockImplementation((k: string) =>
      k === "userId" ? "u2" : k === "ownerCheck" ? JSON.stringify({ userId: "u1", owner: true }) : null,
    );
    (axios.get as jest.Mock).mockResolvedValue(profile("someone@example.com"));
    render(<Probe />);
    expect(screen.getByTestId("probe")).toHaveTextContent("guest");
    await waitFor(() => expect(axios.get).toHaveBeenCalledWith("https://test-api.example/users/u2/profile"));
  });

  it("shares one profile request between hooks mounted together", async () => {
    (localStorage.getItem as jest.Mock).mockImplementation((k: string) => (k === "userId" ? "u3" : null));
    (axios.get as jest.Mock).mockResolvedValue(profile("toka778@gmail.com"));
    render(
      <>
        <Probe label="a" />
        <Probe label="b" />
      </>,
    );
    await waitFor(() => expect(screen.getByTestId("a")).toHaveTextContent("owner"));
    await waitFor(() => expect(screen.getByTestId("b")).toHaveTextContent("owner"));
    expect(axios.get).toHaveBeenCalledTimes(1);
  });

  it("trusts the signed-in user's email without a request", () => {
    (useAuth as jest.Mock).mockReturnValue({ user: { id: "u1", name: "Toka", email: "toka778@gmail.com" } });
    (localStorage.getItem as jest.Mock).mockReturnValue(null);
    render(<Probe />);
    expect(screen.getByTestId("probe")).toHaveTextContent("owner");
    expect(axios.get).not.toHaveBeenCalled();
  });
});
