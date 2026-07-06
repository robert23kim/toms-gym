import { viewerProcessingAttempts } from "../processing";
import type { LiftingResult } from "../../../lib/types";

const result = (status: LiftingResult["processing_status"]): LiftingResult =>
  ({ processing_status: status } as Partial<LiftingResult> as LiftingResult);

const VIDEOS = [
  { attempt_id: "a1", user_id: "u1" },
  { attempt_id: "a2", user_id: "u1" },
  { attempt_id: "a3", user_id: "u2" },
];

describe("viewerProcessingAttempts", () => {
  test("no viewer → nothing is processing", () => {
    expect(
      viewerProcessingAttempts(VIDEOS, { a1: result("processing") }, null)
    ).toEqual([]);
  });

  test("viewer's queued and processing attempts are returned", () => {
    const results = { a1: result("processing"), a2: result("queued") };
    expect(viewerProcessingAttempts(VIDEOS, results, "u1")).toEqual(["a1", "a2"]);
  });

  test("completed and failed attempts are not processing", () => {
    const results = { a1: result("completed"), a2: result("failed") };
    expect(viewerProcessingAttempts(VIDEOS, results, "u1")).toEqual([]);
  });

  test("other users' processing attempts are ignored", () => {
    expect(
      viewerProcessingAttempts(VIDEOS, { a3: result("processing") }, "u1")
    ).toEqual([]);
  });

  test("an attempt with no fetched result is not assumed processing", () => {
    // Old attempts may predate analysis; a missing result must not pin a
    // permanent "processing" banner on them.
    expect(viewerProcessingAttempts(VIDEOS, {}, "u1")).toEqual([]);
  });

  test("viewer id matching coerces number vs string ids", () => {
    const videos = [{ attempt_id: "a9", user_id: 42 }];
    expect(
      viewerProcessingAttempts(videos, { a9: result("processing") }, "42")
    ).toEqual(["a9"]);
  });
});
