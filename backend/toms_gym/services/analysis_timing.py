"""Per-stage timing for analysis jobs, emitted as one greppable log line.

Query in Cloud Logging with textPayload:"ANALYSIS_TIMING". Every stage is a
float number of seconds (or absent when unknown), so the line can be parsed
with a simple key=value split.
"""
import time
from datetime import datetime, timezone


class StageTimer:
    """Accumulates named stage durations; `stage(name)` closes the previous stage."""

    def __init__(self):
        self._t0 = time.monotonic()
        self._last = self._t0
        self._current = None
        self.stages: dict[str, float] = {}

    def stage(self, name: str) -> None:
        self._close()
        self._current = name
        self._last = time.monotonic()

    def _close(self) -> None:
        if self._current is not None:
            now = time.monotonic()
            self.stages[self._current] = self.stages.get(self._current, 0.0) + (now - self._last)
            self._current = None

    def total(self) -> float:
        self._close()
        return time.monotonic() - self._t0


def queue_wait_seconds(created_at, now=None) -> float | None:
    """Seconds between the job row's creation and now (None if unknown)."""
    if created_at is None:
        return None
    now = now or datetime.now(timezone.utc)
    if created_at.tzinfo is None:
        created_at = created_at.replace(tzinfo=timezone.utc)
    return max(0.0, (now - created_at).total_seconds())


def format_timing_line(kind: str, result_id, attempt_id, status: str,
                       stages: dict, total_s: float, **extra) -> str:
    fields = {
        "kind": kind,
        "result": result_id,
        "attempt": attempt_id,
        "status": status,
    }
    for k, v in extra.items():
        if v is not None:
            fields[k] = v
    for k, v in stages.items():
        fields[f"{k}_s"] = round(v, 2)
    fields["total_s"] = round(total_s, 2)
    return "ANALYSIS_TIMING " + " ".join(f"{k}={v}" for k, v in fields.items())
