import React from "react";
import "@testing-library/jest-dom";
import { fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import LiftTypeLine from "../LiftTypeLine";
import { changeLiftType } from "../../../lib/api";

jest.mock("../../../lib/api", () => ({ changeLiftType: jest.fn() }));

const CANDIDATES = ["Situp", "Pushup", "Squat", "Plank"];
const base = {
  attemptId: "a-1",
  viewerId: "u-1",
  isOwner: true,
  candidates: CANDIDATES,
  liftType: "Pushup",
  source: "auto" as const,
  confidence: 0.92,
  needsLiftType: false,
};

describe("LiftTypeLine", () => {
  beforeEach(() => jest.clearAllMocks());

  test("automatic: counted as the detected type, marked Automatic, with Change", () => {
    render(<LiftTypeLine {...base} onRequeued={jest.fn()} />);
    const line = screen.getByTestId("lift-type-line");
    expect(line).toHaveAttribute("data-state", "automatic");
    expect(line).toHaveTextContent(/^Counted as Pushups · Automatic\s*Change$/);
    expect(within(line).getByRole("button", { name: "Change" })).toBeInTheDocument();
  });

  test("manual: counted as the picked type, no Automatic", () => {
    render(<LiftTypeLine {...base} source="user" confidence={null} onRequeued={jest.fn()} />);
    const line = screen.getByTestId("lift-type-line");
    expect(line).toHaveAttribute("data-state", "manual");
    expect(line).toHaveTextContent(/^Counted as Pushups\s*Change$/);
  });

  test("low confidence asks, with Yes and Change", () => {
    render(<LiftTypeLine {...base} confidence={0.41} onRequeued={jest.fn()} />);
    const line = screen.getByTestId("lift-type-line");
    expect(line).toHaveAttribute("data-state", "confirm");
    expect(line).toHaveTextContent("Is this a pushup?");
    expect(within(line).getByRole("button", { name: "Yes" })).toBeInTheDocument();
    expect(within(line).getByRole("button", { name: "Change" })).toBeInTheDocument();
  });

  test("exactly at the threshold counts as confident", () => {
    render(<LiftTypeLine {...base} confidence={0.6} onRequeued={jest.fn()} />);
    expect(screen.getByTestId("lift-type-line")).toHaveAttribute("data-state", "automatic");
  });

  test("no detection asks which lift, with Change only", () => {
    render(<LiftTypeLine {...base} liftType="Auto" confidence={0} needsLiftType onRequeued={jest.fn()} />);
    const line = screen.getByTestId("lift-type-line");
    expect(line).toHaveAttribute("data-state", "confirm");
    expect(line).toHaveTextContent("Which lift is this?");
    expect(within(line).queryByRole("button", { name: "Yes" })).toBeNull();
  });

  test("Yes confirms through the endpoint and settles as manual without re-analysing", async () => {
    (changeLiftType as jest.Mock).mockResolvedValue({ attempt_id: "a-1", lift_type: "Pushup", status: "unchanged" });
    const onRequeued = jest.fn();
    render(<LiftTypeLine {...base} confidence={0.41} onRequeued={onRequeued} />);
    fireEvent.click(screen.getByRole("button", { name: "Yes" }));
    await waitFor(() => expect(screen.getByTestId("lift-type-line")).toHaveAttribute("data-state", "manual"));
    expect(changeLiftType).toHaveBeenCalledWith("a-1", "Pushup", "u-1");
    expect(onRequeued).not.toHaveBeenCalled();
  });

  test("Change opens a sheet of the competition's types and a confirmed pick re-queues", async () => {
    (changeLiftType as jest.Mock).mockResolvedValue({ attempt_id: "a-1", lift_type: "Situp", status: "queued" });
    const onRequeued = jest.fn();
    render(<LiftTypeLine {...base} onRequeued={onRequeued} />);
    fireEvent.click(screen.getByRole("button", { name: "Change" }));
    const sheet = screen.getByRole("dialog", { name: "Change lift type" });
    const options = within(sheet).getAllByRole("radio");
    expect(options.map((o) => o.textContent)).toEqual(["Situps", "Pushups", "Squats", "Plank"]);
    expect(within(sheet).getByRole("radio", { name: "Pushups" })).toHaveAttribute("aria-checked", "true");
    expect(within(sheet).queryByText(/Automatic/)).toBeNull();
    fireEvent.click(within(sheet).getByRole("radio", { name: "Situps" }));
    fireEvent.click(within(sheet).getByRole("button", { name: "Re-analyse" }));
    await waitFor(() => expect(onRequeued).toHaveBeenCalledWith("Situp"));
    expect(changeLiftType).toHaveBeenCalledWith("a-1", "Situp", "u-1");
    expect(screen.queryByRole("dialog")).toBeNull();
  });

  test("a refused change stays in the sheet and says why", async () => {
    (changeLiftType as jest.Mock).mockRejectedValue({ response: { status: 409, data: { error: "Analysis is already running" } } });
    const onRequeued = jest.fn();
    render(<LiftTypeLine {...base} onRequeued={onRequeued} />);
    fireEvent.click(screen.getByRole("button", { name: "Change" }));
    fireEvent.click(screen.getByRole("radio", { name: "Squats" }));
    fireEvent.click(screen.getByRole("button", { name: "Re-analyse" }));
    expect(await screen.findByText("Analysis is already running")).toBeInTheDocument();
    expect(screen.getByRole("dialog")).toBeInTheDocument();
    expect(onRequeued).not.toHaveBeenCalled();
  });

  test("viewers who are not the owner see the line without Change or a prompt", () => {
    render(<LiftTypeLine {...base} isOwner={false} confidence={0.41} onRequeued={jest.fn()} />);
    const line = screen.getByTestId("lift-type-line");
    expect(line).toHaveTextContent(/^Counted as Pushups · Automatic$/);
    expect(within(line).queryByRole("button")).toBeNull();
  });

  test("renders nothing for a non-owner while the type is unknown", () => {
    const { container } = render(
      <LiftTypeLine {...base} isOwner={false} liftType="Auto" needsLiftType onRequeued={jest.fn()} />,
    );
    expect(container).toBeEmptyDOMElement();
  });
});
