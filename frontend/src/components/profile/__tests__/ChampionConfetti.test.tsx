import React from "react";
import "@testing-library/jest-dom";
import { render, screen } from "@testing-library/react";
import ChampionConfetti, { confettiSeenKey } from "../ChampionConfetti";

// jest.setup.js replaces localStorage with jest.fn() stubs — drive it directly.
const store = localStorage as unknown as {
  getItem: jest.Mock;
  setItem: jest.Mock;
};

describe("ChampionConfetti", () => {
  beforeEach(() => {
    store.getItem.mockReset();
    store.setItem.mockReset();
  });

  it("first view: marks seen, shows the champion toast", () => {
    store.getItem.mockReturnValue(null);
    render(<ChampionConfetti competitionId="c1" userId="u1" />);
    expect(screen.getByText(/👑 Champion!/)).toBeInTheDocument();
    expect(store.setItem).toHaveBeenCalledWith(confettiSeenKey("c1", "u1"), "1");
  });

  it("second view: renders nothing and does not re-mark", () => {
    store.getItem.mockReturnValue("1");
    const { container } = render(
      <ChampionConfetti competitionId="c1" userId="u1" />,
    );
    expect(container).toBeEmptyDOMElement();
    expect(store.setItem).not.toHaveBeenCalled();
  });

  it("keys the burst per win and viewer", () => {
    expect(confettiSeenKey("c1", "u1")).toBe("champ-confetti-c1-u1");
  });
});
