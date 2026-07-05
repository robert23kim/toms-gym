import { render, screen } from "@testing-library/react";
import "@testing-library/jest-dom";
import ErrorBoundary from "../ErrorBoundary";
import { reportError } from "../../lib/telemetry";

jest.mock("../../lib/telemetry", () => ({
  reportError: jest.fn(),
}));

const Boom = () => {
  throw new Error("kaboom");
};

describe("ErrorBoundary", () => {
  it("renders the fallback when a child throws", () => {
    const spy = jest.spyOn(console, "error").mockImplementation(() => {});
    render(
      <ErrorBoundary>
        <Boom />
      </ErrorBoundary>
    );
    expect(screen.getByText("Something went wrong")).toBeInTheDocument();
    expect(screen.getByText("kaboom")).toBeInTheDocument();
    spy.mockRestore();
  });

  it("reports the render error to telemetry", () => {
    const spy = jest.spyOn(console, "error").mockImplementation(() => {});
    render(
      <ErrorBoundary>
        <Boom />
      </ErrorBoundary>
    );
    expect(reportError).toHaveBeenCalledWith(
      "ErrorBoundary",
      "render-error",
      expect.objectContaining({ message: "kaboom" }),
      expect.objectContaining({ componentStack: expect.any(String) })
    );
    spy.mockRestore();
  });

  it("renders children when nothing throws", () => {
    render(
      <ErrorBoundary>
        <div>all good</div>
      </ErrorBoundary>
    );
    expect(screen.getByText("all good")).toBeInTheDocument();
  });
});
