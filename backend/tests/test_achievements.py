"""DB-free tests for the achievements ladder (services/achievements.py)."""
from toms_gym.services.achievements import (
    LADDER, AVATAR_CATALOG, PACKS, evaluate, unlocked_avatar_keys,
    resolve_avatar_url, next_milestone, badge_total,
)


def _stats(has_upload=False, best_hold_s=None, plank_attempts=0):
    return {"has_upload": has_upload, "best_hold_s": best_hold_s,
            "plank_attempts": plank_attempts}


def test_ladder_shape():
    assert [t["key"] for t in LADDER] == [
        "first_steps", "half_minute", "iron_minute",
        "two_minute_club", "statue_tier", "plank_royalty",
    ]
    assert badge_total() == 6


def test_no_activity_earns_nothing():
    assert evaluate(_stats()) == []


def test_first_upload_earns_tier1_only():
    assert evaluate(_stats(has_upload=True)) == ["first_steps"]


def test_hold_thresholds_pin_boundaries():
    assert "half_minute" in evaluate(_stats(True, 30.0, 1))
    assert "half_minute" not in evaluate(_stats(True, 29.9, 1))
    assert "iron_minute" in evaluate(_stats(True, 60.0, 1))
    assert "two_minute_club" in evaluate(_stats(True, 120.0, 1))
    assert "statue_tier" in evaluate(_stats(True, 180.0, 1))


def test_royalty_needs_attempts_and_hold():
    assert "plank_royalty" not in evaluate(_stats(True, 240.0, 4))
    assert "plank_royalty" not in evaluate(_stats(True, 119.0, 9))
    assert "plank_royalty" in evaluate(_stats(True, 120.0, 5))


def test_unlocked_avatars_accumulate_by_tier():
    none = unlocked_avatar_keys([])
    t1 = unlocked_avatar_keys(["first_steps"])
    t2 = unlocked_avatar_keys(["first_steps", "half_minute"])
    assert none == []
    assert len(t1) == 6 and len(t2) == 12
    assert set(t1) <= set(t2)


def test_catalog_has_36_resolvable_avatars():
    assert len(AVATAR_CATALOG) == 36
    assert sum(len(keys) for _, keys in PACKS) == 36
    for key, url in AVATAR_CATALOG.items():
        assert resolve_avatar_url(key) == url
        assert url.startswith("https://api.dicebear.com/7.x/")
    assert resolve_avatar_url("nope-1") is None


def test_next_milestone_progress():
    nxt = next_milestone(_stats(True, 102.0, 2), ["first_steps", "half_minute", "iron_minute"])
    assert nxt["key"] == "two_minute_club"
    assert nxt["progress"]["best_hold_s"] == 102.0
    assert nxt["progress"]["needed_s"] == 120
    # all earned -> None
    assert next_milestone(_stats(True, 300.0, 9), [t["key"] for t in LADDER]) is None
