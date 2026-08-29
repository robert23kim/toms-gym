"""Ten-pin scoring from printed roll symbols. Pure, DB-free."""


class InvalidFrame(ValueError):
    pass


def _pins(symbol, prev):
    s = str(symbol).strip().upper()
    if s == "X":
        return 10
    if s == "/":
        if prev is None:
            raise InvalidFrame("spare with no first ball")
        return 10 - prev
    if s in ("-", "F", "", "O", "_"):
        return 0
    if s.isdigit():
        v = int(s)
        if v > 9:
            raise InvalidFrame(f"pin count {v} out of range")
        return v
    raise InvalidFrame(f"unknown symbol {symbol!r}")


def frame_pins(rolls, frame_index):
    """Symbols for one frame -> pins felled per ball."""
    if not rolls:
        raise InvalidFrame("empty frame")
    tenth = frame_index == 9
    if len(rolls) > (3 if tenth else 2):
        raise InvalidFrame("too many rolls")
    pins = []
    prev = None
    for sym in rolls:
        p = _pins(sym, prev)
        if prev is not None and str(sym).strip().upper() != "/" and prev + p > 10:
            raise InvalidFrame(f"{prev}+{p} exceeds 10")
        pins.append(p)
        # a strike or a spare resets the rack; otherwise the next ball completes it
        prev = None if (p == 10 or prev is not None) else p
    if not tenth:
        if pins[0] == 10 and len(pins) > 1:
            raise InvalidFrame("a strike ends the frame")
        if len(rolls) == 1 and pins[0] != 10:
            raise InvalidFrame("open frame needs two balls")
    else:
        need_third = pins[0] == 10 or (len(pins) >= 2 and pins[0] + pins[1] == 10)
        if need_third and len(pins) < 3:
            raise InvalidFrame("tenth frame bonus ball missing")
        if not need_third and len(pins) == 3:
            raise InvalidFrame("tenth frame has an extra ball")
    return pins


def score_frames(frames):
    """Score up to ten frames. Never raises: bad frames land in ``errors``."""
    frames = list(frames)[:10]
    rolls = []
    errors = []
    for i, f in enumerate(frames):
        try:
            p = frame_pins(f, i)
        except InvalidFrame as e:
            errors.append(f"frame {i + 1}: {e}")
            p = [0, 0]
        rolls.extend(p)
    cumulative = []
    total = 0
    i = 0
    complete = len(frames) == 10
    for fr in range(len(frames)):
        if i >= len(rolls):
            complete = False
            break
        first = rolls[i]
        if fr == 9:
            total += sum(rolls[i:])
            i = len(rolls)
        elif first == 10:
            bonus = rolls[i + 1:i + 3]
            if len(bonus) < 2:
                complete = False
            total += 10 + sum(bonus)
            i += 1
        elif i + 1 < len(rolls) and first + rolls[i + 1] == 10:
            bonus = rolls[i + 2:i + 3]
            if not bonus:
                complete = False
            total += 10 + sum(bonus)
            i += 2
        else:
            total += first + (rolls[i + 1] if i + 1 < len(rolls) else 0)
            i += 2
        cumulative.append(total)
    return {
        "cumulative": cumulative,
        "total": total,
        "valid": not errors,
        "errors": errors,
        "complete": complete,
    }


def validate_night_row(games, scratch, hdcp, total):
    """Check the two printed checksums on a night-results row."""
    present = [g for g in games if g is not None]
    if len(present) != len(games):
        return False, "missing game score"
    if scratch is not None and sum(present) != scratch:
        return False, f"games sum {sum(present)} != scratch {scratch}"
    if scratch is not None and hdcp is not None and total is not None and scratch + hdcp != total:
        return False, f"scratch {scratch} + hdcp {hdcp} != total {total}"
    return True, None


def infer_night_row(games, scratch, hdcp, total):
    """Fill values the checksums determine uniquely. Returns (row, inferred_keys)."""
    games = list(games)
    inferred = []
    missing = [i for i, g in enumerate(games) if g is None]
    if len(missing) == 1 and scratch is not None:
        i = missing[0]
        games[i] = scratch - sum(g for g in games if g is not None)
        inferred.append(f"games[{i}]")
    elif not missing and scratch is None:
        scratch = sum(games)
        inferred.append("scratch")
    if scratch is not None:
        if total is None and hdcp is not None:
            total = scratch + hdcp
            inferred.append("total")
        elif hdcp is None and total is not None:
            hdcp = total - scratch
            inferred.append("hdcp")
    return {"games": games, "scratch": scratch, "hdcp": hdcp, "total": total}, inferred
