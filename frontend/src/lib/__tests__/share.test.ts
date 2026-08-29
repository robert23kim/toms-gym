import axios from "axios";
import { shareResult } from "../share";

jest.mock("../../config", () => ({ API_URL: "https://test-api.example" }));
jest.mock("axios", () => {
  const actual = jest.requireActual("axios");
  const mocked = { ...actual, post: jest.fn() };
  return { ...mocked, default: mocked };
});

const meta = { targetUrl: "https://app/result", ogTitle: "Toka's Pushup" };

describe("shareResult", () => {
  const nav = navigator as Navigator & { share?: jest.Mock; clipboard: { writeText: jest.Mock } };

  beforeEach(() => {
    (axios.post as jest.Mock).mockResolvedValue({ data: { short_code: "abc123" } });
    Object.assign(navigator, { clipboard: { writeText: jest.fn().mockResolvedValue(undefined) } });
    delete nav.share;
  });

  it("uses the native share sheet with the words and the short link when available", async () => {
    nav.share = jest.fn().mockResolvedValue(undefined);
    const out = await shareResult(meta, "I'm #2 of 5 — 35 reps. Beat me:");
    expect(nav.share).toHaveBeenCalledWith({
      title: "Toka's Pushup",
      text: "I'm #2 of 5 — 35 reps. Beat me:",
      url: "https://test-api.example/s/abc123",
    });
    expect(out).toEqual({ url: "https://test-api.example/s/abc123", method: "share" });
    expect(nav.clipboard.writeText).not.toHaveBeenCalled();
  });

  it("copies words + link when there is no share sheet", async () => {
    const out = await shareResult(meta, "Beat me:");
    expect(nav.clipboard.writeText).toHaveBeenCalledWith("Beat me: https://test-api.example/s/abc123");
    expect(out.method).toBe("copy");
  });

  it("reports a dismissed share sheet as cancelled without touching the clipboard", async () => {
    nav.share = jest.fn().mockRejectedValue(Object.assign(new Error("dismissed"), { name: "AbortError" }));
    const out = await shareResult(meta, "Beat me:");
    expect(out.method).toBe("cancelled");
    expect(nav.clipboard.writeText).not.toHaveBeenCalled();
  });
});
