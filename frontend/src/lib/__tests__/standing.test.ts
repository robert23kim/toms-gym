import { deriveStanding, ctaLabelFor, attemptScore, metricForLift, personalBest, formatWithUnit, standingShareText } from "../standing";
import type {
  ChallengeLeaderboard,
  ChallengeLeaderboardRow,
  ChallengeMetric,
} from "../types";

const makeRow = (overrides: Partial<ChallengeLeaderboardRow> = {}): ChallengeLeaderboardRow => ({
  rank: 1,
  user_id: "u1",
  name: "Athlete",
  score: 50,
  best_by_lift: { Plank: 50 },
  form_score: 0.9,
  attempt_id: "a1",
  clip_url: "https://cdn/clip.mp4",
  thumbnail_url: null,
  date: "2026-07-01",
  weight_class: "83kg",
  gender: "male",
  attempt_count: 1,
  history: [{ score: 50, date: "2026-07-01" }],
  ...overrides,
});

const board = (
  rows: ChallengeLeaderboardRow[],
  metric: ChallengeMetric = "time",
): Pick<ChallengeLeaderboard, "rows" | "metric"> => ({ rows, metric });

// A mid-pack viewer (#3 of 4) with an improving 3-try history and a #2 above.
const midPack = () =>
  board([
    makeRow({ rank: 1, user_id: "u1", name: "Ana", score: 30 }),
    makeRow({ rank: 2, user_id: "u2", name: "Devon", score: 22.5 }),
    makeRow({
      rank: 3,
      user_id: "me",
      name: "Toka",
      score: 18.6,
      attempt_count: 3,
      history: [
        { score: 9.2, date: "2026-06-28" },
        { score: 14.1, date: "2026-06-30" },
        { score: 18.6, date: "2026-07-02" },
      ],
    }),
    makeRow({ rank: 4, user_id: "u4", name: "Kim", score: 12 }),
  ]);

describe("deriveStanding", () => {
  test("derives rank, of-N, and best from the viewer's row", () => {
    const s = deriveStanding(midPack(), "me")!;
    expect(s).not.toBeNull();
    expect(s.rank).toBe(3);
    expect(s.participantCount).toBe(4);
    expect(s.best).toBe(18.6);
  });

  test("delta is last − first over history (tries = history length)", () => {
    const s = deriveStanding(midPack(), "me")!;
    expect(s.tries).toBe(3);
    expect(s.delta).toBeCloseTo(9.4, 5);
  });

  test("single attempt suppresses the delta", () => {
    const s = deriveStanding(midPack(), "u1")!; // Ana has one history point
    expect(s.tries).toBe(1);
    expect(s.delta).toBeNull();
  });

  test("gap-to-next comes from the row directly above", () => {
    const s = deriveStanding(midPack(), "me")!;
    expect(s.isLeader).toBe(false);
    expect(s.gap).toBeCloseTo(3.9, 5); // 22.5 − 18.6
    expect(s.nextName).toBe("Devon");
    expect(s.nextRank).toBe(2);
    // progress = 18.6 / 22.5, clamped 0..1
    expect(s.progress).toBeCloseTo(18.6 / 22.5, 5);
  });

  test("goal subtitle is metric-aware", () => {
    const s = deriveStanding(midPack(), "me")!;
    expect(s.goalSubtitle).toBe("3.9s to reach #2");
  });

  test("goal-reframed CTA uses the viewer's best", () => {
    const s = deriveStanding(midPack(), "me")!;
    expect(s.ctaLabel).toBe("Beat your best — 18.6s");
  });

  test("#1 viewer is the leader — no gap, bar, or subtitle", () => {
    const s = deriveStanding(midPack(), "u1")!;
    expect(s.isLeader).toBe(true);
    expect(s.gap).toBeNull();
    expect(s.progress).toBeNull();
    expect(s.nextName).toBeNull();
    expect(s.nextRank).toBeNull();
    expect(s.goalSubtitle).toBeNull();
  });

  test("returns null when the viewer isn't in the rows", () => {
    expect(deriveStanding(midPack(), "ghost")).toBeNull();
  });

  test("returns null when the viewer has a zero score (joined, no attempt)", () => {
    const b = board([makeRow({ rank: 1, user_id: "me", score: 0, history: [] })]);
    expect(deriveStanding(b, "me")).toBeNull();
  });

  test("returns null when there's no userId", () => {
    expect(deriveStanding(midPack(), null)).toBeNull();
    expect(deriveStanding(midPack(), undefined)).toBeNull();
  });

  test("weight metric formats gap, subtitle, and CTA with lbs", () => {
    const b = board(
      [
        makeRow({ rank: 1, user_id: "u1", name: "Ana", score: 320 }),
        makeRow({ rank: 2, user_id: "me", name: "Toka", score: 300 }),
      ],
      "weight",
    );
    const s = deriveStanding(b, "me")!;
    expect(s.goalSubtitle).toBe("20lbs to reach #1");
    expect(s.ctaLabel).toBe("Beat your best — 300lbs");
  });

  test("progress clamps to 1 when the athlete above has a zero score", () => {
    const b = board([
      makeRow({ rank: 1, user_id: "u1", score: 0, history: [] }),
      makeRow({ rank: 2, user_id: "me", score: 10 }),
    ]);
    const s = deriveStanding(b, "me")!;
    expect(s.progress).toBe(1);
  });
});

describe("ctaLabelFor", () => {
  test("uses the goal-reframed label when entered", () => {
    const s = deriveStanding(midPack(), "me")!;
    expect(ctaLabelFor(s, "time")).toBe("Beat your best — 18.6s");
  });

  test("falls back to the default upload label when not entered", () => {
    expect(ctaLabelFor(null, "time")).toBe("Upload your plank");
    expect(ctaLabelFor(null, "weight")).toBe("Upload your lift");
  });
});

describe("result ladder additions", () => {
  test("below is the entrant directly under the viewer with the margin they hold", () => {
    const s = deriveStanding(midPack(), "me")!;
    expect(s.below).toMatchObject({ name: "Kim", rank: 4, score: 12 });
    expect(s.below!.gap).toBeCloseTo(6.6, 5);
    expect(deriveStanding(midPack(), "u4")!.below).toBeNull();
  });

  test("below ignores entrants who have not scored yet", () => {
    const b = board([
      makeRow({ rank: 1, user_id: "me", score: 10 }),
      makeRow({ rank: 2, user_id: "u2", score: 0, history: [] }),
    ]);
    expect(deriveStanding(b, "me")!.below).toBeNull();
  });

  test("podiumGap is the distance to #3 only when off the podium", () => {
    expect(deriveStanding(midPack(), "u4")!.podiumGap).toBeCloseTo(6.6, 5);
    expect(deriveStanding(midPack(), "me")!.podiumGap).toBeNull();
  });

  test("personalBest flags an attempt that beat every earlier score", () => {
    const s = deriveStanding(midPack(), "me")!;
    expect(personalBest(s, 18.6)).toEqual({ isPersonalBest: true, previousBest: 14.1, belowBest: false });
  });

  test("personalBest is false on a first attempt, a tie, or an older weaker attempt", () => {
    const firstTry = deriveStanding(board([makeRow({ rank: 1, user_id: "me", score: 30, history: [{ score: 30, date: "d1" }] })]), "me")!;
    expect(personalBest(firstTry, 30)).toEqual({ isPersonalBest: false, previousBest: null, belowBest: false });
    const me = deriveStanding(midPack(), "me")!;
    expect(personalBest(me, 9.2)).toEqual({ isPersonalBest: false, previousBest: 18.6, belowBest: true });
    const tie = deriveStanding(board([makeRow({ rank: 1, user_id: "me", score: 20, history: [{ score: 20, date: "d1" }, { score: 20, date: "d2" }] })]), "me")!;
    expect(personalBest(tie, 20).isPersonalBest).toBe(false);
  });

  test("attemptScore reads the metric's field; metricForLift maps lift types", () => {
    expect(attemptScore("reps", { total_reps: 35 }, 60)).toBe(35);
    expect(attemptScore("time", { total_in_plank_s: 201.3 }, 60)).toBe(201.3);
    expect(attemptScore("weight", { total_reps: 5 }, 115)).toBe(115);
    expect(attemptScore("reps", null, 60)).toBeNull();
    expect(metricForLift("Plank")).toBe("time");
    expect(metricForLift("pushup")).toBe("reps");
    expect(metricForLift("Bench Press")).toBe("weight");
  });

  test("formatWithUnit follows the board's units and pluralises reps", () => {
    expect(formatWithUnit(1, "reps")).toBe("1 rep");
    expect(formatWithUnit(35, "reps")).toBe("35 reps");
    expect(formatWithUnit(18.6, "time")).toBe("18.6s");
    expect(formatWithUnit(115, "weight")).toBe("115lbs");
  });
});

describe("standingShareText", () => {
  test("owner copy dares the reader; the leader offers their spot", () => {
    const me = deriveStanding(midPack(), "me")!;
    expect(standingShareText({ standing: me, metric: "time", challengeName: "Summer plank challenge", athleteName: "Toka", isOwner: true }))
      .toBe("I'm #3 of 4 in the Summer plank challenge — 18.6s. Beat me:");
    const ana = deriveStanding(midPack(), "u1")!;
    expect(standingShareText({ standing: ana, metric: "time", challengeName: null, athleteName: "Ana", isOwner: true }))
      .toBe("I'm #1 of 4 in this challenge — 30.0s. Take my spot:");
  });

  test("visitor copy speaks about the athlete by first name", () => {
    const me = deriveStanding(midPack(), "me")!;
    expect(standingShareText({ standing: me, metric: "time", challengeName: "Summer plank challenge", athleteName: "Toka Oka", isOwner: false }))
      .toBe("Toka is #3 of 4 in the Summer plank challenge — 18.6s. Can you beat it?");
  });
});
