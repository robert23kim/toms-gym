import type { ChallengeLeaderboard } from "../lib/types";

export const REPORTER_ID = "00000000-0000-4000-8000-0000000000a1";

export const liveClubBoard: ChallengeLeaderboard = {
  "competition_id": "32ca7bad-a970-4a09-acec-02b768793063",
  "consistency": {
    "days_left": 3,
    "rules": {
      "base_quota": 100,
      "plank_seconds_per_lift": 10,
      "quota_bonus": 50,
      "ramp": 25,
      "type_bonus": 25,
      "tz": "America/New_York",
      "week_start": "2026-11-02",
      "weeks": 8
    },
    "status": "live",
    "type_leaders": {
      "Plank": [
        {
          "amount": 180.3530257154494,
          "name": "athlete.two",
          "user_id": "00000000-0000-4000-8000-0000000000a2"
        }
      ],
      "Pushup": [
        {
          "amount": 71,
          "name": "athlete.two",
          "user_id": "00000000-0000-4000-8000-0000000000a2"
        }
      ],
      "Situp": [
        {
          "amount": 75.5,
          "name": "athlete.two",
          "user_id": "00000000-0000-4000-8000-0000000000a2"
        }
      ],
      "Squat": [
        {
          "amount": 12,
          "name": "athlete.one",
          "user_id": "00000000-0000-4000-8000-0000000000a1"
        }
      ]
    },
    "week_end": "2026-11-15",
    "week_index": 2,
    "week_start": "2026-11-09",
    "weeks_total": 8
  },
  "lift_types": [
    "Situp",
    "Pushup",
    "Squat",
    "Plank"
  ],
  "metric": "consistency",
  "momentum": {
    "joined": 2,
    "uploaded_today": 0
  },
  "rows": [
    {
      "attempt_count": 14,
      "attempt_id": "00000000-0000-4000-8000-0000000a7701",
      "best_by_lift": {},
      "best_streak": 2,
      "clip_url": "https://storage.example/lifting/clip-1/annotated.mp4",
      "date": "2026-11-13",
      "form_score": null,
      "gender": "male",
      "history": [
        {
          "date": "2026-11-02",
          "score": 15
        },
        {
          "date": "2026-11-02",
          "score": 31.5
        },
        {
          "date": "2026-11-02",
          "score": 5
        },
        {
          "date": "2026-11-03",
          "score": 21
        },
        {
          "date": "2026-11-03",
          "score": 6
        },
        {
          "date": "2026-11-05",
          "score": 29
        },
        {
          "date": "2026-11-09",
          "score": 14
        },
        {
          "date": "2026-11-09",
          "score": 8
        },
        {
          "date": "2026-11-12",
          "score": 22
        },
        {
          "date": "2026-11-12",
          "score": 36
        },
        {
          "date": "2026-11-12",
          "score": 12
        },
        {
          "date": "2026-11-13",
          "score": 18
        },
        {
          "date": "2026-11-13",
          "score": 32
        },
        {
          "date": "2026-11-13",
          "score": 5
        }
      ],
      "name": "athlete.one",
      "rank": 1,
      "score": 375,
      "steadiness": null,
      "streak": 2,
      "this_week": {
        "by_type": {
          "Plank": 13,
          "Pushup": 54,
          "Situp": 68,
          "Squat": 12
        },
        "index": 2,
        "leading": [
          "Squat"
        ],
        "lifts": 147,
        "met": true,
        "pending": 0,
        "plank_seconds": 136.79121080033903,
        "quota": 125
      },
      "thumbnail_url": null,
      "user_id": "00000000-0000-4000-8000-0000000000a1",
      "warmup_lifts": 0,
      "weeks": [
        {
          "bonuses": [
            "Pushup",
            "Plank"
          ],
          "by_type": {
            "Plank": 11,
            "Pushup": 65,
            "Situp": 31.5,
            "Squat": 0
          },
          "index": 1,
          "lifts": 107.5,
          "met": true,
          "pending": 0,
          "plank_seconds": 119.48552762923352,
          "points": 200,
          "quota": 100,
          "start": "2026-11-02"
        },
        {
          "bonuses": [],
          "by_type": {
            "Plank": 13,
            "Pushup": 54,
            "Situp": 68,
            "Squat": 12
          },
          "index": 2,
          "lifts": 147,
          "met": true,
          "pending": 0,
          "plank_seconds": 136.79121080033903,
          "points": 175,
          "quota": 125,
          "start": "2026-11-09"
        }
      ],
      "weeks_met": 2,
      "weight_class": "85kg"
    },
    {
      "attempt_count": 14,
      "attempt_id": "00000000-0000-4000-8000-0000000a7702",
      "best_by_lift": {},
      "best_streak": 2,
      "clip_url": "https://storage.example/lifting/clip-2/annotated.mp4",
      "date": "2026-11-13",
      "form_score": null,
      "gender": "male",
      "history": [
        {
          "date": "2026-11-02",
          "score": 24
        },
        {
          "date": "2026-11-03",
          "score": 27
        },
        {
          "date": "2026-11-06",
          "score": 8
        },
        {
          "date": "2026-11-06",
          "score": 28
        },
        {
          "date": "2026-11-06",
          "score": 13
        },
        {
          "date": "2026-11-10",
          "score": 29
        },
        {
          "date": "2026-11-10",
          "score": 6
        },
        {
          "date": "2026-11-10",
          "score": 25
        },
        {
          "date": "2026-11-11",
          "score": 16.5
        },
        {
          "date": "2026-11-11",
          "score": 5
        },
        {
          "date": "2026-11-11",
          "score": 21
        },
        {
          "date": "2026-11-13",
          "score": 30
        },
        {
          "date": "2026-11-13",
          "score": 5
        },
        {
          "date": "2026-11-13",
          "score": 25
        }
      ],
      "name": "athlete.two",
      "rank": 2,
      "score": 350,
      "steadiness": null,
      "streak": 2,
      "this_week": {
        "by_type": {
          "Plank": 16,
          "Pushup": 71,
          "Situp": 75.5,
          "Squat": 0
        },
        "index": 2,
        "leading": [
          "Situp",
          "Pushup",
          "Plank"
        ],
        "lifts": 162.5,
        "met": true,
        "pending": 0,
        "plank_seconds": 180.3530257154494,
        "quota": 125
      },
      "thumbnail_url": null,
      "user_id": "00000000-0000-4000-8000-0000000000a2",
      "warmup_lifts": 0,
      "weeks": [
        {
          "bonuses": [
            "Situp"
          ],
          "by_type": {
            "Plank": 8,
            "Pushup": 52,
            "Situp": 40,
            "Squat": 0
          },
          "index": 1,
          "lifts": 100,
          "met": true,
          "pending": 0,
          "plank_seconds": 82.7886568703274,
          "points": 175,
          "quota": 100,
          "start": "2026-11-02"
        },
        {
          "bonuses": [],
          "by_type": {
            "Plank": 16,
            "Pushup": 71,
            "Situp": 75.5,
            "Squat": 0
          },
          "index": 2,
          "lifts": 162.5,
          "met": true,
          "pending": 0,
          "plank_seconds": 180.3530257154494,
          "points": 175,
          "quota": 125,
          "start": "2026-11-09"
        }
      ],
      "weeks_met": 2,
      "weight_class": "85kg"
    }
  ]
};
