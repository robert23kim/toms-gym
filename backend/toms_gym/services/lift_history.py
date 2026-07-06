"""Row shaping for the profile lift-history endpoint (GET /users/<id>/lifts).

Pure and DB-free: takes a SQLAlchemy row mapping (Attempt ⋈ UserCompetition ⋈
Competition ⟕ LiftingResult with JSONB ->> extractions) and produces the JSON
row the frontend consumes. Every LiftingResult-side field is null-safe — the
LEFT JOIN yields NULLs for attempts that were never analyzed.
"""
from typing import Any, Mapping, Optional


def _to_int(value: Any) -> Optional[int]:
    try:
        return int(value) if value is not None else None
    except (TypeError, ValueError):
        return None


def _to_float(value: Any) -> Optional[float]:
    try:
        return float(value) if value is not None else None
    except (TypeError, ValueError):
        return None


def shape_lift_row(row: Mapping) -> dict:
    """Shape one history row. The analysis report's lift_type (e.g. 'plank')
    wins over the attempt's coarse lift_type when present."""
    get = row.get if hasattr(row, "get") else lambda k, d=None: getattr(row, k, d)

    created_at = get("created_at")
    return {
        "attempt_id": get("attempt_id"),
        "competition_id": get("competition_id"),
        "competition_name": get("competition_name"),
        "lift_type": get("report_lift_type") or get("lift_type"),
        "weight": _to_float(get("weight")),
        "created_at": created_at.isoformat() if created_at is not None else None,
        "status": get("status"),
        "analysis_status": get("analysis_status"),
        "grade": get("grade"),
        "total_reps": _to_int(get("total_reps")),
        "hold_s": _to_float(get("hold_s")),
    }
