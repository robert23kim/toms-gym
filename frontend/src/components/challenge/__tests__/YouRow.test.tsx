import React from "react";
import { render, screen, fireEvent } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import "@testing-library/jest-dom";
import YouRow from "../YouRow";
import type { ChallengeLeaderboardRow } from "../../../lib/types";

const makeRow = (overrides: Partial<ChallengeLeaderboardRow> = {}): ChallengeLeaderboardRow => ({
  rank: 7,
  user_id: "me",
  name: "Toka",
  score: 18.6,
  best_by_lift: { Plank: 18.6 },
  form_score: 0.8,
  attempt_id: "a1",
  clip_url: "https://cdn/clip.mp4",
  thumbnail_url: null,
  date: "2026-07-03",
  weight_class: null,
  gender: null,
  attempt_count: 3,
  history: [],
  ...overrides,
});

describe("YouRow", () => {
  test("not-entered variant prompts an upload and fires onUpload", () => {
    const onUpload = jest.fn();
    render(
      <MemoryRouter>
        <YouRow entered={false} onUpload={onUpload} />
      </MemoryRouter>,
    );
    const row = screen.getByTestId("you-row");
    expect(row).toHaveAttribute("data-entered", "false");
    expect(row).toHaveTextContent("Not logged yet");
    expect(row).toHaveTextContent("Upload");
    fireEvent.click(row);
    expect(onUpload).toHaveBeenCalledTimes(1);
  });

  test("entered variant shows the viewer's rank and score", () => {
    render(
      <MemoryRouter>
        <YouRow entered row={makeRow()} metric="time" clipHref={null} />
      </MemoryRouter>,
    );
    const row = screen.getByTestId("you-row");
    expect(row).toHaveAttribute("data-entered", "true");
    expect(row).toHaveAttribute("data-rank", "7");
    expect(row).toHaveTextContent("18.6s");
  });

  test("entered variant renders the live goal subtitle when provided", () => {
    render(
      <MemoryRouter>
        <YouRow
          entered
          row={makeRow()}
          metric="time"
          clipHref={null}
          subtitle="3.9s to reach #6"
        />
      </MemoryRouter>,
    );
    expect(screen.getByTestId("you-row-subtitle")).toHaveTextContent("3.9s to reach #6");
  });

  test("entered variant omits the subtitle when none is given", () => {
    render(
      <MemoryRouter>
        <YouRow entered row={makeRow()} metric="time" clipHref={null} />
      </MemoryRouter>,
    );
    expect(screen.queryByTestId("you-row-subtitle")).toBeNull();
  });

  test("entered variant links the clip when resolvable", () => {
    render(
      <MemoryRouter>
        <YouRow
          entered
          row={makeRow()}
          metric="time"
          clipHref="/challenges/1/participants/me/video/5"
        />
      </MemoryRouter>,
    );
    expect(screen.getByRole("link")).toHaveAttribute(
      "href",
      "/challenges/1/participants/me/video/5",
    );
  });

  test("desktop (#1b): both variants align to the 4-column table grid", () => {
    const { rerender } = render(
      <MemoryRouter>
        <YouRow entered={false} onUpload={() => {}} />
      </MemoryRouter>,
    );
    expect(screen.getByTestId("you-row").className).toContain(
      "lg:grid-cols-[52px_1fr_120px_90px]",
    );
    rerender(
      <MemoryRouter>
        <YouRow entered row={makeRow()} metric="time" clipHref={null} />
      </MemoryRouter>,
    );
    expect(screen.getByTestId("you-row").className).toContain(
      "lg:grid-cols-[52px_1fr_120px_90px]",
    );
  });
});
