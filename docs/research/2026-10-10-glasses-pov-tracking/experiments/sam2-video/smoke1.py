"""Smoke: SAM2 video propagation from a purple-blob box prompt on one cut."""
import json, sys, time, os
import cv2, numpy as np
L = '/Users/toka/code/toms_gym/docs/research/2026-10-10-glasses-pov-tracking'
X = L + '/experiments/sam2-video'
stem = sys.argv[1] if len(sys.argv) > 1 else '20260915_185454_f240c883'
k0 = int(sys.argv[2]) if len(sys.argv) > 2 else 16
device = sys.argv[3] if len(sys.argv) > 3 else 'mps'
cuts = {c['stem']: c for c in json.load(open(L + '/work/cuts/cuts.json'))}
cut = cuts[stem]
cap = cv2.VideoCapture(cut['cut_path'])
frames = []
while True:
    ok, im = cap.read()
    if not ok: break
    frames.append(im)
print('cut frames', len(frames), frames[0].shape)

import sys; sys.path.insert(0, X)
from prompt import compact_blobs
H, W = frames[0].shape[:2]
best = compact_blobs(frames[k0])[0]
x, y, w, h = best[0], best[1], best[2]-best[0], best[3]-best[1]
print('prompt blob', best)
box = [int(x), int(y), int(x + w), int(y + h)]
# sub-clip from k0
sub = X + f'/work/sub_{stem}_{k0}.mp4'
vw = cv2.VideoWriter(sub, cv2.VideoWriter_fourcc(*'mp4v'), 30, (W, H))
for f in frames[k0:]: vw.write(f)
vw.release()
from ultralytics.models.sam import SAM2VideoPredictor
ov = dict(conf=0.25, task='segment', mode='predict', imgsz=1024, model='/Users/toka/code/bowling-app/pov-engine/models/sam2.1_t.pt', device=device, verbose=False, save=False)
pred = SAM2VideoPredictor(overrides=ov)
t0 = time.time()
rows = []
for k, r in enumerate(pred(source=sub, bboxes=[box], stream=True)):
    f_src = cut['cut_start'] + k0 + k
    if r.masks is None or len(r.masks.data) == 0:
        rows.append((f_src, None)); continue
    md = r.masks.data[0].cpu().numpy().astype(np.uint8)
    area = int(md.sum())
    if area == 0:
        rows.append((f_src, None)); continue
    ys, xs = np.nonzero(md)
    cx, cy = float(xs.mean()), float(ys.mean())
    rr = float(np.sqrt(area / np.pi))
    rows.append((f_src, (round(cx, 1), round(cy, 1), round(rr, 1), area)))
dt = time.time() - t0
print(f'{device}: {len(rows)} frames in {dt:.1f}s = {dt/len(rows):.2f} s/frame; mask shape', md.shape)
truth = json.load(open(L + f'/truth/{stem}.json'))['ball']
for f, p in rows:
    t = truth.get(str(f))
    tp = (t['x'], t['y'], t['r']) if isinstance(t, dict) else (t[:3] if t else None)
    d = None if (p is None or tp is None) else round(float(np.hypot(p[0] - tp[0], p[1] - tp[1])), 1)
    print(f, p, 'truth', tp, 'd', d)
json.dump({'rows': rows, 'box': box, 'k0': k0, 'dt': dt}, open(X + f'/work/smoke1_{stem}_{device}.json', 'w'))
