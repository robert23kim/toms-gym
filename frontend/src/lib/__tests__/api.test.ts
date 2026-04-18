/**
 * Compile-time type assertions for the Phase B golf API shapes.
 *
 * These tests don't run logic — they fail to type-check if the response
 * shapes from `lib/types.ts` drift from the backend contract defined in
 * `backend/toms_gym/routes/golf_routes.py` (commit e5500d6).
 */

import type {
  GolfCourse,
  GolfTee,
  GolfHole,
  GolfRoundDetail,
  GolfRoundListItem,
  GolfRoundListResponse,
  GolfRoundDetailResponse,
  GolfHandicapHistoryPoint,
  GolfHandicapHistoryResponse,
  GolfCourseSearchResult,
  GolfLeaderboardEntry,
  GolfDetectedPlayer,
  GolfScoresUpdateResponse,
} from "../types";
import {
  fetchRound,
  fetchRounds,
  updateRoundScores,
  searchCourses,
  createCourse,
  getHandicapHistory,
} from "../api";

type Expect<T extends true> = T;
type Equal<X, Y> =
  (<T>() => T extends X ? 1 : 2) extends (<T>() => T extends Y ? 1 : 2)
    ? true
    : false;

describe("golf api types", () => {
  test("GolfCourse has exact backend shape", () => {
    const course: GolfCourse = {
      id: "c1",
      name: "Pebble Beach",
      city: "Pebble Beach",
      state: "CA",
      country: "USA",
      latitude: 36.5,
      longitude: -121.9,
      holes: 18,
      status: "verified",
    };
    expect(course.name).toBe("Pebble Beach");
  });

  test("GolfCourse status is verified | pending", () => {
    type _StatusCheck = Expect<
      Equal<GolfCourse["status"], "verified" | "pending">
    >;
    expect(true).toBe(true);
  });

  test("GolfTee has all rating/slope fields nullable", () => {
    const allNull: GolfTee = {
      id: null, name: null, color_hex: null,
      rating_18: null, slope_18: null,
      rating_9_front: null, slope_9_front: null,
      rating_9_back: null, slope_9_back: null,
      yardage: null, par: null,
      hole_pars: null, hole_yardages: null, hole_handicaps: null,
    };
    expect(allNull.id).toBeNull();

    const filled: GolfTee = {
      id: "t1", name: "Blue", color_hex: "#2563eb",
      rating_18: 71.3, slope_18: 130,
      rating_9_front: 35.1, slope_9_front: 128,
      rating_9_back: 36.2, slope_9_back: 132,
      yardage: 6700, par: 72,
      hole_pars: [4, 4, 3, 5, 4, 4, 3, 5, 4, 4, 4, 3, 5, 4, 4, 3, 5, 4],
      hole_yardages: null, hole_handicaps: null,
    };
    expect(filled.slope_18).toBe(130);
  });

  test("GolfHole shape matches HoleScore response", () => {
    const hole: GolfHole = {
      hole_number: 1,
      par: 4,
      strokes: 5,
      ocr_confidence: 0.92,
      manually_corrected: false,
    };
    expect(hole.hole_number).toBe(1);
  });

  test("GolfRoundDetail has nested course and tee and hole_scores", () => {
    type _HoleScoresCheck = Expect<
      Equal<GolfRoundDetail["hole_scores"], GolfHole[]>
    >;
    type _CourseCheck = Expect<Equal<GolfRoundDetail["course"], GolfCourse>>;
    type _TeeCheck = Expect<Equal<GolfRoundDetail["tee"], GolfTee>>;
    type _PlayedOn = Expect<Equal<GolfRoundDetail["played_on"], string | null>>;
    expect(true).toBe(true);
  });

  test("GolfRoundDetailResponse wraps round in 'round' key plus detected_players", () => {
    type _RoundKey = Expect<
      Equal<GolfRoundDetailResponse["round"], GolfRoundDetail>
    >;
    type _DetectedKey = Expect<
      Equal<GolfRoundDetailResponse["detected_players"], GolfDetectedPlayer[]>
    >;
    expect(true).toBe(true);
  });

  test("GolfRoundListResponse has rounds + handicap_index + rounds_used", () => {
    type _RoundsKey = Expect<
      Equal<GolfRoundListResponse["rounds"], GolfRoundListItem[]>
    >;
    type _HandicapKey = Expect<
      Equal<GolfRoundListResponse["handicap_index"], number | null>
    >;
    type _RoundsUsedKey = Expect<
      Equal<GolfRoundListResponse["rounds_used"], number>
    >;
    expect(true).toBe(true);
  });

  test("GolfHandicapHistoryResponse shape", () => {
    type _HistoryCheck = Expect<
      Equal<GolfHandicapHistoryResponse["history"], GolfHandicapHistoryPoint[]>
    >;
    type _RangeCheck = Expect<
      Equal<GolfHandicapHistoryResponse["range"], "6m" | "12m" | "24m" | "all">
    >;
    expect(true).toBe(true);
  });

  test("GolfLeaderboardEntry includes monthly_delta", () => {
    const entry: GolfLeaderboardEntry = {
      rank: 1,
      user_id: "u1",
      user_name: "Alice",
      handicap_index: 9.4,
      monthly_delta: -0.3,
      rounds_played: 12,
      rounds_used: 8,
      best_differential: 6.2,
      latest_snapshot_at: "2026-04-18 00:00:00",
    };
    expect(entry.monthly_delta).toBe(-0.3);

    const noDelta: GolfLeaderboardEntry = {
      rank: 2,
      user_id: "u2",
      user_name: "Bob",
      handicap_index: 12.1,
      monthly_delta: null,
      rounds_played: 3,
      rounds_used: 3,
      best_differential: null,
      latest_snapshot_at: null,
    };
    expect(noDelta.monthly_delta).toBeNull();
  });

  test("GolfScoresUpdateResponse shape matches PUT /round/:id/scores", () => {
    type _HandicapCheck = Expect<
      Equal<GolfScoresUpdateResponse["handicap_index"], number | null>
    >;
    type _DiffCheck = Expect<
      Equal<GolfScoresUpdateResponse["score_differential"], number | null>
    >;
    expect(true).toBe(true);
  });

  test("fetch functions have expected return types", () => {
    type _FetchRound = Expect<
      Equal<ReturnType<typeof fetchRound>, Promise<GolfRoundDetailResponse>>
    >;
    type _FetchRounds = Expect<
      Equal<ReturnType<typeof fetchRounds>, Promise<GolfRoundListResponse>>
    >;
    type _UpdateScores = Expect<
      Equal<ReturnType<typeof updateRoundScores>, Promise<GolfScoresUpdateResponse>>
    >;
    type _SearchCourses = Expect<
      Equal<ReturnType<typeof searchCourses>, Promise<GolfCourseSearchResult[]>>
    >;
    type _CreateCourse = Expect<
      Equal<ReturnType<typeof createCourse>, Promise<GolfCourse>>
    >;
    type _History = Expect<
      Equal<
        ReturnType<typeof getHandicapHistory>,
        Promise<GolfHandicapHistoryResponse>
      >
    >;
    expect(true).toBe(true);
  });
});
