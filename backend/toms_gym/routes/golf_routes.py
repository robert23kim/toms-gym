"""
Golf Routes for Tom's Gym

Handles golf scorecard uploads, OCR processing, score confirmation,
handicap calculation, and leaderboard.
"""

import io
import json
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
from toms_gym.services.handicap import (
    HandicapResult,
    allocate_strokes,
    apply_twelve_month_cap,
    compute_differential,
    compute_handicap_index,
    net_double_bogey_cap,
)
from toms_gym.services.courses import (
    CourseMatch,
    TeeMatch,
    match_or_create_course,
    match_or_create_tee,
    search_courses,
)

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


# ---------------------------------------------------------------------------
# Helpers: row serialization + handicap recalc
# ---------------------------------------------------------------------------


def _course_to_dict(row):
    """Serialize a joined "Course" row to the nested `course` response block."""
    if row is None:
        return None
    return {
        'id':        str(row['id']),
        'name':      row['name'],
        'city':      row['city'],
        'state':     row['state'],
        'country':   row['country'],
        'latitude':  float(row['latitude'])  if row['latitude']  is not None else None,
        'longitude': float(row['longitude']) if row['longitude'] is not None else None,
        'holes':     row['holes'],
        'status':    row['status'],
    }


def _tee_to_dict(row):
    """Serialize a joined "Tee" row. Returns an all-null tee when row is None so
    the response shape stays stable for rounds awaiting tee entry."""
    if row is None:
        return {
            'id': None, 'name': None, 'color_hex': None,
            'rating_18': None, 'slope_18': None,
            'rating_9_front': None, 'slope_9_front': None,
            'rating_9_back':  None, 'slope_9_back':  None,
            'yardage': None, 'par': None,
            'hole_pars': None, 'hole_yardages': None, 'hole_handicaps': None,
        }
    return {
        'id':              str(row['id']),
        'name':            row['name'],
        'color_hex':       row['color_hex'],
        'rating_18':       float(row['rating_18']) if row['rating_18'] is not None else None,
        'slope_18':        row['slope_18'],
        'rating_9_front':  float(row['rating_9_front']) if row['rating_9_front'] is not None else None,
        'slope_9_front':   row['slope_9_front'],
        'rating_9_back':   float(row['rating_9_back'])  if row['rating_9_back']  is not None else None,
        'slope_9_back':    row['slope_9_back'],
        'yardage':         row['yardage'],
        'par':             row['par'],
        'hole_pars':       list(row['hole_pars'])      if row['hole_pars']      is not None else None,
        'hole_yardages':   list(row['hole_yardages'])  if row['hole_yardages']  is not None else None,
        'hole_handicaps':  list(row['hole_handicaps']) if row['hole_handicaps'] is not None else None,
    }


def _latest_handicap_snapshot(session, user_id):
    """Return (handicap_index, rounds_used, created_at) for the user's latest
    snapshot, or (None, 0, None) when they have no snapshot yet."""
    row = session.execute(sqlalchemy.text("""
        SELECT handicap_index, rounds_used, created_at
        FROM "HandicapSnapshot"
        WHERE user_id = :user_id
        ORDER BY created_at DESC
        LIMIT 1
    """), {"user_id": user_id}).mappings().fetchone()
    if row is None:
        return None, 0, None
    return (
        float(row['handicap_index']) if row['handicap_index'] is not None else None,
        row['rounds_used'],
        row['created_at'],
    )


def _recalculate_handicap(session, user_id, triggered_by_round_id=None):
    """Recompute the user's WHS handicap from last-20 Round differentials and
    INSERT a new HandicapSnapshot. Returns the capped index (or None when the
    user is still establishing).

    Pipeline:
      1. Pull last 20 rounds (score_differential NOT NULL) ordered by played_on DESC.
      2. Build parallel (differentials, nine_hole_flags) lists.
      3. Call compute_handicap_index().
      4. Pull MIN(handicap_index) from the trailing 12 months of HandicapSnapshot.
      5. apply_twelve_month_cap() on the new index.
      6. INSERT one HandicapSnapshot row with the lowest-N differentials used.
    """
    round_rows = session.execute(sqlalchemy.text("""
        SELECT score_differential, holes, played_on
        FROM "Round"
        WHERE user_id = :uid AND score_differential IS NOT NULL
        ORDER BY played_on DESC, created_at DESC
        LIMIT 20
    """), {"uid": user_id}).mappings().fetchall()

    differentials = [float(r['score_differential']) for r in round_rows]
    nine_hole_flags = [r['holes'] == 9 for r in round_rows]

    result = compute_handicap_index(differentials, nine_hole_flags=nine_hole_flags)

    final_index = None
    diffs_used = []
    if result.status == 'active' and result.handicap_index is not None:
        low_12mo_row = session.execute(sqlalchemy.text("""
            SELECT MIN(handicap_index) AS low
            FROM "HandicapSnapshot"
            WHERE user_id = :uid AND handicap_index IS NOT NULL
              AND created_at > now() - INTERVAL '12 months'
        """), {"uid": user_id}).mappings().fetchone()
        low_12mo = float(low_12mo_row['low']) if low_12mo_row and low_12mo_row['low'] is not None else None
        final_index = apply_twelve_month_cap(result.handicap_index, low_12mo)
        diffs_used = sorted(differentials)[:result.diffs_used_count]

    session.execute(sqlalchemy.text("""
        INSERT INTO "HandicapSnapshot"
            (user_id, handicap_index, rounds_used, differentials_used, triggered_by_round_id)
        VALUES (:uid, :idx, :rounds, :diffs, :rid)
    """), {
        "uid": user_id,
        "idx": final_index,
        "rounds": len(round_rows),
        "diffs": json.dumps(diffs_used),
        "rid": triggered_by_round_id,
    })

    return final_index


# ---------------------------------------------------------------------------
# POST /golf/upload
# ---------------------------------------------------------------------------


@golf_bp.route('/upload', methods=['POST'])
@rate_limit('10/hour')
def upload_scorecard():
    """Upload a golf scorecard image for OCR processing.

    Multipart form:
      image          (file, required)
      course_name    (required)
      slope_rating   (optional number; when present with course_rating, an
                      auto-created Tee row is filled with slope_18/rating_18)
      course_rating  (optional number; paired with slope_rating)
      tee_name       (optional, defaults to "Default")
      city, state, country, latitude, longitude (optional — help the fuzzy match)
      user_id        (required — OR email)
      email          (required — OR user_id)

    Creates a Round row pointing at a Course + Tee (matched-or-created), runs
    OCR, inserts HoleScore rows for the primary player, returns nested shape.
    NOTE: `played_on` defaults to CURRENT_DATE; upload does NOT accept an
    override (that's a future-phase concern per plan §Task 4).
    """
    if 'image' not in request.files:
        return jsonify({'error': 'No image file provided'}), 400

    file = request.files['image']
    if file.filename == '':
        return jsonify({'error': 'No selected file'}), 400
    if not _allowed_image(file.filename):
        return jsonify({'error': 'File type not allowed'}), 400

    file.seek(0, 2)
    file_size = file.tell()
    file.seek(0)
    if file_size > 20 * 1024 * 1024:
        return jsonify({'error': 'File too large. Maximum 20MB'}), 400

    course_name = request.form.get('course_name')
    if not course_name:
        return jsonify({'error': 'course_name is required'}), 400

    slope_rating  = request.form.get('slope_rating')
    course_rating = request.form.get('course_rating')
    tee_name      = request.form.get('tee_name') or 'Default'

    rating_18 = None
    slope_18  = None
    if slope_rating or course_rating:
        try:
            if slope_rating:
                slope_18 = int(float(slope_rating))
            if course_rating:
                rating_18 = float(course_rating)
        except (ValueError, TypeError):
            return jsonify({'error': 'slope_rating and course_rating must be numbers'}), 400
        if slope_18 is not None and not (55 <= slope_18 <= 155):
            return jsonify({'error': 'slope_rating must be between 55 and 155'}), 400
        if rating_18 is not None and not (55 <= rating_18 <= 85):
            return jsonify({'error': 'course_rating must be between 55 and 85'}), 400

    city    = request.form.get('city')
    state   = request.form.get('state')
    country = request.form.get('country')
    lat_s   = request.form.get('latitude')
    lng_s   = request.form.get('longitude')
    near = None
    try:
        lat = float(lat_s) if lat_s else None
        lng = float(lng_s) if lng_s else None
        if lat is not None and lng is not None:
            near = (lat, lng)
    except (ValueError, TypeError):
        return jsonify({'error': 'latitude and longitude must be numbers'}), 400

    user_id = request.form.get('user_id')
    email   = request.form.get('email')

    session = get_db_connection()
    try:
        # Resolve user: user_id > email lookup > auto-create from email.
        if not user_id and email:
            user_row = session.execute(
                sqlalchemy.text('SELECT id FROM "User" WHERE LOWER(email) = :email'),
                {"email": email.lower()}
            ).fetchone()
            if user_row:
                user_id = str(user_row[0])
            else:
                user_id = str(uuid.uuid4())
                name = email.split('@')[0].replace('.', ' ').replace('_', ' ').title()
                session.execute(sqlalchemy.text("""
                    INSERT INTO "User" (id, email, name, username, auth_method, status, role, created_at)
                    VALUES (:id, :email, :name, :username, 'password', 'active', 'user', NOW())
                """), {
                    "id": user_id,
                    "email": email.lower(),
                    "name": name,
                    "username": email.lower(),
                })
                session.commit()
                logger.info(f"Auto-created user {user_id} for email {email}")

        if not user_id:
            return jsonify({'error': 'user_id or email is required'}), 400

        # Match-or-create Course + Tee via the courses service.
        # The service issues its own commits for newly-inserted rows.
        course_match = match_or_create_course(session, name=course_name, near=near)
        # Patch city/state/country/lat/lng when we just created a pending course
        # and the caller provided them — the service only stores (name, lat, lng).
        if course_match.created and (city or state or country):
            session.execute(sqlalchemy.text("""
                UPDATE "Course" SET city = :c, state = :s, country = :co
                WHERE id = :id
            """), {"c": city, "s": state, "co": country, "id": course_match.course_id})
            session.commit()

        tee_match = match_or_create_tee(
            session,
            course_id=course_match.course_id,
            name=tee_name,
            rating=rating_18,
            slope=slope_18,
        )

        # Create the Round.
        round_id = str(uuid.uuid4())
        session.execute(sqlalchemy.text("""
            INSERT INTO "Round"
                (id, user_id, course_id, tee_id, holes, processing_status)
            VALUES (:id, :uid, :cid, :tid, 18, 'pending')
        """), {
            "id":  round_id,
            "uid": user_id,
            "cid": course_match.course_id,
            "tid": tee_match.tee_id,
        })
        session.commit()

        # Upload the scorecard image.
        ext = file.filename.rsplit('.', 1)[1].lower()
        content_type = file.content_type or 'image/jpeg'
        raw_bytes = file.read()
        oriented_bytes = _auto_orient_image(raw_bytes, content_type)

        gcs_path = f'golf/scorecards/{user_id}/{round_id}.{ext}'
        blob = bucket.blob(gcs_path)
        blob.upload_from_string(oriented_bytes, content_type=content_type)
        scorecard_image_url = f'https://storage.googleapis.com/{bucket.name}/{gcs_path}'

        session.execute(sqlalchemy.text("""
            UPDATE "Round" SET scorecard_image_url = :url, updated_at = now()
            WHERE id = :id
        """), {"id": round_id, "url": scorecard_image_url})
        session.commit()

        # OCR pass (with 90° rotation retry on empty result).
        holes = []
        detected_players = []
        ocr_confidence = 0.0
        processing_status = 'ocr_complete'

        try:
            gcs_uri = f'gs://{bucket.name}/{gcs_path}'
            ocr_response = _run_ocr(gcs_uri)
            detected_players = _extract_players_from_ocr(ocr_response)

            if not detected_players:
                try:
                    img = Image.open(io.BytesIO(oriented_bytes))
                    rotated = img.rotate(-90, expand=True)
                    rot_buf = io.BytesIO()
                    rotated.save(rot_buf, format='JPEG', quality=95)
                    rot_bytes = rot_buf.getvalue()
                    blob.upload_from_string(rot_bytes, content_type='image/jpeg')
                    ocr_response_rot = _run_ocr(gcs_uri)
                    players_rot = _extract_players_from_ocr(ocr_response_rot)
                    if players_rot:
                        detected_players = players_rot
                        ocr_response = ocr_response_rot
                    else:
                        blob.upload_from_string(oriented_bytes, content_type=content_type)
                except Exception as rot_err:
                    logger.warning(f"Rotation retry failed: {rot_err}")

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
                    session.execute(sqlalchemy.text("""
                        INSERT INTO "HoleScore"
                            (round_id, hole_number, par, strokes, ocr_confidence)
                        VALUES (:rid, :hn, :par, :strokes, :conf)
                        ON CONFLICT (round_id, hole_number) DO UPDATE SET
                            par = :par, strokes = :strokes, ocr_confidence = :conf
                    """), {
                        "rid": round_id,
                        "hn":  hole['hole_number'],
                        "par": hole['par'],
                        "strokes": hole['strokes'],
                        "conf": hole['ocr_confidence'],
                    })

            session.execute(sqlalchemy.text("""
                UPDATE "Round"
                SET processing_status = :status, ocr_raw = :raw, ocr_confidence = :conf,
                    updated_at = now()
                WHERE id = :id
            """), {
                "id": round_id,
                "status": processing_status,
                "raw":    json.dumps(ocr_raw_payload),
                "conf":   ocr_confidence,
            })
            session.commit()

        except Exception as ocr_err:
            logger.error(f"OCR processing failed: {ocr_err}")
            processing_status = 'failed'
            session.execute(sqlalchemy.text("""
                UPDATE "Round" SET processing_status = 'failed', updated_at = now()
                WHERE id = :id
            """), {"id": round_id})
            session.commit()

        return _fetch_and_serialize_round(
            session,
            round_id,
            user_id=user_id,
            extra={
                'detected_players': detected_players,
                'needs_tee': tee_match.needs_tee,
            },
        )

    except Exception as e:
        session.rollback()
        logger.error(f"Error in golf upload: {e}")
        return jsonify({'error': 'Internal server error'}), 500
    finally:
        session.close()


# ---------------------------------------------------------------------------
# GET /golf/round/<id>
# ---------------------------------------------------------------------------


def _fetch_and_serialize_round(session, round_id, user_id=None, extra=None):
    """Shared helper used by upload + GET /round. Joins Round, Course, Tee and
    HoleScore rows; returns an (already JSON'd) Flask response.
    """
    row = session.execute(sqlalchemy.text("""
        SELECT r.id AS round_id, r.user_id, r.played_on, r.holes AS round_holes,
               r.scores, r.total_score, r.front_nine, r.back_nine,
               r.score_differential, r.scorecard_image_url, r.ocr_raw,
               r.ocr_confidence, r.processing_status, r.created_at, r.updated_at,
               c.id AS c_id, c.name AS c_name, c.city, c.state, c.country,
               c.latitude, c.longitude, c.holes AS c_holes, c.status AS c_status,
               t.id AS t_id, t.name AS t_name, t.color_hex,
               t.rating_18, t.slope_18,
               t.rating_9_front, t.slope_9_front, t.rating_9_back, t.slope_9_back,
               t.yardage, t.par, t.hole_pars, t.hole_yardages, t.hole_handicaps
        FROM "Round" r
        JOIN "Course" c ON c.id = r.course_id
        LEFT JOIN "Tee" t ON t.id = r.tee_id
        WHERE r.id = :id
    """), {"id": round_id}).mappings().fetchone()

    if row is None:
        return jsonify({'error': 'Round not found'}), 404

    # Hole scores in order.
    hole_rows = session.execute(sqlalchemy.text("""
        SELECT hole_number, par, strokes, ocr_confidence, manually_corrected
        FROM "HoleScore"
        WHERE round_id = :rid
        ORDER BY hole_number
    """), {"rid": round_id}).mappings().fetchall()
    hole_scores = [
        {
            'hole_number': h['hole_number'],
            'par': h['par'],
            'strokes': h['strokes'],
            'ocr_confidence':
                float(h['ocr_confidence']) if h['ocr_confidence'] is not None else None,
            'manually_corrected': h['manually_corrected'],
        }
        for h in hole_rows
    ]

    # Parse detected_players from ocr_raw.
    detected_players = []
    if row['ocr_raw']:
        try:
            payload = row['ocr_raw'] if isinstance(row['ocr_raw'], dict) else json.loads(row['ocr_raw'])
            if isinstance(payload, dict):
                detected_players = payload.get('detected_players', []) or []
        except (json.JSONDecodeError, TypeError):
            pass

    course_block = _course_to_dict({
        'id': row['c_id'],           'name': row['c_name'],
        'city': row['city'],         'state': row['state'],
        'country': row['country'],   'latitude': row['latitude'],
        'longitude': row['longitude'], 'holes': row['c_holes'],
        'status': row['c_status'],
    })
    tee_block = _tee_to_dict({
        'id': row['t_id'],
        'name': row['t_name'],
        'color_hex': row['color_hex'],
        'rating_18': row['rating_18'], 'slope_18': row['slope_18'],
        'rating_9_front': row['rating_9_front'], 'slope_9_front': row['slope_9_front'],
        'rating_9_back':  row['rating_9_back'],  'slope_9_back':  row['slope_9_back'],
        'yardage': row['yardage'],     'par': row['par'],
        'hole_pars': row['hole_pars'],
        'hole_yardages': row['hole_yardages'],
        'hole_handicaps': row['hole_handicaps'],
    }) if row['t_id'] is not None else _tee_to_dict(None)

    round_block = {
        'id':                  str(row['round_id']),
        'user_id':             str(row['user_id']),
        'played_on':           str(row['played_on']) if row['played_on'] else None,
        'holes':               row['round_holes'],
        'course':              course_block,
        'tee':                 tee_block,
        'hole_scores':         hole_scores,
        'scores':              list(row['scores']) if row['scores'] is not None else None,
        'total_score':         row['total_score'],
        'front_nine':          row['front_nine'],
        'back_nine':           row['back_nine'],
        'score_differential':
            float(row['score_differential']) if row['score_differential'] is not None else None,
        'scorecard_image_url': row['scorecard_image_url'],
        'ocr_confidence':
            float(row['ocr_confidence']) if row['ocr_confidence'] is not None else None,
        'processing_status':   row['processing_status'],
        'needs_tee':           row['t_id'] is None,
        'created_at':          str(row['created_at']) if row['created_at'] else None,
        'updated_at':          str(row['updated_at']) if row['updated_at'] else None,
    }

    body = {
        'round': round_block,
        'detected_players': detected_players,
    }
    if user_id is not None:
        body['user_id'] = user_id
        body['round_id'] = str(row['round_id'])
    if extra:
        body.update(extra)
    return jsonify(body), 200


@golf_bp.route('/round/<round_id>', methods=['GET'])
def get_round(round_id):
    """Get round details with nested course/tee + hole scores."""
    session = get_db_connection()
    try:
        return _fetch_and_serialize_round(session, round_id)
    except Exception as e:
        logger.error(f"Error fetching round: {e}")
        return jsonify({'error': 'Internal server error'}), 500
    finally:
        session.close()


# ---------------------------------------------------------------------------
# PUT /golf/round/<id>/scores
# ---------------------------------------------------------------------------


@golf_bp.route('/round/<round_id>/scores', methods=['PUT'])
def confirm_scores(round_id):
    """Confirm/correct hole scores.

    Body: {"holes": [{"hole_number": 1, "par": 4, "strokes": 5}, ...x18],
           "user_id": "..." (or ?user_id=...)}

    Pipeline:
      1. Validate holes (18 distinct entries, legal values).
      2. Fetch Round + Tee (need slope_18/rating_18/hole_handicaps).
      3. Verify ownership (round.user_id == requesting_user_id).
      4. Upsert each HoleScore with manually_corrected flag derived from prior row.
      5. Fetch the user's latest handicap_index (via _latest_handicap_snapshot).
         allocate_strokes(index, hole_handicaps) → per-hole received or None.
      6. Per hole: NDB cap = net_double_bogey_cap(par, rec, actual=strokes); sum
         the capped values → adjusted_total.
      7. compute_differential(adjusted_total, rating_18, slope_18) → differential.
      8. UPDATE Round with totals + differential + status='confirmed'.
      9. _recalculate_handicap() → new HandicapSnapshot.
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

    hole_numbers = set()
    for hole in holes:
        hole_num = hole.get('hole_number')
        par      = hole.get('par')
        strokes  = hole.get('strokes')
        if hole_num is None or par is None or strokes is None:
            return jsonify({'error': 'Each hole must have hole_number, par, and strokes'}), 400
        if not isinstance(strokes, int) or strokes < 1:
            return jsonify({'error': f'Hole {hole_num}: strokes must be an integer >= 1'}), 400
        if not isinstance(par, int) or par < 3 or par > 6:
            return jsonify({'error': f'Hole {hole_num}: par must be between 3 and 6'}), 400
        if not isinstance(hole_num, int) or hole_num < 1 or hole_num > 18:
            return jsonify({'error': 'hole_number must be between 1 and 18'}), 400
        if hole_num in hole_numbers:
            return jsonify({'error': f'Duplicate hole_number: {hole_num}'}), 400
        hole_numbers.add(hole_num)

    if hole_numbers != set(range(1, 19)):
        return jsonify({'error': 'Must include all holes 1-18'}), 400

    session = get_db_connection()
    try:
        round_row = session.execute(sqlalchemy.text("""
            SELECT r.id, r.user_id, r.tee_id,
                   t.rating_18, t.slope_18, t.hole_handicaps
            FROM "Round" r
            LEFT JOIN "Tee" t ON t.id = r.tee_id
            WHERE r.id = :id
        """), {"id": round_id}).mappings().fetchone()

        if round_row is None:
            return jsonify({'error': 'Round not found'}), 404

        user_id = str(round_row['user_id'])
        if user_id != requesting_user_id:
            return jsonify({'error': 'Not authorized to modify this round'}), 403

        rating_18 = float(round_row['rating_18']) if round_row['rating_18'] is not None else None
        slope_18  = round_row['slope_18']
        if rating_18 is None or slope_18 is None:
            return jsonify({'error': 'Round has no tee rating/slope; pick a tee first'}), 400
        hole_handicaps = list(round_row['hole_handicaps']) if round_row['hole_handicaps'] is not None else None

        # Prior strokes/par -> drive manually_corrected flag.
        existing_rows = session.execute(sqlalchemy.text("""
            SELECT hole_number, strokes, par
            FROM "HoleScore" WHERE round_id = :rid
        """), {"rid": round_id}).mappings().fetchall()
        existing = {r['hole_number']: {'strokes': r['strokes'], 'par': r['par']} for r in existing_rows}

        for hole in holes:
            prior = existing.get(hole['hole_number'])
            manually_corrected = False
            if prior and (prior['strokes'] != hole['strokes'] or prior['par'] != hole['par']):
                manually_corrected = True
            session.execute(sqlalchemy.text("""
                INSERT INTO "HoleScore"
                    (round_id, hole_number, par, strokes, manually_corrected)
                VALUES (:rid, :hn, :par, :strokes, :corrected)
                ON CONFLICT (round_id, hole_number) DO UPDATE SET
                    par = :par, strokes = :strokes, manually_corrected = :corrected
            """), {
                "rid": round_id,
                "hn":  hole['hole_number'],
                "par": hole['par'],
                "strokes": hole['strokes'],
                "corrected": manually_corrected,
            })

        # Current index -> stroke allocation (None when user has no handicap yet).
        current_index, _, _ = _latest_handicap_snapshot(session, user_id)
        received = allocate_strokes(current_index, hole_handicaps)

        # Sort holes 1..18 so the received/hole_handicap mapping stays aligned.
        ordered = sorted(holes, key=lambda h: h['hole_number'])
        total_raw = 0
        total_adjusted = 0
        front = 0
        back  = 0
        scores_array = []
        for i, hole in enumerate(ordered):
            total_raw += hole['strokes']
            if received is None:
                capped = net_double_bogey_cap(par=hole['par'], strokes_received=None, actual=hole['strokes'])
            else:
                capped = net_double_bogey_cap(
                    par=hole['par'], strokes_received=received[i], actual=hole['strokes'],
                )
            total_adjusted += capped
            scores_array.append(hole['strokes'])
            if i < 9:
                front += hole['strokes']
            else:
                back += hole['strokes']

        differential = compute_differential(
            adjusted_total=total_adjusted, rating=rating_18, slope=slope_18,
        )
        # Differentials are stored to 1dp per WHS convention.
        differential_1dp = round(differential, 1)

        session.execute(sqlalchemy.text("""
            UPDATE "Round"
            SET scores = :scores, total_score = :total, front_nine = :front, back_nine = :back,
                score_differential = :diff, processing_status = 'confirmed', updated_at = now()
            WHERE id = :id
        """), {
            "id": round_id,
            "scores": scores_array,
            "total": total_raw,
            "front": front,
            "back":  back,
            "diff":  differential_1dp,
        })

        handicap_index = _recalculate_handicap(session, user_id, triggered_by_round_id=round_id)
        session.commit()

        return jsonify({
            'round_id': round_id,
            'user_id': user_id,
            'adjusted_gross_score': total_adjusted,
            'total_score': total_raw,
            'score_differential': differential_1dp,
            'processing_status': 'confirmed',
            'handicap_index': handicap_index,
        }), 200

    except Exception as e:
        session.rollback()
        logger.error(f"Error confirming scores: {e}")
        return jsonify({'error': 'Internal server error'}), 500
    finally:
        session.close()


# ---------------------------------------------------------------------------
# DELETE /golf/round/<id>
# ---------------------------------------------------------------------------


@golf_bp.route('/round/<round_id>', methods=['DELETE'])
def delete_round(round_id):
    """Delete a round; recalculates handicap (and emits a new snapshot)."""
    requesting_user_id = request.args.get('user_id')
    if not requesting_user_id:
        return jsonify({'error': 'user_id query parameter is required'}), 400

    session = get_db_connection()
    try:
        row = session.execute(sqlalchemy.text("""
            SELECT user_id FROM "Round" WHERE id = :id
        """), {"id": round_id}).fetchone()
        if row is None:
            return jsonify({'error': 'Round not found'}), 404

        user_id = str(row[0])
        if user_id != requesting_user_id:
            return jsonify({'error': 'Not authorized to delete this round'}), 403

        session.execute(sqlalchemy.text('DELETE FROM "Round" WHERE id = :id'), {"id": round_id})
        # triggered_by_round_id becomes None since the round no longer exists.
        _recalculate_handicap(session, user_id, triggered_by_round_id=None)
        session.commit()

        return jsonify({'status': 'deleted'}), 200

    except Exception as e:
        session.rollback()
        logger.error(f"Error deleting round: {e}")
        return jsonify({'error': 'Internal server error'}), 500
    finally:
        session.close()


# ---------------------------------------------------------------------------
# GET /golf/rounds?user_id=
# ---------------------------------------------------------------------------


@golf_bp.route('/rounds', methods=['GET'])
def get_rounds():
    """List a user's rounds with nested course/tee + hole scores.

    Query params: user_id (required), limit (default 50), offset (default 0).
    Response includes the user's latest snapshot handicap_index.
    """
    user_id = request.args.get('user_id')
    if not user_id:
        return jsonify({'error': 'user_id query parameter is required'}), 400

    limit  = request.args.get('limit',  50, type=int)
    offset = request.args.get('offset',  0, type=int)

    session = get_db_connection()
    try:
        rows = session.execute(sqlalchemy.text("""
            SELECT r.id AS round_id, r.user_id, r.played_on, r.holes AS round_holes,
                   r.scores, r.total_score, r.front_nine, r.back_nine,
                   r.score_differential, r.scorecard_image_url, r.ocr_confidence,
                   r.processing_status, r.created_at, r.updated_at,
                   c.id AS c_id, c.name AS c_name, c.city, c.state, c.country,
                   c.latitude, c.longitude, c.holes AS c_holes, c.status AS c_status,
                   t.id AS t_id, t.name AS t_name, t.color_hex,
                   t.rating_18, t.slope_18, t.rating_9_front, t.slope_9_front,
                   t.rating_9_back, t.slope_9_back,
                   t.yardage, t.par, t.hole_pars, t.hole_yardages, t.hole_handicaps
            FROM "Round" r
            JOIN "Course" c ON c.id = r.course_id
            LEFT JOIN "Tee" t ON t.id = r.tee_id
            WHERE r.user_id = :uid
            ORDER BY r.played_on DESC, r.created_at DESC
            LIMIT :limit OFFSET :offset
        """), {"uid": user_id, "limit": limit, "offset": offset}).mappings().fetchall()

        round_ids = [str(r['round_id']) for r in rows]
        holes_by_round = {}
        if round_ids:
            hole_rows = session.execute(sqlalchemy.text("""
                SELECT round_id, hole_number, par, strokes, ocr_confidence, manually_corrected
                FROM "HoleScore"
                WHERE round_id = ANY(:rids)
                ORDER BY round_id, hole_number
            """), {"rids": round_ids}).mappings().fetchall()
            for h in hole_rows:
                rid = str(h['round_id'])
                holes_by_round.setdefault(rid, []).append({
                    'hole_number': h['hole_number'],
                    'par': h['par'],
                    'strokes': h['strokes'],
                    'ocr_confidence':
                        float(h['ocr_confidence']) if h['ocr_confidence'] is not None else None,
                    'manually_corrected': h['manually_corrected'],
                })

        rounds = []
        for r in rows:
            rid = str(r['round_id'])
            course_block = _course_to_dict({
                'id': r['c_id'], 'name': r['c_name'],
                'city': r['city'], 'state': r['state'], 'country': r['country'],
                'latitude': r['latitude'], 'longitude': r['longitude'],
                'holes': r['c_holes'], 'status': r['c_status'],
            })
            tee_block = _tee_to_dict({
                'id': r['t_id'], 'name': r['t_name'], 'color_hex': r['color_hex'],
                'rating_18': r['rating_18'], 'slope_18': r['slope_18'],
                'rating_9_front': r['rating_9_front'], 'slope_9_front': r['slope_9_front'],
                'rating_9_back':  r['rating_9_back'],  'slope_9_back':  r['slope_9_back'],
                'yardage': r['yardage'], 'par': r['par'],
                'hole_pars': r['hole_pars'], 'hole_yardages': r['hole_yardages'],
                'hole_handicaps': r['hole_handicaps'],
            }) if r['t_id'] is not None else _tee_to_dict(None)
            rounds.append({
                'id':                  rid,
                'user_id':             str(r['user_id']),
                'played_on':           str(r['played_on']) if r['played_on'] else None,
                'holes':               r['round_holes'],
                'course':              course_block,
                'tee':                 tee_block,
                'hole_scores':         holes_by_round.get(rid, []),
                'scores':              list(r['scores']) if r['scores'] is not None else None,
                'total_score':         r['total_score'],
                'front_nine':          r['front_nine'],
                'back_nine':           r['back_nine'],
                'score_differential':
                    float(r['score_differential']) if r['score_differential'] is not None else None,
                'scorecard_image_url': r['scorecard_image_url'],
                'ocr_confidence':
                    float(r['ocr_confidence']) if r['ocr_confidence'] is not None else None,
                'processing_status':   r['processing_status'],
                'needs_tee':           r['t_id'] is None,
                'created_at':          str(r['created_at']) if r['created_at'] else None,
                'updated_at':          str(r['updated_at']) if r['updated_at'] else None,
            })

        handicap_index, rounds_used, _ = _latest_handicap_snapshot(session, user_id)
        return jsonify({
            'rounds': rounds,
            'handicap_index': handicap_index,
            'rounds_used': rounds_used,
        }), 200

    except Exception as e:
        logger.error(f"Error fetching rounds: {e}")
        return jsonify({'error': 'Internal server error'}), 500
    finally:
        session.close()


# ---------------------------------------------------------------------------
# GET /golf/handicap/<user_id>
# ---------------------------------------------------------------------------


@golf_bp.route('/handicap/<user_id>', methods=['GET'])
def get_handicap(user_id):
    """Return the user's latest HandicapSnapshot."""
    session = get_db_connection()
    try:
        row = session.execute(sqlalchemy.text("""
            SELECT handicap_index, rounds_used, differentials_used, created_at
            FROM "HandicapSnapshot"
            WHERE user_id = :uid
            ORDER BY created_at DESC
            LIMIT 1
        """), {"uid": user_id}).mappings().fetchone()

        if row is None:
            return jsonify({
                'user_id': user_id,
                'handicap_index': None,
                'rounds_used': 0,
                'differentials_used': [],
                'created_at': None,
            }), 200

        diffs = row['differentials_used']
        if isinstance(diffs, str):
            try:
                diffs = json.loads(diffs)
            except json.JSONDecodeError:
                diffs = []

        return jsonify({
            'user_id': user_id,
            'handicap_index':
                float(row['handicap_index']) if row['handicap_index'] is not None else None,
            'rounds_used': row['rounds_used'],
            'differentials_used': diffs or [],
            'created_at': str(row['created_at']) if row['created_at'] else None,
        }), 200

    except Exception as e:
        logger.error(f"Error fetching handicap: {e}")
        return jsonify({'error': 'Internal server error'}), 500
    finally:
        session.close()


# ---------------------------------------------------------------------------
# POST /golf/handicap/<user_id>/recompute
# ---------------------------------------------------------------------------


@golf_bp.route('/handicap/<user_id>/recompute', methods=['POST'])
def recompute_user_handicap(user_id):
    """Force a fresh HandicapSnapshot for a user from their stored rounds.

    Used when the engine rules change (e.g. minimum-rounds threshold) and we
    need to refresh existing users' indices without re-confirming rounds.
    """
    session = get_db_connection()
    try:
        index = _recalculate_handicap(session, user_id)
        session.commit()
        return jsonify({
            'user_id': user_id,
            'handicap_index': float(index) if index is not None else None,
        }), 200
    except Exception as e:
        session.rollback()
        logger.error(f"Error recomputing handicap for {user_id}: {e}")
        return jsonify({'error': 'Internal server error'}), 500
    finally:
        session.close()


# ---------------------------------------------------------------------------
# GET /golf/leaderboard
# ---------------------------------------------------------------------------


@golf_bp.route('/leaderboard', methods=['GET'])
def get_leaderboard():
    """Global leaderboard — latest snapshot per user + 30-day monthly_delta.

    `monthly_delta` = latest.handicap_index − past.handicap_index where `past`
    is the most-recent snapshot in the [30, 60)-day window. Negative means
    improvement (handicap went down).
    """
    limit  = request.args.get('limit', 50, type=int)
    offset = request.args.get('offset', 0, type=int)

    session = get_db_connection()
    try:
        rows = session.execute(sqlalchemy.text("""
            WITH latest AS (
                SELECT DISTINCT ON (user_id)
                       user_id, handicap_index, rounds_used, created_at
                FROM "HandicapSnapshot"
                WHERE handicap_index IS NOT NULL
                ORDER BY user_id, created_at DESC
            ),
            past AS (
                SELECT DISTINCT ON (user_id)
                       user_id, handicap_index AS past_index, created_at AS past_created
                FROM "HandicapSnapshot"
                WHERE handicap_index IS NOT NULL
                  AND created_at <  now() - INTERVAL '30 days'
                  AND created_at >= now() - INTERVAL '60 days'
                ORDER BY user_id, created_at DESC
            ),
            round_stats AS (
                SELECT user_id,
                       COUNT(*)                         AS total_rounds,
                       MIN(score_differential)          AS best_differential
                FROM "Round"
                WHERE score_differential IS NOT NULL
                GROUP BY user_id
            )
            SELECT l.user_id, u.name AS user_name,
                   l.handicap_index, l.rounds_used, l.created_at,
                   p.past_index,
                   COALESCE(rs.total_rounds, 0) AS total_rounds,
                   rs.best_differential
            FROM latest l
            JOIN "User" u ON u.id = l.user_id
            LEFT JOIN past p ON p.user_id = l.user_id
            LEFT JOIN round_stats rs ON rs.user_id = l.user_id
            ORDER BY l.handicap_index ASC
            LIMIT :limit OFFSET :offset
        """), {"limit": limit, "offset": offset}).mappings().fetchall()

        leaderboard = []
        for i, row in enumerate(rows):
            past = float(row['past_index']) if row['past_index'] is not None else None
            latest_idx = float(row['handicap_index'])
            delta = None
            if past is not None:
                delta = round(latest_idx - past, 1)
            leaderboard.append({
                'rank':              offset + i + 1,
                'user_id':           str(row['user_id']),
                'user_name':         row['user_name'],
                'handicap_index':    latest_idx,
                'monthly_delta':     delta,
                'rounds_played':     row['total_rounds'],
                'rounds_used':       row['rounds_used'],
                'best_differential':
                    float(row['best_differential']) if row['best_differential'] is not None else None,
                'latest_snapshot_at': str(row['created_at']) if row['created_at'] else None,
            })

        return jsonify({'leaderboard': leaderboard}), 200

    except Exception as e:
        logger.error(f"Error fetching leaderboard: {e}")
        return jsonify({'error': 'Internal server error'}), 500
    finally:
        session.close()


# ---------------------------------------------------------------------------
# GET /golf/courses
# ---------------------------------------------------------------------------


def _parse_near(raw):
    """Parse ?near=lat,lng → (lat, lng) or None. Malformed input → None."""
    if not raw:
        return None
    try:
        parts = raw.split(',')
        if len(parts) != 2:
            return None
        return (float(parts[0]), float(parts[1]))
    except (ValueError, TypeError):
        return None


@golf_bp.route('/courses', methods=['GET'])
def list_courses():
    """Fuzzy-search courses by ?q= (and optional ?near=lat,lng)."""
    q = request.args.get('q', '').strip()
    if not q:
        return jsonify({'courses': []}), 200

    near  = _parse_near(request.args.get('near'))
    limit = request.args.get('limit', 10, type=int)

    session = get_db_connection()
    try:
        courses = search_courses(session, q=q, near=near, limit=limit)
        return jsonify({'courses': courses}), 200
    except Exception as e:
        logger.error(f"Error searching courses: {e}")
        return jsonify({'error': 'Internal server error'}), 500
    finally:
        session.close()


@golf_bp.route('/courses', methods=['POST'])
def create_course():
    """Manual unknown-course submission.

    Body: {name, city?, state?, country?, latitude?, longitude?, holes?}.
    `status` = 'verified' when the caller supplies a user_id (proxy for
    authenticated), else 'pending'.
    """
    data = request.get_json() or {}
    name = (data.get('name') or '').strip()
    if not name:
        return jsonify({'error': 'name is required'}), 400

    city      = data.get('city')
    state     = data.get('state')
    country   = data.get('country')
    latitude  = data.get('latitude')
    longitude = data.get('longitude')
    holes     = data.get('holes', 18)
    if holes not in (9, 18):
        return jsonify({'error': 'holes must be 9 or 18'}), 400

    user_id = data.get('user_id')
    status  = 'verified' if user_id else 'pending'

    session = get_db_connection()
    try:
        row = session.execute(sqlalchemy.text("""
            INSERT INTO "Course" (name, city, state, country, latitude, longitude, holes, status)
            VALUES (:name, :city, :state, :country, :lat, :lng, :holes, :status)
            RETURNING id, name, city, state, country, latitude, longitude, holes, status
        """), {
            "name": name, "city": city, "state": state, "country": country,
            "lat": latitude, "lng": longitude,
            "holes": holes, "status": status,
        }).mappings().fetchone()
        session.commit()
        return jsonify({'course': _course_to_dict(row)}), 201

    except Exception as e:
        session.rollback()
        logger.error(f"Error creating course: {e}")
        return jsonify({'error': 'Internal server error'}), 500
    finally:
        session.close()


# ---------------------------------------------------------------------------
# GET /golf/users/<user_id>/handicap/history
# ---------------------------------------------------------------------------


_HANDICAP_HISTORY_RANGES = {
    '6m':  "now() - INTERVAL '6 months'",
    '12m': "now() - INTERVAL '12 months'",
    '24m': "now() - INTERVAL '24 months'",
    'all': None,
}


@golf_bp.route('/users/<user_id>/handicap/history', methods=['GET'])
def get_handicap_history(user_id):
    """HandicapSnapshot time-series for a user. ?range=6m|12m|24m|all (default 12m)."""
    range_key = request.args.get('range', '12m')
    if range_key not in _HANDICAP_HISTORY_RANGES:
        return jsonify({'error': "range must be one of '6m','12m','24m','all'"}), 400
    since_expr = _HANDICAP_HISTORY_RANGES[range_key]
    where = "WHERE user_id = :uid"
    if since_expr:
        where += f" AND created_at >= {since_expr}"

    session = get_db_connection()
    try:
        rows = session.execute(sqlalchemy.text(f"""
            SELECT handicap_index, rounds_used, created_at
            FROM "HandicapSnapshot"
            {where}
            ORDER BY created_at ASC
        """), {"uid": user_id}).mappings().fetchall()

        history = [
            {
                'handicap_index':
                    float(r['handicap_index']) if r['handicap_index'] is not None else None,
                'rounds_used': r['rounds_used'],
                'created_at':  str(r['created_at']) if r['created_at'] else None,
            }
            for r in rows
        ]
        return jsonify({'history': history, 'range': range_key}), 200

    except Exception as e:
        logger.error(f"Error fetching handicap history: {e}")
        return jsonify({'error': 'Internal server error'}), 500
    finally:
        session.close()
