from datetime import datetime, timedelta, timezone

from toms_gym.services.analysis_timing import (
    StageTimer, format_timing_line, queue_wait_seconds,
)


def test_stage_timer_records_each_stage_and_total():
    t = StageTimer()
    t.stage("token")
    t.stage("engine")
    total = t.total()
    assert set(t.stages) == {"token", "engine"}
    assert all(v >= 0 for v in t.stages.values())
    assert total >= sum(t.stages.values()) - 1e-6


def test_stage_timer_total_closes_open_stage():
    t = StageTimer()
    t.stage("store")
    t.total()
    assert "store" in t.stages


def test_queue_wait_handles_naive_and_aware_and_none():
    now = datetime(2026, 8, 29, 2, 0, 0, tzinfo=timezone.utc)
    assert queue_wait_seconds(None, now) is None
    assert queue_wait_seconds(now - timedelta(seconds=12), now) == 12.0
    assert queue_wait_seconds(datetime(2026, 8, 29, 1, 59, 30), now) == 30.0
    assert queue_wait_seconds(now + timedelta(seconds=5), now) == 0.0


def test_format_timing_line_is_greppable_key_values():
    line = format_timing_line(
        "lifting", "r1", "a1", "completed",
        {"engine": 131.456, "store": 0.1234}, 140.0,
        lift_type="pushup", queue_wait_s=None, engine_reported_s=130.9,
    )
    assert line.startswith("ANALYSIS_TIMING ")
    kv = dict(p.split("=", 1) for p in line.split(" ")[1:])
    assert kv["kind"] == "lifting"
    assert kv["engine_s"] == "131.46"
    assert kv["store_s"] == "0.12"
    assert kv["total_s"] == "140.0"
    assert kv["lift_type"] == "pushup"
    assert kv["engine_reported_s"] == "130.9"
    assert "queue_wait_s" not in kv
