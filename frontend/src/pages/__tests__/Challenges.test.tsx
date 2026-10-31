import React from "react";
import "@testing-library/jest-dom";
import { render, screen, waitFor } from "@testing-library/react";
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

const rowFor = (title: string) => screen.getAllByText(title).map((el) => el.closest("a") as HTMLElement);

describe("Challenges list pills", () => {
  beforeEach(() => {
    (axios.get as jest.Mock).mockResolvedValue({ data: { competitions: [club, legacy] } });
  });

  it("labels The 100 Club as a consistency challenge, not by its first lift type", async () => {
    render(
      <MemoryRouter>
        <Challenges />
      </MemoryRouter>,
    );
    await waitFor(() => expect(screen.getAllByText("The 100 Club")).toHaveLength(2));
    for (const row of rowFor("The 100 Club")) {
      expect(row).toHaveTextContent("Consistency");
      expect(row).not.toHaveTextContent("Situp");
    }
    for (const row of rowFor("Biceps and Bench")) {
      expect(row).toHaveTextContent("Bench Press");
    }
  });
});
