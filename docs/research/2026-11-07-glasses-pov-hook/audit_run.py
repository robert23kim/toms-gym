"""audit_run.py <audit.json> <script.py> [args...]: run a script under a sys.addaudithook that records every open()
path, then statically scan every loaded non-stdlib/non-site-packages module for 'truth', 'label' and the holdout path."""
import atexit
import json
import os
import re
import runpy
import sys

HO = '/Users/toka/pov-holdout'
OPENS = []


def hook(ev, args):
    if ev == 'open' and args and isinstance(args[0], (str, bytes, os.PathLike)):
        OPENS.append(os.fsdecode(args[0]))


def finish(out):
    opens = list(OPENS)
    mods = []
    for name, m in list(sys.modules.items()):
        f = getattr(m, '__file__', None)
        if not f or not f.endswith('.py') or not f.startswith(('/Users/toka/code/', HO)) or '/.venv/' in f or 'site-packages' in f:
            continue
        mods.append(f)
    hits = []
    pat = re.compile(r'truth|label|pov-holdout', re.I)
    for f in sorted(set(mods)):
        for i, line in enumerate(open(f, errors='replace').read().splitlines(), 1):
            if pat.search(line):
                hits.append({'file': f, 'line': i, 'text': line.strip()[:160]})
    bad = [p for p in opens if re.search(r'truth|label', p, re.I) or HO in p]
    rec = {'script': sys.argv[0], 'argv': sys.argv[1:], 'n_opens': len(opens),
           'opens_unique': sorted(set(opens)), 'opens_matching_truth_label_or_holdout': bad,
           'modules_scanned': sorted(set(mods)), 'static_hits': hits}
    with open(out, 'w') as fh:
        json.dump(rec, fh, indent=1)


if __name__ == '__main__':
    out = sys.argv[1]
    script = sys.argv[2]
    sys.argv = [script] + sys.argv[3:]
    sys.path.insert(0, os.path.dirname(os.path.abspath(script)))
    atexit.register(finish, out)
    sys.addaudithook(hook)
    runpy.run_path(script, run_name='__main__')
