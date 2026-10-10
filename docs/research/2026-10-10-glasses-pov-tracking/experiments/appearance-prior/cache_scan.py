"""Cache YOLO boxes (conf 0.1) and ORB camera shifts for every cut, one process, videos sequential.
usage: cache_scan.py <stem> [<stem> ...]   -> cache/<stem>.json  {dets: {k: [[x,y,r,conf],...]}, shifts: {k: {...}}, meta}
Frame keys are CUT-LOCAL (k); add cut_start to get source frames."""
import json, sys, time
from pathlib import Path
E = Path('/Users/toka/code/bowling-app/pov-engine')
sys.path.insert(0, str(E))
from src.bowling.trajectory.yolo_chain_pass import scan_video  # noqa: E402

L = Path('/Users/toka/code/toms_gym/docs/research/2026-10-10-glasses-pov-tracking')
X = L / 'experiments' / 'appearance-prior'
cuts = {c['stem']: c for c in json.load(open(L / 'work' / 'cuts' / 'cuts.json'))}
for stem in sys.argv[1:]:
    c = cuts[stem]
    if not c.get('cut_path'):
        print(stem, 'no cut'); continue
    t0 = time.time()
    dets, shifts, meta = scan_video(c['cut_path'], str(E / 'models' / 'yolo11n_bowling.pt'), conf=0.1)
    out = {'stem': stem, 'cut_start': c['cut_start'], 'dets': {str(k): [list(map(float, b)) for b in v] for k, v in dets.items()},
           'shifts': {str(k): v for k, v in shifts.items()}, 'meta': meta, 'wall_s': round(time.time() - t0, 1)}
    json.dump(out, open(X / 'cache' / f'{stem}.json', 'w'))
    print(stem, meta, 'boxes', sum(len(v) for v in dets.values()), 'wall', out['wall_s'])
