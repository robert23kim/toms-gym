import React from "react";
import "@testing-library/jest-dom";
import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import axios from "axios";
import Challenges from "../Challenges";

jest.mock("axios");
jest.mock("../../config", () => ({
  API_URL: "https://test-api.example",
  COMPETITIONS_API_URL: "https://test-api.example",
}));
jest.mock("../../components/Layout", () => ({
  __esModule: true,
  default: ({ children }: { children: React.ReactNode }) => <div>{children}</div>,
}));
jest.mock("../../components/CreateChallenge", () => ({
  __esModule: true,
  default: () => null,
}));

const club = {
  id: "32ca7bad-a970-4a09-acec-02b768793063",
  name: "The 100 Club",
  start_date: "2026-10-01T00:00:00+00:00",
  end_date: "2099-12-28T04:59:59+00:00",
  description:
    '100 lifts a week. Situps, pushups, squats or planks. Hit it and the bar rises. - {"lifttypes": ["Situp", "Pushup", "Squat", "Plank"], "weightclasses": [], "gender": "", "mode": "consistency", "rules": {"base_quota": 100, "ramp": 25, "weeks": 8}}',
};
const legacy = {
  id: "857fc561-69f7-4ed5-85a8-cdeb331087b3",
  name: "Biceps and Bench",
  start_date: "2026-01-31T00:00:00+00:00",
  end_date: "2099-04-04T00:00:00+00:00",
  description: 'Tom\'s Gym - {"lifttypes": ["Bench Press", "Curls"], "weightclasses": [], "gender": "Open"}',
};

const ended = {
  id: "0d1f2a3b-0000-4000-8000-000000000001",
  name: "Old Squat-Off",
  start_date: "2025-01-01T00:00:00+00:00",
  end_date: "2025-02-01T00:00:00+00:00",
  description: 'Tom\'s Gym - {"lifttypes": ["Squat"], "weightclasses": [], "gender": "Open"}',
};
const soon = {
  id: "0d1f2a3b-0000-4000-8000-000000000002",
  name: "Winter Deadlift",
  start_date: "2099-01-01T00:00:00+00:00",
  end_date: "2099-02-01T00:00:00+00:00",
  description: 'Tom\'s Gym - {"lifttypes": ["Deadlift"], "weightclasses": [], "gender": "Open"}',
};

const rowFor = (title: string) => screen.getAllByText(title).map((el) => el.closest("a") as HTMLElement);

const renderPage = () =>
  render(
    <MemoryRouter>
      <Challenges />
    </MemoryRouter>,
  );

describe("Challenges list", () => {
  beforeEach(() => {
    (axios.get as jest.Mock).mockResolvedValue({ data: { competitions: [club, legacy, ended, soon] } });
  });

  it("shows open and upcoming challenges once each and hides past ones behind a toggle", async () => {
    renderPage();
    await waitFor(() => expect(screen.getAllByText("The 100 Club")).toHaveLength(1));
    expect(screen.getByText("Open now")).toBeInTheDocument();
    expect(screen.getByText("Coming up")).toBeInTheDocument();
    expect(screen.getByText("Winter Deadlift").closest("a")).toHaveTextContent("Preview");
    expect(screen.queryByText("Old Squat-Off")).toBeNull();
    const toggle = screen.getByTestId("past-challenges-toggle");
    expect(toggle).toHaveTextContent("Past challenges (1)");
    expect(toggle).toHaveAttribute("aria-expanded", "false");
    fireEvent.click(toggle);
    expect(screen.getByText("Old Squat-Off").closest("a")).toHaveTextContent("Results");
    expect(toggle).toHaveTextContent("Hide past challenges");
    fireEvent.click(toggle);
    expect(screen.queryByText("Old Squat-Off")).toBeNull();
  });

  it("omits the past toggle when nothing has ended", async () => {
    (axios.get as jest.Mock).mockResolvedValue({ data: { competitions: [club] } });
    renderPage();
    await waitFor(() => expect(screen.getAllByText("The 100 Club")).toHaveLength(1));
    expect(screen.queryByTestId("past-challenges-toggle")).toBeNull();
    expect(screen.queryByText("Coming up")).toBeNull();
  });

  it("says so when every challenge has ended", async () => {
    (axios.get as jest.Mock).mockResolvedValue({ data: { competitions: [ended] } });
    renderPage();
    await waitFor(() => expect(screen.getByText("No open challenges right now.")).toBeInTheDocument());
    expect(screen.getByTestId("past-challenges-toggle")).toHaveTextContent("Past challenges (1)");
  });

  it("labels The 100 Club as a consistency challenge, not by its first lift type", async () => {
    renderPage();
    await waitFor(() => expect(screen.getAllByText("The 100 Club")).toHaveLength(1));
    for (const row of rowFor("The 100 Club")) {
      expect(row).toHaveTextContent("Consistency");
      expect(row).not.toHaveTextContent("Situp");
    }
    for (const row of rowFor("Biceps and Bench")) {
      expect(row).toHaveTextContent("Bench Press");
    }
  });
});
