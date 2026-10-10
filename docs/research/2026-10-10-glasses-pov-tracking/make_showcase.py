import json, subprocess, os, sys
import numpy as np, cv2
L = os.path.dirname(os.path.abspath(__file__))
FF = '/opt/homebrew/bin/ffmpeg'
FP = '/opt/homebrew/bin/ffprobe'
cuts = [c for c in json.load(open(f'{L}/work/cuts/cuts.json')) if c.get('cut_start') is not None]
DEV = {'20260915_185121_23d80f05','20260915_185331_19de9ec7','20260915_185645_9fde3c16','20260915_185454_f240c883','20260915_190115_a7cf2c70','20260915_191900_106ea7ca'}
def _nolane(c):
    return len(json.load(open(f"{L}/results/tracks/{c['stem']}.json")).get('lane_top_down', [])) == 0
cuts.sort(key=lambda c: (_nolane(c), c['stem']))
N = len(cuts)
W, H, FPS = 1920, 1080, 30
PURPLE = (200, 60, 140)  # BGR
TAIL = 15
def plan(tail):
    tot = 0
    for c in cuts: tot += (c['pin_hit_frame'] + tail) - (c['release_frame'] - 5) + 1
    return tot
tail, speed = TAIL, 1.0
if plan(tail) / FPS > 55: tail = 8
if plan(tail) / FPS > 55: speed = 1.25
print('tail', tail, 'speed', speed, 'secs', plan(tail) / FPS / speed)

def load(c):
    t = json.load(open(f"{L}/results/tracks/{c['stem']}.json"))
    fr = {p['f']: (p['x'], p['y'], p['r']) for p in t['frames']}
    td = {e['f']: e for e in t.get('lane_top_down', []) if e['zone'] in ('lane', 'gutter_r', 'gutter_l')}
    fb = bool(t.get('meta', {}).get('fallback', {}).get('applied'))
    llf = t.get('meta', {}).get('last_lane_frame')
    td_all = td
    if td:
        ks = sorted(td)
        while len(ks) > 2 and (abs(td[ks[0]]['board'] - td[ks[1]]['board']) > 6 or abs(td[ks[0]]['ft'] - td[ks[1]]['ft']) > 10):
            ks.pop(0)
        td = {k: td[k] for k in ks}
    t['_llf'] = llf
    return t, fr, td, fb

# lane panel geometry
LX, LW, LTOP, LH = 300, 360, 90, 880
def lane_xy(board, ft):
    b = min(max(board, -1.0), 40.0)
    return int(LX + LW * (39 - b) / 38), int(LTOP + LH * (1 - min(ft, 60) / 60))
def base_lane():
    im = np.full((H, 960, 3), 24, np.uint8)
    cv2.rectangle(im, (LX - 32, LTOP), (LX + LW + 32, LTOP + LH), (50, 50, 50), -1)
    cv2.rectangle(im, (LX, LTOP), (LX + LW, LTOP + LH), (120, 175, 215), -1)
    for b in range(2, 39):
        x = int(LX + LW * (39 - (b - .5 + .5)) / 38)
        cv2.line(im, (LX + int(LW * (39 - b) / 38),) * 1 + (LTOP,), (LX + int(LW * (39 - b) / 38), LTOP + LH), (105, 160, 200), 1)
    cv2.line(im, (LX, LTOP + LH), (LX + LW, LTOP + LH), (255, 255, 255), 3)
    for i, bd in enumerate([5.4, 10.3, 15.1, 20.0, 24.9, 29.7, 34.6]):
        x, y = lane_xy(bd, 15 + abs(3 - i) * -0.0 + (3 - abs(3 - i)) * 0.9)
        cv2.polylines(im, [np.array([[x - 7, y + 9], [x, y], [x + 7, y + 9]])], False, (60, 60, 60), 2)
    dy = 0.866 * LH / 60
    for row, n in enumerate([1, 2, 3, 4]):
        y = int(LTOP + 6 + (3 - row) * dy)
        for k in range(n):
            bd = 20.0 + (k - (n - 1) / 2) * 10.99
            x, _ = lane_xy(bd, 60)
            cv2.circle(im, (x, y), 5, (255, 255, 255), -1)
    for b in range(5, 40, 5):
        x = LX + int(LW * (39 - b) / 38)
        cv2.putText(im, str(b), (x - 9, LTOP + LH + 25), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (210, 210, 210), 1, cv2.LINE_AA)
    cv2.putText(im, 'foul line', (LX + LW + 40, LTOP + LH + 4), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (160, 160, 160), 1, cv2.LINE_AA)
    cv2.putText(im, 'pins (60 ft)', (LX + LW + 40, LTOP + 6), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (160, 160, 160), 1, cv2.LINE_AA)
    return im
BASE = base_lane()

def interp_pos(fr, f):
    if f in fr: return fr[f][:3] + (False,)
    lo = [k for k in fr if k < f and f - k <= 6]; hi = [k for k in fr if k > f and k - f <= 6]
    if not lo or not hi: return None
    a, b = max(lo), min(hi); w = (f - a) / (b - a)
    return tuple(fr[a][i] * (1 - w) + fr[b][i] * w for i in range(3)) + (True,)

def card(lines):
    im = np.full((H, W, 3), 20, np.uint8)
    for i, (s, sc) in enumerate(lines):
        (tw, _), _ = cv2.getTextSize(s, cv2.FONT_HERSHEY_SIMPLEX, sc, 2)
        cv2.putText(im, s, ((W - tw) // 2, 450 + i * 90), cv2.FONT_HERSHEY_SIMPLEX, sc, (240, 240, 240), 2, cv2.LINE_AA)
    return im

out = f'{L}/work/showcase_silent.mp4'
pr = subprocess.Popen([FF, '-y', '-loglevel', 'error', '-f', 'rawvideo', '-pix_fmt', 'bgr24', '-s', f'{W}x{H}', '-r', str(FPS * speed),
    '-i', '-', '-vf', f'setpts=PTS/{speed}' if False else 'null', '-r', str(FPS), '-c:v', 'libx264', '-crf', '18', '-pix_fmt', 'yuv420p', out], stdin=subprocess.PIPE)
def put(im, n=1):
    for _ in range(n): pr.stdin.write(im.tobytes())

method = 'sam2-video'
put(card([('Glasses POV bowling - %d throws' % N, 1.6), (method, 1.2), ('2026-10-10', 1.0)]), 2 * FPS)
timeline = []; t_cur = 2.0
segs = []
for i, c in enumerate(cuts):
    t, fr, td, fb = load(c)
    cs = c['cut_start']; f0 = c['release_frame'] - 5; f1 = min(c['pin_hit_frame'] + tail, c['cut_end'] - 1)
    cap = cv2.VideoCapture(c['cut_path'])
    cap.set(cv2.CAP_PROP_POS_FRAMES, f0 - cs)
    tdl = sorted(td)
    nfr = 0
    for f in range(f0, f1 + 1):
        ok, img = cap.read()
        if not ok: break
        sc = H / img.shape[0]; im = cv2.resize(img, (int(img.shape[1] * sc), H))
        left = np.full((H, 960, 3), 12, np.uint8); x0 = (960 - im.shape[1]) // 2
        left[:, x0:x0 + im.shape[1]] = im
        p = interp_pos(fr, f)
        llf = t['_llf']
        if p is not None and (llf is None or f <= llf):
            col = (0, 165, 255) if p[3] else (255, 255, 0)
            cv2.circle(left, (int(x0 + p[0] * sc), int(p[1] * sc)), max(6, int(p[2] * sc)), col, 2, cv2.LINE_AA)
        if not tdl: cv2.putText(left, 'no lane fit: circle only, no top-down trace', (14, 66), cv2.FONT_HERSHEY_SIMPLEX, 0.65, (120, 160, 255), 2, cv2.LINE_AA)
        cv2.putText(left, 'cyan = tracked, orange = interpolated', (14, H - 16), cv2.FONT_HERSHEY_SIMPLEX, 0.55, (200, 200, 200), 1, cv2.LINE_AA)
        cv2.putText(left, f'throw {i+1}/{N} - {c["stem"]} - f{f} - {"dev" if c["stem"] in DEV else "HOLDOUT"}', (14, 34), cv2.FONT_HERSHEY_SIMPLEX, 0.75, (255, 255, 255), 2, cv2.LINE_AA)
        right = BASE.copy()
        pts = [(lane_xy(td[k]['board'], td[k]['ft'])) for k in tdl if k <= f]
        if len(pts) > 1: cv2.polylines(right, [np.array(pts)], False, PURPLE, 2, cv2.LINE_AA)
        for q in pts: cv2.circle(right, q, 3, PURPLE, -1, cv2.LINE_AA)
        if pts: cv2.circle(right, pts[-1], 9, PURPLE, -1, cv2.LINE_AA)
        cur = [k for k in tdl if k <= f]
        if cur: cv2.putText(right, 'board %.1f' % min(max(td[cur[-1]]['board'], -1), 40), (40, 60), cv2.FONT_HERSHEY_SIMPLEX, 1.0, (255, 255, 255), 2, cv2.LINE_AA)
        elif not tdl: cv2.putText(right, 'no lane fit - no top-down trace', (40, 60), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (120, 160, 255), 2, cv2.LINE_AA)
        if f >= c['pin_hit_frame']:
            fbv = t.get('final_board')
            cv2.putText(right, 'final board %s' % ('%g' % fbv if fbv is not None else 'n/a'), (40, 105), cv2.FONT_HERSHEY_SIMPLEX, 1.0, (120, 255, 120), 2, cv2.LINE_AA)
        lab = method + ('+fallback' if fb else '')
        (tw, _), _ = cv2.getTextSize(lab, cv2.FONT_HERSHEY_SIMPLEX, 0.7, 2)
        cv2.putText(right, lab, (960 - tw - 16, H - 16), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (200, 200, 200), 2, cv2.LINE_AA)
        put(np.hstack([left, right])); nfr += 1
    dur = nfr / FPS / speed
    timeline.append((i + 1, c['stem'], t_cur, t_cur + dur, nfr, fb, f0, f1, c['cut_start'])); t_cur += dur
pr.stdin.close(); pr.wait()
if speed != 1.0:
    subprocess.run([FF, '-y', '-loglevel', 'error', '-i', out, '-vf', f'setpts=PTS/{speed}', '-r', str(FPS), '-c:v', 'libx264', '-crf', '18', '-pix_fmt', 'yuv420p', f'{L}/work/showcase_fast.mp4'], check=True)
    out = f'{L}/work/showcase_fast.mp4'
json.dump({'timeline': timeline, 'speed': speed, 'tail': tail}, open(f'{L}/work/showcase_timeline.json', 'w'))

# audio
audio_ok = False
try:
    parts = []
    sil = f'{L}/work/aud_sil.m4a'
    subprocess.run([FF, '-y', '-loglevel', 'error', '-f', 'lavfi', '-i', 'anullsrc=r=44100:cl=mono', '-t', '2', '-c:a', 'aac', sil], check=True)
    lst = [sil]
    for (n, stem, a, b, nfr, fb, f0, f1, cs) in timeline:
        p = f'{L}/work/aud_{n}.m4a'
        subprocess.run([FF, '-y', '-loglevel', 'error', '-ss', str((f0 - cs) / FPS), '-to', str((f1 + 1 - cs) / FPS), '-i', cuts[n-1]['cut_path'],
            '-vn', '-ar', '44100', '-ac', '1', '-af', f'atempo={speed}', '-c:a', 'aac', p], check=True)
        lst.append(p)
    open(f'{L}/work/aud_list.txt', 'w').write(''.join(f"file '{x}'\n" for x in lst))
    subprocess.run([FF, '-y', '-loglevel', 'error', '-f', 'concat', '-safe', '0', '-i', f'{L}/work/aud_list.txt', '-c', 'copy', f'{L}/work/aud_all.m4a'], check=True)
    subprocess.run([FF, '-y', '-loglevel', 'error', '-i', out, '-i', f'{L}/work/aud_all.m4a', '-map', '0:v', '-map', '1:a', '-c:v', 'copy', '-c:a', 'aac', '-shortest', f'{L}/showcase.mp4'], check=True)
    audio_ok = True
except Exception as e:
    print('audio failed', e)
    subprocess.run(['cp', out, f'{L}/showcase.mp4'])
print('audio', audio_ok)
