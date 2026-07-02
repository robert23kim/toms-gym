"""Grid-based scorecard parser.

Recovers the printed table structure of a golf scorecard photo (perspective
rectification + grid-line detection), assigns Vision OCR symbols to table
cells, and reads players/scores/pars/tees from the labeled grid — replacing
the row-chaining/x-clustering geometry heuristics as the primary parser.

Pure and DB-free (same pattern as services/handicap.py). OCR runs once on the
original image; symbol centroids are mapped through the rectification
homography, so tests replay cached OCR dumps without network access.

Design: docs/superpowers/specs/2026-07-02-golf-grid-parser-design.md
"""
import logging
import re

import cv2
import numpy as np

logger = logging.getLogger(__name__)

# Printed labels that identify structural rows via the label column.
TEE_LABELS = {"BLACK", "BLUE", "WHITE", "GOLD", "RED", "GREEN", "SILVER",
              "YELLOW", "CHAMPION", "CHAMPIONSHIP"}
STRUCTURAL_LABELS = TEE_LABELS | {
    "PAR", "HANDICAP", "HOLE", "HOLES", "OUT", "IN", "TOTAL", "TOT", "DATE",
    "SCORER", "ATTEST", "INITIALS", "NET", "HCP", "ADJ", "RATING", "SLOPE",
    "PLEASE", "PLAY", "READY", "GOLF", "KEEP", "PACE", "PLAYER", "MEN",
    "SENIOR", "JUNIORS",
}


class GridParseError(Exception):
    """Raised when the grid structure cannot be recovered; caller falls back."""


# ---------------------------------------------------------------------------
# Stage 1 — rectification
# ---------------------------------------------------------------------------

def _order_quad(pts):
    """Order 4 points as top-left, top-right, bottom-right, bottom-left."""
    pts = np.array(pts, dtype=np.float32)
    s = pts.sum(axis=1)
    d = np.diff(pts, axis=1).ravel()
    return np.array([pts[np.argmin(s)], pts[np.argmin(d)],
                     pts[np.argmax(s)], pts[np.argmax(d)]], dtype=np.float32)


def find_card_homography(image):
    """Find the scorecard quadrilateral and return (H, out_w, out_h).

    Returns (None, w, h) when no plausible card quad is found — callers then
    treat the full frame as the card (identity mapping).
    """
    h, w = image.shape[:2]
    scale = 1000.0 / max(h, w)
    small = cv2.resize(image, None, fx=scale, fy=scale)
    gray = cv2.cvtColor(small, cv2.COLOR_BGR2GRAY)

    # The card is the big bright region; Otsu separates it from dark
    # surroundings (cart wheel, dashboard). Blur first so glare speckle
    # doesn't fragment the contour.
    blur = cv2.GaussianBlur(gray, (5, 5), 0)
    _, thresh = cv2.threshold(blur, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
    thresh = cv2.morphologyEx(thresh, cv2.MORPH_CLOSE, np.ones((9, 9), np.uint8))

    contours, _ = cv2.findContours(thresh, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    if not contours:
        return None, w, h
    biggest = max(contours, key=cv2.contourArea)
    if cv2.contourArea(biggest) < 0.25 * small.shape[0] * small.shape[1]:
        return None, w, h

    peri = cv2.arcLength(biggest, True)
    quad = None
    for eps in (0.02, 0.03, 0.05):
        approx = cv2.approxPolyDP(biggest, eps * peri, True)
        if len(approx) == 4 and cv2.isContourConvex(approx):
            quad = approx.reshape(4, 2)
            break
    if quad is None:
        # Fall back to the minimum-area rectangle around the card blob —
        # handles corners cut off by the frame edge or the clip.
        rect = cv2.minAreaRect(biggest)
        quad = cv2.boxPoints(rect)

    quad = _order_quad(quad / scale)
    tl, tr, br, bl = quad
    out_w = int(max(np.linalg.norm(tr - tl), np.linalg.norm(br - bl)))
    out_h = int(max(np.linalg.norm(bl - tl), np.linalg.norm(br - tr)))
    if out_w < 200 or out_h < 200:
        return None, w, h
    dst = np.array([[0, 0], [out_w - 1, 0], [out_w - 1, out_h - 1],
                    [0, out_h - 1]], dtype=np.float32)
    H = cv2.getPerspectiveTransform(quad, dst)
    return H, out_w, out_h


# ---------------------------------------------------------------------------
# Stage 2 — grid-line detection
# ---------------------------------------------------------------------------

def _line_positions(profile, min_strength, min_gap):
    """Peak-pick a 1-D projection profile into line coordinates."""
    positions = []
    above = profile >= min_strength
    i = 0
    n = len(above)
    while i < n:
        if above[i]:
            j = i
            while j < n and above[j]:
                j += 1
            seg = np.arange(i, j)
            center = int(seg[np.argmax(profile[i:j])])
            if not positions or center - positions[-1] >= min_gap:
                positions.append(center)
            elif profile[center] > profile[positions[-1]]:
                positions[-1] = center
            i = j
        else:
            i += 1
    return positions


def _fill_regular_gaps(positions, axis_len):
    """Insert boundaries where a gap is ~an integer multiple of the local
    median spacing — recovers grid lines hidden by clips, hands, or glare."""
    if len(positions) < 4:
        return positions
    pos = sorted(positions)
    gaps = np.diff(pos)
    med = float(np.median(gaps))
    if med <= 0:
        return pos
    out = [pos[0]]
    for p, g in zip(pos[1:], gaps):
        mult = int(round(g / med))
        if mult >= 2 and abs(g - mult * med) < 0.35 * med:
            for k in range(1, mult):
                out.append(out[-1] + int(round(g / mult)))
        out.append(p)
    return out


def _binarize(gray):
    """Inverted adaptive threshold with large solid blobs removed.

    Solid dark regions (scorecard clip, cart wheel around the card) survive
    a plain inverted threshold as huge white blocks and masquerade as table
    lines; anything thick in both dimensions is not a line, so subtract it.
    """
    binv = cv2.adaptiveThreshold(gray, 255, cv2.ADAPTIVE_THRESH_MEAN_C,
                                 cv2.THRESH_BINARY_INV, 35, 15)
    solid = cv2.morphologyEx(binv, cv2.MORPH_OPEN, np.ones((31, 31), np.uint8))
    solid = cv2.dilate(solid, np.ones((15, 15), np.uint8))
    return cv2.bitwise_and(binv, cv2.bitwise_not(solid))


def _line_segments(gray):
    """Long Hough segments split into horizontal/vertical families.

    Canny + probabilistic Hough rather than directional morphology: tilted
    table lines survive edge detection intact, whereas a 1-px morphological
    kernel erases any line leaning more than a degree or two.
    """
    h, w = gray.shape[:2]
    edges = cv2.Canny(gray, 40, 120)
    edges = cv2.dilate(edges, np.ones((3, 3), np.uint8))
    lines = cv2.HoughLinesP(edges, 1, np.pi / 360, threshold=120,
                            minLineLength=min(h, w) // 8, maxLineGap=15)
    h_segs, v_segs = [], []
    if lines is None:
        return h_segs, v_segs
    for x1, y1, x2, y2 in lines.reshape(-1, 4):
        ang = abs(float(np.degrees(np.arctan2(y2 - y1, x2 - x1))))
        if ang <= 30:
            h_segs.append((x1, y1, x2, y2))
        elif ang >= 60:
            v_segs.append((x1, y1, x2, y2))
    return h_segs, v_segs


def _vanishing_point(segs):
    """Least-squares vanishing point (homogeneous) of a segment family:
    the direction minimizing length-weighted distance to every line."""
    if len(segs) < 3:
        return None
    L, ws = [], []
    for x1, y1, x2, y2 in segs:
        l = np.cross([x1, y1, 1.0], [x2, y2, 1.0])
        n = float(np.hypot(l[0], l[1]))
        if n < 1e-9:
            continue
        L.append(l / n)
        ws.append(float(np.hypot(x2 - x1, y2 - y1)))
    if len(L) < 3:
        return None
    L = np.array(L)
    ws = np.array(ws)
    M = (L * ws[:, None]).T @ L
    _, evecs = np.linalg.eigh(M)
    return evecs[:, 0]


def _refine_rectification(warped_gray):
    """Metric rectification from the table's own vanishing points.

    The card-outline warp is only as good as the detected quad (clips,
    pavement, and cut-off corners routinely pollute it); the printed grid is
    the ground truth. Map the two line families' vanishing points to
    infinity, then rotate/shear so they align with the image axes, and scale
    the result back onto the original canvas.
    """
    h, w = warped_gray.shape[:2]
    identity = np.eye(3, dtype=np.float32)

    h_segs, v_segs = _line_segments(warped_gray)
    v_h = _vanishing_point(h_segs)
    v_v = _vanishing_point(v_segs)
    if v_h is None or v_v is None:
        return identity

    # Projective part: send the vanishing line to infinity.
    linf = np.cross(v_h, v_v)
    if abs(linf[2]) < 1e-12:
        return identity
    linf = linf / linf[2]
    Hp = np.array([[1.0, 0, 0], [0, 1.0, 0], [linf[0], linf[1], 1.0]])

    # Affine part: align the (now parallel) families with the axes.
    dh = Hp @ v_h
    dv = Hp @ v_v
    B = np.array([[dh[0], dv[0]], [dh[1], dv[1]]])
    if abs(np.linalg.det(B)) < 1e-12:
        return identity
    A = np.eye(3)
    A[:2, :2] = np.linalg.inv(B)
    H = A @ Hp

    # Similarity part: undo any flip, then fit the warped corners back onto
    # a canvas of the original size.
    corners = np.array([[0, 0], [w, 0], [w, h], [0, h]], np.float32).reshape(-1, 1, 2)
    tc = cv2.perspectiveTransform(corners, H.astype(np.float32)).reshape(-1, 2)
    if tc[1][0] < tc[0][0]:          # x axis flipped
        H = np.diag([-1.0, 1.0, 1.0]) @ H
        tc[:, 0] *= -1
    if tc[3][1] < tc[0][1]:          # y axis flipped
        H = np.diag([1.0, -1.0, 1.0]) @ H
        tc[:, 1] *= -1
    min_xy = tc.min(axis=0)
    span = tc.max(axis=0) - min_xy
    if span[0] < 1 or span[1] < 1:
        return identity
    scale = min(w / span[0], h / span[1])
    T = np.array([[scale, 0, -min_xy[0] * scale],
                  [0, scale, -min_xy[1] * scale],
                  [0, 0, 1.0]])
    H = T @ H

    # Sanity: refuse corrections that collapse or wildly distort the frame.
    tc2 = cv2.perspectiveTransform(corners, H.astype(np.float32)).reshape(-1, 2)
    area = cv2.contourArea(tc2.astype(np.float32))
    if area < 0.2 * w * h:
        return identity
    return H.astype(np.float32)


def detect_grid(warped_gray):
    """Rectify residual tilt from the table lines, then find them.

    Returns (H_refine, col_xs, row_ys): the 3x3 refinement transform plus
    sorted vertical-line x and horizontal-line y coordinates in refined
    space. Raises GridParseError when no plausible table is present.
    """
    h, w = warped_gray.shape[:2]
    H_refine = _refine_rectification(warped_gray)
    refined = cv2.warpPerspective(warped_gray, H_refine, (w, h),
                                  flags=cv2.INTER_LINEAR, borderValue=255)
    binv = _binarize(refined)

    horiz = cv2.morphologyEx(binv, cv2.MORPH_OPEN,
                             cv2.getStructuringElement(cv2.MORPH_RECT, (max(20, w // 30), 1)))
    vert = cv2.morphologyEx(binv, cv2.MORPH_OPEN,
                            cv2.getStructuringElement(cv2.MORPH_RECT, (1, max(20, h // 30))))

    row_profile = horiz.sum(axis=1) / 255.0   # per-y count of line pixels
    col_profile = vert.sum(axis=0) / 255.0    # per-x count of line pixels

    # A real table line spans a decent fraction of the card even when
    # partially occluded (vertical lines only span the table body, so the
    # bar is lower for them).
    row_ys = _line_positions(row_profile, min_strength=0.25 * w, min_gap=max(10, h // 120))
    col_xs = _line_positions(col_profile, min_strength=0.12 * h, min_gap=max(10, w // 160))

    row_ys = _fill_regular_gaps(row_ys, h)
    col_xs = _fill_regular_gaps(col_xs, w)

    if len(row_ys) < 6 or len(col_xs) < 12:
        raise GridParseError(
            f"table lines not found (rows={len(row_ys)}, cols={len(col_xs)})")
    return H_refine, col_xs, row_ys


# ---------------------------------------------------------------------------
# Stage 3 — symbol → cell assignment
# ---------------------------------------------------------------------------

def map_symbols(symbols, H):
    """Project OCR symbol centroids into rectified-card coordinates and drop
    near-duplicate emissions (Vision frequently returns the same glyph twice
    with slightly offset boxes — even for printed digits, which then read as
    multi-digit cells and break semantic labeling)."""
    if not symbols:
        return []
    pts = np.array([[[s['x'], s['y']]] for s in symbols], dtype=np.float32)
    if H is not None:
        pts = cv2.perspectiveTransform(pts, H)
    out = []
    for s, p in zip(symbols, pts):
        m = dict(s)
        m['wx'] = float(p[0][0])
        m['wy'] = float(p[0][1])
        # True duplicate emissions sit almost exactly on top of each other;
        # a wider tolerance would merge legitimate repeated digits ("116").
        dup = next((i for i, t in enumerate(out)
                    if t['text'] == m['text']
                    and abs(t['wx'] - m['wx']) < 12
                    and abs(t['wy'] - m['wy']) < 12), None)
        if dup is None:
            out.append(m)
        elif m['conf'] > out[dup]['conf']:
            out[dup] = m
    return out


def _interval_index(boundaries, v):
    """Index of the interval [boundaries[i], boundaries[i+1]) containing v.
    -1 before the first line, len-1 after the last."""
    lo, hi = 0, len(boundaries) - 1
    if v < boundaries[0]:
        return -1
    if v >= boundaries[-1]:
        return len(boundaries) - 1
    while lo + 1 < hi:
        mid = (lo + hi) // 2
        if boundaries[mid] <= v:
            lo = mid
        else:
            hi = mid
    return lo


def build_cell_matrix(mapped_symbols, col_xs, row_ys):
    """Bucket symbols into cells[(row_idx, col_idx)] -> [symbols sorted by x]."""
    cells = {}
    for s in mapped_symbols:
        r = _interval_index(row_ys, s['wy'])
        c = _interval_index(col_xs, s['wx'])
        cells.setdefault((r, c), []).append(s)
    for key in cells:
        cells[key].sort(key=lambda s: s['wx'])
    return cells


def _cell_text(cells, r, c):
    return ''.join(s['text'] for s in cells.get((r, c), []))


def _row_text(cells, r, n_cols):
    return ' '.join(filter(None, (_cell_text(cells, r, c) for c in range(-1, n_cols))))


# ---------------------------------------------------------------------------
# Stage 4 — semantic labeling
# ---------------------------------------------------------------------------

def _letters_of(syms):
    return ''.join(s['text'] for s in syms if s['text'].isalpha()).upper()


def _text_lines(mapped_symbols, page_height):
    """Cluster rectified symbols into printed text lines by y-proximity.

    Text lines survive where grid rows fail: half-height tee rows and
    JPEG-softened separators routinely merge grid rows, but each printed
    line keeps its own baseline after rectification.
    """
    if not mapped_symbols:
        return []
    thresh = max(12, page_height * 0.012)
    syms = sorted(mapped_symbols, key=lambda s: s['wy'])
    lines = [[syms[0]]]
    for s in syms[1:]:
        if s['wy'] - lines[-1][-1]['wy'] < thresh:
            lines[-1].append(s)
        else:
            lines.append([s])
    return [sorted(l, key=lambda s: s['wx']) for l in lines]


def _find_par_row(mapped_symbols, col_xs, row_ys, page_height):
    """Locate the topmost PAR text line and read its digits per grid column.

    Returns (row_idx, {col_idx: (value, conf)}, subtotal_cols). Rows come
    from the line's own y (mapped into the grid-row index for band math);
    columns come from the detected vertical lines.
    """
    n_cols = len(col_xs) - 1
    for line in _text_lines(mapped_symbols, page_height):
        txt = _letters_of(line)
        if not txt.startswith('PAR') or txt.startswith('PART'):
            continue
        by_col = {}
        for s in line:
            if not s['text'].isdigit():
                continue
            c = _interval_index(col_xs, s['wx'])
            by_col.setdefault(c, []).append(s)
        par_cells = {}
        multi_cols = []
        for c, digs in by_col.items():
            joined = ''.join(d['text'] for d in sorted(digs, key=lambda s: s['wx']))
            if len(joined) == 1 and 3 <= int(joined) <= 6:
                par_cells[c] = (int(joined), digs[0]['conf'])
            elif len(joined) > 1:
                multi_cols.append(c)
        if len(par_cells) >= 9:
            mid_y = sorted(s['wy'] for s in line)[len(line) // 2]
            row_idx = _interval_index(row_ys, mid_y)
            return row_idx, par_cells, multi_cols
    return None, None, None


def _find_label_row(cells, n_rows, n_cols, word):
    """Topmost row whose left-side letters start with `word`."""
    for r in range(n_rows):
        for c in range(-1, min(6, n_cols)):
            if _letters_of(cells.get((r, c), [])).startswith(word):
                return r
    return None


def label_structure(cells, col_xs, row_ys, mapped_symbols, page_height):
    """Identify hole columns, subtotal columns, and structural rows.

    Returns a dict with: par_row, handicap_row, hole_cols (ordered col
    indices), out_col, in_col, tot_col, pars (list per hole), n_rows, n_cols.
    """
    n_rows = len(row_ys) - 1
    n_cols = len(col_xs) - 1

    par_row, par_cells, multi_cols = _find_par_row(
        mapped_symbols, col_xs, row_ys, page_height)
    if par_row is None:
        raise GridParseError("PAR row not found in grid")

    hole_cols = sorted(par_cells.keys())
    if len(hole_cols) > 18:
        hole_cols = hole_cols[:18]

    # Subtotal columns: multi-digit par-row cells (36/36/72) that sit between
    # or after the hole columns.
    out_col = in_col = tot_col = None
    if len(hole_cols) >= 10:
        # OUT separates the two nines: first multi col after hole 9's column.
        ninth = hole_cols[8]
        tenth = hole_cols[9]
        between = [c for c in multi_cols if ninth < c < tenth]
        out_col = between[0] if between else None
    after = [c for c in multi_cols if c > hole_cols[-1]]
    if after:
        in_col = after[0]
        tot_col = after[1] if len(after) > 1 else None

    handicap_row = _find_label_row(cells, n_rows, n_cols, 'HANDICAP')

    pars = [par_cells[c][0] for c in hole_cols]

    return {
        'par_row': par_row, 'par_cells': par_cells, 'handicap_row': handicap_row,
        'hole_cols': hole_cols, 'out_col': out_col, 'in_col': in_col,
        'tot_col': tot_col, 'pars': pars, 'n_rows': n_rows, 'n_cols': n_cols,
    }


# ---------------------------------------------------------------------------
# Stage 5 — player rows + per-cell scores
# ---------------------------------------------------------------------------

def _is_player_name(name):
    if not name or len(name) < 2 or not name.isalpha():
        return False
    if name in STRUCTURAL_LABELS:
        return False
    return not any(name.startswith(l) for l in STRUCTURAL_LABELS if len(l) >= 3)


def _dedup_cell_digits(digs, x_tol=25):
    """Vision often double-emits a handwritten digit; keep the best copy."""
    out = []
    for s in digs:
        dup = next((i for i, t in enumerate(out)
                    if s['text'] == t['text'] and abs(s['wx'] - t['wx']) < x_tol), None)
        if dup is None:
            out.append(s)
        elif s['conf'] > out[dup]['conf']:
            out[dup] = s
    return out


def extract_players(cells, structure):
    """Find player rows in the scoring band and read their per-hole scores.

    A player row has handwritten letters in the label area. Handwriting
    straddles printed lines, so a nameless digits row adopts the name from an
    adjacent row when that row has no digits of its own (the severed-name
    case that killed row-chaining parsers).
    """
    hole_cols = structure['hole_cols']
    first_hole_col = hole_cols[0]
    band_start = (structure['handicap_row'] + 1
                  if structure['handicap_row'] is not None
                  else structure['par_row'] + 1)

    row_info = {}
    for r in range(band_start, structure['n_rows']):
        letters = []
        for c in range(-1, first_hole_col):
            letters.extend(s for s in cells.get((r, c), []) if s['text'].isalpha())
        letters.sort(key=lambda s: s['wx'])
        name = ''.join(s['text'] for s in letters).upper()
        name = ''.join(ch for ch in name if ch.isalpha())
        digit_count = sum(
            1 for c in hole_cols for s in cells.get((r, c), []) if s['text'].isdigit())
        row_info[r] = {'name': name if _is_player_name(name) else None,
                       'digits': digit_count}

    # Stop the band at the next structural row (Red Tees / Par / Date...).
    stop_rows = set()
    for r in range(band_start, structure['n_rows']):
        for c in range(-1, min(6, structure['n_cols'])):
            txt = _letters_of(cells.get((r, c), []))
            if any(txt.startswith(l) for l in ('RED', 'PAR', 'HANDICAP', 'DATE',
                                               'SCORER', 'PLEASE')) and txt:
                stop_rows.add(r)
    band_end = min(stop_rows) if stop_rows else structure['n_rows']

    players = []
    used = set()
    for r in range(band_start, band_end):
        info = row_info.get(r)
        if not info or r in used:
            continue
        rows_for_player = [r]
        name = info['name']
        if name and info['digits'] < 3:
            # Name row with no scores — adopt an adjacent digits-only row.
            for nb in (r - 1, r + 1):
                nbi = row_info.get(nb)
                if (nbi and nb not in used and not nbi['name']
                        and nbi['digits'] >= 3 and band_start <= nb < band_end):
                    rows_for_player.append(nb)
                    break
        elif not name:
            continue

        used.update(rows_for_player)
        holes = []
        for idx, c in enumerate(hole_cols):
            digs = [s for rr in rows_for_player
                    for s in cells.get((rr, c), []) if s['text'].isdigit()]
            digs = _dedup_cell_digits(sorted(digs, key=lambda s: s['wx']))
            strokes, conf, flagged = None, 0.0, False
            valid = [d for d in digs if 1 <= int(d['text']) <= 15]
            if len(valid) == 1:
                strokes, conf = int(valid[0]['text']), valid[0]['conf']
            elif len(valid) > 1:
                best = max(valid, key=lambda d: d['conf'])
                strokes, conf, flagged = int(best['text']), best['conf'], True
            holes.append({'hole_number': idx + 1, 'par': structure['pars'][idx],
                          'strokes': strokes, 'ocr_confidence': round(conf, 2),
                          'flagged': flagged})

        def _written(col):
            if col is None:
                return None
            digs = [s for rr in rows_for_player
                    for s in cells.get((rr, col), []) if s['text'].isdigit()]
            digs = _dedup_cell_digits(sorted(digs, key=lambda s: s['wx']))
            if not digs:
                return None
            try:
                v = int(''.join(d['text'] for d in digs))
            except ValueError:
                return None
            return v if 18 <= v <= 200 or 25 <= v <= 99 else None

        # A clean 3+ letter name is strong evidence by itself (a player who
        # only recorded a hole or two, e.g. NICK); short names need more
        # digits to rule out stray-mark noise.
        captured = sum(1 for h in holes if h['strokes'] is not None)
        if captured < (1 if len(name) >= 3 else 3):
            continue
        players.append({
            'name': name, 'holes': holes,
            'out_written': _written(structure['out_col']),
            'in_written': _written(structure['in_col']),
            'tot_written': _written(structure['tot_col']),
        })
    return players


# ---------------------------------------------------------------------------
# Stage 6 — checksum validation
# ---------------------------------------------------------------------------

def apply_checksums(players):
    """Compare extracted nines against handwritten subtotals; on mismatch,
    flag the lowest-confidence captured hole in that nine."""
    for p in players:
        holes = p['holes']
        front = [h for h in holes if h['hole_number'] <= 9]
        back = [h for h in holes if h['hole_number'] > 9]
        checks = {}
        for label, nine, written in (('out', front, p.get('out_written')),
                                     ('in', back, p.get('in_written'))):
            captured = [h for h in nine if h['strokes'] is not None]
            total = sum(h['strokes'] for h in captured)
            ok = None
            if written is not None and len(captured) == len(nine) and nine:
                ok = (total == written)
                if not ok:
                    worst = min(captured, key=lambda h: h['ocr_confidence'])
                    worst['flagged'] = True
            checks[label] = {'sum': total if captured else None,
                             'written': written, 'ok': ok}
        tot_written = p.get('tot_written')
        all_captured = [h for h in holes if h['strokes'] is not None]
        if tot_written is not None and len(all_captured) == len(holes) and holes:
            checks['total'] = {'sum': sum(h['strokes'] for h in all_captured),
                               'written': tot_written,
                               'ok': sum(h['strokes'] for h in all_captured) == tot_written}
        p['checksums'] = checks
    return players


# ---------------------------------------------------------------------------
# Stage 7 — tee rating/slope extraction
# ---------------------------------------------------------------------------

RATING_SLOPE_RE = re.compile(r'(\d{2})\s*[.,]\s*(\d)\s*/\s*(\d{2,3})')


def extract_tees(mapped_symbols, page_height):
    """Read per-tee rating/slope from the printed `NN.N/NNN` text.

    Works on y-banded text lines rather than grid rows: tee rows are half
    the height of header rows and their separators hide under scorecard
    clips, so grid rows routinely merge them — but after rectification a
    plain y-cluster reproduces each printed line exactly.
    """
    tees = []
    seen = set()
    for line in _text_lines(mapped_symbols, page_height):
        letters = _letters_of(line)
        label = next((t.title() for t in TEE_LABELS if letters.startswith(t)), None)
        if not label or label in seen:
            continue
        joined = ''.join(s['text'] for s in line)
        matches = list(RATING_SLOPE_RE.finditer(joined))
        if not matches:
            continue
        m = matches[-1]  # rating/slope is the rightmost numeric run
        rating = float(f"{m.group(1)}.{m.group(2)}")
        slope = int(m.group(3))
        if 55 <= rating <= 85 and 55 <= slope <= 155:
            seen.add(label)
            tees.append({'name': label, 'rating': rating, 'slope': slope})
    return tees


# ---------------------------------------------------------------------------
# Public entry point
# ---------------------------------------------------------------------------

def parse_scorecard_grid(image_bytes, symbols, page_width, page_height):
    """Parse a scorecard photo using printed-grid structure.

    `symbols` is the Vision symbol list ({text, x, y, conf}) from the SAME
    image bytes. Returns {'players', 'pars', 'tees', 'debug'}; raises
    GridParseError when the grid cannot be recovered (caller falls back to
    the legacy symbol parser).
    """
    arr = np.frombuffer(image_bytes, dtype=np.uint8)
    image = cv2.imdecode(arr, cv2.IMREAD_COLOR)
    if image is None:
        raise GridParseError("image decode failed")

    H1, out_w, out_h = find_card_homography(image)
    if H1 is not None:
        warped = cv2.warpPerspective(image, H1, (out_w, out_h))
    else:
        warped = image
        out_h, out_w = image.shape[:2]
    warped_gray = cv2.cvtColor(warped, cv2.COLOR_BGR2GRAY)

    H_refine, col_xs, row_ys = detect_grid(warped_gray)
    H = (H_refine @ H1.astype(np.float64)).astype(np.float32) if H1 is not None \
        else H_refine
    mapped = map_symbols(symbols, H)
    cells = build_cell_matrix(mapped, col_xs, row_ys)

    structure = label_structure(cells, col_xs, row_ys, mapped,
                                len(row_ys) and row_ys[-1] or page_height)
    players = extract_players(cells, structure)
    players = apply_checksums(players)
    tees = extract_tees(mapped, len(row_ys) and row_ys[-1] or page_height)

    return {
        'players': players,
        'pars': structure['pars'],
        'tees': tees,
        'debug': {'homography': H.tolist(),
                  'warped_size': (out_w, out_h),
                  'col_xs': col_xs, 'row_ys': row_ys,
                  'structure': {k: structure[k] for k in
                                ('par_row', 'handicap_row', 'hole_cols',
                                 'out_col', 'in_col', 'tot_col')}},
    }
