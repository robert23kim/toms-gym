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


def test_catalog_has_42_resolvable_avatars():
    assert len(AVATAR_CATALOG) == 42
    assert sum(len(keys) for _, keys in PACKS) == 42
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


def test_champion_pack_exists_and_resolves():
    from toms_gym.services.achievements import CHAMPION_PACK_KEYS
    assert len(CHAMPION_PACK_KEYS) == 6
    for key in CHAMPION_PACK_KEYS:
        assert key in AVATAR_CATALOG


def test_champion_pack_unlocked_only_via_champion_key():
    from toms_gym.services.achievements import CHAMPION_PACK_KEYS
    assert not set(CHAMPION_PACK_KEYS) & set(unlocked_avatar_keys(["first_steps"]))
    assert set(CHAMPION_PACK_KEYS) <= set(unlocked_avatar_keys(["champion"]))


def test_pack_hint_explains_how_to_unlock_each_pack():
    from toms_gym.services.achievements import pack_hint
    assert pack_hint("first_steps") == "Upload your first video"
    assert pack_hint("half_minute") == "Hold a plank for 30s"
    assert pack_hint("statue_tier") == "Hold a plank for 180s"
    assert pack_hint("plank_royalty") == "5 plank attempts with a 120s hold"
    assert pack_hint("champion") == "Win a challenge"
    assert pack_hint("nope") is None


def test_locked_packs_lists_every_unearned_pack():
    from toms_gym.services.achievements import locked_packs
    locked = locked_packs(["first_steps"])
    keys = [p["key"] for p in locked]
    assert "first_steps" not in keys
    assert "champion" in keys and "half_minute" in keys
    champ = next(p for p in locked if p["key"] == "champion")
    assert champ == {"key": "champion", "title": "Champion", "emoji": "👑",
                     "hint": "Win a challenge"}


def test_unlocked_avatars_resolve_to_urls():
    from toms_gym.services.achievements import unlocked_avatars
    avatars = unlocked_avatars(["first_steps"])
    assert len(avatars) == 6
    assert all(a["url"].startswith("https://api.dicebear.com/7.x/") for a in avatars)
    assert all(a["key"] in AVATAR_CATALOG for a in avatars)


def test_champion_is_not_a_ladder_tier():
    # champion is a pack unlock, not a milestone: evaluate() never emits it
    assert "champion" not in evaluate(_stats(True, 400.0, 20))
    assert badge_total() == 6
