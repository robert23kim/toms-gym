from toms_gym.services.bowling_insights import compute_insights, merge_duplicate_games

TOM_FRAMES = [["X"], ["8", "1"], ["X"], ["9", "/"], ["X"], ["6", "3"], ["8", "/"], ["X"], ["9", "-"], ["7", "/", "9"]]
CHRIS_FRAMES = [["X"], ["9", "-"], ["X"], ["8", "-"], ["X"], ["9", "/"], ["9", "/"], ["9", "/"], ["X"], ["X", "8", "-"]]

# three sessions x three games; slot 3 averages 15 below slot 1, spread is wide
TOTALS = [
    {"played_on": "2026-08-01", "game_number": 1, "total_score": 180, "hdcp": 30, "frames": None},
    {"played_on": "2026-08-01", "game_number": 2, "total_score": 120, "hdcp": 30, "frames": None},
    {"played_on": "2026-08-01", "game_number": 3, "total_score": 165, "hdcp": 30, "frames": None},
    {"played_on": "2026-08-08", "game_number": 1, "total_score": 200, "hdcp": 28, "frames": None},
    {"played_on": "2026-08-08", "game_number": 2, "total_score": 150, "hdcp": 28, "frames": None},
    {"played_on": "2026-08-08", "game_number": 3, "total_score": 190, "hdcp": 28, "frames": None},
    {"played_on": "2026-08-15", "game_number": 1, "total_score": 220, "hdcp": 24, "frames": None},
    {"played_on": "2026-08-15", "game_number": 2, "total_score": 210, "hdcp": 24, "frames": None},
    {"played_on": "2026-08-15", "game_number": 3, "total_score": 200, "hdcp": 24, "frames": None},
]

FRAME_GAMES = [
    {"played_on": "2026-08-20", "game_number": 1, "total_score": 163, "hdcp": None, "frames": TOM_FRAMES},
    {"played_on": "2026-08-20", "game_number": 2, "total_score": 178, "hdcp": None, "frames": CHRIS_FRAMES},
]


def test_empty():
    out = compute_insights([])
    assert out["games"] == 0
    assert out["frame_stats"] is None
    assert [t["key"] for t in out["tips"]] == ["no_games"]


def test_totals_summary():
    out = compute_insights(TOTALS)
    assert out["games"] == 9
    assert out["average"] == 181.7
    assert out["high"] == 220
    assert out["low"] == 120
    assert out["stdev"] == 31.8
    assert out["over_200"] == 4
    assert out["hdcp_latest"] == 24
    assert out["frame_stats"] is None


def test_totals_trend_and_slots():
    out = compute_insights(TOTALS)
    assert out["trend"] == {"last5": 194.0, "prior": 166.3, "delta": 27.7}
    assert out["slot_averages"] == {"1": 200.0, "2": 160.0, "3": 185.0}


def test_sessions_series_oldest_first():
    out = compute_insights(TOTALS)
    assert out["sessions"] == 3
    assert out["session_series"] == [
        {"played_on": "2026-08-01", "average": 155.0, "games": 3},
        {"played_on": "2026-08-08", "average": 180.0, "games": 3},
        {"played_on": "2026-08-15", "average": 210.0, "games": 3},
    ]


def test_totals_tips():
    keys = [t["key"] for t in compute_insights(TOTALS)["tips"]]
    assert "fade_game3" in keys
    assert "consistency" in keys
    assert "snap_a_game" in keys
    assert len(keys) <= 4
    assert all(t["title"] and t["body"] for t in compute_insights(TOTALS)["tips"])


def test_slow_start_tip():
    reversed_slots = [
        dict(g, total_score={1: 165, 2: 160, 3: 200}[g["game_number"]]) for g in TOTALS
    ]
    keys = [t["key"] for t in compute_insights(reversed_slots)["tips"]]
    assert "slow_start" in keys
    assert "fade_game3" not in keys


def test_frame_stats():
    fs = compute_insights(FRAME_GAMES)["frame_stats"]
    assert fs["frames_analyzed"] == 20
    assert fs["strike_pct"] == 0.409
    assert fs["spare_pct"] == 0.5
    assert fs["open_pct"] == 0.273
    assert fs["first_ball_avg"] == 9.0
    assert fs["single_pin_conversion"] == 0.667
    assert fs["tenth_frame_avg"] == 18.5
    assert fs["strike_by_frame"] == [1.0, 0.0, 1.0, 0.0, 1.0, 0.0, 0.0, 0.5, 0.5, 0.5]
    assert fs["clean_games"] == 0
    assert fs["pins_left"] == 66


def test_frame_tips():
    tips = compute_insights(FRAME_GAMES)["tips"]
    keys = [t["key"] for t in tips]
    assert keys[0] == "spares"
    assert "33" in tips[0]["stat"] or "33" in tips[0]["body"]
    assert "snap_a_game" not in keys


def test_clean_game_and_no_spare_tip():
    clean = [{"played_on": "2026-08-20", "game_number": 1, "total_score": 190,
              "hdcp": None, "frames": [["9", "/"]] * 9 + [["9", "/", "9"]]}]
    out = compute_insights(clean)
    assert out["frame_stats"]["clean_games"] == 1
    assert out["frame_stats"]["spare_pct"] == 1.0
    assert "spares" not in [t["key"] for t in out["tips"]]


def test_first_ball_tip_on_weak_first_balls():
    weak = [{"played_on": "2026-08-20", "game_number": 1, "total_score": 80,
             "hdcp": None, "frames": [["4", "3"]] * 9 + [["4", "3"]]}]
    keys = [t["key"] for t in compute_insights(weak)["tips"]]
    assert "first_ball" in keys


def test_invalid_frames_are_skipped_not_fatal():
    bad = [{"played_on": "2026-08-20", "game_number": 1, "total_score": 100,
            "hdcp": None, "frames": [["9", "9"]] + [["9", "-"]] * 9}]
    fs = compute_insights(bad)["frame_stats"]
    assert fs["frames_analyzed"] == 9


def test_merge_keeps_night_slot_and_takes_screen_frames():
    night = [
        {"id": "n1", "played_on": "2026-09-04", "game_number": 1, "total_score": 153, "hdcp": 0, "frames": None, "has_frames": False, "sheet_type": "night"},
        {"id": "n2", "played_on": "2026-09-04", "game_number": 2, "total_score": 200, "hdcp": 0, "frames": None, "has_frames": False, "sheet_type": "night"},
        {"id": "n3", "played_on": "2026-09-04", "game_number": 3, "total_score": 162, "hdcp": 0, "frames": None, "has_frames": False, "sheet_type": "night"},
    ]
    screens = [
        {"id": "s1", "played_on": "2026-09-04", "game_number": 1, "total_score": 162, "hdcp": None, "frames": TOM_FRAMES, "has_frames": True, "sheet_type": "game"},
        {"id": "s2", "played_on": "2026-09-04", "game_number": 1, "total_score": 200, "hdcp": None, "frames": CHRIS_FRAMES, "has_frames": True, "sheet_type": "game"},
    ]
    merged = merge_duplicate_games(screens + night)
    assert [g["total_score"] for g in merged] == [162, 200, 153]
    by_score = {g["total_score"]: g for g in merged}
    assert by_score[162]["game_number"] == 3 and by_score[162]["frames"] == TOM_FRAMES and by_score[162]["hdcp"] == 0
    assert by_score[200]["game_number"] == 2 and by_score[200]["frames"] == CHRIS_FRAMES
    assert by_score[153]["frames"] is None and by_score[153]["has_frames"] is False
    # the merge must not mutate the caller's rows
    assert screens[0]["game_number"] == 1 and night[2]["frames"] is None


def test_merge_leaves_distinct_games_and_other_dates_alone():
    games = TOTALS + FRAME_GAMES
    assert merge_duplicate_games(games) == games
    same_score_other_day = [
        {"played_on": "2026-09-04", "game_number": 1, "total_score": 153, "hdcp": 0, "frames": None, "sheet_type": "night"},
        {"played_on": "2026-09-11", "game_number": 1, "total_score": 153, "hdcp": None, "frames": TOM_FRAMES, "sheet_type": "game"},
    ]
    assert len(merge_duplicate_games(same_score_other_day)) == 2


def test_insights_count_a_double_stored_night_once():
    night = [{"played_on": "2026-09-04", "game_number": i, "total_score": t, "hdcp": 0, "frames": None, "sheet_type": "night"}
             for i, t in enumerate([153, 200, 162], start=1)]
    screens = [{"played_on": "2026-09-04", "game_number": 1, "total_score": t, "hdcp": None, "frames": TOM_FRAMES, "sheet_type": "game"}
               for t in [153, 200, 162]]
    assert compute_insights(merge_duplicate_games(night + screens))["games"] == 3


def test_merge_propagates_has_frames_without_frame_payload():
    rows = [
        {"played_on": "2026-09-04", "game_number": 2, "total_score": 200, "hdcp": 0, "has_frames": False, "sheet_type": "night"},
        {"played_on": "2026-09-04", "game_number": 1, "total_score": 200, "hdcp": None, "has_frames": True, "sheet_type": "game"},
    ]
    merged = merge_duplicate_games(rows)
    assert len(merged) == 1 and merged[0]["has_frames"] is True and merged[0]["game_number"] == 2
