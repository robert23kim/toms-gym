"""run.py <stem> [--device mps|cpu] [--reprompt-every N] [--no-sam] [--no-refine] [--no-gates]

Loop-2 experiment 'lane-gated-ball' (stage: ball). Re-walks the ball track frame by frame with hard lane-coordinate
gates on top of the loop-1 sam2-video track (the coarse candidate source):
  * camera model: ORB + RANSAC homography chain (loop-1 cam-diff Motion), used for the prediction when a frame has
    no lane quad and for the camera-compensated overlay;
  * prediction: constant velocity in lane coordinates (board, depth ratio s) from the last two accepted points,
    mapped back through the loop-1 per-frame quad of the current frame;
  * gates on every candidate: <= LAT_BOARDS boards lateral change vs the prediction, inside the lane mask + 0.5 board
    (a gutter candidate is kept only when the previous accepted point was already at/over the edge), radius within
    [R_LO, R_HI] x the geometric prior, image jump <= 4 r + 40 px;
  * radius prior: ball diameter 8.5 in = 7.78 board units -> r_geo = 0.5 * 7.78 * lane_width_px(row) / 38 from the
    quad (within ~1 px of the truth r at the deck on dev); 0.8 x the SAM r where there is no quad;
  * far-end refinement (r_geo <= R_FAR px): purple disc-minus-annulus matched filter at r_geo inside a window around
    the gated candidate (or the prediction when nothing survived), distance-penalised; the SAM mask centroid is
    bloated into dark surroundings at the deck (185331: 8-12 px off, r 14 vs 8);
  * SAM 2 re-prompt on a 2x far-end crop from the gated prediction when the coarse source has no accepted candidate
    (--reprompt-every N forces one every N frames in the far window);
  * output: tracks/<stem>.json in the loop-1 tracks format (SOURCE frames) + boards{} from the loop-1 quads at the
    ball centre row, lane_top_down, "stage": "ball", and overlays/final__<stem>.jpg.
"""
import argparse, json, math, os, sys, time
import cv2, numpy as np

L1 = '/Users/toka/code/toms_gym/docs/research/2026-10-10-glasses-pov-tracking'
L2 = '/Users/toka/code/toms_gym/docs/research/2026-11-07-glasses-pov-hook'
X = os.path.join(L2, 'experiments', 'lane-gated-ball')
sys.path.insert(0, L1)
sys.path.insert(0, os.path.join(L1, 'experiments', 'cam-diff'))
sys.path.insert(0, os.path.join(L1, 'experiments', 'sam2-video'))
from camdiff import Motion  # noqa: E402
from lane_geom import lane_point, depth_ratio, image_point, fit_ft_model, edge_x, pin_row  # noqa: E402

BALL_UNITS = 7.78        # 8.5 in / (41.5 / 38 in per board unit)
LAT_BOARDS = 3.0         # max lateral change per frame vs the prediction
LANE_LO, LANE_HI = 0.5, 39.5
R_LO, R_HI = 0.4, 2.2    # candidate r / r_geo (the SAM r is 1.2-1.9x bloated at the deck)
R_FAR = 16.0             # refinement runs where the prior radius is at most this
R_GATE = 20.0            # lane gates + geometric prior only once the quad says r <= this (second half of the roll)
QUAD_SMOOTH = 0.10       # the quad's pin-deck row may move at most this fraction of its span per frame to be trusted
REFINE_MIN_RESP, REFINE_MAX_ANN = 0.40, 0.35
DIST_PEN = 0.015         # response penalty per px from the window centre
COAST_MAX = 3
PIN_TAIL = 4
SAM_CROP_SIDE, SAM_CROP_SCALE, SAM_SPAN = 320, 2, 6
LANE_SEG_START = 8       # quads before release+8 are carried through the head swing and are not trusted (loop-1 rule)


def load_cut(stem):
    return {c['stem']: c for c in json.load(open(os.path.join(L1, 'work', 'cuts', 'cuts.json')))}[stem]


def read_frames(path):
    cap = cv2.VideoCapture(path)
    out = []
    while True:
        ok, im = cap.read()
        if not ok:
            break
        out.append(im)
    return out


def lane_width(q, y):
    return abs(edge_x(q['fl_l'], q['pd_l'], y) - edge_x(q['fl_r'], q['pd_r'], y))


def r_geo(q, y):
    return 0.5 * BALL_UNITS * lane_width(q, y) / 38.0


def to_lane(q, x, y):
    b, _ = lane_point(q, x, y)
    s = depth_ratio(q, y)
    return (None, None) if b is None or s is None else (b, s)


def from_lane(q, b, s):
    p = image_point(q, b, 60.0 * s, 60.0, 0.0)
    return p


def purple(hsv, sat=30):
    return ((hsv[..., 0] >= 112) & (hsv[..., 0] <= 170) & (hsv[..., 1] >= sat)).astype(np.float32)


def disc_kernel(r):
    k = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (2 * r + 1, 2 * r + 1)).astype(np.float32)
    return k / k.sum()


def refine(im, x, y, r, win):
    """Argmax of (purple inside a disc of radius r) - (purple in the annulus r..1.7r), minus DIST_PEN * px from (x, y),
    inside the square window +-win. Returns (cx, cy, resp, inner, annulus, dist) or None."""
    H, W = im.shape[:2]
    ri, ro = max(3, int(round(r))), int(round(1.7 * r)) + 1
    pad = win + ro + 2
    x0, y0, x1, y1 = int(max(0, x - pad)), int(max(0, y - pad)), int(min(W, x + pad + 1)), int(min(H, y + pad + 1))
    if x1 - x0 < 2 * ro + 3 or y1 - y0 < 2 * ro + 3:
        return None
    pm = purple(cv2.cvtColor(im[y0:y1, x0:x1], cv2.COLOR_BGR2HSV))
    inner = cv2.filter2D(pm, -1, disc_kernel(ri))
    outer = cv2.filter2D(pm, -1, disc_kernel(ro))
    ai, ao = math.pi * ri * ri, math.pi * ro * ro
    ann = (outer * ao - inner * ai) / max(1.0, ao - ai)
    Y, Xg = np.mgrid[y0:y1, x0:x1]
    dist = np.hypot(Xg - x, Y - y)
    resp = inner - ann - DIST_PEN * dist
    resp[(np.abs(Xg - x) > win) | (np.abs(Y - y) > win)] = -9
    yy, xx = np.unravel_index(np.argmax(resp), resp.shape)
    if resp[yy, xx] <= -9:
        return None
    d = (Xg - (xx + x0)) ** 2 + (Y - (yy + y0)) ** 2 <= ri * ri
    w = pm * d
    if w.sum() > 0:
        cx, cy = float((w * Xg).sum() / w.sum()), float((w * Y).sum() / w.sum())
    else:
        cx, cy = float(xx + x0), float(yy + y0)
    return cx, cy, float(inner[yy, xx] - ann[yy, xx]), float(inner[yy, xx]), float(ann[yy, xx]), float(dist[yy, xx])


def sam_reprompt(frames, k0, x, y, r, device, work, k_end, log):
    """SAM 2 propagation on a 2x crop around (x, y) from cut frame k0 for SAM_SPAN frames. Returns {k: (x, y, r)}."""
    from sam_track import propagate
    H, W = frames[0].shape[:2]
    side = SAM_CROP_SIDE
    x0 = int(min(max(0, x - side / 2), W - side))
    y0 = int(min(max(0, y - side / 2), H - side))
    ke = min(k_end, k0 + SAM_SPAN)
    crops = [cv2.resize(f[y0:y0 + side, x0:x0 + side], (side * SAM_CROP_SCALE, side * SAM_CROP_SCALE),
                        interpolation=cv2.INTER_CUBIC) for f in frames[:ke + 1]]
    rr = max(r, 5.0) * 1.3
    box = [(x - rr - x0) * SAM_CROP_SCALE, (y - rr - y0) * SAM_CROP_SCALE, (x + rr - x0) * SAM_CROP_SCALE, (y + rr - y0) * SAM_CROP_SCALE]
    box = [max(0, min(side * SAM_CROP_SCALE - 1, v)) for v in box]
    raw = propagate(crops, k0, box, device=device, work_dir=work, tag=f'rp{k0}', log=log, k_end=ke)
    out = {}
    for k, (cx, cy, cr, ca) in raw.items():
        edge = min(cx, cy, side * SAM_CROP_SCALE - cx, side * SAM_CROP_SCALE - cy)
        if edge < 2 * cr + 4:
            continue
        out[k] = (x0 + cx / SAM_CROP_SCALE, y0 + cy / SAM_CROP_SCALE, cr / SAM_CROP_SCALE)
    return out


def compose(motion, s, t):
    """Homography taking frame s pixels onto frame t pixels through the chain (identity where a pair failed)."""
    Hm = np.eye(3)
    if s < t:
        for u in range(s + 1, t + 1):
            if motion.H[u] is not None:
                Hm = motion.H[u] @ Hm
    else:
        for u in range(s, t, -1):
            if motion.H[u] is not None:
                Hm = np.linalg.inv(motion.H[u]) @ Hm
    return Hm


def apply_h(Hm, x, y):
    p = Hm @ np.array([x, y, 1.0])
    return float(p[0] / p[2]), float(p[1] / p[2])


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('stem')
    ap.add_argument('--device', default='mps')
    ap.add_argument('--base', default=None, help='coarse track json (default loop-1 results/tracks/<stem>.json)')
    ap.add_argument('--reprompt-every', type=int, default=0)
    ap.add_argument('--no-sam', action='store_true')
    ap.add_argument('--no-refine', action='store_true')
    ap.add_argument('--no-gates', action='store_true')
    ap.add_argument('--tag', default='')
    args = ap.parse_args()
    log = lambda *a, **k: print(*a, **k, flush=True)  # noqa: E731
    t_start = time.time()
    cut = load_cut(args.stem)
    base = json.load(open(args.base or os.path.join(L1, 'results', 'tracks', f'{args.stem}.json')))
    off = cut['cut_start']
    frames = read_frames(cut['cut_path'])
    k_rel, k_pin = cut['release_frame'] - off, cut['pin_hit_frame'] - off
    k_end = min(len(frames) - 1, k_pin + PIN_TAIL)
    lanes = base.get('lane') or {}
    bpts = {int(p['f']) - off: (float(p['x']), float(p['y']), float(p['r'])) for p in base['frames']}
    log(f'{args.stem}: {len(frames)} cut frames, release k={k_rel}, pin k={k_pin}, base {len(bpts)} points, {len(lanes)} quads')
    t0 = time.time()
    motion = Motion(frames)
    meta = {'device': args.device, 'base_method': base.get('method'), 'base_wall_s': (base.get('meta') or {}).get('wall_s'),
            'orb_s': round(time.time() - t0, 1), 'orb_failed_pairs': sum(1 for h in motion.H[1:] if h is None),
            'gates': {'lateral': 0, 'lane': 0, 'radius': 0, 'jump': 0}, 'refined': 0, 'refine_rejected': 0,
            'coasted': 0, 'sam_reprompts': 0, 'sam_candidates_used': 0, 'cut_start': off,
            'params': {'LAT_BOARDS': LAT_BOARDS, 'R_LO': R_LO, 'R_HI': R_HI, 'R_FAR': R_FAR, 'R_GATE': R_GATE, 'QUAD_SMOOTH': QUAD_SMOOTH, 'REFINE_MIN_RESP': REFINE_MIN_RESP,
                       'REFINE_MAX_ANN': REFINE_MAX_ANN, 'DIST_PEN': DIST_PEN, 'reprompt_every': args.reprompt_every,
                       'no_sam': args.no_sam, 'no_refine': args.no_refine, 'no_gates': args.no_gates}}
    work = os.path.join(X, 'work', args.stem)
    os.makedirs(work, exist_ok=True)

    def quad(k):
        return lanes.get(str(k + off)) if k >= k_rel + LANE_SEG_START else None

    acc = []           # accepted (k, x, y, r, conf, src)
    sam_extra = {}     # k -> (x, y, r) from re-prompts
    coast = 0
    last_reprompt = -99
    k_first = min(bpts) if bpts else k_rel
    events = []

    def trusted(k, y):
        """The quad at k is usable for the ball at row y: at/after release+8, the row inside the quad's span, the ball
        already small (r_geo <= R_GATE: the carried quad is garbage through the head swing, 185331 f304-310 has its
        pin-deck row at 20, 208, 392, 37, -75 px) and the quad smooth against the previous frame's."""
        q = quad(k)
        if q is None or y is None:
            return None
        fl_y, pd_y = 0.5 * (q['fl_l'][1] + q['fl_r'][1]), 0.5 * (q['pd_l'][1] + q['pd_r'][1])
        span = fl_y - pd_y
        if span <= 10 or not (pd_y - 0.1 * span <= y <= fl_y + 0.3 * span) or r_geo(q, y) > R_GATE:
            return None
        qp = quad(k - 1)
        if qp is not None:
            pd_p = 0.5 * (qp['pd_l'][1] + qp['pd_r'][1])
            wr = lane_width(q, pd_y) / max(1e-6, lane_width(qp, pd_p))
            if abs(pd_y - pd_p) > QUAD_SMOOTH * span or not (0.85 <= wr <= 1.18):
                return None
        return q

    for k in range(k_first, k_end + 1):
        real = [a for a in acc if a[5] != 'coast']
        y_ref = bpts[k][1] if k in bpts else (real[-1][2] if real else None)
        q = trusted(k, y_ref)
        # ---- prediction: lane-coordinate line fit over the last 4 real points when their quads are trusted,
        #      else constant velocity through the homography chain
        pred, pred_b, pred_src = None, None, None
        if len(real) >= 3 and q is not None:
            lp = []
            for kk, xx, yy, _, _, _ in real[-4:]:
                qq = trusted(kk, yy)
                if qq is None:
                    lp = []
                    break
                b, sv = to_lane(qq, xx, yy)
                if b is None:
                    lp = []
                    break
                lp.append((kk, b, sv))
            if len(lp) >= 3:
                ks = np.array([v[0] for v in lp], float)
                A = np.c_[ks - ks[-1], np.ones_like(ks)]
                (vb, b1), *_ = np.linalg.lstsq(A, np.array([v[1] for v in lp]), rcond=None)
                (vs, s1), *_ = np.linalg.lstsq(A, np.array([v[2] for v in lp]), rcond=None)
                dt = k - ks[-1]
                pb, ps = b1 + vb * dt, s1 + vs * dt
                p = from_lane(q, pb, ps)
                if p is not None:
                    pred, pred_b, pred_src = p, pb, 'lane'
        if pred is None and len(real) >= 2:
            (k0, x0, y0, _, _, _), (k1, x1, y1, _, _, _) = real[-2], real[-1]
            ax, ay = apply_h(compose(motion, k1, k), x1, y1)
            bx, by = apply_h(compose(motion, k0, k), x0, y0)
            dt = (k - k1) / (k1 - k0)
            pred, pred_src = (ax + (ax - bx) * dt, ay + (ay - by) * dt), 'homography'
        elif pred is None and len(real) == 1:
            k1, x1, y1 = real[-1][0], real[-1][1], real[-1][2]
            pred, pred_src = apply_h(compose(motion, k1, k), x1, y1), 'homography'
        gap = (k - real[-1][0]) if real else 1
        # ---- radius prior
        if q is not None and y_ref is not None:
            rp, rp_src = r_geo(q, y_ref), 'geo'
        elif k in bpts:
            rp, rp_src = 0.8 * bpts[k][2], 'sam'
        else:
            rp, rp_src = (real[-1][3] if real else 10.0), 'carry'
        # ---- candidates: coarse (loop-1) point, then SAM re-prompt extras
        cands = []
        if k in bpts:
            cands.append(('base',) + bpts[k])
        if k in sam_extra:
            cands.append(('sam',) + sam_extra[k])
        far = rp <= R_FAR
        if (not args.no_sam) and far and pred is not None and k <= k_pin and (
                (not cands and k - last_reprompt >= 2) or (args.reprompt_every and k - last_reprompt >= args.reprompt_every)):
            ex = sam_reprompt(frames, k, pred[0], pred[1], rp, args.device, work, k_end, log)
            meta['sam_reprompts'] += 1
            last_reprompt = k
            for kk, v in ex.items():
                sam_extra.setdefault(kk, v)
            if k in ex:
                cands.append(('sam',) + ex[k])
        # ---- gates
        chosen = None
        for src, cx, cy, cr in cands:
            if args.no_gates or pred is None:
                chosen = (src, cx, cy, cr)
                break
            if rp_src == 'geo' and not (R_LO * rp <= cr <= R_HI * rp):
                meta['gates']['radius'] += 1
                events.append((k + off, src, 'radius', round(cr, 1), round(rp, 1)))
                continue
            dj = math.hypot(cx - pred[0], cy - pred[1])
            if dj > (4 * rp + 40) * gap:
                meta['gates']['jump'] += 1
                events.append((k + off, src, 'jump', round(dj, 1)))
                continue
            if pred_src == 'lane':
                cb = to_lane(q, cx, cy)[0]
                if cb is not None:
                    if abs(cb - pred_b) > LAT_BOARDS * gap:
                        meta['gates']['lateral'] += 1
                        events.append((k + off, src, 'lateral', round(cb, 2), round(pred_b, 2)))
                        continue
                    if not (LANE_LO <= cb <= LANE_HI):
                        pq = trusted(real[-1][0], real[-1][2])
                        pbv = to_lane(pq, real[-1][1], real[-1][2])[0] if pq else None
                        if pbv is None or 1.0 <= pbv <= 39.0:
                            meta['gates']['lane'] += 1
                            events.append((k + off, src, 'lane', round(cb, 2)))
                            continue
            chosen = (src, cx, cy, cr)
            break
        # ---- far-end refinement
        if far and not args.no_refine and (chosen is not None or pred is not None):
            cx, cy = (chosen[1], chosen[2]) if chosen is not None else pred
            win = max(2.0 * rp, 12.0)
            rf = refine(frames[k], cx, cy, rp, win)
            ok = rf is not None and rf[2] >= REFINE_MIN_RESP and rf[4] <= REFINE_MAX_ANN
            if ok and pred_src == 'lane':
                rb = to_lane(q, rf[0], rf[1])[0]
                if rb is not None and abs(rb - pred_b) > LAT_BOARDS * gap:
                    ok = False
                    meta['gates']['lateral_refined'] = meta['gates'].get('lateral_refined', 0) + 1
                    events.append((k + off, 'refine', 'lateral', round(rb, 2), round(pred_b, 2)))
            if ok:
                src = (chosen[0] if chosen else 'pred') + '+refine'
                chosen = (src, rf[0], rf[1], rp)
                meta['refined'] += 1
            else:
                meta['refine_rejected'] += 1
        if chosen is None:
            if pred is not None and coast < COAST_MAX:
                coast += 1
                meta['coasted'] += 1
                acc.append((k, pred[0], pred[1], rp, 0.2, 'coast'))
                continue
            if pred is not None:
                log(f'  track ends at k={k} (src {k + off}): {COAST_MAX} coasts')
                break
            continue
        coast = 0
        conf = 1.0 if 'refine' in chosen[0] else 0.8 if chosen[0] == 'base' else 0.6
        if chosen[0].startswith('sam'):
            meta['sam_candidates_used'] += 1
        acc.append((k, chosen[1], chosen[2], chosen[3], conf, chosen[0]))
    meta['events'] = events[:60]
    meta['stage_wall_s'] = round(time.time() - t_start, 1)
    meta['wall_s'] = round(meta['stage_wall_s'] + (meta['base_wall_s'] or 0.0), 1)
    # ---- boards from the loop-1 quads at the ball centre row; final board = median of the last 5 boards <= pin hit
    boards, lane_out = {}, {}
    for k, x, y, r, conf, src in acc:
        q = lanes.get(str(k + off))
        if q is None:
            continue
        b, _ = lane_point(q, x, y)
        if b is not None:
            boards[str(k + off)] = round(b, 2)
        lane_out[str(k + off)] = q
    on = [(k, boards[str(k + off)]) for k, x, y, r, c, s in acc if str(k + off) in boards and k <= k_pin]
    final_board = float(np.median([b for _, b in on[-5:]])) if on else None
    tr = {'stem': args.stem, 'method': 'lane-gated-ball', 'stage': 'ball',
          'frames': [{'f': k + off, 'x': round(x, 1), 'y': round(y, 1), 'r': round(r, 1), 'conf': round(c, 2), 'src': s}
                     for k, x, y, r, c, s in acc],
          'lane': lane_out, 'boards': boards, 'final_board': None if final_board is None else round(final_board, 2),
          'release_frame': cut['release_frame'], 'pin_hit_frame': cut['pin_hit_frame'], 'meta': meta}
    add_top_down(tr)
    out = os.path.join(X, 'tracks', f'{args.stem}{args.tag}.json')
    json.dump(tr, open(out, 'w'), indent=1)
    overlay(frames, cut, tr, base, motion, os.path.join(X, 'overlays', f'final__{args.stem}{args.tag}.jpg'))
    srcs = {}
    for a in acc:
        srcs[a[5]] = srcs.get(a[5], 0) + 1
    log(f'wrote {out}: {len(acc)} frames, final board {tr["final_board"]}, gates {meta["gates"]}, refined {meta["refined"]}, '
        f'sources {srcs}, reprompts {meta["sam_reprompts"]}, stage wall {meta["stage_wall_s"]}s')


def add_top_down(tr):
    lanes = tr.get('lane') or {}
    rel, pin = tr.get('release_frame'), tr.get('pin_hit_frame')
    samples = []
    for p in tr['frames']:
        q = lanes.get(str(p['f']))
        if q and rel <= p['f'] <= pin:
            s = depth_ratio(q, p['y'])
            b = lane_point(q, p['x'], p['y'])[0]
            if s is not None and s <= 1.05 and b is not None and 0.5 <= b <= 39.5:
                samples.append((p['f'], s))
    model = fit_ft_model(samples, rel)
    out = []
    for p in tr['frames']:
        q = lanes.get(str(p['f']))
        if not q:
            continue
        b, ft = lane_point(q, p['x'], p['y'], model['a'], model['b'])
        if b is None or ft is None:
            continue
        on = bool(0.5 <= b <= 39.5 and 0.0 <= ft <= 60.5)
        zone = ('behind_foul' if ft < 0 else 'past_pins' if ft > 60.5 else 'gutter_r' if b < 0.5 else 'gutter_l' if b > 39.5 else 'lane')
        out.append({'f': p['f'], 'board': round(b, 2), 'ft': round(ft, 2), 'on_lane': on, 'zone': zone})
    tr['lane_top_down'] = out
    tr['lane_top_down_model'] = model


def overlay(frames, cut, tr, base, motion, out_path):
    """pin_hit-4 frame: the whole track warped into it through the homography chain (green, this run; grey, loop-1),
    the quad's lane edges (cyan), the board read at the pin row, and a top-down panel (board vs ft)."""
    off = cut['cut_start']
    kt = max(0, min(len(frames) - 1, cut['pin_hit_frame'] - 4 - off))
    im = frames[kt].copy()
    H, W = im.shape[:2]
    f = kt + off
    q = (tr.get('lane') or {}).get(str(f))
    if q:
        vp_y = None
        pts = np.array([q['fl_l'], q['pd_l'], q['pd_r'], q['fl_r']], np.int32)
        cv2.polylines(im, [pts], True, (255, 255, 0), 2)
        py = pin_row(q)
        cv2.line(im, (int(edge_x(q['fl_l'], q['pd_l'], py)), int(py)), (int(edge_x(q['fl_r'], q['pd_r'], py)), int(py)), (0, 255, 255), 2)

    def warped(points):
        pl = []
        for p in points:
            k = p['f'] - off
            if k < 0 or k >= len(frames) or p['f'] > cut['pin_hit_frame'] + 1:
                continue
            x, y = apply_h(compose(motion, k, kt), p['x'], p['y'])
            if 0 <= x < W and 0 <= y < H:
                pl.append((int(x), int(y)))
        return pl
    bl = warped(base.get('frames') or [])
    if len(bl) > 1:
        cv2.polylines(im, [np.array(bl, np.int32)], False, (160, 160, 160), 2)
    pl = warped(tr['frames'])
    if len(pl) > 1:
        cv2.polylines(im, [np.array(pl, np.int32)], False, (60, 220, 60), 3)
    for p in tr['frames']:
        k = p['f'] - off
        if p['f'] >= cut['pin_hit_frame'] - 12 and p['f'] <= cut['pin_hit_frame']:
            x, y = apply_h(compose(motion, k, kt), p['x'], p['y'])
            cv2.circle(im, (int(x), int(y)), max(2, int(p['r'])), (0, 140, 255) if 'refine' in p.get('src', '') else (255, 0, 255), 1)
    pin_read = None
    for p in reversed(tr['frames']):
        if p['f'] <= cut['pin_hit_frame'] and str(p['f']) in tr['boards']:
            pin_read = (p['f'], tr['boards'][str(p['f'])])
            break
    m = tr['meta']
    txt = [f"lane-gated-ball {tr['stem']} f{f}", f"final board {tr['final_board']}  last read f{pin_read[0] if pin_read else '-'}: {pin_read[1] if pin_read else '-'}",
           f"gates {m['gates']}  refined {m['refined']}  reprompts {m['sam_reprompts']}", f"green: this track (cam-compensated)  grey: loop-1 sam2-video"]
    for i, t in enumerate(txt):
        cv2.putText(im, t, (16, 50 + 44 * i), cv2.FONT_HERSHEY_SIMPLEX, 1.1, (0, 0, 0), 6)
        cv2.putText(im, t, (16, 50 + 44 * i), cv2.FONT_HERSHEY_SIMPLEX, 1.1, (255, 255, 255), 2)
    im = cv2.resize(im, (W // 2, H // 2))
    Hs, Ws = im.shape[0], 240
    strip = np.full((Hs, Ws, 3), (70, 160, 215), np.uint8)
    top, bot = 40, Hs - 30
    X_of = lambda b: int(20 + (Ws - 40) * (39 - min(max(b, -1.0), 41.0)) / 38)  # noqa: E731
    Y_of = lambda ft: int(bot - (bot - top) * min(max(ft, 0.0), 62.0) / 60)  # noqa: E731
    for bd in (5, 10, 15, 20, 25, 30, 35):
        cv2.drawMarker(strip, (X_of(bd), Y_of(15)), (40, 40, 40), cv2.MARKER_TRIANGLE_UP, 8, 2)
    for b in (20.0, 14.5, 25.5, 9.0, 31.0, 3.5, 36.5):
        cv2.circle(strip, (X_of(b), Y_of(60)), 4, (255, 255, 255), -1)
    for bd in (1, 10, 20, 30, 39):
        cv2.putText(strip, str(bd), (X_of(bd) - 8, Hs - 8), cv2.FONT_HERSHEY_SIMPLEX, 0.45, (20, 20, 20), 1)
    td = [p for p in tr.get('lane_top_down') or [] if p['f'] <= cut['pin_hit_frame'] and p['zone'] in ('lane', 'gutter_r', 'gutter_l')]
    tp = [(X_of(p['board']), Y_of(p['ft'])) for p in td]
    if len(tp) > 1:
        cv2.polylines(strip, [np.array(tp, np.int32)], False, (150, 40, 150), 2)
    cv2.putText(strip, 'board vs ft', (10, 24), cv2.FONT_HERSHEY_SIMPLEX, 0.55, (20, 20, 20), 1)
    if tr.get('final_board') is not None:
        cv2.putText(strip, f"b{tr['final_board']:g}", (10, Hs - 40), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 0), 2)
    cv2.imwrite(out_path, np.hstack([im, strip]))


if __name__ == '__main__':
    main()
