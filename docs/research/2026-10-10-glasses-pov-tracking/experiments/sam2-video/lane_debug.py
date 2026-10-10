"""lane_debug.py <stem> [k_end_offset]: re-run the engine lane pass on a saved track, verbose."""
import json, os, sys, time
L = '/Users/toka/code/toms_gym/docs/research/2026-10-10-glasses-pov-tracking'
X = os.path.join(L, 'experiments', 'sam2-video'); E = '/Users/toka/code/bowling-app/pov-engine'
sys.path.insert(0, E)
stem = sys.argv[1]; trim = int(sys.argv[2]) if len(sys.argv) > 2 else 999; start = int(sys.argv[3]) if len(sys.argv) > 3 else 0
cut = {c['stem']: c for c in json.load(open(L + '/work/cuts/cuts.json'))}[stem]
tr = json.load(open(f'{X}/tracks/{stem}.json')); off = cut['cut_start']
k_pin = cut['pin_hit_frame'] - off
pos = [(p['f'] - off, p['x'], p['y'], p['r'], 1.0) for p in tr['frames'] if start <= p["f"] - off - (cut["release_frame"] - off) and p["f"] - off <= k_pin + trim]
print(stem, 'positions', len(pos), 'k', pos[0][0], '..', pos[-1][0], 'pin k', k_pin)
from scripts.sam_lane_pass import run_sam_lane_pass
os.chdir(E); t0 = time.time()
calib, fields = run_sam_lane_pass(cut['cut_path'], pos, pin_hit=k_pin, weights='sam2.1_t.pt', weights_dir=E + '/models',
                                  json_path=None, overlay_path=f'{X}/work/lane_debug_{stem}.jpg', verbose=True, segment=pos)
print('fields', {k: v for k, v in fields.items() if k != 'lane_edges'}, 'time', round(time.time() - t0, 1))
