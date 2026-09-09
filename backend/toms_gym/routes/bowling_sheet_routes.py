"""Bowling score-sheet routes: photo → parsed games → insights.

A sheet is one photo (an end-of-night RESULTS screen or a single-game lane
screen). Games are stored unclaimed until the uploader picks their row on the
review page, so league-mates never end up as users.
"""

import io
import json
import logging
import uuid
from datetime import date, datetime

import sqlalchemy
from PIL import Image, ImageOps
from flask import Blueprint, jsonify, request

from toms_gym.db import get_db_connection
from toms_gym.security import rate_limit
from toms_gym.services.bowling_insights import compute_insights, merge_duplicate_games
from toms_gym.services.bowling_links import ME, NEW, guest_email, link_key, save_target
from toms_gym.services.bowling_score import score_frames
from toms_gym.storage import ALLOWED_IMAGE_EXTENSIONS, bucket

logger = logging.getLogger(__name__)

bowling_sheet_bp = Blueprint('bowling_sheet', __name__, url_prefix='/bowling')

SHEET_TYPES = ('night', 'game')
MAX_IMAGE_BYTES = 20 * 1024 * 1024
GAMES_LIMIT_CAP = 50
RECENT_GAMES = 10
ROTATIONS = (0, 180, 90, 270)


def _allowed_image(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_IMAGE_EXTENSIONS


def _auto_orient_image(file_bytes, content_type='image/jpeg'):
    """Apply EXIF orientation. Lane screens are photographed in any rotation;
    the parse pass tries the four 90° turns itself."""
    try:
        img = ImageOps.exif_transpose(Image.open(io.BytesIO(file_bytes)))
        out = io.BytesIO()
        fmt = 'PNG' if content_type and 'png' in content_type.lower() else 'JPEG'
        if fmt == 'JPEG' and img.mode not in ('RGB', 'L'):
            img = img.convert('RGB')
        img.save(out, format=fmt, quality=95)
        return out.getvalue()
    except Exception as e:
        logger.warning(f"Auto-orient failed, using original image: {e}")
        return file_bytes


def _rotate_image(image_bytes, degrees):
    if degrees % 360 == 0:
        return image_bytes
    img = Image.open(io.BytesIO(image_bytes))
    out = io.BytesIO()
    rotated = img.rotate(-degrees, expand=True)
    if rotated.mode not in ('RGB', 'L'):
        rotated = rotated.convert('RGB')
    rotated.save(out, format='JPEG', quality=95)
    return out.getvalue()


def _store_sheet_image(image_bytes, content_type, path):
    blob = bucket.blob(path)
    blob.upload_from_string(image_bytes, content_type=content_type)
    return f'https://storage.googleapis.com/{bucket.name}/{path}'


def _ocr_and_parse(image_bytes, sheet_type, played_on):
    """OCR + parse the sheet, trying each 90° rotation.

    Returns (parsed, game_rows, rotation). Raises when no rotation yields a
    parseable sheet; the caller stores the photo as ``failed`` either way.
    Imported lazily so this module loads without the parser present.
    """
    from toms_gym.services.bowling_sheet_parser import parse_sheet, shape_games
    from toms_gym.services.vision_ocr import extract_words_and_symbols, run_document_ocr

    best = None
    last_error = None
    for degrees in ROTATIONS:
        try:
            candidate_bytes = _rotate_image(image_bytes, degrees)
            words, symbols, page_w, page_h = extract_words_and_symbols(
                run_document_ocr(candidate_bytes)
            )
            parsed = parse_sheet(sheet_type, words, symbols, page_w, page_h)
            rows = shape_games(parsed, sheet_type, played_on)
            clean = sum(1 for p in parsed.get('players', []) if not p.get('flagged'))
            if best is None or clean > best[0]:
                best = (clean, parsed, rows, degrees)
            if clean and clean == len(parsed.get('players', [])):
                break
        except Exception as e:
            last_error = e
            logger.info(f"Sheet parse at {degrees}° failed: {e}")
    if best is None:
        raise last_error or RuntimeError('no player rows found')
    _, parsed, rows, degrees = best
    return parsed, rows, degrees


def _inferred_frames_by_player(raw_parse):
    """Frame numbers the parser filled from the running score alone, per player name."""
    if isinstance(raw_parse, str):
        try:
            raw_parse = json.loads(raw_parse)
        except ValueError:
            return {}
    if not isinstance(raw_parse, dict):
        return {}
    return {p.get("name"): list(p.get("inferred_frames") or [])
            for p in raw_parse.get("players") or [] if isinstance(p, dict)}


def _sheet_payload(session, sheet_id):
    sheet = session.execute(sqlalchemy.text("""
        SELECT id, user_id, sheet_type, played_on, image_url, team_name,
               processing_status, error_message, raw_parse
        FROM "BowlingScoreSheet" WHERE id = :id
    """), {"id": sheet_id}).fetchone()
    if not sheet:
        return None
    inferred_by_name = _inferred_frames_by_player(sheet[8]) if sheet[6] != 'confirmed' else {}
    remembered = _remembered_links(session, sheet[1]) if sheet[6] != 'confirmed' else {}

    rows = session.execute(sqlalchemy.text("""
        SELECT g.id, g.player_name, g.game_number, g.total_score, g.hdcp, g.frames,
               g.computed_total, g.flagged, g.flag_reason, g.confidence, g.user_id, u.name
        FROM "BowlingGame" g
        LEFT JOIN "User" u ON u.id = g.user_id
        WHERE g.sheet_id = :id
        ORDER BY g.player_name, g.game_number
    """), {"id": sheet_id}).fetchall()

    players = []
    by_name = {}
    for r in rows:
        game = {
            "id": str(r[0]),
            "game_number": r[2],
            "total_score": r[3],
            "hdcp": r[4],
            "frames": r[5],
            "computed_total": r[6],
            "flagged": bool(r[7]),
            "flag_reason": r[8],
            "confidence": float(r[9]) if r[9] is not None else None,
            "inferred_frames": inferred_by_name.get(r[1], []) if r[5] else [],
        }
        if r[1] not in by_name:
            linked = {"id": str(r[10]), "name": r[11]} if r[10] else remembered.get(link_key(r[1]))
            by_name[r[1]] = {"name": r[1], "games": [], "linked_user": linked}
            players.append(by_name[r[1]])
        by_name[r[1]]["games"].append(game)

    return {
        "sheet_id": str(sheet[0]),
        "sheet_type": sheet[2],
        "played_on": sheet[3].isoformat() if sheet[3] else None,
        "image_url": sheet[4],
        "team_name": sheet[5],
        "processing_status": sheet[6],
        "error_message": sheet[7],
        "players": players,
        "flagged_count": sum(1 for r in rows if r[7]),
    }


def _remembered_links(session, owner_id):
    """{lowercased sheet name: {id, name}} the owner has saved that name to before."""
    if not owner_id:
        return {}
    rows = session.execute(sqlalchemy.text("""
        SELECT l.player_name, l.user_id, u.name
        FROM "BowlingPlayerLink" l JOIN "User" u ON u.id = l.user_id
        WHERE l.owner_user_id = :owner
    """), {"owner": owner_id}).fetchall()
    return {r[0]: {"id": str(r[1]), "name": r[2]} for r in rows}


def _remember_links(session, owner_id, user_by_name):
    for name, uid in user_by_name.items():
        session.execute(sqlalchemy.text("""
            INSERT INTO "BowlingPlayerLink" (owner_user_id, player_name, user_id)
            VALUES (:owner, :name, :uid)
            ON CONFLICT (owner_user_id, player_name)
            DO UPDATE SET user_id = EXCLUDED.user_id, updated_at = now()
        """), {"owner": owner_id, "name": name, "uid": uid})


def _find_or_create_profile(session, name):
    """Passwordless profile for a league-mate; same name → same profile (also across golf)."""
    email = guest_email(name)
    if not email:
        return None
    row = session.execute(
        sqlalchemy.text('SELECT id FROM "User" WHERE LOWER(email) = :email'), {"email": email}
    ).fetchone()
    if row:
        return str(row[0])
    new_id = str(uuid.uuid4())
    session.execute(sqlalchemy.text("""
        INSERT INTO "User" (id, email, name, username, status, role, created_at)
        VALUES (:id, :email, :name, :username, 'active', 'user', NOW())
    """), {"id": new_id, "email": email, "name": name.strip().title(), "username": email})
    logger.info(f"Auto-created bowling profile {new_id} for {name!r}")
    return new_id


def _resolve_save_targets(session, owner_id, players, claim_player=None):
    """{lowercased sheet name: user id} for every row that saves somewhere. Raises ValueError
    with a client-facing message when a save_as is malformed or names an unknown profile."""
    claim = link_key(claim_player)
    out = {}
    for player in players:
        name = (player.get('name') or '').strip()
        key = link_key(name)
        kind, uid = save_target(player.get('save_as'))
        if kind == 'none' and claim and key == claim:
            kind = ME
        if kind == 'none':
            continue
        if kind == ME:
            if not owner_id:
                raise ValueError("this sheet has no uploader to save 'me' to")
            uid = owner_id
        elif kind == NEW:
            uid = _find_or_create_profile(session, name)
            if not uid:
                raise ValueError(f"cannot create a profile for {name!r}")
        else:
            exists = session.execute(
                sqlalchemy.text('SELECT 1 FROM "User" WHERE id = :id'), {"id": uid}
            ).fetchone()
            if not exists:
                raise ValueError(f"no profile {uid} to save {name!r} to")
        out[key] = uid
    return out


def _insert_games(session, sheet_id, played_on, rows, user_by_name=None):
    user_by_name = user_by_name or {}
    for row in rows:
        name = (row.get('player_name') or '').strip()
        if not name:
            continue
        frames = row.get('frames')
        session.execute(sqlalchemy.text("""
            INSERT INTO "BowlingGame" (
                id, sheet_id, user_id, player_name, game_number, total_score, hdcp,
                frames, computed_total, flagged, flag_reason, confidence, played_on)
            VALUES (:id, :sheet_id, :user_id, :player_name, :game_number, :total_score,
                    :hdcp, CAST(:frames AS JSONB), :computed_total, :flagged,
                    :flag_reason, :confidence, :played_on)
            ON CONFLICT (sheet_id, player_name, game_number) DO NOTHING
        """), {
            "id": str(uuid.uuid4()),
            "sheet_id": sheet_id,
            "user_id": user_by_name.get(link_key(name)),
            "player_name": name,
            "game_number": int(row.get('game_number') or 0),
            "total_score": row.get('total_score'),
            "hdcp": row.get('hdcp'),
            "frames": json.dumps(frames) if frames else None,
            "computed_total": row.get('computed_total'),
            "flagged": bool(row.get('flagged')),
            "flag_reason": row.get('flag_reason'),
            "confidence": row.get('confidence'),
            "played_on": played_on,
        })


def _resolve_user(session, user_id, email):
    if user_id:
        return user_id
    if not email:
        return None
    row = session.execute(
        sqlalchemy.text('SELECT id FROM "User" WHERE LOWER(email) = :email'),
        {"email": email.lower()},
    ).fetchone()
    if row:
        return str(row[0])
    new_id = str(uuid.uuid4())
    name = email.split('@')[0].replace('.', ' ').replace('_', ' ').title()
    # auth_method stays NULL: the enum only covers google/password and an
    # email-only uploader is neither (same as the golf guest path).
    session.execute(sqlalchemy.text("""
        INSERT INTO "User" (id, email, name, username, status, role, created_at)
        VALUES (:id, :email, :name, :username, 'active', 'user', NOW())
    """), {"id": new_id, "email": email.lower(), "name": name, "username": email.lower()})
    session.commit()
    logger.info(f"Auto-created user {new_id} for {email}")
    return new_id


def _valid_uuid(value):
    try:
        uuid.UUID(str(value))
        return True
    except (ValueError, AttributeError, TypeError):
        return False


@bowling_sheet_bp.route('/scoresheet/upload', methods=['POST'])
@rate_limit('20/hour')
def upload_scoresheet():
    if 'image' not in request.files:
        return jsonify({'error': 'No image file provided'}), 400
    file = request.files['image']
    if not file.filename:
        return jsonify({'error': 'No selected file'}), 400
    if not _allowed_image(file.filename):
        return jsonify({'error': 'File type not allowed'}), 400

    file.seek(0, 2)
    file_size = file.tell()
    file.seek(0)
    if file_size > MAX_IMAGE_BYTES:
        return jsonify({'error': 'File too large. Maximum 20MB'}), 413

    sheet_type = (request.form.get('sheet_type') or 'night').strip().lower()
    if sheet_type not in SHEET_TYPES:
        return jsonify({'error': "sheet_type must be 'night' or 'game'"}), 400

    played_on_raw = request.form.get('played_on')
    if played_on_raw:
        try:
            played_on = datetime.strptime(played_on_raw.strip(), '%Y-%m-%d').date()
        except ValueError:
            return jsonify({'error': 'played_on must be YYYY-MM-DD'}), 400
    else:
        played_on = date.today()

    session = get_db_connection()
    try:
        user_id = _resolve_user(session, request.form.get('user_id'), request.form.get('email'))
        if not user_id:
            return jsonify({'error': 'user_id or email is required'}), 400

        sheet_id = str(uuid.uuid4())
        ext = file.filename.rsplit('.', 1)[1].lower()
        content_type = file.content_type or 'image/jpeg'
        image_bytes = _auto_orient_image(file.read(), content_type)
        image_url = _store_sheet_image(
            image_bytes, content_type, f'bowling/sheets/{user_id}/{sheet_id}.{ext}'
        )

        parsed, rows, error_message = None, [], None
        try:
            parsed, rows, _rotation = _ocr_and_parse(image_bytes, sheet_type, played_on.isoformat())
        except Exception as e:
            error_message = str(e)
            logger.warning(f"Score sheet {sheet_id} parse failed: {e}")

        session.execute(sqlalchemy.text("""
            INSERT INTO "BowlingScoreSheet" (
                id, user_id, sheet_type, played_on, image_url, parser, raw_parse,
                processing_status, error_message, team_name)
            VALUES (:id, :user_id, :sheet_type, :played_on, :image_url, :parser,
                    CAST(:raw_parse AS JSONB), :status, :error_message, :team_name)
        """), {
            "id": sheet_id,
            "user_id": user_id,
            "sheet_type": sheet_type,
            "played_on": played_on,
            "image_url": image_url,
            "parser": 'vision' if parsed else None,
            "raw_parse": json.dumps(parsed) if parsed else None,
            "status": 'failed' if error_message else 'parsed',
            "error_message": error_message,
            "team_name": (parsed or {}).get('team_name'),
        })
        _insert_games(session, sheet_id, played_on, rows)
        session.commit()
        return jsonify(_sheet_payload(session, sheet_id)), 200
    except Exception as e:
        session.rollback()
        logger.error(f"Score sheet upload failed: {e}", exc_info=True)
        return jsonify({'error': 'Failed to store score sheet'}), 500
    finally:
        session.close()


@bowling_sheet_bp.route('/scoresheet/<sheet_id>', methods=['GET'])
def get_scoresheet(sheet_id):
    if not _valid_uuid(sheet_id):
        return jsonify({'error': 'Sheet not found'}), 404
    session = get_db_connection()
    try:
        payload = _sheet_payload(session, sheet_id)
        if not payload:
            return jsonify({'error': 'Sheet not found'}), 404
        return jsonify(payload), 200
    finally:
        session.close()


@bowling_sheet_bp.route('/scoresheet/<sheet_id>/confirm', methods=['PUT'])
def confirm_scoresheet(sheet_id):
    if not _valid_uuid(sheet_id):
        return jsonify({'error': 'Sheet not found'}), 404
    body = request.get_json(silent=True) or {}
    players = body.get('players')
    if not isinstance(players, list):
        return jsonify({'error': 'players must be a list'}), 400

    session = get_db_connection()
    try:
        sheet = session.execute(sqlalchemy.text("""
            SELECT user_id, played_on FROM "BowlingScoreSheet" WHERE id = :id
        """), {"id": sheet_id}).fetchone()
        if not sheet:
            return jsonify({'error': 'Sheet not found'}), 404
        user_id, played_on = str(sheet[0]) if sheet[0] else None, sheet[1]

        rows = []
        for player in players:
            name = (player.get('name') or '').strip()
            if not name:
                return jsonify({'error': 'every player needs a name'}), 400
            for game in player.get('games') or []:
                frames = game.get('frames')
                computed_total = None
                if frames:
                    result = score_frames(frames)
                    if not result['valid']:
                        return jsonify({
                            'error': f"invalid frames for {name} game {game.get('game_number')}",
                            'errors': result['errors'],
                        }), 400
                    computed_total = result['total']
                rows.append({
                    "player_name": name,
                    "game_number": game.get('game_number'),
                    "total_score": game.get('total_score') if game.get('total_score') is not None
                    else computed_total,
                    "hdcp": game.get('hdcp'),
                    "frames": frames,
                    "computed_total": computed_total,
                    "flagged": False,
                    "flag_reason": None,
                    "confidence": None,
                })

        try:
            user_by_name = _resolve_save_targets(session, user_id, players, body.get('claim_player'))
        except ValueError as e:
            session.rollback()
            return jsonify({'error': str(e)}), 400
        session.execute(
            sqlalchemy.text('DELETE FROM "BowlingGame" WHERE sheet_id = :id'), {"id": sheet_id}
        )
        _insert_games(session, sheet_id, played_on, rows, user_by_name)
        if user_id:
            _remember_links(session, user_id, user_by_name)
        session.execute(sqlalchemy.text("""
            UPDATE "BowlingScoreSheet"
            SET processing_status = 'confirmed', updated_at = now()
            WHERE id = :id
        """), {"id": sheet_id})
        session.commit()
        return jsonify(_sheet_payload(session, sheet_id)), 200
    except Exception as e:
        session.rollback()
        logger.error(f"Score sheet confirm failed: {e}", exc_info=True)
        return jsonify({'error': 'Failed to confirm score sheet'}), 500
    finally:
        session.close()


@bowling_sheet_bp.route('/scoresheet/<sheet_id>', methods=['DELETE'])
def delete_scoresheet(sheet_id):
    if not _valid_uuid(sheet_id):
        return jsonify({'error': 'Sheet not found'}), 404
    session = get_db_connection()
    try:
        deleted = session.execute(sqlalchemy.text("""
            DELETE FROM "BowlingScoreSheet" WHERE id = :id RETURNING id
        """), {"id": sheet_id}).fetchone()
        session.commit()
        if not deleted:
            return jsonify({'error': 'Sheet not found'}), 404
        return '', 204
    except Exception as e:
        session.rollback()
        logger.error(f"Score sheet delete failed: {e}", exc_info=True)
        return jsonify({'error': 'Failed to delete score sheet'}), 500
    finally:
        session.close()


def _user_games(session, user_id, limit, offset, with_frames=False):
    rows = session.execute(sqlalchemy.text(f"""
        SELECT g.id, g.sheet_id, g.played_on, g.game_number, g.total_score, g.hdcp,
               g.frames IS NOT NULL AS has_frames, g.flagged, s.sheet_type
               {', g.frames' if with_frames else ''}
        FROM "BowlingGame" g
        JOIN "BowlingScoreSheet" s ON s.id = g.sheet_id
        WHERE g.user_id = :user_id AND s.processing_status = 'confirmed'
        ORDER BY g.played_on DESC, g.game_number DESC
        LIMIT :limit OFFSET :offset
    """), {"user_id": user_id, "limit": limit, "offset": offset}).fetchall()
    games = [{
        "id": str(r[0]),
        "sheet_id": str(r[1]),
        "played_on": r[2].isoformat() if r[2] else None,
        "game_number": r[3],
        "total_score": r[4],
        "hdcp": r[5],
        "has_frames": bool(r[6]),
        "flagged": bool(r[7]),
        "sheet_type": r[8],
    } for r in rows]
    if with_frames:
        for game, r in zip(games, rows):
            game["frames"] = r[9]
    return merge_duplicate_games(games)


@bowling_sheet_bp.route('/games', methods=['GET'])
def list_games():
    user_id = request.args.get('user_id')
    if not user_id or not _valid_uuid(user_id):
        return jsonify({'error': 'user_id is required'}), 400
    try:
        limit = min(max(int(request.args.get('limit', 20)), 1), GAMES_LIMIT_CAP)
        offset = max(int(request.args.get('offset', 0)), 0)
    except (TypeError, ValueError):
        return jsonify({'error': 'limit and offset must be integers'}), 400

    session = get_db_connection()
    try:
        total = session.execute(sqlalchemy.text("""
            SELECT count(*) FROM "BowlingGame" g
            JOIN "BowlingScoreSheet" s ON s.id = g.sheet_id
            WHERE g.user_id = :user_id AND s.processing_status = 'confirmed'
        """), {"user_id": user_id}).scalar() or 0
        return jsonify({
            "games": _user_games(session, user_id, limit, offset),
            "total": total,
            "limit": limit,
            "offset": offset,
        }), 200
    finally:
        session.close()


@bowling_sheet_bp.route('/insights/<user_id>', methods=['GET'])
def get_insights(user_id):
    if not _valid_uuid(user_id):
        return jsonify({'error': 'invalid user_id'}), 400
    session = get_db_connection()
    try:
        games = _user_games(session, user_id, 200, 0, with_frames=True)
        insights = compute_insights([{
            "total_score": g["total_score"],
            "game_number": g["game_number"],
            "played_on": g["played_on"],
            "hdcp": g["hdcp"],
            "frames": g.get("frames"),
        } for g in games])
        insights["recent"] = [{k: v for k, v in g.items() if k != "frames"}
                              for g in games[:RECENT_GAMES]]
        return jsonify(insights), 200
    finally:
        session.close()
