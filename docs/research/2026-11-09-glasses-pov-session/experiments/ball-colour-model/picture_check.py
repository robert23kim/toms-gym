"""picture_check.py <stem>...: overlays/check__<stem>.jpg, the tracked circle drawn in its OWN frame at the frames
nearest 20, 40 and 55 ft (ft_cv from the track), 320 px crops side by side, for the J6 picture read."""
import json, os, sys
import cv2, numpy as np

X = os.path.dirname(os.path.abspath(__file__))
S = '/Users/toka/code/toms_gym/docs/research/2026-11-09-glasses-pov-session'
cuts = {c['stem']: c for c in json.load(open(os.path.join(S, 'work', 'cuts', 'cuts.json')))}


def read_frames(path):
    cap = cv2.VideoCapture(path)
    out = []
    while True:
        ok, im = cap.read()
        if not ok:
            break
        out.append(im)
    return out


for stem in sys.argv[1:]:
    tr = json.load(open(os.path.join(X, 'tracks', f'{stem}.json')))
    cut = cuts[stem]
    off, rel, pr = cut['cut_start'], tr['release_frame'], tr['pin_row_frame_est']
    frames = read_frames(cut['cut_path'])
    pts = {p['f']: p for p in tr['frames']}
    tiles = []
    for ft in (20.0, 40.0, 55.0):
        f = int(round(rel + ft / 60.0 * (pr - rel)))
        cand = [g for g in pts if pts[g].get('src') != 'coast']
        g = min(cand, key=lambda q: abs(q - f)) if cand else None
        side = 320
        if g is not None and abs(g - f) <= 1:
            f = g
            p = pts[g]
        im = frames[f - off].copy()
        if g is not None and abs(g - f) <= 1:
            x, y, r = p['x'], p['y'], max(3.0, p['r'] or 3.0)
            cv2.circle(im, (int(x), int(y)), int(round(r)), (0, 140, 255), 2)
            cv2.drawMarker(im, (int(x), int(y)), (0, 140, 255), cv2.MARKER_CROSS, 10, 1)
            label = f'{ft:.0f} ft f{f} r{r:.0f} {p.get("src")}'
            cx, cy = int(x), int(y)
        else:
            label = f'{ft:.0f} ft f{f} NO POINT'
            cx, cy = im.shape[1] // 2, im.shape[0] // 2
        x0 = int(min(max(0, cx - side // 2), im.shape[1] - side))
        y0 = int(min(max(0, cy - side // 2), im.shape[0] - side))
        crop = im[y0:y0 + side, x0:x0 + side].copy()
        crop = cv2.resize(crop, (480, 480), interpolation=cv2.INTER_CUBIC)
        cv2.putText(crop, label, (8, 24), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 0, 0), 4)
        cv2.putText(crop, label, (8, 24), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 1)
        tiles.append(crop)
    out = np.hstack(tiles)
    cv2.putText(out, stem, (8, out.shape[0] - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 0, 0), 4)
    cv2.putText(out, stem, (8, out.shape[0] - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 1)
    op = os.path.join(X, 'overlays', f'check__{stem}.jpg')
    cv2.imwrite(op, out, [cv2.IMWRITE_JPEG_QUALITY, 85])
    print(op)
