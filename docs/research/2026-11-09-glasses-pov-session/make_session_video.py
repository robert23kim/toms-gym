import json, subprocess, os, sys
import numpy as np, cv2
S = os.path.dirname(os.path.abspath(__file__))
CLIPS = '/Users/toka/pov-2026-11-08/drive_raw'
FF = '/opt/homebrew/bin/ffmpeg'
VIDEO_ONLY = sorted(s for s, v in json.load(open(f'{S}/results/judged_final.json'))['stems'].items() if not v['pass'])
W, H, FPS = 1920, 1080, 30
GREY = (95, 95, 95); GREEN = (90, 220, 90); MAG = (200, 60, 200); AMB = (40, 170, 255); CYAN = (255, 230, 80)
EXITC = (60, 240, 255); WHITE = (255, 255, 255)
DECK0, DECK1, FTMAX = 60.0, 62.6, 64.6     # head pin 60 ft, back row 62.6 ft, then the pit
def J(p): return json.load(open(p))
def runmed(v, w=5):
    h = w // 2
    return [float(np.median(v[max(0, i - h):i + h + 1])) for i in range(len(v))]

LX, LW, LTOP, LH = 230, 360, 100, 860
BW = 12.0 / (41.5 / 38)  # board units between neighbouring pins: back row 7/8/9/10 on 36.48/25.49/14.51/3.52
def lxy(board, ft):
    b = min(max(board, -3.0), 42.0)  # inside the gutter bands
    return int(LX + LW * (39 - b) / 38), int(LTOP + LH * (1 - min(max(ft, 0), FTMAX) / FTMAX))
# pin-deck zoom inset: boards across, 58.5..64.6 ft up
IX, IW, ITOP, IH, IFT0 = 636, 270, 112, 250, 58.5
def ixy(board, ft):
    b = min(max(board, -3.0), 42.0)
    return int(IX + 20 + (IW - 40) * (39 - b) / 38), int(ITOP + IH * (1 - (min(max(ft, IFT0), FTMAX) - IFT0) / (FTMAX - IFT0)))
PINS = [(20.0 + (k - row / 2) * BW, DECK0 + 0.866 * row) for row in range(4) for k in range(row + 1)]
def draw_pin(im, xy, r):
    cv2.circle(im, xy, r, (238, 238, 238), -1, cv2.LINE_AA)
    cv2.circle(im, xy, r, (60, 60, 60), 1, cv2.LINE_AA)
    cv2.circle(im, xy, max(2, int(r * 0.42)), (40, 40, 215), 2, cv2.LINE_AA)
def draw_pin_ell(im, xy, rx, ry):
    cv2.ellipse(im, xy, (rx, ry), 0, 0, 360, (238, 238, 238), -1, cv2.LINE_AA)
    cv2.ellipse(im, xy, (rx, ry), 0, 0, 360, (60, 60, 60), 1, cv2.LINE_AA)
    cv2.ellipse(im, xy, (max(2, int(rx * 0.42)), max(1, int(ry * 0.42))), 0, 0, 360, (40, 40, 215), 1, cv2.LINE_AA)
PIN_R, PIN_RI, PIN_RZ = 18, 13, 22   # lane panel draws pins as 20 x 5 px ellipses: depth is compressed (11.5 px row pitch)   # pin ~4.8 in wide = 4.5 boards: main lane, inset, recap zoom
def deck_bands(im, xy, x0, x1, lane_l, lane_r):
    """lane wood to 60 ft, pin deck 60-62.6 ft (lighter band, edges), pit after (dark)."""
    y60, y626, ytop = xy(20, DECK0)[1], xy(20, DECK1)[1], xy(20, FTMAX)[1]
    cv2.rectangle(im, (lane_l, y626), (lane_r, y60), (160, 205, 235), -1)
    cv2.rectangle(im, (x0, ytop), (x1, y626), (18, 18, 18), -1)
    cv2.line(im, (lane_l, y60), (lane_r, y60), (230, 230, 230), 1)
    cv2.line(im, (lane_l, y626), (lane_r, y626), (230, 230, 230), 1)
def base(inset=True):
    im = np.full((H, 960, 3), 24, np.uint8)
    cv2.rectangle(im, (LX - 36, LTOP), (LX + LW + 36, LTOP + LH), (45, 45, 45), -1)
    cv2.rectangle(im, (LX, LTOP), (LX + LW, LTOP + LH), (120, 175, 215), -1)
    for b in range(2, 39):
        x = LX + int(LW * (39 - b) / 38); cv2.line(im, (x, lxy(20, DECK0)[1]), (x, LTOP + LH), (105, 160, 200), 1)
    deck_bands(im, lxy, LX - 36, LX + LW + 36, LX, LX + LW)
    fl = LTOP + LH
    cv2.line(im, (LX - 36, fl), (LX + LW + 36, fl), (255, 255, 255), 3)
    for i, bd in enumerate([5.4, 10.3, 15.1, 20.0, 24.9, 29.7, 34.6]):
        x, y = lxy(bd, 12.5 + (3 - abs(3 - i)) * 1.0)
        cv2.polylines(im, [np.array([[x - 7, y + 9], [x, y], [x + 7, y + 9]])], False, (60, 60, 60), 2)
    for bd, ft in PINS:
        draw_pin_ell(im, lxy(bd, ft), 20, 5)
    for ft in (0, 15, 30, 45, 60):
        y = lxy(20, ft)[1]
        cv2.line(im, (LX - 36, y), (LX - 30, y), (200, 200, 200), 1)
        cv2.putText(im, f'{ft} ft', (LX - 86, y + 5), 0, 0.5, (200, 200, 200), 1, cv2.LINE_AA)
    cv2.putText(im, 'pit', (LX - 70, lxy(20, 63.8)[1] + 5), 0, 0.45, (150, 150, 150), 1, cv2.LINE_AA)
    cv2.putText(im, 'foul line', (LX + LW + 50, fl + 4), 0, 0.5, (160, 160, 160), 1, cv2.LINE_AA)
    for b in range(5, 40, 5):
        cv2.putText(im, str(b), (LX + int(LW * (39 - b) / 38) - 9, fl + 32), 0, 0.5, (210, 210, 210), 1, cv2.LINE_AA)
    cv2.putText(im, 'board (1 = right gutter side)', (LX - 40, fl + 58), 0, 0.5, (150, 150, 150), 1, cv2.LINE_AA)
    if not inset: return im
    il, ir = ixy(39, 60)[0], ixy(1, 60)[0]
    cv2.rectangle(im, (IX, ITOP), (IX + IW, ITOP + IH), (45, 45, 45), -1)
    cv2.rectangle(im, (il, ixy(20, DECK0)[1]), (ir, ITOP + IH), (120, 175, 215), -1)
    deck_bands(im, ixy, IX, IX + IW, il, ir)
    for bd, ft in PINS:
        draw_pin(im, ixy(bd, ft), PIN_RI)
    cv2.rectangle(im, (IX, ITOP), (IX + IW, ITOP + IH), (120, 120, 120), 1)
    cv2.putText(im, 'pin deck zoom', (IX + 4, ITOP - 6), 0, 0.5, (200, 200, 200), 1, cv2.LINE_AA)
    for ft, lab in ((DECK0, '60 ft'), (DECK1, '62.6')):
        cv2.putText(im, lab, (IX + IW + 4, ixy(20, ft)[1] + 4), 0, 0.38, (170, 170, 170), 1, cv2.LINE_AA)
    cv2.putText(im, 'pit', (IX + IW + 4, ixy(20, 63.8)[1] + 4), 0, 0.38, (170, 170, 170), 1, cv2.LINE_AA)
    return im
BASE = base()
BASE_PLAIN = base(inset=False)
def bx(board): return int(LX + LW * (39 - min(max(board, -3.0), 42.0)) / 38)
def interp(fr, f):
    if f in fr: return fr[f] + (False,)
    lo = [k for k in fr if k < f and f - k <= 6]; hi = [k for k in fr if k > f and k - f <= 6]
    if not lo or not hi: return None
    a, b = max(lo), min(hi); w = (f - a) / (b - a)
    return tuple(fr[a][i] * (1 - w) + fr[b][i] * w for i in range(3)) + (True,)
def card(lines):
    im = np.full((H, W, 3), 20, np.uint8)
    for i, (s, sc) in enumerate(lines):
        (tw, _), _ = cv2.getTextSize(s, 0, sc, 2)
        cv2.putText(im, s, ((W - tw) // 2, 400 + i * 90), 0, sc, (240, 240, 240), 2, cv2.LINE_AA)
    return im
def txt(im, s, xy, sc, col, th=1): cv2.putText(im, s, xy, 0, sc, col, th, cv2.LINE_AA)
def dotted(im, pts, col, r=2, step=7):
    for (x0, y0), (x1, y1) in zip(pts, pts[1:]):
        d = max(1.0, float(np.hypot(x1 - x0, y1 - y0)))
        for t in np.arange(0, d, step):
            cv2.circle(im, (int(x0 + (x1 - x0) * t / d), int(y0 + (y1 - y0) * t / d)), r, col, -1, cv2.LINE_AA)
def bstr(b): return 'gutter' if b < 0.5 else ('left gutter' if b > 39.5 else 'board %.1f' % b)
def inr(b): return 0.5 <= b <= 39.5
def hl(b, gut): return bstr(b) if gut else (('board %.1f' % b) if inr(b) else 'edge read, board %.1f' % b)
def dring(im, xy, r, col, th=2):
    for a in range(0, 360, 30): cv2.ellipse(im, xy, (r, r), 0, a, a + 16, col, th, cv2.LINE_AA)
def btxt(im, s_, xy, sc, col, th=1):
    (tw, th_), _ = cv2.getTextSize(s_, 0, sc, th)
    x, y = xy
    ov = im.copy(); cv2.rectangle(ov, (x - 6, y - th_ - 6), (x + tw + 6, y + 7), (12, 12, 12), -1)
    cv2.addWeighted(ov, 0.8, im, 0.2, 0, im)
    cv2.putText(im, s_, xy, 0, sc, col, th, cv2.LINE_AA)
def deflection(entry, ex):
    d = ex - entry
    if abs(d) <= 1.5: return 'through the pocket' if 15.0 <= entry <= 19.5 else 'straight through'
    return 'deflected left' if d > 0 else 'deflected right'

def J(p): return json.load(open(p))
CUTS = {c['stem']: c for c in J(f'{S}/work/cuts/cuts.json')}
SMAP = J(f'{S}/results/session_map.json')['rows']
JF = J(f'{S}/results/judged_final.json')['stems']
RULE_TXT = {'J1': 'ball not tracked on 85% of the roll', 'J2': 'pin row not detected (fallback only)', 'J3': 'entry board off the lane',
            'J4': 'board series not smooth', 'J5': 'lane edges missing', 'T-entry': 'entry off hand truth', 'T-pinrow': 'pin row off hand truth'}
def reason(stem):
    rf = (JF.get(stem[9:15]) or JF.get(stem) or {}).get('rules_failed') or []
    if not rf:
        for k, v in JF.items():
            if stem.startswith('20261108_' + k): rf = v.get('rules_failed') or []
    return ['failed ' + ', '.join(rf) if rf else 'judge failed']+[RULE_TXT.get(r, r) for r in rf]
def tkey(stem): return stem[9:15]
recs = []
for m in SMAP:
    recs.append(m)
groups = {}
for m in recs:
    g, b = m['game'], m['bowler']
    key = ('unassigned',) if g == 0 or not b else (g, b)
    groups.setdefault(key, []).append(m)
order = sorted([k for k in groups if k[0] != 'unassigned'], key=lambda k: (k[0], min(x['stem'] for x in groups[k])))
if ('unassigned',) in groups: order.append(('unassigned',))
for k in groups: groups[k].sort(key=lambda m: (m['frame'], m['stem']))

pr_ = None
FRD = f'{S}/work/session_frames'; os.makedirs(FRD, exist_ok=True)
for f_ in os.listdir(FRD): os.remove(f'{FRD}/{f_}')
SIL = f'{S}/work/session_video_silent.mp4'
pr_ = subprocess.Popen([FF, '-y', '-loglevel', 'error', '-f', 'rawvideo', '-pix_fmt', 'bgr24', '-s', f'{W}x{H}', '-r', str(FPS),
    '-i', '-', '-c:v', 'libx264', '-crf', '18', '-pix_fmt', 'yuv420p', SIL], stdin=subprocess.PIPE)
def put(im, n=1):
    for _ in range(n): pr_.stdin.write(im.tobytes())
segs = []      # ('sil', nframes) | ('clip', path, ss_seconds, nframes)
def sil(n): segs.append(('sil', n))
def tag(im, s, xy, col=MAG):
    (tw, th), _ = cv2.getTextSize(s, 0, 0.5, 1)
    x, y = xy
    cv2.rectangle(im, (x - tw // 2 - 4, y - th - 4), (x + tw // 2 + 4, y + 4), (20, 20, 20), -1)
    cv2.rectangle(im, (x - tw // 2 - 4, y - th - 4), (x + tw // 2 + 4, y + 4), col, 1)
    txt(im, s, (x - tw // 2, y), 0.5, WHITE, 1)
ZX, ZW, ZTOP, ZH = 1040, 560, 150, 430
def zxy(board, ft):
    b = min(max(board, -3.0), 42.0)
    return int(ZX + 40 + (ZW - 80) * (39 - b) / 38), int(ZTOP + ZH * (1 - (min(max(ft, IFT0), FTMAX) - IFT0) / (FTMAX - IFT0)))

def wrap(s, n):
    out, cur = [], ''
    for w in s.split():
        if len(cur) + len(w) + 1 > n: out.append(cur); cur = w
        else: cur = (cur + ' ' + w).strip()
    return out + [cur]

def render_throw(m, lab, gtxt, timeline, tcur):
    stem = m['stem']; c = CUTS[stem]; rel = c['release_frame']; cutpin = c['pin_hit_frame']; cs = c['cut_start']
    vo = stem in VIDEO_ONLY
    unc = m['bowler_confidence'] < 0.7
    head = f"{gtxt} frame {lab}" if m['frame'] else gtxt
    row = dict(lab=lab, stem6=tkey(stem), vo=None, line=[], deck=[], entry=None, ex_b=None, ex_ft=None, kind=None, gutter=False,
               hooker=False, bp=None, defl='', g_from=None, edge=False, extrap=False, reach=False, nothrow=False)
    f0 = rel - 5
    if vo:
        rs = reason(stem); row['vo'] = rs
        f1 = min(c['cut_end'], cutpin + 10); tags = {f0: 'start', cutpin: 'exit'}
        fr = {}; pr = cutpin; ev = {}; last_real = None; gutter = False; hooker = False; detected = False
        line2 = []; deck = []; s2 = []; entry = None; ex_f = None
    else:
        t2 = J(f'{S}/results/tracks/{stem}.json'); ev = t2['events']; pr = ev['pin_row_frame_est']
        ftcv = lambda f: 60.0 * (f - rel) / (pr - rel)  # noqa: E731
        last_real = ev['track_last_real_frame']
        fr = {p['f']: (p['x'], p['y'], p['r']) for p in t2['frames'] if p['f'] <= (last_real or 0)}
        ex_f, ex_b, entry = ev['exit_frame'], ev['exit_board'], ev['entry_board']
        decoy = ev.get('deck_decoy_from')
        bd = {int(k): v for k, v in t2['boards'].items()}
        s2 = [(k, bd[k], ftcv(k)) for k in sorted(bd) if rel <= k <= pr and ftcv(k) >= 1.5]
        l2 = runmed([b for _, b, _ in s2])
        line2 = [(s2[j][0], l2[j], s2[j][2]) for j in range(len(s2))]
        deck = [(d_['f'], d_['board'], d_['ft_deck']) for d_ in ev.get('deck_points') or [] if d_['f'] > pr]
        ex_ft = ev.get('exit_ft_deck') or DECK1; kind = ev.get('exit_kind')
        gutter = (entry is not None and entry < 0.5) or (entry is None and bool(line2) and line2[-1][1] < 0.5)
        detected = not ev['pin_row_source'].startswith('fallback')
        src_lab = ('pin motion - 2' if ev['pin_row_source'].startswith('pin motion')
                   else 'extrapolated crossing' if 'extrapolated crossing' in ev['pin_row_source'] else 'geometric crossing')
        g_from = None
        if gutter:
            for j in range(len(line2)):
                if all(b < 0.5 for _, b, _ in line2[j:]): g_from = line2[j]; break
        brk = (not gutter) and ev['breakpoint_frame'] is not None and not ev['breakpoint_at_roll_end'] and (ev['rise_after_break'] or 0) >= 2.0
        hooker = brk and inr(ev['breakpoint_board']); edge = brk and not hooker
        lend = line2[-1][2] if line2 else 0.0
        extrap = (not gutter) and entry is not None and (ev.get('entry_n') == 0 or lend < 57.0)
        reach = bool(line2) and lend >= 57.0
        row.update(line=line2, deck=deck, entry=entry, ex_b=ex_b, ex_ft=ex_ft, kind=kind, gutter=gutter, hooker=hooker,
                   bp=(ev['breakpoint_board'], ev['breakpoint_ft']) if hooker else None, defl=ev.get('deflection') or '', g_from=g_from, edge=edge, extrap=extrap, reach=reach)
        endf = ex_f if ex_f is not None else (last_real if last_real is not None else pr)
        f1 = min(c['cut_end'], max(endf, pr, last_real or 0) + 8)
        ex_tag_f = ex_f if ex_f is not None else (last_real + 2 if last_real is not None and not gutter else (last_real or pr))
        if ex_f is None and not gutter: ex_tag_f = min(f1, max(ex_tag_f, pr + 2))
        tags = {f0: 'start', (f0 + pr) // 2: 'mid', pr: 'pinrow', ex_tag_f: 'exit'}
    cap = cv2.VideoCapture(c['cut_path'])
    for _ in range(f0 - cs): cap.read()
    n = 0
    for f in range(f0, f1 + 1):
        ok, img = cap.read()
        if not ok: break
        sc = H / img.shape[0]; im = cv2.resize(img, (int(img.shape[1] * sc), H))
        left = np.full((H, 960, 3), 12, np.uint8); x0 = (960 - im.shape[1]) // 2
        xs = max(0, -x0); left[:, max(0, x0):max(0, x0) + min(960, im.shape[1])] = im[:, xs:xs + min(960, im.shape[1])]
        if not vo:
            p = interp(fr, f)
            if p is not None:
                col = (0, 165, 255) if p[3] else (255, 255, 0)
                cv2.circle(left, (int(x0 + p[0] * sc), int(p[1] * sc)), max(6, int(p[2] * sc)), col, 1, cv2.LINE_AA)
        btxt(left, head, (14, 34), 0.8, WHITE, 2)
        btxt(left, f'clip {tkey(stem)}  f{f}', (14, 68), 0.6, WHITE, 1)
        yy = 98
        if unc:
            btxt(left, 'bowler uncertain (confidence %.1f)' % m['bowler_confidence'], (14, yy + 6), 0.65, AMB, 2); yy += 40
        if vo:
            btxt(left, 'video only: no line drawn', (14, yy + 6), 0.65, AMB, 2)
        else:
            btxt(left, 'cyan = tracked, orange = interpolated', (14, H - 16), 0.55, (200, 200, 200))
            if last_real is not None and f > last_real:
                where = 'in the gutter' if gutter else ('behind the pins' if last_real >= pr - 2 else 'short of the pin row')
                btxt(left, 'tracker loses the ball %s here (last point f%d)' % (where, last_real), (14, yy + 6), 0.6, AMB, 1); yy += 36
            if f == pr:
                btxt(left, ('pin row (%s)' % src_lab) if detected else 'pin row = cut label (nothing detected)', (14, yy + 6), 0.7, CYAN, 2)
        right = BASE.copy()
        if vo:
            cv2.rectangle(right, (636, 400), (936, 400 + 40 + 24 * 6), (40, 40, 40), -1)
            cv2.rectangle(right, (636, 400), (936, 400 + 40 + 24 * 6), AMB, 2)
            txt(right, 'VIDEO ONLY', (648, 430), 0.8, AMB, 2)
            yl = 458
            for ln_ in wrap('the tracker did not pass the judge rules, so no line is drawn.', 34) + [r for r in row['vo'][:1]]:
                txt(right, ln_, (648, yl), 0.45, WHITE, 1); yl += 22
            for r_ in row['vo'][1:]:
                for ln_ in wrap(r_, 34): txt(right, ln_, (648, yl), 0.45, (210, 210, 210), 1); yl += 22
        else:
            pts = [(k, b, ft) for (k, b, ft) in s2 if k <= f]
            ln = [lxy(b, ft) for (k, b, ft) in line2 if k <= f]
            if len(ln) > 1: cv2.polylines(right, [np.array(ln)], False, MAG, 2, cv2.LINE_AA)
            iln = [ixy(b, ft) for (k, b, ft) in line2 if k <= f and ft >= IFT0]
            if len(iln) > 1: cv2.polylines(right, [np.array(iln)], False, MAG, 2, cv2.LINE_AA)
            dk = [(k, b, ft) for (k, b, ft) in deck if k <= f]
            if f >= pr and entry is not None and not gutter:
                dpts = [(entry, DECK0)] + [(b, ft) for (k, b, ft) in dk]
                dotted(right, [lxy(b, ft) for b, ft in dpts], EXITC, 2, 6)
                dotted(right, [ixy(b, ft) for b, ft in dpts], EXITC, 3, 9)
                if extrap: dring(right, lxy(entry, DECK0), 9, CYAN); dring(right, ixy(entry, DECK0), 11, CYAN)
                else:
                    cv2.circle(right, lxy(entry, DECK0), 9, CYAN, 2, cv2.LINE_AA)
                    cv2.circle(right, ixy(entry, DECK0), 11, CYAN, 2, cv2.LINE_AA)
                cv2.rectangle(right, (IX + 2, ITOP + IH - 24), (IX + IW - 2, ITOP + IH - 2), (30, 30, 30), -1)
                txt(right, ('entry %s' % bstr(entry)) + (' (extrap.)' if extrap else ''), (IX + 8, ITOP + IH - 7), 0.5, CYAN, 1)
            cur = None
            if dk and f > pr: cur = dk[-1][1]
            elif pts: cur = pts[-1][1]
            if cur is not None:
                cpt = dk[-1] if (dk and f > pr) else pts[-1]
                cv2.circle(right, lxy(cpt[1], cpt[2]), 7, WHITE, 2, cv2.LINE_AA)
                txt(right, ('last seen: ' + ('off the deck' if not inr(cur) else 'board %.1f' % cur)) if (dk and f > pr and not gutter) else hl(cur, gutter), (30, 40), 1.0, WHITE, 2)
            if edge and f >= ev['breakpoint_frame']:
                txt(right, 'line reads at the lane edge:', (636, 530), 0.5, AMB, 1); txt(right, 'edge read, not a break', (636, 552), 0.5, AMB, 1)
            if hooker and f >= ev['breakpoint_frame']:
                bpx = lxy(ev['breakpoint_board'], ev['breakpoint_ft'])
                cv2.drawMarker(right, bpx, (255, 255, 255), cv2.MARKER_TILTED_CROSS, 14, 2, cv2.LINE_AA)
                bl = 'break %.1f @ %.0f ft' % (ev['breakpoint_board'], ev['breakpoint_ft'])
                (tw, _), _ = cv2.getTextSize(bl, 0, 0.55, 1)
                bxx = bpx[0] - tw - 12 if ev['breakpoint_board'] < 20 else bpx[0] + 12
                cv2.rectangle(right, (bxx - 4, bpx[1] - 14), (bxx + tw + 4, bpx[1] + 8), (40, 40, 40), -1)
                txt(right, bl, (bxx, bpx[1] + 5), 0.55, WHITE, 1)
            if gutter and g_from is not None and f >= g_from[0]:
                txt(right, 'GUTTER BALL, in the gutter from ~%.0f ft' % g_from[2], (30, 80), 0.9, AMB, 2)
            if f >= pr and not gutter and entry is not None:
                txt(right, ('entry at the pin row: board %.1f' % entry) if not extrap else ('entry extrapolated: board %.1f (line ends %.0f ft)' % (entry, lend)), (30, 80), 0.75 if not extrap else 0.6, CYAN, 2)
            if ex_f is not None and f >= ex_f and not gutter:
                for xy_, rr in ((lxy(ex_b, ex_ft), 9), (ixy(ex_b, ex_ft), 13)):
                    cv2.circle(right, xy_, rr + 4, (0, 0, 0), 3, cv2.LINE_AA)
                    cv2.circle(right, xy_, rr, EXITC, -1, cv2.LINE_AA)
                cv2.rectangle(right, (IX, 378), (IX + IW + 40, 470), (40, 40, 40), -1)
                cv2.rectangle(right, (IX, 378), (IX + IW + 40, 470), EXITC, 2)
                exs = ('board %.1f' % ex_b) if inr(ex_b) else 'off the deck'
                txt(right, ('EXIT ' if kind == 'pit' else 'LAST SEEN ') + exs, (IX + 12, 418), 0.75 if kind != 'pit' else 1.0, EXITC, 3 if kind == 'pit' else 2)
                txt(right, row['defl'], (IX + 12, 456), 0.8, EXITC, 2)
                if kind == 'cut_end': txt(right, 'clip ends at f%d (ball still on the deck)' % ex_f, (IX, 496), 0.5, (210, 210, 210), 1)
                elif kind != 'pit': txt(right, 'ball hidden by pins after f%d' % ex_f, (IX, 496), 0.5, (210, 210, 210), 1)
            if ex_f is None and not gutter and last_real is not None and f > last_real:
                cv2.rectangle(right, (IX, 378), (IX + IW + 40, 470), (40, 40, 40), -1)
                cv2.rectangle(right, (IX, 378), (IX + IW + 40, 470), AMB, 2)
                txt(right, 'EXIT not measured', (IX + 12, 418), 0.9, AMB, 2)
                txt(right, 'ball lost at f%d' % last_real, (IX + 12, 448), 0.6, AMB, 1)
            yl = 590
            for s_, col in (('magenta = boards to the pin row', MAG), ('   (5-frame median)', MAG), ('dotted = through the pin deck', EXITC),
                            ('ring = entry at the pin row', CYAN), ('depth = constant speed,', (150, 150, 150)),
                            ('   release 0 ft .. pin row 60 ft', (150, 150, 150)),
                            ('pin row f%d (cut label f%d)' % (pr, cutpin) if detected else 'pin row = cut label f%d' % cutpin, (150, 150, 150)),
                            (('   from %s' % src_lab) if detected else '   (nothing detected)', (150, 150, 150))):
                txt(right, s_, (636, yl), 0.45, col); yl += 24
        txt(right, head + (' (bowler uncertain)' if unc else ''), (30, H - 24), 0.6, (200, 200, 200), 1)
        frame = np.hstack([left, right]); put(frame); n += 1
        if f in tags and tags[f] == 'exit': cv2.imwrite(f'{FRD}/throw_{tkey(stem)}_exit.png', frame)
        if f in tags: cv2.imwrite(f'{S}/work/session_frames_all/{tkey(stem)}_{tags[f]}.png', frame)
    segs.append(('clip', c['cut_path'], (f0 - cs) / FPS, n))
    timeline.append(dict(stem=stem, label=head, bowler=m['bowler'], start_s=round(tcur / FPS, 2), n=n, f0=f0, f1=f1, video_only=vo))
    return row, n

def recap(title, rows, fname, note=None):
    rc = np.full((H, W, 3), 20, np.uint8)
    rc[:, :960] = BASE_PLAIN
    nl = sum(1 for r in rows if r['line']); nt = sum(1 for r in rows if not r['nothrow']); nr_ = sum(1 for r in rows if r['reach'])
    txt(rc, (f'{title}: {len(rows)} clip, no throw' if nt == 0 else f"{title}: {nt} throw{'s' if nt != 1 else ''}, {nl} with a line, {nr_} reaching the pin row"), (30, 50), 0.85, WHITE, 2)
    txt(rc, 'magenta = boards vs depth (5-frame median), ring = entry at the pin row, number = frame', (30, 80), 0.48, (190, 190, 190), 1)
    zl, zr = zxy(39, 60)[0], zxy(1, 60)[0]
    cv2.rectangle(rc, (ZX, ZTOP), (ZX + ZW, ZTOP + ZH), (45, 45, 45), -1)
    cv2.rectangle(rc, (zl, zxy(20, DECK0)[1]), (zr, ZTOP + ZH), (120, 175, 215), -1)
    for b in range(2, 39):
        x = zxy(b, 60)[0]; cv2.line(rc, (x, zxy(20, DECK0)[1]), (x, ZTOP + ZH), (105, 160, 200), 1)
    deck_bands(rc, zxy, ZX, ZX + ZW, zl, zr)
    for bd, ft in PINS: draw_pin(rc, zxy(bd, ft), PIN_RZ)
    cv2.rectangle(rc, (ZX, ZTOP), (ZX + ZW, ZTOP + ZH), (120, 120, 120), 1)
    txt(rc, 'pin deck: entry rings and exit / last-seen dots', (ZX, ZTOP - 12), 0.55, (200, 200, 200), 1)
    for ft, lab_ in ((DECK0, '60 ft'), (DECK1, '62.6')): txt(rc, lab_, (ZX + ZW + 6, zxy(20, ft)[1] + 4), 0.42, (170, 170, 170), 1)
    for b in range(5, 40, 5): txt(rc, str(b), (zxy(b, 60)[0] - 8, ZTOP + ZH + 18), 0.42, (210, 210, 210), 1)
    for j, r in enumerate(rows):
        ln = [lxy(b, ft) for (_, b, ft) in r['line']]
        if len(ln) > 1: cv2.polylines(rc, [np.array(ln)], False, MAG, 2, cv2.LINE_AA)
        if ln:
            ft_j = 6.0 + j * 4.8
            kk = min(range(len(r['line'])), key=lambda q: abs(r['line'][q][2] - ft_j))
            px_ = lxy(r['line'][kk][1], r['line'][kk][2]); tx_ = (LX + LW + 70, px_[1])
            cv2.line(rc, px_, (tx_[0] - 14, tx_[1]), (150, 90, 150), 1, cv2.LINE_AA)
            cv2.circle(rc, px_, 4, MAG, -1, cv2.LINE_AA)
            tag(rc, r['lab'], (tx_[0], tx_[1] + 6))
        if r['entry'] is not None and not r['gutter'] and r['line']:
            dpts = [(r['entry'], DECK0)] + [(b, ft) for (_, b, ft) in r['deck']]
            dotted(rc, [zxy(b, ft) for b, ft in dpts], EXITC, 3, 9)
            ex0 = zxy(r['entry'], DECK0)
            if r['extrap']: dring(rc, lxy(r['entry'], DECK0), 6, CYAN); dring(rc, ex0, 11, CYAN)
            else:
                cv2.circle(rc, lxy(r['entry'], DECK0), 6, CYAN, 2, cv2.LINE_AA)
                cv2.circle(rc, ex0, 11, CYAN, 2, cv2.LINE_AA)
            tag(rc, r['lab'], (ex0[0], ex0[1] + 34 + (j % 3) * 22), CYAN)
            if r['ex_b'] is not None:
                xy_ = zxy(r['ex_b'], r['ex_ft'])
                cv2.circle(rc, xy_, 11, (0, 0, 0), 3, cv2.LINE_AA); cv2.circle(rc, xy_, 8, EXITC, -1, cv2.LINE_AA)
                tag(rc, r['lab'], (xy_[0], xy_[1] - 16 - (j % 3) * 20), EXITC)
    ty = ZTOP + ZH + 60
    cols = [(ZX, 'frame'), (ZX + 60, 'clip'), (ZX + 130, 'entry'), (ZX + 280, 'break'), (ZX + 430, 'exit / last seen'), (ZX + 610, 'through the pins')]
    for x, h_ in cols: txt(rc, h_, (x, ty), 0.5, (170, 170, 170), 1)
    step = min(34, 300 // max(len(rows), 1))
    for j, r in enumerate(rows):
        y = ty + 30 + j * step
        if r['vo']:
            vals = [r['lab'], r['stem6'], 'no throw' if r['nothrow'] else 'video only', '-', '-', '; '.join(r['vo'][:1])[:30]]
            colr = AMB
        elif r['gutter']:
            vals = [r['lab'], r['stem6'], 'gutter', '-', '-', 'gutter ball' + (' from ~%.0f ft' % r['g_from'][2] if r['g_from'] else '')]
            colr = WHITE
        else:
            vals = [r['lab'], r['stem6'], ('%.1f' % r['entry'] + (' extrapolated' if r['extrap'] else '')) if r['entry'] is not None else '-',
                    '%.1f @ %.0f ft' % r['bp'] if r['bp'] else ('edge read' if r['edge'] else 'none'),
                    (('%.1f' % r['ex_b'] if inr(r['ex_b']) else 'off deck') + (' (exit)' if r['kind'] == 'pit' else ' (last seen)')) if r['ex_b'] is not None else 'not measured',
                    r['defl'] or '-']
            colr = WHITE if j % 2 == 0 else (215, 215, 215)
        for (x, _), v in zip(cols, vals): txt(rc, v, (x, y), 0.5, colr, 1)
    if note: txt(rc, note, (ZX, H - 64), 0.45, AMB, 1)
    txt(rc, 'depth = constant speed, release 0 ft to the detected pin row 60 ft; video only = no line, reason in the throw', (ZX, H - 40), 0.42, (160, 160, 160), 1)
    txt(rc, 'exit = last real moving point on the deck; on hookers it reads 3-6 boards short (ball behind pins)', (ZX, H - 18), 0.42, (160, 160, 160), 1)
    cv2.imwrite(f'{FRD}/{fname}', rc)
    return rc

os.makedirs(f'{S}/work/session_frames_all', exist_ok=True)
tl = []; tcur = 0
title = card([('Glasses POV bowling session', 1.6), ('2026-11-08   3 games   Tom and Chardie', 1.0),
              ('ball: motion-only residual chain + SAM 2 fill (partial pick)   lane: per-frame edge   pin row: detected where possible', 0.6),
              ('13 throws are video only: the tracker failed the judge rules, no line drawn', 0.6)])
cv2.imwrite(f'{FRD}/card_title.png', title); put(title, 2 * FPS); sil(2 * FPS); tcur += 2 * FPS
gl = []
for key in order:
    ms = groups[key]
    gname = 'unassigned' if key[0] == 'unassigned' else f'Game {key[0]} {key[1]}'
    gtxt = 'Unassigned' if key[0] == 'unassigned' else f'Game {key[0]} {key[1]}'
    ncl = len(ms); nvo = sum(1 for m in ms if m['stem'] in VIDEO_ONLY)
    t_start = tcur / FPS
    conf = ', '.join(sorted({'%.2f' % m['bowler_confidence'] for m in ms}))
    lines = [(gname, 1.8), ('%d clips, %d with a line, %d video only' % (ncl, ncl - nvo - sum(1 for m in ms if m['stem'] not in CUTS or CUTS[m['stem']].get('cut_start') is None), nvo), 0.9),
             ('bowler from the frames, confidence %s' % conf, 0.7)]
    gc = card(lines); cv2.imwrite(f'{FRD}/card_{gname.replace(" ", "_")}.png', gc); put(gc, int(1.5 * FPS)); sil(int(1.5 * FPS)); tcur += int(1.5 * FPS)
    nfr = {}
    for m in ms: nfr[m['frame']] = nfr.get(m['frame'], 0) + 1
    seen = {}; labs = []
    for m in ms:
        fr_ = m['frame']; seen[fr_] = seen.get(fr_, 0) + 1
        labs.append(str(fr_) + ('abcd'[seen[fr_] - 1] if nfr[fr_] > 1 else ''))
    rows = []
    rec_pos = tcur
    # reserve the recap: render throws into a buffer? recap needs rows first, so pre-compute rows by rendering throws after; use two passes
    gl.append((key, gname, gtxt, ms, labs, t_start))
    # pass 1: compute rows without writing video (dry), then write recap, then throws
    class _Null:
        def write(self, b): pass
    _real = pr_.stdin; pr_.stdin = _Null(); _segs = len(segs); _tl = len(tl)
    dry_rows = []
    for m, lab in zip(ms, labs):
        if m['stem'] not in CUTS or CUTS[m['stem']].get('cut_start') is None:
            dry_rows.append(dict(lab='-', stem6=tkey(m['stem']), vo=['no throw in this clip (2.6 s)'], line=[], deck=[], entry=None, ex_b=None, ex_ft=None, kind=None, gutter=False, hooker=False, bp=None, defl='', g_from=None, edge=False, extrap=False, reach=False, nothrow=True)); continue
        r_, _n = render_throw(m, lab, gtxt, [], 0); dry_rows.append(r_)
        del segs[_segs:]
    pr_.stdin = _real
    rcimg = recap(gtxt, dry_rows, f'recap_{gname.replace(" ", "_")}.png', note=('clip without a throw: ' + ', '.join(tkey(m['stem']) for m in ms if m['stem'] not in CUTS or CUTS[m['stem']].get('cut_start') is None)) if any(m['stem'] not in CUTS or CUTS[m['stem']].get('cut_start') is None for m in ms) else None)
    put(rcimg, 5 * FPS); sil(5 * FPS); tcur += 5 * FPS
    for m, lab in zip(ms, labs):
        if m['stem'] not in CUTS or CUTS[m['stem']].get('cut_start') is None:
            raw = f"{CLIPS}/{m['stem']}.mp4"; cap = cv2.VideoCapture(raw); n = 0
            while True:
                ok, img = cap.read()
                if not ok: break
                sc = H / img.shape[0]; im = cv2.resize(img, (int(img.shape[1] * sc), H))
                left = np.full((H, 960, 3), 12, np.uint8); x0 = (960 - im.shape[1]) // 2
                xs = max(0, -x0); left[:, max(0, x0):max(0, x0) + min(960, im.shape[1])] = im[:, xs:xs + min(960, im.shape[1])]
                btxt(left, f'{gtxt}: no throw in this clip', (14, 34), 0.8, WHITE, 2)
                btxt(left, f'clip {tkey(m["stem"])}  f{n}', (14, 68), 0.6, WHITE, 1)
                btxt(left, 'bowler uncertain (confidence %.1f)' % m['bowler_confidence'], (14, 104), 0.65, AMB, 2)
                right = BASE.copy(); txt(right, 'no throw, nothing to track', (30, 60), 0.9, AMB, 2)
                put(np.hstack([left, right])); n += 1
                if n == 40: cv2.imwrite(f'{FRD}/throw_{tkey(m["stem"])}_exit.png', np.hstack([left, right]))
            segs.append(('clip', raw, 0.0, n)); tl.append(dict(stem=m['stem'], label=gtxt + ' no throw', bowler=m['bowler'], start_s=round(tcur / FPS, 2), n=n, video_only=True)); tcur += n
            continue
        r_, n = render_throw(m, lab, gtxt, tl, tcur); tcur += n

pr_.stdin.close(); pr_.wait()
lst = []
for i, sg in enumerate(segs):
    p = f'{S}/work/session_aud_{i}.m4a'
    if sg[0] == 'sil':
        subprocess.run([FF, '-y', '-loglevel', 'error', '-f', 'lavfi', '-i', 'anullsrc=r=44100:cl=mono', '-t', '%.5f' % (sg[1] / FPS), '-c:a', 'aac', p], check=True)
    else:
        subprocess.run([FF, '-y', '-loglevel', 'error', '-ss', '%.5f' % sg[2], '-t', '%.5f' % (sg[3] / FPS), '-i', sg[1], '-vn', '-af', 'apad', '-ar', '44100', '-ac', '1', '-c:a', 'aac', '-t', '%.5f' % (sg[3] / FPS), p], check=True)
    lst.append(p)
open(f'{S}/work/session_aud_list.txt', 'w').write(''.join(f"file '{x}'\n" for x in lst))
subprocess.run([FF, '-y', '-loglevel', 'error', '-f', 'concat', '-safe', '0', '-i', f'{S}/work/session_aud_list.txt', '-c', 'copy', f'{S}/work/session_aud_all.m4a'], check=True)
subprocess.run([FF, '-y', '-loglevel', 'error', '-i', SIL, '-i', f'{S}/work/session_aud_all.m4a', '-map', '0:v', '-map', '1:a', '-c:v', 'copy', '-c:a', 'aac', '-shortest', f'{S}/session.mp4'], check=True)
for p in lst: os.remove(p)
json.dump({'total_frames': tcur, 'total_s': tcur / FPS, 'timeline': tl, 'groups': [(g[1], len(g[3]), g[5]) for g in gl]}, open(f'{S}/work/session_timeline.json', 'w'), indent=1)
print('total s', tcur / FPS)
for g in gl: print(g[1], len(g[3]), round(g[5], 2))
