import * as fs from "fs";
import * as path from "path";
import type { ChallengeLeaderboard } from "../lib/types";
import {
  consistencyLeaderboard,
  endedConsistencyLeaderboard,
  upcomingConsistencyLeaderboard,
} from "./consistencyLeaderboard";

const BACKEND_FIXTURES = path.resolve(__dirname, "../../../backend/tests/fixtures");

const backend = (name: string): ChallengeLeaderboard =>
  JSON.parse(fs.readFileSync(path.join(BACKEND_FIXTURES, `consistency_leaderboard_${name}.json`), "utf8"));

// Ids and clip URLs are made up on each side; every other key must match.
const comparable = (board: ChallengeLeaderboard) => ({
  ...board,
  competition_id: null,
  rows: board.rows.map((r) => ({ ...r, attempt_id: r.attempt_id ? "id" : null, clip_url: r.clip_url ? "url" : null })),
});

describe("100 Club frontend fixtures match the backend payload builder", () => {
  it.each([
    ["sample", consistencyLeaderboard],
    ["upcoming", upcomingConsistencyLeaderboard],
    ["ended", endedConsistencyLeaderboard],
  ])("%s", (name, fixture) => {
    expect(comparable(fixture)).toEqual(comparable(backend(name)));
  });
});
