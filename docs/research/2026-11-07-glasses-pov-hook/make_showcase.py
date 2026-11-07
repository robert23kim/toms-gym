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
fin = json.load(open(f'{L2}/results/final_v2.json'))
ROWS = {r['stem']: r for r in fin['rows']}
W, H, FPS = 1920, 1080, 30
GREY = (125, 125, 125); GREEN = (90, 220, 90); MAG = (200, 60, 200); AMB = (40, 170, 255)
FTMAX = 64.0
def J(p): return json.load(open(p))
def ftcv(f, rel, pin): return 60.0 * (f - rel) / (pin - rel)
def runmed(v, w=5):
    h = w // 2
    return [float(np.median(v[max(0, i - h):i + h + 1])) for i in range(len(v))]

LX, LW, LTOP, LH = 230, 360, 100, 860
BW = 12.0 / 1.0625  # boards between neighbouring pins (12 in / 1.0625 in per board)
def lxy(board, ft):
    b = min(max(board, -3.0), 42.0)  # inside the gutter bands
    return int(LX + LW * (39 - b) / 38), int(LTOP + LH * (1 - min(max(ft, 0), FTMAX) / FTMAX))
def base():
    im = np.full((H, 960, 3), 24, np.uint8)
    cv2.rectangle(im, (LX - 36, LTOP), (LX + LW + 36, LTOP + LH), (45, 45, 45), -1)
    cv2.rectangle(im, (LX, LTOP), (LX + LW, LTOP + LH), (120, 175, 215), -1)
    for b in range(2, 39):
        x = LX + int(LW * (39 - b) / 38); cv2.line(im, (x, LTOP), (x, LTOP + LH), (105, 160, 200), 1)
    fl = LTOP + LH
    cv2.line(im, (LX - 36, fl), (LX + LW + 36, fl), (255, 255, 255), 3)
    for i, bd in enumerate([5.4, 10.3, 15.1, 20.0, 24.9, 29.7, 34.6]):
        x, y = lxy(bd, 12.5 + (3 - abs(3 - i)) * 1.0)
        cv2.polylines(im, [np.array([[x - 7, y + 9], [x, y], [x + 7, y + 9]])], False, (60, 60, 60), 2)
    for row in range(4):
        for k in range(row + 1):
            x, y = lxy(20.0 + (k - row / 2) * BW, 60 + 0.866 * row)
            cv2.circle(im, (x, y), 5, (255, 255, 255), -1)
    for ft in (0, 15, 30, 45, 60):
        y = lxy(20, ft)[1]
        cv2.line(im, (LX - 36, y), (LX - 30, y), (200, 200, 200), 1)
        cv2.putText(im, f'{ft} ft', (LX - 86, y + 5), 0, 0.5, (200, 200, 200), 1, cv2.LINE_AA)
    cv2.putText(im, 'head pin = 60 ft', (LX + LW + 50, lxy(20, 60)[1] + 5), 0, 0.5, (160, 160, 160), 1, cv2.LINE_AA)
    cv2.putText(im, 'foul line', (LX + LW + 50, fl + 4), 0, 0.5, (160, 160, 160), 1, cv2.LINE_AA)
    for b in range(5, 40, 5):
        cv2.putText(im, str(b), (LX + int(LW * (39 - b) / 38) - 9, fl + 32), 0, 0.5, (210, 210, 210), 1, cv2.LINE_AA)
    cv2.putText(im, 'board (1 = right gutter side)', (LX - 40, fl + 58), 0, 0.5, (150, 150, 150), 1, cv2.LINE_AA)
    return im
BASE = base()
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

def series(t, rel, pin, which):
    """(f, board, ft) per frame up to the labelled pin hit; depth = constant speed release->pin_hit."""
    if which == 'v2':
        d = {int(k): v for k, v in t['boards'].items()}
    else:
        d = {e['f']: e['board'] for e in t.get('lane_top_down', []) if e['zone'] in ('lane', 'gutter_r', 'gutter_l')}
    out = [(k, d[k], ftcv(k, rel, pin)) for k in sorted(d) if rel <= k <= pin]
    return [o for o in out if o[2] >= 1.5]

t0 = J(f"{L2}/results/tracks/{cuts[0]['stem']}.json")
stage_line = 'ball: lane-gated-ball   lane: composition edge lane + smooth3 + tail rejection   path: none'
out = f'{L2}/work/showcase_silent.mp4'
pr = subprocess.Popen([FF, '-y', '-loglevel', 'error', '-f', 'rawvideo', '-pix_fmt', 'bgr24', '-s', f'{W}x{H}', '-r', str(FPS),
    '-i', '-', '-c:v', 'libx264', '-crf', '18', '-pix_fmt', 'yuv420p', out], stdin=subprocess.PIPE)
FR = f'{L2}/work/showcase_frames'; os.makedirs(FR, exist_ok=True)
def put(im, n=1):
    for _ in range(n): pr.stdin.write(im.tobytes())
title = card([('Glasses POV bowling - loop 2', 1.6), (stage_line, 0.8), ('2026-11-07', 1.0)])
cv2.imwrite(f'{FR}/card_title.png', title); put(title, 2 * FPS)
timeline = []; tcur = 2.0
TAIL = 15
for i, c in enumerate(cuts):
    stem = c['stem']; rel = c['release_frame']; pin = c['pin_hit_frame']
    t2 = J(f'{L2}/results/tracks/{stem}.json'); t1 = J(f'{L1}/results/tracks/{stem}.json')
    fr = {p['f']: (p['x'], p['y'], p['r']) for p in t2['frames']}
    lastfr = max(fr)
    s2 = series(t2, rel, pin, 'v2'); s1 = series(t1, rel, pin, 'v1')
    l2 = runmed([b for _, b, _ in s2]); l1 = runmed([b for _, b, _ in s1])
    line2 = [(s2[j][0], l2[j], s2[j][2]) for j in range(len(s2))]
    line1 = [(s1[j][0], l1[j], s1[j][2]) for j in range(len(s1))]
    fb = t2.get('final_board'); fb1 = t1.get('final_board')
    gut = [d for d in s2 if d[1] < 1.0]
    gutter = fb is not None and fb < 1.0
    mb = min(s2, key=lambda d: d[1]) if s2 else None
    rise = (max([d[1] for d in s2 if d[0] > mb[0]] or [mb[1]]) - mb[1]) if mb else 0
    truth = None
    if os.path.exists(f'{HO}/{stem}.json') and stem in ('20260915_192142_eeb210f6', '20260915_192636_7c7fbfb0'):
        h = J(f'{HO}/{stem}.json'); truth = (h['observed_pin_contact_frame'], h['entry']['board'])
    f0 = rel - 5; f1 = min(pin + TAIL, c['cut_end'] - 1); cs = c['cut_start']
    cap = cv2.VideoCapture(c['cut_path']); cap.set(cv2.CAP_PROP_POS_FRAMES, f0 - cs)
    lab = stem[9:15]; split = 'dev' if stem in DEV else 'HOLDOUT'
    n = 0
    for f in range(f0, f1 + 1):
        ok, img = cap.read()
        if not ok: break
        sc = H / img.shape[0]; im = cv2.resize(img, (int(img.shape[1] * sc), H))
        left = np.full((H, 960, 3), 12, np.uint8); x0 = (960 - im.shape[1]) // 2
        xs = max(0, -x0); left[:, max(0, x0):max(0, x0) + min(960, im.shape[1])] = im[:, xs:xs + min(960, im.shape[1])]
        p = interp(fr, f)
        if p is not None and f <= lastfr:
            col = (0, 165, 255) if p[3] else (255, 255, 0)
            cv2.circle(left, (int(x0 + p[0] * sc), int(p[1] * sc)), max(6, int(p[2] * sc)), col, 1, cv2.LINE_AA)
        txt(left, f'{lab} f{f} {split}', (14, 34), 0.8, (255, 255, 255), 2)
        txt(left, 'cyan = tracked, orange = interpolated', (14, H - 16), 0.55, (200, 200, 200))
        if f > lastfr: txt(left, 'tracker ends here (pin_hit+4)', (14, 66), 0.6, AMB, 1)
        right = BASE.copy()
        p1 = [lxy(b, ft) for (k, b, ft) in line1 if k <= f]
        if len(p1) > 1: cv2.polylines(right, [np.array(p1)], False, GREY, 2, cv2.LINE_AA)
        txt(right, 'grey line = loop 1' + ('' if line1 else ' (no lane fit)'), (LX + LW + 50, 300), 0.5, GREY)
        pts = [(k, b, ft) for (k, b, ft) in s2 if k <= f]
        ln = [lxy(b, ft) for (k, b, ft) in line2 if k <= f]
        if len(ln) > 1: cv2.polylines(right, [np.array(ln)], False, MAG, 2, cv2.LINE_AA)
        for (k, b, ft) in pts: cv2.circle(right, lxy(b, ft), 3, (255, 140, 255), -1, cv2.LINE_AA)
        if pts: cv2.circle(right, lxy(pts[-1][1], pts[-1][2]), 8, MAG, 2, cv2.LINE_AA)
        txt(right, 'dots = loop 2 boards per frame', (LX + LW + 50, 325), 0.5, (255, 140, 255))
        txt(right, 'line = 5-frame median of dots', (LX + LW + 50, 350), 0.5, MAG)
        txt(right, 'depth = constant speed, release->pin hit', (LX + LW + 50, 375), 0.45, (150, 150, 150))
        txt(right, 'no path fit drawn', (LX + LW + 50, 398), 0.45, (150, 150, 150))
        fl = LTOP + LH
        if pts:
            bcur = pts[-1][1]
            tri = np.array([[bx(bcur), fl + 4], [bx(bcur) - 8, fl + 16], [bx(bcur) + 8, fl + 16]], np.int32)
            cv2.fillPoly(right, [tri], MAG)
            txt(right, 'gutter' if bcur < 1 else 'board %.1f' % bcur, (30, 40), 1.0, (255, 255, 255), 2)
        if mb and rise >= 1.5 and f >= pin and not gutter:
            cv2.circle(right, lxy(mb[1], mb[2]), 12, (255, 255, 255), 2, cv2.LINE_AA)
        if f >= pin:
            if gutter:
                ent = 'GUTTER BALL (loop 1: %s)' % ('%.1f' % fb1 if fb1 is not None else 'n/a')
                txt(right, ent, (30, 78), 0.8, AMB, 2)
                if gut: txt(right, 'in the gutter from ~%.0f ft' % gut[0][2], (480, 40), 0.65, AMB, 2)
            else:
                txt(right, 'entry board %s (loop 1: %s)' % ('%.1f' % fb if fb is not None else 'n/a', '%.1f' % fb1 if fb1 is not None else 'n/a'), (30, 78), 0.8, GREEN, 2)
                if mb: txt(right, 'min board %.1f at %.0f ft' % (mb[1], mb[2]), (500, 40), 0.65, GREEN, 2)
                if fb is not None:
                    x = bx(fb); cv2.line(right, (x, fl + 3), (x, fl + 18), GREEN, 3)
            txt(right, 'readouts at the labelled pin_hit f%d' % pin, (LX + LW + 50, 421), 0.45, (150, 150, 150))
            if truth and f >= pin:
                msg = 'ball carries on to the head pin: hand-label contact f%d, board %.2f' % truth
                txt(right, msg, (30, 122) if False else (LX - 36, H - 12), 0.5, AMB, 1)
                cx, cy = lxy(truth[1], 60)
                cv2.drawMarker(right, (cx, cy), AMB, cv2.MARKER_DIAMOND, 16, 2, cv2.LINE_AA)
        frame = np.hstack([left, right]); put(frame); n += 1
        tag = 'start' if f == f0 else ('pin' if f == pin else ('mid' if f == (f0 + pin) // 2 else ('end' if f == f1 else None)))
        if tag: cv2.imwrite(f'{FR}/throw{i+1}_{lab}_{tag}.png', frame)
    timeline.append((i + 1, stem, round(tcur, 2), round(tcur + n / FPS, 2), n, f0, f1, cs, split)); tcur += n / FPS

def mean(v): return sum(v) / len(v)
def agg(split):
    rs = [r for r in fin['rows'] if (split is None or r['split'] == split)]
    lf = [r for r in rs if r.get('v1_entry_err') is not None]
    return dict(
        n=len(rs), fr1=mean([r['v1_far_recall_pct'] for r in rs]), fr2=mean([r['far_recall_pct'] for r in rs]),
        n_lf=len(lf), e1=mean([r['v1_entry_err'] for r in lf]), e2=mean([r['entry_err'] for r in lf]),
        p1=mean([r['v1_path_err_far'] for r in lf]), p2=mean([r['path_err_far'] for r in lf]))
HOa, DEa = agg('holdout'), agg('dev')
cl = np.full((H, W, 3), 20, np.uint8)
txt(cl, 'Before / after, loop 1 vs loop 2, vs hand truth', (440, 150), 1.3, (240, 240, 240), 2)
cols = (60, 560, 760, 1130, 1330)
hdr = ['', 'HOLDOUT n=5', '', 'dev n=5 (in-sample)', '']
def block(x, a, title):
    txt(cl, title, (x, 250), 0.95, (240, 240, 240), 2)
    txt(cl, 'loop 1', (x + 20, 300), 0.8, (170, 170, 170), 2); txt(cl, 'loop 2', (x + 190, 300), 0.8, GREEN, 2)
    for r, (nm, v1, v2) in enumerate([('far recall %', a['fr1'], a['fr2']), ('entry err', a['e1'], a['e2']), ('path err far', a['p1'], a['p2'])]):
        y = 360 + r * 70
        txt(cl, '%.1f' % v1 if r else '%.0f' % v1, (x + 20, y), 1.0, (240, 240, 240), 2); txt(cl, '%.1f' % v2 if r else '%.0f' % v2, (x + 190, y), 1.0, GREEN, 2)
txt(cl, 'far recall %', (60, 360), 0.9, (170, 170, 170), 1); txt(cl, 'entry err (boards)', (60, 430), 0.9, (170, 170, 170), 1); txt(cl, 'path err far (boards)', (60, 500), 0.9, (170, 170, 170), 1)
block(560, HOa, 'HOLDOUT (n=5)'); block(1130, DEa, 'dev (n=5, in-sample)')
bah = fin['before_after_holdout']
notes = [
    'Entry and path rows use throws where loop 1 had a lane fit (dev n=%d, holdout n=%d); 185121 had none in loop 1.' % (DEa['n_lf'], HOa['n_lf']),
    'Like for like on those 9 throws: entry err loop 1 %.2f -> loop 2 %.2f. The headline mixed n=9 with n=10 (185121 at 0.03).' % (mean([r['v1_entry_err'] for r in fin['rows'] if r.get('v1_entry_err') is not None]), mean([r['entry_err'] for r in fin['rows'] if r.get('v1_entry_err') is not None])),
    'Dev thresholds were tuned on the dev throws, so dev is not a test. The lane and ball stages were picked from the holdout rows,',
    'so holdout is not a fresh test either. 192142 and 192636 entry error is mostly the labelled pin_hit being early (truth contact later).',
    'Truth and tracker share one instrument (purple blob, wood-to-gutter edges): agreement under about 1.5 boards is not established.',
    'Loop 2 still draws no path fit; the line is the measured boards.']
for k, s in enumerate(notes): txt(cl, s, (60, 640 + k * 38), 0.6, (190, 190, 190), 1)
cv2.imwrite(f'{FR}/card_close.png', cl); put(cl, 3 * FPS)
pr.stdin.close(); pr.wait()
total = tcur + 3
sil = f'{L2}/work/aud_sil.m4a'
subprocess.run([FF, '-y', '-loglevel', 'error', '-f', 'lavfi', '-i', 'anullsrc=r=44100:cl=mono', '-t', '2', '-c:a', 'aac', sil], check=True)
lst = [sil]
for (n_, stem, a, b, nf, f0, f1, cs, sp) in timeline:
    p = f'{L2}/work/aud_{n_}.m4a'
    subprocess.run([FF, '-y', '-loglevel', 'error', '-ss', str((f0 - cs) / FPS), '-t', str(nf / FPS), '-i', cuts[n_ - 1]['cut_path'], '-vn', '-ar', '44100', '-ac', '1', '-c:a', 'aac', p], check=True)
    lst.append(p)
sil3 = f'{L2}/work/aud_sil3.m4a'
subprocess.run([FF, '-y', '-loglevel', 'error', '-f', 'lavfi', '-i', 'anullsrc=r=44100:cl=mono', '-t', '3', '-c:a', 'aac', sil3], check=True)
lst.append(sil3)
open(f'{L2}/work/aud_list.txt', 'w').write(''.join(f"file '{x}'\n" for x in lst))
subprocess.run([FF, '-y', '-loglevel', 'error', '-f', 'concat', '-safe', '0', '-i', f'{L2}/work/aud_list.txt', '-c', 'copy', f'{L2}/work/aud_all.m4a'], check=True)
subprocess.run([FF, '-y', '-loglevel', 'error', '-i', out, '-i', f'{L2}/work/aud_all.m4a', '-map', '0:v', '-map', '1:a', '-c:v', 'copy', '-c:a', 'aac', '-shortest', f'{L2}/showcase.mp4'], check=True)
json.dump({'timeline': timeline, 'holdout': HOa, 'dev': DEa}, open(f'{L2}/work/showcase_timeline.json', 'w'))
print('total s', total)
for r in timeline: print(r)
print(HOa, DEa)
