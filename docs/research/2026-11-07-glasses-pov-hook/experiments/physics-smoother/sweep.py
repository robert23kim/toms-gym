"""Sensitivity of the dev means to the fit window and depth-weight exponent (run AFTER the default dev table; this
reads dev truth through score_v2, so any default changed because of it is tuned on truth). Writes results/sensitivity.json."""
import json, os, subprocess, sys, tempfile
HERE = os.path.dirname(os.path.abspath(__file__))
L2 = os.path.dirname(os.path.dirname(HERE))
PY = sys.executable
sys.path.insert(0, L2)
import score_v2  # noqa
STEMS = ['20260915_185331_19de9ec7', '20260915_185454_f240c883', '20260915_185645_9fde3c16', '20260915_190115_a7cf2c70']
KEYS = ['path_err_rms', 'path_err_far', 'entry_err', 'hook_err']
rows = []
for ft0, wexp in [(24, 2), (24, 4), (30, 2), (36, 2), (0, 2), (0, 4), (24, 0)]:
    env = dict(os.environ, PS_FIT_FROM_FT=str(ft0), PS_W_EXP=str(wexp))
    per = {}
    with tempfile.TemporaryDirectory() as td:
        for s in STEMS:
            subprocess.run([PY, os.path.join(HERE, 'run.py'), s], env=env, check=True, capture_output=True)
            tr = json.load(open(os.path.join(HERE, 'tracks', f'{s}.json')))
            r = score_v2.score(tr, json.load(open(os.path.join(L2, 'truth', f'{s}.json'))))
            per[s[9:15]] = {k: r[k] for k in KEYS} | {'dir': r['direction_ok'], 'kind': tr['path_fit']['kind']}
    means = {k: round(sum(per[s][k] for s in per) / len(per), 2) for k in KEYS}
    means['direction_ok_pct'] = round(100 * sum(per[s]['dir'] for s in per) / len(per), 1)
    rows.append({'fit_from_ft': ft0, 'w_exp': wexp, 'means': means, 'per_stem': per})
    print(ft0, wexp, means, {s: per[s]['kind'] for s in per}, flush=True)
json.dump(rows, open(os.path.join(HERE, 'results', 'sensitivity.json'), 'w'), indent=1)
