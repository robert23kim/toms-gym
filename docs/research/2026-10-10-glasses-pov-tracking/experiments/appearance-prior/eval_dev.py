"""eval_dev.py [run.py flags...]  : run every dev stem sequentially with the given flags, score, print a table.
Writes results/<tag>.json. Use --out-dir to keep variants apart."""
import json, subprocess, sys, time
from pathlib import Path
X = Path(__file__).resolve().parent
L = X.parent.parent
PY = sys.executable
DEV = ['20260915_185121_23d80f05', '20260915_185331_19de9ec7', '20260915_185645_9fde3c16', '20260915_185454_f240c883',
       '20260915_190115_a7cf2c70']
flags = sys.argv[1:]
out_dir = X
if '--out-dir' in flags:
    out_dir = Path(flags[flags.index('--out-dir') + 1])
tag = (flags[flags.index('--tag') + 1] if '--tag' in flags else 'default')
rows = []
for stem in DEV:
    t0 = time.time()
    r = subprocess.run([PY, str(X / 'run.py'), stem] + flags, capture_output=True, text=True, cwd=str(X))
    wall = time.time() - t0
    if r.returncode != 0:
        print(stem, 'FAILED', r.stderr[-800:]); rows.append({'stem': stem, 'error': r.stderr[-300:]}); continue
    s = subprocess.run([PY, str(L / 'score_tracks.py'), str(out_dir / 'tracks' / f'{stem}.json'), str(L / 'truth' / f'{stem}.json')],
                       capture_output=True, text=True)
    sc = json.loads(s.stdout)
    sc.pop('lane_err_per_frame', None)
    sc['wall_s'] = round(wall, 1)
    rows.append(sc)
    print(f"{stem[9:15]} recall {sc['recall_pct']:5.1f} ({sc['n_matched']}/{sc['n_truth_points']}) med {sc['median_px_err']} "
          f"board_err {sc['board_err']} lane_err {sc['lane_err_boards']} win {sc['window_err']} pass {sc['pass']} wall {sc['wall_s']}s")
ok = [r for r in rows if 'recall_pct' in r]
mr = sum(r['recall_pct'] for r in ok) / max(1, len(ok))
be = [r['board_err'] for r in ok if r['board_err'] is not None]
print(f"MEAN recall {mr:.1f}  board_err mean {sum(be)/len(be) if be else None} (n={len(be)})  pass {sum(1 for r in ok if r['pass'])}/{len(ok)}  flags {flags}")
(X / 'results').mkdir(exist_ok=True)
json.dump({'flags': flags, 'rows': rows, 'mean_recall': round(mr, 1)}, open(X / 'results' / f'{tag}.json', 'w'), indent=1)
