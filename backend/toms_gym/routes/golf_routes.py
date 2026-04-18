"""
Golf Routes for Tom's Gym

Handles golf scorecard uploads, OCR processing, score confirmation,
handicap calculation, and leaderboard.
"""

import io
import json
import math
import os
import uuid
import logging
from datetime import datetime
from flask import Blueprint, request, jsonify
from werkzeug.utils import secure_filename
import sqlalchemy
from PIL import Image, ImageOps

from toms_gym.db import get_db_connection
from toms_gym.storage import bucket, ALLOWED_IMAGE_EXTENSIONS
from toms_gym.security import rate_limit

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

golf_bp = Blueprint('golf', __name__, url_prefix='/golf')


def _allowed_image(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_IMAGE_EXTENSIONS


def _auto_orient_image(file_bytes, content_type='image/jpeg'):
    """Apply EXIF orientation so the image is visually upright.

    Scorecards can be photographed in either landscape or portrait; we trust
    the EXIF orientation tag and do not force one or the other. If OCR later
    fails to find player rows the upload path will retry with a 90° rotation.
    """
    try:
        img = Image.open(io.BytesIO(file_bytes))
        img = ImageOps.exif_transpose(img)

        output = io.BytesIO()
        fmt = 'JPEG'
        if content_type and 'png' in content_type.lower():
            fmt = 'PNG'
        img.save(output, format=fmt, quality=95)
        output.seek(0)
        return output.getvalue()
    except Exception as e:
        logger.warning(f"Auto-orient failed, using original image: {e}")
        return file_bytes


# WHS table: rounds_available -> (differentials_to_use, adjustment)
WHS_TABLE = {
    3: (1, -2.0), 4: (1, -1.0), 5: (1, 0),
    6: (2, -1.0), 7: (2, 0), 8: (2, 0),
    9: (3, 0), 10: (3, 0), 11: (4, 0), 12: (4, 0),
    13: (5, 0), 14: (5, 0), 15: (6, 0), 16: (6, 0),
    17: (7, 0), 18: (7, 0), 19: (8, 0), 20: (8, 0)
}


def _run_ocr(gcs_uri):
    """Run Vision API document_text_detection on a GCS image."""
    from google.cloud import vision

    client = vision.ImageAnnotatorClient()
    image = vision.Image(source=vision.ImageSource(image_uri=gcs_uri))
    response = client.document_text_detection(image=image)

    if response.error.message:
        raise Exception(f"Vision API error: {response.error.message}")

    return response.full_text_annotation


# Labels that appear on scorecards and must never be confused with player names.
SCORECARD_LABELS = {
    "OUT", "IN", "TOTAL", "TOT", "HCP", "NET", "GROSS", "HDCP", "PAR",
    "HOLE", "SCORE", "PLAYER", "HANDICAP", "SLOPE", "RATING", "COURSE",
    "DATE", "BLACK", "GOLD", "GREEN", "WHITE", "BLUE", "RED", "YELLOW",
    "SILVER", "CHAMPION", "CHAMPIONSHIP",
}


def _extract_symbols(ocr_response):
    """Pull symbol-level OCR into plain dicts with x/y centroids.

    Returns: (symbols, page_width, page_height)
    """
    if not ocr_response or not ocr_response.pages:
        return [], 0, 0
    page = ocr_response.pages[0]
    symbols = []
    for block in page.blocks:
        for paragraph in block.paragraphs:
            for word in paragraph.words:
                for sym in word.symbols:
                    v = sym.bounding_box.vertices
                    symbols.append({
                        'text': sym.text,
                        'x': sum(pt.x for pt in v) / 4,
                        'y': sum(pt.y for pt in v) / 4,
                        'conf': sym.confidence,
                    })
    return symbols, (page.width or 0), (page.height or 0)


def _group_rows(symbols, page_height):
    """Group symbols into rows by y-coordinate proximity."""
    if not symbols:
        return []
    threshold = max(15, min(60, page_height * 0.02)) if page_height else 20
    syms = sorted(symbols, key=lambda s: s['y'])
    rows = []
    current = [syms[0]]
    for s in syms[1:]:
        if abs(s['y'] - current[-1]['y']) < threshold:
            current.append(s)
        else:
            rows.append(sorted(current, key=lambda w: w['x']))
            current = [s]
    rows.append(sorted(current, key=lambda w: w['x']))
    return rows


def _cluster_by_x(items, gap_threshold):
    """Cluster items (each with an `x` key) by x-adjacency.

    Items with x-gap < threshold end up in the same cluster — so a multi-digit
    number like "105" (three symbols ~30 px apart) forms one cluster while
    single-digit hole scores (~130 px apart) stay in separate clusters.
    """
    if not items:
        return []
    sorted_items = sorted(items, key=lambda s: s['x'])
    clusters = [[sorted_items[0]]]
    for it in sorted_items[1:]:
        if it['x'] - clusters[-1][-1]['x'] < gap_threshold:
            clusters[-1].append(it)
        else:
            clusters.append([it])
    return clusters


def _deduplicate_symbols(symbols, x_tol=35, y_tol=25):
    """Drop near-duplicate symbols (same text at essentially the same position).

    Vision API frequently emits the same handwritten digit twice with slightly
    different bounding boxes; we keep the higher-confidence copy.
    """
    out = []
    for s in symbols:
        dup_index = None
        for i, t in enumerate(out):
            if (s['text'] == t['text']
                    and abs(s['x'] - t['x']) < x_tol
                    and abs(s['y'] - t['y']) < y_tol):
                dup_index = i
                break
        if dup_index is None:
            out.append(s)
        elif s['conf'] > out[dup_index]['conf']:
            out[dup_index] = s
    return out


def _parse_player_row(row_syms, gap_threshold):
    """Detect a single player's name + 18 hole scores in one OCR row.

    Returns {'name': str, 'front_9': [(v, conf)|None], 'back_9': [(v, conf)|None]}
    or None if the row is not a player row.
    """
    letters = sorted([s for s in row_syms if s['text'].isalpha()], key=lambda x: x['x'])
    digits = sorted([s for s in row_syms if s['text'].isdigit()], key=lambda x: x['x'])

    # A player row must have a name on the left and plenty of digits to the right.
    if not letters or len(digits) < 15:
        return None
    # Label/tee rows (BLACK, GOLD, HOLE + yardages) carry many more letters
    # than a simple handwritten name; skip those outright.
    if len(letters) > 20:
        return None

    # Take the leftmost contiguous letter cluster as the player's name.
    # Handwritten names can have generous spacing, so we allow a wide gap.
    NAME_GAP = 150
    name_letters = [letters[0]]
    for l in letters[1:]:
        if l['x'] - name_letters[-1]['x'] < NAME_GAP:
            name_letters.append(l)
        else:
            break
    name = ''.join(l['text'] for l in name_letters).strip().upper()
    name = ''.join(c for c in name if c.isalpha())

    if not name or len(name) < 2:
        return None
    if name in SCORECARD_LABELS:
        return None
    # Reject names that start with a known scorecard label (e.g., "WHITEML").
    for label in SCORECARD_LABELS:
        if len(label) >= 3 and name.startswith(label):
            return None

    # Keep digits that sit to the right of the name label.
    name_end_x = name_letters[-1]['x'] + 50
    score_digits = [d for d in digits if d['x'] > name_end_x]
    score_digits = _deduplicate_symbols(score_digits)
    score_digits.sort(key=lambda s: s['x'])

    clusters = _cluster_by_x(score_digits, gap_threshold)

    # Multi-digit clusters are subtotals (OUT, IN, TOT) — use them as separators.
    multi_indices = [i for i, c in enumerate(clusters) if len(c) > 1]

    def _single_value(cluster):
        if len(cluster) != 1:
            return None
        try:
            v = int(cluster[0]['text'])
        except ValueError:
            return None
        if 1 <= v <= 15:
            return (v, cluster[0]['conf'])
        return None

    if multi_indices:
        out_idx = multi_indices[0]
        before_out = [_single_value(c) for c in clusters[:out_idx]]
        before_out = [s for s in before_out if s is not None][:9]

        if len(multi_indices) >= 2:
            between = clusters[out_idx + 1:multi_indices[1]]
        else:
            between = clusters[out_idx + 1:]
        between_singles = [_single_value(c) for c in between]
        between_singles = [s for s in between_singles if s is not None][:9]

        front_9 = before_out
        back_9 = between_singles
    else:
        # No subtotals found — fall back to sequential assignment.
        singles = [_single_value(c) for c in clusters]
        singles = [s for s in singles if s is not None]
        front_9 = singles[:9]
        back_9 = singles[9:18]

    # Pad to 9 each with None
    front_9 += [None] * (9 - len(front_9))
    back_9 += [None] * (9 - len(back_9))

    # Require at least 9 valid scores overall, otherwise it's probably noise.
    valid_count = sum(1 for s in front_9 + back_9 if s is not None)
    if valid_count < 9:
        return None

    return {'name': name, 'front_9': front_9, 'back_9': back_9}


def _parse_scorecard_symbols(symbols, page_width, page_height):
    """Parse symbol-level OCR output into per-player 18-hole scorecards.

    Returns {'players': [{'name': str, 'holes': [dict, ...18]}, ...]}.
    """
    rows = _group_rows(symbols, page_height)
    gap_threshold = max(40, min(90, page_width * 0.018)) if page_width else 70

    players = []
    seen_names = set()
    for row in rows:
        parsed = _parse_player_row(row, gap_threshold)
        if not parsed:
            continue
        # De-duplicate if OCR splits the same row into two bands.
        if parsed['name'] in seen_names:
            continue
        seen_names.add(parsed['name'])
        players.append(parsed)

    out_players = []
    for p in players:
        holes = []
        for i, val in enumerate(p['front_9']):
            strokes, conf = (val if val else (None, 0.0))
            holes.append({
                'hole_number': i + 1,
                'par': 4,
                'strokes': strokes,
                'ocr_confidence': round(conf, 2),
            })
        for i, val in enumerate(p['back_9']):
            strokes, conf = (val if val else (None, 0.0))
            holes.append({
                'hole_number': 10 + i,
                'par': 4,
                'strokes': strokes,
                'ocr_confidence': round(conf, 2),
            })
        out_players.append({'name': p['name'], 'holes': holes})

    return {'players': out_players}


def _parse_scorecard_ocr(ocr_response):
    """Back-compat wrapper returning the first detected player's 18 holes.

    New callers should use the multi-player API via `_extract_players_from_ocr`.
    """
    symbols, w, h = _extract_symbols(ocr_response)
    result = _parse_scorecard_symbols(symbols, w, h)
    if result['players']:
        return result['players'][0]['holes']
    return []


def _extract_players_from_ocr(ocr_response):
    """Multi-player API: returns [{'name', 'holes': [...18]}, ...]."""
    symbols, w, h = _extract_symbols(ocr_response)
    result = _parse_scorecard_symbols(symbols, w, h)
    return result['players']


def _recalculate_handicap(session, user_id):
    """Recalculate WHS handicap index for a user.

    Full WHS formula per USGA Rule 5.2:
    1. Fetch last 20 confirmed rounds
    2. Select best N differentials per WHS table
    3. Handicap Index = (average of selected + adjustment) * 0.96
    4. Truncate to 1 decimal, cap at 54.0
    5. Minimum 3 rounds required; fewer -> NULL
    """
    rows = session.execute(sqlalchemy.text("""
        SELECT differential FROM "GolfRound"
        WHERE user_id = :user_id AND processing_status = 'confirmed' AND differential IS NOT NULL
        ORDER BY played_at DESC
        LIMIT 20
    """), {"user_id": user_id}).fetchall()

    differentials = [float(r[0]) for r in rows]
    n = len(differentials)

    if n < 3:
        # Not enough rounds
        session.execute(sqlalchemy.text("""
            INSERT INTO "GolfHandicap" (id, user_id, handicap_index, rounds_used, differentials_used, last_computed_at)
            VALUES (gen_random_uuid(), :user_id, NULL, :n, :diffs, now())
            ON CONFLICT (user_id) DO UPDATE SET
                handicap_index = NULL, rounds_used = :n, differentials_used = :diffs,
                last_computed_at = now(), updated_at = now()
        """), {"user_id": user_id, "n": n, "diffs": json.dumps([])})
        return None

    num_to_use, adjustment = WHS_TABLE.get(n, (8, 0))

    sorted_diffs = sorted(differentials)
    best = sorted_diffs[:num_to_use]

    # WHS formula: (average + adjustment) * 0.96, truncated to 1 decimal
    avg = sum(best) / len(best)
    handicap_index = math.trunc((avg + adjustment) * 0.96 * 10) / 10
    handicap_index = min(handicap_index, 54.0)

    session.execute(sqlalchemy.text("""
        INSERT INTO "GolfHandicap" (id, user_id, handicap_index, rounds_used, differentials_used, last_computed_at)
        VALUES (gen_random_uuid(), :user_id, :handicap, :n, :diffs, now())
        ON CONFLICT (user_id) DO UPDATE SET
            handicap_index = :handicap, rounds_used = :n, differentials_used = :diffs,
            last_computed_at = now(), updated_at = now()
    """), {
        "user_id": user_id,
        "handicap": handicap_index,
        "n": n,
        "diffs": json.dumps(best)
    })

    return handicap_index


@golf_bp.route('/upload', methods=['POST'])
@rate_limit('10/hour')
def upload_scorecard():
    """
    Upload a golf scorecard image for OCR processing.

    Accepts multipart form: image file, course_name, slope_rating, course_rating,
    user_id OR email, played_at (optional).
    Creates GolfRound, runs OCR, returns extracted scores.
    """
    # Validate image file
    if 'image' not in request.files:
        return jsonify({'error': 'No image file provided'}), 400

    file = request.files['image']
    if file.filename == '':
        return jsonify({'error': 'No selected file'}), 400

    if not _allowed_image(file.filename):
        return jsonify({'error': 'File type not allowed'}), 400

    # Check file size (20MB max)
    file.seek(0, 2)
    file_size = file.tell()
    file.seek(0)
    if file_size > 20 * 1024 * 1024:
        return jsonify({'error': 'File too large. Maximum 20MB'}), 400

    course_name = request.form.get('course_name')
    slope_rating = request.form.get('slope_rating')
    course_rating = request.form.get('course_rating')
    user_id = request.form.get('user_id')
    email = request.form.get('email')
    played_at = request.form.get('played_at')

    if not course_name:
        return jsonify({'error': 'course_name is required'}), 400
    if not slope_rating:
        return jsonify({'error': 'slope_rating is required'}), 400
    if not course_rating:
        return jsonify({'error': 'course_rating is required'}), 400

    try:
        slope_rating = float(slope_rating)
        course_rating = float(course_rating)
    except (ValueError, TypeError):
        return jsonify({'error': 'slope_rating and course_rating must be numbers'}), 400

    if not (55 <= slope_rating <= 155):
        return jsonify({'error': 'slope_rating must be between 55 and 155'}), 400
    if not (55 <= course_rating <= 85):
        return jsonify({'error': 'course_rating must be between 55 and 85'}), 400

    # Resolve user: user_id > email lookup > auto-create from email
    session = get_db_connection()
    try:
        if not user_id and email:
            # Look up existing user by email
            user_row = session.execute(
                sqlalchemy.text('SELECT id FROM "User" WHERE LOWER(email) = :email'),
                {"email": email.lower()}
            ).fetchone()

            if user_row:
                user_id = str(user_row[0])
                logger.info(f"Found existing user by email: {user_id}")
            else:
                # Auto-create user from email
                user_id = str(uuid.uuid4())
                name = email.split('@')[0].replace('.', ' ').replace('_', ' ').title()
                session.execute(
                    sqlalchemy.text("""
                        INSERT INTO "User" (id, email, name, username, auth_method, status, role, created_at)
                        VALUES (:id, :email, :name, :username, 'password', 'active', 'user', NOW())
                    """),
                    {
                        "id": user_id,
                        "email": email.lower(),
                        "name": name,
                        "username": email.lower(),
                    }
                )
                session.commit()
                logger.info(f"Auto-created user: {user_id} for email {email}")

        if not user_id:
            return jsonify({'error': 'user_id or email is required'}), 400

        # Create GolfRound row
        round_id = str(uuid.uuid4())
        session.execute(
            sqlalchemy.text("""
                INSERT INTO "GolfRound" (id, user_id, course_name, slope_rating, course_rating, played_at, processing_status)
                VALUES (:id, :user_id, :course_name, :slope_rating, :course_rating, :played_at, 'pending')
            """),
            {
                "id": round_id,
                "user_id": user_id,
                "course_name": course_name,
                "slope_rating": slope_rating,
                "course_rating": course_rating,
                "played_at": played_at or datetime.now().strftime('%Y-%m-%d'),
            }
        )
        session.commit()

        ext = file.filename.rsplit('.', 1)[1].lower()
        content_type = file.content_type or 'image/jpeg'
        raw_bytes = file.read()
        oriented_bytes = _auto_orient_image(raw_bytes, content_type)
        logger.info(f"Image size: {len(raw_bytes)} -> {len(oriented_bytes)} bytes after orient")

        gcs_path = f'golf/scorecards/{user_id}/{round_id}.{ext}'
        blob = bucket.blob(gcs_path)
        blob.upload_from_string(oriented_bytes, content_type=content_type)
        scorecard_image_url = f'https://storage.googleapis.com/{bucket.name}/{gcs_path}'
        logger.info(f"Uploaded scorecard image: {scorecard_image_url}")

        session.execute(
            sqlalchemy.text("""
                UPDATE "GolfRound" SET scorecard_image_url = :url, updated_at = now()
                WHERE id = :id
            """),
            {"id": round_id, "url": scorecard_image_url}
        )
        session.commit()

        holes = []
        detected_players = []
        ocr_confidence = 0.0
        processing_status = 'ocr_complete'

        try:
            gcs_uri = f'gs://{bucket.name}/{gcs_path}'
            ocr_response = _run_ocr(gcs_uri)
            detected_players = _extract_players_from_ocr(ocr_response)

            # If OCR failed to detect any players, try rotating 90° and re-running.
            if not detected_players:
                logger.info("OCR detected no players, trying 90° rotation...")
                try:
                    img = Image.open(io.BytesIO(oriented_bytes))
                    rotated = img.rotate(-90, expand=True)
                    rot_buf = io.BytesIO()
                    rotated.save(rot_buf, format='JPEG', quality=95)
                    rot_buf.seek(0)
                    rot_bytes = rot_buf.getvalue()

                    blob.upload_from_string(rot_bytes, content_type='image/jpeg')
                    ocr_response_rot = _run_ocr(gcs_uri)
                    players_rot = _extract_players_from_ocr(ocr_response_rot)

                    if players_rot:
                        logger.info(f"Rotated OCR detected {len(players_rot)} players")
                        detected_players = players_rot
                        ocr_response = ocr_response_rot
                    else:
                        blob.upload_from_string(oriented_bytes, content_type=content_type)
                        logger.info("Rotation didn't help — kept original orientation")
                except Exception as rot_err:
                    logger.warning(f"Rotation retry failed: {rot_err}")

            # Use the first detected player's holes as the primary round scores
            # (the user will pick their own row in the review UI if multiple detected).
            if detected_players:
                holes = detected_players[0]['holes']

            if holes:
                confidences = [h['ocr_confidence'] for h in holes if h['ocr_confidence'] > 0]
                ocr_confidence = round(sum(confidences) / len(confidences), 2) if confidences else 0.0

            ocr_raw_payload = {
                'text': ocr_response.text if ocr_response else None,
                'detected_players': detected_players,
            }

            for hole in holes:
                if hole['strokes'] is not None:
                    session.execute(
                        sqlalchemy.text("""
                            INSERT INTO "GolfHoleScore" (id, round_id, hole_number, par, strokes, ocr_confidence)
                            VALUES (gen_random_uuid(), :round_id, :hole_number, :par, :strokes, :ocr_confidence)
                        """),
                        {
                            "round_id": round_id,
                            "hole_number": hole['hole_number'],
                            "par": hole['par'],
                            "strokes": hole['strokes'],
                            "ocr_confidence": hole['ocr_confidence'],
                        }
                    )

            session.execute(
                sqlalchemy.text("""
                    UPDATE "GolfRound"
                    SET processing_status = :status, ocr_raw = :ocr_raw,
                        ocr_confidence = :confidence, updated_at = now()
                    WHERE id = :id
                """),
                {
                    "id": round_id,
                    "status": processing_status,
                    "ocr_raw": json.dumps(ocr_raw_payload),
                    "confidence": ocr_confidence,
                }
            )
            session.commit()

        except Exception as ocr_err:
            logger.error(f"OCR processing failed: {ocr_err}")
            processing_status = 'failed'
            session.execute(
                sqlalchemy.text("""
                    UPDATE "GolfRound"
                    SET processing_status = 'failed', updated_at = now()
                    WHERE id = :id
                """),
                {"id": round_id}
            )
            session.commit()

        return jsonify({
            'round_id': round_id,
            'user_id': user_id,
            'processing_status': processing_status,
            'ocr_confidence': ocr_confidence,
            'holes': holes,
            'detected_players': detected_players,
            'scorecard_image_url': scorecard_image_url,
        }), 200

    except Exception as e:
        session.rollback()
        logger.error(f"Error in golf upload: {e}")
        return jsonify({'error': 'Internal server error'}), 500
    finally:
        session.close()


@golf_bp.route('/round/<round_id>', methods=['GET'])
def get_round(round_id):
    """Get round details with hole scores."""
    session = get_db_connection()
    try:
        row = session.execute(
            sqlalchemy.text("""
                SELECT id, user_id, course_name, slope_rating, course_rating,
                       adjusted_gross_score, differential, scorecard_image_url,
                       ocr_confidence, played_at, processing_status,
                       created_at, updated_at, ocr_raw
                FROM "GolfRound"
                WHERE id = :id
            """),
            {"id": round_id}
        ).fetchone()

        if not row:
            return jsonify({'error': 'Round not found'}), 404

        # Fetch hole scores
        hole_rows = session.execute(
            sqlalchemy.text("""
                SELECT hole_number, par, strokes, ocr_confidence, manually_corrected
                FROM "GolfHoleScore"
                WHERE round_id = :round_id
                ORDER BY hole_number
            """),
            {"round_id": round_id}
        ).fetchall()

        holes = []
        for h in hole_rows:
            holes.append({
                'hole_number': h[0],
                'par': h[1],
                'strokes': h[2],
                'ocr_confidence': float(h[3]) if h[3] is not None else None,
                'manually_corrected': h[4],
            })

        # Extract detected_players from ocr_raw if present.
        detected_players = []
        ocr_raw = row[13]
        if ocr_raw:
            try:
                payload = ocr_raw if isinstance(ocr_raw, dict) else json.loads(ocr_raw)
                if isinstance(payload, dict):
                    detected_players = payload.get('detected_players', []) or []
            except (json.JSONDecodeError, TypeError):
                pass

        return jsonify({
            'id': str(row[0]),
            'user_id': str(row[1]),
            'course_name': row[2],
            'slope_rating': float(row[3]),
            'course_rating': float(row[4]),
            'adjusted_gross_score': row[5],
            'differential': float(row[6]) if row[6] is not None else None,
            'scorecard_image_url': row[7],
            'ocr_confidence': float(row[8]) if row[8] is not None else None,
            'played_at': str(row[9]) if row[9] else None,
            'processing_status': row[10],
            'created_at': str(row[11]) if row[11] else None,
            'updated_at': str(row[12]) if row[12] else None,
            'holes': holes,
            'detected_players': detected_players,
        }), 200

    except Exception as e:
        logger.error(f"Error fetching round: {e}")
        return jsonify({'error': 'Internal server error'}), 500
    finally:
        session.close()


@golf_bp.route('/round/<round_id>/scores', methods=['PUT'])
def confirm_scores(round_id):
    """
    Confirm/correct hole scores, compute differential, recalculate handicap.

    Request body: {"holes": [{"hole_number": 1, "par": 4, "strokes": 5}, ... x18]}
    """
    data = request.get_json()
    if not data or 'holes' not in data:
        return jsonify({'error': 'JSON body with holes array required'}), 400

    requesting_user_id = data.get('user_id') or request.args.get('user_id')
    if not requesting_user_id:
        return jsonify({'error': 'user_id is required (in body or query param)'}), 400

    holes = data['holes']
    if len(holes) != 18:
        return jsonify({'error': 'Exactly 18 holes required'}), 400

    # Validate all holes have distinct hole_numbers 1-18
    hole_numbers = set()
    for hole in holes:
        hole_num = hole.get('hole_number')
        par = hole.get('par')
        strokes = hole.get('strokes')

        if hole_num is None or par is None or strokes is None:
            return jsonify({'error': f'Each hole must have hole_number, par, and strokes'}), 400
        if not isinstance(strokes, int) or strokes < 1:
            return jsonify({'error': f'Hole {hole_num}: strokes must be an integer >= 1'}), 400
        if not isinstance(par, int) or par < 3 or par > 6:
            return jsonify({'error': f'Hole {hole_num}: par must be between 3 and 6'}), 400
        if not isinstance(hole_num, int) or hole_num < 1 or hole_num > 18:
            return jsonify({'error': f'hole_number must be between 1 and 18'}), 400
        if hole_num in hole_numbers:
            return jsonify({'error': f'Duplicate hole_number: {hole_num}'}), 400
        hole_numbers.add(hole_num)

    if hole_numbers != set(range(1, 19)):
        return jsonify({'error': 'Must include all holes 1-18'}), 400

    session = get_db_connection()
    try:
        # Fetch the round
        row = session.execute(
            sqlalchemy.text("""
                SELECT id, user_id, slope_rating, course_rating
                FROM "GolfRound"
                WHERE id = :id
            """),
            {"id": round_id}
        ).fetchone()

        if not row:
            return jsonify({'error': 'Round not found'}), 404

        user_id = str(row[1])
        slope_rating = float(row[2])
        course_rating = float(row[3])

        # Verify ownership
        if user_id != requesting_user_id:
            return jsonify({'error': 'Not authorized to modify this round'}), 403

        # Fetch existing hole scores for comparison (to set manually_corrected)
        existing_holes = {}
        existing_rows = session.execute(
            sqlalchemy.text("""
                SELECT hole_number, strokes, par
                FROM "GolfHoleScore"
                WHERE round_id = :round_id
            """),
            {"round_id": round_id}
        ).fetchall()
        for eh in existing_rows:
            existing_holes[eh[0]] = {'strokes': eh[1], 'par': eh[2]}

        # Upsert GolfHoleScore rows
        for hole in holes:
            existing = existing_holes.get(hole['hole_number'])
            manually_corrected = False
            if existing:
                if existing['strokes'] != hole['strokes'] or existing['par'] != hole['par']:
                    manually_corrected = True

            session.execute(
                sqlalchemy.text("""
                    INSERT INTO "GolfHoleScore" (id, round_id, hole_number, par, strokes, manually_corrected)
                    VALUES (gen_random_uuid(), :round_id, :hole_number, :par, :strokes, :manually_corrected)
                    ON CONFLICT (round_id, hole_number) DO UPDATE SET
                        par = :par, strokes = :strokes, manually_corrected = :manually_corrected
                """),
                {
                    "round_id": round_id,
                    "hole_number": hole['hole_number'],
                    "par": hole['par'],
                    "strokes": hole['strokes'],
                    "manually_corrected": manually_corrected,
                }
            )

        # Compute adjusted_gross_score and differential
        adjusted_gross_score = sum(h['strokes'] for h in holes)
        differential = math.trunc((113 / slope_rating) * (adjusted_gross_score - course_rating) * 10) / 10

        # Update round
        session.execute(
            sqlalchemy.text("""
                UPDATE "GolfRound"
                SET adjusted_gross_score = :score, differential = :diff,
                    processing_status = 'confirmed', updated_at = now()
                WHERE id = :id
            """),
            {
                "id": round_id,
                "score": adjusted_gross_score,
                "diff": differential,
            }
        )

        # Recalculate handicap
        handicap_index = _recalculate_handicap(session, user_id)
        session.commit()

        return jsonify({
            'round_id': round_id,
            'user_id': user_id,
            'adjusted_gross_score': adjusted_gross_score,
            'differential': differential,
            'processing_status': 'confirmed',
            'handicap_index': handicap_index,
        }), 200

    except Exception as e:
        session.rollback()
        logger.error(f"Error confirming scores: {e}")
        return jsonify({'error': 'Internal server error'}), 500
    finally:
        session.close()


@golf_bp.route('/round/<round_id>', methods=['DELETE'])
def delete_round(round_id):
    """Delete a golf round. Verify user owns the round."""
    user_id = request.args.get('user_id')
    if not user_id:
        return jsonify({'error': 'user_id query parameter is required'}), 400

    session = get_db_connection()
    try:
        # Verify ownership
        row = session.execute(
            sqlalchemy.text("""
                SELECT user_id FROM "GolfRound" WHERE id = :id
            """),
            {"id": round_id}
        ).fetchone()

        if not row:
            return jsonify({'error': 'Round not found'}), 404

        if str(row[0]) != user_id:
            return jsonify({'error': 'Not authorized to delete this round'}), 403

        # Delete round (cascades to hole scores)
        session.execute(
            sqlalchemy.text('DELETE FROM "GolfRound" WHERE id = :id'),
            {"id": round_id}
        )

        # Recalculate handicap
        _recalculate_handicap(session, user_id)
        session.commit()

        return jsonify({'status': 'deleted'}), 200

    except Exception as e:
        session.rollback()
        logger.error(f"Error deleting round: {e}")
        return jsonify({'error': 'Internal server error'}), 500
    finally:
        session.close()


@golf_bp.route('/rounds', methods=['GET'])
def get_rounds():
    """
    Get all confirmed rounds for a user with their hole scores.

    Query params: user_id (required), limit (default 50), offset (default 0)
    """
    user_id = request.args.get('user_id')
    if not user_id:
        return jsonify({'error': 'user_id query parameter is required'}), 400

    limit = request.args.get('limit', 50, type=int)
    offset = request.args.get('offset', 0, type=int)

    session = get_db_connection()
    try:
        # Fetch rounds
        round_rows = session.execute(
            sqlalchemy.text("""
                SELECT id, user_id, course_name, slope_rating, course_rating,
                       adjusted_gross_score, differential, scorecard_image_url,
                       ocr_confidence, played_at, processing_status,
                       created_at, updated_at
                FROM "GolfRound"
                WHERE user_id = :user_id
                ORDER BY played_at DESC
                LIMIT :limit OFFSET :offset
            """),
            {"user_id": user_id, "limit": limit, "offset": offset}
        ).fetchall()

        # Collect all round IDs for batch hole score fetch
        round_ids = [str(row[0]) for row in round_rows]

        # Batch fetch all hole scores for these rounds in a single query
        holes_by_round = {}
        if round_ids:
            all_hole_rows = session.execute(
                sqlalchemy.text("""
                    SELECT round_id, hole_number, par, strokes, ocr_confidence, manually_corrected
                    FROM "GolfHoleScore"
                    WHERE round_id = ANY(:round_ids)
                    ORDER BY round_id, hole_number
                """),
                {"round_ids": round_ids}
            ).fetchall()

            for h in all_hole_rows:
                rid = str(h[0])
                if rid not in holes_by_round:
                    holes_by_round[rid] = []
                holes_by_round[rid].append({
                    'hole_number': h[1],
                    'par': h[2],
                    'strokes': h[3],
                    'ocr_confidence': float(h[4]) if h[4] is not None else None,
                    'manually_corrected': h[5],
                })

        rounds = []
        for row in round_rows:
            round_id = str(row[0])

            rounds.append({
                'id': round_id,
                'user_id': str(row[1]),
                'course_name': row[2],
                'slope_rating': float(row[3]),
                'course_rating': float(row[4]),
                'adjusted_gross_score': row[5],
                'differential': float(row[6]) if row[6] is not None else None,
                'scorecard_image_url': row[7],
                'ocr_confidence': float(row[8]) if row[8] is not None else None,
                'played_at': str(row[9]) if row[9] else None,
                'processing_status': row[10],
                'created_at': str(row[11]) if row[11] else None,
                'updated_at': str(row[12]) if row[12] else None,
                'holes': holes_by_round.get(round_id, []),
            })

        # Fetch current handicap
        handicap_row = session.execute(
            sqlalchemy.text("""
                SELECT handicap_index FROM "GolfHandicap" WHERE user_id = :user_id
            """),
            {"user_id": user_id}
        ).fetchone()

        handicap_index = float(handicap_row[0]) if handicap_row and handicap_row[0] is not None else None

        return jsonify({
            'rounds': rounds,
            'handicap_index': handicap_index,
        }), 200

    except Exception as e:
        logger.error(f"Error fetching rounds: {e}")
        return jsonify({'error': 'Internal server error'}), 500
    finally:
        session.close()


@golf_bp.route('/handicap/<user_id>', methods=['GET'])
def get_handicap(user_id):
    """Get current handicap for a user."""
    session = get_db_connection()
    try:
        row = session.execute(
            sqlalchemy.text("""
                SELECT user_id, handicap_index, rounds_used, differentials_used,
                       last_computed_at
                FROM "GolfHandicap"
                WHERE user_id = :user_id
            """),
            {"user_id": user_id}
        ).fetchone()

        if not row:
            return jsonify({
                'user_id': user_id,
                'handicap_index': None,
                'rounds_used': 0,
                'differentials_used': [],
            }), 200

        return jsonify({
            'user_id': str(row[0]),
            'handicap_index': float(row[1]) if row[1] is not None else None,
            'rounds_used': row[2],
            'differentials_used': row[3] if row[3] else [],
        }), 200

    except Exception as e:
        logger.error(f"Error fetching handicap: {e}")
        return jsonify({'error': 'Internal server error'}), 500
    finally:
        session.close()


@golf_bp.route('/leaderboard', methods=['GET'])
def get_leaderboard():
    """
    Global handicap leaderboard.

    Query params: limit (default 50), offset (default 0)
    """
    limit = request.args.get('limit', 50, type=int)
    offset = request.args.get('offset', 0, type=int)

    session = get_db_connection()
    try:
        rows = session.execute(
            sqlalchemy.text("""
                SELECT
                    gh.user_id,
                    u.name AS user_name,
                    gh.handicap_index,
                    gh.rounds_used,
                    (SELECT COUNT(*) FROM "GolfRound" gr
                     WHERE gr.user_id = gh.user_id AND gr.processing_status = 'confirmed') AS total_rounds,
                    (SELECT MIN(gr2.differential) FROM "GolfRound" gr2
                     WHERE gr2.user_id = gh.user_id AND gr2.processing_status = 'confirmed'
                       AND gr2.differential IS NOT NULL) AS best_differential
                FROM "GolfHandicap" gh
                JOIN "User" u ON u.id = gh.user_id
                WHERE gh.handicap_index IS NOT NULL
                ORDER BY gh.handicap_index ASC
                LIMIT :limit OFFSET :offset
            """),
            {"limit": limit, "offset": offset}
        ).fetchall()

        leaderboard = []
        for i, row in enumerate(rows):
            leaderboard.append({
                'rank': offset + i + 1,
                'user_id': str(row[0]),
                'user_name': row[1],
                'handicap_index': float(row[2]),
                'rounds_played': row[4],
                'best_differential': float(row[5]) if row[5] is not None else None,
            })

        return jsonify({'leaderboard': leaderboard}), 200

    except Exception as e:
        logger.error(f"Error fetching leaderboard: {e}")
        return jsonify({'error': 'Internal server error'}), 500
    finally:
        session.close()
