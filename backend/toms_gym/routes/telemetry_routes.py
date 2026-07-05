import json
import logging

from flask import Blueprint, request

logger = logging.getLogger(__name__)

telemetry_bp = Blueprint('telemetry', __name__)


@telemetry_bp.route('/log-error', methods=['POST'])
def log_frontend_error():
    """Log frontend errors to Cloud Run logs for visibility."""
    # Cap request size at 2KB to prevent abuse
    if request.content_length and request.content_length > 2048:
        return '', 204

    # sendBeacon payloads arrive as text/plain (the only CORS-safelisted way to
    # beacon cross-origin without a preflight) — fall back to parsing raw bytes.
    data = request.get_json(silent=True)
    if data is None:
        try:
            data = json.loads(request.get_data(as_text=True))
        except (ValueError, UnicodeDecodeError):
            data = {}
    if not isinstance(data, dict):
        data = {}

    page = data.get('page', 'unknown')
    action = data.get('action', 'unknown')
    error = data.get('error', 'unknown')
    details = data.get('details', {})
    user_agent = data.get('userAgent', '')
    url = data.get('url', '')

    logger.warning(
        "FRONTEND_ERROR page=%s action=%s error=%s url=%s details=%s userAgent=%s",
        page, action, error, url, details, user_agent[:200]
    )

    return '', 204
