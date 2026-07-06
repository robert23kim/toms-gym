"""DB-free tests for the lift-history row shaper (services/lift_history.py)."""
from datetime import datetime, timezone

from toms_gym.services.lift_history import shape_lift_row


def _base_row(**over):
    row = {
        "attempt_id": "a1",
        "lift_type": "Squat",
        "weight": 100.0,
        "video_url": "https://example.com/v.mp4",
        "created_at": datetime(2026, 7, 4, 12, 0, tzinfo=timezone.utc),
        "status": "completed",
        "competition_id": "c1",
        "competition_name": "Summer Squat-Off",
        "analysis_status": "completed",
        "grade": "A",
        "report_lift_type": "squat",
        "total_reps": "5",
        "hold_s": None,
    }
    row.update(over)
    return row


def test_rep_lift_row():
    out = shape_lift_row(_base_row())
    assert out["attempt_id"] == "a1"
    assert out["competition_id"] == "c1"
    assert out["grade"] == "A"
    assert out["total_reps"] == 5  # cast from string
    assert out["hold_s"] is None
    assert out["lift_type"] == "squat"  # report lift_type wins
    assert out["created_at"] == "2026-07-04T12:00:00+00:00"


def test_plank_row_casts_hold_seconds():
    out = shape_lift_row(
        _base_row(report_lift_type="plank", grade=None, total_reps=None, hold_s="244.203")
    )
    assert out["lift_type"] == "plank"
    assert abs(out["hold_s"] - 244.203) < 1e-6
    assert out["grade"] is None
    assert out["total_reps"] is None


def test_no_analysis_row_is_null_safe():
    out = shape_lift_row(
        _base_row(analysis_status=None, grade=None, report_lift_type=None,
                  total_reps=None, hold_s=None)
    )
    assert out["analysis_status"] is None
    assert out["grade"] is None
    assert out["lift_type"] == "Squat"  # falls back to attempt lift_type


def test_missing_keys_tolerated():
    out = shape_lift_row({"attempt_id": "a2"})
    assert out["attempt_id"] == "a2"
    assert out["grade"] is None
    assert out["created_at"] is None
    assert out["weight"] is None


def test_bad_numeric_strings_become_none():
    out = shape_lift_row(_base_row(total_reps="garbage", hold_s="nan-ish"))
    assert out["total_reps"] is None
    assert out["hold_s"] is None
