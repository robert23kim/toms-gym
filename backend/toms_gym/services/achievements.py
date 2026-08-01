"""Milestone ladder + avatar catalog — pure and DB-free (like handicap.py).

Ladder tiers unlock 6-avatar DiceBear packs. `User.avatar` stores a catalog
key from AVATAR_CATALOG; resolution to a URL happens server-side so the
frontend never needs the catalog for display.
"""

_DICEBEAR = "https://api.dicebear.com/7.x"

LADDER = [
    {"key": "first_steps", "tier": 1, "title": "First Steps", "emoji": "🌱",
     "kind": "upload", "threshold": None},
    {"key": "half_minute", "tier": 2, "title": "Half Minute", "emoji": "⏱️",
     "kind": "hold", "threshold": 30},
    {"key": "iron_minute", "tier": 3, "title": "Iron Minute", "emoji": "💪",
     "kind": "hold", "threshold": 60},
    {"key": "two_minute_club", "tier": 4, "title": "Two-Minute Club", "emoji": "🔥",
     "kind": "hold", "threshold": 120},
    {"key": "statue_tier", "tier": 5, "title": "Statue Tier", "emoji": "🗿",
     "kind": "hold", "threshold": 180},
    {"key": "plank_royalty", "tier": 6, "title": "Plank Royalty", "emoji": "👑",
     "kind": "royalty", "threshold": None},
]

_STYLES = [
    ("first_steps", "avataaars", ["ace", "blaze", "coach", "dyno", "echo", "flex"]),
    ("half_minute", "bottts", ["bolt", "cog", "gear", "servo", "volt", "widget"]),
    ("iron_minute", "adventurer", ["arrow", "cliff", "dune", "ridge", "scout", "trail"]),
    ("two_minute_club", "lorelei", ["aria", "iris", "luna", "nova", "sage", "wren"]),
    ("statue_tier", "fun-emoji", ["beam", "grin", "jolt", "smirk", "wink", "zen"]),
    ("plank_royalty", "avataaars", ["monarch", "sovereign", "regal", "crown", "dynasty", "empire"]),
    # champion is a pack key, NOT a LADDER tier: it unlocks when the route
    # appends "champion" to earned keys (holder of >=1 challenge championship)
    ("champion", "big-smile", ["goldie", "laurel", "victor", "trophy", "glory", "champ"]),
]

AVATAR_CATALOG = {}
PACKS = []
for _ladder_key, _style, _seeds in _STYLES:
    _keys = []
    for _i, _seed in enumerate(_seeds, start=1):
        # legendary pack shares the avataaars style; namespace its keys
        _key = f"{_style}-{_seed}"
        AVATAR_CATALOG[_key] = f"{_DICEBEAR}/{_style}/svg?seed={_seed}"
        _keys.append(_key)
    PACKS.append((_ladder_key, _keys))

CHAMPION_PACK_KEYS = dict(PACKS)["champion"]

# The champion pack is unlocked by winning a challenge, not by a ladder tier.
CHAMPION_PACK = {"key": "champion", "title": "Champion", "emoji": "👑",
                 "hint": "Win a challenge"}


def badge_total():
    return len(LADDER)


def pack_hint(pack_key):
    """One line telling the user how to unlock a pack (None if unknown)."""
    if pack_key == CHAMPION_PACK["key"]:
        return CHAMPION_PACK["hint"]
    tier = next((t for t in LADDER if t["key"] == pack_key), None)
    if tier is None:
        return None
    if tier["kind"] == "upload":
        return "Upload your first video"
    if tier["kind"] == "hold":
        return f"Hold a plank for {tier['threshold']}s"
    return "5 plank attempts with a 120s hold"


def locked_packs(earned_keys):
    """Packs the user has NOT unlocked, each with its milestone hint."""
    earned = set(earned_keys)
    titles = {t["key"]: t for t in LADDER}
    locked = []
    for pack_key, _keys in PACKS:
        if pack_key in earned:
            continue
        if pack_key == CHAMPION_PACK["key"]:
            locked.append(dict(CHAMPION_PACK))
            continue
        tier = titles[pack_key]
        locked.append({"key": pack_key, "title": tier["title"],
                       "emoji": tier["emoji"], "hint": pack_hint(pack_key)})
    return locked


def unlocked_avatars(earned_keys):
    """Unlocked avatars as [{key, url}] — the frontend never needs the catalog."""
    return [{"key": k, "url": AVATAR_CATALOG[k]}
            for k in unlocked_avatar_keys(earned_keys)]


def evaluate(stats):
    """Earned ladder keys for {'has_upload', 'best_hold_s', 'plank_attempts'}."""
    best = stats.get("best_hold_s") or 0
    attempts = stats.get("plank_attempts") or 0
    earned = []
    for t in LADDER:
        if t["kind"] == "upload" and stats.get("has_upload"):
            earned.append(t["key"])
        elif t["kind"] == "hold" and best >= t["threshold"]:
            earned.append(t["key"])
        elif t["kind"] == "royalty" and attempts >= 5 and best >= 120:
            earned.append(t["key"])
    return earned


def unlocked_avatar_keys(earned_keys):
    earned = set(earned_keys)
    keys = []
    for ladder_key, pack in PACKS:
        if ladder_key in earned:
            keys.extend(pack)
    return keys


def resolve_avatar_url(key):
    return AVATAR_CATALOG.get(key)


def next_milestone(stats, earned_keys):
    """First unearned tier with progress numbers (None when all earned)."""
    earned = set(earned_keys)
    for t in LADDER:
        if t["key"] in earned:
            continue
        progress = {
            "best_hold_s": stats.get("best_hold_s"),
            "needed_s": t["threshold"] if t["kind"] == "hold" else (120 if t["kind"] == "royalty" else None),
            "plank_attempts": stats.get("plank_attempts") or 0,
            "needed_attempts": 5 if t["kind"] == "royalty" else None,
        }
        return {"key": t["key"], "title": t["title"], "emoji": t["emoji"],
                "tier": t["tier"], "progress": progress}
    return None
