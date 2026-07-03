"""Ticket service: file bug reports / feature requests and triage them.

Powers the /feedback page. Public endpoints — no auth (matches the app's
optional-auth model; admin auth is a known gap from the 2026-07 review).
"""

import logging
import uuid

import sqlalchemy
from flask import Blueprint, jsonify, request
from toms_gym.db import get_db_connection

ticket_bp = Blueprint('ticket', __name__)
logger = logging.getLogger(__name__)

_VALID_TYPES = ('bug', 'feature')
_VALID_STATUSES = ('open', 'in_progress', 'closed')
_MAX_TITLE = 200
_MAX_DESCRIPTION = 5000
_MAX_PAGE_URL = 2048
_MAX_EMAIL = 320
_DEFAULT_LIMIT = 50
_MAX_LIMIT = 100


def _serialize_ticket(row) -> dict:
    """Map a Ticket row to a JSON-serializable dict."""
    return {
        "id": str(row.id),
        "type": row.type,
        "title": row.title,
        "description": row.description,
        "page_url": row.page_url,
        "contact_email": row.contact_email,
        "user_id": str(row.user_id) if row.user_id else None,
        "status": row.status,
        "created_at": row.created_at.isoformat() if row.created_at else None,
        "updated_at": row.updated_at.isoformat() if row.updated_at else None,
    }


def _valid_uuid(value):
    """Return a normalized UUID string if value is a valid UUID, else None."""
    try:
        return str(uuid.UUID(str(value)))
    except (ValueError, AttributeError, TypeError):
        return None


@ticket_bp.route('/tickets', methods=['POST'])
def create_ticket():
    """Create a ticket (bug report or feature request).

    Body: {type, title, description, page_url?, email?, user_id?}
    Returns: {"ticket_id": "<uuid>"} on 201.
    """
    data = request.get_json() or {}

    ticket_type = (data.get('type') or '').strip()
    if ticket_type not in _VALID_TYPES:
        return jsonify({"error": "type must be one of: bug, feature"}), 400

    title = (data.get('title') or '').strip()
    if not title:
        return jsonify({"error": "title is required"}), 400
    if len(title) > _MAX_TITLE:
        return jsonify({"error": f"title too long (max {_MAX_TITLE} chars)"}), 400

    description = (data.get('description') or '').strip()
    if not description:
        return jsonify({"error": "description is required"}), 400
    if len(description) > _MAX_DESCRIPTION:
        return jsonify({"error": f"description too long (max {_MAX_DESCRIPTION} chars)"}), 400

    page_url = (data.get('page_url') or '').strip() or None
    if page_url and len(page_url) > _MAX_PAGE_URL:
        return jsonify({"error": f"page_url too long (max {_MAX_PAGE_URL} chars)"}), 400

    email = (data.get('email') or '').strip() or None
    if email:
        if len(email) > _MAX_EMAIL:
            return jsonify({"error": f"email too long (max {_MAX_EMAIL} chars)"}), 400
        if '@' not in email:
            return jsonify({"error": "email must contain '@'"}), 400

    # Invalid user_id is ignored rather than rejected — keep the endpoint
    # permissive for anonymous callers who may pass junk from localStorage.
    user_id = _valid_uuid(data.get('user_id')) if data.get('user_id') else None

    params = {
        "type": ticket_type,
        "title": title,
        "description": description,
        "page_url": page_url,
        "contact_email": email,
        "user_id": user_id,
    }

    session = get_db_connection()
    try:
        insert_sql = sqlalchemy.text(
            'INSERT INTO "Ticket" (type, title, description, page_url, contact_email, user_id) '
            'VALUES (:type, :title, :description, :page_url, :contact_email, :user_id) '
            'RETURNING id'
        )
        try:
            row = session.execute(insert_sql, params).fetchone()
            session.commit()
        except sqlalchemy.exc.IntegrityError:
            # A valid-looking user_id that doesn't exist in "User" trips the FK.
            # Retry once without it so the ticket is still recorded.
            session.rollback()
            params["user_id"] = None
            row = session.execute(insert_sql, params).fetchone()
            session.commit()

        return jsonify({"ticket_id": str(row.id)}), 201
    except Exception as e:
        session.rollback()
        logger.error("Failed to create ticket: %s", e)
        return jsonify({"error": "Could not create ticket"}), 500
    finally:
        session.close()


@ticket_bp.route('/tickets', methods=['GET'])
def list_tickets():
    """List tickets, newest first. Optional ?status=, ?type=, ?limit= filters."""
    status = request.args.get('status')
    if status is not None and status not in _VALID_STATUSES:
        return jsonify({"error": "status must be one of: open, in_progress, closed"}), 400

    ticket_type = request.args.get('type')
    if ticket_type is not None and ticket_type not in _VALID_TYPES:
        return jsonify({"error": "type must be one of: bug, feature"}), 400

    limit = _DEFAULT_LIMIT
    limit_arg = request.args.get('limit')
    if limit_arg is not None:
        try:
            limit = int(limit_arg)
        except (ValueError, TypeError):
            return jsonify({"error": "limit must be an integer"}), 400
        if limit < 1:
            return jsonify({"error": "limit must be positive"}), 400
        limit = min(limit, _MAX_LIMIT)

    clauses = []
    params = {"limit": limit}
    if status is not None:
        clauses.append("status = :status")
        params["status"] = status
    if ticket_type is not None:
        clauses.append("type = :type")
        params["type"] = ticket_type
    where = f"WHERE {' AND '.join(clauses)}" if clauses else ""

    session = get_db_connection()
    try:
        rows = session.execute(
            sqlalchemy.text(
                'SELECT id, type, title, description, page_url, contact_email, '
                'user_id, status, created_at, updated_at '
                f'FROM "Ticket" {where} '
                'ORDER BY created_at DESC LIMIT :limit'
            ),
            params,
        ).fetchall()
        return jsonify({"tickets": [_serialize_ticket(r) for r in rows]})
    finally:
        session.close()


@ticket_bp.route('/tickets/<string:ticket_id>', methods=['GET'])
def get_ticket(ticket_id):
    """Fetch a single ticket. 404 if missing or the id is not a valid UUID."""
    normalized = _valid_uuid(ticket_id)
    if not normalized:
        return jsonify({"error": "Ticket not found"}), 404

    session = get_db_connection()
    try:
        row = session.execute(
            sqlalchemy.text(
                'SELECT id, type, title, description, page_url, contact_email, '
                'user_id, status, created_at, updated_at '
                'FROM "Ticket" WHERE id = :id'
            ),
            {"id": normalized},
        ).fetchone()
        if not row:
            return jsonify({"error": "Ticket not found"}), 404
        return jsonify(_serialize_ticket(row))
    finally:
        session.close()


@ticket_bp.route('/tickets/<string:ticket_id>/status', methods=['PUT'])
def update_ticket_status(ticket_id):
    """Update a ticket's status. Body: {"status": ...}. 404 if missing."""
    normalized = _valid_uuid(ticket_id)
    if not normalized:
        return jsonify({"error": "Ticket not found"}), 404

    data = request.get_json() or {}
    status = (data.get('status') or '').strip()
    if status not in _VALID_STATUSES:
        return jsonify({"error": "status must be one of: open, in_progress, closed"}), 400

    session = get_db_connection()
    try:
        row = session.execute(
            sqlalchemy.text(
                'UPDATE "Ticket" SET status = :status, updated_at = now() '
                'WHERE id = :id '
                'RETURNING id, type, title, description, page_url, contact_email, '
                'user_id, status, created_at, updated_at'
            ),
            {"status": status, "id": normalized},
        ).fetchone()
        if not row:
            session.rollback()
            return jsonify({"error": "Ticket not found"}), 404
        session.commit()
        return jsonify(_serialize_ticket(row))
    except Exception as e:
        session.rollback()
        logger.error("Failed to update ticket status: %s", e)
        return jsonify({"error": "Could not update ticket"}), 500
    finally:
        session.close()
