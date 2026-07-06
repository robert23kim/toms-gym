"""Short-link service: create a code for a target URL, redirect on GET /s/<code>.

Powers the Share button on lift / bowling / golf result pages. Public
endpoints — no auth.

OG unfurls (T13): share links point at the BACKEND `/s/<code>` so that link
crawlers (Slack, Facebook, Twitter, …) can be served server-rendered Open
Graph meta tags — an SPA cannot set per-link OG tags. The same `/s/<code>`
route 302-redirects real human browsers to the frontend result page, so the
existing human redirect is unchanged; only crawlers (matched by User-Agent, or
`?meta=1`) get the meta HTML. The frontend SPA `/s/:code` route still works for
any legacy link pasted at the frontend origin.
"""

import logging
import secrets
import string

import sqlalchemy
from flask import Blueprint, jsonify, redirect, request, Response
from toms_gym.db import get_db_connection

short_link_bp = Blueprint('short_link', __name__)
logger = logging.getLogger(__name__)

_CODE_ALPHABET = string.ascii_letters + string.digits  # 62 chars
_CODE_LEN = 6
_MAX_COLLISION_RETRIES = 5

# User-Agent substrings for link-unfurl crawlers. Lowercased match.
_CRAWLER_UA = (
    'facebookexternalhit', 'facebookcatalog', 'slackbot', 'twitterbot',
    'linkedinbot', 'discordbot', 'whatsapp', 'telegrambot', 'googlebot',
    'bingbot', 'embedly', 'redditbot', 'pinterest', 'skypeuripreview',
    'vkshare', 'w3c_validator', 'applebot', 'iframely', 'nuzzel',
    'outbrain', 'flipboard',
)

# Optional OG metadata columns on ShortLink (added lazily below).
_OG_COLUMNS = ('og_title', 'og_description', 'og_stat', 'og_image_source', 'og_image_url')


def _generate_code() -> str:
    return ''.join(secrets.choice(_CODE_ALPHABET) for _ in range(_CODE_LEN))


def _ensure_og_columns(session):
    """Lazily add the OG metadata columns (startup-migration-free)."""
    try:
        for col in _OG_COLUMNS:
            session.execute(sqlalchemy.text(
                f'ALTER TABLE "ShortLink" ADD COLUMN IF NOT EXISTS {col} TEXT'
            ))
        session.commit()
    except Exception as e:  # pragma: no cover - best effort
        session.rollback()
        logger.info("ShortLink OG column ensure note: %s", e)


def _is_crawler(user_agent: str) -> bool:
    ua = (user_agent or '').lower()
    return any(bot in ua for bot in _CRAWLER_UA)


@short_link_bp.route('/short-link', methods=['POST'])
def create_short_link():
    """Create a short link for a target URL.

    Body: {"target_url": "https://...",
           "og_title"?, "og_description"?, "og_stat"?, "og_image_source"?}
    Returns: {"short_code": "<code>"}
    The caller builds the user-facing URL using the backend host so crawlers
    reach the meta route, e.g. `${API_URL}/s/${short_code}`.
    """
    data = request.get_json() or {}
    target_url = (data.get('target_url') or '').strip()
    if not target_url:
        return jsonify({"error": "target_url is required"}), 400
    if not (target_url.startswith('http://') or target_url.startswith('https://')):
        return jsonify({"error": "target_url must be absolute (http:// or https://)"}), 400
    if len(target_url) > 2048:
        return jsonify({"error": "target_url too long"}), 400

    def _clip(v, n=512):
        v = (v or '').strip()
        return v[:n] if v else None

    og_title = _clip(data.get('og_title'), 200)
    og_description = _clip(data.get('og_description'), 300)
    og_stat = _clip(data.get('og_stat'), 40)
    og_image_source = _clip(data.get('og_image_source'), 2048)

    session = get_db_connection()
    try:
        _ensure_og_columns(session)
        for _ in range(_MAX_COLLISION_RETRIES):
            code = _generate_code()
            try:
                session.execute(
                    sqlalchemy.text(
                        'INSERT INTO "ShortLink" '
                        '(short_code, target_url, og_title, og_description, og_stat, og_image_source) '
                        'VALUES (:short_code, :target_url, :og_title, :og_description, :og_stat, :og_image_source)'
                    ),
                    {
                        "short_code": code,
                        "target_url": target_url,
                        "og_title": og_title,
                        "og_description": og_description,
                        "og_stat": og_stat,
                        "og_image_source": og_image_source,
                    },
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


def _fetch_link_row(session, short_code):
    """Fetch the full ShortLink row incl. OG columns; None if missing."""
    _ensure_og_columns(session)
    return session.execute(
        sqlalchemy.text(
            'SELECT target_url, og_title, og_description, og_stat, '
            'og_image_source, og_image_url '
            'FROM "ShortLink" WHERE short_code = :code'
        ),
        {"code": short_code},
    ).fetchone()


def _get_or_build_og_image(session, short_code, row, kind):
    """Return a cached OG image URL, generating + storing it on first use."""
    existing = getattr(row, 'og_image_url', None)
    if existing:
        return existing
    try:
        from toms_gym.integrations.og_card import render_card_png
        from toms_gym.storage import bucket

        png = render_card_png(
            kind,
            getattr(row, 'og_title', None) or "Tom's Gym",
            getattr(row, 'og_stat', None) or "",
            getattr(row, 'og_description', None) or "",
        )
        blob = bucket.blob(f'og-cards/{short_code}.png')
        blob.upload_from_string(png, content_type='image/png')
        image_url = f'https://storage.googleapis.com/{bucket.name}/og-cards/{short_code}.png'
        session.execute(
            sqlalchemy.text(
                'UPDATE "ShortLink" SET og_image_url = :url WHERE short_code = :code'
            ),
            {"url": image_url, "code": short_code},
        )
        session.commit()
        return image_url
    except Exception as e:  # pragma: no cover - best effort; unfurl still works w/o image
        session.rollback()
        logger.warning("OG image generation failed for %s: %s", short_code, e)
        return None


@short_link_bp.route('/s/<string:short_code>', methods=['GET'])
def follow_short_link(short_code):
    """Backend /s/<code> handler.

    Crawlers (matched User-Agent or `?meta=1`) get server-rendered OG meta HTML
    with a generated card image. Human browsers get a 302 redirect to the
    frontend result page — unchanged behavior.
    """
    session = get_db_connection()
    try:
        want_meta = _is_crawler(request.headers.get('User-Agent')) or request.args.get('meta') == '1'
        if not want_meta:
            row = session.execute(
                sqlalchemy.text('SELECT target_url FROM "ShortLink" WHERE short_code = :code'),
                {"code": short_code},
            ).fetchone()
            if not row:
                return jsonify({"error": "Short link not found"}), 404
            return redirect(row.target_url, code=302)

        # Crawler path: serve OG meta HTML.
        from toms_gym.integrations.og_card import infer_kind, render_meta_html

        row = _fetch_link_row(session, short_code)
        if not row:
            return jsonify({"error": "Short link not found"}), 404

        kind = infer_kind(row.target_url)
        image_url = _get_or_build_og_image(session, short_code, row, kind)
        html_doc = render_meta_html(
            getattr(row, 'og_title', None) or "Tom's Gym",
            getattr(row, 'og_description', None) or "See the analysis on Tom's Gym.",
            image_url,
            row.target_url,
            kind,
        )
        return Response(html_doc, mimetype='text/html')
    finally:
        session.close()
