"""Short-link service: create a code for a target URL, redirect on GET /s/<code>.

Powers the Share button on lift detail pages. Public endpoints — no auth.
"""

import logging
import secrets
import string

import sqlalchemy
from flask import Blueprint, jsonify, redirect, request
from toms_gym.db import get_db_connection

short_link_bp = Blueprint('short_link', __name__)
logger = logging.getLogger(__name__)

_CODE_ALPHABET = string.ascii_letters + string.digits  # 62 chars
_CODE_LEN = 6
_MAX_COLLISION_RETRIES = 5


def _generate_code() -> str:
    return ''.join(secrets.choice(_CODE_ALPHABET) for _ in range(_CODE_LEN))


@short_link_bp.route('/short-link', methods=['POST'])
def create_short_link():
    """Create a short link for a target URL.

    Body: {"target_url": "https://..."}
    Returns: {"short_code": "<code>"}
    The caller is expected to build the user-facing URL using its own host
    (typically the frontend), e.g. `${window.location.origin}/s/${short_code}`.
    """
    data = request.get_json() or {}
    target_url = (data.get('target_url') or '').strip()
    if not target_url:
        return jsonify({"error": "target_url is required"}), 400
    if not (target_url.startswith('http://') or target_url.startswith('https://')):
        return jsonify({"error": "target_url must be absolute (http:// or https://)"}), 400
    if len(target_url) > 2048:
        return jsonify({"error": "target_url too long"}), 400

    session = get_db_connection()
    try:
        for _ in range(_MAX_COLLISION_RETRIES):
            code = _generate_code()
            try:
                session.execute(
                    sqlalchemy.text(
                        'INSERT INTO "ShortLink" (short_code, target_url) '
                        'VALUES (:short_code, :target_url)'
                    ),
                    {"short_code": code, "target_url": target_url},
                )
                session.commit()
                return jsonify({"short_code": code}), 201
            except sqlalchemy.exc.IntegrityError:
                session.rollback()
                continue

        logger.error("Failed to generate unique short_code after %s attempts", _MAX_COLLISION_RETRIES)
        return jsonify({"error": "Could not generate short link, please retry"}), 503
    finally:
        session.close()


@short_link_bp.route('/short-link/<string:short_code>', methods=['GET'])
def resolve_short_link(short_code):
    """Resolve a short code to its target URL.

    Returns: {"target_url": "https://..."} or 404.
    Used by the frontend /s/:code redirect page.
    """
    session = get_db_connection()
    try:
        row = session.execute(
            sqlalchemy.text('SELECT target_url FROM "ShortLink" WHERE short_code = :code'),
            {"code": short_code},
        ).fetchone()
        if not row:
            return jsonify({"error": "Short link not found"}), 404
        return jsonify({"target_url": row.target_url})
    finally:
        session.close()


@short_link_bp.route('/s/<string:short_code>', methods=['GET'])
def follow_short_link(short_code):
    """Backend fallback: 302 redirect for direct backend-host paste of /s/<code>."""
    session = get_db_connection()
    try:
        row = session.execute(
            sqlalchemy.text('SELECT target_url FROM "ShortLink" WHERE short_code = :code'),
            {"code": short_code},
        ).fetchone()
        if not row:
            return jsonify({"error": "Short link not found"}), 404
        return redirect(row.target_url, code=302)
    finally:
        session.close()
