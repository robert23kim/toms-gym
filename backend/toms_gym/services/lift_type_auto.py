"""Automatic lift type: the switch, competition eligibility and engine I/O.

Pure and DB-free. Design: docs/plans/2026-11-13-auto-lift-type.md.
"""
from __future__ import annotations

import math
import os
from typing import Iterable, List, Optional, Tuple

AUTO = "Auto"
CONFIRM_THRESHOLD = 0.6

_BODYWEIGHT = frozenset({"pushup", "situp", "plank"})


def switch_on() -> bool:
    """AUTO_LIFT_TYPE, read per call so a revision flip needs no reload. Default off."""
    return os.environ.get("AUTO_LIFT_TYPE", "0").strip().lower() in ("1", "true")


def is_auto(lift_type) -> bool:
    return isinstance(lift_type, str) and lift_type.strip().lower() == "auto"


def eligible(lifttypes, mode) -> bool:
    """Two or more declared types, every one bodyweight; club squats are air squats."""
    if not isinstance(lifttypes, list) or len(lifttypes) < 2:
        return False
    bodyweight = _BODYWEIGHT | ({"squat"} if mode == "consistency" else frozenset())
    return all(isinstance(t, str) and t.strip().lower() in bodyweight for t in lifttypes)


def enabled_for(lifttypes, mode) -> bool:
    return switch_on() and eligible(lifttypes, mode)


def _key(name: str) -> str:
    return name.strip().lower().replace(" ", "_")


def engine_candidates(lifttypes: Iterable) -> List[str]:
    return [_key(t) for t in (lifttypes or []) if isinstance(t, str) and t.strip() and not is_auto(t)]


def match_declared(raw, lifttypes) -> Optional[str]:
    """The declared spelling `raw` names (case-insensitive, engine underscores ok); Auto never."""
    if not isinstance(raw, str) or not raw.strip() or is_auto(raw):
        return None
    want = _key(raw)
    for t in lifttypes or []:
        if isinstance(t, str) and not is_auto(t) and _key(t) == want:
            return t
    return None


def _confidence(value) -> Optional[float]:
    if isinstance(value, bool):
        return None
    try:
        c = float(value)
    except (TypeError, ValueError):
        return None
    if not math.isfinite(c):
        return None
    return min(1.0, max(0.0, c))


def detection(result, lifttypes) -> Tuple[Optional[str], Optional[float]]:
    """(declared type, confidence) from an engine response; the summary is `report`."""
    result = result if isinstance(result, dict) else {}
    report = result.get("report") if isinstance(result.get("report"), dict) else {}

    def pick(key):
        return report[key] if report.get(key) is not None else result.get(key)

    return (match_declared(pick("detected_lift_type"), lifttypes),
            _confidence(pick("lift_type_confidence")))


def needs_lift_type(lift_type, processing_status) -> bool:
    return is_auto(lift_type) and processing_status not in ("queued", "processing")
