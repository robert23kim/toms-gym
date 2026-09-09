"""Where each name on a bowling sheet saves to. Pure, DB-free."""
import uuid

ME = "me"
NEW = "new"


def guest_email(name):
    """Deterministic profile email for a league-mate, shared with the golf guest path so the
    same name is the same person across features."""
    slug = ''.join(c for c in (name or '').strip().lower() if c.isalnum())
    return f'{slug}@guest.tomsgym.local' if slug else None


def link_key(name):
    return (name or '').strip().lower()


def save_target(save_as):
    """Classify a player's save_as: ('none'|'me'|'new'|'user', user_id). Raises ValueError
    on anything that is neither a keyword nor a UUID."""
    value = (save_as or '').strip()
    if not value:
        return 'none', None
    if value.lower() == ME:
        return ME, None
    if value.lower() == NEW:
        return NEW, None
    try:
        return 'user', str(uuid.UUID(value))
    except ValueError:
        raise ValueError(f"save_as must be 'me', 'new', a profile id or empty, not {save_as!r}")
