from flask import Blueprint, request
import logging

logger = logging.getLogger(__name__)

telemetry_bp = Blueprint('telemetry', __name__)


@telemetry_bp.route('/log-error', methods=['POST'])
def log_frontend_error():
    """Log frontend errors to Cloud Run logs for visibility."""
    # Cap request size at 2KB to prevent abuse
    if request.content_length and request.content_length > 2048:
        return '', 204

    data = request.get_json(silent=True) or {}

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
