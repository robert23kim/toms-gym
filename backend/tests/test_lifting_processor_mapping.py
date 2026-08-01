"""DB-free mapping tests: frontend label -> DB enum -> engine lift_type.

The three-hop mapping (frontend id -> Postgres lift_type enum -> analysis
engine name) lives in two modules that are easy to let drift apart, so pin
both hops here.
"""
from toms_gym.integrations.lifting_processor import _normalize_lift_type
from toms_gym.routes.upload_routes import LIFT_TYPE_MAPPING


def test_pushup_frontend_label_maps_to_db_enum():
    assert LIFT_TYPE_MAPPING["Pushup"] == "Pushup"


def test_pushup_db_enum_maps_to_engine_name():
    assert _normalize_lift_type("Pushup") == "pushup"


def test_plank_mapping_is_unchanged():
    assert LIFT_TYPE_MAPPING["Plank"] == "Plank"
    assert _normalize_lift_type("Plank") == "plank"


def test_unknown_still_falls_back_to_bicep_curl():
    assert _normalize_lift_type("Zumba") == "bicep_curl"
