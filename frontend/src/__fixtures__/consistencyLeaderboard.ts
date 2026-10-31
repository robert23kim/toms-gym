import type {
  ChallengeLeaderboard,
  ConsistencyBlock,
  ConsistencyRules,
  ConsistencyWeek,
} from "../lib/types";

// Shared 100 Club scenario, as of Thursday 2026-11-19 15:00 America/New_York
// (week 3 of 8). Mirrors the backend-generated fixture key for key.

export const CONSISTENCY_COMPETITION_ID = "club-100";

export const consistencyRules: ConsistencyRules = {
  base_quota: 100,
  ramp: 25,
  weeks: 8,
  quota_bonus: 50,
  type_bonus: 25,
  plank_seconds_per_lift: 10,
  tz: "America/New_York",
  week_start: "2026-11-02",
};

const zeroTypes = (): Record<string, number> => ({ Situp: 0, Pushup: 0, Squat: 0, Plank: 0 });

const emptyWeek = (index: number, start: string): ConsistencyWeek => ({
  index,
  start,
  quota: 100,
  lifts: 0,
  met: false,
  points: 0,
  bonuses: [],
  by_type: zeroTypes(),
  plank_seconds: 0,
  pending: 0,
});

export const liveConsistencyBlock: ConsistencyBlock = {
  rules: consistencyRules,
  status: "live",
  week_index: 3,
  weeks_total: 8,
  week_start: "2026-11-16",
  week_end: "2026-11-22",
  days_left: 4,
  type_leaders: {
    Situp: [{ user_id: "a1", name: "Ana", amount: 42 }],
    Plank: [{ user_id: "b1", name: "Ben", amount: 100 }],
  },
};

export const consistencyLeaderboard: ChallengeLeaderboard = {
  competition_id: CONSISTENCY_COMPETITION_ID,
  metric: "consistency",
  lift_types: ["Situp", "Pushup", "Squat", "Plank"],
  momentum: { joined: 3, uploaded_today: 0 },
  consistency: liveConsistencyBlock,
  rows: [
    {
      rank: 1,
      user_id: "a1",
      name: "Ana",
      weight_class: null,
      gender: null,
      score: 467,
      streak: 2,
      best_streak: 2,
      weeks_met: 2,
      this_week: {
        index: 3,
        quota: 150,
        lifts: 42,
        met: false,
        pending: 0,
        by_type: { Situp: 42, Pushup: 0, Squat: 0, Plank: 0 },
        plank_seconds: 0,
        leading: ["Situp"],
      },
      weeks: [
        {
          index: 1,
          start: "2026-11-02",
          quota: 100,
          lifts: 112,
          met: true,
          points: 200,
          bonuses: ["Situp", "Plank"],
          by_type: { Situp: 45, Pushup: 43, Squat: 0, Plank: 24 },
          plank_seconds: 240,
          pending: 0,
        },
        {
          index: 2,
          start: "2026-11-09",
          quota: 125,
          lifts: 130,
          met: true,
          points: 225,
          bonuses: ["Situp", "Pushup"],
          by_type: { Situp: 60, Pushup: 70, Squat: 0, Plank: 0 },
          plank_seconds: 0,
          pending: 0,
        },
        {
          index: 3,
          start: "2026-11-16",
          quota: 150,
          lifts: 42,
          met: false,
          points: 42,
          bonuses: [],
          by_type: { Situp: 42, Pushup: 0, Squat: 0, Plank: 0 },
          plank_seconds: 0,
          pending: 0,
        },
      ],
      warmup_lifts: 20,
      best_by_lift: {},
      form_score: null,
      steadiness: null,
      attempt_id: "att-a1-situp-1117",
      clip_url: "https://storage.example/ana-situp-1117-annotated.mp4",
      thumbnail_url: null,
      date: "2026-11-17",
      attempt_count: 6,
      history: [
        { score: 24, date: "2026-11-03" },
        { score: 45, date: "2026-11-04" },
        { score: 43, date: "2026-11-05" },
        { score: 70, date: "2026-11-10" },
        { score: 60, date: "2026-11-12" },
        { score: 42, date: "2026-11-17" },
      ],
    },
    {
      rank: 2,
      user_id: "b1",
      name: "Ben",
      weight_class: null,
      gender: null,
      score: 330,
      streak: 1,
      best_streak: 1,
      weeks_met: 1,
      this_week: {
        index: 3,
        quota: 125,
        lifts: 10,
        met: false,
        pending: 1,
        by_type: { Situp: 0, Pushup: 0, Squat: 0, Plank: 10 },
        plank_seconds: 100,
        leading: ["Plank"],
      },
      weeks: [
        {
          index: 1,
          start: "2026-11-02",
          quota: 100,
          lifts: 95,
          met: false,
          points: 145,
          bonuses: ["Pushup", "Squat"],
          by_type: { Situp: 0, Pushup: 60, Squat: 35, Plank: 0 },
          plank_seconds: 0,
          pending: 0,
        },
        {
          index: 2,
          start: "2026-11-09",
          quota: 100,
          lifts: 100,
          met: true,
          points: 175,
          bonuses: ["Squat"],
          by_type: { Situp: 0, Pushup: 0, Squat: 100, Plank: 0 },
          plank_seconds: 0,
          pending: 0,
        },
        {
          index: 3,
          start: "2026-11-16",
          quota: 125,
          lifts: 10,
          met: false,
          points: 10,
          bonuses: [],
          by_type: { Situp: 0, Pushup: 0, Squat: 0, Plank: 10 },
          plank_seconds: 100,
          pending: 1,
        },
      ],
      warmup_lifts: 0,
      best_by_lift: {},
      form_score: null,
      steadiness: null,
      attempt_id: "att-b1-plank-1118",
      clip_url: "https://storage.example/ben-plank-1118-annotated.mp4",
      thumbnail_url: null,
      date: "2026-11-18",
      attempt_count: 4,
      history: [
        { score: 60, date: "2026-11-03" },
        { score: 35, date: "2026-11-05" },
        { score: 100, date: "2026-11-11" },
        { score: 10, date: "2026-11-18" },
      ],
    },
    {
      rank: 3,
      user_id: "c1",
      name: "Cy",
      weight_class: null,
      gender: null,
      score: 0,
      streak: 0,
      best_streak: 0,
      weeks_met: 0,
      this_week: {
        index: 3,
        quota: 100,
        lifts: 0,
        met: false,
        pending: 0,
        by_type: zeroTypes(),
        plank_seconds: 0,
        leading: [],
      },
      weeks: [emptyWeek(1, "2026-11-02"), emptyWeek(2, "2026-11-09"), emptyWeek(3, "2026-11-16")],
      warmup_lifts: 0,
      best_by_lift: {},
      form_score: null,
      steadiness: null,
      attempt_id: null,
      clip_url: null,
      thumbnail_url: null,
      date: null,
      attempt_count: 0,
      history: [],
    },
  ],
};

// Upcoming and ended boards: generated from backend/tests/consistency_scenario.py
// (as_of 2026-10-31 15:00 and 2026-12-28 12:00 America/New_York) and pinned to the
// backend JSON by consistencyFixtures.test.ts.

/** The same rows before week 1: everyone at zero, Ana with a warm-up. */
export const upcomingConsistencyLeaderboard: ChallengeLeaderboard = {
  competition_id: CONSISTENCY_COMPETITION_ID,
  metric: "consistency",
  lift_types: [
    "Situp",
    "Pushup",
    "Squat",
    "Plank"
  ],
  momentum: {
    joined: 3,
    uploaded_today: 0
  },
  rows: [
    {
      user_id: "a1",
      name: "Ana",
      weight_class: null,
      gender: null,
      score: 0,
      streak: 0,
      best_streak: 0,
      weeks_met: 0,
      this_week: {
        index: 0,
        quota: 100,
        lifts: 0,
        met: false,
        pending: 0,
        by_type: {
          Situp: 0,
          Pushup: 0,
          Squat: 0,
          Plank: 0
        },
        plank_seconds: 0,
        leading: []
      },
      weeks: [],
      warmup_lifts: 20,
      best_by_lift: {},
      form_score: null,
      steadiness: null,
      attempt_id: null,
      clip_url: null,
      thumbnail_url: null,
      date: null,
      attempt_count: 0,
      history: [],
      rank: 1
    },
    {
      user_id: "b1",
      name: "Ben",
      weight_class: null,
      gender: null,
      score: 0,
      streak: 0,
      best_streak: 0,
      weeks_met: 0,
      this_week: {
        index: 0,
        quota: 100,
        lifts: 0,
        met: false,
        pending: 0,
        by_type: {
          Situp: 0,
          Pushup: 0,
          Squat: 0,
          Plank: 0
        },
        plank_seconds: 0,
        leading: []
      },
      weeks: [],
      warmup_lifts: 0,
      best_by_lift: {},
      form_score: null,
      steadiness: null,
      attempt_id: null,
      clip_url: null,
      thumbnail_url: null,
      date: null,
      attempt_count: 0,
      history: [],
      rank: 2
    },
    {
      user_id: "c1",
      name: "Cy",
      weight_class: null,
      gender: null,
      score: 0,
      streak: 0,
      best_streak: 0,
      weeks_met: 0,
      this_week: {
        index: 0,
        quota: 100,
        lifts: 0,
        met: false,
        pending: 0,
        by_type: {
          Situp: 0,
          Pushup: 0,
          Squat: 0,
          Plank: 0
        },
        plank_seconds: 0,
        leading: []
      },
      weeks: [],
      warmup_lifts: 0,
      best_by_lift: {},
      form_score: null,
      steadiness: null,
      attempt_id: null,
      clip_url: null,
      thumbnail_url: null,
      date: null,
      attempt_count: 0,
      history: [],
      rank: 3
    }
  ],
  consistency: {
    rules: {
      base_quota: 100,
      ramp: 25,
      weeks: 8,
      quota_bonus: 50,
      type_bonus: 25,
      plank_seconds_per_lift: 10,
      tz: "America/New_York",
      week_start: "2026-11-02"
    },
    status: "upcoming",
    week_index: 0,
    weeks_total: 8,
    week_start: "2026-11-02",
    week_end: "2026-11-08",
    days_left: 0,
    type_leaders: {}
  }
};

/** The same rows after the last week. */
export const endedConsistencyLeaderboard: ChallengeLeaderboard = {
  competition_id: CONSISTENCY_COMPETITION_ID,
  metric: "consistency",
  lift_types: [
    "Situp",
    "Pushup",
    "Squat",
    "Plank"
  ],
  momentum: {
    joined: 3,
    uploaded_today: 0
  },
  rows: [
    {
      user_id: "a1",
      name: "Ana",
      weight_class: null,
      gender: null,
      score: 492,
      streak: 0,
      best_streak: 2,
      weeks_met: 2,
      this_week: {
        index: 9,
        quota: 100,
        lifts: 0,
        met: false,
        pending: 0,
        by_type: {
          Situp: 0,
          Pushup: 0,
          Squat: 0,
          Plank: 0
        },
        plank_seconds: 0,
        leading: []
      },
      weeks: [
        {
          index: 1,
          start: "2026-11-02",
          quota: 100,
          lifts: 112,
          met: true,
          points: 200,
          bonuses: [
            "Situp",
            "Plank"
          ],
          by_type: {
            Situp: 45,
            Pushup: 43,
            Squat: 0,
            Plank: 24
          },
          plank_seconds: 240,
          pending: 0
        },
        {
          index: 2,
          start: "2026-11-09",
          quota: 125,
          lifts: 130,
          met: true,
          points: 225,
          bonuses: [
            "Situp",
            "Pushup"
          ],
          by_type: {
            Situp: 60,
            Pushup: 70,
            Squat: 0,
            Plank: 0
          },
          plank_seconds: 0,
          pending: 0
        },
        {
          index: 3,
          start: "2026-11-16",
          quota: 150,
          lifts: 42,
          met: false,
          points: 67,
          bonuses: [
            "Situp"
          ],
          by_type: {
            Situp: 42,
            Pushup: 0,
            Squat: 0,
            Plank: 0
          },
          plank_seconds: 0,
          pending: 0
        },
        {
          index: 4,
          start: "2026-11-23",
          quota: 100,
          lifts: 0,
          met: false,
          points: 0,
          bonuses: [],
          by_type: {
            Situp: 0,
            Pushup: 0,
            Squat: 0,
            Plank: 0
          },
          plank_seconds: 0,
          pending: 0
        },
        {
          index: 5,
          start: "2026-11-30",
          quota: 100,
          lifts: 0,
          met: false,
          points: 0,
          bonuses: [],
          by_type: {
            Situp: 0,
            Pushup: 0,
            Squat: 0,
            Plank: 0
          },
          plank_seconds: 0,
          pending: 0
        },
        {
          index: 6,
          start: "2026-12-07",
          quota: 100,
          lifts: 0,
          met: false,
          points: 0,
          bonuses: [],
          by_type: {
            Situp: 0,
            Pushup: 0,
            Squat: 0,
            Plank: 0
          },
          plank_seconds: 0,
          pending: 0
        },
        {
          index: 7,
          start: "2026-12-14",
          quota: 100,
          lifts: 0,
          met: false,
          points: 0,
          bonuses: [],
          by_type: {
            Situp: 0,
            Pushup: 0,
            Squat: 0,
            Plank: 0
          },
          plank_seconds: 0,
          pending: 0
        },
        {
          index: 8,
          start: "2026-12-21",
          quota: 100,
          lifts: 0,
          met: false,
          points: 0,
          bonuses: [],
          by_type: {
            Situp: 0,
            Pushup: 0,
            Squat: 0,
            Plank: 0
          },
          plank_seconds: 0,
          pending: 0
        }
      ],
      warmup_lifts: 20,
      best_by_lift: {},
      form_score: null,
      steadiness: null,
      attempt_id: "a1-situp3",
      clip_url: "https://storage.example/a1-situp3-annotated.mp4",
      thumbnail_url: null,
      date: "2026-11-17",
      attempt_count: 6,
      history: [
        {
          score: 24,
          date: "2026-11-03"
        },
        {
          score: 45,
          date: "2026-11-04"
        },
        {
          score: 43,
          date: "2026-11-05"
        },
        {
          score: 70,
          date: "2026-11-10"
        },
        {
          score: 60,
          date: "2026-11-12"
        },
        {
          score: 42,
          date: "2026-11-17"
        }
      ],
      rank: 1
    },
    {
      user_id: "b1",
      name: "Ben",
      weight_class: null,
      gender: null,
      score: 355,
      streak: 0,
      best_streak: 1,
      weeks_met: 1,
      this_week: {
        index: 9,
        quota: 100,
        lifts: 0,
        met: false,
        pending: 0,
        by_type: {
          Situp: 0,
          Pushup: 0,
          Squat: 0,
          Plank: 0
        },
        plank_seconds: 0,
        leading: []
      },
      weeks: [
        {
          index: 1,
          start: "2026-11-02",
          quota: 100,
          lifts: 95,
          met: false,
          points: 145,
          bonuses: [
            "Pushup",
            "Squat"
          ],
          by_type: {
            Situp: 0,
            Pushup: 60,
            Squat: 35,
            Plank: 0
          },
          plank_seconds: 0,
          pending: 0
        },
        {
          index: 2,
          start: "2026-11-09",
          quota: 100,
          lifts: 100,
          met: true,
          points: 175,
          bonuses: [
            "Squat"
          ],
          by_type: {
            Situp: 0,
            Pushup: 0,
            Squat: 100,
            Plank: 0
          },
          plank_seconds: 0,
          pending: 0
        },
        {
          index: 3,
          start: "2026-11-16",
          quota: 125,
          lifts: 10,
          met: false,
          points: 35,
          bonuses: [
            "Plank"
          ],
          by_type: {
            Situp: 0,
            Pushup: 0,
            Squat: 0,
            Plank: 10
          },
          plank_seconds: 100,
          pending: 1
        },
        {
          index: 4,
          start: "2026-11-23",
          quota: 100,
          lifts: 0,
          met: false,
          points: 0,
          bonuses: [],
          by_type: {
            Situp: 0,
            Pushup: 0,
            Squat: 0,
            Plank: 0
          },
          plank_seconds: 0,
          pending: 0
        },
        {
          index: 5,
          start: "2026-11-30",
          quota: 100,
          lifts: 0,
          met: false,
          points: 0,
          bonuses: [],
          by_type: {
            Situp: 0,
            Pushup: 0,
            Squat: 0,
            Plank: 0
          },
          plank_seconds: 0,
          pending: 0
        },
        {
          index: 6,
          start: "2026-12-07",
          quota: 100,
          lifts: 0,
          met: false,
          points: 0,
          bonuses: [],
          by_type: {
            Situp: 0,
            Pushup: 0,
            Squat: 0,
            Plank: 0
          },
          plank_seconds: 0,
          pending: 0
        },
        {
          index: 7,
          start: "2026-12-14",
          quota: 100,
          lifts: 0,
          met: false,
          points: 0,
          bonuses: [],
          by_type: {
            Situp: 0,
            Pushup: 0,
            Squat: 0,
            Plank: 0
          },
          plank_seconds: 0,
          pending: 0
        },
        {
          index: 8,
          start: "2026-12-21",
          quota: 100,
          lifts: 0,
          met: false,
          points: 0,
          bonuses: [],
          by_type: {
            Situp: 0,
            Pushup: 0,
            Squat: 0,
            Plank: 0
          },
          plank_seconds: 0,
          pending: 0
        }
      ],
      warmup_lifts: 0,
      best_by_lift: {},
      form_score: null,
      steadiness: null,
      attempt_id: "b1-plank",
      clip_url: "https://storage.example/b1-plank-annotated.mp4",
      thumbnail_url: null,
      date: "2026-11-18",
      attempt_count: 4,
      history: [
        {
          score: 60,
          date: "2026-11-03"
        },
        {
          score: 35,
          date: "2026-11-05"
        },
        {
          score: 100,
          date: "2026-11-11"
        },
        {
          score: 10,
          date: "2026-11-18"
        }
      ],
      rank: 2
    },
    {
      user_id: "c1",
      name: "Cy",
      weight_class: null,
      gender: null,
      score: 0,
      streak: 0,
      best_streak: 0,
      weeks_met: 0,
      this_week: {
        index: 9,
        quota: 100,
        lifts: 0,
        met: false,
        pending: 0,
        by_type: {
          Situp: 0,
          Pushup: 0,
          Squat: 0,
          Plank: 0
        },
        plank_seconds: 0,
        leading: []
      },
      weeks: [
        {
          index: 1,
          start: "2026-11-02",
          quota: 100,
          lifts: 0,
          met: false,
          points: 0,
          bonuses: [],
          by_type: {
            Situp: 0,
            Pushup: 0,
            Squat: 0,
            Plank: 0
          },
          plank_seconds: 0,
          pending: 0
        },
        {
          index: 2,
          start: "2026-11-09",
          quota: 100,
          lifts: 0,
          met: false,
          points: 0,
          bonuses: [],
          by_type: {
            Situp: 0,
            Pushup: 0,
            Squat: 0,
            Plank: 0
          },
          plank_seconds: 0,
          pending: 0
        },
        {
          index: 3,
          start: "2026-11-16",
          quota: 100,
          lifts: 0,
          met: false,
          points: 0,
          bonuses: [],
          by_type: {
            Situp: 0,
            Pushup: 0,
            Squat: 0,
            Plank: 0
          },
          plank_seconds: 0,
          pending: 0
        },
        {
          index: 4,
          start: "2026-11-23",
          quota: 100,
          lifts: 0,
          met: false,
          points: 0,
          bonuses: [],
          by_type: {
            Situp: 0,
            Pushup: 0,
            Squat: 0,
            Plank: 0
          },
          plank_seconds: 0,
          pending: 0
        },
        {
          index: 5,
          start: "2026-11-30",
          quota: 100,
          lifts: 0,
          met: false,
          points: 0,
          bonuses: [],
          by_type: {
            Situp: 0,
            Pushup: 0,
            Squat: 0,
            Plank: 0
          },
          plank_seconds: 0,
          pending: 0
        },
        {
          index: 6,
          start: "2026-12-07",
          quota: 100,
          lifts: 0,
          met: false,
          points: 0,
          bonuses: [],
          by_type: {
            Situp: 0,
            Pushup: 0,
            Squat: 0,
            Plank: 0
          },
          plank_seconds: 0,
          pending: 0
        },
        {
          index: 7,
          start: "2026-12-14",
          quota: 100,
          lifts: 0,
          met: false,
          points: 0,
          bonuses: [],
          by_type: {
            Situp: 0,
            Pushup: 0,
            Squat: 0,
            Plank: 0
          },
          plank_seconds: 0,
          pending: 0
        },
        {
          index: 8,
          start: "2026-12-21",
          quota: 100,
          lifts: 0,
          met: false,
          points: 0,
          bonuses: [],
          by_type: {
            Situp: 0,
            Pushup: 0,
            Squat: 0,
            Plank: 0
          },
          plank_seconds: 0,
          pending: 0
        }
      ],
      warmup_lifts: 0,
      best_by_lift: {},
      form_score: null,
      steadiness: null,
      attempt_id: null,
      clip_url: null,
      thumbnail_url: null,
      date: null,
      attempt_count: 0,
      history: [],
      rank: 3
    }
  ],
  consistency: {
    rules: {
      base_quota: 100,
      ramp: 25,
      weeks: 8,
      quota_bonus: 50,
      type_bonus: 25,
      plank_seconds_per_lift: 10,
      tz: "America/New_York",
      week_start: "2026-11-02"
    },
    status: "ended",
    week_index: 9,
    weeks_total: 8,
    week_start: "2026-12-21",
    week_end: "2026-12-27",
    days_left: 0,
    type_leaders: {}
  }
};
