import React from "react";
import "@testing-library/jest-dom";
import { render } from "@testing-library/react";
import AmbientBackground from "../AmbientBackground";

describe("AmbientBackground", () => {
  it("renders doodle + three glow layers, all aria-hidden and pointer-transparent", () => {
    const { container } = render(<AmbientBackground />);
    const layers = container.querySelectorAll("[aria-hidden='true']");
    expect(layers.length).toBe(4); // 1 doodle + 3 glows
    layers.forEach((el) => {
      expect(el.className).toContain("pointer-events-none");
      expect(el.className).toContain("fixed");
    });
  });
});
