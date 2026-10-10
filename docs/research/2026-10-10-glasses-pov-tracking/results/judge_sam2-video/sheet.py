import json, sys, cv2, numpy as np
L = '/Users/toka/code/toms_gym/docs/research/2026-10-10-glasses-pov-tracking'
stem, out = sys.argv[1], sys.argv[2]
fl = [int(v) for v in sys.argv[3].split(',')]
cut = {c['stem']: c for c in json.load(open(f'{L}/work/cuts/cuts.json'))}[stem]
tr = json.load(open(f'{L}/experiments/sam2-video/tracks/{stem}.json'))
pts = {p['f']: p for p in tr['frames']}
cap = cv2.VideoCapture(cut['cut_path']); frames = []
while True:
    ok, im = cap.read()
    if not ok: break
    frames.append(im)
tiles = []
for f in fl:
    im = frames[f - cut['cut_start']].copy()
    q = tr['lane'].get(str(f))
    if q:
        cv2.polylines(im, [np.array([q['fl_l'], q['pd_l'], q['pd_r'], q['fl_r']], np.int32)], True, (255, 255, 0), 2)
    p = pts.get(f)
    if p:
        cx, cy, r = int(p['x']), int(p['y']), int(max(4, p['r']))
        cv2.circle(im, (cx, cy), r + 4, (0, 140, 255), 2)
        x0, y0 = max(0, cx - 160), max(0, cy - 160)
        crop = im[y0:y0 + 320, x0:x0 + 320]
    else:
        crop = im[300:620, 500:820]
    crop = cv2.resize(crop, (480, 480), interpolation=cv2.INTER_NEAREST)
    b = tr['boards'].get(str(f))
    cv2.putText(crop, f'f{f} b{b}', (8, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.9, (255, 255, 255), 2)
    tiles.append(crop)
while len(tiles) % 3: tiles.append(np.zeros_like(tiles[0]))
rows = [np.hstack(tiles[i:i + 3]) for i in range(0, len(tiles), 3)]
cv2.imwrite(out, np.vstack(rows))
