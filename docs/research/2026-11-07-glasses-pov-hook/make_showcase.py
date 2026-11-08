import json, subprocess, os
import numpy as np, cv2
L2 = os.path.dirname(os.path.abspath(__file__))
L1 = '/Users/toka/code/toms_gym/docs/research/2026-10-10-glasses-pov-tracking'
HO = '/Users/toka/pov-holdout/2026-11-07-glasses-pov-hook'
FF = '/opt/homebrew/bin/ffmpeg'
DEV = {'20260915_185121_23d80f05', '20260915_185331_19de9ec7', '20260915_185645_9fde3c16', '20260915_185454_f240c883', '20260915_190115_a7cf2c70'}
cuts = [c for c in json.load(open(f'{L1}/work/cuts/cuts.json')) if c.get('cut_start') is not None and '191900' not in c['stem']]
# holdout throws first (the first 10 s must not be in-sample), stem order inside each split; 185121 last only if it has no lane fit
cuts.sort(key=lambda c: (c['stem'] in DEV, c['stem']))
fin = json.load(open(f'{L2}/results/final_v3.json'))
ROWS = {r['stem']: r for r in fin['rows']}
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
PIN_R, PIN_RI, PIN_RZ = 18, 13, 22   # pin ~4.8 in wide = 4.5 boards: main lane, inset, recap zoom
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
        draw_pin(im, lxy(bd, ft), PIN_R)
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
recap_rows = []
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
def deflection(entry, ex):
    d = ex - entry
    if abs(d) <= 1.5: return 'through the pocket' if 15.0 <= entry <= 19.5 else 'straight through'
    return 'deflected left' if d > 0 else 'deflected right'

t0 = J(f"{L2}/results/tracks/{cuts[0]['stem']}.json")
stage_line = 'ball: lane-gated-ball to the end of the cut   lane: per-frame edge lane   pin row: detected   path: none'
out = f'{L2}/work/showcase_silent.mp4'
pr_ = subprocess.Popen([FF, '-y', '-loglevel', 'error', '-f', 'rawvideo', '-pix_fmt', 'bgr24', '-s', f'{W}x{H}', '-r', str(FPS),
    '-i', '-', '-c:v', 'libx264', '-crf', '18', '-pix_fmt', 'yuv420p', out], stdin=subprocess.PIPE)
FR = f'{L2}/work/showcase_frames_v3'; os.makedirs(FR, exist_ok=True)
def put(im, n=1):
    for _ in range(n): pr_.stdin.write(im.tobytes())
title = card([('Glasses POV bowling - loop 2, through the pin deck', 1.5), (stage_line, 0.75), ('2026-11-07', 1.0)])
cv2.imwrite(f'{FR}/card_title.png', title); put(title, 2 * FPS)
timeline = []; tcur = 2.0
for i, c in enumerate(cuts):
    stem = c['stem']; rel = c['release_frame']; cutpin = c['pin_hit_frame']
    t2 = J(f'{L2}/results/tracks/{stem}.json'); t1 = J(f'{L1}/results/tracks/{stem}.json')
    ev = t2['events']; pr = ev['pin_row_frame_est']
    ftcv = lambda f: 60.0 * (f - rel) / (pr - rel)  # noqa: E731
    real = {p['f'] for p in t2['frames'] if p.get('src') != 'coast'}
    fr = {p['f']: (p['x'], p['y'], p['r']) for p in t2['frames'] if p['f'] <= (ev['track_last_real_frame'] or 0)}
    last_real = ev['track_last_real_frame']
    ex_f, ex_b, entry = ev['exit_frame'], ev['exit_board'], ev['entry_board']
    decoy = ev.get('deck_decoy_from')
    bd = {int(k): v for k, v in t2['boards'].items()}
    rawc = {int(k): v for k, v in (t2.get('boards_clean_raw') or {}).items()}
    s2 = [(k, bd[k], ftcv(k)) for k in sorted(bd) if rel <= k <= pr and ftcv(k) >= 1.5]
    l2 = runmed([b for _, b, _ in s2])
    line2 = [(s2[j][0], l2[j], s2[j][2]) for j in range(len(s2))]
    deck = [(d_['f'], d_['board'], d_['ft_deck']) for d_ in ev.get('deck_points') or [] if d_['f'] > pr]
    ex_ft = ev.get('exit_ft_deck') or DECK1
    kind = ev.get('exit_kind')
    d1 = {e['f']: e['board'] for e in t1.get('lane_top_down', []) if e['zone'] in ('lane', 'gutter_r', 'gutter_l')}
    s1 = [(k, d1[k], ftcv(k)) for k in sorted(d1) if rel <= k <= cutpin and ftcv(k) >= 1.5]
    l1 = runmed([b for _, b, _ in s1]); line1 = [(s1[j][0], l1[j], s1[j][2]) for j in range(len(s1))]
    gutter = (entry is not None and entry < 0.5) or (entry is None and bool(line2) and line2[-1][1] < 0.5)
    detected = not ev['pin_row_source'].startswith('fallback')
    src_lab = 'pin motion - 2' if ev['pin_row_source'].startswith('pin motion') else 'geometric crossing'
    g_from = None
    if gutter:
        for j in range(len(line2)):
            if all(b < 0.5 for _, b, _ in line2[j:]):
                g_from = line2[j]; break
    hooker = (not gutter) and ev['breakpoint_frame'] is not None and not ev['breakpoint_at_roll_end'] and (ev['rise_after_break'] or 0) >= 2.0
    recap_rows.append(dict(lab=stem[9:15], split='dev' if stem in DEV else 'HOLDOUT', line=line2, deck=deck, entry=entry, ex_b=ex_b, ex_ft=ex_ft,
                           kind=kind, gutter=gutter, hooker=hooker, bp=(ev['breakpoint_board'], ev['breakpoint_ft']) if hooker else None,
                           defl=ev.get('deflection') or '', g_from=g_from))
    f0 = rel - 5; f1 = min(c['cut_end'], max(pr, last_real or pr) + 8); cs = c['cut_start']
    cap = cv2.VideoCapture(c['cut_path'])
    for _ in range(f0 - cs): cap.read()   # sequential: CAP_PROP_POS_FRAMES seeks one frame late on 185121
    lab = stem[9:15]; split = 'dev' if stem in DEV else 'HOLDOUT'
    ex_tag_f = ex_f if ex_f is not None else (last_real + 2 if last_real is not None and not gutter else last_real)
    tags = {f0: 'start', (f0 + pr) // 2: 'mid', pr: 'pinrow', ex_tag_f: 'exit'}
    n = 0
    for f in range(f0, f1 + 1):
        ok, img = cap.read()
        if not ok: break
        sc = H / img.shape[0]; im = cv2.resize(img, (int(img.shape[1] * sc), H))
        left = np.full((H, 960, 3), 12, np.uint8); x0 = (960 - im.shape[1]) // 2
        xs = max(0, -x0); left[:, max(0, x0):max(0, x0) + min(960, im.shape[1])] = im[:, xs:xs + min(960, im.shape[1])]
        p = interp(fr, f)
        if p is not None:
            col = (0, 165, 255) if p[3] else (255, 255, 0)
            cv2.circle(left, (int(x0 + p[0] * sc), int(p[1] * sc)), max(6, int(p[2] * sc)), col, 1, cv2.LINE_AA)
        txt(left, f'{lab} f{f} {split}', (14, 34), 0.8, WHITE, 2)
        txt(left, 'cyan = tracked, orange = interpolated', (14, H - 16), 0.55, (200, 200, 200))
        if last_real is not None and f > last_real:
            where = 'in the gutter' if gutter else 'behind the pins'
            txt(left, 'tracker loses the ball %s here (last point f%d)' % (where, last_real), (14, 66), 0.6, AMB, 1)
        if f == pr:
            txt(left, ('pin row (%s)' % src_lab) if detected else 'pin row = cut label (nothing detected)', (14, 98), 0.7, CYAN, 2)
        right = BASE.copy()
        p1 = [lxy(b, ft) for (k, b, ft) in line1 if k <= f]
        if len(p1) > 1: cv2.polylines(right, [np.array(p1)], False, GREY, 2, cv2.LINE_AA)
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
            cv2.circle(right, lxy(entry, DECK0), 9, CYAN, 2, cv2.LINE_AA)
            cv2.circle(right, ixy(entry, DECK0), 11, CYAN, 2, cv2.LINE_AA)
            ex0 = ixy(entry, DECK0)
            cv2.rectangle(right, (IX + 2, ITOP + IH - 24), (IX + IW - 2, ITOP + IH - 2), (30, 30, 30), -1)
            txt(right, 'entry %s' % bstr(entry), (IX + 8, ITOP + IH - 7), 0.5, CYAN, 1)
        cur = None
        if dk and f > pr: cur = dk[-1][1]
        elif pts: cur = pts[-1][1]
        if cur is not None:
            cpt = dk[-1] if (dk and f > pr) else pts[-1]
            cv2.circle(right, lxy(cpt[1], cpt[2]), 7, WHITE, 2, cv2.LINE_AA)
            txt(right, bstr(cur), (30, 40), 1.0, WHITE, 2)
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
        if f >= pr:
            if gutter:
                pass
            elif entry is not None:
                txt(right, 'entry at the pin row: board %.1f' % entry, (30, 80), 0.75, CYAN, 2)
        if ex_f is not None and f >= ex_f and not gutter:
            dirw = ev.get('deflection') or ''
            for xy_, rr in ((lxy(ex_b, ex_ft), 9), (ixy(ex_b, ex_ft), 13)):
                cv2.circle(right, xy_, rr + 4, (0, 0, 0), 3, cv2.LINE_AA)
                cv2.circle(right, xy_, rr, EXITC, -1, cv2.LINE_AA)
            cv2.rectangle(right, (IX, 378), (IX + IW + 40, 470), (40, 40, 40), -1)
            cv2.rectangle(right, (IX, 378), (IX + IW + 40, 470), EXITC, 2)
            txt(right, ('EXIT board %.1f' if kind == 'pit' else 'LAST SEEN board %.1f') % ex_b, (IX + 12, 418), 0.75 if kind != 'pit' else 1.0, EXITC, 3 if kind == 'pit' else 2)
            txt(right, dirw, (IX + 12, 456), 0.8, EXITC, 2)
            if kind == 'cut_end':
                txt(right, 'clip ends at f%d (ball still on the deck)' % ex_f, (IX, 496), 0.5, (210, 210, 210), 1)
            elif kind != 'pit':
                txt(right, 'ball hidden by pins after f%d' % ex_f, (IX, 496), 0.5, (210, 210, 210), 1)
            txt(right, 'on hookers the tracker reads 3-6 boards', (IX, 520), 0.42, (170, 170, 170), 1)
            txt(right, 'short of the hand truth (ball behind pins)', (IX, 540), 0.42, (170, 170, 170), 1)
        if ex_f is None and not gutter and last_real is not None and f > last_real:
            cv2.rectangle(right, (IX, 378), (IX + IW + 40, 470), (40, 40, 40), -1)
            cv2.rectangle(right, (IX, 378), (IX + IW + 40, 470), AMB, 2)
            txt(right, 'EXIT not measured', (IX + 12, 418), 0.9, AMB, 2)
            txt(right, 'ball lost at f%d' % last_real, (IX + 12, 448), 0.6, AMB, 1)
            if decoy: txt(right, '(then a static pit patch)', (IX + 12, 466), 0.45, AMB, 1)
        yl = 590
        for s_, col in (('magenta = boards to the pin row', MAG),
                        ('   (5-frame median)', MAG),
                        ('dotted = through the pin deck', EXITC),
                        ('ring = entry at the pin row', CYAN),
                        ('grey = loop 1' + ('' if line1 else ' (no lane fit)'), (150, 150, 150)),
                        ('depth = constant speed,', (150, 150, 150)),
                        ('   release 0 ft .. pin row 60 ft', (150, 150, 150)),
                        ('pin row f%d (cut label f%d)' % (pr, cutpin) if detected else 'pin row = cut label f%d' % cutpin, (150, 150, 150)),
                        (('   from %s' % src_lab) if detected else '   (nothing detected)', (150, 150, 150))):
            if s_: txt(right, s_, (636, yl), 0.45, col)
            yl += 24
        frame = np.hstack([left, right]); put(frame); n += 1
        if f in tags: cv2.imwrite(f'{FR}/throw{i+1}_{lab}_{tags[f]}.png', frame)
    timeline.append((i + 1, stem, round(tcur, 2), round(tcur + n / FPS, 2), n, f0, f1, cs, split)); tcur += n / FPS

M = fin['means']
def mv(split, k):
    v = M[split].get(k) or {}
    return v.get('mean'), v.get('n', 0)
cl = np.full((H, W, 3), 20, np.uint8)
txt(cl, 'Before / after vs hand truth: pin row, entry at the pin row, exit from the deck', (250, 110), 1.05, (240, 240, 240), 2)
rowsdef = [('pin row vs truth 60-ft frame', 'cut_pin_row_err_rederived_truth_only', 'pin_row_err_rederived_truth_only', '', ''),
           ('pin row vs first pin motion', 'cut_contact_err', 'contact_frame_err', '', ''),
           ('entry at pin row (boards)', 'v2_entry_err_pr_rederived_truth_only', 'entry_err_pr_rederived_truth_only', '', ''),
           ('exit / last-seen board (boards)', 'v2_exit_err', 'exit_err', '', '')]
def fmt(v): return '-' if v[0] is None else '%.1f' % v[0]
for x, split, title in ((60, 'holdout', 'HOLDOUT'), (1000, 'dev', 'dev (in-sample)')):
    nmax = max(mv(split, k)[1] for _, _, k, _, _ in rowsdef)
    txt(cl, '%s, truth on %d of 5' % (title, nmax), (x, 190), 0.9, (240, 240, 240), 2)
    txt(cl, 'before', (x + 470, 235), 0.7, (170, 170, 170), 2); txt(cl, 'after', (x + 640, 235), 0.7, GREEN, 2)
    for r, (nm, kb, ka, lb, la) in enumerate(rowsdef):
        y = 285 + r * 58
        txt(cl, nm, (x, y), 0.68, (190, 190, 190), 1)
        if kb: txt(cl, fmt(mv(split, kb)), (x + 470, y), 0.9, (240, 240, 240), 2)
        txt(cl, fmt(mv(split, ka)) + ('  n=%d' % mv(split, ka)[1]), (x + 640, y), 0.9, GREEN, 2)
miss = [s_[9:15] for s_ in fin['truth_missing_pin_row_or_exit']]
hb = {r['stem'][9:15]: r for r in fin['rows']}
notes = [
    'Before = loop 2 as shipped: 60 ft at the hand-cut pin_hit, ball followed to pin_hit+4. After = pin row detected by the tracker, ball followed to the end of the cut.',
    'The board series through the deck agrees with truth (192142 raw 22.2 vs 22.2, 192636 18.2 vs 18.3 at the truth pin-row frame); entry error follows the pin-row frame.',
    'Pin row: geometric crossing on 7, pin motion on 1 (191820, a false hit on the camera whip), cut label on 185121 / 190115. A static pit patch ends the ball track.',
    'Exit = last real moving point on the deck; on hookers it reads 3-6 boards short (ball behind pins). Pin-motion clock (4x baseline) fired on 1 of 10, falsely (191820 camera whip).',
    'Frames: before = hand-cut pin_hit. 60-ft truth = ball bottom at the headpin base row (re-derived on all 10). Exit is scored where observed (not 190115 / 185645).',
    'Release is still a hand-labelled input. The pin-row definition was chosen after seeing 192142 / 192636. All 10 throws have been seen (no fresh holdout).',
    'Truth and tracker share one instrument (purple ball, wood-to-gutter edges): agreement under about 1.5 boards is not established.' +
    ('  Truth pin_row/exit missing: ' + ', '.join(miss) + '.' if miss else '')]
for k, s_ in enumerate(notes): txt(cl, s_, (60, 600 + k * 42), 0.54, (190, 190, 190), 1)
cv2.imwrite(f'{FR}/card_close.png', cl); put(cl, 4 * FPS)

# session recap: every magenta line on one lane, every entry / exit on one pin deck
ZX, ZW, ZTOP, ZH = 1040, 560, 150, 430
def zxy(board, ft):
    b = min(max(board, -3.0), 42.0)
    return int(ZX + 40 + (ZW - 80) * (39 - b) / 38), int(ZTOP + ZH * (1 - (min(max(ft, IFT0), FTMAX) - IFT0) / (FTMAX - IFT0)))
def tag(im, s, xy, col=MAG):
    (tw, th), _ = cv2.getTextSize(s, 0, 0.5, 1)
    x, y = xy
    cv2.rectangle(im, (x - tw // 2 - 4, y - th - 4), (x + tw // 2 + 4, y + 4), (20, 20, 20), -1)
    cv2.rectangle(im, (x - tw // 2 - 4, y - th - 4), (x + tw // 2 + 4, y + 4), col, 1)
    txt(im, s, (x - tw // 2, y), 0.5, WHITE, 1)
rc = np.full((H, W, 3), 20, np.uint8)
rc[:, :960] = BASE_PLAIN
txt(rc, 'Session recap: %d throws, every line to the pin row' % len(recap_rows), (30, 50), 0.85, WHITE, 2)
txt(rc, 'magenta = boards vs depth (5-frame median), ring = entry at the pin row, number = throw order in this video', (30, 80), 0.48, (190, 190, 190), 1)
zl, zr = zxy(39, 60)[0], zxy(1, 60)[0]
cv2.rectangle(rc, (ZX, ZTOP), (ZX + ZW, ZTOP + ZH), (45, 45, 45), -1)
cv2.rectangle(rc, (zl, zxy(20, DECK0)[1]), (zr, ZTOP + ZH), (120, 175, 215), -1)
for b in range(2, 39):
    x = zxy(b, 60)[0]; cv2.line(rc, (x, zxy(20, DECK0)[1]), (x, ZTOP + ZH), (105, 160, 200), 1)
deck_bands(rc, zxy, ZX, ZX + ZW, zl, zr)
for bd, ft in PINS: draw_pin(rc, zxy(bd, ft), PIN_RZ)
cv2.rectangle(rc, (ZX, ZTOP), (ZX + ZW, ZTOP + ZH), (120, 120, 120), 1)
txt(rc, 'pin deck: entry rings and exit / last-seen dots', (ZX, ZTOP - 12), 0.55, (200, 200, 200), 1)
for ft, lab_ in ((DECK0, '60 ft'), (DECK1, '62.6')):
    txt(rc, lab_, (ZX + ZW + 6, zxy(20, ft)[1] + 4), 0.42, (170, 170, 170), 1)
for b in range(5, 40, 5):
    txt(rc, str(b), (zxy(b, 60)[0] - 8, ZTOP + ZH + 18), 0.42, (210, 210, 210), 1)
for j, r in enumerate(recap_rows):
    ln = [lxy(b, ft) for (_, b, ft) in r['line']]
    if len(ln) > 1: cv2.polylines(rc, [np.array(ln)], False, MAG, 2, cv2.LINE_AA)
    if ln:
        ft_j = 6.0 + j * 4.8   # one tag depth per throw, leader to the line, tag beside the right gutter
        kk = min(range(len(r['line'])), key=lambda q: abs(r['line'][q][2] - ft_j))
        px_ = lxy(r['line'][kk][1], r['line'][kk][2]); tx_ = (LX + LW + 70, px_[1])
        cv2.line(rc, px_, (tx_[0] - 14, tx_[1]), (150, 90, 150), 1, cv2.LINE_AA)
        cv2.circle(rc, px_, 4, MAG, -1, cv2.LINE_AA)
        tag(rc, str(j + 1), (tx_[0], tx_[1] + 6))
    if r['entry'] is not None and not r['gutter']:
        dpts = [(r['entry'], DECK0)] + [(b, ft) for (_, b, ft) in r['deck']]
        dotted(rc, [zxy(b, ft) for b, ft in dpts], EXITC, 3, 9)
        cv2.circle(rc, lxy(r['entry'], DECK0), 6, CYAN, 2, cv2.LINE_AA)
        ex0 = zxy(r['entry'], DECK0)
        cv2.circle(rc, ex0, 11, CYAN, 2, cv2.LINE_AA)
        tag(rc, str(j + 1), (ex0[0], ex0[1] + 34 + (j % 3) * 22), CYAN)
        if r['ex_b'] is not None:
            xy_ = zxy(r['ex_b'], r['ex_ft'])
            cv2.circle(rc, xy_, 11, (0, 0, 0), 3, cv2.LINE_AA); cv2.circle(rc, xy_, 8, EXITC, -1, cv2.LINE_AA)
            tag(rc, str(j + 1), (xy_[0], xy_[1] - 16 - (j % 3) * 20), EXITC)
ty = ZTOP + ZH + 70
cols = [(ZX, '#'), (ZX + 40, 'throw'), (ZX + 130, 'split'), (ZX + 220, 'entry'), (ZX + 320, 'break'), (ZX + 430, 'exit / last seen'), (ZX + 620, 'through the pins')]
for x, h_ in cols: txt(rc, h_, (x, ty), 0.5, (170, 170, 170), 1)
for j, r in enumerate(recap_rows):
    y = ty + 34 + j * 34
    if r['gutter']:
        vals = [str(j + 1), r['lab'], r['split'], 'gutter', '-', '-', 'gutter ball' + (' from ~%.0f ft' % r['g_from'][2] if r['g_from'] else '')]
    else:
        vals = [str(j + 1), r['lab'], r['split'], '%.1f' % r['entry'] if r['entry'] is not None else '-',
                '%.1f @ %.0f ft' % r['bp'] if r['bp'] else 'none',
                ('%.1f' % r['ex_b'] + (' (exit)' if r['kind'] == 'pit' else ' (last seen)')) if r['ex_b'] is not None else 'not measured',
                r['defl'] or '-']
    for (x, _), v in zip(cols, vals): txt(rc, v, (x, y), 0.5, WHITE if j % 2 == 0 else (215, 215, 215), 1)
txt(rc, 'depth = constant speed, release 0 ft to the detected pin row 60 ft', (ZX, H - 60), 0.42, (160, 160, 160), 1)
txt(rc, 'exit = last real moving point on the deck; on hookers it reads 3-6 boards short (ball behind pins)', (ZX, H - 36), 0.42, (160, 160, 160), 1)
cv2.imwrite(f'{FR}/card_recap.png', rc); put(rc, 6 * FPS)
pr_.stdin.close(); pr_.wait()
total = tcur + 4 + 6
sil = f'{L2}/work/aud_sil.m4a'
subprocess.run([FF, '-y', '-loglevel', 'error', '-f', 'lavfi', '-i', 'anullsrc=r=44100:cl=mono', '-t', '2', '-c:a', 'aac', sil], check=True)
lst = [sil]
for (n_, stem, a, b, nf, f0, f1, cs, sp) in timeline:
    p = f'{L2}/work/aud_{n_}.m4a'
    subprocess.run([FF, '-y', '-loglevel', 'error', '-ss', str((f0 - cs) / FPS), '-t', str(nf / FPS), '-i', cuts[n_ - 1]['cut_path'], '-vn', '-ar', '44100', '-ac', '1', '-c:a', 'aac', p], check=True)
    lst.append(p)
sil3 = f'{L2}/work/aud_sil3.m4a'
subprocess.run([FF, '-y', '-loglevel', 'error', '-f', 'lavfi', '-i', 'anullsrc=r=44100:cl=mono', '-t', '10', '-c:a', 'aac', sil3], check=True)
lst.append(sil3)
open(f'{L2}/work/aud_list.txt', 'w').write(''.join(f"file '{x}'\n" for x in lst))
subprocess.run([FF, '-y', '-loglevel', 'error', '-f', 'concat', '-safe', '0', '-i', f'{L2}/work/aud_list.txt', '-c', 'copy', f'{L2}/work/aud_all.m4a'], check=True)
subprocess.run([FF, '-y', '-loglevel', 'error', '-i', out, '-i', f'{L2}/work/aud_all.m4a', '-map', '0:v', '-map', '1:a', '-c:v', 'copy', '-c:a', 'aac', '-shortest', f'{L2}/showcase.mp4'], check=True)
json.dump({'timeline': timeline, 'means': M}, open(f'{L2}/work/showcase_timeline.json', 'w'))
print('total s', total)
for r in timeline: print(r)
